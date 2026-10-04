"""Unit checks for deterministic task lifecycle rules."""

import pytest

from app.models.task import TaskStatus
from app.services.task_service import ALLOWED_TRANSITIONS


@pytest.mark.parametrize(
    ("source", "target", "allowed"),
    [
        (TaskStatus.TODO, TaskStatus.IN_PROGRESS, True),
        (TaskStatus.TODO, TaskStatus.CANCELLED, True),
        (TaskStatus.IN_PROGRESS, TaskStatus.DONE, True),
        (TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED, True),
        (TaskStatus.DONE, TaskStatus.TODO, False),
        (TaskStatus.CANCELLED, TaskStatus.IN_PROGRESS, False),
    ],
)
def test_allowed_status_transition_matrix(
    source: TaskStatus, target: TaskStatus, allowed: bool
) -> None:
    """Only the specified forward transitions are supported."""
    assert (target in ALLOWED_TRANSITIONS[source]) is allowed
