"""Print a stable digest of the experiment database's logical contents."""

import hashlib
import json
from typing import Any

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User


def fingerprint() -> dict[str, int | str]:
    """Hash stable business fields across all A0 tables in primary-key order."""
    with SessionLocal() as session:
        users = list(
            session.execute(
                select(User.id, User.name, User.email, User.created_at).order_by(User.id)
            ).all()
        )
        tasks = list(
            session.execute(
                select(
                    Task.id,
                    Task.title,
                    Task.description,
                    Task.status,
                    Task.created_by,
                    Task.assignee_id,
                    Task.created_at,
                    Task.updated_at,
                ).order_by(Task.id)
            ).all()
        )
        notifications = int(session.scalar(select(func.count(Notification.id))) or 0)
        audit_events = int(session.scalar(select(func.count(AuditEvent.id))) or 0)
    logical_state: dict[str, Any] = {
        "users": [
            tuple(
                value.isoformat()
                if hasattr(value, "isoformat")
                else str(value)
                if value is not None
                else None
                for value in row
            )
            for row in users
        ],
        "tasks": [
            tuple(
                value.value
                if hasattr(value, "value")
                else value.isoformat()
                if hasattr(value, "isoformat")
                else str(value)
                if value is not None
                else None
                for value in row
            )
            for row in tasks
        ],
        "notifications_count": notifications,
        "audit_event_count": audit_events,
    }
    digest = hashlib.sha256(json.dumps(logical_state, sort_keys=True).encode()).hexdigest()
    return {
        "user_count": len(users),
        "task_count": len(tasks),
        "notification_count": notifications,
        "audit_event_count": audit_events,
        "sha256": digest,
    }


if __name__ == "__main__":
    print(json.dumps(fingerprint(), sort_keys=True))
