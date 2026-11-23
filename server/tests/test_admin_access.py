from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from admin_access import add_admin_column, promote_user
from database import engine, get_db
from main import app
from routes.auth import DASHBOARD_COOKIE


@pytest.fixture
def accounts():
    # A private users table makes last-admin checks independent of existing accounts.
    with engine.connect() as conn, conn.begin():
        conn.execute(text("CREATE TEMP TABLE users (LIKE users INCLUDING ALL) ON COMMIT DROP"))
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
    registered = client.post("/auth/register", json={"email": email, "password": "abc123", "is_admin": True})
    assert registered.status_code == 201
    assert registered.json()["is_admin"] is False
    login = client.post("/auth/login", data={"username": email, "password": "abc123"})
    assert login.status_code == 200
    return registered.json()["id"], {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_dashboard_and_management_authorize_against_the_current_role(accounts):
    with closing(TestClient(app)) as client:
        assert client.get("/admin/access").status_code == 401
        assert client.get("/admin/users").status_code == 401
        user_id, bearer = sign_up(client, "first")
        role_url = f"/admin/users/{user_id}/role"
        assert client.get("/admin/access").status_code == 403
        assert client.get("/admin/users", headers=bearer).status_code == 403
        assert client.patch(role_url, json={"is_admin": True}, headers=bearer).status_code == 403

        with accounts() as db:
            promote_user(db, " FIRST@UDAYTON.EDU ")
        assert client.get("/admin/access").status_code == 204
        assert client.patch(role_url, json={"is_admin": False}).status_code == 401
        page_bearer = {"Authorization": f"Bearer {client.cookies.get(DASHBOARD_COOKIE)}"}
        assert client.get("/admin/users", headers=page_bearer).status_code == 401
        assert client.patch(role_url, json={"is_admin": False}, headers=bearer).status_code == 409
        listing = client.get("/admin/users", headers=bearer)
        assert listing.status_code == 200
        assert [u["id"] for u in listing.json()] == [user_id]
        assert "password_hash" not in listing.json()[0]

        with closing(TestClient(app)) as second:
            second_id, second_bearer = sign_up(second, "second")
            assert client.patch(f"/admin/users/{second_id}/role", json={"is_admin": True}, headers=bearer).status_code == 200
            self_change = client.patch(role_url, json={"is_admin": False}, headers=bearer)
            assert self_change.status_code == 409
            assert self_change.json()["detail"] == "You cannot remove your own admin access."
            assert second.patch(role_url, json={"is_admin": False}, headers=second_bearer).status_code == 200
            assert second.post("/auth/logout").status_code == 204
            assert second.get("/admin/access").status_code == 401
        assert client.get("/admin/users", headers=bearer).status_code == 403
        assert client.get("/admin/access").status_code == 403


def test_existing_accounts_receive_the_default_role():
    with engine.connect() as conn, conn.begin():
        conn.execute(text("CREATE TEMP TABLE users (id integer PRIMARY KEY) ON COMMIT DROP"))
        conn.execute(text("INSERT INTO users VALUES (1)"))
        add_admin_column(conn)
        assert conn.scalar(text("SELECT is_admin FROM users WHERE id = 1")) is False
        conn.execute(text("UPDATE users SET is_admin = true WHERE id = 1"))
        add_admin_column(conn)
        assert conn.scalar(text("SELECT is_admin FROM users WHERE id = 1")) is True


def test_upgraded_users_table_needs_only_a_read_only_check():
    with engine.begin() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        add_admin_column(conn)
