"""Notification persistence queries."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def add_notification(session: Session, user_id: uuid.UUID, kind: str, message: str) -> Notification:
    """Persist a notification in the caller's transaction."""
    notification = Notification(user_id=user_id, type=kind, message=message)
    session.add(notification)
    session.flush()
    return notification


def list_notifications(session: Session, user_id: uuid.UUID, limit: int) -> list[Notification]:
    """Return newest notifications for one user."""
    query = select(Notification).where(Notification.user_id == user_id)
    return list(
        session.scalars(
            query.order_by(Notification.created_at.desc(), Notification.id).limit(limit)
        )
    )
