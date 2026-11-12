# User input validation
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator

class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        # Friendly error if it isn't a UD address (the database also enforces this).
        if not re.fullmatch(r"[^@\s]+@udayton\.edu", value):
            raise ValueError("Email must be a valid @udayton.edu address")
        return value
 
    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if not 3 <= len(value) <= 128:
            raise ValueError("Password must be 3 to 128 characters")
        return value
 

class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    created: datetime