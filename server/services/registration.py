from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models import User
 
hasher = PasswordHash.recommended()
 
 
class EmailAlreadyRegistered(Exception):
    """Raised when the email is already in the database."""
 
def register_user(db: Session, email: str, password: str) -> User:
    user = User(email=email, password_hash=hasher.hash(password))
    db.add(user)  # stage it
 
    try:
        db.commit()  
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegistered()
 
    db.refresh(user)  
    return us