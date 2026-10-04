"""Synchronous in-application notification creation."""

import uuid

from sqlalchemy.orm import Session

from app.experiment.fault_injector import apply_notification_faults
from app.models.notification import Notification
from app.observability.metrics import notifications_created_total
from app.observability.tracing import span
from app.repositories.notification_repository import add_notification, list_notifications


def create_notification(
    session: Session, user_id: uuid.UUID, kind: str, message: str
) -> Notification:
    """Create one notification synchronously in the caller's transaction."""
    with span("notification.create"):
        apply_notification_faults()
        notification = add_notification(session, user_id, kind, message)
        notifications_created_total.inc()
        return notification


def get_notifications(session: Session, user_id: uuid.UUID, limit: int = 100) -> list[Notification]:
    """List a user's latest notifications."""
    return list_notifications(session, user_id, limit)
