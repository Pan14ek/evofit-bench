"""Stable Python API for creating notifications in a caller-owned transaction."""

import uuid

from sqlalchemy.orm import Session

from app.modules.notifications.service import create_notification as _create_notification

__all__ = ["create_notification"]


def create_notification(session: Session, user_id: uuid.UUID, kind: str, message: str) -> None:
    """Create a notification using the supplied session without committing it."""
    _create_notification(session, user_id, kind, message)
