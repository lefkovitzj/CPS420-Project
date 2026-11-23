import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from catalog import SectionRecord, publish_catalog
from database import engine, get_db
from main import app
from models.course import CourseSection
from routes.auth import get_current_user


TERM = "209980"
OTHER_TERM = "209910"


@pytest.fixture
def db():
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection) as session:
                yield session
        finally:
            transaction.rollback()


def test_search_and_refresh_preserve_course_identity(db):
    first = SectionRecord(TERM, "10001", "CPS", "420", "Software Engineering")
    second = SectionRecord(TERM, "10002", "cps", "420", "Software Engineering")
    math = SectionRecord(TERM, "10003", "MTH", "420", "Mathematics")
    other = SectionRecord(OTHER_TERM, "10001", "BIO", "101", "Biology")
    publish_catalog(db, OTHER_TERM, [other])
    assert publish_catalog(db, TERM, [first, second, math]) == 3
    publish_catalog(db, TERM, [first, second, math])

    client = TestClient(app)
    assert client.get("/courses", params={"term": TERM}).status_code == 401
    assert client.get("/courses/terms").status_code == 401
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: object()
    try:
        def search(q="", term=TERM):
            response = client.get("/courses", params={"term": term, "q": q})
            assert response.status_code == 200
            return response.json()

        results = search("420")
        assert [result["subject"] for result in results] == ["CPS", "MTH"]
        cps_id = results[0]["id"]
        assert results[1]["id"] != cps_id
        assert search("software")[0]["id"] == cps_id
        assert search("CPS 420")[0]["id"] == cps_id
        assert search("unlisted") == []
        terms = client.get("/courses/terms").json()
        assert terms.index(TERM) < terms.index(OTHER_TERM)

        updated = SectionRecord(TERM, "10002", "CPS", "420", "Software Design")
        publish_catalog(db, TERM, [updated])
        assert search() == [
            {"id": cps_id, "subject": "CPS", "course_number": "420", "title": "Software Design"}
        ]
        assert not db.get(CourseSection, (TERM, "10001")).available
        assert search(term=OTHER_TERM)[0]["subject"] == "BIO"
    finally:
        del app.dependency_overrides[get_db]
        del app.dependency_overrides[get_current_user]
        client.close()


def test_incomplete_or_conflicting_refresh_preserves_published_sections(db):
    previous = SectionRecord(TERM, "10001", "CPS", "420", "Software Engineering")
    publish_catalog(db, TERM, [previous])
    replacement = SectionRecord(TERM, "10002", "MTH", "101", "Algebra")
    for bad_snapshot in (
        [],
        [replacement, SectionRecord(TERM, "10002", "MTH", "201", "Calculus")],
        [replacement, SectionRecord(TERM, "", "CHM", "101", "Chemistry")],
        [replacement, SectionRecord(OTHER_TERM, "10003", "BIO", "101", "Biology")],
    ):
        with pytest.raises(ValueError):
            publish_catalog(db, TERM, bad_snapshot)
        assert db.get(CourseSection, (TERM, previous.crn)).available
        assert db.get(CourseSection, (TERM, replacement.crn)) is None
