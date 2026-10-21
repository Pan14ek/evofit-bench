"""Synchronous in-process domain-event contracts and dispatch."""

from app.events.contracts import (
    DOMAIN_EVENT_CONTRACT_VERSION,
    DomainEvent,
    TaskAssignedV1,
    TaskStatusChangedV1,
    TaskStatusValue,
)
from app.events.dispatcher import (
    DuplicateHandlerRegistrationError,
    EventDispatcher,
    MissingEventHandlerError,
)

__all__ = [
    "DOMAIN_EVENT_CONTRACT_VERSION",
    "DomainEvent",
    "DuplicateHandlerRegistrationError",
    "EventDispatcher",
    "MissingEventHandlerError",
    "TaskAssignedV1",
    "TaskStatusChangedV1",
    "TaskStatusValue",
]
