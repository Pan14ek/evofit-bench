"""Read-only warm-up workload using seeded records only."""

import os

from locust import HttpUser, between, task

from load.workload_profile import READ_ONLY_OPERATIONS, weights_from_environment
from scripts.seed_identity import seeded_uuid_value

SEED_ID = os.environ.get("SEED_ID", "a0-v1")
WEIGHTS = weights_from_environment(
    os.environ.get("A0_REQUEST_MIX_JSON"), required_operations=READ_ONLY_OPERATIONS
)


def seeded_task_id(index: int) -> str:
    """Return a seeded task identifier from the canonical seed namespace."""
    return str(seeded_uuid_value("task", index, SEED_ID))


class WarmupUser(HttpUser):
    """Issue only read operations to leave the seeded dataset unchanged."""

    wait_time = between(0.5, 1.5)

    @task(WEIGHTS["get_task"])
    def get_task(self) -> None:
        self.client.get(f"/api/v1/tasks/{seeded_task_id(1)}", name="GET /api/v1/tasks/{task_id}")

    @task(WEIGHTS["list_tasks"])
    def list_tasks(self) -> None:
        self.client.get("/api/v1/tasks?limit=50", name="GET /api/v1/tasks")

    @task(WEIGHTS["task_summary"])
    def task_summary(self) -> None:
        self.client.get("/api/v1/reports/task-summary", name="GET /api/v1/reports/task-summary")
