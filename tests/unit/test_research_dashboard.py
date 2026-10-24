"""Source-bound and synthetic checks for the read-only Method P dashboard."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import struct
import xml.etree.ElementTree as ET
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
    validate_publication_export_readiness,
    validate_results_payload,
)
from research_dashboard.figures import export_publication_figures
from research_dashboard.figures import main as figures_main
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


@pytest.fixture
def isolated_dataset(dataset: ExperimentDataset, tmp_path: Path) -> ExperimentDataset:
    """Copy the retained source package so negative tests never mutate it."""

    copied_experiment = tmp_path / "experiment"
    shutil.copytree(dataset.experiment_dir, copied_experiment)
    return load_dataset(copied_experiment / "run_v1" / "results_v1.json")


def _refresh_checksum(run_dir: Path, relative_path: str) -> None:
    inventory = run_dir / "SHA256SUMS"
    lines = inventory.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        digest, listed_path = line.split(maxsplit=1)
        listed_path = listed_path.lstrip("* ")
        if listed_path == relative_path:
            actual = hashlib.sha256((run_dir / relative_path).read_bytes()).hexdigest()
            lines[index] = f"{actual}  {relative_path}"
            inventory.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    raise AssertionError(f"Expected {relative_path} to be listed in SHA256SUMS")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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
    assert list(figure.layout.xaxis.ticktext) == [
        "Current coverage assessment",
        "Observed operation",
        "Candidate coverage assessment",
        "Governance",
    ]


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
    governance_figure = confusion_matrix_figure(dataset, "governance")
    operation_figure = confusion_matrix_figure(dataset, "operation")
    assert len(governance_figure.data) == 1
    assert len(operation_figure.data) == 1
    assert "author-declared reference" in governance_figure.layout.title.text.lower()
    assert "author-declared reference" in operation_figure.layout.title.text.lower()


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
    validate_publication_export_readiness(dataset)
    paths = export_publication_figures(dataset, tmp_path)
    assert len(paths) == 6
    assert {path.suffix for path in paths} == {".svg", ".png"}
    assert all(path.is_file() and path.stat().st_size > 1_000 for path in paths)
    svg_paths = [path for path in paths if path.suffix == ".svg"]
    png_paths = [path for path in paths if path.suffix == ".png"]
    for path in svg_paths:
        # These SVG files are generated by Matplotlib in this test, not user input.
        svg_bytes = path.read_bytes()
        ET.fromstring(svg_bytes)  # noqa: S314
        assert all(line == line.rstrip(b" \t") for line in svg_bytes.splitlines())
    for path in png_paths:
        png = path.read_bytes()
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        phys_offset = png.index(b"pHYs")
        pixels_per_meter = struct.unpack(">I", png[phys_offset + 4 : phys_offset + 8])[0]
        assert png[phys_offset + 12] == 1
        assert pixels_per_meter * 0.0254 == pytest.approx(300, abs=0.1)
    first_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    with pytest.raises(FileExistsError, match="Choose another"):
        export_publication_figures(dataset, tmp_path)

    repeated_paths = export_publication_figures(dataset, tmp_path, force=True)
    repeated_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in repeated_paths
    }
    assert first_hashes == repeated_hashes


@pytest.mark.parametrize(
    ("relative_path", "message"),
    [
        ("run_v1/SHA256SUMS", "SHA256SUMS"),
        ("run_v1/execution_manifest.json", "execution manifest"),
        ("run_v1/raw_records_manifest.json", "raw-record manifest"),
        ("run_v1/score_manifest.json", "score manifest"),
        ("run_v1/results_v1.json", "results"),
        ("run_v1/report_v1.md", "source report"),
        ("reference_v1.json", "author-declared reference"),
    ],
)
def test_publication_export_requires_source_artifacts_before_output_creation(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
    relative_path: str,
    message: str,
) -> None:
    source = isolated_dataset.experiment_dir / relative_path
    source.unlink()
    output = tmp_path / "not-created"

    with pytest.raises(DashboardDataError, match=message):
        export_publication_figures(isolated_dataset, output)

    assert not output.exists()


def test_publication_export_rejects_empty_checksum_inventory(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    (isolated_dataset.run_dir / "SHA256SUMS").write_text("", encoding="utf-8")
    reloaded = load_dataset(isolated_dataset.results_path)
    output = tmp_path / "empty-inventory-output"

    with pytest.raises(DashboardDataError, match="0/0|non-empty SHA256SUMS"):
        export_publication_figures(reloaded, output)

    assert not output.exists()


def test_publication_export_rejects_missing_checksum_listed_artifact(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    (isolated_dataset.run_dir / "raw" / "A1_method_p_rep_01.json").unlink()
    output = tmp_path / "missing-artifact-output"

    with pytest.raises(DashboardDataError, match="complete checksum verification"):
        export_publication_figures(isolated_dataset, output)

    assert not output.exists()


def test_publication_export_rejects_checksum_mismatch(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    artifact = isolated_dataset.run_dir / "raw" / "A1_method_p_rep_01.json"
    artifact.write_bytes(artifact.read_bytes() + b"corruption")
    output = tmp_path / "corrupted-output"

    with pytest.raises(DashboardDataError, match="SHA-256 mismatch"):
        export_publication_figures(isolated_dataset, output)

    assert not output.exists()


def test_publication_export_rejects_uncovered_checksum_inventory(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    inventory = isolated_dataset.run_dir / "SHA256SUMS"
    lines = inventory.read_text(encoding="utf-8").splitlines()
    inventory.write_text(
        "\n".join(line for line in lines if not line.endswith("  score_manifest.json")) + "\n",
        encoding="utf-8",
    )
    reloaded = load_dataset(isolated_dataset.results_path)
    output = tmp_path / "incomplete-inventory-output"

    with pytest.raises(DashboardDataError, match="does not cover required source artifacts"):
        export_publication_figures(reloaded, output)

    assert not output.exists()


def test_publication_export_rejects_score_manifest_identity_mismatch(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    score_path = isolated_dataset.run_dir / "score_manifest.json"
    score_manifest = json.loads(score_path.read_text(encoding="utf-8"))
    score_manifest["reference_sha256"] = "0" * 64
    score_path.write_text(json.dumps(score_manifest, indent=2) + "\n", encoding="utf-8")
    _refresh_checksum(isolated_dataset.run_dir, "score_manifest.json")
    source_dataset = load_dataset(isolated_dataset.results_path)
    output = tmp_path / "identity-mismatch-output"

    with pytest.raises(DashboardDataError, match="Score manifest reference_sha256"):
        export_publication_figures(source_dataset, output)

    assert not output.exists()


def test_publication_export_rejects_execution_manifest_identity_mismatch(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    run_dir = isolated_dataset.run_dir
    execution_path = run_dir / "execution_manifest.json"
    execution_manifest = json.loads(execution_path.read_text(encoding="utf-8"))
    execution_manifest["experiment_id"] = "UNRELATED_EXPERIMENT"
    _write_json(execution_path, execution_manifest)
    execution_digest = hashlib.sha256(execution_path.read_bytes()).hexdigest()

    results_path = run_dir / "results_v1.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    results["execution_manifest_sha256"] = execution_digest
    _write_json(results_path, results)
    results_digest = hashlib.sha256(results_path.read_bytes()).hexdigest()

    score_path = run_dir / "score_manifest.json"
    score_manifest = json.loads(score_path.read_text(encoding="utf-8"))
    score_manifest["execution_manifest_sha256"] = execution_digest
    score_manifest["result_sha256"] = results_digest
    _write_json(score_path, score_manifest)
    for relative_path in (
        "execution_manifest.json",
        "results_v1.json",
        "score_manifest.json",
    ):
        _refresh_checksum(run_dir, relative_path)
    source_dataset = load_dataset(results_path)
    output = tmp_path / "execution-identity-output"

    with pytest.raises(DashboardDataError, match="experiment_id does not match results"):
        export_publication_figures(source_dataset, output)

    assert not output.exists()


def test_publication_export_rejects_inconsistent_report_summary(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    report_path = isolated_dataset.run_dir / "report_v1.md"
    report_text = report_path.read_text(encoding="utf-8")
    changed_report = report_text.replace(
        "Scenario-level outcomes: 8", "Scenario-level outcomes: 7", 1
    )
    assert changed_report != report_text
    report_path.write_text(changed_report, encoding="utf-8")
    score_path = isolated_dataset.run_dir / "score_manifest.json"
    score_manifest = json.loads(score_path.read_text(encoding="utf-8"))
    score_manifest["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    score_path.write_text(json.dumps(score_manifest, indent=2) + "\n", encoding="utf-8")
    _refresh_checksum(isolated_dataset.run_dir, "report_v1.md")
    _refresh_checksum(isolated_dataset.run_dir, "score_manifest.json")
    inconsistent_dataset = load_dataset(isolated_dataset.results_path)
    output = tmp_path / "inconsistent-report-output"

    with pytest.raises(DashboardDataError, match="report consistency check failed"):
        export_publication_figures(inconsistent_dataset, output)

    assert not output.exists()


def test_failed_force_export_preserves_existing_figures(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
) -> None:
    output = tmp_path / "existing-output"
    output.mkdir()
    existing = output / "coverage_assessment_transitions.svg"
    existing.write_bytes(b"previous publication figure")
    (isolated_dataset.run_dir / "SHA256SUMS").unlink()

    with pytest.raises(DashboardDataError, match="checksum inventory"):
        export_publication_figures(isolated_dataset, output, force=True)

    assert existing.read_bytes() == b"previous publication figure"
    assert sorted(path.name for path in output.iterdir()) == [existing.name]


def test_cli_force_does_not_bypass_publication_integrity(
    isolated_dataset: ExperimentDataset,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (isolated_dataset.run_dir / "SHA256SUMS").write_text("", encoding="utf-8")
    output = tmp_path / "cli-output"

    exit_code = figures_main(
        ["--results", str(isolated_dataset.results_path), "--output-dir", str(output), "--force"]
    )
    error_output = capsys.readouterr().err

    assert exit_code != 0
    assert "0/0" in error_output or "non-empty SHA256SUMS" in error_output
    assert not output.exists()
