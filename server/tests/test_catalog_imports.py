import secrets
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.exc import OperationalError

from admin_access import require_admin
from banner_scraper import BannerError
from catalog import SectionRecord
from database import SessionLocal
from main import app
from models.catalog_import import CatalogImport
from models.course import Course, CourseSection
from routes import catalog_imports


def test_background_refresh_status_conflicts_and_preserves_previous_catalog(monkeypatch):
    term = str(900000 + secrets.randbelow(100000))
    subject = f"TEST{term}"
    client = TestClient(app)
    path = "/admin/imports"
    payload = {"term_code": term}
    assert client.post(path, json=payload).status_code == 401
    assert client.get(f"{path}/latest").status_code == 401
    app.dependency_overrides[require_admin] = lambda: object()

    def scrape(term_code):
        latest = client.get(f"{path}/latest", params=payload).json()
        assert latest["status"] == "running"
        assert client.post(path, json=payload).status_code == 409
        return [SectionRecord(term_code, "10001", subject, "420", "Software Engineering")]

    def unavailable(_):
        raise BannerError("Banner stopped returning pages before the import was complete.")

    try:
        monkeypatch.setattr(catalog_imports, "scrape_banner", scrape)
        start = client.post(path, json=payload)
        assert start.status_code == 202
        job = client.get(f"{path}/{start.json()['id']}").json()
        assert (job["status"], job["section_count"]) == ("succeeded", 1)
        assert job["finished_at"]

        monkeypatch.setattr(catalog_imports, "scrape_banner", unavailable)
        retry = client.post(path, json=payload)
        assert retry.status_code == 202
        failure = client.get(f"{path}/latest", params=payload).json()
        assert failure["id"] == retry.json()["id"]
        assert failure["status"] == "failed"
        assert "before the import was complete" in failure["error"]
        with SessionLocal() as db:
            section = db.get(CourseSection, (term, "10001"))
            assert section.available and section.title == "Software Engineering"
    finally:
        del app.dependency_overrides[require_admin]
        client.close()
        with SessionLocal.begin() as db:
            db.execute(delete(CourseSection).where(CourseSection.term_code == term))
            db.execute(delete(Course).where(Course.subject == subject))
            db.execute(delete(CatalogImport).where(CatalogImport.term_code == term))


@pytest.mark.parametrize("published_before_disconnect", [False, True])
def test_import_recovers_when_postgres_loses_the_worker_connection(monkeypatch, published_before_disconnect):
    term = str(900000 + secrets.randbelow(100000))
    subject = f"OUTAGE{term}"
    records = [SectionRecord(term, "10001", subject, "420", "Software Engineering")]
    path = "/admin/imports"

    def disconnect():
        raise OperationalError(None, None, ConnectionError("temporary outage"))

    class DisconnectedWorker:
        @contextmanager
        def begin(self):
            if published_before_disconnect:
                # Simulate COMMIT succeeding, but the acknowledgement being lost.
                with SessionLocal.begin() as db:
                    yield db
            disconnect()

        def __call__(self):
            disconnect()  # The attempt to record the failure also loses its connection.

    client = TestClient(app)
    app.dependency_overrides[require_admin] = lambda: object()
    monkeypatch.setattr(catalog_imports, "scrape_banner", lambda _: records)
    try:
        with monkeypatch.context() as outage:
            outage.setattr(catalog_imports, "SessionLocal", DisconnectedWorker())
            start = client.post(path, json={"term_code": term})
            assert start.status_code == 202
            job_id = start.json()["id"]
        if published_before_disconnect:
            # The first poll after recovery must preserve the successful import.
            job = client.get(f"{path}/latest", params={"term_code": term}).json()
            assert (job["id"], job["status"], job["section_count"]) == (job_id, "succeeded", 1)
        else:
            # Starting again works even when no status request arrives first.
            retry = client.post(path, json={"term_code": term})
            assert retry.status_code == 202
            assert client.get(f"{path}/{job_id}").json()["status"] == "failed"
            assert client.get(f"{path}/{retry.json()['id']}").json()["status"] == "succeeded"
    finally:
        del app.dependency_overrides[require_admin]
        client.close()
        with SessionLocal.begin() as db:
            db.execute(delete(CourseSection).where(CourseSection.term_code == term))
            db.execute(delete(Course).where(Course.subject == subject))
            db.execute(delete(CatalogImport).where(CatalogImport.term_code == term))
