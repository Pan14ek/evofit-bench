"""SQLAlchemy engine construction."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import get_settings


def make_engine(database_url: str | None = None) -> Engine:
    """Create the application's synchronous database engine."""
    return create_engine(database_url or get_settings().database_url, pool_pre_ping=True)


engine = make_engine()
