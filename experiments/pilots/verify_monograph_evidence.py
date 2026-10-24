"""Verify and reproduce the bounded CI evidence package without changing source evidence."""

# Long lines in this module include publication prose embedded in derived artifacts.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from research_dashboard.data import (
    DashboardDataError,
    default_results_path,
    load_dataset,
    validate_publication_export_readiness,
)
from research_dashboard.figures import (
    coverage_figure,
    duration_figure,
    export_publication_figures,
    operations_governance_figure,
)
from research_dashboard.metrics import (
    duration_rows,
    duration_summary,
    report_consistency_issues,
    summary_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
BASE_MAIN_SHA = "e5dca56e1ad287eece538e93a6fa9294afeb2e73"
PACKAGE_ID = "MONO_E1_CI_EVIDENCE_PACKAGE_V1"
PACKAGE_DIR = ROOT / "experiments/pilots/mono_e1_ci_evidence_v1"
REPORT_PATH = ROOT / "docs/MONO_E1_CI_EXPERIMENTAL_EVIDENCE_REPORT_UA.md"
RESULTS_PATH = default_results_path()
EXPERIMENT_DIR = ROOT / "experiments/pilots/mono_e1_dev_p_decisions_v1"
RUN_DIR = EXPERIMENT_DIR / "run_v1"
SCENARIO_PATH = EXPERIMENT_DIR / "scenarios_v1.json"
REFERENCE_PATH = EXPERIMENT_DIR / "reference_v1.json"
EVAL_ARTIFACTS = {
    "EVAL-01": {
        "archive": ROOT / "experiments/pilots/EVAL01_RAW_EVIDENCE_V1.zip",
        "analysis": ROOT / "experiments/pilots/EVAL01_ANALYSIS_V1.json",
        "cases": ROOT / "experiments/pilots/EVAL01_CASE_RESULTS_V1.csv",
        "report": ROOT / "experiments/pilots/EVAL01_REPORT_V1.md",
        "analysis_member": "EVAL01_ANALYSIS_V1.json",
        "cases_member": "EVAL01_CASE_RESULTS_V1.csv",
        "report_member": "EVAL01_REPORT_V1.md",
        "metric_heading": "### Case-level detection metrics",
        "timing_heading": "### Subprocess wall time",
    },
    "EVAL-02": {
        "archive": ROOT / "experiments/pilots/EVAL02_RAW_EVIDENCE_V1.zip",
        "analysis": ROOT / "experiments/pilots/EVAL02_ANALYSIS_V1.json",
        "cases": ROOT / "experiments/pilots/EVAL02_CASE_RESULTS_V1.csv",
        "report": ROOT / "experiments/pilots/EVAL02_REPORT_V1.md",
        "analysis_member": "EVAL02_ANALYSIS_V1.json",
        "cases_member": "EVAL02_CASE_RESULTS_V1.csv",
        "report_member": "EVAL02_REPORT_V1.md",
        "metric_heading": "## Case-level metrics",
        "timing_heading": "## Descriptive evaluator time",
    },
}
TABLE_FILES = {
    "table_1_scope": "table_01_scope_v1.csv",
    "table_2_evaluators": "table_02_evaluator_results_v1.csv",
    "table_3_method_p": "table_03_method_p_decisions_v1.csv",
    "table_4_governance": "table_04_governance_v1.csv",
    "table_5_execution_cost": "table_05_execution_cost_v1.csv",
    "table_6_limitations": "table_06_limitations_v1.csv",
    "claim_to_evidence": "claim_to_evidence_v1.csv",
}
FIGURE_FILES = {
    "coverage_assessment_transitions": (
        "coverage_assessment_transitions.svg",
        "coverage_assessment_transitions.png",
    ),
    "operations_and_governance": (
        "operations_and_governance.svg",
        "operations_and_governance.png",
    ),
    "execution_duration_by_operation_scenario": (
        "execution_duration_by_operation_scenario.svg",
        "execution_duration_by_operation_scenario.png",
    ),
}


class EvidencePackageError(ValueError):
    """Raised when source evidence or a derived publication artifact is inconsistent."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise EvidencePackageError(f"Required evidence file is missing: {path}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise EvidencePackageError(f"Could not read JSON evidence {path}: {error}") from error
    if not isinstance(value, dict):
        raise EvidencePackageError(f"Expected a JSON object in {path}")
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as error:
        raise EvidencePackageError(f"Could not read evidence file {path}: {error}") from error


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _display(value: Any) -> str:
    if value is None:
        return "NOT_REPORTED"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    from io import StringIO

    output = StringIO(newline="")
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _display(row.get(key)) for key in fieldnames})
    return output.getvalue().encode("utf-8")


def _markdown_cell(value: Any) -> str:
    return _display(value).replace("|", "\\|").replace("\n", " ")


def _markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "*Дані відсутні.*"
    headings = [heading for _key, heading in columns]
    lines = ["| " + " | ".join(headings) + " |", "|" + "|".join("---" for _ in headings) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(_markdown_cell(row.get(key)) for key, _ in columns) + " |")
    return "\n".join(lines)


def _replay_method_p(root: Path, dataset: Any) -> dict[str, Any]:
    """Re-run the pinned scorer on a temporary copy of raw records; never write to the retained run."""

    from experiments.pilots.mono_e1_dev_p_decisions_v1 import runner

    score_manifest = dataset.score_manifest
    if not isinstance(score_manifest, dict):
        raise EvidencePackageError("The retained Method P score manifest is unavailable")
    scorer_path = Path(runner.__file__).resolve()
    expected_code_digest = score_manifest.get("scorer_code_sha256")
    actual_code_digest = _sha256_file(scorer_path)
    if actual_code_digest != expected_code_digest:
        raise EvidencePackageError(
            "Pinned Method P scorer source digest differs from score_manifest.json"
        )
    scorer_commit = str(score_manifest.get("scorer_source_commit_sha", ""))
    if not scorer_commit:
        raise EvidencePackageError("score_manifest.json has no scorer source commit")

    try:
        raw_rows = runner._verify_raw_manifest(dataset.run_dir)
        execution_manifest = runner._read_json(dataset.run_dir / "execution_manifest.json")
        runner._verify_method_input_archives(dataset.run_dir, execution_manifest)
        raw_manifest_bytes = (dataset.run_dir / "raw_records_manifest.json").read_bytes()
    except (OSError, RuntimeError, ValueError) as error:
        raise EvidencePackageError(f"Method P raw evidence verification failed: {error}") from error

    original_git = runner._git

    def pinned_scorer_git(*arguments: str, cwd: Path = root) -> str:
        if arguments == ("rev-parse", "HEAD") and cwd.resolve() == root.resolve():
            return scorer_commit
        return original_git(*arguments, cwd=cwd)

    with tempfile.TemporaryDirectory(prefix="mono-e1-evidence-replay-") as temporary:
        temporary_run = Path(temporary) / "run_v1"
        shutil.copytree(dataset.run_dir, temporary_run)
        runner._git = pinned_scorer_git
        try:
            runner._score(temporary_run)
        except Exception as error:
            raise EvidencePackageError(
                f"Read-only Method P scorer replay failed: {type(error).__name__}: {error}"
            ) from error
        finally:
            runner._git = original_git

        replayed_results = _read_json(temporary_run / "results_v1.json")
        replayed_report = (temporary_run / "report_v1.md").read_bytes()
        replayed_score_manifest = _read_json(temporary_run / "score_manifest.json")

    stored_results = dataset.results
    stored_report = dataset.report_text.encode("utf-8")
    stored_score_manifest = dataset.score_manifest
    if replayed_results != stored_results:
        raise EvidencePackageError(
            "Scorer replay derived results that differ from retained results_v1.json"
        )
    if replayed_report != stored_report:
        raise EvidencePackageError("Scorer replay report differs from retained report_v1.md")
    if replayed_score_manifest != stored_score_manifest:
        raise EvidencePackageError(
            "Scorer replay manifest differs from retained score_manifest.json"
        )
    if (dataset.run_dir / "raw_records_manifest.json").read_bytes() != raw_manifest_bytes:
        raise EvidencePackageError("Method P raw-record manifest changed during read-only replay")
    return {
        "raw_record_files_verified": len(raw_rows),
        "input_bundle_archives_verified": len(
            execution_manifest["method_input_bundle_archive_sha256"]
        ),
        "scorer_replay": "PASS",
        "results_report_score_manifest_match": "PASS",
        "raw_manifest_sha256": _sha256_bytes(raw_manifest_bytes),
        "scorer_source_commit_sha": scorer_commit,
        "scorer_code_sha256": actual_code_digest,
        "execution_source_commit_sha": execution_manifest.get("source_commit_sha"),
        "reference_sha256": score_manifest.get("reference_sha256"),
    }


def _metric_from_case_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Recalculate binary evaluator metrics from eligible case-level observations."""

    eligible = [
        row
        for row in rows
        if row.get("valid_for_confusion_matrix") is True
        and row.get("expected_compliance") in {"COMPLIANT", "NON_COMPLIANT"}
        and row.get("observed_compliance_case_level") in {"COMPLIANT", "NON_COMPLIANT"}
    ]
    case_ids = [str(row.get("case_id")) for row in eligible]
    if len(case_ids) != len(set(case_ids)):
        raise EvidencePackageError("Evaluator case table contains duplicate eligible case IDs")
    tp = sum(
        row["expected_compliance"] == "NON_COMPLIANT"
        and row["observed_compliance_case_level"] == "NON_COMPLIANT"
        for row in eligible
    )
    fp = sum(
        row["expected_compliance"] == "COMPLIANT"
        and row["observed_compliance_case_level"] == "NON_COMPLIANT"
        for row in eligible
    )
    tn = sum(
        row["expected_compliance"] == "COMPLIANT"
        and row["observed_compliance_case_level"] == "COMPLIANT"
        for row in eligible
    )
    fn = sum(
        row["expected_compliance"] == "NON_COMPLIANT"
        and row["observed_compliance_case_level"] == "COMPLIANT"
        for row in eligible
    )
    total = len(eligible)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    accuracy = (tp + tn) / total if total else None
    f1_denominator = 2 * tp + fp + fn
    f1 = 2 * tp / f1_denominator if f1_denominator else None
    return {
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "evaluable_cases": total,
        "excluded_cases": len(rows) - total,
        "precision": precision,
        "recall_sensitivity": recall,
        "specificity": specificity,
        "accuracy": accuracy,
        "f1": f1,
    }


def _markdown_table_after(text: str, heading: str) -> tuple[list[str], list[dict[str, str]]]:
    lines = text.splitlines()
    try:
        heading_index = lines.index(heading)
    except ValueError as error:
        raise EvidencePackageError(
            f"Published evaluator report is missing section {heading!r}"
        ) from error
    table_lines: list[str] = []
    for line in lines[heading_index + 1 :]:
        if line.startswith("|"):
            table_lines.append(line)
        elif table_lines:
            break
    if len(table_lines) < 3:
        raise EvidencePackageError(f"Published evaluator report has no table after {heading!r}")
    headers = [cell.strip().strip("`") for cell in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        values = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(values) != len(headers):
            raise EvidencePackageError(f"Malformed table row in report section {heading!r}")
        rows.append(dict(zip(headers, values, strict=True)))
    return headers, rows


def _assert_number(actual: str, expected: Any, label: str) -> None:
    try:
        actual_number = float(actual)
        expected_number = float(expected)
    except (TypeError, ValueError) as error:
        raise EvidencePackageError(f"Invalid numeric value for {label}: {actual!r}") from error
    if not math.isclose(actual_number, expected_number, rel_tol=1e-9, abs_tol=1e-9):
        raise EvidencePackageError(
            f"Published {label} {actual_number} differs from derived value {expected_number}"
        )


def _assert_eval_report_aggregates(
    experiment_id: str,
    analysis: dict[str, Any],
    report_text: str,
) -> None:
    config = EVAL_ARTIFACTS[experiment_id]
    _headers, metric_rows = _markdown_table_after(report_text, config["metric_heading"])
    metrics_by_evaluator = analysis["evaluator_metrics"]
    if len(metric_rows) != len(metrics_by_evaluator):
        raise EvidencePackageError(
            f"{experiment_id} report evaluator table row count differs from analysis"
        )
    for evaluator_id, aggregate in metrics_by_evaluator.items():
        row = next(
            (candidate for candidate in metric_rows if candidate.get("Evaluator") == evaluator_id),
            None,
        )
        if row is None:
            raise EvidencePackageError(f"{experiment_id} report omits {evaluator_id}")
        matrix = aggregate["confusion_matrix"]
        for column in ("TP", "FP", "TN", "FN"):
            key = column.lower()
            if int(row[column]) != int(matrix[key]):
                raise EvidencePackageError(
                    f"{experiment_id} report {column} differs for {evaluator_id}"
                )
        for column, key in (
            ("Precision", "precision"),
            ("Recall", "recall_sensitivity"),
            ("Specificity", "specificity"),
            ("Accuracy", "accuracy"),
            ("F1", "f1"),
        ):
            _assert_number(row[column], aggregate[key], f"{experiment_id} {evaluator_id} {column}")
        evaluable_key = "Labeled/evaluable" if experiment_id == "EVAL-01" else "Labeled/evaluable"
        expected_evaluable = int(
            aggregate.get(
                "evaluable_labeled_cases", aggregate.get("evaluable_binary_applicable_cases", 0)
            )
        )
        expected_eligible = int(
            aggregate.get(
                "eligible_labeled_cases", aggregate.get("eligible_binary_applicable_cases", 0)
            )
        )
        if row[evaluable_key] != f"{expected_eligible}/{expected_evaluable}":
            raise EvidencePackageError(
                f"{experiment_id} report eligible-case count differs for {evaluator_id}"
            )
        if experiment_id == "EVAL-01":
            if int(row["Unknown or invalid"]) != int(aggregate["unknown_or_invalid_labeled_cases"]):
                raise EvidencePackageError(
                    f"{experiment_id} unknown-case count differs for {evaluator_id}"
                )
        elif int(row["Excluded"]) != int(aggregate["excluded_from_matrix_cases"]):
            raise EvidencePackageError(
                f"{experiment_id} excluded-case count differs for {evaluator_id}"
            )

    _timing_headers, timing_rows = _markdown_table_after(report_text, config["timing_heading"])
    timing = analysis["descriptive_wall_time"]
    if len(timing_rows) != len(timing):
        raise EvidencePackageError(
            f"{experiment_id} report timing table row count differs from analysis"
        )
    for evaluator_id, summary in timing.items():
        row = next(
            (candidate for candidate in timing_rows if candidate.get("Evaluator") == evaluator_id),
            None,
        )
        if row is None:
            raise EvidencePackageError(f"{experiment_id} timing table omits {evaluator_id}")
        if int(row["Valid completed calls"]) != int(summary["n_completed"]):
            raise EvidencePackageError(
                f"{experiment_id} completed timing count differs for {evaluator_id}"
            )
        for column, key in (
            ("Median ms", "median_ms"),
            ("Minimum ms", "minimum_ms"),
            ("Maximum ms", "maximum_ms"),
        ):
            _assert_number(row[column], summary[key], f"{experiment_id} {evaluator_id} {column}")


def _assert_eval_csv_matches_analysis(
    experiment_id: str,
    csv_path: Path,
    analysis: dict[str, Any],
) -> None:
    expected = {
        (row["case_id"], evaluator_id): row
        for evaluator_id, rows in analysis["evaluator_case_results"].items()
        for row in rows
    }
    try:
        with csv_path.open(encoding="utf-8", newline="") as source:
            actual = {(row["case_id"], row["evaluator_id"]): row for row in csv.DictReader(source)}
    except (OSError, KeyError) as error:
        raise EvidencePackageError(
            f"Could not read {experiment_id} case-result CSV: {error}"
        ) from error
    if set(actual) != set(expected) or len(actual) != len(expected):
        raise EvidencePackageError(f"{experiment_id} CSV case inventory differs from analysis JSON")
    fields = (
        "source_commit_sha",
        "application_tree_sha",
        "expected_compliance",
        "observed_compliance_case_level",
        "valid_for_confusion_matrix",
    )
    for key, expected_row in expected.items():
        actual_row = actual[key]
        for field in fields:
            expected_value = expected_row.get(field)
            actual_value: Any = actual_row.get(field)
            if field == "valid_for_confusion_matrix":
                actual_value = actual_value == "True"
            if actual_value != expected_value:
                raise EvidencePackageError(
                    f"{experiment_id} CSV {field} differs from analysis for {key}"
                )


def _assert_eval02_report_preserves_archive(archived: bytes, published: bytes, root: Path) -> None:
    """Validate the documented report erratum without replacing the archived original."""

    archived_text = archived.decode("utf-8").replace("\r\n", "\n")
    published_text = published.decode("utf-8").replace("\r\n", "\n")
    clarification_heading = "## Post-experiment execution-status clarification\n"
    next_heading = "## Threats to validity\n"
    try:
        before, remainder = published_text.split(clarification_heading, maxsplit=1)
        clarification, after = remainder.split(next_heading, maxsplit=1)
    except ValueError as error:
        raise EvidencePackageError(
            "Published EVAL-02 report is missing its bounded post-experiment clarification"
        ) from error

    reconstructed_archive = before + next_heading + after
    reconstructed_archive = reconstructed_archive.replace(
        "Raw archive/inventory integrity: PASS;",
        "Raw archive/inventory integrity: - PASS;",
        1,
    )
    if reconstructed_archive != archived_text or not clarification.strip():
        raise EvidencePackageError(
            "Published EVAL-02 report changes archived content outside its documented erratum"
        )
    erratum = (root / "experiments/pilots/EVAL02_POST_EXPERIMENT_ERRATUM_V1.md").read_text(
        encoding="utf-8"
    )
    required_clarification_facts = (
        "all 60 calls completed",
        "three `FINDING_CLASS_MISMATCH` failures",
        "zero launch errors and zero parse errors",
        "all three repeats",
    )
    if (
        "editorial amendments" not in erratum
        or "diagnostic-expectation mismatches" not in erratum
        or any(fact not in clarification for fact in required_clarification_facts)
    ):
        raise EvidencePackageError("EVAL-02 report clarification is not supported by its erratum")


def _validate_evaluator_reports(root: Path, canonical_validation: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for experiment_id, files in EVAL_ARTIFACTS.items():
        analysis = _read_json(files["analysis"])
        report_text = files["report"].read_text(encoding="utf-8")
        _assert_eval_report_aggregates(experiment_id, analysis, report_text)
        _assert_eval_csv_matches_analysis(experiment_id, files["cases"], analysis)
        metrics: dict[str, Any] = {}
        for evaluator_id, case_rows in analysis["evaluator_case_results"].items():
            calculated = _metric_from_case_rows(case_rows)
            recorded = analysis["evaluator_metrics"][evaluator_id]
            if calculated["confusion_matrix"] != recorded["confusion_matrix"]:
                raise EvidencePackageError(
                    f"{experiment_id} recalculated confusion matrix differs for {evaluator_id}"
                )
            for key in ("precision", "recall_sensitivity", "specificity", "accuracy", "f1"):
                recorded_value = recorded[key]
                if calculated[key] is None or not math.isclose(
                    float(calculated[key]), float(recorded_value), rel_tol=1e-9, abs_tol=1e-9
                ):
                    raise EvidencePackageError(
                        f"{experiment_id} recalculated {key} differs for {evaluator_id}"
                    )
            metrics[evaluator_id] = calculated

        archive_path = files["archive"]
        validation_entry = canonical_validation["evaluator_control_evidence"][experiment_id]
        try:
            with ZipFile(archive_path) as archive:
                for member_key in ("analysis_member", "cases_member", "report_member"):
                    member = files[member_key]
                    published_path = files[member_key.replace("_member", "")]
                    archived_bytes = archive.read(member)
                    published_bytes = published_path.read_bytes()
                    if experiment_id == "EVAL-02" and member_key == "report_member":
                        _assert_eval02_report_preserves_archive(
                            archived_bytes,
                            published_bytes,
                            root,
                        )
                        continue
                    if archived_bytes.replace(b"\r\n", b"\n") != published_bytes.replace(
                        b"\r\n", b"\n"
                    ):
                        raise EvidencePackageError(
                            f"{experiment_id} published {member} differs from the validated archive"
                        )
        except (BadZipFile, KeyError, OSError) as error:
            raise EvidencePackageError(
                f"{experiment_id} archive readback failed: {error}"
            ) from error

        result[experiment_id] = {
            "archive_sha256": validation_entry["archive_sha256"],
            "technical_calls": validation_entry["calls_completed"],
            "internal_checksums_verified": validation_entry["internal_checksums_verified"],
            "diagnostic_mismatches": validation_entry["diagnostic_mismatches"],
            "repeats_are_independent_cases": analysis.get(
                "repeats_are_independent_cases",
                analysis.get("repeated_runs_are_independent_cases"),
            ),
            "recalculated_metrics": metrics,
            "published_report_csv_archive_match": "PASS",
        }
    if result["EVAL-02"]["diagnostic_mismatches"] != 3:
        raise EvidencePackageError("EVAL-02 must retain all three diagnostic mismatches")
    eval02_report = EVAL_ARTIFACTS["EVAL-02"]["report"].read_text(encoding="utf-8")
    eval02_erratum = root / "experiments/pilots/EVAL02_POST_EXPERIMENT_ERRATUM_V1.md"
    erratum_text = eval02_erratum.read_text(encoding="utf-8")
    if (
        "FINDING_CLASS_MISMATCH" not in eval02_report
        or "FINDING_CLASS_MISMATCH" not in erratum_text
    ):
        raise EvidencePackageError(
            "EVAL-02 diagnostic mismatches are absent from report or erratum"
        )
    for repeat in (1, 2, 3):
        if f"repeat {repeat}" not in eval02_report:
            raise EvidencePackageError(f"EVAL-02 report omits diagnostic mismatch repeat {repeat}")
    result["EVAL-02"]["diagnostic_mismatch_repeats"] = [1, 2, 3]
    result["EVAL-02"]["postrun_validator"] = "PASS"
    return result


def _canonical_rows(root: Path, canonical_validation: dict[str, Any]) -> list[dict[str, Any]]:
    files = {
        "A0_3_GOVERNED_MODULE_GRAPH": (
            root / "architecture/acceptance/a1/a0_3_canonical_checkpoint.json",
            {
                "AC_PUBLIC_API": root
                / "architecture/acceptance/a1/a0_3_canonical_public_api_observation.json",
                "AC_MODULE_GRAPH": root
                / "architecture/acceptance/a1/a0_3_canonical_module_graph_observation.json",
            },
        ),
        "A0_4_REPORT_QUERY_PORT": (
            root / "architecture/acceptance/a1/a0_4_canonical_checkpoint.json",
            {
                "AC_PUBLIC_API": root
                / "architecture/acceptance/a1/a0_4_canonical_public_api_observation.json",
                "AC_MODULE_GRAPH": root
                / "architecture/acceptance/a1/a0_4_canonical_module_graph_observation.json",
            },
        ),
    }
    rows = []
    for state, (checkpoint_path, observations) in files.items():
        checkpoint = _read_json(checkpoint_path)
        source = checkpoint.get("source") or checkpoint
        source_sha = source.get("source_sha")
        app_tree_sha = source.get("application_tree_sha")
        repository_tree_sha = source.get("repository_tree_sha")
        if not source_sha or not app_tree_sha or checkpoint.get("readback_status") != "PASS":
            raise EvidencePackageError(f"Canonical checkpoint identity is incomplete for {state}")
        for evaluator_id, observation_path in observations.items():
            evaluator = checkpoint.get("evaluators", {}).get(evaluator_id)
            observation = _read_json(observation_path)
            observation_state = observation.get("architecture", {}).get("state")
            observation_result = observation.get("result", {})
            if evaluator is None or observation_state != state:
                raise EvidencePackageError(
                    f"Canonical observation does not match {state}/{evaluator_id}"
                )
            if evaluator.get("compliance") != observation_result.get("compliance"):
                raise EvidencePackageError(
                    f"Canonical checkpoint/observation outcome differs for {evaluator_id}"
                )
            if evaluator.get("source_scope_complete") is not True:
                raise EvidencePackageError(
                    f"Canonical {evaluator_id} declared source scope is incomplete"
                )
            rows.append(
                {
                    "track": "A",
                    "evidence_type": "CANONICAL_SOURCE_BOUND_OBSERVATION",
                    "architecture_state": state,
                    "architecture_before": "NOT_APPLICABLE",
                    "architecture_after": "NOT_APPLICABLE",
                    "source_commit_sha": source_sha,
                    "repository_tree_sha": repository_tree_sha or "NOT_RECORDED",
                    "application_tree_sha": app_tree_sha,
                    "evaluator_id": evaluator_id,
                    "outcome": observation_result.get("compliance", "NOT_REPORTED"),
                    "inspection_scope": (
                        f"статична інспекція app/modules; {evaluator.get('inspected_files')} файлів; "
                        f"{evaluator.get('inspected_imports')} імпортів; повний задекларований обсяг"
                    ),
                    "lifecycle_stage": "CI — статична перевірка вихідного коду",
                    "evidence_source": f"{checkpoint_path.relative_to(root).as_posix()} + {observation_path.relative_to(root).as_posix()}",
                    "limitations": "Одне зафіксоване спостереження на оцінювача/стан; лише задекларований статичний обсяг; не є доказом повного семантичного покриття зобов'язань або runtime/розгортання.",
                }
            )
    return rows


def _raw_records_by_scenario(root: Path) -> dict[str, list[dict[str, Any]]]:
    raw_dir = RUN_DIR / "raw"
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(raw_dir.glob("*_method_p_rep_*.json")):
        record = _read_json(path)
        grouped[str(record["scenario_id"])].append(record)
    for scenario_id, records in grouped.items():
        records.sort(key=lambda record: int(record["repetition"]))
        if [int(record["repetition"]) for record in records] != [1, 2, 3]:
            raise EvidencePackageError(f"Raw Method P repetitions are incomplete for {scenario_id}")
    if len(grouped) != 8:
        raise EvidencePackageError(f"Expected eight synthetic scenarios, found {len(grouped)}")
    return dict(grouped)


def _candidate_evidence_summary(record: dict[str, Any]) -> str:
    inventory = record.get("evidence_record_inventory", {})
    sidecar = inventory.get("adaptation_evidence_sidecar", {})
    evaluator_rows = inventory.get("evaluator_evidence_records", [])
    sidecar_statuses = sorted(
        {str(row.get("status", "UNKNOWN")) for row in inventory.get("sidecar_pair_proofs", [])}
    )
    current_statuses = sorted(
        {
            str(row.get("status", "UNKNOWN"))
            for row in inventory.get("pre_adaptation_pair_assessments", [])
        }
    )
    candidate_statuses = sorted(
        {
            str(row.get("status", "UNKNOWN"))
            for row in inventory.get("candidate_pair_assessments", [])
        }
    )

    def fmt(values: list[str]) -> str:
        return ",".join(values) if values else "NO_RECORDS"

    return (
        f"sidecar={'PRESENT' if sidecar.get('present') else 'ABSENT'}; "
        f"evaluator_records={len(evaluator_rows)}; "
        f"sidecar_pair_proofs={fmt(sidecar_statuses)}; "
        f"Method_P_current_pairs={fmt(current_statuses)}; "
        f"Method_P_candidate_pairs={fmt(candidate_statuses)}"
    )


def _scenario_and_governance_tables(
    root: Path,
    dataset: Any,
    raw_grouped: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    scenarios = _read_json(SCENARIO_PATH)["scenarios"]
    references = _read_json(REFERENCE_PATH)
    reference_by_id = {str(row["scenario_id"]): row for row in references["cases"]}
    scenario_catalog = {str(row["scenario_id"]): row for row in scenarios}
    result_rows = {row["scenario_id"]: row for row in dataset.results["scenario_results"]}
    repetition_rows = {row["scenario_id"]: [] for row in dataset.results["scenario_results"]}
    for row in dataset.results["technical_repetition_results"]:
        repetition_rows[row["scenario_id"]].append(row)

    table1_synthetic: list[dict[str, Any]] = []
    table3: list[dict[str, Any]] = []
    governance_pairs: Counter[tuple[str, str]] = Counter()
    governance_reasons: dict[tuple[str, str], set[str]] = defaultdict(set)
    for scenario_id in sorted(scenario_catalog):
        scenario = scenario_catalog[scenario_id]
        expected = reference_by_id[scenario_id]
        result = result_rows[scenario_id]
        repetitions = sorted(repetition_rows[scenario_id], key=lambda row: int(row["repetition"]))
        raw_records = raw_grouped[scenario_id]
        first_raw = raw_records[0]
        operation_counts = Counter(row["proposed_operation"] for row in repetitions)
        governance_counts = Counter(row["governance_result"] for row in repetitions)
        operation = next(iter(operation_counts)) if len(operation_counts) == 1 else "MIXED"
        governance = next(iter(governance_counts)) if len(governance_counts) == 1 else "MIXED"
        correct = sum(row["classification"] == "CORRECT" for row in repetitions)
        correctness_counts = result["correct_incorrect_not_evaluable"]
        combined_classification = next(
            (
                status.upper()
                for status, count in correctness_counts.items()
                if count == len(repetitions)
            ),
            "MIXED",
        )
        candidate_counts = Counter(
            row["candidate_configuration_coverage"]["status"] for row in repetitions
        )
        actual_counts = Counter(
            row["actual_post_adaptation_coverage"]["status"] for row in repetitions
        )
        table1_synthetic.append(
            {
                "track": "B",
                "evidence_type": "SYNTHETIC_TEST_ONLY_SCENARIO",
                "architecture_state": scenario_id,
                "source_commit_sha": "SYNTHETIC_FIXTURE — no canonical application revision",
                "repository_tree_sha": "NOT_APPLICABLE",
                "application_tree_sha": first_raw["architecture_after_sha"],
                "evaluator_id": "synthetic_scope_probe_v1 + Method P DEVELOPMENT V1",
                "outcome": scenario["group"],
                "inspection_scope": (
                    f"синтетичні докази режиму {scenario['evidence']['mode']}; "
                    f"{len(scenario['obligations'])} зобов'язань; "
                    f"хеш пакета {first_raw['input_bundle_sha256']}"
                ),
                "lifecycle_stage": "CI — синтетична фікстура TEST_ONLY",
                "evidence_source": f"experiments/pilots/mono_e1_dev_p_decisions_v1/scenarios_v1.json + run_v1/raw/{scenario_id}_method_p_rep_01.json",
                "limitations": "Авторський синтетичний перехід і довіра до політики/оцінювача; не виконання A0.3/A0.4, не незалежний еталон і не вимірювання канонічного методу P.",
                "architecture_before": scenario["architecture_before"],
                "architecture_after": scenario["architecture_after"],
            }
        )
        table3.append(
            {
                "scenario_id": scenario_id,
                "expected_operation_author_declared": expected["expected_operation"].upper(),
                "observed_operation": operation.upper(),
                "expected_governance_author_declared": expected["expected_governance"],
                "observed_governance": governance,
                "operation_agreement": f"{sum(row['proposed_operation'] == expected['expected_operation'] for row in repetitions)}/{len(repetitions)} technical repetitions",
                "combined_reference_agreement": (
                    f"{correct}/{len(repetitions)} classifications; {combined_classification}"
                ),
                "evidence_status": _candidate_evidence_summary(repetitions[0]),
                "candidate_coverage_assessment": ", ".join(
                    f"{status} ({count}/{len(repetitions)})"
                    for status, count in sorted(candidate_counts.items())
                ),
                "actual_post_adaptation_coverage": ", ".join(
                    f"{status} ({count}/{len(repetitions)})"
                    for status, count in sorted(actual_counts.items())
                ),
                "technical_repetitions": len(repetitions),
                "independent_scenario_unit": True,
            }
        )
        for raw_record in raw_records:
            governance = raw_record.get("result", {}).get("governance") or {}
            observed = str(governance.get("result", "EXECUTION_FAILURE"))
            key = (str(expected["expected_governance"]), observed)
            governance_pairs[key] += 1
            governance_reasons[key].update(str(code) for code in governance.get("reason_codes", []))

    table4 = []
    for (expected_governance, observed_governance), count in sorted(governance_pairs.items()):
        matching = count if expected_governance == observed_governance else 0
        scenarios = sorted(
            scenario_id
            for scenario_id, rows in raw_grouped.items()
            if rows[0].get("result", {}).get("governance", {}).get("result") == observed_governance
            and reference_by_id[scenario_id]["expected_governance"] == expected_governance
        )
        if observed_governance == "REJECT" and expected_governance == "HOLD":
            interpretation = "Захисну відмову винесено після зареєстрованих порушень інваріантів і неможливості матеріалізувати заміну; це залишається розбіжністю з оголошеним автором очікуванням HOLD."
        elif observed_governance == "HOLD":
            interpretation = "Невизначеність і недостатність доказів не дозволили прийняти кандидата; HOLD збігається з оголошеним еталоном."
        else:
            interpretation = (
                "Рішення врядування збігається з оголошеним еталоном у цих технічних повторах."
            )
        table4.append(
            {
                "expected_governance": expected_governance,
                "observed_governance": observed_governance,
                "technical_repetition_count": count,
                "matching_repetitions": matching,
                "mismatching_repetitions": count - matching,
                "scenario_ids": ",".join(scenarios),
                "governance_reason_codes": ",".join(
                    sorted(governance_reasons[(expected_governance, observed_governance)])
                )
                or "NONE_RECORDED",
                "interpretation": interpretation,
            }
        )

    return table1_synthetic, table3, table4


def _table5_cost(dataset: Any) -> list[dict[str, Any]]:
    all_rows = duration_rows(dataset)
    result = []
    for operation in ("ALL", "retain", "add", "replace", "hold"):
        selected = (
            all_rows if operation == "ALL" else duration_rows(dataset, operations={operation})
        )
        stats = duration_summary(selected)
        scenario_count = len({row["scenario_id"] for row in selected})
        result.append(
            {
                "observed_operation": operation.upper(),
                "technical_repetitions_n": stats["n"],
                "distinct_scenarios_n": scenario_count,
                "missing_measurements_n": stats["missing"],
                "minimum_ms": stats["minimum_ms"],
                "median_ms": stats["median_ms"],
                "mean_ms": stats["mean_ms"],
                "sample_standard_deviation_ms": stats["sample_stdev_ms"],
                "maximum_ms": stats["maximum_ms"],
                "measurement_boundary": "perf_counter_ns: від початку verify_v3_p_bundle() до результату run_adaptation(); не охоплює створення фікстур/sidecar, архівування пакета, оцінювання, застосування чи повторну оцінку.",
                "interpretation": "Лише описова тривалість технічних повторів; незалежної базової групи та статистичного порівняння немає.",
            }
        )
    return result


def _table6_limitations() -> list[dict[str, Any]]:
    return [
        {
            "limitation_class": "OBSERVED",
            "what_is_supported": "По два source-bound CI-спостереження оцінювачів для кожного канонічного стану та результати скінченних контрольованих змін EVAL-01/EVAL-02.",
            "evidence_status": "OBSERVED",
            "what_is_not_supported": "Повна семантична відповідність усім архітектурним зобов'язанням, runtime-поведінка, ідентичність розгортання або контроль упродовж життєвого циклу.",
            "evidence_sources": "Канонічні checkpoints і спостереження A0.3/A0.4; звіти та перевірені архіви EVAL-01/EVAL-02.",
        },
        {
            "limitation_class": "SYNTHETIC_ONLY",
            "what_is_supported": "Поведінка рішень методу P у восьми авторських синтетичних переходах TEST_ONLY із трьома технічними повторами на сценарій.",
            "evidence_status": "SYNTHETICALLY_VERIFIED",
            "what_is_not_supported": "Результативність методу P на канонічному переході A0.3→A0.4 або на незалежно відібраних реальних архітектурах.",
            "evidence_sources": "Сценарії MONO_E1_DEV_P_DECISIONS_V1, сирі записи та не незалежний еталон, оголошений автором.",
        },
        {
            "limitation_class": "ASSESSED_NOT_APPLIED",
            "what_is_supported": "Для запропонованих конфігурацій-кандидатів зафіксовано оцінку покриття: COMPLETE у шести сценаріях, UNKNOWN в одному та INCOMPLETE в одному.",
            "evidence_status": "OBSERVED_AS_ASSESSMENT",
            "what_is_not_supported": "Твердження, що кандидатні конфігурації активували або що вони поліпшили реальну архітектуру.",
            "evidence_sources": "Сирі записи методу P та повторно розрахований results_v1.json.",
        },
        {
            "limitation_class": "NOT_MEASURED",
            "what_is_supported": "Пакет явно фіксує NOT_MEASURED для фактичного покриття після адаптації в кожному технічному повторі.",
            "evidence_status": "NOT_MEASURED",
            "what_is_not_supported": "Фактичне покриття після адаптації, канонічне виконання B0/P або порівняння з участю людей для B1.",
            "evidence_sources": "Сирі записи методу P і похідна таблиця 3; офіційні ворота залишаються P_ALGORITHM_STATUS=NOT_READY, G1=INCOMPLETE, G4=NOT_AUTHORIZED.",
        },
        {
            "limitation_class": "OUTSIDE_SCOPE",
            "what_is_supported": "Пакет охоплює лише CI/статичну інспекцію вихідного коду та окремий синтетичний CI-трек рішень.",
            "evidence_status": "PROPOSED_MODEL_SCOPE_ONLY",
            "what_is_not_supported": "Перевірка розгортання/runtime, виробнича авторитетність, точність на популяції, статистично значуща перевага або емпірична валідація всього життєвого циклу.",
            "evidence_sources": "Дослідницький контекст, поточні ворота готовності та обмежені інвентарі доказів.",
        },
    ]


def _claim_matrix() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "CLAIM-A1",
            "scientific_statement": "On the pinned canonical A0.3 and A0.4 revisions, AC_PUBLIC_API and AC_MODULE_GRAPH each produced one source-bound COMPLIANT observation over the declared static app/modules scope.",
            "experimental_track": "A — canonical source-bound CI observations",
            "supporting_source_file": "architecture/acceptance/a1/a0_3_canonical_checkpoint.json; architecture/acceptance/a1/a0_4_canonical_checkpoint.json; corresponding observations",
            "supporting_metric_or_observation": "COMPLIANT; complete declared scope; 31 files and 185 imports for each recorded evaluator observation.",
            "verification_method": "mono_e1_a03_fitness_config.validate_project() source/checkpoint readback; observation-to-checkpoint comparison.",
            "evidence_strength": "OBSERVED — source-bound engineering evidence",
            "limitation": "One observation per evaluator/state and the declared static scope only; no semantic obligation denominator or runtime/deployment evidence.",
            "permitted_interpretation": "Both named CI controls executed successfully on the pinned states within their declared inspection scope.",
            "prohibited_interpretation": "The complete set of architectural obligations is covered throughout CI, deployment, and runtime.",
        },
        {
            "claim_id": "CLAIM-A2",
            "scientific_statement": "EVAL-01 and EVAL-02 produced the recorded binary evaluator outcomes on their finite applicable source-condition sets.",
            "experimental_track": "A — controlled evaluator studies",
            "supporting_source_file": "experiments/pilots/EVAL01_ANALYSIS_V1.json; experiments/pilots/EVAL02_ANALYSIS_V1.json; reports and raw archives",
            "supporting_metric_or_observation": "EVAL-01 F1=1.0 on 6 eligible conditions per evaluator; EVAL-02 F1=1.0 on 8 AC_PUBLIC_API and 6 AC_MODULE_GRAPH eligible conditions.",
            "verification_method": "Archive integrity validators; case-row binary-metric recalculation; report/CSV/analysis aggregate cross-check.",
            "evidence_strength": "OBSERVED — finite author-selected engineering conditions",
            "limitation": "Three technical calls per source condition are collapsed; finite author-selected cases; no population estimate or independent semantic review.",
            "permitted_interpretation": "The binary outputs matched the preregistered expectations on these applicable cases.",
            "prohibited_interpretation": "The evaluators are complete architecture oracles or have perfect diagnostic correspondence.",
        },
        {
            "claim_id": "CLAIM-A3",
            "scientific_statement": "EVAL-02 retained three diagnostic-expectation mismatches for missing_required_public_function / AC_PUBLIC_API while all 60 evaluator calls completed.",
            "experimental_track": "A — EVAL-02 diagnostic behavior",
            "supporting_source_file": "experiments/pilots/EVAL02_REPORT_V1.md; experiments/pilots/EVAL02_POST_EXPERIMENT_ERRATUM_V1.md; EVAL02 raw archive",
            "supporting_metric_or_observation": "Three repeats observed PUBLIC_INTERFACE_MISSING plus UNDECLARED_PUBLIC_INTERFACE; binary NON_COMPLIANT matched; runner exit status remained nonzero.",
            "verification_method": "validate_eval02_archive(); diagnostic repeat inventory and report/erratum readback.",
            "evidence_strength": "OBSERVED — preserved failure/deviation",
            "limitation": "The mismatch concerns finding-set correspondence on one mutation condition, not the binary metric.",
            "permitted_interpretation": "Binary classification matched while all three detailed diagnostic sets differed from the preregistered expected set.",
            "prohibited_interpretation": "EVAL-02 had no failures or diagnostic mismatches because F1 was 1.0.",
        },
        {
            "claim_id": "CLAIM-B1",
            "scientific_statement": "In MONO_E1_DEV_P_DECISIONS_V1, Method P selected the author-declared expected operation in all 24 recorded technical repetitions across eight distinct synthetic scenarios.",
            "experimental_track": "B — synthetic Method P DEVELOPMENT decisions",
            "supporting_source_file": "experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1/raw/; reference_v1.json; results_v1.json",
            "supporting_metric_or_observation": "24/24 operation matches; 8 scenarios × 3 technical repetitions.",
            "verification_method": "Pinned scorer replay from raw records on a temporary copy; raw manifest and input bundle digest verification.",
            "evidence_strength": "DERIVED — replayed synthetic records against a non-independent reference",
            "limitation": "The eight scenarios are authored synthetic fixtures; the reference is AUTHOR_DECLARED and NON_INDEPENDENT.",
            "permitted_interpretation": "Method P correctly selected the declared operation in these recorded DEVELOPMENT technical repetitions.",
            "prohibited_interpretation": "Method P has been proven superior to B0 in production or on canonical A0.4.",
        },
        {
            "claim_id": "CLAIM-B2",
            "scientific_statement": "The proposed candidate received a COMPLETE coverage assessment in six synthetic scenarios, UNKNOWN in one, and INCOMPLETE in one.",
            "experimental_track": "B — synthetic candidate assessment",
            "supporting_source_file": "experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1/raw/; results_v1.json",
            "supporting_metric_or_observation": "Candidate coverage assessment status by scenario: COMPLETE 6, UNKNOWN 1, INCOMPLETE 1.",
            "verification_method": "Raw scorer replay; dashboard scenario summaries compared with replayed result records.",
            "evidence_strength": "DERIVED — synthetic assessment output",
            "limitation": "The candidate was not applied and re-evaluated; this status is not measured post-adaptation coverage.",
            "permitted_interpretation": "The proposed candidate received a complete coverage assessment in the specified synthetic scenarios.",
            "prohibited_interpretation": "Applying Method P experimentally improved actual architectural coverage.",
        },
        {
            "claim_id": "CLAIM-B3",
            "scientific_statement": "D2 preserves an expected HOLD / observed REJECT governance mismatch in all three repetitions although the proposed operation was HOLD each time.",
            "experimental_track": "B — synthetic governance behavior",
            "supporting_source_file": "experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1/raw/D2_method_p_rep_01.json; D2 repetitions 02–03; results_v1.json",
            "supporting_metric_or_observation": "Operation agreement 3/3; governance agreement 0/3; combined classification INCORRECT 3/3.",
            "verification_method": "Pinned scorer replay; expected/observed operation and governance cross-tabulation.",
            "evidence_strength": "OBSERVED — mismatch retained in synthetic records",
            "limitation": "D2 is synthetic and compared with a non-independent author-declared label.",
            "permitted_interpretation": "The recorded fail-closed REJECT differed from the declared HOLD reference despite the same HOLD operation.",
            "prohibited_interpretation": "A protective REJECT is agreement with the declared HOLD reference.",
        },
        {
            "claim_id": "CLAIM-B4",
            "scientific_statement": "Actual post-adaptation coverage was not measured in any of the 24 Method P technical repetitions.",
            "experimental_track": "B — post-adaptation outcome boundary",
            "supporting_source_file": "experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1/results_v1.json; raw Method P records",
            "supporting_metric_or_observation": "NOT_MEASURED 24/24; no candidate configuration was applied and re-evaluated.",
            "verification_method": "Raw scorer replay and exact comparison with dashboard actual_post_adaptation_coverage distribution.",
            "evidence_strength": "NOT_MEASURED — explicitly unavailable outcome",
            "limitation": "Candidate assessment output does not substitute for post-application observation.",
            "permitted_interpretation": "The experiment did not measure actual post-adaptation coverage.",
            "prohibited_interpretation": "Candidate assessment values are measured post-adaptation coverage.",
        },
        {
            "claim_id": "CLAIM-C1",
            "scientific_statement": "The retained DEVELOPMENT run recorded descriptive Method P durations over 24 technical repetitions; these do not estimate a B0 comparison.",
            "experimental_track": "B — execution cost",
            "supporting_source_file": "experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1/raw/*_method_p_rep_*.json; results_v1.json",
            "supporting_metric_or_observation": "Mean 451.401 ms; median 460.321 ms; range 369.337–500.405 ms; n=24.",
            "verification_method": "Statistics recalculated from replayed raw duration_ns values via existing dashboard duration_summary().",
            "evidence_strength": "DERIVED — descriptive technical-repeat timing",
            "limitation": "Timer covers bundle verification through run_adaptation result construction; no B0 arm, application, post-adaptation evaluation, CPU or memory comparison.",
            "permitted_interpretation": "The saved technical-repeat duration distribution can be described within its measurement boundary.",
            "prohibited_interpretation": "Method P is statistically faster or has lower overhead than an independently executed baseline.",
        },
        {
            "claim_id": "CLAIM-C2",
            "scientific_statement": "No canonical A0.3/A0.4 B0/P experiment, simulated human B1 comparison, deployment/runtime validation, or actual post-adaptation remeasurement is included.",
            "experimental_track": "A and B — scope boundary",
            "supporting_source_file": "docs/RESEARCH_CONTEXT.md; current P/G1/G4 gates; MONO_E1_DEV_P_DECISIONS_V1 execution manifest",
            "supporting_metric_or_observation": "P_ALGORITHM_STATUS=NOT_READY; G1=INCOMPLETE; G4=NOT_AUTHORIZED; MONO_E1=NO_GO; actual post-adaptation coverage NOT_MEASURED.",
            "verification_method": "Canonical DEVELOPMENT configuration validator and retained execution manifest; no method or application execution.",
            "evidence_strength": "NOT_MEASURED / NOT_AUTHORIZED",
            "limitation": "This bounded package cannot resolve the external authority and independent-review prerequisites.",
            "permitted_interpretation": "The empirical scope is limited to source-bound CI observations and separate synthetic decision records.",
            "prohibited_interpretation": "The package validates the general lifecycle-wide model or establishes official MONO-E1 readiness.",
        },
    ]


def _figure_metadata(
    dataset: Any,
    generated_dir: Path,
    *,
    figure_hash_dir: Path | None = None,
) -> list[dict[str, Any]]:
    figure_builders = (
        ("coverage_assessment_transitions", coverage_figure),
        ("operations_and_governance", operations_governance_figure),
        ("execution_duration_by_operation_scenario", duration_figure),
    )
    claim_ids = {
        "coverage_assessment_transitions": ["CLAIM-B2", "CLAIM-B4"],
        "operations_and_governance": ["CLAIM-B1", "CLAIM-B3"],
        "execution_duration_by_operation_scenario": ["CLAIM-C1"],
    }
    metadata: list[dict[str, Any]] = []
    for index, (figure_id, builder) in enumerate(figure_builders, start=1):
        figure = builder(dataset)
        try:
            title = figure._suptitle.get_text() if figure._suptitle is not None else ""
            axis_labels = [
                [label.get_text() for label in axis.get_xticklabels() if label.get_text()]
                for axis in figure.axes
            ]
            y_labels = [axis.get_ylabel() for axis in figure.axes if axis.get_ylabel()]
            captions = [text.get_text() for text in figure.texts if text.get_text()]
            captions.extend(
                axis.get_title(loc=location)
                for axis in figure.axes
                for location in ("left", "center", "right")
                if axis.get_title(loc=location)
            )
            filenames = FIGURE_FILES[figure_id]
            hash_dir = generated_dir if figure_hash_dir is None else figure_hash_dir
            figure_asset_hashes = {
                filename: _sha256_file(hash_dir / filename) for filename in filenames
            }
            if not title or not all(
                (generated_dir / filename).is_file() and (hash_dir / filename).is_file()
                for filename in filenames
            ):
                raise EvidencePackageError(f"Figure export is incomplete for {figure_id}")
            if figure_id == "coverage_assessment_transitions" and not any(
                "NOT_MEASURED" in caption for caption in captions
            ):
                raise EvidencePackageError(
                    "Coverage figure does not distinguish assessment from measurement"
                )
            if figure_id == "operations_and_governance" and not any(
                "AUTHOR_DECLARED" in caption and "NON_INDEPENDENT" in caption
                for caption in captions
            ):
                raise EvidencePackageError(
                    "Decision figure does not identify its non-independent reference"
                )
            metadata.append(
                {
                    "figure_id": f"FIG-{index:02d}",
                    "file_stem": figure_id,
                    "title": title,
                    "x_axis_or_columns": axis_labels,
                    "y_axis_labels": y_labels,
                    "caption_and_footnotes": captions,
                    "data_unit": "one synthetic scenario"
                    if index <= 2
                    else "one technical repetition",
                    "source_data": "Raw Method P records replayed into results_v1.json; dashboard preflight PASS.",
                    "figure_files": figure_asset_hashes,
                    "claim_ids": claim_ids[figure_id],
                    "monograph_interpretation": {
                        "coverage_assessment_transitions": "Categorical current/candidate assessments and decision states; not measured post-adaptation change.",
                        "operations_and_governance": "Scenario-level expected/observed operation and governance relative to an AUTHOR_DECLARED, NON_INDEPENDENT reference; D2 mismatch retained.",
                        "execution_duration_by_operation_scenario": "Recorded technical repetitions by scenario and operation; no independent baseline comparison.",
                    }[figure_id],
                }
            )
        finally:
            import matplotlib.pyplot as plt

            plt.close(figure)
    return metadata


def _build_package(
    root: Path = ROOT,
    *,
    figure_hash_dir: Path | None = None,
) -> tuple[dict[str, Any], str, dict[str, bytes]]:
    """Validate sources and derive tables, report, figure metadata and temporary dashboard renders."""

    if root.resolve() != ROOT.resolve():
        raise EvidencePackageError(
            "The canonical verifier currently requires the repository checkout root"
        )
    dataset = load_dataset(RESULTS_PATH)
    validate_publication_export_readiness(dataset)
    if (
        dataset.integrity.expected_files == 0
        or dataset.integrity.expected_files != dataset.integrity.verified_files
    ):
        raise EvidencePackageError(
            "Dashboard preflight did not verify a complete non-empty checksum inventory"
        )
    issues = report_consistency_issues(dataset)
    if issues:
        raise EvidencePackageError("Dashboard report consistency failed: " + "; ".join(issues))

    replay = _replay_method_p(root, dataset)
    replayed_metrics = summary_metrics(dataset)
    if (
        replayed_metrics["scenario_count"] != 8
        or replayed_metrics["technical_repetition_count"] != 24
    ):
        raise EvidencePackageError(
            "Dashboard units do not preserve 8 scenarios and 24 technical repetitions"
        )
    if replayed_metrics["actual_post_adaptation_coverage_distribution"] != {"NOT_MEASURED": 24}:
        raise EvidencePackageError(
            "Actual post-adaptation coverage must remain NOT_MEASURED in all repetitions"
        )

    from experiments.execution.tooling.mono_e1_a03_fitness_config import validate_project

    canonical_validation = validate_project(root)
    if (
        canonical_validation.get("canonical_source_and_checkpoint_provenance") != "PASS"
        or canonical_validation.get("semantic_fitness_validity") != "UNKNOWN"
        or canonical_validation.get("method_p_execution_authorized") is not False
    ):
        raise EvidencePackageError("Canonical evidence validation changed or was not conclusive")
    evaluator_validation = _validate_evaluator_reports(root, canonical_validation)
    from experiments.pilots.validate_eval02_postrun import validate_eval02_archive

    eval02_validation = validate_eval02_archive(EVAL_ARTIFACTS["EVAL-02"]["archive"])
    if eval02_validation["execution_status"]["diagnostic_expectation_mismatches"] != 3:
        raise EvidencePackageError(
            "EVAL-02 post-run validator did not preserve three diagnostic mismatches"
        )

    raw_grouped = _raw_records_by_scenario(root)
    canonical_table = _canonical_rows(root, canonical_validation)
    synthetic_table1, table3, table4 = _scenario_and_governance_tables(root, dataset, raw_grouped)
    table1 = canonical_table + synthetic_table1
    table5 = _table5_cost(dataset)
    table6 = _table6_limitations()
    claims = _claim_matrix()

    with tempfile.TemporaryDirectory(prefix="mono-e1-publication-figures-") as temporary:
        generated_dir = Path(temporary)
        export_paths = export_publication_figures(dataset, generated_dir)
        if len(export_paths) != 6:
            raise EvidencePackageError(f"Expected six SVG/PNG files, exported {len(export_paths)}")
        figures = _figure_metadata(
            dataset,
            generated_dir,
            figure_hash_dir=figure_hash_dir,
        )
        figure_bytes = {path.name: path.read_bytes() for path in export_paths}

    metrics = summary_metrics(dataset)
    eval01_summary = evaluator_validation["EVAL-01"]
    eval02_summary = evaluator_validation["EVAL-02"]
    p_summary = {
        **replay,
        "dashboard_checksum_files_verified": dataset.integrity.verified_files,
        "dashboard_checksum_files_expected": dataset.integrity.expected_files,
        "dashboard_raw_inventory_and_report_consistency": "PASS",
        "scenario_count": metrics["scenario_count"],
        "technical_repetition_count": metrics["technical_repetition_count"],
        "operation_matches": f"{metrics['operation_match_count']}/{metrics['operation_evaluable_count']}",
        "combined_correct_incorrect_not_evaluable": [
            metrics["combined_correct_count"],
            metrics["combined_incorrect_count"],
            metrics["combined_not_evaluable_count"],
        ],
        "governance_distribution": metrics["governance_distribution"],
        "actual_post_adaptation_coverage": metrics["actual_post_adaptation_coverage_distribution"],
        "b0_synth_is_independent_arm": metrics["b0_synth"].get(
            "independently_executed_baseline_arm"
        ),
    }
    package = {
        "schema_version": 1,
        "package_id": PACKAGE_ID,
        "experimental_scope": {
            "track_A": "Source-bound canonical A0.3/A0.4 CI observations plus finite EVAL-01/EVAL-02 static evaluator control studies.",
            "track_B": "MONO_E1_DEV_P_DECISIONS_V1: eight distinct authored synthetic scenarios, three technical repetitions each, TEST_ONLY trust.",
            "tracks_are_combined_causally": False,
            "official_mono_e1_or_canonical_b0p_experiment": False,
            "actual_post_adaptation_coverage": "NOT_MEASURED",
        },
        "provenance": {
            "base_main_sha": BASE_MAIN_SHA,
            "canonical_states": [
                {
                    "state": "A0_3_GOVERNED_MODULE_GRAPH",
                    "source_sha": _read_json(
                        root / "architecture/acceptance/a1/a0_3_canonical_checkpoint.json"
                    ).get("source_sha"),
                    "application_tree_sha": _read_json(
                        root / "architecture/acceptance/a1/a0_3_canonical_checkpoint.json"
                    ).get("application_tree_sha"),
                },
                {
                    "state": "A0_4_REPORT_QUERY_PORT",
                    "source_sha": _read_json(
                        root / "architecture/acceptance/a1/a0_4_canonical_checkpoint.json"
                    )["source"]["source_sha"],
                    "application_tree_sha": _read_json(
                        root / "architecture/acceptance/a1/a0_4_canonical_checkpoint.json"
                    )["source"]["application_tree_sha"],
                },
            ],
            "a03_development_fitness_configuration_sha256": canonical_validation[
                "configuration_sha256"
            ],
            "p_execution_source_commit_sha": replay["execution_source_commit_sha"],
            "p_scorer_source_commit_sha": replay["scorer_source_commit_sha"],
            "p_reference_sha256": replay["reference_sha256"],
            "evaluator_archives": {
                "EVAL-01": eval01_summary["archive_sha256"],
                "EVAL-02": eval02_summary["archive_sha256"],
            },
        },
        "verification": {
            "method_p_raw_replay": p_summary,
            "canonical_source_and_checkpoint_validation": canonical_validation,
            "evaluator_control_validation": evaluator_validation,
            "eval02_postrun_validation": {
                "evidence_status": eval02_validation["execution_status"]["evidence_status"],
                "evaluator_invocation_failures": eval02_validation["execution_status"][
                    "evaluator_invocation_failures"
                ],
                "source_provenance_failures": eval02_validation["execution_status"][
                    "source_provenance_failures"
                ],
                "diagnostic_expectation_mismatches": eval02_validation["execution_status"][
                    "diagnostic_expectation_mismatches"
                ],
                "diagnostic_mismatch_repeats": eval02_validation["execution_status"][
                    "diagnostic_mismatch_repeats"
                ],
            },
            "dashboard_rows_match_replayed_results": "PASS",
            "figure_metadata_matches_validated_source_data": "PASS",
            "checked_in_figure_asset_sha256": "PASS",
        },
        "tables": {
            "table_1_scope": table1,
            "table_2_evaluators": _table2_evaluators(root, canonical_table, evaluator_validation),
            "table_3_method_p": table3,
            "table_4_governance": table4,
            "table_5_execution_cost": table5,
            "table_6_limitations": table6,
        },
        "claim_to_evidence": claims,
        "figure_to_claim": figures,
    }
    report = _render_ukrainian_report(package)
    return package, report, figure_bytes


def _table2_evaluators(
    root: Path,
    canonical_rows: list[dict[str, Any]],
    evaluator_validation: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for canonical in canonical_rows:
        rows.append(
            {
                "track": "A",
                "study": "CANONICAL_SOURCE_OBSERVATION",
                "architecture_state": canonical["architecture_state"],
                "evaluator_id": canonical["evaluator_id"],
                "outcome": canonical["outcome"],
                "tp": "NOT_APPLICABLE",
                "fp": "NOT_APPLICABLE",
                "tn": "NOT_APPLICABLE",
                "fn": "NOT_APPLICABLE",
                "f1": "NOT_MEASURED",
                "evaluable_conditions": 1,
                "excluded_or_not_evaluable_conditions": 0,
                "technical_calls": 1,
                "diagnostic_mismatches": 0,
                "source_identity": f"{canonical['source_commit_sha']} / app tree {canonical['application_tree_sha']}",
                "scope_and_limit": canonical["inspection_scope"] + "; " + canonical["limitations"],
            }
        )

    for experiment_id in ("EVAL-01", "EVAL-02"):
        analysis = _read_json(EVAL_ARTIFACTS[experiment_id]["analysis"])
        validation = evaluator_validation[experiment_id]
        for evaluator_id, metrics in analysis["evaluator_metrics"].items():
            matrix = metrics["confusion_matrix"]
            if experiment_id == "EVAL-01":
                evaluable = metrics["evaluable_labeled_cases"]
                excluded = metrics["not_evaluable_catalog_cases"]
                calls = validation["technical_calls"] // 2
                mismatch_count = 0
                scope_limit = "Одна базова версія A0.4; три технічні виклики на умову згорнуто до одного випадку; відсутня очікувана можливість має статус NOT_EVALUABLE і виключається. Лише скінченні умови, обрані автором."
            else:
                evaluable = metrics["evaluable_binary_applicable_cases"]
                excluded = metrics["excluded_from_matrix_cases"]
                calls = validation["technical_calls"] // 2
                mismatch_count = 3 if evaluator_id == "AC_PUBLIC_API" else 0
                scope_limit = (
                    "Десять умов вихідного коду; три виклики на умову; бінарні метрики охоплюють лише застосовні умови. "
                    f"Кількість за застосовністю: {json.dumps(metrics['evaluator_applicability_counts'], sort_keys=True)}. "
                    "Три розбіжності набору діагностик AC_PUBLIC_API збережено; вони не змінюють бінарну класифікацію NON_COMPLIANT."
                )
            rows.append(
                {
                    "track": "A",
                    "study": experiment_id,
                    "architecture_state": "A0_4_REPORT_QUERY_PORT",
                    "evaluator_id": evaluator_id,
                    "outcome": "FINITE_BINARY_CASE_METRICS",
                    "tp": matrix["tp"],
                    "fp": matrix["fp"],
                    "tn": matrix["tn"],
                    "fn": matrix["fn"],
                    "f1": metrics["f1"],
                    "evaluable_conditions": evaluable,
                    "excluded_or_not_evaluable_conditions": excluded,
                    "technical_calls": calls,
                    "diagnostic_mismatches": mismatch_count,
                    "source_identity": "A0.4 source commit d3101c0d3aa9b7b709253b6ec7518416f05f65b9 / app tree 007196f68652bc13f6798805793ffdfae96f95f7",
                    "scope_and_limit": scope_limit,
                }
            )
    return rows


def _render_ukrainian_report(package: dict[str, Any]) -> str:
    tables = package["tables"]
    timing = tables["table_5_execution_cost"][0]
    table1_columns = [
        ("track", "Трек"),
        ("architecture_state", "Стан / сценарій"),
        ("architecture_before", "Архітектура до переходу"),
        ("architecture_after", "Архітектура після переходу"),
        ("source_commit_sha", "Ідентифікатор джерела"),
        ("evaluator_id", "Оцінювачі"),
        ("inspection_scope", "Обсяг оцінювання"),
        ("lifecycle_stage", "Етап життєвого циклу"),
        ("evidence_source", "Джерело доказів"),
        ("limitations", "Обмеження"),
    ]
    table2_columns = [
        ("study", "Дослідження"),
        ("architecture_state", "Стан"),
        ("evaluator_id", "Оцінювач"),
        ("outcome", "Результат"),
        ("tp", "TP"),
        ("fp", "FP"),
        ("tn", "TN"),
        ("fn", "FN"),
        ("f1", "F1"),
        ("evaluable_conditions", "Придатні умови"),
        ("excluded_or_not_evaluable_conditions", "Виключені / NOT_EVALUABLE"),
        ("technical_calls", "Технічні виклики"),
        ("diagnostic_mismatches", "Діагностичні розбіжності"),
        ("scope_and_limit", "Обсяг і обмеження"),
    ]
    table3_columns = [
        ("scenario_id", "Сценарій"),
        ("expected_operation_author_declared", "Очікувана операція¹"),
        ("observed_operation", "Спостережена операція"),
        ("expected_governance_author_declared", "Очікуване врядування¹"),
        ("observed_governance", "Спостережене врядування"),
        ("operation_agreement", "Збіг операції"),
        ("combined_reference_agreement", "Збіг класифікації"),
        ("evidence_status", "Статус доказів"),
        ("candidate_coverage_assessment", "Оцінка конфігурації-кандидата"),
        ("actual_post_adaptation_coverage", "Фактичне покриття після адаптації"),
    ]
    table4_columns = [
        ("expected_governance", "Очікуване¹"),
        ("observed_governance", "Спостережене"),
        ("technical_repetition_count", "n технічних повторів"),
        ("matching_repetitions", "Збіг"),
        ("mismatching_repetitions", "Розбіжність"),
        ("scenario_ids", "Сценарії"),
        ("governance_reason_codes", "Коди причин"),
        ("interpretation", "Інтерпретація"),
    ]
    table5_columns = [
        ("observed_operation", "Операція"),
        ("technical_repetitions_n", "n технічних вимірів"),
        ("distinct_scenarios_n", "n сценаріїв"),
        ("minimum_ms", "Мінімум, мс"),
        ("median_ms", "Медіана, мс"),
        ("mean_ms", "Середнє, мс"),
        ("sample_standard_deviation_ms", "Вибіркове SD, мс"),
        ("maximum_ms", "Максимум, мс"),
    ]
    table6_columns = [
        ("limitation_class", "Категорія"),
        ("what_is_supported", "Що спостерігалося або оцінювалося"),
        ("evidence_status", "Статус доказу"),
        ("what_is_not_supported", "Що не підтверджується"),
    ]
    figure_links = [
        (
            "Рис. 1 — оцінювання поточної та запропонованої конфігурацій",
            "coverage_assessment_transitions.svg",
            "FIG-01",
        ),
        (
            "Рис. 2 — очікувані та спостережені операції й рішення врядування",
            "operations_and_governance.svg",
            "FIG-02",
        ),
        (
            "Рис. 3 — тривалість виконання за операціями та сценаріями",
            "execution_duration_by_operation_scenario.svg",
            "FIG-03",
        ),
    ]
    figure_block = "\n\n".join(
        f"**{title}.** Технічний файл: [SVG](../experiments/pilots/mono_e1_ci_evidence_v1/{filename}); відповідність твердженням описана в [карті рисунків](../experiments/pilots/mono_e1_ci_evidence_v1/figure_to_claim_map_v1.json)."
        for title, filename, _figure_id in figure_links
    )
    return f"""# Експериментальні результати для обмеженого CI-дослідження

## 1. Мета експериментального дослідження

Мета полягає у відтворюваній перевірці двох окремих масивів уже зібраних доказів: (А) виконання статичних функцій придатності на канонічних станах A0.3 та A0.4 і контрольованих умовах EVAL-01/EVAL-02; (Б) рішень DEVELOPMENT-реалізації методу P у восьми синтетичних сценаріях. Емпіричний обсяг обмежено CI та статичною перевіркою вихідного коду. Ці треки не утворюють спільного причинного експерименту.

Пакет перевіряє цілісність вихідних записів, повторно розраховує результати методом P на тимчасовій копії незмінних сирих записів, звіряє агрегати EVAL-01/EVAL-02 з машинними таблицями, а також відновлює метадані рисунків із валідованих даних і перевіряє SHA-256 збережених SVG/PNG. Байти Matplotlib-рендерингу залежать від платформи й не порівнюються між операційними системами. Верифікатор не запускає метод P на канонічному переході, не застосовує кандидат і не виконує повторного експерименту.

## 2. Об'єкт, предмет та умови експерименту

У треку А розглянуто стани `A0_3_GOVERNED_MODULE_GRAPH` та `A0_4_REPORT_QUERY_PORT`. У кожному збережено по одному source-bound спостереженню `AC_PUBLIC_API` і `AC_MODULE_GRAPH` для визначеного статичного обсягу `app/modules`. Окремі EVAL-01 та EVAL-02 перевіряють два оцінювачі на скінченних наборах контрольованих змін коду.

У треку Б розглянуто `MONO_E1_DEV_P_DECISIONS_V1`: вісім відмінних синтетичних переходів для операцій RETAIN, ADD, REPLACE і HOLD. Для кожного сценарію збережено три технічні повтори. Еталонні очікування мають статус AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT. Усі набори, оцінювачі та довірчі припущення цього треку є синтетичними TEST_ONLY.

{_markdown_table(tables["table_1_scope"], table1_columns)}

Для канонічних спостережень поля переходу не застосовуються. Описові формулювання архітектури до та після синтетичного переходу збережено мовою вихідного сценарію; коди, ідентифікатори й назви артефактів наведено без перекладу.

## 3. Методика проведення експерименту

Для одиниці аналізу розрізнено канонічне спостереження, evaluator-by-source-condition в EVAL-01/EVAL-02, синтетичний сценарій та технічний повтор. Повтори оцінювачів згортаються на рівні умови, а три повтори одного сценарію методу P не збільшують кількість незалежних сценаріїв. Мітки в синтетичному треку не є незалежним еталоном.

Цілісність MONO_E1_DEV_P_DECISIONS_V1 перевірено за manifest сирих записів, SHA-256 усіх перелічених файлів, вісьмома архівами V3-входів, їхніми дайджестами та повторним запуском збереженого scorer-коду на тимчасовій копії `run_v1`. Похідні `results_v1.json`, `report_v1.md` і `score_manifest.json` мають повністю збігтися з повторно розрахованими файлами. Дашбордова передумова повторно завантажує доказовий набір і вимагає непорожній повний checksum-інвентар.

Для EVAL-01/EVAL-02 агрегати перераховано з рівня evaluator-by-source-condition, а потім звірено з аналізом JSON, CSV, звітами й файлами у перевірених ZIP-архівах. Неоцінювані або виключені за застосовністю умови залишено видимими. У EVAL-02 три діагностичні розбіжності збережено як відхилення, навіть попри збіг бінарної класифікації.

## 4. Результати перевірки архітектурних функцій придатності

Канонічні спостереження A0.3 та A0.4 для `AC_PUBLIC_API` і `AC_MODULE_GRAPH` мають статус `COMPLIANT`; у кожному записі вказано повний задекларований статичний обсяг із 31 файлу та 185 імпортів. Це одиничні source-bound інженерні спостереження, а не оцінка точності або доказ повного семантичного покриття архітектурних зобов'язань.

У EVAL-01 обидва оцінювачі мають F1=1,0 на шести придатних умовах кожен; по одній умові `NOT_EVALUABLE` на оцінювач виключено з бінарної метрики. Всього збережено 42 виклики (три на кожну з 14 пар «оцінювач — умова»); повтори не є незалежними випадками.

У EVAL-02 F1=1,0 обчислено на восьми придатних умовах `AC_PUBLIC_API` і шести `AC_MODULE_GRAPH`. Для бінарної метрики виключено відповідно дві та чотири умови за незастосовністю або виходом за межі оцінювача. Виконано всі 60 викликів. Водночас для `missing_required_public_function` / `AC_PUBLIC_API` зафіксовано три невідповідності набору діагностичних кодів: очікуваний `PUBLIC_INTERFACE_MISSING` супроводжувався фактичним `UNDECLARED_PUBLIC_INTERFACE`. Спостережений бінарний результат `NON_COMPLIANT` збігся, однак діагностичні розбіжності і ненульовий код виконання збережено.

{_markdown_table(tables["table_2_evaluators"], table2_columns)}

{figure_block.split(chr(10) + chr(10))[0]}

## 5. Результати дослідження методу керованої адаптації

У межах восьми синтетичних сценаріїв спостережена операція збіглася з AUTHOR_DECLARED очікуванням у 24 із 24 технічних повторів. Комбінована класифікація «операція / врядування / семантична підтримка» правильна у 21 із 24 повторів. Різниця зумовлена сценарієм D2: операція HOLD спостерігалася тричі, але врядування повернуло REJECT замість очікуваного HOLD; усі три невідповідності збережено.

Кандидатна конфігурація отримала оцінку `COMPLETE` у шести сценаріях, `UNKNOWN` в одному та `INCOMPLETE` в одному. Кандидат не застосовували та не переоцінювали; фактичне покриття після адаптації залишається `NOT_MEASURED` у всіх 24 записах.

{_markdown_table(tables["table_3_method_p"], table3_columns)}

{figure_block.split(chr(10) + chr(10))[1]}

Урядування `ACCEPT` спостерігалося 18 разів і збіглося з очікуванням. `HOLD` спостерігалося тричі у D1 за неповних та невизначених доказів. `REJECT` спостерігалося тричі у D2 після зареєстрованих порушень інваріантів та відсутності матеріалізовного заміщення. Це захисне відхилення кандидата, але воно не є збігом з оголошеним еталоном HOLD.

{_markdown_table(tables["table_4_governance"], table4_columns)}

## 6. Аналіз обчислювальних витрат

Тривалість розраховано з наявних `duration_ns` для 24 технічних повторів. Межа вимірювання починається перед перевіркою V3-пакета методу і закінчується після повернення результату `run_adaptation`; підготовка фікстур і sidecar, архівування входів, оцінювання після застосування кандидата та повний час CI до виміру не належать. Для всіх повторів середнє становить {timing["mean_ms"]:.3f} мс, медіана — {timing["median_ms"]:.3f} мс, діапазон — {timing["minimum_ms"]:.3f}–{timing["maximum_ms"]:.3f} мс. Це описова статистика технічних повторів, а не висновок про перевагу над незалежно виконаною базовою конфігурацією.

{_markdown_table(tables["table_5_execution_cost"], table5_columns)}

{figure_block.split(chr(10) + chr(10))[2]}

## 7. Обговорення результатів

Наведені дані підтверджують відтворюваність конкретних збережених вихідних спостережень і поведінки DEVELOPMENT-конвеєра на заданих синтетичних входах. Для канонічних джерел підтверджено лише успішність двох названих статичних контролів у межах їхнього інспектованого обсягу. EVAL-01 та EVAL-02 описують обмежені набори контрольованих випадків, а не точність оцінювачів у популяції архітектур.

У синтетичному треку повний збіг операцій не означає повного збігу рішень врядування: D2 залишає видимою відмінність між захисним `REJECT` та еталонним `HOLD`. Оцінка кандидатної конфігурації також не є вимірюванням після її застосування. Тому ці результати є інженерним та синтетичним доказом поведінки реалізації в конкретних умовах, але не незалежною валідацією на канонічній архітектурі.

## 8. Обмеження дослідження

{_markdown_table(tables["table_6_limitations"], table6_columns)}

Еталонні мітки синтетичного треку визначені автором і не є незалежною ground truth. Не проведено незалежного реального порівняння B0/P, участі людей для B1 або застосування кандидата з повторним оцінюванням. Емпіричні дані не охоплюють розгортання чи runtime та не перевіряють загальність математичної моделі для інших стадій життєвого циклу. Статистичної значущості або причинної переваги не встановлено. Статуси дослідницьких воріт залишаються `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED`, `MONO_E1=NO_GO`.

## 9. Висновки

1. У канонічних джерелах A0.3 та A0.4 два визначені CI-оцінювачі завершили source-bound статичну перевірку з результатом `COMPLIANT` у повному задекларованому обсязі; це не підтверджує семантичного покриття всіх зобов'язань.
2. EVAL-01 та EVAL-02 мають F1=1,0 на зазначених скінченних наборах придатних умов; три діагностичні розбіжності EVAL-02 і всі виключені умови залишаються в звіті.
3. У восьми синтетичних сценаріях метод P обрав очікувані операції у 24/24 технічних повторів, тоді як комбінована класифікація збіглася у 21/24 через D2.
4. Кандидатні оцінки покриття є оцінками запропонованої конфігурації; фактичне покриття після адаптації не вимірювалося.
5. Тривалості подано як описові технічні виміри з визначеною межею; вони не доводять статистичної переваги над B0.
6. Емпірично перевірений обсяг обмежений статичними CI-спостереженнями та окремим синтетичним DEVELOPMENT-треком. Даних про канонічний експеримент B0/P, людську B1, розгортання або runtime немає.

¹ Очікування операції та врядування в треку Б походять з AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT reference; вони не є незалежною оцінкою правильності.

Машинні таблиці, матриця «твердження — доказ» і хешовані рисунки містяться в [пакеті доказів](../experiments/pilots/mono_e1_ci_evidence_v1/README.md). Команда `make test-monograph-evidence` виконує read-only перевірку; `python -m experiments.pilots.verify_monograph_evidence write-derived` відновлює лише похідні таблиці, звіт і рисунки, не змінюючи сирих експериментальних матеріалів.
"""


def _render_package_readme() -> str:
    return """# MONO-E1 CI evidence package

This package consolidates two distinct empirical tracks for the Ukrainian monograph: source-bound A0.3/A0.4 CI observations and finite EVAL-01/EVAL-02 evaluator controls (Track A), plus eight synthetic Method P DEVELOPMENT scenarios with 24 technical repetitions (Track B). It is not an official MONO-E1/B0/P experiment.

## Contents

- `evidence_tables_v1.json` — complete derived tables, provenance, verification results, claim matrix, and figure metadata.
- `table_01_scope_v1.csv` through `table_06_limitations_v1.csv` — publication tables.
- `claim_to_evidence_v1.csv` — claim IDs, evidence strength, permitted/prohibited interpretations, and verification routes.
- `figure_to_claim_map_v1.json` — figure titles, axes, captions, exact claim mapping, source-data boundary, and SHA-256 for each existing dashboard export.
- `coverage_assessment_transitions.{svg,png}`, `operations_and_governance.{svg,png}`, `execution_duration_by_operation_scenario.{svg,png}` — exports from the existing read-only dashboard figure exporter; no new visualization logic.
- `../../../docs/MONO_E1_CI_EXPERIMENTAL_EVIDENCE_REPORT_UA.md` — Ukrainian monograph-ready report.

## Reproduce and verify

```bash
make test-monograph-evidence
```

The read-only verifier validates the P raw manifest and all 57 run checksums, verifies eight V3 input archives, reruns the pinned scorer on a temporary copy, compares P results/report/score manifest, checks canonical A0.3/A0.4 source and evaluator identities, recalculates EVAL binary metrics from case rows, verifies report/CSV/archive parity, and derives figure titles, axes and captions from validated source data. It verifies checked-in SVG/PNG assets through the SHA-256 values in the evidence table. Matplotlib render bytes can vary across platforms, so verification does not require regenerated image bytes to match byte-for-byte. It writes no experiment or publication files.

To regenerate only derived tables, report, and dashboard-export figures after source evidence changes:

```bash
uv run --frozen --extra dev --with-requirements research_dashboard/requirements.lock \\
  python -m experiments.pilots.verify_monograph_evidence write-derived
```

`write-derived` never executes Method P or evaluator studies and never edits retained raw records, manifests, references, canonical checkpoints, EVAL archives, G1/G4, or readiness flags.

## Scientific boundary

Three technical repetitions per synthetic scenario are not independent scenarios. The reference is AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT. Candidate coverage is an assessment, not an applied outcome; actual post-adaptation coverage is `NOT_MEASURED`. D2's expected HOLD / observed REJECT and all three EVAL-02 diagnostic mismatches remain explicit. No canonical B0/P execution, human B1 comparison, production approval, deployment/runtime observation, or statistical superiority is claimed.
"""


def _all_output_bytes(
    package: dict[str, Any], report: str, figures: dict[str, bytes]
) -> dict[Path, bytes]:
    outputs: dict[Path, bytes] = {
        PACKAGE_DIR / "evidence_tables_v1.json": _json_bytes(package),
        PACKAGE_DIR / "figure_to_claim_map_v1.json": _json_bytes(package["figure_to_claim"]),
        PACKAGE_DIR / "README.md": _render_package_readme().encode("utf-8"),
        REPORT_PATH: report.encode("utf-8"),
    }
    for key, filename in TABLE_FILES.items():
        outputs[PACKAGE_DIR / filename] = _csv_bytes(
            package["claim_to_evidence"] if key == "claim_to_evidence" else package["tables"][key]
        )
    outputs.update({PACKAGE_DIR / name: payload for name, payload in figures.items()})
    return outputs


def verify_package() -> dict[str, Any]:
    """Verify source evidence, exact text outputs, and checked-in figure asset digests read-only."""

    package, report, figures = _build_package(ROOT, figure_hash_dir=PACKAGE_DIR)
    outputs = _all_output_bytes(package, report, figures)
    missing = [path.relative_to(ROOT).as_posix() for path in outputs if not path.is_file()]
    if missing:
        raise EvidencePackageError("Derived package files are missing: " + ", ".join(missing))
    rendered_figure_paths = {
        PACKAGE_DIR / filename for filenames in FIGURE_FILES.values() for filename in filenames
    }
    mismatched = [
        path.relative_to(ROOT).as_posix()
        for path, expected in outputs.items()
        if path not in rendered_figure_paths and path.read_bytes() != expected
    ]
    if mismatched:
        raise EvidencePackageError(
            "Derived publication artifacts differ from verified source evidence: "
            + ", ".join(mismatched)
            + ". Run write-derived only after reviewing the source changes."
        )
    return {
        "status": "PASS",
        "package_id": PACKAGE_ID,
        "base_main_sha": BASE_MAIN_SHA,
        "verified_derived_files": len(outputs),
        "p_raw_files_verified": package["verification"]["method_p_raw_replay"][
            "raw_record_files_verified"
        ],
        "p_input_bundle_archives_verified": package["verification"]["method_p_raw_replay"][
            "input_bundle_archives_verified"
        ],
        "p_raw_checksum_files_verified": package["verification"]["method_p_raw_replay"][
            "dashboard_checksum_files_verified"
        ],
        "canonical_source_pair": "PASS",
        "eval01_calls": package["verification"]["evaluator_control_validation"]["EVAL-01"][
            "technical_calls"
        ],
        "eval02_calls": package["verification"]["evaluator_control_validation"]["EVAL-02"][
            "technical_calls"
        ],
        "eval02_diagnostic_mismatches": package["verification"]["evaluator_control_validation"][
            "EVAL-02"
        ]["diagnostic_mismatches"],
        "p_scenario_count": package["verification"]["method_p_raw_replay"]["scenario_count"],
        "p_technical_repetition_count": package["verification"]["method_p_raw_replay"][
            "technical_repetition_count"
        ],
        "p_actual_post_adaptation_coverage": "NOT_MEASURED",
        "official_mono_e1_b0p_experiment": False,
    }


def write_derived_package() -> dict[str, Any]:
    """Write deterministic tables, report, and figures only; preserved experiment evidence is read-only."""

    package, report, figures = _build_package(ROOT)
    outputs = _all_output_bytes(package, report, figures)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return {
        "status": "WRITTEN_DERIVED_FILES_ONLY",
        "package_id": PACKAGE_ID,
        "file_count": len(outputs),
        "raw_experiment_artifacts_modified": False,
        "files": [path.relative_to(ROOT).as_posix() for path in sorted(outputs)],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="read-only evidence and derived-artifact verification")
    subparsers.add_parser(
        "write-derived",
        help="write deterministic publication tables/report/figures; never alter source evidence",
    )
    args = parser.parse_args(argv)
    try:
        result = verify_package() if args.command == "verify" else write_derived_package()
    except (
        DashboardDataError,
        EvidencePackageError,
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
    ) as error:
        print(
            json.dumps(
                {"status": "INVALID", "error": f"{type(error).__name__}: {error}"},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
