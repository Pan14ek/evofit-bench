"""Validate Alembic head against a disposable PostgreSQL database."""

import os
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from scripts.disposable_postgres import (
    DISPOSABLE_DATABASE_NAME,
    SCHEMA_RESET_CONFIRMATION_ENV,
    validate_disposable_postgres_test_url,
)

REQUIRED_TABLES = {"users", "tasks", "notifications", "audit_events", "alembic_version"}
EXPECTED_REVISION = "0001_a0_schema"


def validate() -> None:
    """Recreate public schema, migrate to head, and verify basic persistence."""
    database_url = os.environ.get("TEST_DATABASE_URL")
    try:
        database_url = validate_disposable_postgres_test_url(
            database_url,
            schema_reset_confirmation=os.environ.get(SCHEMA_RESET_CONFIRMATION_ENV),
        )
    except ValueError as error:
        raise RuntimeError(f"Refusing migration-test: {error}") from error

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            actual_database = connection.scalar(text("SELECT current_database()"))
        if actual_database != DISPOSABLE_DATABASE_NAME:
            raise RuntimeError(
                "Refusing migration-test: PostgreSQL connected to unexpected database "
                f"{actual_database!r}"
            )
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
