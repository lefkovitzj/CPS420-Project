from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Authenticator(Base):
    __tablename__ = "authenticators"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    encrypted_secret: Mapped[str] = mapped_column(Text)
    last_used_step: Mapped[int] = mapped_column(BigInteger)


class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    device_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    last_mfa_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PendingAuthentication(Base):
    __tablename__ = "pending_authentications"

    device_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    purpose: Mapped[str] = mapped_column(String(8), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    encrypted_secret: Mapped[str | None] = mapped_column(Text)
