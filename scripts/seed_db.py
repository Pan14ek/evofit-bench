"""Load the deterministic A0 seed dataset."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete

from app.config import get_settings
from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.notification import Notification
from app.models.task import Task, TaskStatus
from app.models.user import User
from scripts.seed_identity import seeded_uuid_value

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def seeded_uuid(kind: str, index: int) -> UUID:
    """Generate a stable UUID for a seed entity."""
    return seeded_uuid_value(kind, index, get_settings().seed_id)


def seed() -> None:
    """Replace experiment rows with the fixed 100-user/500-task dataset."""
    with SessionLocal() as session:
        session.execute(delete(AuditEvent))
        session.execute(delete(Notification))
        session.execute(delete(Task))
        session.execute(delete(User))
        users = [
            User(
                id=seeded_uuid("user", i),
                name=f"Research User {i:03d}",
                email=f"user{i:03d}@example.test",
                created_at=BASE_TIME + timedelta(seconds=i),
            )
            for i in range(1, 101)
        ]
        session.add_all(users)
        session.flush()
        statuses = (
            [TaskStatus.TODO] * 200
            + [TaskStatus.IN_PROGRESS] * 150
            + [TaskStatus.DONE] * 100
            + [TaskStatus.CANCELLED] * 50
        )
        tasks = []
        for index, status in enumerate(statuses, start=1):
            assignee = seeded_uuid("user", ((index * 7) % 100) + 1) if index % 4 != 0 else None
            tasks.append(
                Task(
                    id=seeded_uuid("task", index),
                    title=f"Seed task {index:03d}",
                    description=f"Deterministic A0 seed item {index}",
                    status=status,
                    created_by=seeded_uuid("user", ((index - 1) % 100) + 1),
                    assignee_id=assignee,
                    created_at=BASE_TIME + timedelta(seconds=1000 + index),
                    updated_at=BASE_TIME + timedelta(seconds=1000 + index),
                )
            )
        session.add_all(tasks)
        session.commit()
    print(f"Seeded 100 users and 500 tasks ({get_settings().seed_id}).")


if __name__ == "__main__":
    seed()
