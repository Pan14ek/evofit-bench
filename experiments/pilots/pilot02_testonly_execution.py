"""TEST_ONLY inputs for the prospective PILOT-02 DEVELOPMENT continuation.

This module creates bounded, explicitly non-authoritative evidence only for the
PILOT-02 continuation. It delegates adaptation to the existing Method P engine.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_adaptation import VerifiedPBundle
from experiments.execution.tooling.p_adaptation_evidence import (
    AdaptationEvidenceVerifierRegistry,
)
from experiments.execution.tooling.p_applicability import (
    EvidenceLedger,
    EvidenceProof,
    ProofStatus,
)
from experiments.execution.tooling.p_input_validation import SourceReference
from experiments.execution.tooling.p_operations import template_descriptor_sha256
from experiments.execution.tooling.p_semantic import pair_proof_subject

POLICY_VERIFIER_ID = "pilot02_test_only_policy_verifier_v1"
ADAPTATION_VERIFIER_ID = "pilot02_test_only_adaptation_verifier_v1"
POLICY_SIGNER_ID = "PILOT02_TEST_ONLY_KEY"
POLICY_HMAC_KEY = b"pilot02-public-test-only-policy-key-v1"
ADAPTATION_HMAC_KEY = b"pilot02-public-test-only-adaptation-key-v1"


class Pilot02TestOnlyTrustContext:
    """Local synthetic verifier. Its TEST_ONLY scope cannot establish authority."""

    verifier_id = POLICY_VERIFIER_ID
    signer_key_id = POLICY_SIGNER_ID
    policy_key = POLICY_HMAC_KEY
    adaptation_key = ADAPTATION_HMAC_KEY
    trust_scope: Literal["TEST_ONLY"] = "TEST_ONLY"

    def __init__(self) -> None:
        self.adaptation_evidence_verifiers = AdaptationEvidenceVerifierRegistry(
            {ADAPTATION_VERIFIER_ID: _Pilot02AdaptationEvidenceVerifier()}
        )

    def verify_charter(
        self,
        charter: Mapping[str, Any],
        source: SourceReference,
        evaluation_as_of: str,
    ) -> bool | None:
        try:
            source_charter = json.loads(source.content or b"")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return bool(
            source_charter == dict(charter)
            and charter.get("version") == "pilot02-test-only-assumption-v1"
            and isinstance(charter.get("effective_from"), str)
            and charter["effective_from"] <= evaluation_as_of
        )

    def verify_approval(
        self,
        policy: Mapping[str, Any],
        charter: Mapping[str, Any],
        source: SourceReference,
        evaluation_as_of: str,
    ) -> bool | None:
        del charter
        try:
            approval = json.loads(source.content or b"")
            effective_from = approval.get("effective_from")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if approval.get("signer_key_id") != self.signer_key_id:
            return None
        signed_payload = {
            "action": approval.get("action"),
            "policy_sha256": sha256_bytes(canonical_json_bytes(dict(policy))),
            "signer_key_id": self.signer_key_id,
        }
        expected = hmac.new(
            self.policy_key, canonical_json_bytes(signed_payload), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(str(approval.get("signature", "")), expected):
            return None
        if not isinstance(effective_from, str):
            return None
        return effective_from <= evaluation_as_of


class _Pilot02AdaptationEvidenceVerifier:
    trust_scope: Literal["TEST_ONLY"] = "TEST_ONLY"

    def verify(self, verifier_id: str, content_sha256: str, signature: str) -> bool:
        if verifier_id != ADAPTATION_VERIFIER_ID:
            return False
        expected = hmac.new(
            ADAPTATION_HMAC_KEY, content_sha256.encode("ascii"), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


def create_testonly_policy_source(
    source_directory: Path,
    destination: Path,
    *,
    evaluation_as_of: str,
    before_sha: str,
    after_sha: str,
    obligation_catalog_sha256: str,
    target_obligation_ids: Sequence[str],
    applicability_by_obligation: Mapping[str, Mapping[str, str]] | None = None,
) -> tuple[Path, Pilot02TestOnlyTrustContext]:
    """Create an isolated policy input embodying explicit TEST_ONLY state assumptions."""
    source = destination / "policy-source-test-only"
    if source.exists():
        raise ValueError("TEST_ONLY policy source destination already exists")
    if applicability_by_obligation is not None and set(applicability_by_obligation) != set(
        target_obligation_ids
    ):
        raise ValueError("TEST_ONLY applicability assumptions do not match the target obligations")
    shutil.copytree(source_directory, source)
    registry_path = source / "fitness/policy/registry.json"
    registry = json.loads(registry_path.read_bytes())
    selected: list[dict[str, Any]] = []
    for obligation_id in target_obligation_ids:
        matches = [
            row
            for row in registry.get("policies", [])
            if isinstance(row, Mapping) and obligation_id in row.get("obligation_ids", [])
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one pilot policy for {obligation_id}")
        policy = dict(matches[0])
        state_assumption = (
            applicability_by_obligation.get(obligation_id)
            if applicability_by_obligation is not None
            else {"before": "INACTIVE", "after": "ACTIVE"}
        )
        if not isinstance(state_assumption, Mapping):
            raise ValueError(f"Missing TEST_ONLY applicability assumption for {obligation_id}")
        states = [state for state in ("before", "after") if state_assumption.get(state) == "ACTIVE"]
        invalid_state = any(
            state_assumption.get(state) not in {"ACTIVE", "INACTIVE"}
            for state in ("before", "after")
        )
        if invalid_state or not states:
            raise ValueError(f"Invalid TEST_ONLY applicability assumption for {obligation_id}")
        policy["normative_status"] = "APPROVED"
        policy["scope"] = "application"
        policy["applies_to_states"] = states
        # The explicit TEST_ONLY state assessment stands in for a source-backed
        # predicate evaluation; it is not promoted to an authority or policy finding.
        policy["kind"] = "UNCONDITIONAL_MANDATE"
        policy.pop("condition_ref", None)
        policy["approval_source_id"] = f"PILOT02_APPROVAL_{obligation_id}"
        selected.append(policy)

    registry["schema_version"] = "1.2"
    registry["registry_version"] = "pilot02-test-only-development-v1"
    registry["scope"] = "application"
    registry["closure"] = "CLAIMED_CLOSED"
    registry.pop("closure_claim_id", None)
    registry["closure_claim_ids"] = [
        "PILOT02_TEST_ONLY_CLOSURE_BEFORE",
        "PILOT02_TEST_ONLY_CLOSURE_AFTER",
    ]
    registry["policies"] = selected

    charter_path = source / "fitness/policy/authority-charter.json"
    charter = json.loads(charter_path.read_bytes())
    charter["version"] = "pilot02-test-only-assumption-v1"
    charter["role_permissions"]["research_policy_author"] = [
        "APPROVE_POLICY",
        "DRAFT_POLICY",
    ]

    _write_json(charter_path, charter)
    _write_json(registry_path, registry)
    approvals = source / "fitness/policy/approvals"
    approvals.mkdir(exist_ok=True)
    for policy in selected:
        action = str(policy["normative_status"])
        signed_payload = {
            "action": action,
            "policy_sha256": sha256_bytes(canonical_json_bytes(policy)),
            "signer_key_id": POLICY_SIGNER_ID,
        }
        approval = {
            "schema_version": "1.1",
            "action": action,
            "policy_id": policy["id"],
            "policy_registry_version": registry["registry_version"],
            "policy_source_id": policy["source_id"],
            "issuer_role": policy["issuer_role"],
            "scope": policy["scope"],
            "effective_from": policy["effective_from"],
            "effective_until": policy["effective_until"],
            "policy_sha256": signed_payload["policy_sha256"],
            "historical_consequence": None,
            "superseded_by_policy_ids": [],
            "signer_key_id": POLICY_SIGNER_ID,
            "signature": hmac.new(
                POLICY_HMAC_KEY, canonical_json_bytes(signed_payload), hashlib.sha256
            ).hexdigest(),
        }
        _write_json(approvals / f"{policy['approval_source_id']}.json", approval)

    claims: list[dict[str, Any]] = []
    for state, revision in (("before", before_sha), ("after", after_sha)):
        claim_id = f"PILOT02_TEST_ONLY_CLOSURE_{state.upper()}"
        evidence_id = f"PILOT02_TEST_ONLY_REGISTRY_EVIDENCE_{state.upper()}"
        claim = {
            "id": claim_id,
            "kind": "AUTHORITATIVE_POLICY_REGISTRY",
            "state": state,
            "fact_type": "obligation:all",
            "scope": "application",
            "architecture_revision": revision,
            "method_id": "pilot02_test_only_registry_assumption_v1",
            "evidence_source_ids": [evidence_id],
            "assumptions": [f"obligation_catalog_sha256:{obligation_catalog_sha256}"],
            "procedure_ref": "synthetic-test://pilot02-development-assumptions-v1",
            "policy_registry_version": registry["registry_version"],
            "as_of": evaluation_as_of,
        }
        evidence = {
            "fixture": "pilot02-test-only-closed-registry-v1",
            "state": state,
            "scope": "application",
            "policy_registry_version": registry["registry_version"],
            "as_of": evaluation_as_of,
            "architecture_revision": revision,
        }
        claims.append(claim)
        _write_json(source / f"fitness/policy/evidence/{evidence_id}.json", evidence)
    claims.sort(key=lambda row: str(row["id"]))
    _write_json(source / "fitness/policy/completeness-claims.json", claims)
    return source, Pilot02TestOnlyTrustContext()


def testonly_completeness_verifier(
    claim: Mapping[str, Any],
    sources: Mapping[str, SourceReference],
    snapshot: Mapping[str, Any],
) -> bool | None:
    """Check that test-only closure fixtures bind exact state and source revision."""
    evidence_ids = claim.get("evidence_source_ids")
    if not isinstance(evidence_ids, list) or len(evidence_ids) != 1:
        return None
    source = sources.get(str(evidence_ids[0]))
    if source is None or source.content is None:
        return None
    try:
        evidence = json.loads(source.content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    architecture = snapshot.get("architecture")
    registry = snapshot.get("policy_registry")
    if not isinstance(architecture, Mapping) or not isinstance(registry, Mapping):
        return None
    revision_key = "before_commit" if claim.get("state") == "before" else "after_commit"
    return bool(
        claim.get("kind") == "AUTHORITATIVE_POLICY_REGISTRY"
        and evidence.get("fixture") == "pilot02-test-only-closed-registry-v1"
        and claim.get("state") == evidence.get("state")
        and claim.get("scope") == evidence.get("scope") == registry.get("scope")
        and claim.get("policy_registry_version")
        == evidence.get("policy_registry_version")
        == registry.get("registry_version")
        and claim.get("as_of") == evidence.get("as_of") == registry.get("as_of")
        and claim.get("architecture_revision")
        == evidence.get("architecture_revision")
        == architecture.get(revision_key)
    )


def build_testonly_evidence_ledger(
    snapshot: Mapping[str, Any],
    source_manifest: Mapping[str, SourceReference],
    *,
    source_integrity_valid: bool,
    trust_context: Pilot02TestOnlyTrustContext,
) -> EvidenceLedger:
    """Create source-bound TEST_ONLY ledger entries for the isolated assumption source."""
    registry = snapshot["policy_registry"]
    architecture = snapshot["architecture"]
    charter_id = str(registry["authority_charter_source_id"])
    registry_id = str(registry["source_id"])
    charter_source = source_manifest[charter_id]
    charter = json.loads(charter_source.content or b"{}")
    as_of = str(architecture["evaluation_as_of"])

    registry_status = ProofStatus.VALID if source_integrity_valid else ProofStatus.UNDETERMINED
    registry_proof = _evidence_proof(
        registry_status,
        registry,
        [registry_id],
        source_manifest,
        "pilot02_test_only_integrity_v1",
    )
    charter_status = (
        ProofStatus.VALID
        if trust_context.verify_charter(charter, charter_source, as_of) is True
        else ProofStatus.UNDETERMINED
    )
    charter_proof = _evidence_proof(
        charter_status,
        {"source_id": charter_id, "sha256": charter_source.sha256},
        [charter_id],
        source_manifest,
        trust_context.verifier_id,
    )

    policy_proofs: dict[str, EvidenceProof] = {}
    for policy in snapshot.get("policies", []):
        if not isinstance(policy, Mapping):
            continue
        approval_id = str(policy.get("approval_source_id", ""))
        approval_source = source_manifest.get(approval_id)
        if approval_source is None:
            continue
        verdict = trust_context.verify_approval(policy, charter, approval_source, as_of)
        status = ProofStatus.VALID if verdict is True else ProofStatus.UNDETERMINED
        policy_proofs[str(policy["id"])] = _evidence_proof(
            status,
            policy,
            [registry_id, approval_id, charter_id],
            source_manifest,
            trust_context.verifier_id,
        )

    completeness_proofs: dict[str, EvidenceProof] = {}
    for claim in snapshot.get("completeness_claims", []):
        if not isinstance(claim, Mapping):
            continue
        source_ids = [str(item) for item in claim.get("evidence_source_ids", [])]
        sources = {item: source_manifest[item] for item in source_ids if item in source_manifest}
        verdict = testonly_completeness_verifier(claim, sources, snapshot)
        status = ProofStatus.VALID if verdict is True else ProofStatus.UNDETERMINED
        completeness_proofs[str(claim["id"])] = _evidence_proof(
            status,
            claim,
            list(sources),
            source_manifest,
            "pilot02_test_only_completeness_v1",
        )

    return EvidenceLedger(
        fact_proofs={},
        policy_proofs=policy_proofs,
        completeness_proofs=completeness_proofs,
        registry_proof=registry_proof,
        charter_proof=charter_proof,
    )


def build_adaptation_sidecar(
    bundle: VerifiedPBundle,
    *,
    assumptions: Mapping[str, Any],
    evaluator_evidence: Sequence[Mapping[str, Any]],
    b0_representation: Mapping[str, Any],
    b0_evaluator_evidence: Mapping[str, Any],
    extra_artifacts: Mapping[str, bytes],
    semantic_pair_proofs: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Sign actual evaluator executions and TEST_ONLY planning assumptions."""
    architecture = bundle.snapshot["architecture"]
    before_sha = str(architecture["before_commit"])
    after_sha = str(architecture["after_commit"])
    registry = bundle.snapshot["policy_registry"]
    scope = str(registry["scope"])
    bundle_sha = str(bundle.manifest["bundle_sha256"])
    policy_revision = str(bundle.manifest["policy_source_revision"])
    policy_sha = str(bundle.manifest["policy_bundle_sha256"])
    source_bindings = [
        {"source_id": source_id, "sha256": digest}
        for source_id, digest in sorted(bundle.source_digests.items())
    ]
    outer_bindings = set(bundle.source_digests.items())
    payload_evidence = [dict(row) for row in evaluator_evidence]
    b0_key = (str(b0_representation["id"]), "AC_LAYERING")
    payload_evidence.append(
        {
            "representation_id": b0_key[0],
            "obligation_id": b0_key[1],
            "evidence": dict(b0_evaluator_evidence),
        }
    )

    pair_subject = pair_proof_subject(
        b0_representation,
        next(row for row in bundle.obligations if row["id"] == b0_key[1]),
        after_sha,
        b0_evaluator_evidence,
    )
    missing_targets = b0_evaluator_evidence.get("missing_targets", [])
    pair_status = "INVALID" if missing_targets else "UNDETERMINED"
    pair_reason_codes = (
        ["PILOT02_TEST_ONLY_B0_SCOPE_MISMATCH"] if missing_targets else ["B0_SCOPE_UNRESOLVED"]
    )
    pair_proof = {
        "representation_id": b0_key[0],
        "obligation_id": b0_key[1],
        "status": pair_status,
        "subject_sha256": sha256_bytes(canonical_json_bytes(pair_subject)),
        "verifier_id": ADAPTATION_VERIFIER_ID,
        "source_bindings": _binding_rows(bundle, ["P_CAPABILITIES", "P_TRACEABILITY"]),
        "evidence_refs": ["P_CAPABILITIES", "P_TRACEABILITY"],
        "reason_codes": pair_reason_codes,
    }

    policy_rows = [dict(row) for row in bundle.snapshot.get("policies", [])]
    policy_source_ids = _policy_source_ids(bundle.snapshot, policy_rows)
    inventories: list[dict[str, Any]] = []
    for state, revision in (("before", before_sha), ("after", after_sha)):
        subject = {
            "claim_type": "policy_inventory",
            "state": state,
            "scope": scope,
            "architecture_source_sha": revision,
            "policy_source_revision": policy_revision,
            "policy_bundle_sha256": policy_sha,
            "rows_sha256": sha256_bytes(canonical_json_bytes(policy_rows)),
        }
        inventories.append(
            {
                "state": state,
                "scope": scope,
                "architecture_source_sha": revision,
                "rows": policy_rows,
                "proof": _scoped_proof(
                    bundle,
                    subject,
                    scope,
                    (revision,),
                    sorted(policy_source_ids),
                ),
            }
        )

    required_stages = {
        str(obligation_id): ["ci"]
        for obligation_id in assumptions["transition"]["target_obligation_ids"]
    }
    stage_subject = {
        "claim_type": "required_stages",
        "required_stages_sha256": sha256_bytes(canonical_json_bytes(required_stages)),
        "input_bundle_sha256": bundle_sha,
    }
    trace_subject = {
        "claim_type": "trace_inventory",
        "trace_graph_sha256": bundle.trace_graph.graph_sha256,
        "input_bundle_sha256": bundle_sha,
    }
    change_subject = {
        "claim_type": "change_inventory",
        "snapshot_sha256": bundle.snapshot_validation.snapshot_digest,
        "input_bundle_sha256": bundle_sha,
        "policy_source_revision": policy_revision,
        "policy_bundle_sha256": policy_sha,
    }
    capability_digest = bundle.source_digests["P_CAPABILITIES"]
    cost_subject = {
        "claim_type": "cost_model_authority",
        "cost_model_sha256": sha256_bytes(canonical_json_bytes(bundle.cost_model)),
        "capabilities_sha256": capability_digest,
        "input_bundle_sha256": bundle_sha,
    }

    target_ids = set(assumptions["transition"]["target_obligation_ids"])
    classification_rows = [
        {"obligation_id": str(row["id"]), "mandatory": str(row["id"]) in target_ids}
        for row in bundle.obligations
    ]
    classification_subject = {
        "claim_type": "test_only_mandatory_classification",
        "rows_sha256": sha256_bytes(canonical_json_bytes(classification_rows)),
        "input_bundle_sha256": bundle_sha,
        "policy_source_revision": policy_revision,
        "policy_bundle_sha256": policy_sha,
    }
    change_source_ids = _change_inventory_source_ids(bundle.snapshot)
    payload = {
        "evaluator_evidence": payload_evidence,
        "pair_proofs": [pair_proof, *[dict(row) for row in semantic_pair_proofs]],
        "artifact_bytes": [
            {
                "path": path,
                "sha256": sha256_bytes(content),
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
            for path, content in sorted(extra_artifacts.items())
        ],
        "fact_absence_proofs": [],
        "policy_inventories": inventories,
        "trace_inventory_proof": _scoped_proof(
            bundle, trace_subject, scope, (before_sha, after_sha), ["P_TRACEABILITY"]
        ),
        "change_inventory_proof": _scoped_proof(
            bundle,
            change_subject,
            scope,
            (before_sha, after_sha),
            sorted(change_source_ids),
        ),
        "required_stages": required_stages,
        "stage_contract_proof": _scoped_proof(
            bundle, stage_subject, scope, (after_sha,), ["P_CAPABILITIES"]
        ),
        "test_only_mandatory_classification": {
            "rows": classification_rows,
            "proof": _scoped_proof(
                bundle,
                classification_subject,
                scope,
                (before_sha, after_sha),
                sorted(policy_source_ids),
            ),
        },
        "adjustment_rules": [],
        "authorized_template_descriptor_sha256": [
            template_descriptor_sha256(template) for template in bundle.templates
        ],
        "cost_model_proof": _scoped_proof(
            bundle, cost_subject, scope, (after_sha,), ["P_CAPABILITIES"]
        ),
    }
    if not extra_artifacts or not outer_bindings:
        raise ValueError("TEST_ONLY sidecar requires pinned sources and actual raw artifacts")
    unsigned = {
        "schema_version": 2,
        "contract_id": "P_ADAPTATION_EVIDENCE_V2",
        "input_bundle_sha256": bundle_sha,
        "architecture_before_sha": before_sha,
        "architecture_after_sha": after_sha,
        "policy_source_revision": policy_revision,
        "policy_bundle_sha256": policy_sha,
        "evaluation_as_of": str(architecture["evaluation_as_of"]),
        "scope": scope,
        "source_bindings": source_bindings,
        "verifier_id": ADAPTATION_VERIFIER_ID,
        "payload": payload,
    }
    digest = sha256_bytes(canonical_json_bytes(unsigned))
    return {
        **unsigned,
        "sidecar_sha256": digest,
        "signature": hmac.new(
            ADAPTATION_HMAC_KEY, digest.encode("ascii"), hashlib.sha256
        ).hexdigest(),
    }


def _evidence_proof(
    status: ProofStatus,
    subject: Mapping[str, Any],
    source_ids: Sequence[str],
    source_manifest: Mapping[str, SourceReference],
    verifier_id: str,
) -> EvidenceProof:
    bindings = tuple(
        sorted((source_id, source_manifest[source_id].sha256) for source_id in set(source_ids))
    )
    refs = tuple(sorted(set(source_ids)))
    return EvidenceProof(
        status=status,
        subject_sha256=sha256_bytes(canonical_json_bytes(dict(subject))),
        source_bindings=bindings,
        verifier_id=verifier_id,
        evidence_refs=refs,
    )


def _binding_rows(bundle: VerifiedPBundle, source_ids: Sequence[str]) -> list[dict[str, str]]:
    return [
        {"source_id": source_id, "sha256": bundle.source_digests[source_id]}
        for source_id in sorted(set(source_ids))
    ]


def _scoped_proof(
    bundle: VerifiedPBundle,
    subject: Mapping[str, Any],
    scope: str,
    architecture_shas: Sequence[str],
    source_ids: Sequence[str],
) -> dict[str, Any]:
    return {
        "status": "VALID",
        "subject_sha256": sha256_bytes(canonical_json_bytes(dict(subject))),
        "scope": scope,
        "architecture_source_shas": list(architecture_shas),
        "verifier_id": ADAPTATION_VERIFIER_ID,
        "source_bindings": _binding_rows(bundle, source_ids),
        "evidence_refs": sorted(set(source_ids)),
    }


def _policy_source_ids(snapshot: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> set[str]:
    registry = snapshot.get("policy_registry")
    result: set[str] = set()
    if isinstance(registry, Mapping):
        result.update(
            str(registry[key])
            for key in ("source_id", "authority_charter_source_id")
            if isinstance(registry.get(key), str)
        )
    for row in [*snapshot.get("policies", []), *rows]:
        if isinstance(row, Mapping):
            result.update(
                str(row[key])
                for key in ("source_id", "approval_source_id")
                if isinstance(row.get(key), str)
            )
    return result


def _change_inventory_source_ids(snapshot: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for fact in snapshot.get("facts", []):
        if isinstance(fact, Mapping):
            result.update(str(item) for item in fact.get("source_ids", []) if isinstance(item, str))
    result.update(_policy_source_ids(snapshot, ()))
    for claim in snapshot.get("completeness_claims", []):
        if isinstance(claim, Mapping):
            result.update(
                str(item) for item in claim.get("evidence_source_ids", []) if isinstance(item, str)
            )
    return result


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "Pilot02TestOnlyTrustContext",
    "build_adaptation_sidecar",
    "build_testonly_evidence_ledger",
    "create_testonly_policy_source",
    "testonly_completeness_verifier",
]
