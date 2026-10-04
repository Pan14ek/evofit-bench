"""Task request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.task import TaskStatus

__all__ = ["TaskAssign", "TaskCreate", "TaskRead", "TaskStatus", "TaskStatusChange"]


class TaskCreate(BaseModel):
    """Fields required to create a task."""

    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    creator_user_id: uuid.UUID

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        """Reject titles that contain only whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized


class TaskAssign(BaseModel):
    """Assignment command."""

    assignee_user_id: uuid.UUID
    actor_user_id: uuid.UUID


class TaskStatusChange(BaseModel):
    """Task status transition command."""

    status: TaskStatus
    actor_user_id: uuid.UUID


class TaskRead(BaseModel):
    """Public task representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    created_by: uuid.UUID
    assignee_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
