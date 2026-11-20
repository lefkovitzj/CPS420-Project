import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from admin_access import require_admin
from banner_scraper import BannerError, list_banner_terms, scrape_banner
from catalog import publish_catalog
from database import SessionLocal, get_db
from models.catalog_import import CatalogImport

router = APIRouter(prefix="/admin/imports", tags=["admin"], dependencies=[Depends(require_admin)])
logger = logging.getLogger(__name__)


class ImportRequest(BaseModel):
    term_code: str = Field(pattern=r"^[0-9]{6}$")


class ImportStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    term_code: str
    status: str
    section_count: int | None
    started_at: datetime
    finished_at: datetime | None
    error: str | None


def recover_interrupted_imports(db: Session) -> None:
    # The Compose backend runs a single Uvicorn process. Its old background tasks
    # cannot survive a restart, even though their status rows do.
    db.execute(update(CatalogImport).where(CatalogImport.status == "running").values(
        status="failed", error="The server restarted during the import. Start a new import to retry.",
        finished_at=datetime.now(timezone.utc)))
    db.commit()


def run_import(job_id: int, term_code: str) -> None:
    try:
        sections = scrape_banner(term_code)
        with SessionLocal.begin() as db:
            job = db.get(CatalogImport, job_id)
            if job is None or job.status != "running":
                return
            job.section_count = publish_catalog(db, term_code, sections)
            job.status = "succeeded"
            job.finished_at = datetime.now(timezone.utc)
    except Exception as exc:
        logger.exception("Banner import %s failed for term %s", job_id, term_code)
        # Do not expose raw browser traces or database connection details in the dashboard.
        reason = ("Banner returned incomplete or invalid course data."
                  if isinstance(exc, ValueError) else "Could not finish the Banner import. Check the backend log before retrying.")
        if isinstance(exc, BannerError):
            reason = str(exc)[:300]
        with SessionLocal.begin() as db:
            db.execute(update(CatalogImport).where(
                CatalogImport.id == job_id, CatalogImport.status == "running").values(
                    status="failed", finished_at=datetime.now(timezone.utc), error=reason))


@router.get("/terms")
def terms() -> list[dict[str, str]]:
    try:
        return list_banner_terms()
    except Exception as exc:
        logger.warning("Could not list Banner terms: %s", exc)
        raise HTTPException(502, "Could not load terms from Banner.") from exc


@router.get("/latest", response_model=ImportStatus | None)
def latest_import(term_code: str | None = None, db: Session = Depends(get_db)):
    query = select(CatalogImport)
    if term_code is not None:
        query = query.where(CatalogImport.term_code == term_code)
    return db.scalar(query.order_by(CatalogImport.id.desc()).limit(1))


@router.get("/{job_id}", response_model=ImportStatus)
def import_status(job_id: int, db: Session = Depends(get_db)):
    job = db.get(CatalogImport, job_id)
    if job is None:
        raise HTTPException(404, "Import not found.")
    return job


@router.post("", response_model=ImportStatus, status_code=202)
def start_import(request: ImportRequest, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # The partial unique index serializes concurrent starts, including requests
    # from separate admin tabs. Completed runs never block a fresh import.
    statement = insert(CatalogImport).values(term_code=request.term_code, status="running").on_conflict_do_nothing()
    job = db.scalar(statement.returning(CatalogImport))
    if job is None:
        raise HTTPException(409, "An import for this term is already running.")
    result = ImportStatus.model_validate(job)
    db.commit()
    tasks.add_task(run_import, result.id, result.term_code)
    return result
