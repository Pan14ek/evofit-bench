"""Unit checks for fault state reset and deterministic consumption."""

from app.experiment.fault_state import FaultConfig, FaultState


def test_fault_failure_count_is_consumed_one_at_a_time() -> None:
    """Forced notification failures have deterministic bounded consumption."""
    state = FaultState()
    state.set(FaultConfig(fail_next_n_notifications=2))
    assert state.consume_notification_failure()
    assert state.consume_notification_failure()
    assert not state.consume_notification_failure()


def test_reset_clears_every_fault() -> None:
    """Reset returns the experiment controls to their disabled state."""
    state = FaultState()
    state.set(
        FaultConfig(notification_delay_ms=300, task_delay_ms=100, fail_next_n_notifications=3)
    )
    assert state.reset() == FaultConfig()
