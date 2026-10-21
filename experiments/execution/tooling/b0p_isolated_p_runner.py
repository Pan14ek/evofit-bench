"""Run the frozen Method P implementation in its restricted container."""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes
from experiments.execution.tooling.p_adaptation import (
    run_adaptation,
    verify_v3_p_bundle,
)
from experiments.execution.tooling.p_applicability import EvidenceLedger
from experiments.execution.tooling.p_input_validation import (
    ValidationStatus,
    load_verified_source_manifest,
)
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3
from experiments.execution.tooling.sealing import seal_prediction
from experiments.pilots.pilot02_testonly_execution import (
    Pilot02TestOnlyTrustContext,
    build_testonly_evidence_ledger,
    build_testonly_fact_verifier,
    testonly_completeness_verifier,
    verify_testonly_sidecar_signature,
)


def _write_once(path: Path, payload: Any) -> str:
    """Write canonical run output without replacing an existing artifact."""
    content = pretty_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    path.chmod(0o444)
    return sha256_bytes(content)


def _adaptation_trace(
    bundle: Any,
    result: Any,
    *,
    evidence_sidecar: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Serialize the existing P result; this wrapper does not add a decision rule."""
    input_manifest = (bundle.root / "method_input_v3.json").read_bytes()
    return {
        "schema_version": 1,
        "trace_type": "development_method_p_execution",
        "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        "input_manifest_sha256": sha256_bytes(input_manifest),
        "policy_source_revision": bundle.manifest["policy_source_revision"],
        "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
        "snapshot_validation": bundle.snapshot_validation.to_dict(),
        "architecture": {
            "before_commit": bundle.snapshot["architecture"]["before_commit"],
            "after_commit": bundle.snapshot["architecture"]["after_commit"],
        },
        "before_applicability": result.before_applicability.to_dict(),
        "after_applicability": result.after_applicability.to_dict(),
        "impact_assessment": result.impact.to_dict(),
        "current_pairs": [item.to_dict() for item in result.current_pairs],
        "candidate_pairs": [item.to_dict() for item in result.candidate_pairs],
        "current_coverage": result.current_coverage.to_dict(),
        "candidate_coverage": (
            result.candidate_coverage.to_dict() if result.candidate_coverage is not None else None
        ),
        "operation_plan": result.operation_plan.to_dict(),
        "candidate_configuration": (
            dict(result.candidate) if isinstance(result.candidate, Mapping) else None
        ),
        "candidate_sha256": result.candidate_sha256,
        "governance": result.governance.to_dict(),
        "candidate_v1": dict(result.candidate_v1) if result.candidate_v1 is not None else None,
        "prediction_v1": dict(result.prediction_v1) if result.prediction_v1 is not None else None,
        "adaptation_evidence_trust_scope": result.evidence_trust_scope,
        "adaptation_evidence_sidecar_supplied": evidence_sidecar is not None,
        "adaptation_evidence_sidecar_sha256": (
            evidence_sidecar.get("sidecar_sha256") if evidence_sidecar is not None else None
        ),
        "independent_pair_proof_supplied": bool(
            evidence_sidecar
            and isinstance(evidence_sidecar.get("payload"), Mapping)
            and evidence_sidecar["payload"].get("pair_proofs")
        ),
        "unresolved_prerequisites": sorted(
            set(result.governance.to_dict()["reason_codes"])
            | set(result.operation_plan.hold_reasons)
            | set(result.operation_plan.reject_reasons)
        ),
    }


def run_p(
    input_directory: Path,
    output_directory: Path,
    *,
    architecture_source_sha: str,
    expected_bundle_sha256: str,
    evidence_sidecar_path: Path | None = None,
) -> dict[str, Any]:
    """Run frozen P in isolation, with optional contract-verified TEST_ONLY evidence."""
    started_ns = time.perf_counter_ns()
    evidence_sidecar: dict[str, Any] | None = None
    trust_context: Pilot02TestOnlyTrustContext | None = None
    fact_verifier = None
    completeness_verifier = None
    evidence_ledger = EvidenceLedger({}, {}, {})
    if evidence_sidecar_path is not None:
        evidence_sidecar = json.loads(evidence_sidecar_path.read_bytes())
        if not isinstance(evidence_sidecar, dict) or not verify_testonly_sidecar_signature(
            evidence_sidecar
        ):
            raise ValueError("TEST_ONLY adaptation evidence signature is invalid")
        if evidence_sidecar.get("input_bundle_sha256") != expected_bundle_sha256:
            raise ValueError("TEST_ONLY adaptation evidence is bound to another method input")
        if evidence_sidecar.get("architecture_after_sha") != architecture_source_sha:
            raise ValueError("TEST_ONLY adaptation evidence is bound to another architecture")
        trust_context = Pilot02TestOnlyTrustContext()
        method_manifest = verify_method_bundle_v3(input_directory, expected_method_id="P")
        snapshot = json.loads((input_directory / "architecture-policy-snapshot.json").read_bytes())
        source_manifest, source_report = load_verified_source_manifest(
            snapshot, method_manifest, input_directory
        )
        if source_report.status is not ValidationStatus.VALID:
            raise ValueError("Method P source manifest failed TEST_ONLY verification")
        evidence_ledger = build_testonly_evidence_ledger(
            snapshot,
            source_manifest,
            source_integrity_valid=True,
            trust_context=trust_context,
        )
        fact_verifier = build_testonly_fact_verifier(
            evidence_sidecar, expected_input_bundle_sha256=expected_bundle_sha256
        )
        completeness_verifier = testonly_completeness_verifier
    bundle = verify_v3_p_bundle(
        input_directory,
        evidence_ledger=evidence_ledger,
        trust_context=trust_context,
        fact_verifier=fact_verifier,
        completeness_verifier=completeness_verifier,
    )
    if bundle.manifest.get("bundle_sha256") != expected_bundle_sha256:
        raise ValueError("Method P input bundle digest does not match the execution manifest")
    if bundle.snapshot.get("architecture", {}).get("after_commit") != architecture_source_sha:
        raise ValueError("Method P input is bound to another architecture revision")
    adaptation_started_ns = time.perf_counter_ns()
    result = run_adaptation(bundle, evidence_context=evidence_sidecar)
    adaptation_duration_ns = time.perf_counter_ns() - adaptation_started_ns
    method_duration_ns = time.perf_counter_ns() - started_ns
    trace = _adaptation_trace(bundle, result, evidence_sidecar=evidence_sidecar)
    trace["method_execution_time_ns"] = method_duration_ns
    trace["adaptation_time_ns"] = adaptation_duration_ns
    trace_sha256 = _write_once(output_directory / "method_p_trace.json", trace)

    candidate_sha256 = None
    candidate_validation = "NOT_MATERIALIZED"
    if isinstance(result.candidate, Mapping):
        candidate = dict(result.candidate)
        validate_payload("p_candidate_configuration_v1.schema.json", candidate)
        candidate_sha256 = _write_once(output_directory / "candidate_configuration.json", candidate)
        raw_status = str(candidate.get("candidate_validation", {}).get("status", "unknown"))
        candidate_validation = {
            "valid": "VALID",
            "invalid": "INVALID",
            "failed": "INVALID",
            "not_run": "UNKNOWN",
        }.get(raw_status, "UNKNOWN")

    governance_result = result.governance.result.value
    prediction_status = (
        "NOT_EMITTED_GOVERNANCE_HOLD"
        if governance_result == "HOLD"
        else f"NOT_EMITTED_{governance_result}"
    )
    prediction_sha256 = None
    if result.prediction_v1 is not None:
        sealed = seal_prediction(dict(result.prediction_v1), output_directory / "prediction")
        prediction_status = "SEALED"
        prediction_sha256 = sealed.sha256
    else:
        marker = {
            "schema_version": 1,
            "method_id": "P",
            "architecture_source_sha": architecture_source_sha,
            "input_bundle_sha256": expected_bundle_sha256,
            "prediction_status": prediction_status,
            "governance_result": governance_result,
            "reason_codes": list(result.governance.to_dict()["reason_codes"]),
            "method_trace_sha256": trace_sha256,
        }
        prediction_sha256 = _write_once(output_directory / "prediction_not_emitted.json", marker)

    execution = {
        "schema_version": 1,
        "method_id": "P",
        "method_version": "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
        "architecture_source_sha": architecture_source_sha,
        "input_bundle_sha256": expected_bundle_sha256,
        "method_execution_time_ns": method_duration_ns,
        "adaptation_time_ns": adaptation_duration_ns,
        "candidate_validation": candidate_validation,
        "candidate_configuration_sha256": candidate_sha256,
        "governance_result": governance_result,
        "governance_reason_codes": list(result.governance.to_dict()["reason_codes"]),
        "prediction_status": prediction_status,
        "prediction_sha256": prediction_sha256,
        "method_trace_sha256": trace_sha256,
        "adaptation_evidence_sidecar_sha256": (
            evidence_sidecar.get("sidecar_sha256") if evidence_sidecar is not None else None
        ),
        "adaptation_evidence_trust_scope": result.evidence_trust_scope,
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
    }
    execution_sha256 = _write_once(output_directory / "execution_result.json", execution)
    return {**execution, "execution_result_sha256": execution_sha256}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("/input"))
    parser.add_argument("--output", type=Path, default=Path("/output"))
    parser.add_argument("--architecture-source-sha", required=True)
    parser.add_argument("--expected-bundle-sha256", required=True)
    parser.add_argument("--evidence-sidecar", type=Path)
    args = parser.parse_args()
    result = run_p(
        args.input,
        args.output,
        architecture_source_sha=args.architecture_source_sha,
        expected_bundle_sha256=args.expected_bundle_sha256,
        evidence_sidecar_path=args.evidence_sidecar,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
