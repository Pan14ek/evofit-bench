"""Versioned smoke and repeatable experiment-baseline Locust workload."""

import os
from itertools import count

from locust import HttpUser, between, task

from scripts.seed_identity import seeded_uuid_value

SEED_ID = os.environ.get("SEED_ID", "a0-v1")
_status_task_slots = count()


def seeded_uuid(kind: str, index: int) -> str:
    """Match the stable IDs emitted by scripts/seed_db.py."""
    return str(seeded_uuid_value(kind, index, SEED_ID))


class BaselineUser(HttpUser):
    """Fixed 25/20/15/15/15/10 request mix for both documented profiles."""

    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        """Initialize the user's sequential status-transition state."""
        self._status_sequence = 0
        self._status_task_index: int | None = None

    @task(25)
    def get_task(self) -> None:
        self.client.get(
            f"/api/v1/tasks/{seeded_uuid('task', 1)}", name="GET /api/v1/tasks/{task_id}"
        )

    @task(20)
    def list_tasks(self) -> None:
        self.client.get("/api/v1/tasks?limit=50", name="GET /api/v1/tasks")

    @task(15)
    def create_task(self) -> None:
        self.client.post(
            "/api/v1/tasks",
            name="POST /api/v1/tasks",
            json={"title": "Locust task", "creator_user_id": seeded_uuid("user", 1)},
        )

    @task(15)
    def assign_task(self) -> None:
        self.client.post(
            f"/api/v1/tasks/{seeded_uuid('task', 2)}/assign",
            name="POST /api/v1/tasks/{task_id}/assign",
            json={
                "assignee_user_id": seeded_uuid("user", 2),
                "actor_user_id": seeded_uuid("user", 1),
            },
        )

    @task(15)
    def change_status(self) -> None:
        sequence = self._status_sequence
        self._status_sequence += 1
        if sequence % 2 == 0:
            self._status_task_index = next(_status_task_slots) % 200 + 1
        task_index = self._status_task_index
        if task_index is None:
            return
        status = "IN_PROGRESS" if sequence % 2 == 0 else "DONE"
        self.client.post(
            f"/api/v1/tasks/{seeded_uuid('task', task_index)}/status",
            name="POST /api/v1/tasks/{task_id}/status",
            json={"status": status, "actor_user_id": seeded_uuid("user", 1)},
        )

    @task(10)
    def task_summary(self) -> None:
        self.client.get("/api/v1/reports/task-summary", name="GET /api/v1/reports/task-summary")
