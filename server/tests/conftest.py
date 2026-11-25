"""Shared test setup.

The tests exercise the real routes against a PostgreSQL database (see
database.py). `TestClient(app)` only runs the app's lifespan handler when it is
used as a context manager, and these test modules create it at import time, so
the schema has to be created here. This matters most in CI, where the database
starts out empty.
"""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest

from database import engine
from admin_access import initialize_schema
from routes import auth


@pytest.fixture(scope="session", autouse=True)
def create_schema():
    initialize_schema(engine)
    yield


@pytest.fixture(name="clock")
def auth_clock(monkeypatch):
    class Clock(datetime):
        current = datetime.now(UTC).replace(microsecond=0)

        @classmethod
        def now(cls, tz):
            return cls.current.astimezone(tz)

    monkeypatch.setattr(auth, "datetime", Clock)
    return Clock


@pytest.fixture
def sign_up(clock):
    def register_and_login(client, name, *, request_admin=False):
        email = f"{name}@udayton.edu"
        password = "abc123"
        registered = client.post(
            "/auth/register", json={"email": email, "password": password, "is_admin": request_admin}
        )
        assert registered.status_code == 202
        setup = registered.json()
        authenticator = pyotp.parse_uri(setup["provisioning_uri"])
        verified = client.post(
            "/auth/register/verify",
            json={"challenge_token": setup["challenge_token"], "otp": authenticator.at(clock.current)},
        )
        assert verified.status_code == 201
        assert verified.json()["is_admin"] is False

        # Enrollment consumed the first code. Sign in on the next authenticator interval.
        clock.current += timedelta(seconds=authenticator.interval)
        login = client.post("/auth/login", data={"username": email, "password": password})
        assert login.status_code == 202
        verified_login = client.post(
            "/auth/login/verify",
            json={"challenge_token": login.json()["challenge_token"], "otp": authenticator.at(clock.current)},
        )
        assert verified_login.status_code == 200
        assert client.cookies.get(auth.DASHBOARD_COOKIE) is not None
        return verified.json()["id"], {"Authorization": f"Bearer {verified_login.json()['access_token']}"}

    return register_and_login
