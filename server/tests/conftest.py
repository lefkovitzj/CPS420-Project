"""Shared test setup.

The tests exercise the real routes against a PostgreSQL database (see
database.py). `TestClient(app)` only runs the app's lifespan handler when it is
used as a context manager, and these test modules create it at import time, so
the schema has to be created here. This matters most in CI, where the database
starts out empty.
"""

import pytest

from database import engine
from admin_access import initialize_schema


@pytest.fixture(scope="session", autouse=True)
def create_schema():
    initialize_schema(engine)
    yield
