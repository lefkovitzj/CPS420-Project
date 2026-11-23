from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AddCourseRequest(BaseModel):
    subject: str 
    course_number: str 



class UserCourseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    subject: str
    course_number: str
    created_at: datetime