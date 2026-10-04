"""End-to-end REST scenarios against a real PostgreSQL database."""

import time
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.experiment.fault_state import fault_state
from app.models.audit_event import AuditEvent


def create_user(client: TestClient, email: str) -> dict[str, Any]:
    """Create a user through the public REST API."""
    response = client.post("/api/v1/users", json={"name": "Researcher", "email": email})
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def audit_actions(client: TestClient) -> list[str]:
    """Read the audit ledger through the fixture's PostgreSQL session factory."""
    test_app = cast(Any, client.app)
    factory = cast(sessionmaker[Session], test_app.state.test_session_factory)
    with factory() as session:
        return list(session.scalars(select(AuditEvent.action).order_by(AuditEvent.created_at)))


def test_task_lifecycle_notification_audit_and_report(client: TestClient) -> None:
    """Exercise user, task, assignment, status, notification, audit and report flows."""
    creator = create_user(client, "creator@example.com")
    assignee = create_user(client, "assignee@example.com")
    task_response = client.post(
        "/api/v1/tasks",
        json={"title": "Baseline task", "description": "A0 flow", "creator_user_id": creator["id"]},
    )
    assert task_response.status_code == 201
    task = task_response.json()
    assert task["status"] == "TODO"
    assigned = client.post(
        f"/api/v1/tasks/{task['id']}/assign",
        json={"assignee_user_id": assignee["id"], "actor_user_id": creator["id"]},
    )
    assert assigned.status_code == 200
    moved = client.post(
        f"/api/v1/tasks/{task['id']}/status",
        json={"status": "IN_PROGRESS", "actor_user_id": creator["id"]},
    )
    assert moved.status_code == 200
    done = client.post(
        f"/api/v1/tasks/{task['id']}/status",
        json={"status": "DONE", "actor_user_id": creator["id"]},
    )
    assert done.status_code == 200
    assert (
        client.post(
            f"/api/v1/tasks/{task['id']}/status",
            json={"status": "TODO", "actor_user_id": creator["id"]},
        ).status_code
        == 409
    )
    listed = client.get("/api/v1/tasks", params={"status": "DONE", "assignee_id": assignee["id"]})
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert len(client.get("/api/v1/tasks").json()) == 1
    fetched = client.get(f"/api/v1/tasks/{task['id']}")
    assert fetched.status_code == 200
    notices = client.get("/api/v1/notifications", params={"user_id": assignee["id"]})
    assert notices.status_code == 200 and len(notices.json()) == 3
    summary = client.get("/api/v1/reports/task-summary").json()
    assert summary["total_task_count"] == 1
    assert summary["count_by_status"]["DONE"] == 1
    assert summary["assigned_task_count"] == 1
    assert client.get(f"/api/v1/users/{creator['id']}").status_code == 200
    actions = audit_actions(client)
    assert actions.count("created") == 3
    assert actions.count("assigned") == 1
    assert actions.count("status_changed") == 2


def test_not_found_validation_conflict_and_request_id(client: TestClient) -> None:
    """Verify stable error envelopes, duplicate email handling, and request IDs."""
    response = client.get(
        f"/api/v1/users/{UUID(int=0)}", headers={"X-Request-ID": "research-run-1"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.headers["X-Request-ID"] == "research-run-1"
    create_user(client, "duplicate@example.com")
    duplicate = client.post(
        "/api/v1/users", json={"name": "Again", "email": "duplicate@example.com"}
    )
    assert duplicate.status_code == 409
    invalid = client.post("/api/v1/users", json={"name": "   ", "email": "bad"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_health_metrics_and_experiment_mode_disabled(client: TestClient) -> None:
    """Expose operations endpoints and keep fault controls hidden by default."""
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "http_request_duration_seconds" in metrics.text
    assert client.get("/internal/experiment/faults").status_code == 404


def test_enabled_faults_delay_fail_deterministically_and_reset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Experiment controls apply task latency, consume one forced failure, and reset."""
    monkeypatch.setenv("EXPERIMENT_MODE", "true")
    get_settings.cache_clear()
    try:
        creator = create_user(client, "fault-creator@example.com")
        assignee = create_user(client, "fault-assignee@example.com")
        task = client.post(
            "/api/v1/tasks", json={"title": "Fault task", "creator_user_id": creator["id"]}
        ).json()
        assigned = client.post(
            f"/api/v1/tasks/{task['id']}/assign",
            json={"assignee_user_id": assignee["id"], "actor_user_id": creator["id"]},
        )
        assert assigned.status_code == 200
        before_failure = audit_actions(client)
        configured = client.put(
            "/internal/experiment/faults",
            json={"task_delay_ms": 60, "notification_delay_ms": 60, "fail_next_n_notifications": 1},
        )
        assert configured.status_code == 200
        assert client.get("/internal/experiment/faults").json() == configured.json()
        started = time.perf_counter()
        failed = client.post(
            f"/api/v1/tasks/{task['id']}/status",
            json={"status": "IN_PROGRESS", "actor_user_id": creator["id"]},
        )
        assert time.perf_counter() - started >= 0.1
        assert failed.status_code == 500
        assert client.get(f"/api/v1/tasks/{task['id']}").json()["status"] == "TODO"
        assert (
            len(client.get("/api/v1/notifications", params={"user_id": assignee["id"]}).json()) == 1
        )
        assert audit_actions(client) == before_failure
        reset = client.delete("/internal/experiment/faults")
        assert reset.status_code == 200
        assert reset.json() == {
            "notification_delay_ms": 0,
            "task_delay_ms": 0,
            "fail_next_n_notifications": 0,
        }
        succeeded = client.post(
            f"/api/v1/tasks/{task['id']}/status",
            json={"status": "IN_PROGRESS", "actor_user_id": creator["id"]},
        )
        assert succeeded.status_code == 200
    finally:
        fault_state.reset()
        monkeypatch.delenv("EXPERIMENT_MODE", raising=False)
        get_settings.cache_clear()
