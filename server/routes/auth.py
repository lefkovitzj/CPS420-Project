from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models import Authenticator, TrustedDevice, User
from schemas.mfa import AccessToken, AuthError, MFAConfigured, MFARequired, MFASetupRequired, VerifyMFARequest
from schemas.user import RegisterRequest, UserResponse
from services.mfa import (
    ALGORITHM,
    DEVICE_COOKIE,
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
DASHBOARD_COOKIE = "dashboard_access"

password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    bearerFormat="JWT",
    description=(
        "Paste the `access_token` returned by sign-in or MFA verification. "
        f"The JWT expires after {ACCESS_TOKEN_EXPIRE_MINUTES} minutes."
    ),
    auto_error=False,
)
router = APIRouter(prefix="/auth", tags=["auth"])
Database = Annotated[Session, Depends(get_db)]
DEVICE_COOKIE_HEADER = {
    "Set-Cookie": {
        "description": (
            f"Sets the `{DEVICE_COOKIE}` cookie for this browser with `HttpOnly`, `SameSite=Lax`, "
            "and `Path=/`. Uses `Secure` when the backend sees HTTPS or `AUTH_COOKIE_SECURE=true`."
        ),
        "schema": {"type": "string"},
    },
}


def issue_access_token(user: User) -> AccessToken:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return AccessToken(access_token=jwt.encode(
        {"sub": user.email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM
    ))


def set_dashboard_cookie(request: Request, response: Response, user: User) -> None:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    page_token = jwt.encode(
        {"sub": user.email, "exp": expire, "aud": DASHBOARD_COOKIE},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response.set_cookie(
        DASHBOARD_COOKIE,
        page_token,
        path="/admin",
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def commit_auth_changes(db: Session, failure_message: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=failure_message) from exc


def user_from_token(token: str, db: Session, audience: str | None = None) -> User:
    try:
        email = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=audience)["sub"]
    except (InvalidTokenError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


# Import this in any route you want to protect
def get_current_user(
    authorization: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Database,
):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return user_from_token(authorization.credentials, db)


@router.post(
    "/login",
    response_model=AccessToken,
    response_description="Access token issued for a trusted device.",
    responses={
        202: {
            "model": MFARequired | MFASetupRequired,
            "description": "Authenticator code or setup required. Keep the device cookie for verification.",
            "headers": DEVICE_COOKIE_HEADER,
        },
        401: {"model": AuthError, "description": "Incorrect email or password."},
        503: {"model": AuthError, "description": "Sign-in could not be started."},
    },
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
    db: Database,
) -> AccessToken | JSONResponse:
    """Send the email in the `username` form field along with `password`.

    A `202` response with `mfa_required` asks for an authenticator code.
    With `mfa_setup_required`, first add the account to the authenticator app using
    `provisioning_uri`. In either case, send the returned `challenge_token` and the
    current code to `POST /auth/login/verify` from the same browser.
    """
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
            set_dashboard_cookie(request, response, user)
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


@router.post("/logout", status_code=204)
def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie(DASHBOARD_COOKIE, path="/admin")
    return response


@router.post(
    "/login/verify",
    response_description=(
        "Access token issued or authenticator setup confirmed. When an access token is "
        f"issued, the browser receives a device cookie and is trusted for {DEVICE_TRUST_PERIOD.days} days."
    ),
    responses={
        200: {"headers": DEVICE_COOKIE_HEADER},
        401: {"model": AuthError, "description": "Invalid challenge or authenticator code."},
        409: {"model": AuthError, "description": "Authenticator already configured. Sign in again."},
        503: {"model": AuthError, "description": "Verification could not be saved."},
    },
)
def verify_login(
    data: VerifyMFARequest, request: Request, response: Response, db: Database
) -> AccessToken | MFAConfigured:
    """Verify the authenticator code using the challenge from `POST /auth/login`.

    A regular verification returns an `access_token`. If `status` is
    `mfa_configured`, start sign-in again to obtain an access token.
    """
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
    set_dashboard_cookie(request, response, user)
    return token


@router.post(
    "/register",
    status_code=202,
    response_description="Registration is pending authenticator setup.",
    responses={
        202: {"headers": DEVICE_COOKIE_HEADER},
        409: {"model": AuthError, "description": "Email already registered."},
        503: {"model": AuthError, "description": "Registration could not be started."},
    },
)
def register(data: RegisterRequest, request: Request, response: Response, db: Database) -> MFASetupRequired:
    """Start registration using a University of Dayton email address.

    Add the account to the authenticator app using `provisioning_uri`. Send the
    returned `challenge_token` and the current code to `POST /auth/register/verify`
    from the same browser to create the account.
    """
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


@router.post(
    "/register/verify",
    status_code=201,
    response_description="Account created. Sign in to obtain an access token.",
    responses={
        401: {"model": AuthError, "description": "Invalid challenge or authenticator code."},
        409: {"model": AuthError, "description": "Email already registered."},
        503: {"model": AuthError, "description": "Account could not be saved."},
    },
)
def verify_registration(data: VerifyMFARequest, request: Request, db: Database) -> UserResponse:
    """Create the account using the challenge from `POST /auth/register` and the authenticator code."""
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


@router.get(
    "/me",
    summary="Get the signed-in user",
    response_model=UserResponse,
    responses={401: {"model": AuthError, "description": "Bearer token is missing, invalid, or expired."}},
)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    """Send `Authorization: Bearer <access_token>` to retrieve the current user's profile.

    Sign in again when the access token expires.
    """
    return current_user
