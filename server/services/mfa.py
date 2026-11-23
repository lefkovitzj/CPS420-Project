import os
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import compare_digest, digest
from secrets import token_urlsafe
from uuid import UUID

import jwt
import pyotp
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request, Response
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import PendingAuthentication

SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
DEVICE_COOKIE = "device_id"
DEVICE_COOKIE_AUDIENCE = "cps420-device"
DEVICE_TRUST_PERIOD = timedelta(days=30)
DEVICE_COOKIE_MAX_AGE = int(timedelta(days=365).total_seconds())

# A dedicated key lets deployments rotate JWT signing without affecting enrollment.
_encryption_key = os.environ.get("MFA_ENCRYPTION_KEY") or urlsafe_b64encode(
    digest(SECRET_KEY.encode(), b"cps420 authenticator encryption", "sha256")
)
_authenticator_cipher = Fernet(_encryption_key)


def read_device_id(request: Request) -> UUID | None:
    cookie = request.cookies.get(DEVICE_COOKIE)
    if not cookie:
        return None
    try:
        claims = jwt.decode(
            cookie,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=DEVICE_COOKIE_AUDIENCE,
            options={"require": ["sub", "aud"]},
        )
        return UUID(claims["sub"])
    except (InvalidTokenError, ValueError):
        return None


def set_device_cookie(request: Request, response: Response, device_id: UUID) -> None:
    cookie = jwt.encode(
        {"sub": str(device_id), "aud": DEVICE_COOKIE_AUDIENCE},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response.set_cookie(
        key=DEVICE_COOKIE,
        value=cookie,
        max_age=DEVICE_COOKIE_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https" or os.environ.get("AUTH_COOKIE_SECURE") == "true",
        samesite="lax",
    )


def new_authenticator(email: str) -> tuple[str, str]:
    secret = pyotp.random_base32()
    encrypted_secret = _authenticator_cipher.encrypt(secret.encode()).decode()
    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="CPS420")
    return encrypted_secret, provisioning_uri


def verify_otp(
    encrypted_secret: str,
    otp: str,
    now: datetime,
    last_used_step: int = -1,
) -> int:
    if len(otp) == 6 and otp.isascii() and otp.isdecimal():
        secret = _authenticator_cipher.decrypt(encrypted_secret.encode()).decode()
        authenticator = pyotp.TOTP(secret)
        step = authenticator.timecode(now)
        for candidate in (step, step - 1, step + 1):
            if compare_digest(otp, authenticator.generate_otp(candidate)):
                if candidate > last_used_step:
                    return candidate
                break
    raise HTTPException(status_code=401, detail="Incorrect or already used authenticator code")


def start_challenge(
    db: Session,
    *,
    device_id: UUID,
    purpose: str,
    email: str,
    password_hash: str,
    user_id: UUID | None = None,
    encrypted_secret: str | None = None,
) -> str:
    token = token_urlsafe(32)
    values = {
        "token_hash": sha256(token.encode()).hexdigest(),
        "email": email,
        "password_hash": password_hash,
        "user_id": user_id,
        "encrypted_secret": encrypted_secret,
    }
    # Starting over replaces this browser's previous attempt for the same flow.
    new_challenge = insert(PendingAuthentication).values(device_id=device_id, purpose=purpose, **values)
    db.execute(new_challenge.on_conflict_do_update(
        index_elements=[PendingAuthentication.device_id, PendingAuthentication.purpose],
        set_=values,
    ))
    return token


def lock_challenge(
    db: Session, request: Request, purpose: str, token: str
) -> PendingAuthentication:
    device_id = read_device_id(request)
    if device_id is not None:
        pending = db.scalar(
            select(PendingAuthentication)
            .where(
                PendingAuthentication.device_id == device_id,
                PendingAuthentication.purpose == purpose,
                PendingAuthentication.token_hash == sha256(token.encode()).hexdigest(),
            )
            .with_for_update()
        )
        if pending is not None:
            return pending
    raise HTTPException(status_code=401, detail="Invalid authentication challenge. Submit your credentials again.")
