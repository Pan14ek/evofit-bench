"""Validate preserved EVAL-02 evidence without rerunning evaluators."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZipFile

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = REPOSITORY_ROOT / "experiments/pilots/EVAL02_RAW_EVIDENCE_V1.zip"
EXPECTED_ARCHIVE_SHA256 = "9039e17b5b640db5641b808719c6b972a389b8f5e833ac1dc7783e658f4bf18c"
EXPECTED_CONFUSION_MATRICES = {
    "AC_PUBLIC_API": {"tp": 4, "fp": 0, "tn": 4, "fn": 0},
    "AC_MODULE_GRAPH": {"tp": 2, "fp": 0, "tn": 4, "fn": 0},
}
EXPECTED_DIAGNOSTIC_MISMATCH = {
    "case_id": "missing_required_public_function",
    "evaluator_id": "AC_PUBLIC_API",
    "stage": "observation_validation",
    "detail": "FINDING_CLASS_MISMATCH",
}
EXPECTED_DIAGNOSTIC_CODES = [
    "PUBLIC_INTERFACE_MISSING",
    "UNDECLARED_PUBLIC_INTERFACE",
]


def classify_execution_status(
    run_records: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    evaluator_catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Separate invocation, provenance, and preregistered diagnostic failures."""
    execution_failures = [
        row
        for row in run_records
        if row.get("execution_status") != "COMPLETED"
        or row.get("launch_error")
        or row.get("parse_error")
    ]
    provenance_failures = []
    for row in run_records:
        source_invalid = (
            row.get("source_sha_status") != "MATCHED"
            or row.get("source_commit_sha") != row.get("expected_source_sha")
            or row.get("source_commit_sha") != row.get("target_source_sha")
            or row.get("subject_source_dirty") is not False
            or row.get("checkout_status_after") != "clean"
        )
        evaluator_invalid = False
        if evaluator_catalog is not None:
            expected = evaluator_catalog[row["evaluator_id"]]
            evaluator_invalid = (
                row.get("evaluator_version") != expected["version"]
                or row.get("evaluator_source_digest") != expected["expected_source_artifact_digest"]
                or row.get("configuration_digest") != expected["configuration_sha256"]
            )
        if source_invalid or evaluator_invalid:
            provenance_failures.append(row)
    diagnostic_mismatches = [
        item
        for item in failures
        if item.get("stage") == EXPECTED_DIAGNOSTIC_MISMATCH["stage"]
        and item.get("detail") == EXPECTED_DIAGNOSTIC_MISMATCH["detail"]
    ]
    other_validation_failures = [
        item
        for item in failures
        if item.get("stage") == "observation_validation" and item not in diagnostic_mismatches
    ]
    runner_exit_code = 1 if failures else 0
    if execution_failures or provenance_failures or other_validation_failures:
        evidence_status = "INCOMPLETE_OR_INVALID"
    elif diagnostic_mismatches:
        evidence_status = "COMPLETE_WITH_DIAGNOSTIC_EXPECTATION_MISMATCHES"
    else:
        evidence_status = "COMPLETE_WITHOUT_RECORDED_MISMATCHES"
    return {
        "runner_execution_stage_exit_code": runner_exit_code,
        "runner_exit_code_basis": (
            "Reconstructed from the preserved run manifest and preregistered return rule; "
            "this validator does not invoke the runner."
        ),
        "evaluator_invocation_failures": len(execution_failures),
        "source_provenance_failures": len(provenance_failures),
        "diagnostic_expectation_mismatches": len(diagnostic_mismatches),
        "diagnostic_mismatch_repeats": sorted(
            int(item["repeat"])
            for item in diagnostic_mismatches
            if item.get("case_id") == EXPECTED_DIAGNOSTIC_MISMATCH["case_id"]
            and item.get("evaluator_id") == EXPECTED_DIAGNOSTIC_MISMATCH["evaluator_id"]
        ),
        "other_observation_validation_failures": len(other_validation_failures),
        "evidence_status": evidence_status,
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(archive: ZipFile, path: str) -> dict[str, Any]:
    value = json.loads(archive.read(path))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _verify_internal_checksums(archive: ZipFile) -> int:
    names = set(archive.namelist())
    if "SHA256SUMS" not in names:
        raise ValueError("Archive is missing SHA256SUMS")
    checksum_entries: dict[str, str] = {}
    for line_number, line in enumerate(archive.read("SHA256SUMS").decode("utf-8").splitlines(), 1):
        digest, separator, name = line.partition("  ")
        name = name.lstrip("*")
        normalized = PurePosixPath(name)
        if not separator or normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError(f"Invalid checksum entry on SHA256SUMS line {line_number}")
        checksum_entries[name] = digest
    if set(checksum_entries) != names - {"SHA256SUMS"}:
        raise ValueError("SHA256SUMS does not cover exactly the archived files")
    for name, expected in checksum_entries.items():
        actual = _sha256(archive.read(name))
        if actual != expected:
            raise ValueError(f"Internal SHA-256 mismatch for {name}")
    return len(checksum_entries)


def validate_eval02_archive(archive_path: Path, sidecar_path: Path | None = None) -> dict[str, Any]:
    """Check evidence integrity, recorded statuses, and frozen case metrics."""
    archive_path = archive_path.resolve()
    sidecar_path = sidecar_path or Path(f"{archive_path}.sha256")
    expected_archive_sha = sidecar_path.read_text(encoding="utf-8").split()[0]
    actual_archive_sha = _sha256(archive_path.read_bytes())
    if (
        expected_archive_sha != EXPECTED_ARCHIVE_SHA256
        or actual_archive_sha != EXPECTED_ARCHIVE_SHA256
    ):
        raise ValueError("External archive SHA-256 does not match its sidecar")

    with ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"ZIP CRC check failed for {bad_member}")
        checksum_count = _verify_internal_checksums(archive)
        manifest = _read_json(archive, "run-manifest.json")
        analysis = _read_json(archive, "EVAL02_ANALYSIS_V1.json")
        catalog = _read_json(archive, "preregistration/mutation_catalog.json")
        run_records = [
            json.loads(line)
            for line in archive.read("execution.jsonl").decode("utf-8").splitlines()
            if line.strip()
        ]
        classification = classify_execution_status(
            run_records, manifest.get("failures", []), catalog["evaluators"]
        )

        evaluators = list(catalog["evaluators"])
        repeat_count = int(catalog["execution_protocol"]["measured_repeats_per_case_evaluator"])
        planned = {
            (case["case_id"], evaluator_id, repeat)
            for case in catalog["cases"]
            for evaluator_id in evaluators
            for repeat in range(1, repeat_count + 1)
        }
        observed = {
            (row["case_id"], row["evaluator_id"], int(row["repeat"])) for row in run_records
        }
        if observed != planned or len(run_records) != len(planned):
            raise ValueError("Raw evaluator-call inventory differs from the preregistered schedule")
        if len(run_records) != manifest["execution_environment"]["planned_evaluator_calls"]:
            raise ValueError("Run manifest call count differs from the raw observation stream")

        diagnostic_rows = [
            item
            for item in manifest.get("failures", [])
            if all(item.get(key) == value for key, value in EXPECTED_DIAGNOSTIC_MISMATCH.items())
        ]
        mismatch_repeats = sorted(int(item["repeat"]) for item in diagnostic_rows)
        if mismatch_repeats != [1, 2, 3] or len(manifest.get("failures", [])) != 3:
            raise ValueError(
                "Preserved diagnostic-mismatch rows differ from the recorded EVAL-02 result"
            )

        mismatch_runs = [
            row
            for row in run_records
            if row["case_id"] == EXPECTED_DIAGNOSTIC_MISMATCH["case_id"]
            and row["evaluator_id"] == EXPECTED_DIAGNOSTIC_MISMATCH["evaluator_id"]
        ]
        if len(mismatch_runs) != 3 or any(
            row.get("observed_compliance") != "NON_COMPLIANT"
            or row.get("finding_codes") != EXPECTED_DIAGNOSTIC_CODES
            for row in mismatch_runs
        ):
            raise ValueError(
                "Recorded diagnostic-mismatch observations do not match the case report"
            )

        if classification["evaluator_invocation_failures"] != 0:
            raise ValueError("One or more evaluator invocations failed to complete")
        if classification["source_provenance_failures"] != 0:
            raise ValueError("One or more evaluator records failed source-provenance checks")
        if classification["other_observation_validation_failures"] != 0:
            raise ValueError("Unexpected observation-validation failures are present")
        if classification["diagnostic_expectation_mismatches"] != 3:
            raise ValueError("Expected exactly three diagnostic-set mismatches")
        if manifest.get("analysis_raw_inventory_verification") != "PASS":
            raise ValueError("Run manifest does not record a passing analysis inventory check")
        if analysis.get("raw_inventory_verification") != "PASS" or analysis.get(
            "raw_inventory_errors"
        ):
            raise ValueError("Archived analysis reports a raw-inventory problem")
        if manifest.get("analysis_raw_inventory_errors"):
            raise ValueError("Run manifest records raw-inventory errors")
        if analysis.get("repeats_are_independent_cases") is not False:
            raise ValueError("Archived analysis does not mark technical repeats as non-independent")
        all_case_rows = [
            row
            for evaluator_id in evaluators
            for row in analysis["evaluator_case_results"][evaluator_id]
        ]
        if len(all_case_rows) != len(catalog["cases"]) * len(evaluators) or any(
            row.get("provenance_valid") is not True for row in all_case_rows
        ):
            raise ValueError("One or more archived case-level provenance checks did not pass")

        for evaluator_id, expected_matrix in EXPECTED_CONFUSION_MATRICES.items():
            metrics = analysis["evaluator_metrics"][evaluator_id]
            if metrics["confusion_matrix"] != expected_matrix or metrics["f1"] != 1.0:
                raise ValueError(f"Frozen binary metrics differ for {evaluator_id}")
            if analysis["not_evaluable_case_ids_by_evaluator"][evaluator_id]:
                raise ValueError(f"Unexpected NOT_EVALUABLE case for {evaluator_id}")

        analysis_artifacts = {
            "EVAL02_ANALYSIS_V1.json": "EVAL02_ANALYSIS_V1.json",
            "EVAL02_CASE_RESULTS_V1.csv": "EVAL02_CASE_RESULTS_V1.csv",
            "EVAL02_REPORT_V1.md": "EVAL02_REPORT_V1.md",
            "EVAL02_MANUSCRIPT_UA.md": "EVAL02_MANUSCRIPT_UA.md",
        }
        for manifest_name, archive_name in analysis_artifacts.items():
            expected_digest = manifest.get("analysis_artifacts_sha256", {}).get(manifest_name)
            if expected_digest != _sha256(archive.read(archive_name)):
                raise ValueError(
                    f"Archived analysis artifact does not match manifest: {archive_name}"
                )

        case_result = next(
            row
            for row in analysis["evaluator_case_results"]["AC_PUBLIC_API"]
            if row["case_id"] == EXPECTED_DIAGNOSTIC_MISMATCH["case_id"]
        )
        if (
            case_result["architectural_status"] != "NON_COMPLIANT"
            or case_result["observed_compliance_by_repeat"]
            != [
                "NON_COMPLIANT",
                "NON_COMPLIANT",
                "NON_COMPLIANT",
            ]
            or case_result["expected_finding_codes"] != ["PUBLIC_INTERFACE_MISSING"]
            or case_result["observed_finding_codes_by_repeat"] != [EXPECTED_DIAGNOSTIC_CODES] * 3
            or case_result["preregistered_expected_outcome_matched"] is not False
            or case_result["valid_for_confusion_matrix"] is not True
        ):
            raise ValueError(
                "Archived case analysis does not represent the diagnostic mismatch accurately"
            )

    return {
        "archive_integrity": {
            "external_sha256": "PASS",
            "pinned_archive_sha256": "PASS",
            "zip_crc": "PASS",
            "internal_checksum_files_verified": checksum_count,
            "internal_sha256": "PASS",
        },
        "evaluator_calls": {"planned": len(planned), "completed": len(run_records)},
        "execution_status": classification,
        "analysis_status": "COMPLETE",
        "raw_inventory_status": "PASS",
        "not_evaluable_cases": {evaluator_id: [] for evaluator_id in evaluators},
        "confusion_matrices": EXPECTED_CONFUSION_MATRICES,
        "f1_by_evaluator": {evaluator_id: 1.0 for evaluator_id in evaluators},
        "evaluator_calls_by_return_code": {
            str(code): sum(row.get("return_code") == code for row in run_records)
            for code in sorted({row.get("return_code") for row in run_records})
        },
    }


def main() -> int:
    """Run the read-only post-experiment evidence validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--sidecar", type=Path)
    args = parser.parse_args()
    try:
        result = validate_eval02_archive(args.archive, args.sidecar)
    except Exception as exc:
        print(f"EVAL-02 post-run validation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
