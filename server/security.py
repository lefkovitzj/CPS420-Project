import uuid
from datetime import datetime, timedelta, timezone
import jwt  
from pwdlib import PasswordHash
import config

password_hasher = PasswordHash.recommended()
 
 
def hash_password(password: str) -> str:
    return password_hasher.hash(password)
 
 
def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)
 
 
# --- JWT --------------------------------------------------------------------
def create_access_token(user_id: uuid.UUID) -> str:
    """Build a signed JWT that says 'this token belongs to user X until time Y'."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_LIFETIME_MINUTES)
    payload = {
        "sub": str(user_id), 
        "exp": expires,       
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None