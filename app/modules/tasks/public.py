"""Stable Python API for task queries shared with other modules."""

from typing import TypedDict, cast

from sqlalchemy.orm import Session

from app.modules.tasks.service import task_summary as _task_summary

__all__ = ["TaskSummary", "get_task_summary"]


class TaskSummary(TypedDict):
    """Stable, ORM-free result shape for the task summary query."""

    total_task_count: int
    count_by_status: dict[str, int]
    assigned_task_count: int
    unassigned_task_count: int


def get_task_summary(session: Session) -> TaskSummary:
    """Return aggregate task counts through the public Tasks contract."""
    return cast(TaskSummary, _task_summary(session))
