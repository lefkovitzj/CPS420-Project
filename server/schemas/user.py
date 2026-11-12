# User input validation
import re
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator

class RegisterRequest(BaseModel):
    """What the client must send to /auth/register (JSON body)."""
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@udayton\.edu", value):
            raise ValueError("Email must be a valid @udayton.edu address")
        return value
 
    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if not 3 <= len(value) <= 128:
            raise ValueError("Password must be 3 to 128 characters")
        return value
 

class UserResponse(BaseModel):
    """What the API sends back. Only the fields listed here are included."""
    id: UUID
    email: EmailStr
    created_at: datetime
    
    model_config = {"from_attributes": True}