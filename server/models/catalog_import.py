from datetime import datetime

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CatalogImport(Base):
    __tablename__ = "catalog_imports"
    __table_args__ = (
        Index("uq_running_catalog_import_term", "term_code", unique=True,
              postgresql_where=text("status = 'running'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    term_code: Mapped[str] = mapped_column(String(6))
    status: Mapped[str] = mapped_column(String(12), default="running")
    section_count: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(String(300))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
