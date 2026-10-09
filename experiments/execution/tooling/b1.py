"""Readiness checks for the real human B1 manual-adaptation procedure."""

from __future__ import annotations

from typing import Any

B1_CHECKLIST_VERSION = "B1_MANUAL_ADAPTATION_V1"


def operator_readiness(operator_record: dict[str, Any] | None) -> dict[str, str | bool]:
    """Require a named independent operator and explicit exposure record."""
    required_fields = (
        "operator_id",
        "experience",
        "prior_exposure",
        "access_recorded",
        "time_budget_recorded",
        "independent_of_method_development",
        "blind_to_reference_answers",
    )
    missing = [
        field
        for field in required_fields
        if operator_record is None or operator_record.get(field) in (None, "", False)
    ]
    return {
        "status": "READY" if not missing else "NOT READY",
        "independent_human_operator_recorded": not missing,
        "reason": "operator protocol recorded"
        if not missing
        else f"missing operator fields: {', '.join(missing)}",
    }


__all__ = ["B1_CHECKLIST_VERSION", "operator_readiness"]
