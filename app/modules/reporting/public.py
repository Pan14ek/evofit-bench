"""Stable Python API for Reporting queries."""

from typing import cast

from sqlalchemy.orm import Session

from app.modules.reporting.service import get_task_summary as _get_task_summary
from app.modules.tasks.public import TaskSummary

__all__ = ["get_task_summary"]


def get_task_summary(session: Session) -> TaskSummary:
    """Return the canonical Tasks summary shape through Reporting's API."""
    return cast(TaskSummary, _get_task_summary(session))
