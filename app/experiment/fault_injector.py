"""Business-independent fault hooks used by services."""

from app.config import get_settings
from app.experiment.fault_state import fault_state


def apply_task_delay() -> None:
    """Apply task latency only when experiment mode is enabled."""
    if get_settings().experiment_mode:
        fault_state.task_delay()


def apply_notification_faults() -> None:
    """Delay or deterministically fail notification creation in experiment mode."""
    if not get_settings().experiment_mode:
        return
    fault_state.notification_delay()
    if fault_state.consume_notification_failure():
        raise RuntimeError("Experiment-forced notification failure")
