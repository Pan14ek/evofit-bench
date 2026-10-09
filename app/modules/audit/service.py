"""Synchronous audit event creation."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit.model import AuditEvent
from app.modules.audit.repository import add_audit_event
from app.observability.tracing import span


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
