from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from database import get_db
from models import Course, User, UserCourse
from routes.auth import get_current_user
from schemas import UserCourseRequest, UserCourseItem

router = APIRouter(
    prefix="/profile/courses",
    tags=["profile"],
    dependencies=[Depends(get_current_user)],
)

def lookup_course(db: Session, subject: str, course_number: str) -> Course | None:
    normalized_subject = subject.strip().upper()
    normalized_course_number = course_number.strip().upper()

    if not normalized_subject or not normalized_course_number:
        return None

    return db.scalar(
        select(Course).where(
            func.upper(Course.subject) == normalized_subject,
            func.upper(Course.course_number) == normalized_course_number,
        )
    )

@router.post("", response_model=UserCourseItem, status_code=status.HTTP_201_CREATED)
def add_user_course(
    payload: UserCourseRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):

    course = lookup_course(db, payload.subject, payload.course_number)
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


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_course(
    payload: UserCourseRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    course = lookup_course(db, payload.subject, payload.course_number)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found in your profile.",
        )

    deleted_id = db.scalar(
        delete(UserCourse)
        .where(
            UserCourse.user_id == current_user.id,
            UserCourse.course_id == course.id,
        )
        .returning(UserCourse.id)
    )

    if deleted_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found in your profile.",
        )

    db.commit()