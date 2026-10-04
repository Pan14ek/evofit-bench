"""Synchronous audit event creation."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.observability.tracing import span
from app.repositories.audit_repository import add_audit_event


def record_event(
    session: Session,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID | None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Write an audit event inside the caller's transaction."""
    with span("audit.create"):
        return add_audit_event(session, entity_type, entity_id, action, actor_id, details or {})
