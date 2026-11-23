from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from models.course import Course, CourseSection
from routes.auth import get_current_user


router = APIRouter(prefix="/courses", tags=["courses"], dependencies=[Depends(get_current_user)])


class CourseResult(BaseModel):
    id: int
    subject: str
    course_number: str
    title: str


@router.get("/terms", response_model=list[str])
def available_terms(db: Annotated[Session, Depends(get_db)]):
    query = (
        select(CourseSection.term_code)
        .where(CourseSection.available)
        .distinct()
        .order_by(CourseSection.term_code.desc())
    )
    return db.scalars(query).all()


@router.get("", response_model=list[CourseResult])
def search_courses(
    term: Annotated[str, Query(min_length=1, max_length=64)],
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str, Query(max_length=160)] = "",
):
    # Section titles can differ for a single course (e.g. special topics).
    # Show one matching title and one selectable ID per subject and course number.
    query = (
        select(Course.id, Course.subject, Course.course_number, func.min(CourseSection.title).label("title"))
        .join(CourseSection, CourseSection.course_id == Course.id)
        .where(CourseSection.term_code == term, CourseSection.available)
    )
    if search := q.strip():
        label = Course.subject + " " + Course.course_number + " " + CourseSection.title
        query = query.where(label.icontains(search, autoescape=True))
    query = query.group_by(Course.id).order_by(Course.subject, Course.course_number).limit(50)
    return db.execute(query).mappings().all()
