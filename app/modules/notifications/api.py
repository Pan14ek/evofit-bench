"""Notification REST endpoint."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.modules.notifications.schemas import NotificationRead
from app.modules.notifications.service import get_notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_user_notifications(
    user_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[NotificationRead]:
    """List the latest notifications for a user."""
    return [
        NotificationRead.model_validate(item) for item in get_notifications(session, user_id, limit)
    ]
