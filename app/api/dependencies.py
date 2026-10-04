"""Shared HTTP dependencies."""

from app.db.session import get_session

__all__ = ["get_session"]
