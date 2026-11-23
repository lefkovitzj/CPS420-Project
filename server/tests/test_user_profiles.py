from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from database import engine, get_db
from main import app


@pytest.fixture
def profile_env():
    # Temp tables keep users, catalog courses, and saved user_courses isolated per test.
    with engine.connect() as conn, conn.begin():
        conn.execute(text("CREATE TEMP TABLE users (LIKE users INCLUDING ALL) ON COMMIT DROP"))
        conn.execute(text("CREATE TEMP TABLE courses (LIKE courses INCLUDING ALL) ON COMMIT DROP"))
        conn.execute(text("CREATE TEMP TABLE user_courses (LIKE user_courses INCLUDING ALL) ON COMMIT DROP"))

        conn.execute(
            text(
                """
                INSERT INTO courses (subject, course_number)
                VALUES
                    ('BIO', '151'),
                    ('BIO', '152'),
                    ('CPS', '420')
                """
            )
        )

        sessions = sessionmaker(bind=conn, join_transaction_mode="create_savepoint")

        def get_test_db():
            with sessions() as db:
                yield db

        app.dependency_overrides[get_db] = get_test_db
        try:
            yield sessions
        finally:
            app.dependency_overrides.pop(get_db)


def sign_up(client, name):
    email = f"{name}@udayton.edu"
    registered = client.post(
        "/auth/register",
        json={"email": email, "password": "abc123", "is_admin": False},
    )
    assert registered.status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": "abc123"})
    assert login.status_code == 200
    return registered.json()["id"], {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_profile_courses_requires_auth():
    with closing(TestClient(app)) as client:
        assert client.get("/profile/courses").status_code == 401
        assert (
            client.post(
                "/profile/courses",
                json={"subject": "CPS", "course_number": "420"},
            ).status_code
            == 401
        )


def test_add_and_list_user_courses_normalizes_and_scopes_to_user(profile_env):
    with closing(TestClient(app)) as client, closing(TestClient(app)) as other_client:
        _, bearer = sign_up(client, "student1")
        _, other_bearer = sign_up(other_client, "student2")

        # Initially empty
        initial = client.get("/profile/courses", headers=bearer)
        assert initial.status_code == 200
        assert initial.json() == []

        # Add with mixed case & surrounding whitespace
        added_cps = client.post(
            "/profile/courses",
            headers=bearer,
            json={"subject": " cps ", "course_number": " 420 "},
        )
        assert added_cps.status_code == 201
        cps_body = added_cps.json()
        assert cps_body["subject"] == "CPS"
        assert cps_body["course_number"] == "420"
        assert isinstance(cps_body["id"], int)
        assert isinstance(cps_body["course_id"], int)
        assert "created_at" in cps_body

        added_bio = client.post(
            "/profile/courses",
            headers=bearer,
            json={"subject": "BIO", "course_number": "151"},
        )
        assert added_bio.status_code == 201

        # GET returns sorted courses for student1 only
        listed = client.get("/profile/courses", headers=bearer)
        assert listed.status_code == 200
        assert [(item["subject"], item["course_number"]) for item in listed.json()] == [
            ("BIO", "151"),
            ("CPS", "420"),
        ]

        # Other user has their own separate list
        other_list = other_client.get("/profile/courses", headers=other_bearer)
        assert other_list.status_code == 200
        assert other_list.json() == []


def test_add_user_course_rejects_duplicates_missing_and_blank_values(profile_env):
    with closing(TestClient(app)) as client:
        _, bearer = sign_up(client, "student1")

        first = client.post(
            "/profile/courses",
            headers=bearer,
            json={"subject": "BIO", "course_number": "152"},
        )
        assert first.status_code == 201

        # Duplicate pairing -> 409 Conflict
        duplicate = client.post(
            "/profile/courses",
            headers=bearer,
            json={"subject": "bio", "course_number": "152"},
        )
        assert duplicate.status_code == 409

        # Unknown catalog course -> 404 Not Found
        missing = client.post(
            "/profile/courses",
            headers=bearer,
            json={"subject": "MTH", "course_number": "999"},
        )
        assert missing.status_code == 404

        # Empty / whitespace fields -> 422
        empty = client.post(
            "/profile/courses",
            headers=bearer,
            json={"subject": "", "course_number": "420"},
        )
        assert empty.status_code == 422

        whitespace = client.post(
            "/profile/courses",
            headers=bearer,
            json={"subject": "   ", "course_number": "   "},
        )
        assert whitespace.status_code == 422 

def test_delete_user_course_removes_course_and_scopes_to_user(profile_env):
    with closing(TestClient(app)) as client, closing(TestClient(app)) as other_client:
        _, bearer = sign_up(client, "student1")
        _, other_bearer = sign_up(other_client, "student2")

        # Add a course for student1
        added = client.post(
            "/profile/courses",
            headers=bearer,
            json={"subject": "BIO", "course_number": "151"},
        )
        assert added.status_code == 201

        # Add the same course for student2
        other_added = other_client.post(
            "/profile/courses",
            headers=other_bearer,
            json={"subject": "BIO", "course_number": "151"},
        )
        assert other_added.status_code == 201

        # Delete using mixed case and surrounding whitespace
        deleted = client.request(
            "DELETE",
            "/profile/courses",
            headers=bearer,
            json={"subject": " bio ", "course_number": " 151 "},
        )
        assert deleted.status_code == 204

        # Verify student1 no longer has the course
        student1_courses = client.get("/profile/courses", headers=bearer)
        assert student1_courses.status_code == 200
        assert student1_courses.json() == []

        # Verify student2 still has their course
        student2_courses = other_client.get(
            "/profile/courses", headers=other_bearer
        )
        assert student2_courses.status_code == 200
        assert len(student2_courses.json()) == 1
        assert student2_courses.json()[0]["subject"] == "BIO"
        assert student2_courses.json()[0]["course_number"] == "151"
        
def test_delete_user_course_rejects_missing_and_invalid_courses(profile_env):
    with closing(TestClient(app)) as client:
        _, bearer = sign_up(client, "student1")

        # Course exists in catalog but is not in the user's profile
        not_saved = client.request(
            "DELETE",
            "/profile/courses",
            headers=bearer,
            json={"subject": "BIO", "course_number": "152"},
        )
        assert not_saved.status_code == 404

        # Course does not exist in catalog
        missing = client.request(
            "DELETE",
            "/profile/courses",
            headers=bearer,
            json={"subject": "MTH", "course_number": "999"},
        )
        assert missing.status_code == 404

        # Empty field
        empty = client.request(
            "DELETE",
            "/profile/courses",
            headers=bearer,
            json={"subject": "", "course_number": "151"},
        )
        assert empty.status_code == 422

        # Whitespace-only fields
        whitespace = client.request(
            "DELETE",
            "/profile/courses",
            headers=bearer,
            json={"subject": "   ", "course_number": "   "},
        )
        assert whitespace.status_code == 422