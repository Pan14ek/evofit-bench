"""Bounds and verifies the PILOT-02 TEST_ONLY continuation source."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from experiments.execution.tooling.hashing import sha256_bytes
from experiments.execution.tooling.p_adaptation_evidence import verify_adaptation_evidence
from experiments.execution.tooling.p_input_validation import SourceReference
from experiments.pilots.pilot02_testonly_execution import (
    ADAPTATION_VERIFIER_ID,
    Pilot02TestOnlyTrustContext,
    build_adaptation_sidecar,
    create_testonly_policy_source,
)
from experiments.pilots.run_pilot02_method_p import (
    _candidate_template_match,
    _exp02_execution_evidence_admission,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_SOURCE = ROOT / "experiments/execution/policy-pilot/v1/source"
TARGET_IDS = ["AC_LAYERING", "AC_MODULE_STRUCTURE"]
BEFORE_SHA = "b78b0967be937634b7762baccf5ac6892b279a73"
AFTER_SHA = "3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306"
CATALOG_SHA = "8c5bd8fffe3bdb2af8fb85f8d0012bc34673f72866e52daed99fab96f9763011"
AS_OF = "2026-10-14T00:00:00Z"


def test_execution_evidence_admission_trace_matches_verified_sidecar_scope() -> None:
    assert _exp02_execution_evidence_admission(sidecar_supplied=True, trust_scope="TEST_ONLY") == (
        "admitted_execution_evidence",
        True,
    )


def test_semantic_proof_is_not_reusable_after_candidate_row_changes() -> None:
    candidate_record = {
        "candidate_profile_binding": {
            "status": "matched",
            "candidate_row_sha256": "a" * 64,
            "template_sha256": "b" * 64,
            "evaluator_artifact_sha256": "c" * 64,
        }
    }

    assert (
        _candidate_template_match(
            template_preflight_verified=True,
            candidate_record=candidate_record,
            template_evaluator_artifact_sha256="c" * 64,
        )
        is False
    )


def test_sidecar_carries_supplied_semantic_pair_proof_through_testonly_verifier() -> None:
    source_digests = {
        "P_CAPABILITIES": "a" * 64,
        "P_TRACEABILITY": "b" * 64,
        "SYN_REGISTRY_SOURCE": "c" * 64,
        "SYN_CHARTER_SOURCE": "d" * 64,
    }
    bundle_sha = "e" * 64
    policy_bundle_sha = "f" * 64
    snapshot = {
        "architecture": {
            "before_commit": BEFORE_SHA,
            "after_commit": AFTER_SHA,
            "evaluation_as_of": AS_OF,
        },
        "policy_registry": {
            "scope": "service:synth",
            "source_id": "SYN_REGISTRY_SOURCE",
            "authority_charter_source_id": "SYN_CHARTER_SOURCE",
            "registry_version": "TEST_ONLY_V1",
        },
        "policies": [],
        "facts": [],
        "completeness_claims": [],
    }
    bundle = SimpleNamespace(
        snapshot=snapshot,
        manifest={
            "bundle_sha256": bundle_sha,
            "policy_source_revision": "SYN_POLICY_REV_1",
            "policy_bundle_sha256": policy_bundle_sha,
        },
        source_digests=source_digests,
        obligations=({"id": "AC_LAYERING"}, {"id": "AC_MODULE_STRUCTURE"}),
        trace_graph=SimpleNamespace(graph_sha256="1" * 64),
        snapshot_validation=SimpleNamespace(snapshot_digest="2" * 64),
        cost_model={
            "schema_version": 1,
            "model_version": "TEST_ONLY_COST_V1",
            "authority_status": "TEST_ONLY",
            "max_incremental_cost": 1,
            "max_search_nodes": 1,
            "candidate_costs": {},
        },
        templates=(),
    )
    semantic_proof = {
        "representation_id": "REP_A01_ARCH_INTERNAL_LAYERING_CI",
        "obligation_id": "AC_LAYERING",
        "status": "VALID",
        "subject_sha256": "3" * 64,
        "verifier_id": ADAPTATION_VERIFIER_ID,
        "source_bindings": [
            {"source_id": "P_CAPABILITIES", "sha256": source_digests["P_CAPABILITIES"]},
            {"source_id": "P_TRACEABILITY", "sha256": source_digests["P_TRACEABILITY"]},
        ],
        "evidence_refs": ["PILOT02_SEMANTIC_REPORT_AC_LAYERING"],
        "reason_codes": [],
    }
    trust = Pilot02TestOnlyTrustContext()
    sidecar = build_adaptation_sidecar(
        bundle,
        assumptions={"transition": {"target_obligation_ids": TARGET_IDS}},
        evaluator_evidence=[],
        b0_representation={"id": "REP_A0_ARCH_CI_LAYERING"},
        b0_evaluator_evidence={"missing_targets": []},
        extra_artifacts={"semantic/report.json": b"{}"},
        semantic_pair_proofs=[semantic_proof],
    )
    verified = verify_adaptation_evidence(
        sidecar,
        expected_bindings={
            "input_bundle_sha256": bundle_sha,
            "architecture_before_sha": BEFORE_SHA,
            "architecture_after_sha": AFTER_SHA,
            "policy_source_revision": "SYN_POLICY_REV_1",
            "policy_bundle_sha256": policy_bundle_sha,
            "evaluation_as_of": AS_OF,
            "scope": "service:synth",
        },
        expected_source_digests=source_digests,
        verifier_registry=trust.adaptation_evidence_verifiers,
        allow_test_only=True,
        expected_trust_scope="TEST_ONLY",
    )

    assert verified is not None
    proofs = verified.payload["pair_proofs"]
    assert len(proofs) == 2
    assert proofs[1]["representation_id"] == semantic_proof["representation_id"]
    assert proofs[1]["status"] == "VALID"
    assert _exp02_execution_evidence_admission(sidecar_supplied=False, trust_scope="TEST_ONLY") == (
        "not_admitted",
        False,
    )
    assert _exp02_execution_evidence_admission(sidecar_supplied=True, trust_scope=None) == (
        "not_admitted",
        False,
    )


def _create_source(tmp_path: Path) -> tuple[Path, Any]:
    """Build the same isolated source shape used by the prospective run."""
    return create_testonly_policy_source(
        POLICY_SOURCE,
        tmp_path,
        evaluation_as_of=AS_OF,
        before_sha=BEFORE_SHA,
        after_sha=AFTER_SHA,
        obligation_catalog_sha256=CATALOG_SHA,
        target_obligation_ids=TARGET_IDS,
    )


def _reference(source_id: str, path: Path, kind: str) -> SourceReference:
    content = path.read_bytes()
    return SourceReference(
        source_id=source_id,
        kind=kind,
        path=path.relative_to(path.parents[4]).as_posix(),
        sha256=sha256_bytes(content),
        content=content,
    )


def test_source_is_isolated_and_limited_to_declared_obligations(tmp_path: Path) -> None:
    original_registry = (POLICY_SOURCE / "fitness/policy/registry.json").read_bytes()
    original_charter = (POLICY_SOURCE / "fitness/policy/authority-charter.json").read_bytes()

    source, trust = _create_source(tmp_path)

    registry = json.loads((source / "fitness/policy/registry.json").read_bytes())
    policies = registry["policies"]
    claims = json.loads((source / "fitness/policy/completeness-claims.json").read_bytes())
    assert {item["obligation_ids"][0] for item in policies} == set(TARGET_IDS)
    assert all(item["normative_status"] == "APPROVED" for item in policies)
    assert all(item["applies_to_states"] == ["after"] for item in policies)
    assert [item["id"] for item in claims] == sorted(item["id"] for item in claims)
    assert trust.trust_scope == "TEST_ONLY"
    assert (POLICY_SOURCE / "fitness/policy/registry.json").read_bytes() == original_registry
    assert (
        POLICY_SOURCE / "fitness/policy/authority-charter.json"
    ).read_bytes() == original_charter


def test_testonly_signatures_verify_and_tampering_is_unresolved(tmp_path: Path) -> None:
    source, trust = _create_source(tmp_path)
    registry = json.loads((source / "fitness/policy/registry.json").read_bytes())
    policy = registry["policies"][0]
    charter_path = source / "fitness/policy/authority-charter.json"
    approval_path = source / "fitness/policy/approvals" / f"{policy['approval_source_id']}.json"
    charter = json.loads(charter_path.read_bytes())
    charter_source = _reference("CHARTER", charter_path, "AUTHORITY_CHARTER")
    approval_source = _reference(str(policy["approval_source_id"]), approval_path, "APPROVAL")

    assert trust.verify_charter(charter, charter_source, AS_OF) is True
    assert trust.verify_approval(policy, charter, approval_source, AS_OF) is True

    tampered = copy.deepcopy(json.loads(approval_path.read_bytes()))
    tampered["signature"] = "0" * 64
    tampered_source = SourceReference(
        source_id=approval_source.source_id,
        kind=approval_source.kind,
        path=approval_source.path,
        sha256=approval_source.sha256,
        content=json.dumps(tampered).encode("utf-8"),
    )
    assert trust.verify_approval(policy, charter, tampered_source, AS_OF) is None


def test_per_obligation_applicability_states_are_preserved_in_testonly_policy_source(
    tmp_path: Path,
) -> None:
    """V2 keeps layering applicable in A0 while module structure starts in A0.1."""
    source, _ = create_testonly_policy_source(
        POLICY_SOURCE,
        tmp_path,
        evaluation_as_of=AS_OF,
        before_sha=BEFORE_SHA,
        after_sha=AFTER_SHA,
        obligation_catalog_sha256=CATALOG_SHA,
        target_obligation_ids=TARGET_IDS,
        applicability_by_obligation={
            "AC_LAYERING": {"before": "ACTIVE", "after": "ACTIVE"},
            "AC_MODULE_STRUCTURE": {"before": "INACTIVE", "after": "ACTIVE"},
        },
    )

    registry = json.loads((source / "fitness/policy/registry.json").read_bytes())
    policies = {row["obligation_ids"][0]: row for row in registry["policies"]}
    assert policies["AC_LAYERING"]["applies_to_states"] == ["before", "after"]
    assert policies["AC_MODULE_STRUCTURE"]["applies_to_states"] == ["after"]
    assert all(row["kind"] == "UNCONDITIONAL_MANDATE" for row in policies.values())
    assert "condition_ref" not in policies["AC_MODULE_STRUCTURE"]
