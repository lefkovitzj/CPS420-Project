import secrets

from fastapi.testclient import TestClient
from sqlalchemy import delete

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
