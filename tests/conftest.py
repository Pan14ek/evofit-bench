"""Safety hooks shared by the integration test suite."""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from scripts.disposable_postgres import (
    DISPOSABLE_DATABASE_NAME,
    SCHEMA_RESET_CONFIRMATION_ENV,
    validate_disposable_postgres_test_url,
)


def pytest_collection_finish(session: pytest.Session) -> None:
    """Verify any configured integration DB before its schema-reset fixture runs."""
    integration_root = Path(__file__).resolve().parent / "integration"
    integration_selected = any(
        Path(str(item.path)).is_relative_to(integration_root) for item in session.items
    )
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not integration_selected or not database_url:
        return

    try:
        database_url = validate_disposable_postgres_test_url(
            database_url,
            schema_reset_confirmation=os.environ.get(SCHEMA_RESET_CONFIRMATION_ENV),
        )
    except ValueError as error:
        raise pytest.UsageError(str(error)) from error

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            actual_database = connection.scalar(text("SELECT current_database()"))
        if actual_database != DISPOSABLE_DATABASE_NAME:
            raise pytest.UsageError(
                "PostgreSQL connected to an unexpected database before schema reset: "
                f"{actual_database!r}"
            )
    except SQLAlchemyError as error:
        raise pytest.UsageError(
            "Could not verify TEST_DATABASE_URL before integration schema reset"
        ) from error
    finally:
        engine.dispose()
