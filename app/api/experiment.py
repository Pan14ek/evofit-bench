"""Experiment-only fault controls."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.experiment.fault_state import FaultConfig, fault_state

router = APIRouter(prefix="/internal/experiment/faults", tags=["experiment"])


class FaultUpdate(BaseModel):
    """Validated fault configuration update."""

    notification_delay_ms: int = Field(default=0, ge=0, le=5000)
    task_delay_ms: int = Field(default=0, ge=0, le=5000)
    fail_next_n_notifications: int = Field(default=0, ge=0, le=10000)


def require_experiment_mode() -> None:
    """Hide fault-control API unless explicitly enabled."""
    if not get_settings().experiment_mode:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Not found"})


@router.get("")
def get_faults() -> dict[str, int]:
    """Read current fault configuration."""
    require_experiment_mode()
    config = fault_state.get()
    return {
        "notification_delay_ms": config.notification_delay_ms,
        "task_delay_ms": config.task_delay_ms,
        "fail_next_n_notifications": config.fail_next_n_notifications,
    }


@router.put("")
def set_faults(payload: FaultUpdate) -> dict[str, int]:
    """Replace current fault configuration."""
    require_experiment_mode()
    config = fault_state.set(FaultConfig(**payload.model_dump()))
    return {
        "notification_delay_ms": config.notification_delay_ms,
        "task_delay_ms": config.task_delay_ms,
        "fail_next_n_notifications": config.fail_next_n_notifications,
    }


@router.delete("")
def reset_faults() -> dict[str, int]:
    """Disable all configured faults."""
    require_experiment_mode()
    config = fault_state.reset()
    return {
        "notification_delay_ms": config.notification_delay_ms,
        "task_delay_ms": config.task_delay_ms,
        "fail_next_n_notifications": config.fail_next_n_notifications,
    }
