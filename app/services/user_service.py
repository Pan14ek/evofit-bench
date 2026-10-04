"""User business operations."""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.observability.metrics import business_operation_failures_total, users_created_total
from app.repositories.user_repository import add_user, get_by_email, get_user
from app.services.audit_service import record_event
from app.services.errors import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


def create_user(session: Session, name: str, email: str) -> User:
    """Create a unique user and its audit event atomically."""
    normalized_email = email.strip().lower()
    if get_by_email(session, normalized_email):
        business_operation_failures_total.labels(operation="create_user").inc()
        raise ConflictError("Email is already registered")
    try:
        user = add_user(session, name=name.strip(), email=normalized_email)
        record_event(session, "user", user.id, "created", user.id, {"email": normalized_email})
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        business_operation_failures_total.labels(operation="create_user").inc()
        raise ConflictError("Email is already registered") from exc
    except Exception:
        session.rollback()
        raise
    users_created_total.inc()
    logger.info(
        "Business operation completed",
        extra={"operation": "create_user", "entity_id": user.id, "outcome": "success"},
    )
    return user


def retrieve_user(session: Session, user_id: uuid.UUID) -> User:
    """Return a user or raise a domain not-found error."""
    user = get_user(session, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user
