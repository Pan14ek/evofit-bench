"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_session

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    """Report process liveness."""
    return {"status": "live"}


@router.get("/health/ready")
def ready(session: Session = Depends(get_session)) -> dict[str, str]:
    """Check PostgreSQL readiness."""
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "not_ready", "message": "Database unavailable"},
        ) from exc
    return {"status": "ready"}
