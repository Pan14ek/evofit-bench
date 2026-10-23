"""Post-experiment EVAL-02 evidence-status validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.pilots.validate_eval02_postrun import (
    classify_execution_status,
    validate_eval02_archive,
)


def _completed_record(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "execution_status": "COMPLETED",
        "launch_error": None,
        "parse_error": None,
        "source_sha_status": "MATCHED",
        "source_commit_sha": "a" * 40,
        "expected_source_sha": "a" * 40,
        "target_source_sha": "a" * 40,
        "subject_source_dirty": False,
        "checkout_status_after": "clean",
        "evaluator_id": "AC_PUBLIC_API",
        "evaluator_version": "1.0.0",
        "evaluator_source_digest": "evaluator-digest",
        "configuration_digest": "configuration-digest",
        "return_code": 1,
        "observed_compliance": "NON_COMPLIANT",
    }
    record.update(overrides)
    return record


def test_eval02_postrun_validation_distinguishes_complete_run_from_three_mismatches() -> None:
    """The archived run has complete calls and provenance despite a nonzero runner status."""
    archive = Path(__file__).resolve().parents[2] / "experiments/pilots/EVAL02_RAW_EVIDENCE_V1.zip"

    result = validate_eval02_archive(archive)

    assert result["evaluator_calls"] == {"planned": 60, "completed": 60}
    assert result["execution_status"]["runner_execution_stage_exit_code"] == 1
    assert result["execution_status"]["evaluator_invocation_failures"] == 0
    assert result["execution_status"]["source_provenance_failures"] == 0
    assert result["execution_status"]["diagnostic_expectation_mismatches"] == 3
    assert result["execution_status"]["diagnostic_mismatch_repeats"] == [1, 2, 3]
    assert result["execution_status"]["evidence_status"] == (
        "COMPLETE_WITH_DIAGNOSTIC_EXPECTATION_MISMATCHES"
    )
    assert result["analysis_status"] == "COMPLETE"
    assert result["raw_inventory_status"] == "PASS"
    assert result["archive_integrity"]["external_sha256"] == "PASS"
    assert result["archive_integrity"]["zip_crc"] == "PASS"
    assert result["archive_integrity"]["internal_sha256"] == "PASS"
    assert result["confusion_matrices"]["AC_PUBLIC_API"] == {
        "tp": 4,
        "fp": 0,
        "tn": 4,
        "fn": 0,
    }
    assert result["confusion_matrices"]["AC_MODULE_GRAPH"] == {
        "tp": 2,
        "fp": 0,
        "tn": 4,
        "fn": 0,
    }
    assert result["f1_by_evaluator"] == {"AC_PUBLIC_API": 1.0, "AC_MODULE_GRAPH": 1.0}


def test_eval02_failure_taxonomy_does_not_treat_expected_noncompliance_as_launch_failure() -> None:
    """Diagnostic mismatch, launch failure, and provenance failure remain distinct."""
    record = _completed_record()
    evaluator_catalog = {
        "AC_PUBLIC_API": {
            "version": "1.0.0",
            "expected_source_artifact_digest": "evaluator-digest",
            "configuration_sha256": "configuration-digest",
        }
    }
    mismatches = [
        {
            "case_id": "missing_required_public_function",
            "evaluator_id": "AC_PUBLIC_API",
            "repeat": repeat,
            "stage": "observation_validation",
            "detail": "FINDING_CLASS_MISMATCH",
        }
        for repeat in (1, 2, 3)
    ]

    status = classify_execution_status([record], mismatches, evaluator_catalog)

    assert status["runner_execution_stage_exit_code"] == 1
    assert status["evaluator_invocation_failures"] == 0
    assert status["source_provenance_failures"] == 0
    assert status["diagnostic_expectation_mismatches"] == 3
    assert status["evidence_status"] == "COMPLETE_WITH_DIAGNOSTIC_EXPECTATION_MISMATCHES"

    launch_status = classify_execution_status(
        [_completed_record(launch_error="could not launch")], [], evaluator_catalog
    )
    assert launch_status["evaluator_invocation_failures"] == 1
    assert launch_status["diagnostic_expectation_mismatches"] == 0

    provenance_status = classify_execution_status(
        [_completed_record(target_source_sha="b" * 40)], [], evaluator_catalog
    )
    assert provenance_status["evaluator_invocation_failures"] == 0
    assert provenance_status["source_provenance_failures"] == 1
