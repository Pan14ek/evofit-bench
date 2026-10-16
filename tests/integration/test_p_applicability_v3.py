"""Isolation tests for the independently pinned policy source V3 candidate."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import load_schema
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.inputs import FITNESS_INPUTS, TRACEABILITY_INPUT
from experiments.execution.tooling.p_adaptation import run_adaptation, verify_v3_p_bundle
from experiments.execution.tooling.p_applicability import (
    ApplicabilityStatus,
    EvidenceLedger,
    EvidenceProof,
    ProofStatus,
    evaluate_obligations,
    load_and_validate_ruleset,
)
from experiments.execution.tooling.p_input_export_v2 import (
    STRUCTURAL_MANIFEST_PATH,
)
from experiments.execution.tooling.p_input_validation import (
    P_INPUT_SNAPSHOT_PATH,
    CompletenessVerifier,
    SourceReference,
    ValidationStatus,
    load_and_validate_snapshot,
    load_fact_vocabulary,
    load_verified_source_manifest,
    validate_snapshot_schema,
    validate_source_references,
)
from experiments.execution.tooling.p_policy_source_v3 import (
    RULESET_PATH,
    export_method_inputs_v3,
    package_policy_source_v3,
    verify_method_bundle_v3,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
POLICY_SOURCE = REPOSITORY_ROOT / "experiments/execution/policy-pilot/v1/source"
EVALUATION_AS_OF = "2026-10-14T00:00:00Z"


def _git(repository: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise AssertionError("Git is required for V3 isolation tests")
    result = subprocess.run(  # noqa: S603 - fixed local Git executable and argument list
        [executable, "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _write(repository: Path, relative: str, content: bytes) -> None:
    destination = repository / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", "-A")
    _git(
        repository,
        "-c",
        "user.name=Applicability V3 Test",
        "-c",
        "user.email=applicability-v3@example.invalid",
        "commit",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD")


def _synthetic_architecture_repository(root: Path) -> tuple[Path, str, str]:
    repository = root / "synthetic-architecture"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Applicability V3 Test")
    _git(repository, "config", "user.email", "applicability-v3@example.invalid")

    shutil.copytree(REPOSITORY_ROOT / "app", repository / "app")
    paths = [STRUCTURAL_MANIFEST_PATH, *(entry[0] for entry in FITNESS_INPUTS)]
    paths.append(TRACEABILITY_INPUT[0])
    for relative in paths:
        _write(repository, relative, (REPOSITORY_ROOT / relative).read_bytes())
    before_sha = _commit(repository, "synthetic architecture before")

    app_init = repository / "app/__init__.py"
    app_init.write_bytes(app_init.read_bytes() + b"\n# synthetic target revision\n")
    after_sha = _commit(repository, "synthetic architecture after")
    return repository, before_sha, after_sha


def _export(
    repository: Path,
    policy_bundle: Path,
    destination: Path,
    method_id: str,
    before_sha: str,
    after_sha: str,
) -> dict[str, Any]:
    return export_method_inputs_v3(
        repository,
        policy_bundle,
        destination,
        method_id,  # type: ignore[arg-type]
        before_sha,
        after_sha,
        EVALUATION_AS_OF,
    )


def _role_records(manifest: dict[str, Any], role: str) -> list[dict[str, Any]]:
    return [record for record in manifest["files"] if record["role"] == role]


def test_b1_and_p_receive_identical_policy_and_common_snapshot(
    tmp_path: Path,
) -> None:
    repository, before_sha, after_sha = _synthetic_architecture_repository(tmp_path)
    policy_bundle = tmp_path / "policy-bundles/shared-v1"
    source_manifest = package_policy_source_v3(
        POLICY_SOURCE, policy_bundle, "controlled-policy-pilot-candidates-v1"
    )
    b1_root = tmp_path / "method-inputs/B1"
    p_root = tmp_path / "method-inputs/P"
    b1 = _export(repository, policy_bundle, b1_root, "B1", before_sha, after_sha)
    p = _export(repository, policy_bundle, p_root, "P", before_sha, after_sha)

    assert b1["profile_status"] == p["profile_status"] == "DEVELOPMENT_UNFROZEN"
    assert b1["architecture_source_sha"] == p["architecture_source_sha"] == after_sha
    assert b1["before_tree_sha"] == p["before_tree_sha"]
    assert b1["after_tree_sha"] == p["after_tree_sha"]
    assert b1["common_snapshot_sha256"] == p["common_snapshot_sha256"]
    assert b1["policy_source_revision"] == p["policy_source_revision"]
    assert b1["policy_bundle_sha256"] == p["policy_bundle_sha256"]
    assert b1["policy_bundle_sha256"] == source_manifest["policy_bundle_sha256"]
    snapshot_bytes = (b1_root / "architecture-policy-snapshot.json").read_bytes()
    assert snapshot_bytes == (p_root / "architecture-policy-snapshot.json").read_bytes()
    snapshot = json.loads(snapshot_bytes)
    assert snapshot["policy_registry"]["closure"] == "OPEN"
    assert len(snapshot["policies"]) == 18
    assert all(policy["normative_status"] == "DRAFT" for policy in snapshot["policies"])
    assert "approval_evidence" not in {record["role"] for record in source_manifest["files"]}
    assert (b1_root / "fitness/policy/registry.json").read_bytes() == (
        p_root / "fitness/policy/registry.json"
    ).read_bytes()
    assert _role_records(b1, "architecture_before_source") == _role_records(
        p, "architecture_before_source"
    )
    assert _role_records(b1, "architecture_after_source") == _role_records(
        p, "architecture_after_source"
    )
    assert "fitness/a0-traceability.yaml" not in {record["path"] for record in b1["files"]}
    assert "fitness/a0-traceability.yaml" in {record["path"] for record in p["files"]}
    assert verify_method_bundle_v3(b1_root)["method_id"] == "B1"
    assert verify_method_bundle_v3(p_root)["method_id"] == "P"

    tampered_registry = b1_root / "fitness/policy/registry.json"
    tampered_registry.write_bytes(tampered_registry.read_bytes() + b" ")
    with pytest.raises(ProtocolError, match="hash mismatch"):
        verify_method_bundle_v3(b1_root)


def test_policy_revision_changes_without_changing_pinned_architecture(
    tmp_path: Path,
) -> None:
    repository, before_sha, after_sha = _synthetic_architecture_repository(tmp_path)
    first_source = tmp_path / "policy-source-v1"
    second_source = tmp_path / "policy-source-v2"
    shutil.copytree(POLICY_SOURCE, first_source)
    shutil.copytree(POLICY_SOURCE, second_source)
    registry_path = second_source / "fitness/policy/registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["registry_version"] = "controlled-policy-pilot-candidates-v2"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")

    first_bundle = tmp_path / "policy-bundles/v1"
    second_bundle = tmp_path / "policy-bundles/v2"
    first_policy = package_policy_source_v3(first_source, first_bundle, "policy-source-v1")
    second_policy = package_policy_source_v3(second_source, second_bundle, "policy-source-v2")
    first_root = tmp_path / "method-inputs/revision-v1"
    second_root = tmp_path / "method-inputs/revision-v2"
    first = _export(repository, first_bundle, first_root, "B1", before_sha, after_sha)
    second = _export(repository, second_bundle, second_root, "B1", before_sha, after_sha)

    assert first_policy["policy_bundle_sha256"] != second_policy["policy_bundle_sha256"]
    assert first["policy_bundle_sha256"] != second["policy_bundle_sha256"]
    assert first["architecture_before_sha"] == second["architecture_before_sha"] == before_sha
    assert first["architecture_source_sha"] == second["architecture_source_sha"] == after_sha
    assert first["before_tree_sha"] == second["before_tree_sha"]
    assert first["after_tree_sha"] == second["after_tree_sha"]
    assert _role_records(first, "architecture_before_source") == _role_records(
        second, "architecture_before_source"
    )
    assert _role_records(first, "architecture_after_source") == _role_records(
        second, "architecture_after_source"
    )
    assert first["common_snapshot_sha256"] != second["common_snapshot_sha256"]


def test_policy_source_rejects_answer_markers_and_unallowlisted_files(tmp_path: Path) -> None:
    source = tmp_path / "policy-source"
    shutil.copytree(POLICY_SOURCE, source)
    registry_path = source / "fitness/policy/registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["expected_operations"] = ["SYNTHETIC_FORBIDDEN_FIELD"]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(ProtocolError, match="Forbidden oracle/answer marker"):
        package_policy_source_v3(source, tmp_path / "rejected-output", "reject-answer-data")

    registry.pop("expected_operations")
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    (source / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ProtocolError, match="allowlist mismatch"):
        package_policy_source_v3(source, tmp_path / "rejected-inventory", "reject-extra-file")


class _SyntheticTrustContext:
    """Test-only verifier for deterministic synthetic approvals in this integration test."""

    verifier_id = "synthetic_policy_test_verifier_v1"
    signer_key_id = "SYNTHETIC_TEST_KEY"

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
        effective_from = charter.get("effective_from")
        if not isinstance(effective_from, str):
            return None
        return (
            source_charter == charter
            and charter.get("version") == "synthetic-integration-test-v1"
            and effective_from <= evaluation_as_of
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
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if approval.get("signer_key_id") != self.signer_key_id:
            return None
        signed_payload = {
            "action": approval.get("action"),
            "policy_sha256": sha256_bytes(canonical_json_bytes(dict(policy))),
            "signer_key_id": self.signer_key_id,
        }
        expected_signature = sha256_bytes(canonical_json_bytes(signed_payload))
        if approval.get("signature") != expected_signature:
            return None
        if approval.get("effective_from") > evaluation_as_of:
            return False
        return True


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _synthetic_policy_source_for_pipeline(root: Path, after_revision: str) -> tuple[Path, str]:
    """Build a test-only source with one verified and one unresolved mandate."""
    source = root / "synthetic-policy-source"
    shutil.copytree(POLICY_SOURCE, source)
    ruleset = load_and_validate_ruleset(
        source / RULESET_PATH,
        load_fact_vocabulary(),
        REPOSITORY_ROOT / "fitness/catalog/architectural-obligations.yaml",
    )
    registry_path = source / "fitness/policy/registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    unconditional = [
        policy for policy in registry["policies"] if policy["kind"] == "UNCONDITIONAL_MANDATE"
    ]
    assert len(unconditional) >= 2
    selected = unconditional[:2]
    charter_path = source / "fitness/policy/authority-charter.json"
    charter = json.loads(charter_path.read_text(encoding="utf-8"))
    charter["version"] = "synthetic-integration-test-v1"
    charter["role_permissions"]["research_policy_author"] = ["APPROVE_POLICY", "DRAFT_POLICY"]
    _write_json(charter_path, charter)

    approval_states: dict[str, str] = {}
    for index, policy in enumerate(selected):
        approval_id = f"SYNTHETIC_APPROVAL_{index + 1}"
        policy["normative_status"] = "APPROVED"
        policy["approval_source_id"] = approval_id
        approval_states[approval_id] = "VERIFIED" if index == 0 else "UNDETERMINED"

    registry["closure"] = "CLAIMED_CLOSED"
    registry["closure_claim_id"] = "SYNTHETIC_POLICY_CLOSURE"
    _write_json(registry_path, registry)

    for policy in selected:
        approval_id = str(policy["approval_source_id"])
        is_verified = approval_states[approval_id] == "VERIFIED"
        signed_payload = {
            "action": "APPROVED",
            "policy_sha256": sha256_bytes(canonical_json_bytes(policy)),
            "signer_key_id": _SyntheticTrustContext.signer_key_id,
        }
        approval = {
            "schema_version": "1.1",
            "action": "APPROVED",
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
            "signer_key_id": _SyntheticTrustContext.signer_key_id,
            "signature": (
                sha256_bytes(canonical_json_bytes(signed_payload))
                if is_verified
                else "synthetic-signature-not-verified"
            ),
        }
        _write_json(source / f"fitness/policy/approvals/{approval_id}.json", approval)

    closure_claim = {
        "id": "SYNTHETIC_POLICY_CLOSURE",
        "kind": "AUTHORITATIVE_POLICY_REGISTRY",
        "state": "after",
        "fact_type": "obligation:all",
        "scope": registry["scope"],
        "architecture_revision": after_revision,
        "method_id": "synthetic_policy_registry_verifier_v1",
        "evidence_source_ids": ["SYNTHETIC_CLOSURE_EVIDENCE"],
        "assumptions": [f"obligation_catalog_sha256:{ruleset.obligation_catalog_sha256}"],
        "procedure_ref": "synthetic-test://closed-policy-registry",
        "policy_registry_version": registry["registry_version"],
        "as_of": registry["as_of"],
    }
    _write_json(source / "fitness/policy/completeness-claims.json", [closure_claim])
    evidence = {
        "fixture": "synthetic-closed-policy-registry-v1",
        "scope": registry["scope"],
        "policy_registry_version": registry["registry_version"],
        "as_of": registry["as_of"],
        "architecture_revision": after_revision,
    }
    _write_json(source / "fitness/policy/evidence/SYNTHETIC_CLOSURE_EVIDENCE.json", evidence)
    return source, "SYNTHETIC_POLICY_CLOSURE"


def _synthetic_completeness_verifier(
    claim: Mapping[str, Any],
    sources: Mapping[str, SourceReference],
    snapshot: Mapping[str, Any],
) -> bool | None:
    source_id = "SYNTHETIC_CLOSURE_EVIDENCE"
    source = sources.get(source_id)
    if source is None or source.content is None:
        return None
    try:
        evidence = json.loads(source.content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    architecture = snapshot.get("architecture", {})
    registry = snapshot.get("policy_registry", {})
    return bool(
        evidence.get("fixture") == "synthetic-closed-policy-registry-v1"
        and claim.get("scope") == evidence.get("scope") == registry.get("scope")
        and claim.get("policy_registry_version")
        == evidence.get("policy_registry_version")
        == registry.get("registry_version")
        and claim.get("as_of") == evidence.get("as_of") == registry.get("as_of")
        and claim.get("architecture_revision")
        == evidence.get("architecture_revision")
        == architecture.get("after_commit")
    )


def _proof(
    status: ProofStatus,
    subject: Any,
    source_ids: list[str],
    source_manifest: dict[str, SourceReference],
    verifier_id: str,
) -> EvidenceProof:
    return EvidenceProof(
        status=status,
        subject_sha256=sha256_bytes(canonical_json_bytes(subject)),
        source_bindings=tuple(
            sorted((source_id, source_manifest[source_id].sha256) for source_id in source_ids)
        ),
        verifier_id=verifier_id,
        evidence_refs=tuple(sorted(source_ids)),
    )


def _evidence_ledger_from_spec01(
    snapshot: dict[str, Any],
    source_manifest: dict[str, SourceReference],
    validation: Any,
    trust_context: _SyntheticTrustContext,
    completeness_verifier: CompletenessVerifier,
) -> EvidenceLedger:
    registry = snapshot["policy_registry"]
    charter_id = str(registry["authority_charter_source_id"])
    registry_id = str(registry["source_id"])
    charter_source = source_manifest[charter_id]
    charter = json.loads(charter_source.content or b"{}")
    architecture = snapshot["architecture"]
    evaluation_as_of = str(architecture["evaluation_as_of"])
    charter_status = (
        ProofStatus.VALID
        if trust_context.verify_charter(charter, charter_source, evaluation_as_of) is True
        else ProofStatus.UNDETERMINED
    )
    registry_status = (
        ProofStatus.VALID
        if validation.integrity_status is ValidationStatus.VALID
        else ProofStatus.UNDETERMINED
    )
    charter_proof = _proof(
        charter_status,
        {"source_id": charter_id, "sha256": charter_source.sha256},
        [charter_id],
        source_manifest,
        trust_context.verifier_id,
    )
    registry_proof = _proof(
        registry_status,
        registry,
        [registry_id],
        source_manifest,
        "spec01_pinned_source_integrity_v1",
    )
    policy_proofs: dict[str, EvidenceProof] = {}
    for policy in snapshot["policies"]:
        approval_id = policy.get("approval_source_id")
        if not isinstance(approval_id, str):
            continue
        approval_source = source_manifest[approval_id]
        verdict = trust_context.verify_approval(policy, charter, approval_source, evaluation_as_of)
        status = (
            ProofStatus.VALID
            if verdict is True
            else ProofStatus.INVALID
            if verdict is False
            else ProofStatus.UNDETERMINED
        )
        policy_proofs[str(policy["id"])] = _proof(
            status,
            policy,
            [registry_id, approval_id, charter_id],
            source_manifest,
            trust_context.verifier_id,
        )

    completeness_proofs: dict[str, EvidenceProof] = {}
    for claim in snapshot["completeness_claims"]:
        claim_sources = {
            str(source_id): source_manifest[str(source_id)]
            for source_id in claim["evidence_source_ids"]
            if str(source_id) in source_manifest
        }
        verdict = completeness_verifier(claim, claim_sources, snapshot)
        status = ProofStatus.VALID if verdict is True else ProofStatus.UNDETERMINED
        completeness_proofs[str(claim["id"])] = _proof(
            status,
            claim,
            list(claim_sources),
            source_manifest,
            "synthetic_completeness_verifier_v1",
        )
    return EvidenceLedger(
        fact_proofs={},
        policy_proofs=policy_proofs,
        completeness_proofs=completeness_proofs,
        registry_proof=registry_proof,
        charter_proof=charter_proof,
    )


def test_v3_spec01_evidence_ledger_and_applicability_pipeline(tmp_path: Path) -> None:
    repository, before_sha, after_sha = _synthetic_architecture_repository(tmp_path)
    policy_source, closure_id = _synthetic_policy_source_for_pipeline(tmp_path, after_sha)
    policy_bundle = tmp_path / "policy-bundles/pipeline"
    package_policy_source_v3(policy_source, policy_bundle, "synthetic-integration-policy-v1")
    bundle_root = tmp_path / "method-inputs/P"
    _export(repository, policy_bundle, bundle_root, "P", before_sha, after_sha)

    method_manifest = verify_method_bundle_v3(bundle_root)
    snapshot_bytes = (bundle_root / P_INPUT_SNAPSHOT_PATH).read_bytes()
    snapshot = json.loads(snapshot_bytes)
    validate_snapshot_schema(snapshot)
    source_manifest, source_report = load_verified_source_manifest(
        snapshot, method_manifest, bundle_root
    )
    assert source_report.status is ValidationStatus.VALID
    assert validate_source_references(snapshot, method_manifest, bundle_root).status is (
        ValidationStatus.VALID
    )

    trust_context = _SyntheticTrustContext()
    completeness_verifier = _synthetic_completeness_verifier
    rules = load_and_validate_ruleset(
        bundle_root / RULESET_PATH,
        load_fact_vocabulary(),
        REPOSITORY_ROOT / "fitness/catalog/architectural-obligations.yaml",
    )
    validation = load_and_validate_snapshot(
        bundle_root,
        method_manifest,
        trust_context=trust_context,
        fact_verifier=lambda _fact, _sources, _snapshot: None,
        evidence_verifier=completeness_verifier,
        known_obligation_ids={item.obligation_id for item in rules.obligations},
        known_condition_ids=set(rules.conditions),
    )
    assert validation.schema_status is ValidationStatus.VALID
    assert validation.integrity_status is ValidationStatus.VALID
    assert validation.completeness_status is ValidationStatus.VALID
    assert validation.authority_status is ValidationStatus.UNDETERMINED
    assert validation.snapshot_digest == sha256_bytes(snapshot_bytes)

    ledger = _evidence_ledger_from_spec01(
        snapshot, source_manifest, validation, trust_context, completeness_verifier
    )
    assert ledger.fact_proofs == {}  # The test never promotes Snapshot facts to verified facts.
    assessment = evaluate_obligations(snapshot, rules, ledger, "after", validation)
    repeated = evaluate_obligations(snapshot, rules, ledger, "after", validation)
    assert assessment.to_dict() == repeated.to_dict()
    assert assessment.common_input_sha256 != validation.snapshot_digest
    Draft202012Validator(load_schema("applicability_assessment_v1.schema.json")).validate(
        assessment.to_dict()
    )
    assert len(assessment.results) == 18
    statuses = Counter(result.status for result in assessment.results)
    assert statuses == {
        ApplicabilityStatus.ACTIVE: 1,
        ApplicabilityStatus.INACTIVE: 16,
        ApplicabilityStatus.UNKNOWN: 1,
    }

    approved_policies = [
        policy for policy in snapshot["policies"] if policy.get("normative_status") == "APPROVED"
    ]
    active_policy_id = str(approved_policies[0]["id"])
    active_obligation_id = str(approved_policies[0]["obligation_ids"][0])
    active_result = next(
        result for result in assessment.results if result.obligation_id == active_obligation_id
    )
    assert active_result.status is ApplicabilityStatus.ACTIVE
    assert active_policy_id in active_result.contributing_policy_ids

    unresolved_policy = approved_policies[1]
    unresolved_result = next(
        result
        for result in assessment.results
        if result.obligation_id == unresolved_policy["obligation_ids"][0]
    )
    assert unresolved_result.status is ApplicabilityStatus.UNKNOWN
    assert "POLICY_APPROVAL_UNVERIFIED" in unresolved_result.reason_codes
    assert closure_id == snapshot["policy_registry"]["closure_claim_id"]
    substituted = dict(snapshot)
    substituted_registry = dict(snapshot["policy_registry"])
    substituted_registry["registry_version"] = "substituted-snapshot-v1"
    substituted["policy_registry"] = substituted_registry
    with pytest.raises(ContractValidationError, match="SNAPSHOT_VALIDATION_MISMATCH"):
        evaluate_obligations(substituted, rules, ledger, "after", validation)

    damaged_policy_proofs = dict(ledger.policy_proofs)
    original_proof = damaged_policy_proofs[active_policy_id]
    damaged_bindings = tuple(
        (source_id, "0" * 64 if source_id == "REGISTRY" else digest)
        for source_id, digest in original_proof.source_bindings
    )
    damaged_policy_proofs[active_policy_id] = replace(
        original_proof, source_bindings=damaged_bindings
    )
    damaged_ledger = replace(ledger, policy_proofs=damaged_policy_proofs)
    damaged_assessment = evaluate_obligations(snapshot, rules, damaged_ledger, "after", validation)
    damaged_result = next(
        result
        for result in damaged_assessment.results
        if result.obligation_id == active_obligation_id
    )
    assert damaged_result.status is ApplicabilityStatus.UNKNOWN
    assert "EVIDENCE_VERSION_MISMATCH" in damaged_result.reason_codes


def test_v3_verifier_binds_nested_bundle_content_before_adaptation(tmp_path: Path) -> None:
    repository, before_sha, after_sha = _synthetic_architecture_repository(tmp_path)
    policy_source, _closure_id = _synthetic_policy_source_for_pipeline(tmp_path, after_sha)
    policy_bundle = tmp_path / "policy-bundles/verification-binding"
    package_policy_source_v3(policy_source, policy_bundle, "synthetic-verification-binding-v1")
    bundle_root = tmp_path / "method-inputs/P"
    _export(repository, policy_bundle, bundle_root, "P", before_sha, after_sha)

    verified = verify_v3_p_bundle(
        bundle_root,
        evidence_ledger=EvidenceLedger({}, {}, {}),
    )
    facts = verified.snapshot["facts"]
    assert isinstance(facts, list)
    facts.append({"id": "SYN_TAMPERED_FACT"})

    with pytest.raises(ContractValidationError, match="P03_VERIFIED_BUNDLE_CONTENT_CHANGED"):
        run_adaptation(verified)
