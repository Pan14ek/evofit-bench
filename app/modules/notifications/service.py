"""Synchronous in-application notification creation."""

import uuid

from sqlalchemy.orm import Session

from app.experiment.fault_injector import apply_notification_faults
from app.modules.notifications.model import Notification
from app.modules.notifications.repository import add_notification, list_notifications
from app.observability.tracing import span


def create_notification(
    session: Session, user_id: uuid.UUID, kind: str, message: str
) -> Notification:
    """Create one notification synchronously in the caller's transaction."""
    with span("notification.create"):
        apply_notification_faults()
        notification = add_notification(session, user_id, kind, message)
        return notification


def get_notifications(session: Session, user_id: uuid.UUID, limit: int = 100) -> list[Notification]:
    """List a user's latest notifications."""
    return list_notifications(session, user_id, limit)
