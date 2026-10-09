"""Audit-event persistence queries."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit.model import AuditEvent


def add_audit_event(
    session: Session,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID | None,
    details: dict[str, Any],
) -> AuditEvent:
    """Persist an audit event in the caller's transaction."""
    event = AuditEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        metadata_json=details,
    )
    session.add(event)
    session.flush()
    return event
