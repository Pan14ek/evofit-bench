"""Basic reporting operations."""

from sqlalchemy.orm import Session

from app.modules.tasks.service import task_summary


def get_task_summary(session: Session) -> dict[str, int | dict[str, int]]:
    """Return the task summary report."""
    return task_summary(session)
