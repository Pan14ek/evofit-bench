"""PostgreSQL checks for public module contracts and transaction ownership."""

from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.experiment.fault_state import fault_state
from app.modules.audit.model import AuditEvent
from app.modules.audit.public import record_event
from app.modules.notifications.model import Notification
from app.modules.notifications.public import create_notification
from app.modules.reporting.public import get_task_summary as reporting_task_summary
from app.modules.tasks.public import get_task_summary as tasks_task_summary
from app.modules.users.public import user_exists


def _session_factory(client: TestClient) -> sessionmaker[Session]:
    """Return the disposable database session factory installed by the fixture."""
    test_app = cast(Any, client.app)
    return cast(sessionmaker[Session], test_app.state.test_session_factory)


def _create_user(client: TestClient, email: str) -> dict[str, Any]:
    """Create a user through its stable REST contract."""
    response = client.post("/api/v1/users", json={"name": "Public API", "email": email})
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_write_facades_use_the_callers_transaction(client: TestClient) -> None:
    """Audit and notification writes remain invisible until the caller commits."""
    user = _create_user(client, "public-transaction@example.com")
    user_id = UUID(user["id"])
    entity_id = uuid4()
    marker = f"public-contract-{uuid4()}"
    factory = _session_factory(client)

    with factory() as session:
        assert user_exists(session, user_id) is True
        record_event(session, "contract-test", entity_id, marker, user_id)
        create_notification(session, user_id, "CONTRACT_TEST", marker)

        assert session.in_transaction()
        assert session.scalar(select(AuditEvent.id).where(AuditEvent.action == marker)) is not None
        assert (
            session.scalar(select(Notification.id).where(Notification.message == marker))
            is not None
        )
        with factory() as observer:
            assert observer.scalar(select(AuditEvent.id).where(AuditEvent.action == marker)) is None
            assert (
                observer.scalar(select(Notification.id).where(Notification.message == marker))
                is None
            )

        session.commit()

    with factory() as observer:
        assert observer.scalar(select(AuditEvent.id).where(AuditEvent.action == marker)) is not None
        assert (
            observer.scalar(select(Notification.id).where(Notification.message == marker))
            is not None
        )

        rollback_marker = f"public-rollback-{uuid4()}"
        record_event(observer, "contract-test", entity_id, rollback_marker, user_id)
        create_notification(observer, user_id, "CONTRACT_TEST", rollback_marker)
        observer.rollback()

    with factory() as observer:
        assert (
            observer.scalar(select(AuditEvent.id).where(AuditEvent.action == rollback_marker))
            is None
        )
        assert (
            observer.scalar(select(Notification.id).where(Notification.message == rollback_marker))
            is None
        )


def test_task_and_reporting_public_summaries_keep_the_existing_shape(client: TestClient) -> None:
    """The new task query and Reporting facade expose the established fields."""
    creator = _create_user(client, "public-summary@example.com")
    task_response = client.post(
        "/api/v1/tasks",
        json={"title": "Public summary", "creator_user_id": creator["id"]},
    )
    assert task_response.status_code == 201
    expected = {
        "total_task_count": 1,
        "count_by_status": {"TODO": 1, "IN_PROGRESS": 0, "DONE": 0, "CANCELLED": 0},
        "assigned_task_count": 0,
        "unassigned_task_count": 1,
    }

    with _session_factory(client)() as session:
        assert tasks_task_summary(session) == expected
        assert reporting_task_summary(session) == expected


def test_assignment_failure_rolls_back_task_and_audit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed synchronous notification leaves assignment and audit unchanged."""
    monkeypatch.setenv("EXPERIMENT_MODE", "true")
    get_settings.cache_clear()
    fault_state.reset()
    try:
        creator = _create_user(client, "public-assign-creator@example.com")
        assignee = _create_user(client, "public-assign-assignee@example.com")
        task_response = client.post(
            "/api/v1/tasks",
            json={"title": "Assignment rollback", "creator_user_id": creator["id"]},
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]
        factory = _session_factory(client)
        with factory() as session:
            audit_before = list(session.scalars(select(AuditEvent.action)))

        configured = client.put(
            "/internal/experiment/faults", json={"fail_next_n_notifications": 1}
        )
        assert configured.status_code == 200
        failed = client.post(
            f"/api/v1/tasks/{task_id}/assign",
            json={"assignee_user_id": assignee["id"], "actor_user_id": creator["id"]},
        )
        assert failed.status_code == 500
        assert client.get(f"/api/v1/tasks/{task_id}").json()["assignee_id"] is None
        assert client.get("/api/v1/notifications", params={"user_id": assignee["id"]}).json() == []
        with factory() as session:
            assert list(session.scalars(select(AuditEvent.action))) == audit_before

        succeeded = client.post(
            f"/api/v1/tasks/{task_id}/assign",
            json={"assignee_user_id": assignee["id"], "actor_user_id": creator["id"]},
        )
        assert succeeded.status_code == 200
        assert succeeded.json()["assignee_id"] == assignee["id"]
        assert (
            len(client.get("/api/v1/notifications", params={"user_id": assignee["id"]}).json()) == 1
        )
        with factory() as session:
            assert list(session.scalars(select(AuditEvent.action))).count("assigned") == 1
    finally:
        fault_state.reset()
        monkeypatch.delenv("EXPERIMENT_MODE", raising=False)
        get_settings.cache_clear()
