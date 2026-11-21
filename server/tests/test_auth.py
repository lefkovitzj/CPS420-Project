import uuid
from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import SessionLocal
from main import app
from models import Authenticator, TrustedDevice, User
from routes import auth
from services.mfa import DEVICE_COOKIE, DEVICE_TRUST_PERIOD

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_cookies():
    client.cookies.clear()


@pytest.fixture
def clock(monkeypatch):
    class Clock(datetime):
        current = datetime.now(UTC).replace(microsecond=0)

        @classmethod
        def now(cls, tz):
            return cls.current.astimezone(tz)

    monkeypatch.setattr(auth, "datetime", Clock)
    return Clock


def new_email():
    return f"pytest_{uuid.uuid4().hex[:8]}@udayton.edu"


def register(email, password="password123", browser=client):
    return browser.post("/auth/register", json={"email": email, "password": password})


def login(email, password="password123", browser=client):
    return browser.post("/auth/login", data={"username": email, "password": password})


def verify(flow, challenge, otp, browser=client):
    return browser.post(
        f"/auth/{flow}/verify", json={"challenge_token": challenge["challenge_token"], "otp": otp}
    )


def enrolled_account(clock, browser=client):
    email = new_email()
    setup = register(email, browser=browser)
    assert setup.status_code == 202
    authenticator = pyotp.parse_uri(setup.json()["provisioning_uri"])
    response = verify("register", setup.json(), authenticator.at(clock.current), browser)
    assert response.status_code == 201
    clock.current += timedelta(seconds=30)
    return email, authenticator, uuid.UUID(response.json()["id"])


def incorrect_code(authenticator, now):
    valid_codes = {authenticator.at(now + timedelta(seconds=offset)) for offset in (-30, 0, 30)}
    return next(code for code in ("000000", "000001", "000002", "000003") if code not in valid_codes)


def trusted_devices(user_id):
    with SessionLocal() as db:
        return dict(db.execute(
            select(TrustedDevice.device_id, TrustedDevice.last_mfa_at).where(TrustedDevice.user_id == user_id)
        ).all())


def get_me(token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})


# --- Happy path -------------------------------------------------------------
def test_register_login_me(clock):
    email, authenticator, user_id = enrolled_account(clock)
    assert trusted_devices(user_id) == {}

    challenge = login(email)
    assert challenge.status_code == 202
    assert challenge.json()["status"] == "mfa_required"
    assert "access_token" not in challenge.json()
    assert get_me(challenge.json()["challenge_token"]).status_code == 401
    assert get_me(client.cookies[DEVICE_COOKIE]).status_code == 401
    assert "HttpOnly" in challenge.headers["set-cookie"]
    assert "SameSite=lax" in challenge.headers["set-cookie"]

    result = verify("login", challenge.json(), authenticator.at(clock.current))
    assert result.status_code == 200
    me = get_me(result.json()["access_token"])
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert list(trusted_devices(user_id).values()) == [clock.current]


# --- Registration failures --------------------------------------------------
def test_register_duplicate_email(clock):
    email, _, _ = enrolled_account(clock)
    assert register(email).status_code == 409


def test_register_duplicate_email_different_case(clock):
    email, _, _ = enrolled_account(clock)
    # The schema lowercases emails, so this should still count as a duplicate
    assert register(email.upper().replace("@UDAYTON.EDU", "@udayton.edu")).status_code == 409


def test_register_non_udayton_email():
    assert register("someone@gmail.com").status_code == 422


def test_register_password_too_short():
    assert register(new_email(), password="ab").status_code == 422


def test_register_password_too_long():
    assert register(new_email(), password="a" * 129).status_code == 422


def test_registration_requires_correct_code_and_can_retry(clock):
    email = new_email()
    setup = register(email).json()
    assert setup["status"] == "mfa_setup_required"
    assert login(email).status_code == 401
    authenticator = pyotp.parse_uri(setup["provisioning_uri"])
    wrong = verify("register", setup, incorrect_code(authenticator, clock.current))
    assert wrong.status_code == 401
    assert "authenticator code" in wrong.json()["detail"]
    assert login(email).status_code == 401

    otp = authenticator.at(clock.current)
    created = verify("register", setup, otp)
    assert created.status_code == 201
    assert created.json()["email"] == email
    assert "access_token" not in created.json()
    assert verify("register", setup, otp).status_code == 401


def test_registration_restarts_and_rejects_the_previous_challenge(clock):
    email = new_email()
    original = register(email).json()
    otp = pyotp.parse_uri(original["provisioning_uri"]).at(clock.current)
    assert register(email).status_code == 202
    assert verify("register", original, otp).status_code == 401


def test_registration_save_failure_can_retry(clock, monkeypatch):
    email = new_email()
    setup = register(email).json()
    otp = pyotp.parse_uri(setup["provisioning_uri"]).at(clock.current)

    def fail_commit(_session):
        raise SQLAlchemyError("Simulated save failure")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        assert verify("register", setup, otp).status_code == 503
    assert login(email).status_code == 401
    assert verify("register", setup, otp).status_code == 201


# --- Login failures ---------------------------------------------------------
def test_me_requires_bearer_authentication():
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Not authenticated"}


def test_login_wrong_password(clock):
    email, _, _ = enrolled_account(clock)
    assert login(email, password="wrongpassword").status_code == 401


def test_login_challenge_is_device_bound_and_can_retry(clock):
    email, authenticator, user_id = enrolled_account(clock)
    challenge = login(email).json()

    with TestClient(app) as other_browser:
        other = login(email, browser=other_browser)
        assert other.status_code == 202
        code = authenticator.at(clock.current)
        assert verify("login", challenge, code, other_browser).status_code == 401

    incorrect = incorrect_code(authenticator, clock.current)
    for _ in range(11):
        rejected = verify("login", challenge, incorrect)
        assert rejected.status_code == 401
        assert "authenticator code" in rejected.json()["detail"]
    assert trusted_devices(user_id) == {}

    clock.current += timedelta(minutes=16)
    code = authenticator.at(clock.current)
    assert verify("login", challenge, code).status_code == 200
    assert verify("login", challenge, code).status_code == 401


def test_trust_is_per_device_and_expires_after_thirty_days(clock):
    email, authenticator, user_id = enrolled_account(clock)
    challenge = login(email).json()
    assert verify("login", challenge, authenticator.at(clock.current)).status_code == 200
    first_verified_at = clock.current
    original_history = trusted_devices(user_id)

    with TestClient(app, base_url="https://testserver") as other_browser:
        other = login(email, browser=other_browser)
        assert other.status_code == 202
        assert "Secure" in other.headers["set-cookie"]
        assert verify("login", other.json(), authenticator.at(clock.current), other_browser).status_code == 401
        clock.current += timedelta(days=1)
        assert verify("login", other.json(), authenticator.at(clock.current), other_browser).status_code == 200
        history = trusted_devices(user_id)
        assert len(history) == 2
        assert original_history.items() <= history.items()

        clock.current = first_verified_at + DEVICE_TRUST_PERIOD - timedelta(microseconds=1)
        assert login(email).status_code == 200
        assert login(email, password="wrongpassword").status_code == 401
        assert trusted_devices(user_id) == history

        clock.current += timedelta(microseconds=1)
        expired = login(email)
        assert expired.status_code == 202
        assert login(email, browser=other_browser).status_code == 200
        assert verify("login", expired.json(), authenticator.at(clock.current)).status_code == 200
        renewed = trusted_devices(user_id)
        original_device_id = next(iter(original_history))
        assert renewed == {**history, original_device_id: clock.current}


def test_tampered_device_cookie_does_not_grant_trust(clock):
    email, authenticator, _ = enrolled_account(clock)
    challenge = login(email).json()
    assert verify("login", challenge, authenticator.at(clock.current)).status_code == 200

    cookie = client.cookies[DEVICE_COOKIE]
    client.cookies.clear()
    client.cookies.set(DEVICE_COOKIE, f"{cookie}.tampered")
    assert login(email).status_code == 202


def test_existing_account_must_set_up_authenticator_before_signing_in(clock):
    email = new_email()
    with SessionLocal() as db:
        user = User(email=email, password_hash=auth.password_hash.hash("password123"))
        db.add(user)
        db.commit()
        user_id = user.id

    challenge = login(email)
    assert challenge.status_code == 202
    setup = challenge.json()
    assert setup["status"] == "mfa_setup_required"
    authenticator = pyotp.parse_uri(setup["provisioning_uri"])
    configured = verify("login", setup, authenticator.at(clock.current))
    assert configured.status_code == 200
    assert configured.json() == {"status": "mfa_configured"}
    assert trusted_devices(user_id) == {}
    assert login(email).json()["status"] == "mfa_required"

    with SessionLocal() as db:
        enrollment = db.get(Authenticator, user_id)
        assert authenticator.secret not in enrollment.encrypted_secret
