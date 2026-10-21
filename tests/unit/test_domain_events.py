"""Contract and dispatcher tests for the ΔA6 in-process domain events."""

import asyncio
from threading import get_ident
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.events.contracts import (
    DOMAIN_EVENT_CONTRACT_VERSION,
    TaskAssignedV1,
    TaskStatusChangedV1,
    TaskStatusValue,
)
from app.events.dispatcher import (
    DuplicateHandlerRegistrationError,
    EventDispatcher,
    MissingEventHandlerError,
)
from app.modules import notifications as notifications_module
from app.modules.notifications import event_handlers
from app.modules.tasks.model import TaskStatus

TASK_ID = UUID("00000000-0000-0000-0000-000000000001")
ASSIGNEE_ID = UUID("00000000-0000-0000-0000-000000000002")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000003")


def test_event_contract_is_versioned_typed_validated_and_immutable() -> None:
    event = TaskStatusChangedV1(
        task_id=TASK_ID,
        actor_id=ACTOR_ID,
        previous_status="TODO",
        new_status="IN_PROGRESS",
    )

    assert DOMAIN_EVENT_CONTRACT_VERSION == "1.0.0"
    assert event.event_type == "task.status_changed.v1"
    assert event.previous_status is TaskStatusValue.TODO
    assert event.new_status is TaskStatusValue.IN_PROGRESS
    assert event.assignee_id is None
    with pytest.raises(ValidationError):
        event.new_status = TaskStatusValue.DONE  # type: ignore[misc]
    with pytest.raises(ValidationError):
        TaskAssignedV1.model_validate(
            {
                "task_id": TASK_ID,
                "assignee_id": ASSIGNEE_ID,
                "actor_id": ACTOR_ID,
                "unexpected": "not part of v1",
            }
        )
    with pytest.raises(ValidationError):
        TaskStatusChangedV1(
            task_id=TASK_ID,
            actor_id=ACTOR_ID,
            previous_status="UNKNOWN",
            new_status="DONE",
        )


def test_event_task_status_values_match_canonical_task_status_enum() -> None:
    """Keep the event-owned status mirror exactly aligned with TaskStatus."""
    assert {name: member.value for name, member in TaskStatusValue.__members__.items()} == {
        name: member.value for name, member in TaskStatus.__members__.items()
    }


def test_dispatch_passes_exact_session_and_event_inline() -> None:
    dispatcher = EventDispatcher()
    session = MagicMock(spec=Session)
    event = TaskAssignedV1(task_id=TASK_ID, assignee_id=ASSIGNEE_ID, actor_id=ACTOR_ID)
    caller_thread = get_ident()
    observed: list[tuple[Session, TaskAssignedV1, bool]] = []

    def handler(received_session: Session, received_event: TaskAssignedV1) -> None:
        observed.append((received_session, received_event, get_ident() == caller_thread))

    assert dispatcher.register(TaskAssignedV1, handler) is True
    dispatcher.dispatch(session, event)

    assert observed == [(session, event, True)]
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_handlers_run_synchronously_in_registration_order() -> None:
    dispatcher = EventDispatcher()
    session = MagicMock(spec=Session)
    event = TaskAssignedV1(task_id=TASK_ID, assignee_id=ASSIGNEE_ID, actor_id=ACTOR_ID)
    calls: list[str] = []

    def first(_session: Session, _event: TaskAssignedV1) -> None:
        calls.append("first")

    def second(_session: Session, _event: TaskAssignedV1) -> None:
        calls.append("second")

    dispatcher.register(TaskAssignedV1, first)
    dispatcher.register(TaskAssignedV1, second)
    dispatcher.dispatch(session, event)

    assert calls == ["first", "second"]


def test_handler_failure_propagates_unchanged_and_stops_dispatch() -> None:
    dispatcher = EventDispatcher()
    session = MagicMock(spec=Session)
    event = TaskAssignedV1(task_id=TASK_ID, assignee_id=ASSIGNEE_ID, actor_id=ACTOR_ID)
    failure = RuntimeError("handler failed")
    later_handler_called = False

    def failing(_session: Session, _event: TaskAssignedV1) -> None:
        raise failure

    def later(_session: Session, _event: TaskAssignedV1) -> None:
        nonlocal later_handler_called
        later_handler_called = True

    dispatcher.register(TaskAssignedV1, failing)
    dispatcher.register(TaskAssignedV1, later)
    with pytest.raises(RuntimeError) as raised:
        dispatcher.dispatch(session, event)

    assert raised.value is failure
    assert later_handler_called is False
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_registration_is_idempotent_and_rejects_identity_collision() -> None:
    dispatcher = EventDispatcher()

    def handler(_session: Session, _event: TaskAssignedV1) -> None:
        return None

    def conflicting_handler(_session: Session, _event: TaskAssignedV1) -> None:
        return None

    conflicting_handler.__module__ = handler.__module__
    conflicting_handler.__qualname__ = handler.__qualname__

    assert dispatcher.register(TaskAssignedV1, handler) is True
    assert dispatcher.register(TaskAssignedV1, handler) is False
    assert dispatcher.handler_count(TaskAssignedV1) == 1
    with pytest.raises(DuplicateHandlerRegistrationError):
        dispatcher.register(TaskAssignedV1, conflicting_handler)
    assert dispatcher.handler_count(TaskAssignedV1) == 1


def test_dispatch_without_a_required_handler_fails_explicitly() -> None:
    dispatcher = EventDispatcher()
    event = TaskAssignedV1(task_id=TASK_ID, assignee_id=ASSIGNEE_ID, actor_id=ACTOR_ID)

    with pytest.raises(MissingEventHandlerError, match="task.assigned.v1"):
        dispatcher.dispatch(MagicMock(spec=Session), event)


def test_coroutine_handlers_are_rejected() -> None:
    dispatcher = EventDispatcher()

    async def handler(_session: Session, _event: TaskAssignedV1) -> None:
        await asyncio.sleep(0)

    with pytest.raises(TypeError, match="must be synchronous"):
        dispatcher.register(TaskAssignedV1, handler)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("event", "expected_kind", "expected_message"),
    [
        (
            TaskAssignedV1(task_id=TASK_ID, assignee_id=ASSIGNEE_ID, actor_id=ACTOR_ID),
            "TASK_ASSIGNED",
            f"Task {TASK_ID} was assigned to you",
        ),
        (
            TaskStatusChangedV1(
                task_id=TASK_ID,
                actor_id=ACTOR_ID,
                previous_status=TaskStatusValue.TODO,
                new_status=TaskStatusValue.IN_PROGRESS,
                assignee_id=ASSIGNEE_ID,
            ),
            "TASK_STATUS_CHANGED",
            f"Task {TASK_ID} changed to IN_PROGRESS",
        ),
    ],
)
def test_notification_handlers_preserve_existing_notification_contract(
    monkeypatch: pytest.MonkeyPatch,
    event: TaskAssignedV1 | TaskStatusChangedV1,
    expected_kind: str,
    expected_message: str,
) -> None:
    create_notification = MagicMock()
    monkeypatch.setattr(
        notifications_module,
        "public",
        SimpleNamespace(create_notification=create_notification),
        raising=False,
    )
    session = MagicMock(spec=Session)

    if isinstance(event, TaskAssignedV1):
        event_handlers.handle_task_assigned(session, event)
    else:
        event_handlers.handle_task_status_changed(session, event)

    create_notification.assert_called_once_with(
        session, ASSIGNEE_ID, expected_kind, expected_message
    )


def test_unassigned_status_change_does_not_create_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_notification = MagicMock()
    monkeypatch.setattr(
        notifications_module,
        "public",
        SimpleNamespace(create_notification=create_notification),
        raising=False,
    )
    event = TaskStatusChangedV1(
        task_id=TASK_ID,
        actor_id=ACTOR_ID,
        previous_status=TaskStatusValue.TODO,
        new_status=TaskStatusValue.IN_PROGRESS,
    )

    event_handlers.handle_task_status_changed(MagicMock(spec=Session), event)

    create_notification.assert_not_called()


def test_exact_duplicate_registration_does_not_duplicate_delivery() -> None:
    dispatcher = EventDispatcher()
    session = MagicMock(spec=Session)
    event = TaskAssignedV1(task_id=TASK_ID, assignee_id=ASSIGNEE_ID, actor_id=ACTOR_ID)

    handler_call = MagicMock()
    dispatcher.register(TaskAssignedV1, handler_call)
    assert dispatcher.register(TaskAssignedV1, handler_call) is False
    dispatcher.dispatch(session, event)
    handler_call.assert_called_once_with(session, event)


def test_dispatch_requires_a_domain_event_instance() -> None:
    dispatcher = EventDispatcher()
    with pytest.raises(TypeError, match="DomainEvent instance"):
        dispatcher.dispatch(MagicMock(spec=Session), object())  # type: ignore[arg-type]


def test_notification_bootstrap_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatcher = EventDispatcher()
    session = MagicMock(spec=Session)
    create_notification = MagicMock()
    monkeypatch.setattr(
        notifications_module,
        "public",
        SimpleNamespace(create_notification=create_notification),
        raising=False,
    )
    event = TaskAssignedV1(task_id=TASK_ID, assignee_id=ASSIGNEE_ID, actor_id=ACTOR_ID)

    event_handlers.register_notification_handlers(dispatcher)
    event_handlers.register_notification_handlers(dispatcher)
    dispatcher.dispatch(session, event)

    assert dispatcher.handler_count(TaskAssignedV1) == 1
    assert dispatcher.handler_count(TaskStatusChangedV1) == 1
    create_notification.assert_called_once_with(
        session, ASSIGNEE_ID, "TASK_ASSIGNED", f"Task {TASK_ID} was assigned to you"
    )
