"""Read-only loading, schema validation, and source-integrity checks."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

EXPERIMENT_ID = "MONO_E1_DEV_P_DECISIONS_V1"
RESULTS_SCHEMA_VERSION = 2
DEFAULT_RESULTS_RELATIVE_PATH = Path(
    "experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1/results_v1.json"
)


class DashboardDataError(ValueError):
    """Raised when a dashboard data source is invalid or internally inconsistent."""


@dataclass(frozen=True)
class IntegritySummary:
    """Counts from the run's file checksum inventory."""

    expected_files: int = 0
    verified_files: int = 0
    missing_files: int = 0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExperimentDataset:
    """Validated experiment records and their nearby source artifacts."""

    repo_root: Path
    run_dir: Path
    experiment_dir: Path
    results_path: Path
    scenario_catalog_path: Path | None
    results: dict[str, Any]
    scenario_catalog: dict[str, Any]
    execution_manifest: dict[str, Any] | None
    raw_records_manifest: dict[str, Any] | None
    score_manifest: dict[str, Any] | None
    report_text: str
    integrity: IntegritySummary
    warnings: tuple[str, ...] = ()


def default_results_path() -> Path:
    """Return the canonical retained result path in this checkout."""

    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / DEFAULT_RESULTS_RELATIVE_PATH


def _reject_json_constant(value: str) -> None:
    raise DashboardDataError(f"Non-finite JSON numeric value {value!r} is not supported.")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except FileNotFoundError as exc:
        raise DashboardDataError(f"Required JSON file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DashboardDataError(
            f"Could not parse JSON file {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise DashboardDataError(f"Expected a JSON object in {path}.")
    return payload


def _scan_finite_numbers(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise DashboardDataError(f"Non-finite numeric value at {path}.")
    if isinstance(value, dict):
        for key, child in value.items():
            _scan_finite_numbers(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_finite_numbers(child, f"{path}[{index}]")


def _format_schema_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.absolute_path) or "<root>"
    return f"{location}: {error.message}"


def validate_results_payload(
    payload: dict[str, Any],
    schema_path: Path | None = None,
) -> tuple[str, ...]:
    """Validate the corrected v2 reader contract and internal record counts."""

    actual_schema = schema_path or (
        Path(__file__).resolve().parent / "schemas" / "results_v2.schema.json"
    )
    schema = _read_json(actual_schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=_format_schema_error)
    if errors:
        details = "; ".join(_format_schema_error(error) for error in errors[:5])
        more = f" ({len(errors) - 5} more)" if len(errors) > 5 else ""
        raise DashboardDataError(f"Results schema v2 validation failed: {details}{more}")

    _scan_finite_numbers(payload)
    if payload.get("schema_version") != RESULTS_SCHEMA_VERSION:
        raise DashboardDataError(
            "Unsupported results schema_version "
            f"{payload.get('schema_version')!r}; dashboard supports version "
            f"{RESULTS_SCHEMA_VERSION}."
        )
    if payload.get("experiment_id") != EXPERIMENT_ID:
        raise DashboardDataError(
            f"Unsupported experiment_id {payload.get('experiment_id')!r}; expected {EXPERIMENT_ID}."
        )

    scenario_rows = payload["scenario_results"]
    repetition_rows = payload["technical_repetition_results"]
    if payload["scenario_count"] != len(scenario_rows):
        raise DashboardDataError(
            "Declared scenario_count does not match scenario_results length "
            f"({payload['scenario_count']} declared, {len(scenario_rows)} present)."
        )
    if payload["technical_repetition_count"] != len(repetition_rows):
        raise DashboardDataError(
            "Declared technical_repetition_count does not match "
            "technical_repetition_results length "
            f"({payload['technical_repetition_count']} declared, "
            f"{len(repetition_rows)} present)."
        )

    scenario_ids = [row["scenario_id"] for row in scenario_rows]
    if len(set(scenario_ids)) != len(scenario_ids):
        raise DashboardDataError("scenario_results contains duplicate scenario_id values.")
    repetition_keys = [(row["scenario_id"], row["repetition"]) for row in repetition_rows]
    if len(set(repetition_keys)) != len(repetition_keys):
        raise DashboardDataError(
            "technical_repetition_results contains duplicate scenario/repetition pairs."
        )

    classifications = Counter(row["classification"] for row in repetition_rows)
    for category in ("correct", "incorrect", "not_evaluable"):
        observed_count = classifications.get(category.upper(), 0)
        declared_count = payload["summary_counts"][category]
        if declared_count != observed_count:
            raise DashboardDataError(
                f"summary_counts.{category} ({declared_count}) does not match "
                f"technical repetition classifications ({observed_count})."
            )
    governance_counts = dict(Counter(row["governance_result"] for row in repetition_rows))
    declared_governance = {
        key: count for key, count in payload["governance_distribution"].items() if count
    }
    if declared_governance != governance_counts:
        raise DashboardDataError(
            "governance_distribution does not match technical repetition records."
        )
    operation_records = [
        row
        for row in repetition_rows
        if row.get("expected_operation") is not None and row.get("proposed_operation") is not None
    ]
    operation_matches = sum(
        row["expected_operation"] == row["proposed_operation"] for row in operation_records
    )
    operation_summary = payload["operation_decision_accuracy"]
    if operation_summary["correct_operation_count"] != operation_matches or operation_summary[
        "evaluable_execution_count"
    ] != len(operation_records):
        raise DashboardDataError(
            "operation_decision_accuracy does not match technical repetition records."
        )
    combined_correct = classifications.get("CORRECT", 0)
    combined_evaluable = combined_correct + classifications.get("INCORRECT", 0)
    combined_summary = payload["combined_decision_accuracy"]
    if (
        combined_summary["correct_count"] != combined_correct
        or combined_summary["evaluable_execution_count"] != combined_evaluable
    ):
        raise DashboardDataError(
            "combined_decision_accuracy does not match technical repetition records."
        )

    warnings: list[str] = []
    if not scenario_rows and not repetition_rows:
        warnings.append("No scenario or technical-repetition records are available.")
    return tuple(warnings)


def _find_repo_root(results_path: Path) -> Path:
    for candidate in (results_path, *results_path.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / "experiments").is_dir():
            return candidate
    return results_path.parent


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_inventory_path(relative_path: str, run_dir: Path) -> Path:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise DashboardDataError(f"Unsafe path in artifact checksum inventory: {relative_path!r}")
    return run_dir.joinpath(*path.parts)


def _check_digest(path: Path, expected: Any, label: str) -> None:
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise DashboardDataError(f"{label} does not contain a valid SHA-256 digest.")
    actual = _sha256(path)
    if actual.lower() != expected.lower():
        raise DashboardDataError(
            f"SHA-256 mismatch for {label}: expected {expected}, found {actual}."
        )


def _read_optional_manifest(path: Path, warnings: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        warnings.append(f"Integrity metadata is unavailable because {path.name} is missing.")
        return None
    return _read_json(path)


def _read_sha256sum_entries(run_dir: Path) -> list[tuple[str, str]]:
    """Parse the checksum inventory after its existence has been established."""

    inventory_path = run_dir / "SHA256SUMS"
    entries: list[tuple[str, str]] = []
    for line_number, line in enumerate(inventory_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            raise DashboardDataError(f"Malformed SHA256SUMS entry on line {line_number}.")
        relative_path = parts[1].lstrip("* ")
        _safe_inventory_path(relative_path, run_dir)
        entries.append((parts[0].lower(), relative_path))

    if len({path for _, path in entries}) != len(entries):
        raise DashboardDataError("SHA256SUMS contains duplicate file paths.")
    return entries


def _verify_sha256sums(run_dir: Path, warnings: list[str]) -> tuple[int, int, int]:
    inventory_path = run_dir / "SHA256SUMS"
    if not inventory_path.is_file():
        warnings.append("SHA256SUMS is unavailable; file-level checksum verification was skipped.")
        return 0, 0, 0

    entries = _read_sha256sum_entries(run_dir)

    verified = 0
    missing = 0
    for expected, relative_path in entries:
        artifact_path = _safe_inventory_path(relative_path, run_dir)
        if not artifact_path.is_file():
            missing += 1
            continue
        _check_digest(artifact_path, expected, f"SHA256SUMS entry {relative_path}")
        verified += 1

    if missing:
        warnings.append(
            f"{missing} files listed in SHA256SUMS are unavailable; "
            f"{verified} available files were verified."
        )
    return len(entries), verified, missing


def _verify_raw_manifest(
    run_dir: Path,
    manifest: dict[str, Any] | None,
    warnings: list[str],
) -> None:
    if manifest is None:
        return
    files = manifest.get("files")
    if not isinstance(files, list):
        raise DashboardDataError("raw_records_manifest.json must contain a files array.")
    missing: list[str] = []
    for item in files:
        if not isinstance(item, dict):
            raise DashboardDataError("Each raw-record manifest entry must be an object.")
        relative_path = item.get("path")
        if not isinstance(relative_path, str):
            raise DashboardDataError("A raw-record manifest entry is missing its path.")
        artifact_path = _safe_inventory_path(relative_path, run_dir)
        if not artifact_path.is_file():
            missing.append(relative_path)
            continue
        expected_size = item.get("size_bytes")
        if isinstance(expected_size, int) and artifact_path.stat().st_size != expected_size:
            raise DashboardDataError(f"Byte-size mismatch for raw artifact {relative_path}.")
        _check_digest(artifact_path, item.get("sha256"), f"raw artifact {relative_path}")
    if missing:
        warnings.append(
            f"{len(missing)} raw-record manifest files are unavailable; their records "
            "remain listed as unavailable."
        )


def _verify_source_manifests(
    results_path: Path,
    results: dict[str, Any],
    execution_manifest: dict[str, Any] | None,
    raw_manifest: dict[str, Any] | None,
    score_manifest: dict[str, Any] | None,
    experiment_dir: Path,
    warnings: list[str],
) -> None:
    run_dir = results_path.parent
    execution_path = run_dir / "execution_manifest.json"
    raw_path = run_dir / "raw_records_manifest.json"
    report_path = run_dir / "report_v1.md"

    for path, expected, label in (
        (execution_path, results.get("execution_manifest_sha256"), "execution manifest"),
        (raw_path, results.get("raw_records_manifest_sha256"), "raw-record manifest"),
        (
            experiment_dir / "reference_v1.json",
            results.get("reference_sha256"),
            "author-declared reference",
        ),
    ):
        if path.is_file():
            _check_digest(path, expected, label)
        else:
            warnings.append(f"{label.capitalize()} file is unavailable: {path.name}.")

    if execution_manifest is not None:
        recorded_commit = execution_manifest.get("source_commit_sha")
        if recorded_commit and recorded_commit != results.get("source_commit_sha"):
            raise DashboardDataError("Result and execution-manifest source commits do not match.")
        manifest_method_identity = execution_manifest.get("method_identity")
        method_version = (
            manifest_method_identity.get("method_version")
            if isinstance(manifest_method_identity, dict)
            else None
        )
        if method_version and method_version != results.get("method_identity", {}).get(
            "method_version"
        ):
            raise DashboardDataError("Result and execution-manifest method versions do not match.")

    if raw_manifest is not None:
        _verify_raw_manifest(run_dir, raw_manifest, warnings)

    if score_manifest is not None:
        for key, path, label in (
            ("result_sha256", results_path, "scored results"),
            ("report_sha256", report_path, "scored report"),
        ):
            expected = score_manifest.get(key)
            if path.is_file():
                _check_digest(path, expected, label)
            else:
                warnings.append(f"{label.capitalize()} file is unavailable: {path.name}.")
        if score_manifest.get("scenario_count") != results.get("scenario_count"):
            raise DashboardDataError("Score manifest scenario_count does not match results.")
        if score_manifest.get("technical_repetition_count") != results.get(
            "technical_repetition_count"
        ):
            raise DashboardDataError(
                "Score manifest technical_repetition_count does not match results."
            )


def load_dataset(
    results_path: str | Path | None = None,
    scenario_catalog_path: str | Path | None = None,
) -> ExperimentDataset:
    """Load the scored run and nearby metadata without writing to any source file."""

    selected_results_path = Path(results_path or default_results_path()).expanduser().resolve()
    if not selected_results_path.is_file():
        raise DashboardDataError(
            f"Results file not found: {selected_results_path}. "
            "Choose the v2 results_v1.json file from the experiment run."
        )
    results = _read_json(selected_results_path)
    schema_warnings = list(validate_results_payload(results))

    run_dir = selected_results_path.parent
    experiment_dir = run_dir.parent
    repo_root = _find_repo_root(selected_results_path)
    warnings = list(schema_warnings)

    selected_scenario_path = (
        Path(scenario_catalog_path).expanduser().resolve()
        if scenario_catalog_path
        else experiment_dir / "scenarios_v1.json"
    )
    scenario_catalog: dict[str, Any] = {}
    if selected_scenario_path.is_file():
        scenario_catalog = _read_json(selected_scenario_path)
        scenario_schema_path = experiment_dir / "scenario.schema.json"
        if scenario_schema_path.is_file():
            scenario_schema = _read_json(scenario_schema_path)
            scenario_errors = sorted(
                Draft202012Validator(scenario_schema).iter_errors(scenario_catalog),
                key=_format_schema_error,
            )
            if scenario_errors:
                details = "; ".join(_format_schema_error(error) for error in scenario_errors[:5])
                raise DashboardDataError(f"Scenario catalog schema validation failed: {details}")
        else:
            warnings.append("scenario.schema.json is unavailable; scenario metadata is unverified.")
    else:
        warnings.append(
            f"Scenario definitions are unavailable: {selected_scenario_path}. "
            "The decision explorer will show recorded results only."
        )

    scenario_ids = {
        item.get("scenario_id")
        for item in scenario_catalog.get("scenarios", [])
        if isinstance(item, dict)
    }
    result_scenario_ids = {row["scenario_id"] for row in results["scenario_results"]}
    repetition_scenario_ids = {
        row["scenario_id"] for row in results["technical_repetition_results"]
    }
    unknown_scenarios = (result_scenario_ids | repetition_scenario_ids) - scenario_ids
    if scenario_ids and unknown_scenarios:
        raise DashboardDataError(
            "Results refer to scenario IDs absent from scenarios_v1.json: "
            + ", ".join(sorted(unknown_scenarios))
        )
    if scenario_ids and result_scenario_ids != scenario_ids:
        warnings.append(
            "The result table contains only a subset of scenario-catalog entries; "
            "views show available records."
        )

    execution_manifest = _read_optional_manifest(run_dir / "execution_manifest.json", warnings)
    raw_manifest = _read_optional_manifest(run_dir / "raw_records_manifest.json", warnings)
    score_manifest = _read_optional_manifest(run_dir / "score_manifest.json", warnings)
    report_path = run_dir / "report_v1.md"
    if report_path.is_file():
        report_text = report_path.read_text(encoding="utf-8")
    else:
        report_text = ""
        warnings.append("report_v1.md is unavailable; report cross-checks cannot run.")

    expected_files, verified_files, missing_files = _verify_sha256sums(run_dir, warnings)
    _verify_source_manifests(
        selected_results_path,
        results,
        execution_manifest,
        raw_manifest,
        score_manifest,
        experiment_dir,
        warnings,
    )

    return ExperimentDataset(
        repo_root=repo_root,
        run_dir=run_dir,
        experiment_dir=experiment_dir,
        results_path=selected_results_path,
        scenario_catalog_path=selected_scenario_path if selected_scenario_path.is_file() else None,
        results=results,
        scenario_catalog=scenario_catalog,
        execution_manifest=execution_manifest,
        raw_records_manifest=raw_manifest,
        score_manifest=score_manifest,
        report_text=report_text,
        integrity=IntegritySummary(
            expected_files=expected_files,
            verified_files=verified_files,
            missing_files=missing_files,
            warnings=tuple(warnings),
        ),
        warnings=tuple(warnings),
    )


def validate_publication_export_readiness(dataset: ExperimentDataset) -> None:
    """Fail closed unless the dataset and its current source artifacts are publication-ready.

    The exploratory loader intentionally represents missing optional evidence as warnings.
    Publication export uses a fresh read so validation cannot rely on a stale dataset or on
    an earlier successful checksum pass.
    """

    run_dir = dataset.run_dir.expanduser().resolve()
    results_path = dataset.results_path.expanduser().resolve()
    experiment_dir = dataset.experiment_dir.expanduser().resolve()
    expected_results_path = run_dir / "results_v1.json"
    if results_path != expected_results_path or experiment_dir != run_dir.parent:
        raise DashboardDataError(
            "Publication figure export requires results_v1.json and its adjacent source artifacts."
        )

    required_paths = {
        "execution manifest": run_dir / "execution_manifest.json",
        "raw-record manifest": run_dir / "raw_records_manifest.json",
        "score manifest": run_dir / "score_manifest.json",
        "checksum inventory": run_dir / "SHA256SUMS",
        "results": expected_results_path,
        "source report": run_dir / "report_v1.md",
        "author-declared reference": experiment_dir / "reference_v1.json",
    }
    missing = []
    for label, path in required_paths.items():
        if not path.is_file():
            missing.append(f"{label} ({path.name})")
    if missing:
        raise DashboardDataError(
            "Publication figure export requires verified source artifacts; missing: "
            + ", ".join(missing)
            + "."
        )

    verified = load_dataset(results_path)
    if (
        dataset.results != verified.results
        or dataset.report_text != verified.report_text
        or dataset.execution_manifest != verified.execution_manifest
        or dataset.raw_records_manifest != verified.raw_records_manifest
        or dataset.score_manifest != verified.score_manifest
    ):
        raise DashboardDataError(
            "Publication figure export rejected a dataset that differs from its current "
            "source artifacts."
        )

    integrity = verified.integrity
    if integrity.expected_files == 0:
        raise DashboardDataError(
            "Publication figure export requires a non-empty SHA256SUMS inventory; "
            "0/0 files is not a successful verification."
        )
    if integrity.verified_files != integrity.expected_files or integrity.missing_files != 0:
        raise DashboardDataError(
            "Publication figure export requires complete checksum verification: "
            f"{integrity.verified_files}/{integrity.expected_files} files verified, "
            f"{integrity.missing_files} listed files missing."
        )
    if dataset.integrity != integrity:
        raise DashboardDataError(
            "Publication figure export rejected stale integrity results; reload the source dataset."
        )

    entries = _read_sha256sum_entries(run_dir)
    inventory_paths = {relative_path for _, relative_path in entries}
    required_inventory_paths = {
        "execution_manifest.json",
        "raw_records_manifest.json",
        "score_manifest.json",
        "results_v1.json",
        "report_v1.md",
    }
    raw_manifest = verified.raw_records_manifest
    if raw_manifest is None:
        raise DashboardDataError(
            "Publication figure export requires a verified raw-record manifest."
        )
    raw_files = raw_manifest.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise DashboardDataError(
            "Publication figure export requires a non-empty raw-record manifest."
        )
    for item in raw_files:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            required_inventory_paths.add(item["path"])
    uncovered = sorted(required_inventory_paths - inventory_paths)
    if uncovered:
        raise DashboardDataError(
            "SHA256SUMS does not cover required source artifacts: " + ", ".join(uncovered) + "."
        )

    execution_manifest = verified.execution_manifest
    score_manifest = verified.score_manifest
    if execution_manifest is None or score_manifest is None:
        raise DashboardDataError(
            "Publication figure export requires verified execution and score manifests."
        )
    for label, manifest, expected_version in (
        ("execution", execution_manifest, 1),
        ("raw-record", raw_manifest, 1),
        ("score", score_manifest, 2),
    ):
        if manifest.get("schema_version") != expected_version:
            raise DashboardDataError(
                f"Publication figure export found an unsupported {label} manifest schema_version."
            )
    if execution_manifest.get("experiment_id") != verified.results.get("experiment_id"):
        raise DashboardDataError("Execution manifest experiment_id does not match results.")
    recorded_commit = execution_manifest.get("source_commit_sha")
    if not recorded_commit or recorded_commit != verified.results.get("source_commit_sha"):
        raise DashboardDataError(
            "Execution manifest source_commit_sha is missing or does not match results."
        )
    manifest_method_identity = execution_manifest.get("method_identity")
    result_method_identity = verified.results.get("method_identity")
    manifest_method = (
        manifest_method_identity.get("method_version")
        if isinstance(manifest_method_identity, dict)
        else None
    )
    result_method = (
        result_method_identity.get("method_version")
        if isinstance(result_method_identity, dict)
        else None
    )
    if not manifest_method or manifest_method != result_method:
        raise DashboardDataError(
            "Execution manifest method_version is missing or does not match results."
        )
    for manifest_key, result_key in (
        ("execution_manifest_sha256", "execution_manifest_sha256"),
        ("raw_manifest_sha256", "raw_records_manifest_sha256"),
        ("reference_sha256", "reference_sha256"),
    ):
        if score_manifest.get(manifest_key) != verified.results.get(result_key):
            raise DashboardDataError(
                f"Score manifest {manifest_key} does not match results.{result_key}."
            )

    from research_dashboard.metrics import report_consistency_issues

    report_issues = report_consistency_issues(verified)
    if report_issues:
        raise DashboardDataError(
            "Publication figure export report consistency check failed: " + "; ".join(report_issues)
        )


def repository_relative_path(path: Path, repo_root: Path) -> str:
    """Return a readable repository-relative path when possible."""

    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
