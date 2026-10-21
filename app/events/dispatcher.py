"""Synchronous in-process dispatch over an explicitly registered handler list."""

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy.orm import Session

from app.events.contracts import DomainEvent

logger = logging.getLogger(__name__)

EventT = TypeVar("EventT", bound=DomainEvent)
EventHandler = Callable[[Session, EventT], None]


class DuplicateHandlerRegistrationError(ValueError):
    """Raised when two different callables claim one stable handler identity."""


class MissingEventHandlerError(LookupError):
    """Raised when a required event is dispatched without a registered handler."""


@dataclass(frozen=True, slots=True)
class _HandlerRegistration:
    """Keep the declared identity, callable and typed invocation adapter together."""

    identity: str
    handler: Callable[..., None]
    invoke: Callable[[Session, DomainEvent], None]


class EventDispatcher:
    """Run explicitly registered event handlers synchronously in registration order.

    The caller owns the supplied SQLAlchemy session and its transaction. This
    dispatcher never commits or rolls back that transaction.
    """

    def __init__(self) -> None:
        """Create an empty dispatcher without external infrastructure."""
        self._handlers: dict[type[DomainEvent], list[_HandlerRegistration]] = {}

    def register(self, event_type: type[EventT], handler: EventHandler[EventT]) -> bool:
        """Register one synchronous handler, idempotently for an exact duplicate.

        Returns:
            `True` when the handler was added; `False` when the same registration
            already exists.

        Raises:
            TypeError: If the event type is invalid or the handler is asynchronous.
            DuplicateHandlerRegistrationError: If another callable claims the
                same module-qualified handler identity.
        """
        if not isinstance(event_type, type) or not issubclass(event_type, DomainEvent):
            raise TypeError("event_type must be a DomainEvent subclass")

        call_method = type(handler).__call__
        if inspect.iscoroutinefunction(handler) or inspect.iscoroutinefunction(call_method):
            raise TypeError("domain event handlers must be synchronous")

        identity = _handler_identity(handler)
        registrations = self._handlers.setdefault(event_type, [])
        for registration in registrations:
            if registration.identity != identity:
                continue
            if _same_handler(registration.handler, handler):
                return False
            raise DuplicateHandlerRegistrationError(
                f"Handler identity {identity!r} is already registered for {event_type.__name__}"
            )

        def invoke(session: Session, event: DomainEvent) -> None:
            if type(event) is not event_type:
                raise TypeError(
                    f"Handler for {event_type.__name__} received {type(event).__name__}"
                )
            handler(session, event)

        registrations.append(_HandlerRegistration(identity, handler, invoke))
        return True

    def dispatch(self, session: Session, event: DomainEvent) -> None:
        """Invoke all handlers inline using the caller's active SQLAlchemy session.

        Handler failures propagate unchanged. No commit, rollback, scheduling or
        retry is performed here.

        Raises:
            TypeError: If `event` is not a `DomainEvent` instance.
            MissingEventHandlerError: If no handler is registered for its type.
            Exception: Any exception raised by a handler, unchanged.
        """
        if not isinstance(event, DomainEvent):
            raise TypeError("event must be a DomainEvent instance")

        registrations = self._handlers.get(type(event), [])
        if not registrations:
            raise MissingEventHandlerError(f"No handler registered for {event.event_type}")

        logger.debug(
            "Dispatching in-process domain event",
            extra={"domain_event_type": event.event_type, "handler_count": len(registrations)},
        )
        for registration in tuple(registrations):
            logger.debug(
                "Invoking in-process domain event handler",
                extra={
                    "domain_event_type": event.event_type,
                    "domain_event_handler": registration.identity,
                },
            )
            registration.invoke(session, event)
        logger.debug(
            "Completed in-process domain event dispatch",
            extra={"domain_event_type": event.event_type, "handler_count": len(registrations)},
        )

    def handler_count(self, event_type: type[DomainEvent]) -> int:
        """Return the number of explicitly registered handlers for an event type."""
        return len(self._handlers.get(event_type, []))


def _handler_identity(handler: Callable[..., None]) -> str:
    """Return a stable source identity for functions and callable handler objects."""
    module = getattr(handler, "__module__", type(handler).__module__)
    qualified_name = getattr(handler, "__qualname__", type(handler).__qualname__)
    return f"{module}.{qualified_name}"


def _same_handler(left: Callable[..., None], right: Callable[..., None]) -> bool:
    """Compare function and bound-method registrations without user-defined equality."""
    if left is right:
        return True
    return (
        inspect.ismethod(left)
        and inspect.ismethod(right)
        and left.__self__ is right.__self__
        and left.__func__ is right.__func__
    )
