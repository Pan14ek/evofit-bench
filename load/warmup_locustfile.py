"""Read-only warm-up workload using seeded records only."""

import os

from locust import HttpUser, between, task

from scripts.seed_identity import seeded_uuid_value

SEED_ID = os.environ.get("SEED_ID", "a0-v1")


def seeded_task_id(index: int) -> str:
    """Return a seeded task identifier from the canonical seed namespace."""
    return str(seeded_uuid_value("task", index, SEED_ID))


class WarmupUser(HttpUser):
    """Issue only read operations to leave the seeded dataset unchanged."""

    wait_time = between(0.5, 1.5)

    @task(5)
    def get_task(self) -> None:
        self.client.get(f"/api/v1/tasks/{seeded_task_id(1)}", name="GET /api/v1/tasks/{task_id}")

    @task(3)
    def list_tasks(self) -> None:
        self.client.get("/api/v1/tasks?limit=50", name="GET /api/v1/tasks")

    @task(2)
    def task_summary(self) -> None:
        self.client.get("/api/v1/reports/task-summary", name="GET /api/v1/reports/task-summary")
