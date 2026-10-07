import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://studio:test-local-only@127.0.0.1:55432/studio_test",
)
os.environ.setdefault("APP_ORIGIN", "http://localhost:8080")
os.environ.setdefault(
    "DATA_DIR", str(Path(__file__).parents[2] / ".local" / "test-files")
)
from cryptography.fernet import Fernet

os.environ.setdefault("MASTER_KEY", Fernet.generate_key().decode())
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from app.db import Base, engine, SessionLocal
from app.api import app
from app.models import User
from app.security import password_hasher


@pytest.fixture(autouse=True)
def clean_database():
    if not engine.url.database.endswith("_test"):
        raise RuntimeError(
            "Tests require an explicitly named *_test database; never run on production."
        )
    with engine.begin() as conn:
        names = ",".join('"' + name + '"' for name in Base.metadata.tables)
        conn.execute(text("TRUNCATE " + names + " RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client():
    with TestClient(app, base_url="http://localhost:8080") as c:
        yield c


@pytest.fixture
def authed(client, db):
    db.add(
        User(
            username="german",
            password_hash=password_hasher.hash("test-password-strong"),
        )
    )
    db.commit()
    result = client.post(
        "/api/auth/login",
        headers={"Origin": "http://localhost:8080"},
        json={"username": "german", "password": "test-password-strong"},
    )
    assert result.status_code == 200
    client.headers.update(
        {"Origin": "http://localhost:8080", "X-CSRF-Token": result.json()["csrf"]}
    )
    return client
