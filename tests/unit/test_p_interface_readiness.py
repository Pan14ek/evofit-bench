"""Regression guard for the measured Method P readiness boundary."""

from __future__ import annotations

import pytest

from experiments.execution.tooling.errors import MethodNotReadyError
from experiments.execution.tooling.p_interface import P_ALGORITHM_STATUS, require_p_algorithm


def test_measured_method_p_interface_stays_not_ready_until_separate_review() -> None:
    assert P_ALGORITHM_STATUS == "NOT_READY"

    with pytest.raises(MethodNotReadyError, match="rules are not frozen"):
        require_p_algorithm()
