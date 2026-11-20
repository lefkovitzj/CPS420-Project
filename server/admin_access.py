"""Admin role checks and operator entry point: python -m admin_access EMAIL."""

import argparse
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import Connection, Engine, select, text
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Base, User
from routes.auth import get_current_user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Administrator access required")
    return user


def add_admin_column(conn: Connection) -> None:
    # create_all creates new tables but does not upgrade an existing users table.
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin boolean NOT NULL DEFAULT false"))


def initialize_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        add_admin_column(conn)


def promote_user(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()).with_for_update())
    if user is None:
        raise ValueError("No registered user with that email address")
    user.is_admin = True
    db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grant admin access to a registered user.")
    parser.add_argument("email")
    args = parser.parse_args()
    with SessionLocal() as session:
        try:
            promote_user(session, args.email)
        except ValueError as exc:
            parser.exit(1, f"{exc}\n")
    print("Administrator access granted.")
