"""Basic reporting operations."""

from sqlalchemy.orm import Session

from app.modules.tasks.public import TaskSummary
from app.modules.tasks.public import get_task_summary as _get_task_summary


def get_task_summary(session: Session) -> TaskSummary:
    """Return the task summary report."""
    return _get_task_summary(session)
