"""Unit checks for explicit capability-module API contracts."""

import ast
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.modules import audit, notifications, reporting, tasks, users
from app.modules.audit import public as audit_public
from app.modules.notifications import public as notifications_public
from app.modules.reporting import public as reporting_public
from app.modules.tasks import public as tasks_public
from app.modules.users import public as users_public

ROOT = Path(__file__).resolve().parents[2]
MODULES_ROOT = ROOT / "app/modules"


def _foreign_module_imports(source_module: str) -> set[str]:
    """Return capability-module imports that cross a module boundary."""
    source_path = MODULES_ROOT / source_module / "service.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("app.modules."):
                imported_module = node.module.rsplit(".", 1)[0]
                target_module = imported_module.removeprefix("app.modules.").split(".", 1)[0]
                if target_module != source_module:
                    imports.add(node.module)
    return imports


def test_public_modules_declare_narrow_exports() -> None:
    """Each facade exports only the operation and DTO approved for ΔA2."""
    assert users.public.__all__ == ["user_exists"]
    assert audit.public.__all__ == ["record_event"]
    assert notifications.public.__all__ == ["create_notification"]
    assert tasks.public.__all__ == ["TaskSummary", "get_task_summary"]
    assert reporting.public.__all__ == ["get_task_summary"]
    assert set(tasks_public.TaskSummary.__annotations__) == {
        "total_task_count",
        "count_by_status",
        "assigned_task_count",
        "unassigned_task_count",
    }


def test_users_public_contract_returns_existence_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Users contract maps repository results to a boolean."""
    session = cast(Session, object())
    user_id = UUID(int=1)
    seen: list[tuple[Session, UUID]] = []

    def get_user_delegate(actual_session: Session, actual_id: UUID) -> Any:
        seen.append((actual_session, actual_id))
        return object()

    monkeypatch.setattr(
        users_public,
        "_get_user",
        get_user_delegate,
    )

    assert users_public.user_exists(session, user_id) is True
    assert seen == [(session, user_id)]

    monkeypatch.setattr(users_public, "_get_user", lambda actual_session, actual_id: None)
    assert users_public.user_exists(session, user_id) is False


def test_audit_and_notification_contracts_delegate_without_return_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Write facades pass the caller session through and hide persistence objects."""
    session = cast(Session, object())
    user_id = UUID(int=1)
    event_id = UUID(int=2)
    calls: list[tuple[Any, ...]] = []

    def record_event_delegate(*args: Any) -> Any:
        calls.append(args)
        return object()

    def create_notification_delegate(*args: Any) -> Any:
        calls.append(args)
        return object()

    monkeypatch.setattr(
        audit_public,
        "_record_event",
        record_event_delegate,
    )
    monkeypatch.setattr(
        notifications_public,
        "_create_notification",
        create_notification_delegate,
    )

    audit_result = cast(Any, audit_public.record_event)(
        session, "task", event_id, "changed", user_id
    )
    notification_result = cast(Any, notifications_public.create_notification)(
        session, user_id, "TASK_CHANGED", "changed"
    )
    assert audit_result is None
    assert notification_result is None
    assert calls == [
        (session, "task", event_id, "changed", user_id, None),
        (session, user_id, "TASK_CHANGED", "changed"),
    ]


def test_public_write_facades_propagate_service_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Facade calls preserve existing exception identity and failure semantics."""
    session = cast(Session, object())
    failure = RuntimeError("write failed")

    def fail(*args: Any) -> None:
        raise failure

    monkeypatch.setattr(audit_public, "_record_event", fail)
    with pytest.raises(RuntimeError) as audit_error:
        audit_public.record_event(session, "task", UUID(int=2), "changed", None)
    assert audit_error.value is failure

    monkeypatch.setattr(notifications_public, "_create_notification", fail)
    with pytest.raises(RuntimeError) as notification_error:
        notifications_public.create_notification(session, UUID(int=1), "TASK_CHANGED", "changed")
    assert notification_error.value is failure


def test_task_and_reporting_queries_keep_the_existing_summary_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both query facades return the four established report fields unchanged."""
    session = cast(Session, object())
    summary = {
        "total_task_count": 3,
        "count_by_status": {"TODO": 2, "DONE": 1},
        "assigned_task_count": 1,
        "unassigned_task_count": 2,
    }
    monkeypatch.setattr(tasks_public, "_task_summary", lambda actual_session: summary)
    monkeypatch.setattr(reporting_public, "_get_task_summary", lambda actual_session: summary)

    assert tasks_public.get_task_summary(session) == summary
    assert reporting_public.get_task_summary(session) == summary


def test_foreign_service_callers_import_public_contracts_only() -> None:
    """Reject foreign repository/service imports while preserving the ΔA4 edge."""
    assert _foreign_module_imports("tasks") == {
        "app.modules.audit.public",
        "app.modules.notifications.public",
        "app.modules.users.public",
    }
    assert _foreign_module_imports("users") == {"app.modules.audit.public"}

    # This representative private path is deliberately prohibited by the contract.
    forbidden_path = "app.modules.users.repository"
    assert forbidden_path not in _foreign_module_imports("tasks")

    reporting_source = (MODULES_ROOT / "reporting/service.py").read_text(encoding="utf-8")
    assert "from app.modules.tasks.service import task_summary" in reporting_source
