from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class UserCourseRequest(BaseModel):
    subject: str 
    course_number: str 

    @field_validator("subject", "course_number")
    @classmethod
    def normalize_and_reject_blank(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("must not be blank.")
        return normalized


class UserCourseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    subject: str
    course_number: str
    created_at: datetime