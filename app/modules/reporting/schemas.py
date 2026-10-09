"""Task summary report schema."""

from pydantic import BaseModel


class TaskSummary(BaseModel):
    """Counts used in the basic task summary."""

    total_task_count: int
    count_by_status: dict[str, int]
    assigned_task_count: int
    unassigned_task_count: int
