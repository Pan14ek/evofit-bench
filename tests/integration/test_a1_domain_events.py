"""PostgreSQL preparation checks for synchronous ΔA6 notification dispatch.

These tests exercise the dispatcher and Notification handler independently of
Task-service wiring. Final Task/Notification/Audit REST rollback tests remain
pending W0 authorization of the integrated ΔA6 source state.
"""

import os
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.events.contracts import TaskAssignedV1
from app.events.dispatcher import EventDispatcher
from app.modules.notifications.event_handlers import register_notification_handlers
from app.modules.notifications.model import Notification


@pytest.fixture(autouse=True)
def require_disposable_evofit_database() -> None:
    """Guard the shared integration fixture before it resets the public schema."""
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL must point to a disposable PostgreSQL database")
    database_name = make_url(database_url).database or ""
    if "evofit" not in database_name.lower():
        pytest.fail("TEST_DATABASE_URL database name must contain 'evofit' before schema reset")


def _create_user(client: TestClient) -> UUID:
    response = client.post(
        "/api/v1/users",
        json={"name": "Event recipient", "email": f"{uuid4()}@example.com"},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _session_factory(client: TestClient) -> sessionmaker[Session]:
    return cast(sessionmaker[Session], cast(Any, client.app).state.test_session_factory)


def _create_dispatcher() -> EventDispatcher:
    dispatcher = EventDispatcher()
    register_notification_handlers(dispatcher)
    return dispatcher


def test_assignment_event_delivers_synchronously_in_caller_transaction(
    client: TestClient,
) -> None:
    """The handler flushes its notification before caller-owned commit."""
    assignee_id = _create_user(client)
    event = TaskAssignedV1(task_id=uuid4(), assignee_id=assignee_id, actor_id=uuid4())
    factory = _session_factory(client)

    with factory() as session:
        _create_dispatcher().dispatch(session, event)
        pending = list(
            session.scalars(select(Notification).where(Notification.user_id == assignee_id))
        )
        assert [(row.type, row.message) for row in pending] == [
            ("TASK_ASSIGNED", f"Task {event.task_id} was assigned to you")
        ]
        session.commit()

    with factory() as session:
        persisted = list(
            session.scalars(select(Notification).where(Notification.user_id == assignee_id))
        )
    assert [(row.type, row.message) for row in persisted] == [
        ("TASK_ASSIGNED", f"Task {event.task_id} was assigned to you")
    ]


def test_injected_handler_failure_rolls_back_and_caller_can_recover(
    client: TestClient,
) -> None:
    """A real flushed notification rolls back, then the same session can recover."""
    assignee_id = _create_user(client)
    event = TaskAssignedV1(task_id=uuid4(), assignee_id=assignee_id, actor_id=uuid4())
    factory = _session_factory(client)
    dispatcher = _create_dispatcher()
    failure = RuntimeError("injected notification handler failure")

    def fail_after_notification(_session: Session, _event: TaskAssignedV1) -> None:
        raise failure

    dispatcher.register(TaskAssignedV1, fail_after_notification)

    with factory() as session:
        with pytest.raises(RuntimeError) as raised:
            dispatcher.dispatch(session, event)
        assert raised.value is failure
        flushed = list(
            session.scalars(select(Notification).where(Notification.user_id == assignee_id))
        )
        assert [(row.type, row.message) for row in flushed] == [
            ("TASK_ASSIGNED", f"Task {event.task_id} was assigned to you")
        ]

        session.rollback()
        assert (
            list(session.scalars(select(Notification).where(Notification.user_id == assignee_id)))
            == []
        )

        _create_dispatcher().dispatch(session, event)
        session.commit()

    with factory() as session:
        recovered = list(
            session.scalars(select(Notification).where(Notification.user_id == assignee_id))
        )
    assert [(row.type, row.message) for row in recovered] == [
        ("TASK_ASSIGNED", f"Task {event.task_id} was assigned to you")
    ]
