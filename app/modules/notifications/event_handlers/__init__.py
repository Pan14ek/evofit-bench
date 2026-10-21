"""Notification-side handlers for versioned Task domain events."""

from sqlalchemy.orm import Session

from app.events.contracts import TaskAssignedV1, TaskStatusChangedV1
from app.events.dispatcher import EventDispatcher
from app.modules.notifications.service import create_notification


def handle_task_assigned(session: Session, event: TaskAssignedV1) -> None:
    """Create the existing assignment notification in the caller's transaction."""
    create_notification(
        session,
        event.assignee_id,
        "TASK_ASSIGNED",
        f"Task {event.task_id} was assigned to you",
    )


def handle_task_status_changed(session: Session, event: TaskStatusChangedV1) -> None:
    """Notify the assignee of a status change, if the task has an assignee."""
    if event.assignee_id is None:
        return
    create_notification(
        session,
        event.assignee_id,
        "TASK_STATUS_CHANGED",
        f"Task {event.task_id} changed to {event.new_status.value}",
    )


def register_notification_handlers(dispatcher: EventDispatcher) -> None:
    """Explicitly register Notification handlers in the declared v1 order."""
    dispatcher.register(TaskAssignedV1, handle_task_assigned)
    dispatcher.register(TaskStatusChangedV1, handle_task_status_changed)
