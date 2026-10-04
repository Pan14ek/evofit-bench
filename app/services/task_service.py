"""Task business operations and lifecycle rules."""

import logging
import uuid

from sqlalchemy.orm import Session

from app.experiment.fault_injector import apply_task_delay
from app.models.task import Task, TaskStatus
from app.observability.metrics import (
    notifications_created_total,
    task_status_changes_total,
    tasks_assigned_total,
    tasks_created_total,
)
from app.observability.tracing import span
from app.repositories.task_repository import (
    count_by_status,
    get_task,
    list_tasks,
    task_assignment_counts,
)
from app.repositories.user_repository import get_user
from app.services.audit_service import record_event
from app.services.errors import ConflictError, NotFoundError
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)
ALLOWED_TRANSITIONS = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.DONE: set(),
    TaskStatus.CANCELLED: set(),
}


def create_task(
    session: Session, title: str, description: str | None, creator_id: uuid.UUID
) -> Task:
    """Create a TODO task after validating its creator."""
    apply_task_delay()
    if get_user(session, creator_id) is None:
        raise NotFoundError("Creator user not found")
    with span("task.create"):
        task = Task(title=title.strip(), description=description, created_by=creator_id)
        try:
            session.add(task)
            session.flush()
            record_event(
                session, "task", task.id, "created", creator_id, {"status": TaskStatus.TODO.value}
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    tasks_created_total.inc()
    logger.info(
        "Business operation completed",
        extra={"operation": "create_task", "entity_id": task.id, "outcome": "success"},
    )
    return task


def retrieve_task(session: Session, task_id: uuid.UUID) -> Task:
    """Return a task or raise a not-found error."""
    task = get_task(session, task_id)
    if task is None:
        raise NotFoundError("Task not found")
    return task


def get_tasks(
    session: Session,
    status: TaskStatus | None,
    assignee_id: uuid.UUID | None,
    limit: int = 100,
    offset: int = 0,
) -> list[Task]:
    """List tasks with stable pagination and optional filters."""
    return list_tasks(session, status, assignee_id, limit, offset)


def assign_task(
    session: Session, task_id: uuid.UUID, assignee_id: uuid.UUID, actor_id: uuid.UUID
) -> Task:
    """Assign a task and atomically create notification and audit records."""
    task = retrieve_task(session, task_id)
    if get_user(session, assignee_id) is None:
        raise NotFoundError("Assignee user not found")
    if get_user(session, actor_id) is None:
        raise NotFoundError("Actor user not found")
    with span("task.assign"):
        try:
            task.assignee_id = assignee_id
            record_event(
                session, "task", task.id, "assigned", actor_id, {"assignee_id": str(assignee_id)}
            )
            create_notification(
                session, assignee_id, "TASK_ASSIGNED", f"Task {task.id} was assigned to you"
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    tasks_assigned_total.inc()
    notifications_created_total.inc()
    logger.info(
        "Business operation completed",
        extra={"operation": "assign_task", "entity_id": task.id, "outcome": "success"},
    )
    return task


def change_task_status(
    session: Session, task_id: uuid.UUID, status: TaskStatus, actor_id: uuid.UUID
) -> Task:
    """Apply an allowed lifecycle transition and synchronous side effects."""
    apply_task_delay()
    task = retrieve_task(session, task_id)
    if get_user(session, actor_id) is None:
        raise NotFoundError("Actor user not found")
    if status not in ALLOWED_TRANSITIONS[task.status]:
        raise ConflictError(f"Transition from {task.status.value} to {status.value} is not allowed")
    with span("task.change_status"):
        try:
            previous_status = task.status
            task.status = status
            record_event(
                session,
                "task",
                task.id,
                "status_changed",
                actor_id,
                {"from": previous_status.value, "to": status.value},
            )
            if task.assignee_id is not None:
                create_notification(
                    session,
                    task.assignee_id,
                    "TASK_STATUS_CHANGED",
                    f"Task {task.id} changed to {status.value}",
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
    if task.assignee_id is not None:
        notifications_created_total.inc()
    task_status_changes_total.inc()
    return task


def task_summary(session: Session) -> dict[str, int | dict[str, int]]:
    """Return basic aggregate counts across tasks."""
    total, assigned, unassigned = task_assignment_counts(session)
    return {
        "total_task_count": total,
        "count_by_status": count_by_status(session),
        "assigned_task_count": assigned,
        "unassigned_task_count": unassigned,
    }
