"""Safety checks for PostgreSQL databases that development tests may reset."""

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DISPOSABLE_DATABASE_NAME = "evofit_test"
SCHEMA_RESET_CONFIRMATION = "I_CONFIRM_DISPOSABLE_DATABASE_SCHEMA_RESET"
SCHEMA_RESET_CONFIRMATION_ENV = "EVOFIT_TEST_DATABASE_ALLOW_SCHEMA_RESET"
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_TARGET_OVERRIDE_OPTIONS = frozenset(
    {"database", "dbname", "host", "hostaddr", "service", "servicefile"}
)


def validate_disposable_postgres_test_url(
    database_url: str | None,
    *,
    schema_reset_confirmation: str | None,
) -> str:
    """Fail closed unless the target is the explicitly confirmed local test DB."""
    if not database_url:
        raise ValueError("TEST_DATABASE_URL must name the disposable PostgreSQL database")

    try:
        url = make_url(database_url)
    except ArgumentError as error:
        raise ValueError("TEST_DATABASE_URL is not a valid SQLAlchemy database URL") from error

    if url.drivername.split("+", maxsplit=1)[0] not in {"postgres", "postgresql"}:
        raise ValueError("TEST_DATABASE_URL must use PostgreSQL")
    if url.database != DISPOSABLE_DATABASE_NAME:
        raise ValueError(
            f"TEST_DATABASE_URL must target the dedicated {DISPOSABLE_DATABASE_NAME!r} database"
        )
    host = (url.host or "").strip("[]").lower()
    if host not in _LOOPBACK_HOSTS:
        raise ValueError("TEST_DATABASE_URL must connect through a local loopback host")
    overridden_target_options = _TARGET_OVERRIDE_OPTIONS.intersection(url.query)
    if overridden_target_options:
        raise ValueError(
            "TEST_DATABASE_URL cannot override its database or host through query options: "
            f"{sorted(overridden_target_options)}"
        )
    if schema_reset_confirmation != SCHEMA_RESET_CONFIRMATION:
        raise ValueError(
            f"Set {SCHEMA_RESET_CONFIRMATION_ENV}={SCHEMA_RESET_CONFIRMATION} only after "
            "verifying that the local database is disposable; its public schema is dropped"
        )
    return database_url
