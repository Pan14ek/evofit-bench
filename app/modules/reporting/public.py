"""Stable Python API for Reporting queries."""

from sqlalchemy.orm import Session

from app.modules.reporting.service import get_task_summary as _get_task_summary

__all__ = ["get_task_summary"]


def get_task_summary(session: Session) -> dict[str, int | dict[str, int]]:
    """Return the existing task-summary mapping through Reporting's API."""
    return _get_task_summary(session)
