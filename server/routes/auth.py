from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
 
from database import get_db
from schemas.users import RegisterRequest, UserResponse
from services.users import EmailAlreadyRegistered, register_user
 
 router = APIRouter(prefix="/auth", tags=["auth"])
 
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    # By the time we get here, FastAPI has already checked and cleaned `data`
    # using the rules in schemas/users.py.
    try:
        return register_user(db, data.email, data.password)
    except EmailAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
