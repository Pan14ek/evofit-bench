"""Adversarial checks for the evidence-sufficient E1 execution envelope."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.b0p_e1_execution import (
    B0PE1ExecutionError,
    _execution_status,
    _require_new_run_directory,
    _rq2_obligation_table,
    _verify_e1_method_input,
    _verify_no_oracle_contamination,
    validate_e1_rq1_gate,
    validate_e1_sidecar_binding,
    validate_rq2_denominator,
)
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_input_validation import SourceReference
from experiments.pilots.pilot02_testonly_execution import (
    ADAPTATION_HMAC_KEY,
    ADAPTATION_VERIFIER_ID,
    build_testonly_fact_verifier,
)

BEFORE_SHA = "b78b0967be937634b7762baccf5ac6892b279a73"
AFTER_SHA = "3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306"
BUNDLE_SHA = "a" * 64
POLICY_REVISION = "PILOT02_TEST_ONLY_e1-calibration-01"
DENOMINATOR = [
    "P_EXT_LATENCY",
    "R_BUSINESS_FAILURE",
    "R_HTTP_5XX",
    "R_LOCAL_ATOMICITY",
    "AC_LAYERING",
    "AC_MODULE_STRUCTURE",
]


def _signed_sidecar(
    *,
    artifact_path: str = "evidence/source_fact_verification.json",
    artifact_content: bytes | None = None,
    policy_revision: str = POLICY_REVISION,
    input_bundle_sha256: str = BUNDLE_SHA,
    before_sha: str = BEFORE_SHA,
    after_sha: str = AFTER_SHA,
) -> dict[str, Any]:
    if artifact_content is None:
        artifact_content = json.dumps(_fact_report()).encode()
    unsigned = {
        "schema_version": 2,
        "contract_id": "P_ADAPTATION_EVIDENCE_V2",
        "input_bundle_sha256": input_bundle_sha256,
        "architecture_before_sha": before_sha,
        "architecture_after_sha": after_sha,
        "policy_source_revision": policy_revision,
        "policy_bundle_sha256": "b" * 64,
        "evaluation_as_of": "2026-10-14T00:00:00Z",
        "scope": "service:pilot02",
        "verifier_id": ADAPTATION_VERIFIER_ID,
        "payload": {
            "artifact_bytes": [
                {
                    "path": artifact_path,
                    "sha256": sha256_bytes(artifact_content),
                    "content_base64": base64.b64encode(artifact_content).decode("ascii"),
                }
            ]
        },
    }
    digest = sha256_bytes(canonical_json_bytes(unsigned))
    return {
        **unsigned,
        "sidecar_sha256": digest,
        "signature": hmac.new(
            ADAPTATION_HMAC_KEY, digest.encode("ascii"), hashlib.sha256
        ).hexdigest(),
    }


def _fact_report() -> dict[str, Any]:
    fields = {
        "before_module_names": ["app", "app.api"],
        "after_module_names": ["app", "app.modules"],
        "added_module_names": ["app.modules"],
        "removed_module_names": ["app.api"],
    }
    return {
        "schema_version": 1,
        "assessment": "VERIFIED_GIT_INVENTORY",
        "verification_scope": "PINNED_GIT_PYTHON_MODULE_INVENTORY_ONLY",
        "before_sha": BEFORE_SHA,
        "after_sha": AFTER_SHA,
        "p_input_bundle_sha256": BUNDLE_SHA,
        "field_results": {
            field: {"matches": True, "expected": value, "reported": value}
            for field, value in fields.items()
        },
    }


def _p_bundle(**updates: Any) -> dict[str, Any]:
    return {
        "bundle_sha256": BUNDLE_SHA,
        "policy_source_revision": POLICY_REVISION,
        **updates,
    }


def test_e1_sidecar_requires_signature_digest_source_and_exact_run_binding() -> None:
    sidecar = _signed_sidecar()
    validate_e1_sidecar_binding(
        sidecar,
        _p_bundle(),
        input_bundle_sha256=BUNDLE_SHA,
        run_id="e1-calibration-01",
        architecture_before_sha=BEFORE_SHA,
        architecture_after_sha=AFTER_SHA,
    )

    for changed_sidecar, expected_bundle in (
        ({**sidecar, "signature": "0" * 64}, BUNDLE_SHA),
        (_signed_sidecar(policy_revision="PILOT02_TEST_ONLY_other-run"), BUNDLE_SHA),
        (_signed_sidecar(before_sha="c" * 40), BUNDLE_SHA),
        (sidecar, "d" * 64),
    ):
        with pytest.raises(B0PE1ExecutionError, match="invalid or bound to another run"):
            validate_e1_sidecar_binding(
                changed_sidecar,
                _p_bundle(),
                input_bundle_sha256=expected_bundle,
                run_id="e1-calibration-01",
                architecture_before_sha=BEFORE_SHA,
                architecture_after_sha=AFTER_SHA,
            )


def test_git_fact_verifier_recomputes_each_reported_inventory_field() -> None:
    sidecar = _signed_sidecar()
    verify = build_testonly_fact_verifier(sidecar, expected_input_bundle_sha256=BUNDLE_SHA)
    after = json.dumps({"state": "after", "commit_sha": AFTER_SHA}).encode()
    source = SourceReference(
        source_id="ARCH_AFTER",
        kind="ARCHITECTURE_SOURCE",
        path="evidence/arch_after.json",
        sha256=sha256_bytes(after),
        state="after",
        revision=AFTER_SHA,
        content=after,
    )
    fact = {
        "predicate": "component.python_module_identity",
        "state": "after",
        "value": ["app", "app.modules"],
    }
    snapshot = {"architecture": {"before_commit": BEFORE_SHA, "after_commit": AFTER_SHA}}
    assert verify(fact, {"ARCH_AFTER": source}, snapshot) is True
    assert (
        verify(
            fact,
            {"ARCH_AFTER": source},
            {"architecture": {"before_commit": BEFORE_SHA, "after_commit": "c" * 40}},
        )
        is False
    )

    tampered_report = _fact_report()
    tampered_report["field_results"]["after_module_names"]["reported"] = ["app", "tampered"]
    invalid_sidecar = _signed_sidecar(artifact_content=json.dumps(tampered_report).encode())
    with pytest.raises(ValueError, match="field is not verified"):
        build_testonly_fact_verifier(invalid_sidecar, expected_input_bundle_sha256=BUNDLE_SHA)


def test_rq2_requires_exact_complete_denominator_and_never_fabricates_percent() -> None:
    rows = [
        {
            "obligation_id": obligation,
            "applicability": "APPLICABLE_PUBLIC_DA01_DENOMINATOR",
            "B0_coverage": "UNKNOWN",
            "P_candidate_potential": "UNKNOWN",
            "P_governance_accepted_coverage": "ABSENT",
            "exact_pair_evidence": [],
            "final_result": "UNKNOWN",
            "missing_proof": "No pair proof",
        }
        for obligation in DENOMINATOR
    ]
    payload = {
        "status": "UNKNOWN",
        "required_obligation_set_bound": True,
        "same_denominator_for_arms": True,
        "coverage_percentage": None,
        "rows": rows,
    }
    validate_rq2_denominator(payload, DENOMINATOR)
    with pytest.raises(B0PE1ExecutionError, match="incomplete or unbound denominator"):
        validate_rq2_denominator({**payload, "rows": rows[:-1]}, DENOMINATOR)
    with pytest.raises(B0PE1ExecutionError, match="incomplete or unbound denominator"):
        validate_rq2_denominator({**payload, "coverage_percentage": 0.33}, DENOMINATOR)


def test_candidate_potential_is_diagnostic_when_governance_holds() -> None:
    pair = {
        "representation_id": "REP_A01_ARCH_INTERNAL_LAYERING_CI",
        "obligation_id": "AC_LAYERING",
        "independent_verification": "VERIFIED",
        "evaluator_artifact_sha256": "c" * 64,
    }
    detail = _rq2_obligation_table(
        "e1-calibration-01",
        DENOMINATOR,
        {"pairs": [pair]},
        {"docker_exit_status": 0},
        {"candidate_validation": "VALID", "governance_result": "HOLD"},
        {
            "candidate_pairs": [
                {"representation_id": pair["representation_id"], "obligation_id": "AC_LAYERING"}
            ]
        },
        {
            "representations": [
                {
                    "id": pair["representation_id"],
                    "active": True,
                    "evaluator_artifact": {"sha256": "c" * 64},
                }
            ]
        },
    )
    row = next(item for item in detail["rows"] if item["obligation_id"] == "AC_LAYERING")
    assert row["P_candidate_potential"] == "DIAGNOSTIC_ONLY"
    assert row["P_governance_accepted_coverage"] == "ABSENT"
    assert row["final_result"] == "UNKNOWN"
    assert detail["coverage_percentage"] is None


def test_oracle_contamination_and_historical_overwrite_are_rejected(tmp_path: Path) -> None:
    p_input = tmp_path / "p-input"
    p_input.mkdir()
    (p_input / "method_input_v3.json").write_text(
        json.dumps({"files": [{"path": "ground_truth.yaml"}]})
    )
    with pytest.raises(B0PE1ExecutionError, match="prohibited oracle"):
        _verify_no_oracle_contamination(p_input, _signed_sidecar())

    existing = tmp_path / "existing-run"
    existing.mkdir()
    with pytest.raises(B0PE1ExecutionError, match="write-once"):
        _require_new_run_directory(existing)


def test_e1_p_input_readback_requires_directory_and_exact_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import experiments.execution.tooling.b0p_e1_execution as e1

    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "p-input").mkdir()
    bundle = {"bundle_sha256": BUNDLE_SHA, "policy_source_revision": POLICY_REVISION}
    calls: list[tuple[Path, str]] = []

    def verify_method_input(path: Path, *, expected_method_id: str) -> dict[str, str]:
        calls.append((path, expected_method_id))
        return bundle

    monkeypatch.setattr(e1, "verify_method_bundle_v3", verify_method_input)
    evidence = {
        "p_input_path": "p-input",
        "p_input_bundle_sha256": BUNDLE_SHA,
        "p_policy_source_revision": POLICY_REVISION,
    }

    assert _verify_e1_method_input(run_root, evidence) == bundle
    assert calls == [(run_root / "p-input", "P")]

    (run_root / "p-input-file").write_text("not a directory")
    with pytest.raises(B0PE1ExecutionError, match="regular directory"):
        _verify_e1_method_input(run_root, {**evidence, "p_input_path": "p-input-file"})
    with pytest.raises(B0PE1ExecutionError, match="bundle digest changed"):
        _verify_e1_method_input(run_root, {**evidence, "p_input_bundle_sha256": "b" * 64})


def test_hold_is_a_completed_method_outcome_when_both_arms_and_evaluators_ran() -> None:
    assert (
        _execution_status(
            {"docker_exit_status": 0},
            {"docker_exit_status": 0, "prediction_status": "NOT_EMITTED_GOVERNANCE_HOLD"},
            [{"evaluator_id": "import_linter"}, {"evaluator_id": "pytest_architecture"}],
        )
        == "EXECUTED_COMPLETE"
    )
    assert (
        _execution_status(
            {"docker_exit_status": 0},
            {"docker_exit_status": 0},
            [{"evaluator_id": "import_linter"}],
        )
        == "EXECUTED_PARTIAL"
    )


def test_hold_cannot_invoke_canonical_rq1_or_emit_score() -> None:
    validate_e1_rq1_gate(
        {"status": "NOT_EVALUABLE", "scorer_invoked": False, "results": {}},
        p_prediction_status="NOT_EMITTED_GOVERNANCE_HOLD",
    )
    with pytest.raises(B0PE1ExecutionError, match="cannot score or manufacture"):
        validate_e1_rq1_gate(
            {"status": "SCORED", "scorer_invoked": True, "results": {"B0": {}}},
            p_prediction_status="NOT_EMITTED_GOVERNANCE_HOLD",
        )
