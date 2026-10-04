"""Task persistence queries."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus


def get_task(session: Session, task_id: uuid.UUID) -> Task | None:
    """Find a task by primary key."""
    return session.get(Task, task_id)


def list_tasks(
    session: Session,
    status: TaskStatus | None,
    assignee_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> list[Task]:
    """List tasks with optional status and assignee filters."""
    query = select(Task)
    if status is not None:
        query = query.where(Task.status == status)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    return list(
        session.scalars(query.order_by(Task.created_at, Task.id).limit(limit).offset(offset))
    )


def count_by_status(session: Session) -> dict[str, int]:
    """Return counts for all supported states, including zero-count states."""
    rows = session.execute(select(Task.status, func.count(Task.id)).group_by(Task.status)).all()
    counts = {status.value: 0 for status in TaskStatus}
    counts.update({status.value: count for status, count in rows})
    return counts


def task_assignment_counts(session: Session) -> tuple[int, int, int]:
    """Return total, assigned, and unassigned task counts."""
    total = session.scalar(select(func.count(Task.id)))
    assigned = session.scalar(select(func.count(Task.id)).where(Task.assignee_id.is_not(None)))
    total_count = int(total or 0)
    assigned_count = int(assigned or 0)
    return total_count, assigned_count, total_count - assigned_count
