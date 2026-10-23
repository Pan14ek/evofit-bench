"""EVAL-01 analysis-contract and fail-closed runner checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from experiments.pilots.run_eval01 import (
    EXPECTED_RETURN_CODES,
    analyze_case,
    confusion_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "experiments/pilots/EVAL01_MUTATION_CATALOG_V1.json"


def _catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _records(case: dict[str, Any], evaluator_id: str, *, repeats: int = 3) -> list[dict[str, Any]]:
    expected = case["expected_by_evaluator"][evaluator_id]
    evaluator = _catalog()["evaluators"][evaluator_id]
    source_sha = "1" * 40
    return [
        {
            "case_id": case["case_id"],
            "evaluator_id": evaluator_id,
            "repeat": repeat,
            "observed_compliance": expected["compliance"],
            "finding_codes": sorted(expected["finding_codes"]),
            "launch_error": None,
            "parse_error": None,
            "execution_status": "COMPLETED",
            "target_source_sha": source_sha,
            "expected_source_sha": source_sha,
            "source_commit_sha": source_sha,
            "source_sha_status": "MATCHED",
            "subject_source_dirty": False,
            "checkout_status_after": "clean",
            "evaluator_version": evaluator["version"],
            "evaluator_source_digest": evaluator["expected_source_artifact_digest"],
            "configuration_digest": evaluator["configuration_sha256"],
            "return_code": EXPECTED_RETURN_CODES[expected["compliance"]],
            "wall_time_ms": 10.0 + repeat,
        }
        for repeat in range(1, repeats + 1)
    ]


@pytest.mark.parametrize(
    ("evaluator_id", "expected_matrix"),
    [
        ("AC_PUBLIC_API", {"tp": 1, "fp": 0, "tn": 5, "fn": 0}),
        ("AC_MODULE_GRAPH", {"tp": 3, "fp": 0, "tn": 3, "fn": 0}),
    ],
)
def test_eval01_req01_confusion_metrics_count_source_cases_once(
    evaluator_id: str, expected_matrix: dict[str, int]
) -> None:
    """EVAL01-TEST-01: three timing repeats collapse to each labeled case once."""
    catalog = _catalog()
    rows = [
        analyze_case(case, evaluator_id, _records(case, evaluator_id), 3, catalog)
        for case in catalog["cases"]
        if case["metric_eligible"]
    ]

    metrics = confusion_metrics(rows)

    assert metrics["confusion_matrix"] == expected_matrix
    assert metrics["eligible_labeled_cases"] == 6
    assert metrics["evaluable_labeled_cases"] == 6
    assert metrics["unknown_or_invalid_labeled_cases"] == 0
    assert metrics["not_evaluable_catalog_cases"] == 0


def test_eval01_req02_source_identity_mismatch_is_not_a_true_positive() -> None:
    """EVAL01-TEST-02: source mismatch invalidates otherwise positive observations."""
    catalog = _catalog()
    case = next(
        item
        for item in catalog["cases"]
        if item["case_id"] == "forbidden_private_cross_module_import"
    )
    records = _records(case, "AC_PUBLIC_API")
    records[-1]["expected_source_sha"] = "2" * 40

    row = analyze_case(case, "AC_PUBLIC_API", records, 3, catalog)
    metrics = confusion_metrics([row])

    assert row["observed_compliance_case_level"] == "NON_COMPLIANT"
    assert row["valid_for_confusion_matrix"] is False
    assert "REPEATED_RUN_PROVENANCE_OR_EXECUTION_INCOMPLETE" in row["exclusion_reasons"]
    assert metrics["confusion_matrix"] == {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    assert metrics["unknown_or_invalid_labeled_cases"] == 1


def test_eval01_req03_unstable_and_not_evaluable_runs_stay_out_of_metrics() -> None:
    """EVAL01-TEST-03: unstable repeats and incomplete scope never become detections."""
    catalog = _catalog()
    positive = next(
        item
        for item in catalog["cases"]
        if item["case_id"] == "forbidden_private_cross_module_import"
    )
    unstable = _records(positive, "AC_PUBLIC_API")
    unstable[-1]["observed_compliance"] = "COMPLIANT"
    unstable[-1]["finding_codes"] = []
    unstable[-1]["return_code"] = EXPECTED_RETURN_CODES["COMPLIANT"]
    unstable_row = analyze_case(positive, "AC_PUBLIC_API", unstable, 3, catalog)

    missing_scope = next(
        item for item in catalog["cases"] if item["case_id"] == "missing_expected_capability"
    )
    not_evaluable_row = analyze_case(
        missing_scope,
        "AC_PUBLIC_API",
        _records(missing_scope, "AC_PUBLIC_API"),
        3,
        catalog,
    )
    metrics = confusion_metrics([unstable_row, not_evaluable_row])

    assert unstable_row["observed_compliance_case_level"] == "UNKNOWN"
    assert unstable_row["valid_for_confusion_matrix"] is False
    assert not_evaluable_row["observed_compliance_case_level"] == "NOT_EVALUABLE"
    assert not_evaluable_row["valid_for_confusion_matrix"] is False
    assert metrics["confusion_matrix"] == {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    assert metrics["unknown_or_invalid_labeled_cases"] == 1
    assert metrics["not_evaluable_catalog_cases"] == 1
