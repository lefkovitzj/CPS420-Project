import os
from datetime import datetime, timedelta, timezone
from typing import Annotated
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas.user import RegisterRequest, UserResponse

# Gets key from .env passed through docker
SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Creates password hasher
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])


# Import this in any route you want to protect
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        # Gets user's email from decoding token
        email = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    except (InvalidTokenError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    # queries for user
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@router.post("/login")
def login( form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)], ):
    """
    Log in with email and password.

    Form fields: `username` (the email) and `password`.

    Returns: `{"access_token": "<jwt>", "token_type": "bearer"}`
    Errors: 401 if the email or password is wrong.
    """
    
    # Strips email for query
    email = form_data.username.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    # Checks password and email
    if user is None or not password_hash.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    # Creates access token if it is a valid user
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": user.email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
    """Create an account. Email must be @udayton.edu. Password must be between 3 and 128 characters."""
    # Creates a new user
    user = User(email=data.email, password_hash=password_hash.hash(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(user)
    return user

@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    # Given an access token gets the current user
    return current_user