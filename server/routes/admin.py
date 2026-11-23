from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from admin_access import require_admin
from database import get_db
from models import User
from routes.auth import DASHBOARD_COOKIE, user_from_token


router = APIRouter(prefix="/admin", tags=["admin"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


class AdminUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    is_admin: bool
    created_at: datetime


class RoleChange(BaseModel):
    is_admin: bool


@router.get("/access", status_code=204)
def dashboard_access(
    db: Db, dashboard_cookie: Annotated[str | None, Cookie(alias=DASHBOARD_COOKIE)] = None,
) -> Response:
    if not dashboard_cookie:
        raise HTTPException(401, "Authentication required")
    require_admin(user_from_token(dashboard_cookie, db, audience=DASHBOARD_COOKIE))
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/users", response_model=list[AdminUser])
def list_users(admin: Admin, db: Db):
    return db.scalars(select(User).order_by(User.email)).all()


@router.patch("/users/{user_id}/role", response_model=AdminUser)
def update_role(user_id: UUID, change: RoleChange, admin: Admin, db: Db):
    # Serialize competing demotions and recheck the caller's role after waiting.
    admins = set(db.scalars(select(User.id).where(User.is_admin).order_by(User.id).with_for_update()))
    if admin.id not in admins:
        raise HTTPException(403, "Administrator access required")
    user = db.get(User, user_id, populate_existing=True)
    if user is None:
        raise HTTPException(404, "User not found")
    if not change.is_admin and user.id == admin.id:
        raise HTTPException(409, "You cannot remove your own admin access.")
    user.is_admin = change.is_admin
    db.commit()
    db.refresh(user)
    return user
