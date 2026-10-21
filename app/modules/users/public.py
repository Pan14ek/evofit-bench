"""Stable Python API for interactions with the Users module."""

import uuid

from sqlalchemy.orm import Session

from app.modules.users.repository import get_user as _get_user

__all__ = ["user_exists"]


def user_exists(session: Session, user_id: uuid.UUID) -> bool:
    """Return whether a user exists without exposing the Users ORM model."""
    return _get_user(session, user_id) is not None
