"""Version 1 of the immutable in-process Task domain-event contract."""

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DOMAIN_EVENT_CONTRACT_VERSION = "1.0.0"


class TaskStatusValue(StrEnum):
    """Task status values carried by events without importing Task internals."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class DomainEvent(BaseModel):
    """Base class for immutable, validated, versioned domain-event payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: str


class TaskAssignedV1(DomainEvent):
    """Task assignment fact consumed by in-process Notification handlers."""

    event_type: Literal["task.assigned.v1"] = "task.assigned.v1"
    task_id: UUID
    assignee_id: UUID
    actor_id: UUID


class TaskStatusChangedV1(DomainEvent):
    """Task status-change fact, including the assignee snapshot at the change."""

    event_type: Literal["task.status_changed.v1"] = "task.status_changed.v1"
    task_id: UUID
    actor_id: UUID
    previous_status: TaskStatusValue
    new_status: TaskStatusValue
    assignee_id: UUID | None = None
