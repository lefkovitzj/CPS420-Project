# User input validation
import re
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator

class RegisterRequest(BaseModel):
    """What the client must send to /auth/register (JSON body)."""
    email: EmailStr
    password: str

    @field_validator("email", mode="after")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        value = value.strip().lower()
        if not value.endswith("@udayton.edu"):
            raise ValueError("Only @udayton.edu addresses are allowed")
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
    is_admin: bool
    
    model_config = {"from_attributes": True}
