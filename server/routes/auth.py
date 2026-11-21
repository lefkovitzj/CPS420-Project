from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Authenticator, TrustedDevice, User
from schemas.mfa import AccessToken, MFAConfigured, MFARequired, MFASetupRequired, VerifyMFARequest
from schemas.user import RegisterRequest, UserResponse
from services.mfa import (
    ALGORITHM,
    DEVICE_TRUST_PERIOD,
    SECRET_KEY,
    lock_challenge,
    new_authenticator,
    read_device_id,
    set_device_cookie,
    start_challenge,
    verify_otp,
)

ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/auth", tags=["auth"])
Database = Annotated[Session, Depends(get_db)]


def issue_access_token(user: User) -> AccessToken:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return AccessToken(access_token=jwt.encode(
        {"sub": user.email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM
    ))


def commit_auth_changes(db: Session, failure_message: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=failure_message) from exc


# Import this in any route you want to protect
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Database,
):
    try:
        email = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    except (InvalidTokenError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@router.post(
    "/login",
    response_model=AccessToken,
    responses={202: {"model": MFARequired | MFASetupRequired}},
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
    db: Database,
) -> AccessToken | JSONResponse:
    """Verify the email and password. Request authenticator setup or a code when needed."""
    email = form_data.username.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not password_hash.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    device_id = read_device_id(request) or uuid4()
    authenticator = db.get(Authenticator, user.id)
    if authenticator is not None:
        trusted_device = db.get(TrustedDevice, (user.id, device_id))
        if (
            trusted_device is not None
            and trusted_device.last_mfa_at > datetime.now(UTC) - DEVICE_TRUST_PERIOD
        ):
            response.headers["Cache-Control"] = "no-store"
            return issue_access_token(user)

    encrypted_secret, provisioning_uri = (None, None)
    if authenticator is None:
        encrypted_secret, provisioning_uri = new_authenticator(user.email)
    challenge_token = start_challenge(
        db,
        device_id=device_id,
        purpose="login",
        email=user.email,
        password_hash=user.password_hash,
        user_id=user.id,
        encrypted_secret=encrypted_secret,
    )
    commit_auth_changes(db, "Sign-in could not be started. Please try again.")

    if provisioning_uri is not None:
        challenge = MFASetupRequired(challenge_token=challenge_token, provisioning_uri=provisioning_uri)
    else:
        challenge = MFARequired(challenge_token=challenge_token)
    pending_response = JSONResponse(
        challenge.model_dump(), status_code=202, headers={"Cache-Control": "no-store"}
    )
    set_device_cookie(request, pending_response, device_id)
    return pending_response


@router.post("/login/verify")
def verify_login(
    data: VerifyMFARequest, request: Request, response: Response, db: Database
) -> AccessToken | MFAConfigured:
    """Verify a login code, or confirm setup for an existing account."""
    pending = lock_challenge(db, request, "login", data.challenge_token)
    # Serialize code consumption across devices for the same account.
    user = db.scalar(select(User).where(User.id == pending.user_id).with_for_update())
    if user is None or user.password_hash != pending.password_hash:
        raise HTTPException(status_code=401, detail="Invalid authentication challenge. Submit your credentials again.")

    response.headers["Cache-Control"] = "no-store"
    authenticator = db.get(Authenticator, user.id)
    now = datetime.now(UTC)
    if pending.encrypted_secret is not None:
        if authenticator is not None:
            raise HTTPException(status_code=409, detail="Authenticator already configured. Sign in again.")
        step = verify_otp(pending.encrypted_secret, data.otp, now)
        db.add(Authenticator(user_id=user.id, encrypted_secret=pending.encrypted_secret, last_used_step=step))
        db.delete(pending)
        commit_auth_changes(db, "Authenticator setup could not be saved. Please try again.")
        return MFAConfigured()

    if authenticator is None:
        raise HTTPException(status_code=401, detail="Authenticator setup is required. Sign in again.")

    authenticator.last_used_step = verify_otp(
        authenticator.encrypted_secret, data.otp, now, authenticator.last_used_step
    )
    device_id = pending.device_id
    trusted_device = db.get(TrustedDevice, (user.id, device_id))
    if trusted_device is None:
        db.add(TrustedDevice(user_id=user.id, device_id=device_id, last_mfa_at=now))
    else:
        trusted_device.last_mfa_at = now

    token = issue_access_token(user)
    db.delete(pending)
    commit_auth_changes(db, "Sign-in could not be completed. Please sign in again.")
    set_device_cookie(request, response, device_id)
    return token


@router.post("/register", status_code=202)
def register(data: RegisterRequest, request: Request, response: Response, db: Database) -> MFASetupRequired:
    """Start registration and return the provisioning URI for the authenticator app."""
    if db.scalar(select(User.id).where(User.email == data.email)) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    device_id = read_device_id(request) or uuid4()
    encrypted_secret, provisioning_uri = new_authenticator(data.email)
    challenge_token = start_challenge(
        db,
        device_id=device_id,
        purpose="register",
        email=data.email,
        password_hash=password_hash.hash(data.password),
        encrypted_secret=encrypted_secret,
    )
    commit_auth_changes(db, "Authenticator setup could not be started. Please try again.")
    set_device_cookie(request, response, device_id)
    response.headers["Cache-Control"] = "no-store"
    return MFASetupRequired(challenge_token=challenge_token, provisioning_uri=provisioning_uri)


@router.post("/register/verify", status_code=201)
def verify_registration(data: VerifyMFARequest, request: Request, db: Database) -> UserResponse:
    """Create the account after verifying the authenticator setup code."""
    pending = lock_challenge(db, request, "register", data.challenge_token)
    if pending.encrypted_secret is None:
        raise HTTPException(status_code=401, detail="Invalid authentication challenge. Submit your credentials again.")

    step = verify_otp(pending.encrypted_secret, data.otp, datetime.now(UTC))
    user = User(email=pending.email, password_hash=pending.password_hash)
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Authenticator setup could not be saved. Please try again.") from exc

    db.add(Authenticator(user_id=user.id, encrypted_secret=pending.encrypted_secret, last_used_step=step))
    db.delete(pending)
    account = UserResponse.model_validate(user)
    commit_auth_changes(db, "Authenticator setup could not be saved. Please try again.")
    return account


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
