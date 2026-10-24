"""Separate scoring-readiness gate for MONO CI B0/Ψ execution records.

This scorer-side entrypoint runs only after a sealed execution result exists.
Until an independently held scorer reference is approved, it emits categorical
metric statuses and no numeric scores. The execution runner never imports this
module, and its inputs are not part of either method arm bundle.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_file
from experiments.execution.tooling.mono_ci_b0_psi_execution import (
    verify_development_result,
)

SCORING_SCHEMA = "mono_ci_b0_psi_score_v1.schema.json"


def score_development_run(run_root: Path, output_root: Path) -> dict[str, Any]:
    """Write a separate, unscored assessment for a verified DEVELOPMENT run."""
    if run_root.is_symlink():
        raise ProtocolError("MONO_CI_B0_PSI_SCORING_INPUT_SYMLINK_FORBIDDEN")
    run = verify_development_result(run_root)
    result_path = run_root.resolve(strict=True) / "development_run.json"
    destination = output_root.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ProtocolError("MONO_CI_B0_PSI_SCORING_OUTPUT_MUST_BE_NEW")
    parent = destination.parent.resolve(strict=True)
    run_directory = run_root.resolve(strict=True)
    if (
        destination == parent
        or destination.is_relative_to(run_directory)
        or run_directory.is_relative_to(destination)
    ):
        raise ProtocolError("MONO_CI_B0_PSI_SCORING_OUTPUT_MUST_BE_SEPARATE")

    assessment: dict[str, Any] = {
        "schema_version": "MONO_CI_B0_PSI_SCORE_V1",
        "study_id": run["study_id"],
        "execution_id": run["execution_id"],
        "source_execution_sha256": sha256_file(result_path),
        "scoring_status": "NOT_EVALUABLE",
        "reference_status": "NOT_ESTABLISHED",
        "reason": "NO_SEPARATE_APPROVED_SCORER_REFERENCE",
        "metric_statuses": run["metrics"],
        "numeric_results": {},
    }
    validate_payload(SCORING_SCHEMA, assessment)
    destination.mkdir(parents=True, exist_ok=False)
    assessment_path = destination / "scoring_assessment.json"
    assessment_path.write_bytes(pretty_json_bytes(assessment))
    digest = sha256_file(assessment_path)
    (destination / "scoring_assessment.json.sha256").write_text(
        f"{digest}  scoring_assessment.json\n", encoding="utf-8"
    )
    inventory = {
        path.relative_to(destination).as_posix(): sha256_file(path)
        for path in sorted(destination.iterdir())
        if path.is_file()
    }
    (destination / "SHA256SUMS").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(inventory.items())),
        encoding="utf-8",
    )
    verify_scoring_assessment(destination)
    return assessment


def verify_scoring_assessment(output_root: Path) -> dict[str, Any]:
    """Read back the separate assessment and verify its write-once seals."""
    if output_root.is_symlink():
        raise ContractValidationError("MONO_CI_B0_PSI_SCORING_OUTPUT_SYMLINK_FORBIDDEN")
    root = output_root.resolve(strict=True)
    if any(path.is_symlink() for path in root.iterdir()):
        raise ContractValidationError("MONO_CI_B0_PSI_SCORING_OUTPUT_SYMLINK_FORBIDDEN")
    assessment_path = root / "scoring_assessment.json"
    try:
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError("MONO_CI_B0_PSI_SCORING_ASSESSMENT_READ_FAILED") from error
    if not isinstance(assessment, dict):
        raise ContractValidationError("MONO_CI_B0_PSI_SCORING_ASSESSMENT_OBJECT_REQUIRED")
    payload = cast(dict[str, Any], assessment)
    validate_payload(SCORING_SCHEMA, payload)
    digest = sha256_file(assessment_path)
    sidecar = (root / "scoring_assessment.json.sha256").read_text(encoding="utf-8").strip()
    if sidecar != f"{digest}  scoring_assessment.json":
        raise ContractValidationError("MONO_CI_B0_PSI_SCORING_ASSESSMENT_SEAL_MISMATCH")
    declared: dict[str, str] = {}
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        pieces = line.split("  ", 1)
        if len(pieces) != 2 or pieces[1] in declared:
            raise ContractValidationError("MONO_CI_B0_PSI_SCORING_INVENTORY_INVALID")
        declared[pieces[1]] = pieces[0]
    actual = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in root.iterdir()
        if path.is_file() and path.name != "SHA256SUMS"
    }
    if declared != actual:
        raise ContractValidationError("MONO_CI_B0_PSI_SCORING_INVENTORY_MISMATCH")
    return payload


def main(argv: list[str] | None = None) -> int:
    """Run the separate scorer-readiness gate for a sealed DEVELOPMENT result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = score_development_run(args.run, args.output)
    except (ContractValidationError, ProtocolError) as error:
        print(json.dumps({"scoring_status": "NOT_EVALUABLE", "error": str(error)}))
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


__all__ = ["score_development_run", "verify_scoring_assessment"]


if __name__ == "__main__":
    sys.exit(main())
