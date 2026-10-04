"""Validate Alembic head against a disposable PostgreSQL database."""

import os
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command

REQUIRED_TABLES = {"users", "tasks", "notifications", "audit_events", "alembic_version"}
EXPECTED_REVISION = "0001_a0_schema"


def validate() -> None:
    """Recreate public schema, migrate to head, and verify basic persistence."""
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        raise RuntimeError("TEST_DATABASE_URL must name a disposable PostgreSQL database")
    engine = create_engine(database_url, pool_pre_ping=True)
    database_name = engine.url.database or ""
    if "evofit" not in database_name.lower():
        raise RuntimeError("Refusing migration-test: database name must contain 'evofit'")
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic.ini"))
        config.attributes["database_url"] = database_url
        command.upgrade(config, "head")
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        missing = REQUIRED_TABLES - tables
        if missing:
            raise RuntimeError(f"migration is missing required tables: {sorted(missing)}")
        with engine.begin() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != EXPECTED_REVISION:
                raise RuntimeError(f"expected Alembic revision {EXPECTED_REVISION}, got {revision}")
            user_id = uuid4()
            connection.execute(
                text(
                    "INSERT INTO users (id, name, email, created_at) "
                    "VALUES (:id, :name, :email, now())"
                ),
                {"id": user_id, "name": "Migration check", "email": f"{user_id}@example.test"},
            )
            read_id = connection.scalar(text("SELECT id FROM users WHERE id=:id"), {"id": user_id})
            if read_id != user_id:
                raise RuntimeError("basic insert/read failed after migration")
        print(f"Migration validation passed at {EXPECTED_REVISION}: {sorted(REQUIRED_TABLES)}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    validate()
