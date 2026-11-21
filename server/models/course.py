from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("subject", "course_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str]
    course_number: Mapped[str]


class CourseSection(Base):
    __tablename__ = "course_sections"

    term_code: Mapped[str] = mapped_column(primary_key=True)
    crn: Mapped[str] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    title: Mapped[str]
    available: Mapped[bool] = mapped_column(default=True)
