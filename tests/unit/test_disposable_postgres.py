"""Negative checks for destructive PostgreSQL test-database configuration."""

import pytest

from scripts.disposable_postgres import (
    SCHEMA_RESET_CONFIRMATION,
    validate_disposable_postgres_test_url,
)

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
