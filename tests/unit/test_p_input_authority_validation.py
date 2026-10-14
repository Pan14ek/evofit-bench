"""Source integrity, APA, and completeness validation with synthetic trust anchors."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.p_input_validation import (
    AuthorityTrustContext,
    SourceReference,
    ValidationStatus,
    load_verified_source_manifest,
    validate_source_references,
    verify_completeness_claims,
    verify_policy_authority,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "p_input_contract_v11_snapshot.json"
TEST_ONLY_HMAC_KEY = b"synthetic-development-only-trust-anchor-not-for-production"
ROLE_BY_KIND = {
    "STRUCTURAL_OBSERVATION": "structural_observations",
    "POLICY_CHARTER": "policy_charter",
    "POLICY_REGISTRY": "policy_registry",
    "EVIDENCE": "completeness_evidence",
    "APPROVAL": "approval_evidence",
}


def _canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _charter() -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "charter_id": "SYNTHETIC_CHARTER",
        "version": "synthetic-charter-v1",
        "effective_from": "2026-01-01T00:00:00Z",
        "effective_until": None,
        "role_permissions": {
            "architecture_authority": ["APPROVE_POLICY", "REVOKE_POLICY", "SUPERSEDE_POLICY"],
            "junior_authority": ["APPROVE_POLICY", "REVOKE_POLICY", "SUPERSEDE_POLICY"],
        },
        "scope_hierarchy": [],
        "source_allowlist": [
            {
                "kind": "STRUCTURAL_OBSERVATION",
                "path_prefix": "architecture/structural-observations.json",
            },
            {"kind": "POLICY_REGISTRY", "path_prefix": "policies/registry.json"},
            {"kind": "APPROVAL", "path_prefix": "policies/approvals/"},
            {"kind": "EVIDENCE", "path_prefix": "policies/evidence/"},
        ],
        "precedence": [],
        "evidence_source_ids": ["AUTHORITY_EVIDENCE"],
    }


def _policy(
    *,
    policy_id: str = "POL_PUBLIC_API",
    status: str = "APPROVED",
    kind: str = "UNCONDITIONAL_MANDATE",
    role: str = "architecture_authority",
    polarity: str = "REQUIRED",
    targets: list[str] | None = None,
    applies_to_states: list[str] | None = None,
    effective_from: str = "2026-10-01T00:00:00Z",
    effective_until: str | None = None,
    approval_source_id: str | None = None,
    condition_ref: str | None = None,
) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "id": policy_id,
        "kind": kind,
        "normative_status": status,
        "obligation_ids": ["AC_PUBLIC_API"],
        "proposition": "Synthetic policy proposition",
        "scope": "application",
        "issuer_role": role,
        "approval_source_id": approval_source_id
        or (None if status == "DRAFT" else f"APPROVAL_{policy_id}"),
        "source_id": "REGISTRY",
        "effective_from": effective_from,
        "effective_until": effective_until,
        "applies_to_states": applies_to_states or ["after"],
        "target_policy_ids": targets or [],
        "proposition_polarity": polarity,
    }
    if condition_ref is not None:
        policy["condition_ref"] = condition_ref
    return policy


def _signed_approval(
    policy: dict[str, Any], registry_version: str = "synthetic-registry-v1"
) -> dict[str, Any]:
    proof: dict[str, Any] = {
        "schema_version": "1.1",
        "action": policy["normative_status"],
        "policy_id": policy["id"],
        "policy_registry_version": registry_version,
        "policy_source_id": policy["source_id"],
        "issuer_role": policy["issuer_role"],
        "scope": policy["scope"],
        "effective_from": policy["effective_from"],
        "effective_until": policy["effective_until"],
        "policy_sha256": sha256_bytes(canonical_json_bytes(policy)),
        "historical_consequence": "Synthetic historical consequence"
        if policy["normative_status"] in {"REVOKED", "SUPERSEDED"}
        else "",
        "superseded_by_policy_ids": [],
        "signer_key_id": "SYNTHETIC_TEST_KEY",
    }
    signature = hmac.new(TEST_ONLY_HMAC_KEY, _canonical_bytes(proof), hashlib.sha256).hexdigest()
    return {**proof, "signature": signature}


class _SyntheticTrustContext:
    """Test-only trust double pinned to a synthetic charter SHA and HMAC key."""

    def __init__(self, charter_sha256: str) -> None:
        self.charter_sha256 = charter_sha256

    def verify_charter(
        self, charter: Mapping[str, Any], source: SourceReference, evaluation_as_of: str
    ) -> bool | None:
        return (
            source.sha256 == self.charter_sha256
            and charter.get("charter_id") == "SYNTHETIC_CHARTER"
            and evaluation_as_of == "2026-10-13T00:00:00Z"
        )

    def verify_approval(
        self,
        policy: Mapping[str, Any],
        charter: Mapping[str, Any],
        source: SourceReference,
        evaluation_as_of: str,
    ) -> bool | None:
        del charter, evaluation_as_of
        if source.content is None:
            return False
        proof = json.loads(source.content)
        signature = proof.pop("signature")
        expected = hmac.new(TEST_ONLY_HMAC_KEY, _canonical_bytes(proof), hashlib.sha256).hexdigest()
        return (
            hmac.compare_digest(str(signature), expected)
            and proof.get("signer_key_id") == "SYNTHETIC_TEST_KEY"
            and proof.get("policy_id") == policy.get("id")
        )


def _build_bundle(
    root: Path,
    *,
    policies: list[dict[str, Any]] | None = None,
    closure: str = "OPEN",
    claims: list[dict[str, Any]] | None = None,
    source_overrides: dict[str, tuple[str, str, bytes]] | None = None,
    registry_as_of: str = "2026-10-13T00:00:00Z",
) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build a synthetic source bundle; never reads the DA01 scenario or oracle."""
    snapshot = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    policies = policies or []
    claims = claims or []
    snapshot["policies"] = policies
    snapshot["completeness_claims"] = claims
    closure_claim_id = next(
        (claim["id"] for claim in claims if claim.get("kind") == "AUTHORITATIVE_POLICY_REGISTRY"),
        None,
    )
    snapshot["policy_registry"] = {
        "scope": "application",
        "source_id": "REGISTRY",
        "closure": closure,
        "closure_claim_id": closure_claim_id,
        "authority_charter_source_id": "CHARTER",
        "registry_version": "synthetic-registry-v1",
        "as_of": registry_as_of,
    }
    charter = _charter()
    source_payloads: dict[str, tuple[str, str, bytes]] = {
        "ARCH_OBS": (
            "architecture/structural-observations.json",
            "STRUCTURAL_OBSERVATION",
            _canonical_bytes(
                {
                    "source_state": "after",
                    "source_commit_sha": snapshot["architecture"]["after_commit"],
                    "source_tree_sha": snapshot["architecture"]["after_tree"],
                    "target_structural_manifest": {"deployment": {"deployment_units": 1}},
                }
            ),
        ),
        "CHARTER": (
            "policies/authority-charter.json",
            "POLICY_CHARTER",
            _canonical_bytes(charter),
        ),
        "AUTHORITY_EVIDENCE": (
            "policies/evidence/authority.json",
            "EVIDENCE",
            b"SYNTHETIC TEST ONLY: charter trust anchor evidence\n",
        ),
    }
    if source_overrides:
        source_payloads.update(source_overrides)
    for policy in policies:
        if policy.get("approval_source_id") is None:
            continue
        approval_id = str(policy["approval_source_id"])
        source_payloads[approval_id] = (
            f"policies/approvals/{approval_id}.json",
            "APPROVAL",
            _canonical_bytes(_signed_approval(policy)),
        )
    registry_artifact = {
        "schema_version": "1.1",
        "registry_version": "synthetic-registry-v1",
        "scope": "application",
        "as_of": registry_as_of,
        "closure": closure,
        "closure_claim_id": closure_claim_id,
        "authority_charter_source_id": "CHARTER",
        "policies": policies,
    }
    source_payloads["REGISTRY"] = (
        "policies/registry.json",
        "POLICY_REGISTRY",
        _canonical_bytes(registry_artifact),
    )
    for claim in claims:
        for source_id in claim.get("evidence_source_ids", []):
            source_payloads.setdefault(
                source_id,
                (
                    f"policies/evidence/{source_id}.json",
                    "EVIDENCE",
                    b"SYNTHETIC TEST ONLY: completeness evidence\n",
                ),
            )

    root.mkdir(parents=True, exist_ok=True)
    snapshot_sources: list[dict[str, Any]] = []
    file_records: list[dict[str, Any]] = []
    for source_id, (relative_path, kind, content) in sorted(source_payloads.items()):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        digest = sha256_bytes(content)
        snapshot_sources.append(
            {
                "id": source_id,
                "path": relative_path,
                "sha256": digest,
                "kind": kind,
                "producer": "synthetic_test_fixture",
            }
        )
        file_records.append(
            {
                "path": relative_path,
                "role": ROLE_BY_KIND[kind],
                "size_bytes": len(content),
                "sha256": digest,
            }
        )
    snapshot["sources"] = snapshot_sources
    snapshot_bytes = _canonical_bytes(snapshot)
    snapshot_path = root / "architecture-policy-snapshot.json"
    snapshot_path.write_bytes(snapshot_bytes)
    file_records.append(
        {
            "path": "architecture-policy-snapshot.json",
            "role": "architecture_policy_snapshot",
            "size_bytes": len(snapshot_bytes),
            "sha256": sha256_bytes(snapshot_bytes),
        }
    )
    file_records.sort(key=lambda item: item["path"])
    manifest = {
        "schema_version": 2,
        "allowlist_version": "DA01_METHOD_INPUTS_V2_CANDIDATE",
        "profile_status": "DEVELOPMENT_UNFROZEN",
        "method_id": "B1",
        "architecture_before_sha": snapshot["architecture"]["before_commit"],
        "architecture_source_sha": snapshot["architecture"]["after_commit"],
        "before_tree_sha": snapshot["architecture"]["before_tree"],
        "after_tree_sha": snapshot["architecture"]["after_tree"],
        "files": file_records,
        "bundle_sha256": bundle_sha256(file_records),
        "common_snapshot_sha256": sha256_bytes(snapshot_bytes),
    }
    return root, snapshot, manifest, charter


def _verified_sources(
    root: Path, snapshot: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, SourceReference]:
    references, report = load_verified_source_manifest(snapshot, manifest, root)
    assert report.status is ValidationStatus.VALID, report.to_dict()
    return references


def _synthetic_trust(
    references: dict[str, SourceReference],
) -> AuthorityTrustContext:
    return _SyntheticTrustContext(references["CHARTER"].sha256)


def test_source_references_verify_typed_roles_exact_bytes_and_pinned_revisions(
    tmp_path: Path,
) -> None:
    root, snapshot, manifest, _ = _build_bundle(tmp_path / "bundle")

    report = validate_source_references(snapshot, manifest, root)

    assert report.status is ValidationStatus.VALID


def test_source_reference_rejects_sha_mismatch_and_wrong_role(tmp_path: Path) -> None:
    root, snapshot, manifest, _ = _build_bundle(tmp_path / "bundle")
    source = snapshot["sources"][0]
    source["sha256"] = "0" * 64
    report = validate_source_references(snapshot, manifest, root)

    assert report.status is ValidationStatus.INVALID
    assert "SOURCE_HASH_MISMATCH" in report.reason_codes

    source["sha256"] = next(
        record["sha256"] for record in manifest["files"] if record["path"] == source["path"]
    )
    file_record = next(record for record in manifest["files"] if record["path"] == source["path"])
    file_record["role"] = "policy_registry"
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    report = validate_source_references(snapshot, manifest, root)

    assert report.status is ValidationStatus.INVALID
    assert "SOURCE_NOT_ALLOWLISTED" in report.reason_codes


def test_source_reference_rejects_path_traversal_symlink_escape_and_self_reference(
    tmp_path: Path,
) -> None:
    root, snapshot, manifest, _ = _build_bundle(tmp_path / "bundle")
    source = snapshot["sources"][0]
    source["path"] = "../outside.json"
    report = validate_source_references(snapshot, manifest, root)
    assert "FORBIDDEN_INPUT" in report.reason_codes

    root, snapshot, manifest, _ = _build_bundle(tmp_path / "symlink-bundle")
    source = snapshot["sources"][0]
    original_path = root / source["path"]
    outside = tmp_path / "outside.json"
    outside.write_bytes(original_path.read_bytes())
    original_path.unlink()
    original_path.symlink_to(outside)
    manifest["files"] = [
        {
            **record,
            "sha256": sha256_bytes(outside.read_bytes()),
            "size_bytes": outside.stat().st_size,
        }
        if record["path"] == source["path"]
        else record
        for record in manifest["files"]
    ]
    source["sha256"] = sha256_bytes(outside.read_bytes())
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    report = validate_source_references(snapshot, manifest, root)
    assert "FORBIDDEN_INPUT" in report.reason_codes

    source["path"] = "method_input_v2.json"
    report = validate_source_references(snapshot, manifest, root)
    assert "FORBIDDEN_INPUT" in report.reason_codes


def test_source_reference_rejects_duplicate_ids_and_outer_commit_mismatch(
    tmp_path: Path,
) -> None:
    root, snapshot, manifest, _ = _build_bundle(tmp_path / "bundle")
    snapshot["facts"][0]["id"] = snapshot["sources"][0]["id"]
    manifest["architecture_source_sha"] = "e" * 40
    report = validate_source_references(snapshot, manifest, root)

    assert "DUPLICATE_IDENTIFIER" in report.reason_codes
    assert "VERSION_MISMATCH" in report.reason_codes


def test_open_registry_and_untrusted_approval_remain_undetermined(tmp_path: Path) -> None:
    policy = _policy()
    root, snapshot, manifest, charter = _build_bundle(tmp_path / "bundle", policies=[policy])
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        trust_context=None,
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert report.status is ValidationStatus.UNDETERMINED
    assert "POLICY_APPROVAL_UNVERIFIED" in report.reason_codes
    assert "REGISTRY_CLOSURE_UNVERIFIED" in report.reason_codes


def test_registry_as_of_must_match_snapshot_evaluation_time(tmp_path: Path) -> None:
    policy = _policy()
    root, snapshot, manifest, charter = _build_bundle(
        tmp_path / "bundle",
        policies=[policy],
        registry_as_of="2026-10-12T00:00:00Z",
    )
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert report.status is ValidationStatus.INVALID
    assert "VERSION_MISMATCH" in report.reason_codes


def test_expired_policy_is_invalid_at_evaluation_time(tmp_path: Path) -> None:
    policy = _policy(effective_until="2026-10-13T00:00:00Z")
    root, snapshot, manifest, charter = _build_bundle(tmp_path / "bundle", policies=[policy])
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert report.status is ValidationStatus.INVALID
    assert "VERSION_MISMATCH" in report.reason_codes


def test_synthetic_approval_is_bound_to_policy_but_does_not_verify_open_registry(
    tmp_path: Path,
) -> None:
    policy = _policy()
    root, snapshot, manifest, charter = _build_bundle(tmp_path / "bundle", policies=[policy])
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert report.status is ValidationStatus.UNDETERMINED
    assert "APPROVAL_POL_PUBLIC_API" in report.evidence_refs
    assert "POLICY_APPROVAL_UNVERIFIED" not in report.reason_codes
    assert "REGISTRY_CLOSURE_UNVERIFIED" in report.reason_codes


def test_policy_approval_binds_entire_policy_content(tmp_path: Path) -> None:
    policy = _policy()
    root, snapshot, manifest, charter = _build_bundle(tmp_path / "bundle", policies=[policy])
    altered_policy = {**policy, "proposition": "Tampered policy content"}
    snapshot["policies"] = [altered_policy]
    registry_path = root / "policies/registry.json"
    registry_artifact = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_artifact["policies"] = [altered_policy]
    registry_bytes = _canonical_bytes(registry_artifact)
    registry_path.write_bytes(registry_bytes)
    registry_source = next(source for source in snapshot["sources"] if source["id"] == "REGISTRY")
    registry_source["sha256"] = sha256_bytes(registry_bytes)
    registry_record = next(
        record for record in manifest["files"] if record["path"] == registry_source["path"]
    )
    registry_record["size_bytes"] = len(registry_bytes)
    registry_record["sha256"] = sha256_bytes(registry_bytes)
    snapshot_bytes = _canonical_bytes(snapshot)
    (root / "architecture-policy-snapshot.json").write_bytes(snapshot_bytes)
    snapshot_record = next(
        record
        for record in manifest["files"]
        if record["path"] == "architecture-policy-snapshot.json"
    )
    snapshot_record["size_bytes"] = len(snapshot_bytes)
    snapshot_record["sha256"] = sha256_bytes(snapshot_bytes)
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    sources = _verified_sources(root, snapshot, manifest)

    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert report.status is ValidationStatus.INVALID
    assert "POLICY_APPROVAL_UNVERIFIED" in report.reason_codes


def test_draft_policy_is_not_treated_as_normatively_valid(tmp_path: Path) -> None:
    policy = _policy(status="DRAFT")
    root, snapshot, manifest, charter = _build_bundle(tmp_path / "bundle", policies=[policy])
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert report.status is ValidationStatus.UNDETERMINED
    assert "POLICY_DRAFT_NON_NORMATIVE" in report.reason_codes


def test_equal_authority_conflicting_polarities_return_policy_conflict(
    tmp_path: Path,
) -> None:
    first = _policy(policy_id="POL_REQUIRED", polarity="REQUIRED")
    second = _policy(policy_id="POL_FORBIDDEN", polarity="FORBIDDEN")
    root, snapshot, manifest, charter = _build_bundle(tmp_path / "bundle", policies=[first, second])
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert "POLICY_CONFLICT" in report.reason_codes
    assert report.status is ValidationStatus.UNDETERMINED


def test_lower_authority_retirement_does_not_override_higher_authority(
    tmp_path: Path,
) -> None:
    target = _policy(policy_id="POL_SENIOR", role="architecture_authority")
    retirement = _policy(
        policy_id="POL_RETIREMENT",
        kind="RETIREMENT",
        role="junior_authority",
        targets=["POL_SENIOR"],
    )
    root, snapshot, manifest, charter = _build_bundle(
        tmp_path / "bundle", policies=[target, retirement]
    )
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert report.status is ValidationStatus.UNDETERMINED
    assert "POLICY_CONFLICT" in report.reason_codes


def _closure_claim(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "CLAIM_REGISTRY_CLOSED",
        "kind": "AUTHORITATIVE_POLICY_REGISTRY",
        "state": "after",
        "fact_type": "policy_registry",
        "scope": "application",
        "architecture_revision": snapshot["architecture"]["after_commit"],
        "method_id": "synthetic_registry_closure_check_v1",
        "evidence_source_ids": ["CLOSURE_EVIDENCE"],
        "assumptions": [],
        "procedure_ref": "SYNTHETIC_REVIEW_PROCEDURE_V1",
        "policy_registry_version": "synthetic-registry-v1",
        "as_of": "2026-10-13T00:00:00Z",
    }


def test_claimed_registry_closure_requires_independent_verifier(tmp_path: Path) -> None:
    seed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    claim = _closure_claim(seed)
    root, snapshot, manifest, charter = _build_bundle(
        tmp_path / "bundle", closure="CLAIMED_CLOSED", claims=[claim]
    )
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_completeness_claims(snapshot, None, sources)
    authority = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        completeness_report=report,
    )

    assert report.status is ValidationStatus.UNDETERMINED
    assert authority.status is ValidationStatus.UNDETERMINED
    assert "REGISTRY_CLOSURE_UNVERIFIED" in authority.reason_codes


def test_completeness_verifier_rejects_non_evidence_source_role(tmp_path: Path) -> None:
    seed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    claim = _closure_claim(seed)
    root, snapshot, manifest, _ = _build_bundle(
        tmp_path / "bundle",
        closure="CLAIMED_CLOSED",
        claims=[claim],
        source_overrides={
            "CLOSURE_EVIDENCE": (
                "architecture/structural-evidence.json",
                "STRUCTURAL_OBSERVATION",
                b"synthetic wrong role evidence",
            )
        },
    )
    sources, integrity_report = load_verified_source_manifest(snapshot, manifest, root)
    assert integrity_report.status is ValidationStatus.INVALID

    report = verify_completeness_claims(snapshot, lambda *_args: True, sources)

    assert report.status is ValidationStatus.INVALID
    assert "SOURCE_NOT_ALLOWLISTED" in report.reason_codes


@pytest.mark.parametrize("verdict", [True, False, "timeout"])
def test_completeness_verifier_has_separate_bounded_verdict(
    tmp_path: Path, verdict: bool | str
) -> None:
    seed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    claim = _closure_claim(seed)
    root, snapshot, manifest, _ = _build_bundle(
        tmp_path / "bundle", closure="CLAIMED_CLOSED", claims=[claim]
    )
    sources = _verified_sources(root, snapshot, manifest)

    def verifier(
        claim: Mapping[str, Any],
        sources: Mapping[str, SourceReference],
        snapshot: Mapping[str, Any],
    ) -> bool | None:
        del claim, sources, snapshot
        if verdict == "timeout":
            raise TimeoutError("synthetic verifier timeout")
        if isinstance(verdict, bool):
            return verdict
        raise AssertionError("unreachable test verifier state")

    report = verify_completeness_claims(snapshot, verifier, sources)
    if verdict is True:
        assert report.status is ValidationStatus.VALID
        assert "CLAIM_REGISTRY_CLOSED" in report.evidence_refs
    else:
        assert report.status is ValidationStatus.UNDETERMINED
        assert "COMPLETENESS_UNVERIFIED" in report.reason_codes


def test_completeness_claim_revision_or_registry_version_mismatch_is_invalid(
    tmp_path: Path,
) -> None:
    seed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    claim = _closure_claim(seed)
    claim["architecture_revision"] = "f" * 40
    root, snapshot, manifest, _ = _build_bundle(
        tmp_path / "bundle", closure="CLAIMED_CLOSED", claims=[claim]
    )
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_completeness_claims(snapshot, lambda *_args: True, sources)

    assert report.status is ValidationStatus.INVALID
    assert "VERSION_MISMATCH" in report.reason_codes


def test_failed_policy_approval_binding_is_invalid(tmp_path: Path) -> None:
    policy = _policy(effective_from="2027-01-01T00:00:00Z")
    root, snapshot, manifest, charter = _build_bundle(tmp_path / "bundle", policies=[policy])
    sources = _verified_sources(root, snapshot, manifest)
    report = verify_policy_authority(
        snapshot,
        charter,
        sources,
        _synthetic_trust(sources),
        known_obligation_ids={"AC_PUBLIC_API"},
    )

    assert report.status is ValidationStatus.INVALID
    assert "VERSION_MISMATCH" in report.reason_codes
