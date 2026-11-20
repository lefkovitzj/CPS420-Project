import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Uuid, false, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        # Requires users to end in @udayton.edu
        CheckConstraint(
            "email ~* '^[^@]+@udayton\\.edu$'",
            name="check_udayton_email"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
