"""Synthetic trust/evidence helpers for applicability tests only."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_applicability import (
    EvidenceLedger,
    EvidenceProof,
    ProofStatus,
)
from experiments.execution.tooling.p_input_validation import (
    SnapshotValidationResult,
    ValidationStatus,
)

SNAPSHOT_FIXTURE = Path(__file__).parents[1] / "fixtures/p_input_contract_v11_snapshot.json"


def snapshot_fixture() -> dict[str, Any]:
    """Load a fresh copy of the public synthetic SPEC 01 contract fixture."""
    return copy.deepcopy(json.loads(SNAPSHOT_FIXTURE.read_text(encoding="utf-8")))


def validation_result() -> SnapshotValidationResult:
    """Return a synthetic SPEC 01 summary for isolated engine tests."""
    return SnapshotValidationResult(
        schema_status=ValidationStatus.VALID,
        integrity_status=ValidationStatus.VALID,
        authority_status=ValidationStatus.UNDETERMINED,
        fact_status=ValidationStatus.UNDETERMINED,
        completeness_status=ValidationStatus.UNDETERMINED,
        reason_codes=("SYNTHETIC_TEST_EVIDENCE",),
        evidence_refs=(),
        snapshot_digest=None,
    )


def add_fact(
    snapshot: dict[str, Any],
    *,
    fact_id: str,
    predicate: str,
    value: Any,
    subject: str = "application",
    scope: str = "application",
    state: str = "after",
    epistemic_kind: str = "DECLARED",
    source_ids: list[str] | None = None,
) -> None:
    fact: dict[str, Any] = {
        "id": fact_id,
        "state": state,
        "predicate": predicate,
        "subject": subject,
        "scope": scope,
        "value": value,
        "epistemic_kind": epistemic_kind,
        "source_ids": source_ids or ["ARCH_OBS"],
    }
    if epistemic_kind == "EXTRACTED":
        fact["method_id"] = "git_tree_py_module_inventory_v1"
    snapshot["facts"].append(fact)


def add_policy(
    snapshot: dict[str, Any],
    *,
    policy_id: str = "POL_TEST",
    obligation_id: str = "AC_PUBLIC_API",
    kind: str = "UNCONDITIONAL_MANDATE",
    status: str = "APPROVED",
    condition_ref: str | None = None,
    polarity: str = "REQUIRED",
    target_policy_ids: list[str] | None = None,
    applies_to_states: list[str] | None = None,
    scope: str = "application",
    approval_id: str | None = None,
    effective_from: str = "2026-10-01T00:00:00Z",
    effective_until: str | None = None,
) -> dict[str, Any]:
    source_id = approval_id or f"APPROVAL_{policy_id}"
    policy: dict[str, Any] = {
        "id": policy_id,
        "kind": kind,
        "normative_status": status,
        "obligation_ids": [obligation_id],
        "proposition": "Synthetic applicability policy for tests.",
        "scope": scope,
        "issuer_role": "architecture_authority",
        "approval_source_id": None if status == "DRAFT" else source_id,
        "source_id": "REGISTRY",
        "effective_from": effective_from,
        "effective_until": effective_until,
        "applies_to_states": applies_to_states or ["after"],
        "target_policy_ids": target_policy_ids or [],
        "proposition_polarity": polarity,
    }
    if condition_ref is not None:
        policy["condition_ref"] = condition_ref
    snapshot["policies"].append(policy)
    if status != "DRAFT":
        snapshot["sources"].append(
            {
                "id": source_id,
                "path": f"policies/approvals/{source_id}.json",
                "sha256": (str(len(source_id)) * 64)[:64],
                "kind": "APPROVAL",
                "producer": "synthetic_test_only",
            }
        )
    return policy


def close_registry_for(
    snapshot: dict[str, Any],
    obligation_id: str,
    *,
    state: str = "after",
    scope: str = "application",
    evidence_id: str | None = None,
    fact_type: str | None = None,
    assumptions: list[str] | None = None,
) -> dict[str, Any]:
    claim_id = f"CLOSURE_{obligation_id}_{state.upper()}"
    evidence_id = evidence_id or f"EVIDENCE_{claim_id}"
    revision = snapshot["architecture"]["before_commit" if state == "before" else "after_commit"]
    snapshot["policy_registry"]["closure"] = "CLAIMED_CLOSED"
    snapshot["policy_registry"]["closure_claim_id"] = claim_id
    snapshot["sources"].append(
        {
            "id": evidence_id,
            "path": f"policies/evidence/{evidence_id}.json",
            "sha256": "5" * 64,
            "kind": "EVIDENCE",
            "producer": "synthetic_test_only",
        }
    )
    claim = {
        "id": claim_id,
        "kind": "AUTHORITATIVE_POLICY_REGISTRY",
        "state": state,
        "fact_type": fact_type or f"obligation:{obligation_id}",
        "scope": scope,
        "architecture_revision": revision,
        "method_id": "synthetic_policy_registry_review_v1",
        "evidence_source_ids": [evidence_id],
        "assumptions": assumptions or [],
        "procedure_ref": "test-only://registry-closure",
        "policy_registry_version": snapshot["policy_registry"]["registry_version"],
        "as_of": snapshot["policy_registry"]["as_of"],
    }
    snapshot["completeness_claims"].append(claim)
    return claim


def close_facts_for(
    snapshot: dict[str, Any],
    predicate: str,
    *,
    state: str = "after",
    scope: str = "application",
    evidence_id: str = "FACT_CLOSURE_EVIDENCE",
) -> dict[str, Any]:
    claim_id = f"FACT_CLOSURE_{predicate.replace('.', '_')}"
    revision = snapshot["architecture"]["before_commit" if state == "before" else "after_commit"]
    snapshot["sources"].append(
        {
            "id": evidence_id,
            "path": f"policies/evidence/{evidence_id}.json",
            "sha256": "6" * 64,
            "kind": "EVIDENCE",
            "producer": "synthetic_test_only",
        }
    )
    claim = {
        "id": claim_id,
        "kind": "EXACT_ENUMERATION",
        "state": state,
        "fact_type": predicate,
        "scope": scope,
        "architecture_revision": revision,
        "method_id": "synthetic_fact_inventory_v1",
        "evidence_source_ids": [evidence_id],
        "assumptions": [],
        "procedure_ref": "test-only://fact-closure",
    }
    snapshot["completeness_claims"].append(claim)
    return claim


def evidence_ledger(
    snapshot: dict[str, Any],
    *,
    proof_status: ProofStatus = ProofStatus.VALID,
    policy_statuses: dict[str, ProofStatus] | None = None,
    completeness_statuses: dict[str, ProofStatus] | None = None,
    override_proofs: dict[tuple[str, str], EvidenceProof] | None = None,
    precedence_proofs: dict[tuple[str, str], EvidenceProof] | None = None,
) -> EvidenceLedger:
    source_hashes = {
        str(source["id"]): str(source["sha256"])
        for source in snapshot["sources"]
        if isinstance(source, dict)
    }

    def bind(subject: Any, source_ids: list[str] | tuple[str, ...]) -> EvidenceProof:
        bindings = tuple(
            sorted(
                {
                    (source_id, source_hashes[source_id])
                    for source_id in source_ids
                    if source_id in source_hashes
                }
            )
        )
        refs = tuple(sorted(set(source_ids)))
        return EvidenceProof(
            status=proof_status,
            subject_sha256=sha256_bytes(canonical_json_bytes(subject)),
            source_bindings=bindings,
            verifier_id="synthetic_test_verifier",
            evidence_refs=refs,
        )

    charter_source_id = str(snapshot["policy_registry"]["authority_charter_source_id"])
    charter_digest = source_hashes.get(charter_source_id)
    charter_proof = bind(
        {"source_id": charter_source_id, "sha256": charter_digest},
        [charter_source_id],
    )
    registry_id = str(snapshot["policy_registry"]["source_id"])
    registry_proof = bind(snapshot["policy_registry"], [registry_id])
    fact_proofs = {
        str(fact["id"]): bind(fact, list(fact.get("source_ids", [])))
        for fact in snapshot["facts"]
        if isinstance(fact, dict) and fact.get("epistemic_kind") != "UNKNOWN"
    }
    policy_proofs: dict[str, EvidenceProof] = {}
    for policy in snapshot["policies"]:
        if not isinstance(policy, dict) or not isinstance(policy.get("approval_source_id"), str):
            continue
        policy_id = str(policy["id"])
        status = (policy_statuses or {}).get(policy_id, proof_status)
        policy_proofs[policy_id] = EvidenceProof(
            status=status,
            subject_sha256=sha256_bytes(canonical_json_bytes(policy)),
            source_bindings=tuple(
                sorted(
                    {
                        (source_id, source_hashes[source_id])
                        for source_id in (
                            registry_id,
                            str(policy["approval_source_id"]),
                            charter_source_id,
                        )
                        if source_id in source_hashes
                    }
                )
            ),
            verifier_id="synthetic_test_verifier",
            evidence_refs=tuple(
                sorted({registry_id, str(policy["approval_source_id"]), charter_source_id})
            ),
            reason_codes=("POLICY_ISSUER_UNAUTHORIZED",)
            if status is ProofStatus.INVALID and policy.get("kind") in {"EXCEPTION", "RETIREMENT"}
            else (),
        )
    completeness_proofs: dict[str, EvidenceProof] = {}
    for claim in snapshot["completeness_claims"]:
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim["id"])
        status = (completeness_statuses or {}).get(claim_id, proof_status)
        completeness_proofs[claim_id] = EvidenceProof(
            status=status,
            subject_sha256=sha256_bytes(canonical_json_bytes(claim)),
            source_bindings=tuple(
                sorted(
                    {
                        (source_id, source_hashes[source_id])
                        for source_id in claim.get("evidence_source_ids", [])
                        if source_id in source_hashes
                    }
                )
            ),
            verifier_id="synthetic_test_verifier",
            evidence_refs=tuple(sorted(set(claim.get("evidence_source_ids", [])))),
        )
    return EvidenceLedger(
        fact_proofs=fact_proofs,
        policy_proofs=policy_proofs,
        completeness_proofs=completeness_proofs,
        registry_proof=registry_proof,
        charter_proof=charter_proof,
        authorized_overrides=override_proofs,
        policy_precedence=precedence_proofs,
    )


def proof_for(
    status: ProofStatus,
    subject: Any,
    snapshot: dict[str, Any],
    source_ids: list[str],
    *,
    reason_codes: tuple[str, ...] = (),
) -> EvidenceProof:
    source_hashes = {
        str(source["id"]): str(source["sha256"])
        for source in snapshot["sources"]
        if isinstance(source, dict)
    }
    return EvidenceProof(
        status=status,
        subject_sha256=sha256_bytes(canonical_json_bytes(subject)),
        source_bindings=tuple(
            sorted({(source_id, source_hashes[source_id]) for source_id in source_ids})
        ),
        verifier_id="synthetic_test_verifier",
        evidence_refs=tuple(sorted(set(source_ids))),
        reason_codes=reason_codes,
    )
