"""Reporting REST endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.schemas.reports import TaskSummary
from app.services.report_service import get_task_summary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/task-summary", response_model=TaskSummary)
def task_summary_report(session: Session = Depends(get_session)) -> TaskSummary:
    """Return task counts by status and assignment."""
    return TaskSummary.model_validate(get_task_summary(session))
