from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from database import get_db
from models import Course, User, UserCourse
from routes.auth import get_current_user
from schemas import AddCourseRequest, UserCourseItem

router = APIRouter(
    prefix="/profile/courses",
    tags=["profile"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=UserCourseItem, status_code=status.HTTP_201_CREATED)
def add_user_course(
    payload: AddCourseRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    subject = payload.subject.strip().upper()
    course_number = payload.course_number.strip().upper()

    if not subject or not course_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="subject and course_number must not be blank.",
        )

    course = db.scalar(
        select(Course).where(
            func.upper(Course.subject) == subject,
            func.upper(Course.course_number) == course_number,
        )
    )
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    query = (
        insert(UserCourse)
        .values(
            user_id=current_user.id,
            course_id=course.id,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "course_id"])
        .returning(UserCourse)
    )
    created = db.scalar(query)

    if created is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course is already in your profile.",
        )

    db.commit()

    return UserCourseItem(
        id=created.id,
        course_id=course.id,
        subject=course.subject,
        course_number=course.course_number,
        created_at=created.created_at,
    )


@router.get("", response_model=list[UserCourseItem])
def list_user_courses(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    query = (
        select(
            UserCourse.id,
            Course.id.label("course_id"),
            Course.subject,
            Course.course_number,
            UserCourse.created_at,
        )
        .join(Course, Course.id == UserCourse.course_id)
        .where(UserCourse.user_id == current_user.id)
        .order_by(Course.subject, Course.course_number)
    )
    return db.execute(query).mappings().all()