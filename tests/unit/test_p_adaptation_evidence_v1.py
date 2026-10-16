"""Trust-boundary and immutable-snapshot tests for method-side evidence."""

from __future__ import annotations

from typing import Any, Literal

from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_adaptation_evidence import (
    AdaptationEvidenceVerifierRegistry,
    thaw_verified_payload,
    verify_adaptation_evidence,
)


class _SyntheticVerifier:
    trust_scope: Literal["TEST_ONLY"] = "TEST_ONLY"

    def __init__(self, sidecar: dict[str, Any] | None = None) -> None:
        self.sidecar = sidecar

    def verify(self, verifier_id: str, content_sha256: str, signature: str) -> bool:
        del verifier_id, content_sha256, signature
        if self.sidecar is not None:
            payload = self.sidecar["payload"]
            assert isinstance(payload, dict)
            records = payload["evaluator_evidence"]
            assert isinstance(records, list)
            evidence = records[0]["evidence"]
            assert isinstance(evidence, dict)
            evidence["synthetic_mutation"] = True
        return True


def _sidecar() -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    source_digests = {"SYN_SOURCE": "a" * 64}
    bindings: dict[str, Any] = {
        "input_bundle_sha256": "b" * 64,
        "architecture_before_sha": "1" * 40,
        "architecture_after_sha": "2" * 40,
        "policy_source_revision": "SYN_POLICY_REV_1",
        "policy_bundle_sha256": "c" * 64,
        "evaluation_as_of": "2026-01-01T00:00:00Z",
        "scope": "service:synth",
    }
    verifier_id = "SYN_TEST_VERIFIER"
    proof = {
        "status": "UNDETERMINED",
        "subject_sha256": "d" * 64,
        "scope": "service:synth",
        "architecture_source_shas": ["2" * 40],
        "verifier_id": verifier_id,
        "source_bindings": [],
        "evidence_refs": [],
    }
    sidecar: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": "P_ADAPTATION_EVIDENCE_V1",
        **bindings,
        "source_bindings": [{"source_id": "SYN_SOURCE", "sha256": "a" * 64}],
        "verifier_id": verifier_id,
        "payload": {
            "evaluator_evidence": [
                {
                    "representation_id": "REP_SYN",
                    "obligation_id": "SYN_OBL",
                    "evidence": {"synthetic_value": "original"},
                }
            ],
            "pair_proofs": [],
            "artifact_bytes": [],
            "fact_absence_proofs": [],
            "policy_inventories": [],
            "trace_inventory_proof": proof,
            "change_inventory_proof": proof,
            "required_stages": {},
            "stage_contract_proof": proof,
            "adjustment_rules": [],
            "authorized_template_artifact_sha256": [],
            "cost_model_proof": proof,
        },
    }
    sidecar["sidecar_sha256"] = sha256_bytes(canonical_json_bytes(sidecar))
    sidecar["signature"] = "synthetic-test-signature"
    return sidecar, source_digests, bindings


def test_unregistered_permissive_evidence_verifier_is_not_trusted() -> None:
    sidecar, source_digests, bindings = _sidecar()
    result = verify_adaptation_evidence(
        sidecar,
        expected_bindings=bindings,
        expected_source_digests=source_digests,
        verifier_registry=AdaptationEvidenceVerifierRegistry({}),
        allow_test_only=True,
        expected_trust_scope="TEST_ONLY",
    )
    assert result is None


def test_verified_payload_uses_the_signed_snapshot_after_verifier_mutation() -> None:
    sidecar, source_digests, bindings = _sidecar()
    verifier = _SyntheticVerifier(sidecar)
    result = verify_adaptation_evidence(
        sidecar,
        expected_bindings=bindings,
        expected_source_digests=source_digests,
        verifier_registry=AdaptationEvidenceVerifierRegistry({"SYN_TEST_VERIFIER": verifier}),
        allow_test_only=True,
        expected_trust_scope="TEST_ONLY",
    )
    assert result is not None
    payload = thaw_verified_payload(result)
    assert payload["evaluator_evidence"][0]["evidence"] == {"synthetic_value": "original"}
    assert sidecar["payload"]["evaluator_evidence"][0]["evidence"]["synthetic_mutation"] is True
