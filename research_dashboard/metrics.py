"""Descriptive calculations kept outside the dashboard presentation layer."""

from __future__ import annotations

import json
import math
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from research_dashboard.data import ExperimentDataset

COVERAGE_STATUSES = ("COMPLETE", "INCOMPLETE", "UNKNOWN")
OPERATIONS = ("retain", "add", "replace", "hold")
GOVERNANCE_RESULTS = ("ACCEPT", "HOLD", "REJECT")


def repetition_rows(dataset: ExperimentDataset) -> list[dict[str, Any]]:
    """Return the retained technical observations without collapsing repeats."""

    return list(dataset.results["technical_repetition_results"])


def _scenario_catalog_by_id(dataset: ExperimentDataset) -> dict[str, dict[str, Any]]:
    return {
        row["scenario_id"]: row
        for row in dataset.scenario_catalog.get("scenarios", [])
        if isinstance(row, dict) and isinstance(row.get("scenario_id"), str)
    }


def _scenario_result_by_id(dataset: ExperimentDataset) -> dict[str, dict[str, Any]]:
    return {row["scenario_id"]: row for row in dataset.results["scenario_results"]}


def repetitions_by_scenario(dataset: ExperimentDataset) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in repetition_rows(dataset):
        grouped[row["scenario_id"]].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: row["repetition"])
    return dict(grouped)


def _consensus(values: list[str]) -> str:
    if not values:
        return "NO DATA"
    distinct = set(values)
    return values[0] if len(distinct) == 1 else "MIXED"


def scenario_rows(dataset: ExperimentDataset) -> list[dict[str, Any]]:
    """Build one descriptive row per catalog/result scenario, including empty cases."""

    source_results = _scenario_result_by_id(dataset)
    catalog = _scenario_catalog_by_id(dataset)
    grouped = repetitions_by_scenario(dataset)
    scenario_ids = list(catalog)
    scenario_ids.extend(item for item in source_results if item not in catalog)
    rows: list[dict[str, Any]] = []

    for scenario_id in scenario_ids:
        repetitions = grouped.get(scenario_id, [])
        source_row = source_results.get(scenario_id, {})
        catalog_row = catalog.get(scenario_id, {})
        initial_statuses = [row["pre_adaptation_coverage"]["status"] for row in repetitions]
        candidate_statuses = [
            row["candidate_configuration_coverage"]["status"] for row in repetitions
        ]
        observed_operations = [row["proposed_operation"] for row in repetitions]
        observed_governance = [row["governance_result"] for row in repetitions]
        classifications = [row["classification"] for row in repetitions]
        expected_operations = [row["expected_operation"] for row in repetitions]
        expected_governance = [row["expected_governance"] for row in repetitions]
        if not expected_operations and source_row.get("expected_operation"):
            expected_operations = [source_row["expected_operation"]]
        if not expected_governance and source_row.get("expected_governance"):
            expected_governance = [source_row["expected_governance"]]

        if not repetitions:
            correctness = "NO DATA"
        elif all(value == "CORRECT" for value in classifications):
            correctness = "MATCH"
        elif any(value == "INCORRECT" for value in classifications):
            correctness = "MISMATCH"
        elif all(value == "NOT_EVALUABLE" for value in classifications):
            correctness = "NOT EVALUABLE"
        else:
            correctness = "MIXED"

        initial_status = _consensus(initial_statuses)
        candidate_status = _consensus(candidate_statuses)
        operation = _consensus(observed_operations)
        governance = _consensus(observed_governance)
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario_group": catalog_row.get("group", "UNAVAILABLE"),
                "architecture_before": catalog_row.get("architecture_before", "UNAVAILABLE"),
                "architecture_after": catalog_row.get("architecture_after", "UNAVAILABLE"),
                "obligations": catalog_row.get("obligations", []),
                "initial_configuration": catalog_row.get("initial_fitness_configuration", {}),
                "current_coverage": initial_status,
                "operation": operation.upper() if operation in OPERATIONS else operation,
                "candidate_coverage": candidate_status,
                "governance": governance,
                "expected_operation": (
                    _consensus(expected_operations).upper()
                    if expected_operations
                    else "UNAVAILABLE"
                ),
                "expected_governance": (
                    _consensus(expected_governance) if expected_governance else "UNAVAILABLE"
                ),
                "correctness": correctness,
                "repetition_count": len(repetitions),
                "correct_count": sum(value == "CORRECT" for value in classifications),
                "incorrect_count": sum(value == "INCORRECT" for value in classifications),
                "not_evaluable_count": sum(value == "NOT_EVALUABLE" for value in classifications),
                "candidate_transition_emphasized": (
                    initial_status == "INCOMPLETE"
                    and candidate_status == "COMPLETE"
                    and operation in {"add", "replace"}
                ),
            }
        )
    return rows


def summary_metrics(dataset: ExperimentDataset) -> dict[str, Any]:
    """Recalculate decision metrics from the repetition-level records."""

    repetitions = repetition_rows(dataset)
    operation_evaluable = [
        row
        for row in repetitions
        if row.get("expected_operation") is not None and row.get("proposed_operation") is not None
    ]
    operation_matches = sum(
        row["expected_operation"] == row["proposed_operation"] for row in operation_evaluable
    )
    governance_evaluable = [
        row
        for row in repetitions
        if row.get("expected_governance") is not None and row.get("governance_result") is not None
    ]
    governance_matches = sum(
        row["expected_governance"] == row["governance_result"] for row in governance_evaluable
    )
    correct = sum(row["classification"] == "CORRECT" for row in repetitions)
    incorrect = sum(row["classification"] == "INCORRECT" for row in repetitions)
    not_evaluable = sum(row["classification"] == "NOT_EVALUABLE" for row in repetitions)
    governance_distribution = dict(
        sorted(Counter(row["governance_result"] for row in repetitions).items())
    )
    actual_coverage_distribution = dict(
        sorted(
            Counter(row["actual_post_adaptation_coverage"]["status"] for row in repetitions).items()
        )
    )

    return {
        "scenario_count": len(dataset.results["scenario_results"]),
        "technical_repetition_count": len(repetitions),
        "operation_match_count": operation_matches,
        "operation_evaluable_count": len(operation_evaluable),
        "operation_match_rate": (
            operation_matches / len(operation_evaluable) if operation_evaluable else None
        ),
        "governance_match_count": governance_matches,
        "governance_evaluable_count": len(governance_evaluable),
        "combined_correct_count": correct,
        "combined_incorrect_count": incorrect,
        "combined_not_evaluable_count": not_evaluable,
        "combined_evaluable_count": correct + incorrect,
        "combined_match_rate": correct / (correct + incorrect) if correct + incorrect else None,
        "governance_distribution": governance_distribution,
        "execution_failure_count": dataset.results.get("summary_counts", {}).get(
            "execution_failures"
        ),
        "actual_post_adaptation_coverage_distribution": actual_coverage_distribution,
        "b0_synth": dataset.results.get("b0_synth_vs_method_p", {}),
    }


def confusion_matrix(
    dataset: ExperimentDataset,
    decision: str,
) -> tuple[list[str], list[list[int]]]:
    """Return expected-row/observed-column counts for operations or governance."""

    if decision == "operation":
        categories = list(OPERATIONS)
        expected_key = "expected_operation"
        observed_key = "proposed_operation"
    elif decision == "governance":
        categories = list(GOVERNANCE_RESULTS)
        expected_key = "expected_governance"
        observed_key = "governance_result"
    else:
        raise ValueError("decision must be 'operation' or 'governance'.")

    indexes = {value: index for index, value in enumerate(categories)}
    matrix = [[0 for _ in categories] for _ in categories]
    for row in repetition_rows(dataset):
        expected = row.get(expected_key)
        observed = row.get(observed_key)
        if expected in indexes and observed in indexes:
            matrix[indexes[expected]][indexes[observed]] += 1
    return categories, matrix


def coverage_transition_rows(dataset: ExperimentDataset) -> list[dict[str, Any]]:
    """Return categorical current-to-candidate transitions at scenario level."""

    return scenario_rows(dataset)


def mismatch_rows(dataset: ExperimentDataset) -> list[dict[str, Any]]:
    """Return repetition records the scorer classified as incorrect or not evaluable."""

    return [row for row in repetition_rows(dataset) if row["classification"] != "CORRECT"]


def duration_rows(
    dataset: ExperimentDataset,
    operations: set[str] | None = None,
    scenario_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Convert nanosecond measurements to milliseconds and preserve missing values."""

    rows: list[dict[str, Any]] = []
    for row in repetition_rows(dataset):
        operation = row["proposed_operation"]
        scenario_id = row["scenario_id"]
        if operations is not None and operation not in operations:
            continue
        if scenario_ids is not None and scenario_id not in scenario_ids:
            continue
        duration_ns = row.get("duration_ns")
        duration_ms = duration_ns / 1_000_000 if isinstance(duration_ns, (int, float)) else None
        rows.append(
            {
                "scenario_id": scenario_id,
                "repetition": row["repetition"],
                "operation": operation,
                "duration_ns": duration_ns,
                "duration_ms": duration_ms,
            }
        )
    return rows


def duration_summary(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    """Return descriptive duration statistics without imputing missing runs."""

    values = [
        float(row["duration_ms"])
        for row in rows
        if isinstance(row.get("duration_ms"), (int, float))
        and math.isfinite(float(row["duration_ms"]))
    ]
    return {
        "n": len(values),
        "missing": len(rows) - len(values),
        "minimum_ms": min(values) if values else None,
        "median_ms": statistics.median(values) if values else None,
        "mean_ms": statistics.fmean(values) if values else None,
        "maximum_ms": max(values) if values else None,
        "sample_stdev_ms": statistics.stdev(values) if len(values) > 1 else None,
    }


def evidence_inventory_rows(dataset: ExperimentDataset) -> list[dict[str, Any]]:
    """Flatten per-repetition evidence availability and pair-status counts."""

    rows: list[dict[str, Any]] = []
    for record in repetition_rows(dataset):
        inventory = record["evidence_record_inventory"]
        sidecar = inventory.get("adaptation_evidence_sidecar", {})
        evaluator_records = inventory.get("evaluator_execution_records", {})
        proofs = inventory.get("sidecar_pair_proofs", [])
        current_pairs = inventory.get("pre_adaptation_pair_assessments", [])
        candidate_pairs = inventory.get("candidate_pair_assessments", [])
        rows.append(
            {
                "scenario_id": record["scenario_id"],
                "repetition": record["repetition"],
                "raw_record_sha256": record.get("raw_record_sha256"),
                "input_bundle_sha256": record.get("input_bundle_sha256"),
                "operation_plan_sha256": record.get("operation_plan_sha256"),
                "candidate_configuration_sha256": record.get("candidate_configuration_sha256"),
                "sidecar_present": bool(sidecar.get("present", False)),
                "sidecar_sha256": sidecar.get("file_sha256"),
                "evaluator_evidence_count": len(inventory.get("evaluator_evidence_records", [])),
                "evaluator_execution_records_present": bool(
                    evaluator_records.get("present", False)
                ),
                "evaluator_execution_record_count": len(evaluator_records.get("records", [])),
                "evaluator_execution_file_sha256": evaluator_records.get("file_sha256"),
                "sidecar_pair_proofs": _status_counts(proofs, "status"),
                "pre_adaptation_pair_assessments": _status_counts(current_pairs, "status"),
                "candidate_pair_assessments": _status_counts(candidate_pairs, "status"),
            }
        )
    return rows


def evidence_artifact_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    """List artifact identifiers and hashes embedded in one repetition inventory."""

    inventory = record["evidence_record_inventory"]
    rows: list[dict[str, Any]] = []
    sidecar = inventory.get("adaptation_evidence_sidecar", {})
    if sidecar.get("file_sha256"):
        rows.append(
            {
                "evidence_type": "Adaptation evidence sidecar",
                "identifier": sidecar.get("contract_id") or "sidecar",
                "path": "raw/*_adaptation_evidence_test_only.json",
                "status": "PRESENT" if sidecar.get("present") else "UNAVAILABLE",
                "sha256": sidecar.get("file_sha256"),
            }
        )
    for evidence in inventory.get("evaluator_evidence_records", []):
        for artifact in evidence.get("evidence_artifacts", []):
            rows.append(
                {
                    "evidence_type": "Evaluator evidence artifact",
                    "identifier": evidence.get("evaluator_id", "UNAVAILABLE"),
                    "path": artifact.get("path", "UNAVAILABLE"),
                    "status": evidence.get("infrastructure_status", "UNAVAILABLE"),
                    "sha256": artifact.get("sha256"),
                }
            )
    evaluator_execution = inventory.get("evaluator_execution_records", {})
    if evaluator_execution.get("file_sha256"):
        rows.append(
            {
                "evidence_type": "Evaluator execution records",
                "identifier": "evaluator_execution_records",
                "path": "raw/*_sidecar_evaluator_records.json",
                "status": ("PRESENT" if evaluator_execution.get("present") else "UNAVAILABLE"),
                "sha256": evaluator_execution.get("file_sha256"),
            }
        )
    return rows


def _status_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key, "UNAVAILABLE")) for row in rows).items()))


def _code_block_json_after(text: str, heading: str) -> Any | None:
    heading_index = text.find(heading)
    if heading_index < 0:
        return None
    fence = chr(96) * 3
    match = re.search(f"{fence}json\\s*(\\{{.*?\\}})\\s*{fence}", text[heading_index:], re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def report_consistency_issues(dataset: ExperimentDataset) -> list[str]:
    """Cross-check recalculated counts and timing summaries against report_v1.md."""

    report = dataset.report_text
    if not report:
        return ["Source report is unavailable; summary cross-check was skipped."]
    metrics = summary_metrics(dataset)
    issues: list[str] = []

    def check_report_count(pattern: str, expected: int, name: str) -> None:
        match = re.search(pattern, report, re.IGNORECASE)
        if not match:
            issues.append(f"Source report is missing its {name} summary.")
        elif int(match.group(1)) != expected:
            issues.append(
                f"Derived {name} count {expected} does not match report count {match.group(1)}."
            )

    check_report_count(r"Scenario-level outcomes:\s*(\d+)", metrics["scenario_count"], "scenario")
    check_report_count(
        r"technical Method P repetitions:\s*(\d+)",
        metrics["technical_repetition_count"],
        "technical-repetition",
    )

    classification_match = re.search(
        r"Correct / incorrect / not evaluable:\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)",
        report,
        re.IGNORECASE,
    )
    if not classification_match:
        issues.append("Source report is missing its correct/incorrect/not-evaluable summary.")
    else:
        report_classification = tuple(int(classification_match.group(i)) for i in (1, 2, 3))
        derived_classification = (
            metrics["combined_correct_count"],
            metrics["combined_incorrect_count"],
            metrics["combined_not_evaluable_count"],
        )
        if report_classification != derived_classification:
            issues.append(
                "Derived correct/incorrect/not-evaluable counts "
                f"{derived_classification} do not match report counts {report_classification}."
            )

    operation_match = re.search(
        r"Operation decision accuracy:\s*(\d+)\s*/\s*(\d+)",
        report,
        re.IGNORECASE,
    )
    if not operation_match or (
        int(operation_match.group(1)) != metrics["operation_match_count"]
        or int(operation_match.group(2)) != metrics["operation_evaluable_count"]
    ):
        issues.append("Derived operation agreement does not match the source report.")

    combined_match = re.search(
        r"Combined operation/governance/semantic accuracy:\s*(\d+)\s*/\s*(\d+)",
        report,
        re.IGNORECASE,
    )
    if not combined_match or (
        int(combined_match.group(1)) != metrics["combined_correct_count"]
        or int(combined_match.group(2)) != metrics["combined_evaluable_count"]
    ):
        issues.append("Derived combined decision agreement does not match the source report.")

    if metrics["execution_failure_count"] is not None:
        failure_match = re.search(r"Execution failures:\s*(\d+)", report, re.IGNORECASE)
        if not failure_match or int(failure_match.group(1)) != metrics["execution_failure_count"]:
            issues.append("Execution-failure count does not match the source report.")

    reported_governance: Counter[str] = Counter()
    in_scenario_table = False
    for line in report.splitlines():
        if line.startswith("| Scenario |"):
            in_scenario_table = True
            continue
        if in_scenario_table and line.startswith("|---"):
            continue
        if in_scenario_table and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 4 and re.fullmatch(r"[A-D][1-2]", cells[0]):
                counts = re.fullmatch(r"([A-Z]+):\s*(\d+)", cells[3])
                if counts:
                    reported_governance[counts.group(1)] += int(counts.group(2))
        elif in_scenario_table and not line.startswith("|"):
            break
    if (
        reported_governance
        and dict(sorted(reported_governance.items())) != metrics["governance_distribution"]
    ):
        issues.append(
            "Derived governance distribution does not match the source report scenario table."
        )

    reported_matrix = _code_block_json_after(report, "Operation confusion matrix")
    if reported_matrix is None:
        issues.append("Source report operation confusion matrix is unavailable.")
    else:
        categories, matrix = confusion_matrix(dataset, "operation")
        derived_matrix = {
            expected: {
                observed: matrix[row_index][column_index]
                for column_index, observed in enumerate(categories)
                if matrix[row_index][column_index]
            }
            for row_index, expected in enumerate(categories)
            if any(matrix[row_index])
        }
        if reported_matrix != derived_matrix:
            issues.append("Derived operation confusion matrix does not match the source report.")

    reported_durations = _code_block_json_after(
        report, "Execution duration by observed operation (nanoseconds)"
    )
    if reported_durations is None:
        issues.append("Source report duration summary is unavailable.")
    else:
        derived: dict[str, dict[str, int | float]] = {}
        values_by_operation: dict[str, list[int]] = defaultdict(list)
        for row in repetition_rows(dataset):
            duration = row.get("duration_ns")
            if isinstance(duration, int):
                values_by_operation[row["proposed_operation"]].append(duration)
        for operation, values in values_by_operation.items():
            derived[operation] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
            }
        if set(derived) != set(reported_durations):
            issues.append("Derived duration operation groups do not match the source report.")
        else:
            for operation, stats in derived.items():
                report_stats = reported_durations[operation]
                for key in ("count", "min", "max"):
                    if stats[key] != report_stats.get(key):
                        issues.append(
                            f"Derived {operation} duration {key} does not match the report."
                        )
                if not math.isclose(
                    float(stats["mean"]),
                    float(report_stats.get("mean", math.nan)),
                    rel_tol=1e-12,
                    abs_tol=1e-9,
                ):
                    issues.append(f"Derived {operation} duration mean does not match the report.")
    return issues
