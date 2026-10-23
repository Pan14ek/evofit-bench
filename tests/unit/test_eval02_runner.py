"""EVAL-02 analysis contracts for labels, applicability, and repeated runs."""

from __future__ import annotations

from experiments.pilots.run_eval02 import analyze_case, confusion_metrics


def _catalog() -> dict[str, object]:
    return {
        "evaluators": {
            "AC_PUBLIC_API": {
                "version": "1.0.0",
                "expected_source_artifact_digest": "evaluator-digest",
                "configuration_sha256": "configuration-digest",
            }
        }
    }


def _records(
    case_id: str,
    observed: str,
    *,
    repeats: int = 3,
    source_sha: str = "a" * 40,
) -> list[dict[str, object]]:
    return [
        {
            "case_id": case_id,
            "evaluator_id": "AC_PUBLIC_API",
            "repeat": repeat,
            "observed_compliance": observed,
            "finding_codes": [],
            "launch_error": None,
            "parse_error": None,
            "execution_status": "COMPLETED",
            "target_source_sha": source_sha,
            "expected_source_sha": source_sha,
            "source_commit_sha": source_sha,
            "source_sha_status": "MATCHED",
            "subject_source_dirty": False,
            "checkout_status_after": "clean",
            "evaluator_version": "1.0.0",
            "evaluator_source_digest": "evaluator-digest",
            "configuration_digest": "configuration-digest",
            "return_code": 0 if observed == "COMPLIANT" else 1,
            "wall_time_ms": 10.0 + repeat,
        }
        for repeat in range(1, repeats + 1)
    ]


def test_eval02_stable_miss_uses_architecture_label_not_expected_output() -> None:
    """A source-bound miss remains a false negative, even when output differs from expectation."""
    case = {
        "case_id": "negative-case",
        "expected_by_evaluator": {
            "AC_PUBLIC_API": {
                "applicability": "APPLICABLE",
                "architectural_status": "NON_COMPLIANT",
                "metric_eligible": True,
                "compliance": "NON_COMPLIANT",
                "finding_codes": ["EXPECTED_FINDING"],
            }
        },
    }

    row = analyze_case(case, "AC_PUBLIC_API", _records("negative-case", "COMPLIANT"), 3, _catalog())
    metrics = confusion_metrics([row])

    assert row["architectural_status"] == "NON_COMPLIANT"
    assert row["observed_compliance_case_level"] == "COMPLIANT"
    assert row["preregistered_expected_outcome_matched"] is False
    assert row["valid_for_confusion_matrix"] is True
    assert metrics["confusion_matrix"] == {"tp": 0, "fp": 0, "tn": 0, "fn": 1}


def test_eval02_out_of_scope_architecture_defect_is_not_a_detection_metric() -> None:
    """A clear architecture label does not make an inapplicable evaluator measurable."""
    case = {
        "case_id": "dynamic-import-boundary",
        "exclusion_reason": "dynamic imports are outside the evaluator scope",
        "expected_by_evaluator": {
            "AC_PUBLIC_API": {
                "applicability": "OUT_OF_SCOPE_DYNAMIC_IMPORT",
                "architectural_status": "NON_COMPLIANT",
                "metric_eligible": False,
                "compliance": "COMPLIANT",
                "finding_codes": [],
            }
        },
    }

    row = analyze_case(
        case, "AC_PUBLIC_API", _records("dynamic-import-boundary", "COMPLIANT"), 3, _catalog()
    )
    metrics = confusion_metrics([row])

    assert row["architectural_status"] == "NON_COMPLIANT"
    assert row["evaluator_applicability"] == "OUT_OF_SCOPE_DYNAMIC_IMPORT"
    assert row["valid_for_confusion_matrix"] is False
    assert metrics["confusion_matrix"] == {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    assert metrics["excluded_from_matrix_cases"] == 1
    assert metrics["evaluator_applicability_counts"] == {"OUT_OF_SCOPE_DYNAMIC_IMPORT": 1}


def test_eval02_case_metrics_collapse_repeats_and_exclude_unstable_provenance() -> None:
    """Technical repeats contribute one case, and source mismatches remain unknown."""
    cases = [
        {
            "case_id": "positive",
            "expected_by_evaluator": {
                "AC_PUBLIC_API": {
                    "applicability": "APPLICABLE",
                    "architectural_status": "NON_COMPLIANT",
                    "metric_eligible": True,
                    "compliance": "NON_COMPLIANT",
                    "finding_codes": [],
                }
            },
        },
        {
            "case_id": "mismatch",
            "expected_by_evaluator": {
                "AC_PUBLIC_API": {
                    "applicability": "APPLICABLE",
                    "architectural_status": "COMPLIANT",
                    "metric_eligible": True,
                    "compliance": "COMPLIANT",
                    "finding_codes": [],
                }
            },
        },
    ]
    records = _records("positive", "NON_COMPLIANT") + _records(
        "mismatch", "COMPLIANT", source_sha="b" * 40
    )
    records[-1]["expected_source_sha"] = "c" * 40
    rows = [analyze_case(case, "AC_PUBLIC_API", records, 3, _catalog()) for case in cases]

    metrics = confusion_metrics(rows)

    assert metrics["eligible_binary_applicable_cases"] == 2
    assert metrics["evaluable_binary_applicable_cases"] == 1
    assert metrics["unknown_or_invalid_cases"] == 1
    assert metrics["confusion_matrix"] == {"tp": 1, "fp": 0, "tn": 0, "fn": 0}
