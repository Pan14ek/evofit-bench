"""PostgreSQL-backed integration fixtures."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.db.session import get_session
from app.main import app
from scripts.disposable_postgres import (
    DISPOSABLE_DATABASE_NAME,
    SCHEMA_RESET_CONFIRMATION_ENV,
    validate_disposable_postgres_test_url,
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Create an isolated PostgreSQL schema-backed API client."""
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL must point to PostgreSQL")
    try:
        database_url = validate_disposable_postgres_test_url(
            database_url,
            schema_reset_confirmation=os.environ.get(SCHEMA_RESET_CONFIRMATION_ENV),
        )
    except ValueError as error:
        pytest.fail(str(error), pytrace=False)

    test_engine = create_engine(database_url, pool_pre_ping=True)
    with test_engine.connect() as connection:
        actual_database = connection.scalar(text("SELECT current_database()"))
    if actual_database != DISPOSABLE_DATABASE_NAME:
        test_engine.dispose()
        pytest.fail(
            "PostgreSQL connected to an unexpected database before schema reset: "
            f"{actual_database!r}",
            pytrace=False,
        )
    with test_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    migration_config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    migration_config.attributes["database_url"] = database_url
    command.upgrade(migration_config, "head")
    testing_session = sessionmaker(bind=test_engine, expire_on_commit=False)

    def override_session() -> Iterator[Session]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.state.test_session_factory = testing_session
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.test_session_factory
    with test_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    test_engine.dispose()
