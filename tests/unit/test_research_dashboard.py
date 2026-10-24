"""Source-bound and synthetic checks for the read-only Method P dashboard."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from research_dashboard.charts import (
    confusion_matrix_figure,
    coverage_transition_figure,
    duration_distribution_figure,
)
from research_dashboard.data import (
    DashboardDataError,
    ExperimentDataset,
    IntegritySummary,
    default_results_path,
    load_dataset,
    validate_results_payload,
)
from research_dashboard.figures import export_publication_figures
from research_dashboard.metrics import (
    confusion_matrix,
    duration_rows,
    duration_summary,
    mismatch_rows,
    repetition_rows,
    report_consistency_issues,
    scenario_rows,
    summary_metrics,
)


@pytest.fixture(scope="module")
def dataset() -> ExperimentDataset:
    return load_dataset(default_results_path())


def test_corrected_results_schema_and_source_report_are_valid(dataset: ExperimentDataset) -> None:
    payload = json.loads(dataset.results_path.read_text(encoding="utf-8"))
    assert validate_results_payload(payload) == ()
    assert report_consistency_issues(dataset) == []
    assert dataset.integrity.expected_files > 0
    assert dataset.integrity.verified_files == dataset.integrity.expected_files
    assert dataset.integrity.missing_files == 0


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload.update(schema_version=99),
            "Results schema v2 validation failed",
        ),
        (
            lambda payload: payload.pop("experiment_id"),
            "Results schema v2 validation failed",
        ),
        (
            lambda payload: payload.update(scenario_count=7),
            "scenario_count does not match",
        ),
        (
            lambda payload: payload["summary_counts"].update(correct=20),
            "summary_counts.correct",
        ),
        (
            lambda payload: payload["technical_repetition_results"][0][
                "pre_adaptation_coverage"
            ].update(status="PARTIAL"),
            "Results schema v2 validation failed",
        ),
        (
            lambda payload: payload["technical_repetition_results"][0].update(
                duration_ns=float("nan")
            ),
            "Non-finite numeric value",
        ),
    ],
)
def test_invalid_payloads_fail_clearly(
    dataset: ExperimentDataset,
    mutation: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    payload = copy.deepcopy(dataset.results)
    mutation(payload)
    with pytest.raises(DashboardDataError, match=message):
        validate_results_payload(payload)


def test_required_manifest_identity_fields_fail_closed(dataset: ExperimentDataset) -> None:
    payload = copy.deepcopy(dataset.results)
    payload.pop("reference_sha256")
    with pytest.raises(DashboardDataError, match="reference_sha256"):
        validate_results_payload(payload)


def test_scenario_and_repetition_units_remain_separate(dataset: ExperimentDataset) -> None:
    rows = scenario_rows(dataset)
    repetitions = repetition_rows(dataset)
    assert len(rows) == 8
    assert len(repetitions) == 24
    assert [row["scenario_id"] for row in rows] == [
        "A1",
        "A2",
        "B1",
        "B2",
        "C1",
        "C2",
        "D1",
        "D2",
    ]
    assert all(row["repetition_count"] == 3 for row in rows)
    assert sum(row["repetition_count"] for row in rows) == len(repetitions)
    assert summary_metrics(dataset)["scenario_count"] == 8
    assert summary_metrics(dataset)["technical_repetition_count"] == 24


def test_coverage_transitions_are_categorical_and_candidate_only(
    dataset: ExperimentDataset,
) -> None:
    rows = {row["scenario_id"]: row for row in scenario_rows(dataset)}
    expected_transitions = {
        "A1": ("COMPLETE", "COMPLETE"),
        "A2": ("COMPLETE", "COMPLETE"),
        "B1": ("INCOMPLETE", "COMPLETE"),
        "B2": ("INCOMPLETE", "COMPLETE"),
        "C1": ("INCOMPLETE", "COMPLETE"),
        "C2": ("INCOMPLETE", "COMPLETE"),
        "D1": ("UNKNOWN", "UNKNOWN"),
        "D2": ("INCOMPLETE", "INCOMPLETE"),
    }
    assert {
        scenario_id: (row["current_coverage"], row["candidate_coverage"])
        for scenario_id, row in rows.items()
    } == expected_transitions
    emphasized = {
        row["scenario_id"] for row in rows.values() if row["candidate_transition_emphasized"]
    }
    assert emphasized == {"B1", "B2", "C1", "C2"}
    assert all(
        row["actual_post_adaptation_coverage"]["status"] == "NOT_MEASURED"
        for row in repetitions_from(dataset)
    )
    assert summary_metrics(dataset)["actual_post_adaptation_coverage_distribution"] == {
        "NOT_MEASURED": 24
    }
    figure = coverage_transition_figure(list(rows.values()))
    assert len(figure.data) == 1
    assert len(figure.layout.shapes) == 4


def repetitions_from(dataset: ExperimentDataset) -> list[dict[str, Any]]:
    return list(dataset.results["technical_repetition_results"])


def test_agreement_metrics_preserve_d2_operation_and_governance_difference(
    dataset: ExperimentDataset,
) -> None:
    metrics = summary_metrics(dataset)
    assert metrics["operation_match_count"] == 24
    assert metrics["operation_evaluable_count"] == 24
    assert metrics["combined_correct_count"] == 21
    assert metrics["combined_incorrect_count"] == 3
    assert metrics["governance_distribution"] == {
        "ACCEPT": 18,
        "HOLD": 3,
        "REJECT": 3,
    }

    operation_categories, operation = confusion_matrix(dataset, "operation")
    hold_index = operation_categories.index("hold")
    assert operation[hold_index][hold_index] == 6

    governance_categories, governance = confusion_matrix(dataset, "governance")
    expected_hold = governance_categories.index("HOLD")
    observed_reject = governance_categories.index("REJECT")
    assert governance[expected_hold][observed_reject] == 3

    d2 = next(row for row in scenario_rows(dataset) if row["scenario_id"] == "D2")
    assert d2["expected_operation"] == "HOLD"
    assert d2["operation"] == "HOLD"
    assert d2["expected_governance"] == "HOLD"
    assert d2["governance"] == "REJECT"
    assert d2["correctness"] == "MISMATCH"
    assert d2["incorrect_count"] == 3
    assert len([row for row in mismatch_rows(dataset) if row["scenario_id"] == "D2"]) == 3
    assert len(confusion_matrix_figure(dataset, "governance").data) == 1


def test_b0_synth_is_a_derived_reference_not_an_independent_arm(
    dataset: ExperimentDataset,
) -> None:
    baseline = summary_metrics(dataset)["b0_synth"]
    assert baseline["assessment_type"] == "DERIVED_UNCHANGED_CONFIGURATION_ASSESSMENT"
    assert baseline["independently_executed_baseline_arm"] is False
    assert baseline["operation"] == "UNCHANGED_CONFIGURATION"


def test_duration_conversion_and_missing_measurements_are_preserved(
    dataset: ExperimentDataset,
) -> None:
    rows = duration_rows(dataset)
    assert duration_rows(dataset, operations=set()) == []
    first = rows[0]
    assert first["duration_ms"] == pytest.approx(first["duration_ns"] / 1_000_000)
    modified = copy.deepcopy(dataset.results)
    modified["technical_repetition_results"][0]["duration_ns"] = None
    with_missing = replace(dataset, results=modified)
    missing_rows = duration_rows(with_missing)
    assert missing_rows[0]["duration_ns"] is None
    assert missing_rows[0]["duration_ms"] is None
    summary = duration_summary(missing_rows)
    assert summary["n"] == 23
    assert summary["missing"] == 1
    assert len(duration_distribution_figure(missing_rows).data) == 1


def test_empty_dataset_aggregations_and_charts_are_graceful(
    dataset: ExperimentDataset,
) -> None:
    results = copy.deepcopy(dataset.results)
    results["scenario_results"] = []
    results["technical_repetition_results"] = []
    results["scenario_count"] = 0
    results["technical_repetition_count"] = 0
    empty = replace(
        dataset,
        results=results,
        scenario_catalog={},
        report_text="",
        integrity=IntegritySummary(),
        warnings=(),
    )
    assert scenario_rows(empty) == []
    assert repetition_rows(empty) == []
    assert mismatch_rows(empty) == []
    assert summary_metrics(empty)["technical_repetition_count"] == 0
    assert duration_summary(duration_rows(empty))["n"] == 0
    assert report_consistency_issues(empty)
    assert len(coverage_transition_figure([]).data) == 0
    assert len(duration_distribution_figure([]).data) == 0


def test_publication_figures_export_and_refuse_accidental_overwrite(
    dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    paths = export_publication_figures(dataset, tmp_path)
    assert len(paths) == 6
    assert {path.suffix for path in paths} == {".svg", ".png"}
    assert all(path.is_file() and path.stat().st_size > 1_000 for path in paths)
    first_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    with pytest.raises(FileExistsError, match="Choose another"):
        export_publication_figures(dataset, tmp_path)

    repeated_paths = export_publication_figures(dataset, tmp_path, force=True)
    repeated_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in repeated_paths
    }
    assert first_hashes == repeated_hashes
