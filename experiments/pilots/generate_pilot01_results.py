"""Validate PILOT-01 evidence and derive its CSV table and descriptive statistics."""

import argparse
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any

from scripts.exp01_evidence_contract import BUNDLE_FILENAME, validate_bundle
from scripts.exp02_fitness_evidence import validate_representation_evidence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIR = ROOT / "experiments/results"
DEFAULT_CSV_PATH = ROOT / "experiments/pilots/PILOT_01_RESULTS.csv"
DEFAULT_STATS_PATH = ROOT / "experiments/pilots/PILOT_01_DESCRIPTIVE_STATISTICS.json"
RUN_ID_PATTERN = re.compile(r"pilot01-s(?P<condition>[01])-r(?P<repetition>[0-9]{2})$")
NUMERIC_FIELDS = (
    "import_linter_duration_seconds",
    "module_structure_duration_seconds",
    "request_count",
    "failure_count",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "throughput_requests_per_second",
    "application_cpu_seconds_delta",
    "application_rss_max_bytes",
    "runtime_sample_count",
)
CSV_FIELDS = (
    "experiment_id",
    "condition",
    "repetition_id",
    "source_revision",
    "injected_architectural_change",
    "fitness_configuration_sha256",
    "evaluator_configuration_sha256",
    "workload_profile_id",
    "workload_profile_sha256",
    "import_linter_exit_code",
    "contract_violations",
    "module_structure_test_outcome",
    "evidence_validity",
    "evidence_completeness",
    *NUMERIC_FIELDS,
    "runtime_application_identity_status",
    "environment_json",
    "artifact_references_json",
)


def sha256_file(path: Path) -> str:
    """Hash exact bytes from a real artifact file."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"artifact is missing or is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_artifact_inventory(root: Path, references: list[dict[str, Any]]) -> None:
    """Reject missing, escaping, symlinked, resized, or digest-mismatched artifacts."""
    resolved_root = root.resolve(strict=True)
    for reference in references:
        relative = Path(reference["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("artifact inventory contains an unsafe path")
        target = root.joinpath(relative)
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"artifact inventory path is missing or symlinked: {relative}")
        try:
            target.resolve(strict=True).relative_to(resolved_root)
        except ValueError as error:
            raise ValueError("artifact inventory path escapes the checkout") from error
        if target.stat().st_size != reference["size_bytes"]:
            raise ValueError(f"artifact inventory size mismatch: {relative}")
        if sha256_file(target) != reference["sha256"]:
            raise ValueError(f"artifact inventory digest mismatch: {relative}")


def _artifact_reference(root: Path, path: Path, role: str) -> dict[str, str]:
    """Return a compact path-and-digest reference for the table."""
    return {
        "role": role,
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
    }


def _measurement_row(root: Path, run_dir: Path) -> dict[str, Any]:
    """Revalidate one run and derive a row exclusively from its saved artifacts."""
    manifest_path = run_dir / "run_manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    match = RUN_ID_PATTERN.fullmatch(manifest["run_id"])
    if match is None or run_dir.name != manifest["run_id"]:
        raise ValueError("run directory name does not match a PILOT-01 condition/repetition")
    if manifest["condition"] != f"S{match.group('condition')}":
        raise ValueError("run condition conflicts with the run identity")
    if manifest["repetition_id"] != f"{manifest['condition']}-r{match.group('repetition')}":
        raise ValueError("repetition identity conflicts with the run directory")
    if manifest["source_git_dirty"] is not False:
        raise ValueError("PILOT-01 evidence must come from a clean source worktree")
    verify_artifact_inventory(root, manifest["artifact_references"])

    evidence_dir = run_dir.parent / manifest["exp01_run_id"]
    bundle = validate_bundle(evidence_dir)
    representation = validate_representation_evidence(evidence_dir, bundle)
    if bundle["source_revision"]["commit_sha"] != manifest["source_revision"]:
        raise ValueError("EXP-01 source revision conflicts with the run manifest")
    if bundle["bundle_status"] != manifest["evidence"]["exp01_bundle_status"]:
        raise ValueError("EXP-01 completeness conflicts with the run manifest")
    if manifest["evidence"]["exp02_validation"] != "valid":
        raise ValueError("EXP-02 validation status is not valid")
    if representation["coverage_claims"]["Coverage_P"] != "not_assessed":
        raise ValueError("PILOT-01 cannot report Coverage_P")
    if representation["coverage_claims"]["Coverage_ref"] != "not_established":
        raise ValueError("PILOT-01 cannot report Coverage_ref")

    records = {record["record_id"]: record for record in bundle["records"]}
    import_record = records["exp01-ci-import-linter-v1"]
    module_record = records["exp02-ci-module-structure-v1"]
    runtime_record = records["exp01-runtime-v1"]
    if (
        import_record["measurements"]["dependency_rule_violations"]
        != manifest["import_linter"]["broken_contract_count"]
    ):
        raise ValueError("Import Linter result conflicts with the validated bundle")
    if module_record["execution_verdict"] != manifest["module_structure_test"]["outcome"]:
        raise ValueError("module-structure result conflicts with the validated bundle")
    if (
        runtime_record["source_binding"]["status"]
        != manifest["runtime"]["runtime_application_identity_status"]
    ):
        raise ValueError("runtime application identity status conflicts with the validated bundle")

    bundle_path = evidence_dir / BUNDLE_FILENAME
    representation_path = evidence_dir / bundle["fitness_representation_evidence"]["path"]
    references = [
        _artifact_reference(root, manifest_path, "run_manifest"),
        _artifact_reference(root, bundle_path, "exp01_bundle"),
        _artifact_reference(root, representation_path, "exp02_representation_evidence"),
        _artifact_reference(root, run_dir / "locust_stats.csv", "locust_statistics"),
        _artifact_reference(root, run_dir / "runtime_metrics.csv", "runtime_metrics"),
        _artifact_reference(root, run_dir / "workload_profile.yaml", "workload_profile"),
    ]
    runtime = manifest["runtime"]
    return {
        "experiment_id": manifest["experiment_id"],
        "condition": manifest["condition"],
        "repetition_id": manifest["repetition_id"],
        "source_revision": manifest["source_revision"],
        "injected_architectural_change": manifest["injected_architectural_change"] or "none",
        "fitness_configuration_sha256": manifest["fitness_configuration_sha256"],
        "evaluator_configuration_sha256": manifest["evaluator_configuration_sha256"],
        "workload_profile_id": manifest["workload_profile_id"],
        "workload_profile_sha256": manifest["workload_profile_sha256"],
        "import_linter_exit_code": import_record["exit_status"],
        "contract_violations": import_record["measurements"]["dependency_rule_violations"],
        "module_structure_test_outcome": module_record["execution_verdict"],
        "evidence_validity": "valid",
        "evidence_completeness": bundle["bundle_status"],
        "import_linter_duration_seconds": import_record["duration_seconds"],
        "module_structure_duration_seconds": module_record["duration_seconds"],
        "request_count": runtime["request_count"],
        "failure_count": runtime["failure_count"],
        "p50_ms": runtime["p50_ms"],
        "p95_ms": runtime["p95_ms"],
        "p99_ms": runtime["p99_ms"],
        "throughput_requests_per_second": runtime["throughput_requests_per_second"],
        "application_cpu_seconds_delta": runtime["application_cpu_seconds_delta"],
        "application_rss_max_bytes": runtime["application_rss_max_bytes"],
        "runtime_sample_count": runtime["sample_count"],
        "runtime_application_identity_status": runtime_record["source_binding"]["status"],
        "environment_json": json.dumps(
            manifest["environment"], sort_keys=True, separators=(",", ":")
        ),
        "artifact_references_json": json.dumps(references, sort_keys=True, separators=(",", ":")),
    }


def descriptive_statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate min/mean/max over technical repetitions without inferential claims."""
    result: dict[str, Any] = {
        "scope": "technical repetitions of one controlled source-level condition",
        "independent_architecture_change_count": 1,
        "inferential_statistics": "not_applicable",
        "conditions": {},
    }
    conditions = result["conditions"]
    for condition in ("S0", "S1"):
        condition_rows = [row for row in rows if row["condition"] == condition]
        descriptions: dict[str, Any] = {}
        for field in NUMERIC_FIELDS:
            values = [float(row[field]) for row in condition_rows]
            descriptions[field] = {
                "n": len(values),
                "min": min(values),
                "mean": statistics.mean(values),
                "max": max(values),
            }
        conditions[condition] = {"repetition_count": len(condition_rows), "metrics": descriptions}
    return result


def generate_results(
    results_dir: Path, csv_path: Path, stats_path: Path, expected_repetitions: int = 3
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate all runs, then write the machine-readable table and descriptive summary."""
    root = ROOT
    run_dirs = sorted(
        path
        for path in results_dir.iterdir()
        if path.is_dir() and RUN_ID_PATTERN.fullmatch(path.name)
    )
    rows = [_measurement_row(root, run_dir) for run_dir in run_dirs]
    for condition in ("S0", "S1"):
        condition_rows = [row for row in rows if row["condition"] == condition]
        if len(condition_rows) != expected_repetitions:
            raise ValueError(
                f"{condition} requires {expected_repetitions} validated repetitions; "
                f"found {len(condition_rows)}"
            )
        repetitions = [row["repetition_id"] for row in condition_rows]
        if len(set(repetitions)) != expected_repetitions:
            raise ValueError(f"{condition} contains duplicate repetition identities")
    for field in (
        "fitness_configuration_sha256",
        "evaluator_configuration_sha256",
        "workload_profile_sha256",
    ):
        if len({row[field] for row in rows}) != 1:
            raise ValueError(f"PILOT-01 control changed across runs: {field}")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = descriptive_statistics(rows)
    stats_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return rows, summary


def main(argv: list[str] | None = None) -> int:
    """Validate saved evidence and derive results from it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--stats-output", type=Path, default=DEFAULT_STATS_PATH)
    parser.add_argument("--expected-repetitions", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        rows, summary = generate_results(
            args.results_dir.resolve(),
            args.csv_output,
            args.stats_output,
            args.expected_repetitions,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "valid",
                "row_count": len(rows),
                "csv_path": str(args.csv_output),
                "descriptive_statistics_path": str(args.stats_output),
                "scope": summary["scope"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
