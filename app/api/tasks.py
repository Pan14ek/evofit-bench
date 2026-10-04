"""Task REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.schemas.tasks import TaskAssign, TaskCreate, TaskRead, TaskStatus, TaskStatusChange
from app.services.task_service import (
    assign_task,
    change_task_status,
    create_task,
    get_tasks,
    retrieve_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
def post_task(payload: TaskCreate, session: Session = Depends(get_session)) -> TaskRead:
    """Create a task."""
    return TaskRead.model_validate(
        create_task(session, payload.title, payload.description, payload.creator_user_id)
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: uuid.UUID, session: Session = Depends(get_session)) -> TaskRead:
    """Get a task by ID."""
    return TaskRead.model_validate(retrieve_task(session, task_id))


@router.get("", response_model=list[TaskRead])
def get_task_list(
    status: TaskStatus | None = None,
    assignee_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[TaskRead]:
    """List tasks with optional filters."""
    return [
        TaskRead.model_validate(task)
        for task in get_tasks(session, status, assignee_id, limit, offset)
    ]


@router.post("/{task_id}/assign", response_model=TaskRead)
def post_assignment(
    task_id: uuid.UUID, payload: TaskAssign, session: Session = Depends(get_session)
) -> TaskRead:
    """Assign a task."""
    return TaskRead.model_validate(
        assign_task(session, task_id, payload.assignee_user_id, payload.actor_user_id)
    )


@router.post("/{task_id}/status", response_model=TaskRead)
def post_status(
    task_id: uuid.UUID, payload: TaskStatusChange, session: Session = Depends(get_session)
) -> TaskRead:
    """Change a task's status."""
    return TaskRead.model_validate(
        change_task_status(session, task_id, payload.status, payload.actor_user_id)
    )
