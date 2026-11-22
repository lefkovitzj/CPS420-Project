import uuid
from datetime import datetime, timedelta, timezone
import jwt
from fastapi.testclient import TestClient
from routes.auth import ALGORITHM, SECRET_KEY  # adjust if your file is routers/auth.py
from main import app

client = TestClient(app)

def new_email():
    return f"pytest_{uuid.uuid4().hex[:8]}@udayton.edu"

def register(email, password="password123"):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(email, password="password123"):
    return client.post("/auth/login", data={"username": email, "password": password})


def make_token(sub, secret=SECRET_KEY, expires_in=timedelta(minutes=5)):
    payload = {"exp": datetime.now(timezone.utc) + expires_in}
    if sub is not None:
        payload["sub"] = sub
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def get_me(token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

# --- Happy path -------------------------------------------------------------
def test_register_login_me():
    email = new_email()
    assert register(email).status_code == 201

    res = login(email)
    assert res.status_code == 200
    token = res.json()["access_token"]

    me = get_me(token)
    assert me.status_code == 200
    assert me.json()["email"] == email


# --- Registration failures --------------------------------------------------
def test_register_duplicate_email():
    email = new_email()
    assert register(email).status_code == 201
    assert register(email).status_code == 409


def test_register_duplicate_email_different_case():
    email = new_email()
    assert register(email).status_code == 201
    # The schema lowercases emails, so this should still count as a duplicate
    assert register(email.upper().replace("@UDAYTON.EDU", "@udayton.edu")).status_code == 409


def test_register_non_udayton_email():
    assert register("someone@gmail.com").status_code == 422


def test_register_password_too_short():
    assert register(new_email(), password="ab").status_code == 422


def test_register_password_too_long():
    assert register(new_email(), password="a" * 129).status_code == 422

# --- Login failures ---------------------------------------------------------
def test_login_wrong_password():
    email = new_email()
    register(email)
    assert login(email, password="wrongpassword").status_code == 401
