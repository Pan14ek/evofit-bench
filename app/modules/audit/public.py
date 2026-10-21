"""Stable Python API for recording audit events in a caller-owned transaction."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit.service import record_event as _record_event

__all__ = ["record_event"]


def record_event(
    session: Session,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID | None,
    details: dict[str, Any] | None = None,
) -> None:
    """Record an event using the supplied session without committing it."""
    _record_event(session, entity_type, entity_id, action, actor_id, details)
