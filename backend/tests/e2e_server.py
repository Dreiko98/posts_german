"""Loopback-only test fixture. Never loaded by the production image."""

import os
import threading
from sqlalchemy import text
from app.db import engine, Base, SessionLocal
from app.models import User, Connection, Configuration
from app.security import password_hasher, encrypt
from app.services import current_context
from app.ai import ADAPTERS
from tests.fakes import fake_ai
from app.worker import run_one

if not engine.url.database.endswith("_test") or os.environ.get("E2E_FIXTURE") != "1":
    raise SystemExit("Only an explicitly selected test database is permitted.")
with engine.begin() as conn:
    conn.execute(
        text(
            "TRUNCATE "
            + ",".join('"' + name + '"' for name in Base.metadata.tables)
            + " RESTART IDENTITY CASCADE"
        )
    )
with SessionLocal() as db:
    db.add(
        User(
            username="e2e",
            password_hash=password_hasher.hash(os.environ["E2E_PASSWORD"]),
        )
    )
    db.add(
        Connection(
            provider="openai",
            config={},
            encrypted=encrypt({"api_key": "test-only"}),
            status="conectada",
            detail="Proveedor simulado para pruebas E2E.",
        )
    )
    db.add(
        Configuration(
            key="preferences", value={"app_name": "Germán Content Studio · pruebas"}
        )
    )
    db.commit()
    current_context(db)
ADAPTERS["openai"] = fake_ai
ADAPTERS["anthropic"] = fake_ai


def worker():
    while True:
        if not run_one("e2e-worker"):
            threading.Event().wait(0.2)


threading.Thread(target=worker, daemon=True).start()
if __name__ == "__main__":
    import uvicorn
    from app.api import app

    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False, log_level="warning")
