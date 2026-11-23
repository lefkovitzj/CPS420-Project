from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models.course import Course, CourseSection


@dataclass(frozen=True)
class SectionRecord:
    term_code: str
    crn: str
    subject: str
    course_number: str
    title: str


def publish_catalog(db: Session, term_code: str, records: Iterable[SectionRecord]) -> int:
    """Publish a complete scrape in the caller's transaction; return its section count."""
    sections = {}
    for row in records:
        if row.term_code != term_code or not term_code.strip():
            raise ValueError("A section does not belong to the requested Banner term.")
        fields = (row.crn, row.subject, row.course_number, row.title)
        if any(not isinstance(value, str) or not value.strip() for value in fields):
            raise ValueError("A Banner section is missing its CRN, subject, course number, or title.")
        crn = row.crn.strip()
        values = (row.subject.strip().upper(), row.course_number.strip().upper(), row.title.strip())
        if crn in sections and sections[crn] != values:
            raise ValueError(f"Conflicting Banner rows for CRN {crn}.")
        sections[crn] = values

    if not sections:
        raise ValueError("Banner returned no sections. The existing catalog was kept.")

    course_keys = sorted({(subject, number) for subject, number, _ in sections.values()})
    db.execute(
        insert(Course).on_conflict_do_nothing(index_elements=["subject", "course_number"]),
        [{"subject": subject, "course_number": number} for subject, number in course_keys],
    )
    subjects = {subject for subject, _ in course_keys}
    course_ids = {
        (subject, number): course_id
        for subject, number, course_id in db.execute(
            select(Course.subject, Course.course_number, Course.id).where(Course.subject.in_(subjects))
        )
    }
    previous = {
        section.crn: section
        for section in db.scalars(select(CourseSection).where(CourseSection.term_code == term_code))
    }
    for crn, (subject, number, title) in sections.items():
        section = previous.pop(crn, None)
        if section is None:
            section = CourseSection(term_code=term_code, crn=crn)
            db.add(section)
        section.course_id = course_ids[subject, number]
        section.title = title
        section.available = True
    for missing in previous.values():
        missing.available = False

    db.flush()
    return len(sections)
