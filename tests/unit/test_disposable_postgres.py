"""Negative checks for destructive PostgreSQL test-database configuration."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import disposable_postgres
from scripts.disposable_postgres import (
    SCHEMA_RESET_CONFIRMATION,
    validate_disposable_postgres_test_url,
)
from tests import conftest as pytest_hooks

_URL = "postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test"


def test_accepts_confirmed_local_disposable_postgres_url() -> None:
    assert (
        validate_disposable_postgres_test_url(
            _URL,
            schema_reset_confirmation=SCHEMA_RESET_CONFIRMATION,
        )
        == _URL
    )


@pytest.mark.parametrize(
    ("database_url", "confirmation", "message"),
    [
        (_URL, None, "EVOFIT_TEST_DATABASE_ALLOW_SCHEMA_RESET"),
        (_URL.replace("localhost", "db.internal"), SCHEMA_RESET_CONFIRMATION, "loopback"),
        (_URL.replace("evofit_test", "evofit"), SCHEMA_RESET_CONFIRMATION, "dedicated"),
        (
            f"{_URL}?hostaddr=192.0.2.10",
            SCHEMA_RESET_CONFIRMATION,
            "cannot override",
        ),
        (
            f"{_URL}?dbname=production",
            SCHEMA_RESET_CONFIRMATION,
            "cannot override",
        ),
        (
            "sqlite:///evofit_test.db",
            SCHEMA_RESET_CONFIRMATION,
            "must use PostgreSQL",
        ),
    ],
)
def test_rejects_unsafe_database_targets(
    database_url: str,
    confirmation: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_disposable_postgres_test_url(
            database_url,
            schema_reset_confirmation=confirmation,
        )


def test_rejects_missing_database_url() -> None:
    with pytest.raises(ValueError, match="TEST_DATABASE_URL must name"):
        validate_disposable_postgres_test_url(
            None,
            schema_reset_confirmation=SCHEMA_RESET_CONFIRMATION,
        )


def test_integration_collection_hook_rejects_missing_reset_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", _URL)
    monkeypatch.delenv(disposable_postgres.SCHEMA_RESET_CONFIRMATION_ENV, raising=False)
    monkeypatch.setattr(
        pytest_hooks,
        "create_engine",
        lambda *_args, **_kwargs: pytest.fail("unsafe target reached database connection"),
    )
    session = SimpleNamespace(
        items=[
            SimpleNamespace(path=Path(pytest_hooks.__file__).parent / "integration/test_example.py")
        ]
    )

    with pytest.raises(pytest.UsageError, match="EVOFIT_TEST_DATABASE_ALLOW_SCHEMA_RESET"):
        pytest_hooks.pytest_collection_finish(session)  # type: ignore[arg-type]


def test_integration_collection_hook_verifies_live_database_before_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", _URL)
    monkeypatch.setenv(
        disposable_postgres.SCHEMA_RESET_CONFIRMATION_ENV,
        SCHEMA_RESET_CONFIRMATION,
    )

    class FakeConnection:
        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        @staticmethod
        def scalar(_query: object) -> str:
            return "evofit_test"

    class FakeEngine:
        disposed = False

        @staticmethod
        def connect() -> FakeConnection:
            return FakeConnection()

        def dispose(self) -> None:
            self.disposed = True

    engine = FakeEngine()
    monkeypatch.setattr(pytest_hooks, "create_engine", lambda *_args, **_kwargs: engine)
    session = SimpleNamespace(
        items=[
            SimpleNamespace(path=Path(pytest_hooks.__file__).parent / "integration/test_example.py")
        ]
    )

    pytest_hooks.pytest_collection_finish(session)  # type: ignore[arg-type]

    assert engine.disposed
