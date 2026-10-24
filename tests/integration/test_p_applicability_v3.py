"""Isolation tests for the independently pinned policy source V3 candidate."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import pytest
import yaml
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import load_schema
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.inputs import FITNESS_INPUTS, TRACEABILITY_INPUT
from experiments.execution.tooling.p_adaptation import (
    _side_evidence_inputs,
    _verify_adaptation_evidence,
    run_adaptation,
    verify_v3_p_bundle,
)
from experiments.execution.tooling.p_adaptation_evidence import (
    AdaptationEvidenceVerifierRegistry,
    thaw_verified_payload,
)
from experiments.execution.tooling.p_applicability import (
    ApplicabilityStatus,
    EvidenceLedger,
    EvidenceProof,
    ProofStatus,
    evaluate_obligations,
    load_and_validate_ruleset,
)
from experiments.execution.tooling.p_candidate import candidate_sha256
from experiments.execution.tooling.p_governance import governance_authorizes_outputs
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
from experiments.execution.tooling.p_operations import template_descriptor_sha256
from experiments.execution.tooling.p_policy_source_v3 import (
    RULESET_PATH,
    export_method_inputs_v3,
    package_policy_source_v3,
    verify_method_bundle_v3,
)
from experiments.execution.tooling.p_semantic import pair_proof_subject

REPOSITORY_ROOT = Path(__file__).parents[2]
POLICY_SOURCE = REPOSITORY_ROOT / "experiments/execution/policy-pilot/v1/source"
EVALUATION_AS_OF = "2026-10-14T00:00:00Z"


def _git(
    repository: Path,
    *arguments: str,
    env: Mapping[str, str] | None = None,
) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise AssertionError("Git is required for V3 isolation tests")
    result = subprocess.run(  # noqa: S603 - fixed local Git executable and argument list
        [executable, "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=dict(env) if env is not None else None,
    )
    return result.stdout.strip()


def _write(repository: Path, relative: str, content: bytes) -> None:
    destination = repository / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", "-A")
    environment = dict(os.environ)
    environment["GIT_AUTHOR_DATE"] = "2000-01-01T00:00:00Z"
    environment["GIT_COMMITTER_DATE"] = "2000-01-01T00:00:00Z"
    _git(
        repository,
        "-c",
        "user.name=Applicability V3 Test",
        "-c",
        "user.email=applicability-v3@example.invalid",
        "commit",
        "-m",
        message,
        env=environment,
    )
    return _git(repository, "rev-parse", "HEAD")


def _synthetic_architecture_repository(
    root: Path,
    *,
    include_structural_facts: bool = True,
    before_files: Mapping[str, bytes] | None = None,
    after_files: Mapping[str, bytes] | None = None,
    removed_after_paths: Sequence[str] = (),
) -> tuple[Path, str, str]:
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
    if not include_structural_facts:
        manifest_path = repository / STRUCTURAL_MANIFEST_PATH
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        for key in (
            "deployment",
            "shared_infrastructure",
            "modules",
            "preserved_cross_module_dependencies",
        ):
            manifest.pop(key, None)
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    for relative, content in sorted((before_files or {}).items()):
        _write(repository, relative, content)
    before_sha = _commit(repository, "synthetic architecture before")

    app_init = repository / "app/__init__.py"
    app_init.write_bytes(app_init.read_bytes() + b"\n# synthetic target revision\n")
    for relative in sorted(removed_after_paths):
        (repository / relative).unlink()
    for relative, content in sorted((after_files or {}).items()):
        _write(repository, relative, content)
    after_sha = _commit(repository, "synthetic architecture after")
    return repository, before_sha, after_sha


def _synthetic_evaluator_source() -> bytes:
    """Return an independently authored evaluator used only by this TEST_ONLY fixture."""
    return (
        b"from pathlib import Path\n"
        b"import json, sys\n"
        b"root = Path(sys.argv[1])\n"
        b"if len(sys.argv) > 3:\n"
        b" configured = json.loads(sys.argv[2])\n"
        b" required = json.loads(sys.argv[3])\n"
        b" resolved = sorted(target for target in configured if target in required "
        b"and (root / target).is_file())\n"
        b" missing = sorted(set(required) - set(resolved))\n"
        b" inspected = sorted(set(required))\n"
        b"else:\n"
        b" targets = sorted(path.relative_to(root).as_posix() for path in root.rglob('*.py'))\n"
        b" resolved = ['app.modules'] if any(name.startswith('modules/') "
        b"for name in targets) else []\n"
        b" required = ['app.modules']\n"
        b" configured = ['app.modules']\n"
        b" missing = [] if resolved else required\n"
        b" inspected = [name for name in targets if name.startswith('modules/')]\n"
        b"ok = bool(resolved) and not missing\n"
        b"print(json.dumps({'configured_targets': configured, 'resolved_targets': resolved, "
        b"'inspected_subjects': inspected, 'missing_targets': missing, "
        b"'inspected_edge_count': len(inspected), 'inspection_unit': 'file', "
        b"'expected_subjects': inspected, 'measured_count': len(inspected)}, sort_keys=True))\n"
        b"raise SystemExit(0 if ok else 2)\n"
    )


def _synthetic_positive_architecture_repository(
    root: Path,
    *,
    include_parent_representation: bool = True,
    before_files: Mapping[str, bytes] | None = None,
    after_files: Mapping[str, bytes] | None = None,
    removed_after_paths: Sequence[str] = (),
    parent_scope: Mapping[str, Any] | None = None,
) -> tuple[Path, str, str, bytes]:
    """Pin a TEST_ONLY evaluator input in a throwaway Git repository."""
    repository, before_sha, after_sha = _synthetic_architecture_repository(
        root,
        include_structural_facts=False,
        before_files=before_files,
        after_files=after_files,
        removed_after_paths=removed_after_paths,
    )
    artifact = _synthetic_evaluator_source()
    representations_path = repository / "fitness/catalog/a0-fitness-elements.yaml"
    representation_doc = yaml.safe_load(representations_path.read_text(encoding="utf-8"))
    for row in representation_doc["representations"]:
        if row["id"] == "REP_A0_ARCH_CI_LAYERING":
            row["active"] = True
            row["evaluator"] = "synthetic_scope_probe_v1"
            row["evaluator_artifact"] = {
                "path": "synthetic/evaluators/scope_probe.py",
                "sha256": sha256_bytes(artifact),
            }
            row["evidence_contract"] = {"contract_id": "SYNTHETIC_SCOPE_PROBE_V1"}
            if parent_scope is not None:
                row["applicability_scope"] = dict(parent_scope)
    representation_doc["representations"] = (
        [
            row
            for row in representation_doc["representations"]
            if row["id"] == "REP_A0_ARCH_CI_LAYERING"
        ]
        if include_parent_representation
        else []
    )
    representations_path.write_text(
        yaml.safe_dump(representation_doc, sort_keys=False), encoding="utf-8"
    )
    after_sha = _commit(repository, "test-only evaluator capability")
    return repository, before_sha, after_sha, artifact


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
    trust_scope: Literal["TEST_ONLY"] = "TEST_ONLY"
    policy_key = b"test-only-policy-approval-key"
    adaptation_key = b"test-only-adaptation-evidence-key"

    def __init__(self) -> None:
        self.adaptation_evidence_verifiers = AdaptationEvidenceVerifierRegistry(
            {"synthetic_adaptation_test_verifier_v1": _SyntheticAdaptationEvidenceVerifier()}
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
        expected_signature = hmac.new(
            self.policy_key, canonical_json_bytes(signed_payload), hashlib.sha256
        ).hexdigest()
        if approval.get("signature") != expected_signature:
            return None
        if approval.get("effective_from") > evaluation_as_of:
            return False
        return True


class _SyntheticAdaptationEvidenceVerifier:
    """HMAC verifier whose fixed key is confined to TEST_ONLY integration tests."""

    trust_scope: Literal["TEST_ONLY"] = "TEST_ONLY"

    def verify(self, verifier_id: str, content_sha256: str, signature: str) -> bool:
        if verifier_id != "synthetic_adaptation_test_verifier_v1":
            return False
        expected = hmac.new(
            _SyntheticTrustContext.adaptation_key,
            content_sha256.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _synthetic_policy_source_for_pipeline(
    root: Path,
    after_revision: str,
    *,
    before_revision: str | None = None,
    positive_active_policy_id: str | None = None,
    multi_state_closure: bool = True,
    closure_binding_override: tuple[str, str, str] | None = None,
    complete_fact_inventory: bool = False,
    active_policy_states: Sequence[str] = ("before", "after"),
    architecture_repository: Path | None = None,
) -> tuple[Path, str]:
    """Build a closed test-only source; the optional positive fixture resolves all candidates."""
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
    if positive_active_policy_id is None:
        selected = unconditional[:2]
    else:
        selected = list(registry["policies"])
        active = [policy for policy in selected if policy["id"] == positive_active_policy_id]
        assert len(active) == 1
    registry["scope"] = "source:app"
    for policy in registry["policies"]:
        policy["scope"] = "source:app"
    if positive_active_policy_id is not None:
        active[0]["applies_to_states"] = list(active_policy_states)
    charter_path = source / "fitness/policy/authority-charter.json"
    charter = json.loads(charter_path.read_text(encoding="utf-8"))
    charter["version"] = "synthetic-integration-test-v1"
    charter["role_permissions"]["research_policy_author"] = [
        "APPROVE_POLICY",
        "DRAFT_POLICY",
        *(["REVOKE_POLICY"] if positive_active_policy_id is not None else []),
    ]
    _write_json(charter_path, charter)

    approval_states: dict[str, str] = {}
    for index, policy in enumerate(selected):
        approval_id = f"SYNTHETIC_APPROVAL_{index + 1}"
        if positive_active_policy_id is None:
            policy["normative_status"] = "APPROVED"
        else:
            policy["normative_status"] = (
                "APPROVED" if policy["id"] == positive_active_policy_id else "REVOKED"
            )
            if policy["normative_status"] == "REVOKED":
                # The snapshot contract requires a selector even on a revoked row. The
                # selector is never evaluated for this TEST_ONLY retired candidate.
                if policy.get("condition_ref") is not None:
                    policy["condition_ref"] = "COND_HAS_SHARED_INFRASTRUCTURE"
        policy["approval_source_id"] = approval_id
        approval_states[approval_id] = (
            "UNDETERMINED" if positive_active_policy_id is None and index == 1 else "VERIFIED"
        )

    registry["closure"] = "CLAIMED_CLOSED"
    if multi_state_closure:
        registry["schema_version"] = "1.2"
        registry.pop("closure_claim_id")
        registry["closure_claim_ids"] = [
            f"SYNTHETIC_POLICY_CLOSURE_{state.upper()}"
            for state, revision in (("after", after_revision), ("before", before_revision))
            if revision is not None
        ]
    else:
        registry["closure_claim_id"] = "SYNTHETIC_POLICY_CLOSURE_AFTER"
    _write_json(registry_path, registry)

    for policy in selected:
        approval_id = str(policy["approval_source_id"])
        action = str(policy["normative_status"])
        is_verified = approval_states[approval_id] == "VERIFIED"
        signed_payload = {
            "action": action,
            "policy_sha256": sha256_bytes(canonical_json_bytes(policy)),
            "signer_key_id": _SyntheticTrustContext.signer_key_id,
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
            "historical_consequence": (
                "TEST_ONLY fixture excludes non-selected synthetic candidate"
                if action == "REVOKED"
                else None
            ),
            "superseded_by_policy_ids": [],
            "signer_key_id": _SyntheticTrustContext.signer_key_id,
            "signature": (
                hmac.new(
                    _SyntheticTrustContext.policy_key,
                    canonical_json_bytes(signed_payload),
                    hashlib.sha256,
                ).hexdigest()
                if is_verified
                else "synthetic-signature-not-verified"
            ),
        }
        _write_json(source / f"fitness/policy/approvals/{approval_id}.json", approval)

    closure_claims: list[dict[str, Any]] = []
    for state, revision in (("after", after_revision), ("before", before_revision)):
        if revision is None:
            continue
        evidence_id = f"SYNTHETIC_CLOSURE_EVIDENCE_{state.upper()}"
        closure_claim = {
            "id": f"SYNTHETIC_POLICY_CLOSURE_{state.upper()}",
            "kind": "AUTHORITATIVE_POLICY_REGISTRY",
            "state": state,
            "fact_type": "obligation:all",
            "scope": registry["scope"],
            "architecture_revision": revision,
            "method_id": "synthetic_policy_registry_verifier_v1",
            "evidence_source_ids": [evidence_id],
            "assumptions": [f"obligation_catalog_sha256:{ruleset.obligation_catalog_sha256}"],
            "procedure_ref": "synthetic-test://closed-policy-registry",
            "policy_registry_version": registry["registry_version"],
            "as_of": registry["as_of"],
        }
        if closure_binding_override is not None and state == closure_binding_override[0]:
            _, field, value = closure_binding_override
            closure_claim[field] = value
        closure_claims.append(closure_claim)
        evidence = {
            "fixture": "synthetic-closed-policy-registry-v1",
            "state": state,
            "scope": registry["scope"],
            "policy_registry_version": registry["registry_version"],
            "as_of": registry["as_of"],
            "architecture_revision": revision,
        }
        _write_json(source / f"fitness/policy/evidence/{evidence_id}.json", evidence)
    if complete_fact_inventory:
        if architecture_repository is None or before_revision is None:
            raise ValueError("Complete synthetic module inventory requires both Git revisions")
        before_modules = _synthetic_python_modules(architecture_repository, before_revision)
        after_modules = _synthetic_python_modules(architecture_repository, after_revision)
        module_deltas = {
            "component.module_added": sorted(after_modules - before_modules),
            "component.module_removed": sorted(before_modules - after_modules),
        }
        for fact_type, module_delta_value in module_deltas.items():
            delta_suffix = fact_type.rsplit(".", maxsplit=1)[-1].upper()
            claim_id = f"SYNTHETIC_MODULE_DELTA_{delta_suffix}_BEFORE"
            evidence_id = f"SYNTHETIC_MODULE_DELTA_{delta_suffix}_EVIDENCE"
            claim = {
                "id": claim_id,
                "kind": "EXACT_ENUMERATION",
                "state": "before",
                "fact_type": fact_type,
                "scope": registry["scope"],
                "architecture_revision": before_revision,
                "method_id": "synthetic_exact_fact_inventory_v1",
                "evidence_source_ids": [evidence_id],
                "assumptions": [],
                "procedure_ref": "synthetic-test://exact-module-delta",
            }
            closure_claims.append(claim)
            _write_json(
                source / f"fitness/policy/evidence/{evidence_id}.json",
                {
                    "fixture": "synthetic-exact-module-delta-v1",
                    "state": "before",
                    "fact_type": fact_type,
                    "scope": registry["scope"],
                    "architecture_revision": before_revision,
                    "value": module_delta_value,
                },
            )
    _write_json(
        source / "fitness/policy/completeness-claims.json",
        sorted(closure_claims, key=lambda claim: str(claim["id"])),
    )
    return source, "SYNTHETIC_POLICY_CLOSURE_AFTER"


def _synthetic_python_modules(repository: Path, revision: str) -> set[str]:
    paths = _git(repository, "ls-tree", "-r", "--name-only", revision, "--", "app").splitlines()
    modules: set[str] = set()
    for value in paths:
        path = Path(value)
        if path.suffix != ".py" or not path.parts or path.parts[0] != "app":
            continue
        parts = list(path.parts[1:-1]) + [path.stem]
        if parts[-1] == "__init__":
            parts.pop()
        modules.add("app" if not parts else "app." + ".".join(parts))
    return modules


def _synthetic_completeness_verifier(
    claim: Mapping[str, Any],
    sources: Mapping[str, SourceReference],
    snapshot: Mapping[str, Any],
) -> bool | None:
    evidence_ids = claim.get("evidence_source_ids")
    if not isinstance(evidence_ids, list) or len(evidence_ids) != 1:
        return None
    source_id = str(evidence_ids[0])
    source = sources.get(source_id)
    if source is None or source.content is None:
        return None
    try:
        evidence = json.loads(source.content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    architecture = snapshot.get("architecture", {})
    registry = snapshot.get("policy_registry", {})
    state = claim.get("state")
    revision_key = "before_commit" if state == "before" else "after_commit"
    closure_verified = bool(
        claim.get("kind") == "AUTHORITATIVE_POLICY_REGISTRY"
        and evidence.get("fixture") == "synthetic-closed-policy-registry-v1"
        and evidence.get("state") == state
        and claim.get("scope") == evidence.get("scope") == registry.get("scope")
        and claim.get("policy_registry_version")
        == evidence.get("policy_registry_version")
        == registry.get("registry_version")
        and claim.get("as_of") == evidence.get("as_of") == registry.get("as_of")
        and claim.get("architecture_revision")
        == evidence.get("architecture_revision")
        == architecture.get(revision_key)
    )
    if claim.get("kind") == "AUTHORITATIVE_POLICY_REGISTRY":
        return closure_verified

    facts = snapshot.get("facts", [])
    matching_facts = [
        fact
        for fact in facts
        if isinstance(fact, Mapping)
        and fact.get("predicate") == claim.get("fact_type")
        and fact.get("state") == "after"
        and fact.get("scope") == claim.get("scope")
    ]
    before_module_facts = [
        fact
        for fact in facts
        if isinstance(fact, Mapping)
        and fact.get("predicate") == "component.python_module_identity"
        and fact.get("state") == "before"
        and fact.get("scope") == claim.get("scope")
    ]
    after_module_facts = [
        fact
        for fact in facts
        if isinstance(fact, Mapping)
        and fact.get("predicate") == "component.python_module_identity"
        and fact.get("state") == "after"
        and fact.get("scope") == claim.get("scope")
    ]
    expected_module_delta: list[str] | None = None
    if len(before_module_facts) == 1 and len(after_module_facts) == 1:
        before_modules = set(before_module_facts[0].get("value", []))
        after_modules = set(after_module_facts[0].get("value", []))
        if claim.get("fact_type") == "component.module_added":
            expected_module_delta = sorted(after_modules - before_modules)
        elif claim.get("fact_type") == "component.module_removed":
            expected_module_delta = sorted(before_modules - after_modules)
    exact_module_delta = (
        expected_module_delta is not None
        and evidence.get("value") == expected_module_delta
        and len(matching_facts) == 1
        and matching_facts[0].get("value") == expected_module_delta
    )
    return bool(
        claim.get("kind") == "EXACT_ENUMERATION"
        and state == "before"
        and evidence.get("fixture") == "synthetic-exact-module-delta-v1"
        and evidence.get("state") == state
        and evidence.get("fact_type") == claim.get("fact_type")
        and evidence.get("scope") == claim.get("scope") == registry.get("scope")
        and evidence.get("architecture_revision")
        == claim.get("architecture_revision")
        == architecture.get("before_commit")
        and exact_module_delta
        and len(matching_facts) == 1
        and matching_facts[0].get("value") == evidence.get("value")
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
    fact_proofs = {
        str(fact["id"]): _proof(
            ProofStatus.VALID,
            fact,
            [str(source_id) for source_id in fact["source_ids"]],
            source_manifest,
            "synthetic_fact_inventory_verifier_v1",
        )
        for fact in snapshot["facts"]
        if isinstance(fact, Mapping)
        and fact.get("epistemic_kind") != "UNKNOWN"
        and validation.fact_status is ValidationStatus.VALID
        and (
            fact.get("epistemic_kind") != "EXTRACTED"
            or _synthetic_fact_verifier(
                fact,
                {
                    str(source_id): source_manifest[str(source_id)]
                    for source_id in fact.get("source_ids", [])
                    if str(source_id) in source_manifest
                },
                snapshot,
            )
            is True
        )
    }
    return EvidenceLedger(
        fact_proofs=fact_proofs,
        policy_proofs=policy_proofs,
        completeness_proofs=completeness_proofs,
        registry_proof=registry_proof,
        charter_proof=charter_proof,
    )


def _synthetic_fact_verifier(
    fact: Mapping[str, Any],
    sources: Mapping[str, SourceReference],
    snapshot: Mapping[str, Any],
) -> bool | None:
    """Recompute the three exported module inventory facts from pinned inventory bytes."""
    if fact.get("method_id") != "git_tree_py_module_inventory_v1":
        return None
    state_sources = {
        source.state: source
        for source in sources.values()
        if source.state in {"before", "after"} and source.content is not None
    }
    state = fact.get("state")
    if state not in {"before", "after"}:
        return None
    try:
        inventories = {
            name: json.loads(source.content or b"") for name, source in state_sources.items()
        }
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    def module_names(inventory: Mapping[str, Any]) -> set[str]:
        result: set[str] = set()
        for row in inventory.get("files", []):
            if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
                return set()
            path = Path(str(row["path"]))
            if path.suffix != ".py" or not path.parts or path.parts[0] != "app":
                return set()
            parts = list(path.parts[1:-1]) + [path.stem]
            if parts[-1] == "__init__":
                parts.pop()
            result.add("app" if not parts else "app." + ".".join(parts))
        return result

    by_state = {name: module_names(value) for name, value in inventories.items()}
    if not by_state or not all(by_state.values()):
        return None
    predicate = fact.get("predicate")
    expected: Any
    if predicate == "component.python_module_identity":
        expected = sorted(by_state[str(state)])
    elif predicate == "component.module_added":
        if set(by_state) != {"before", "after"}:
            return None
        expected = sorted(by_state["after"] - by_state["before"])
    elif predicate == "component.module_removed":
        if set(by_state) != {"before", "after"}:
            return None
        expected = sorted(by_state["before"] - by_state["after"])
    else:
        return None
    architecture = snapshot.get("architecture")
    source = state_sources.get(str(state))
    if (
        not isinstance(architecture, Mapping)
        or source is None
        or source.revision != architecture.get(f"{state}_commit")
        or fact.get("value") != expected
    ):
        return False
    return True


def _refresh_method_manifest_file(bundle_root: Path, relative: str) -> dict[str, Any]:
    manifest_path = bundle_root / "method_input_v3.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_bytes())
    content = (bundle_root / relative).read_bytes()
    row = next(item for item in manifest["files"] if item["path"] == relative)
    row["sha256"] = sha256_bytes(content)
    row["size_bytes"] = len(content)
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    manifest_path.write_bytes(pretty_json_bytes(manifest))
    return manifest


def _synthetic_positive_bundle(
    tmp_path: Path,
    *,
    include_parent_representation: bool = True,
    include_add_template: bool = False,
    multi_state_closure: bool = True,
    closure_binding_override: tuple[str, str, str] | None = None,
    architecture_noop: bool = False,
    before_files: Mapping[str, bytes] | None = None,
    after_files: Mapping[str, bytes] | None = None,
    removed_after_paths: Sequence[str] = (),
    complete_fact_inventory: bool | None = None,
    active_policy_states: Sequence[str] = ("before", "after"),
    parent_scope: Mapping[str, Any] | None = None,
    template_scope: Mapping[str, Any] | None = None,
) -> tuple[Any, _SyntheticTrustContext, bytes]:
    repository, before_sha, after_sha, evaluator_artifact = (
        _synthetic_positive_architecture_repository(
            tmp_path,
            include_parent_representation=include_parent_representation,
            before_files=before_files,
            after_files=after_files,
            removed_after_paths=removed_after_paths,
            parent_scope=parent_scope,
        )
    )
    if architecture_noop:
        before_sha = after_sha
        _git(repository, "commit", "--allow-empty", "-m", "synthetic no-op revision")
        after_sha = _git(repository, "rev-parse", "HEAD")
    policy_source, _closure_id = _synthetic_policy_source_for_pipeline(
        tmp_path,
        after_sha,
        before_revision=before_sha,
        positive_active_policy_id="POLICY_CANDIDATE_AC_LAYERING",
        multi_state_closure=multi_state_closure,
        closure_binding_override=closure_binding_override,
        complete_fact_inventory=(
            architecture_noop if complete_fact_inventory is None else complete_fact_inventory
        ),
        active_policy_states=active_policy_states,
        architecture_repository=repository,
    )
    policy_bundle = tmp_path / "policy-bundles/synthetic-positive"
    package_policy_source_v3(policy_source, policy_bundle, "synthetic-positive-policy-v1")
    bundle_root = tmp_path / "method-inputs/synthetic-positive-P"
    _export(repository, policy_bundle, bundle_root, "P", before_sha, after_sha)

    capabilities_path = bundle_root / "fitness/evaluator-capabilities.json"
    capabilities = json.loads(capabilities_path.read_bytes())
    capabilities["evaluators"].append({"id": "synthetic_scope_probe_v1", "stages": ["ci"]})
    candidate_costs: dict[str, int] = {}
    if include_add_template:
        template_artifact = {
            "path": "synthetic/evaluators/scope_probe.py",
            "sha256": sha256_bytes(evaluator_artifact),
        }
        capabilities["generic_candidate_templates"] = [
            {
                "id": "TPL_SYNTHETIC_SCOPE_PROBE_V1",
                "representation": {
                    "id": "REP_SYNTHETIC_ARCH_CI_LAYERING",
                    "criterion": "architecture_compliance",
                    "stage": "ci",
                    "evaluator": "synthetic_scope_probe_v1",
                    "evaluator_artifact": template_artifact,
                    "covers": ["AC_LAYERING"],
                    "applicability_scope": dict(template_scope)
                    if template_scope is not None
                    else {"scope": "source:app"},
                    "evidence_contract": {"contract_id": "SYNTHETIC_SCOPE_PROBE_V1"},
                },
            }
        ]
        candidate_costs[template_artifact["sha256"]] = 0
    capabilities["p_cost_model_v1"] = {
        "schema_version": 1,
        "model_version": "SYNTHETIC_COST_V1",
        "authority_status": "TEST_ONLY",
        "max_incremental_cost": 0,
        "max_search_nodes": 10,
        "candidate_costs": candidate_costs,
    }
    capabilities_path.write_bytes(pretty_json_bytes(capabilities))
    _refresh_method_manifest_file(bundle_root, "fitness/evaluator-capabilities.json")

    trust_context = _SyntheticTrustContext()
    manifest = verify_method_bundle_v3(bundle_root, expected_method_id="P")
    snapshot = json.loads((bundle_root / P_INPUT_SNAPSHOT_PATH).read_bytes())
    rules = load_and_validate_ruleset(
        bundle_root / RULESET_PATH,
        load_fact_vocabulary(),
        REPOSITORY_ROOT / "fitness/catalog/architectural-obligations.yaml",
    )
    source_manifest, source_report = load_verified_source_manifest(snapshot, manifest, bundle_root)
    assert source_report.status is ValidationStatus.VALID
    validation = load_and_validate_snapshot(
        bundle_root,
        manifest,
        trust_context=trust_context,
        fact_verifier=_synthetic_fact_verifier,
        evidence_verifier=_synthetic_completeness_verifier,
        known_obligation_ids={item.obligation_id for item in rules.obligations},
        known_condition_ids=set(rules.conditions),
    )
    assert validation.schema_status is ValidationStatus.VALID
    assert validation.integrity_status is ValidationStatus.VALID
    assert validation.authority_status is ValidationStatus.VALID
    assert validation.fact_status is ValidationStatus.VALID
    assert validation.completeness_status is ValidationStatus.VALID
    ledger = _evidence_ledger_from_spec01(
        snapshot,
        source_manifest,
        validation,
        trust_context,
        _synthetic_completeness_verifier,
    )
    assert len(ledger.fact_proofs) == sum(
        row.get("epistemic_kind") != "UNKNOWN" for row in snapshot["facts"]
    )

    # First pass through the V3 verifier obtains the strictly parsed legacy graph. It is
    # projected into a complete TEST_ONLY typed inventory below, then verified again.
    initial_bundle = verify_v3_p_bundle(
        bundle_root,
        evidence_ledger=ledger,
        trust_context=trust_context,
        fact_verifier=_synthetic_fact_verifier,
        completeness_verifier=_synthetic_completeness_verifier,
    )
    scope = str(snapshot["policy_registry"]["scope"])
    version = str(initial_bundle.manifest["architecture_source_sha"])
    source_refs = ["P_TRACEABILITY"]
    typed_nodes: list[dict[str, Any]] = []
    by_node_id: dict[str, dict[str, Any]] = {}
    for node in initial_bundle.trace_graph.nodes:
        row = {
            "id": node.node_id,
            "kind": node.kind,
            "scope": scope,
            "version": version,
            "source_refs": source_refs,
        }
        typed_nodes.append(row)
        by_node_id[node.node_id] = row
    before_facts = [
        row
        for row in snapshot["facts"]
        if row.get("state") == "before" and row.get("epistemic_kind") != "UNKNOWN"
    ]
    after_facts = [
        row
        for row in snapshot["facts"]
        if row.get("state") == "after" and row.get("epistemic_kind") != "UNKNOWN"
    ]
    for fact in after_facts:
        matching_before = next(
            (
                row
                for row in before_facts
                if (row.get("predicate"), row.get("subject"), row.get("scope"))
                == (fact.get("predicate"), fact.get("subject"), fact.get("scope"))
            ),
            None,
        )
        fact_sources = sorted(
            set(fact.get("source_ids", []))
            | set(matching_before.get("source_ids", []) if matching_before else [])
        )
        fact_version = ",".join(
            f"{source_id}={initial_bundle.source_digests[source_id]}"
            for source_id in fact.get("source_ids", [])
        )
        row = {
            "id": str(fact["id"]),
            "kind": "fact",
            "scope": str(fact["scope"]),
            "version": fact_version,
            "source_refs": sorted(set(fact_sources) | {"P_TRACEABILITY"}),
        }
        typed_nodes.append(row)
        by_node_id[str(row["id"])] = row
    typed_edges = [
        {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "kind": edge.kind,
            "source_refs": source_refs,
            "scope": scope,
            "source_version": by_node_id[edge.source_id]["version"],
            "target_version": by_node_id[edge.target_id]["version"],
        }
        for edge in initial_bundle.trace_graph.edges
    ]
    trace_path = bundle_root / "fitness/a0-traceability.yaml"
    trace_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "inventory_complete": True,
                "nodes": typed_nodes,
                "edges": typed_edges,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _refresh_method_manifest_file(bundle_root, "fitness/a0-traceability.yaml")

    manifest = verify_method_bundle_v3(bundle_root, expected_method_id="P")
    source_manifest, source_report = load_verified_source_manifest(snapshot, manifest, bundle_root)
    assert source_report.status is ValidationStatus.VALID
    validation = load_and_validate_snapshot(
        bundle_root,
        manifest,
        trust_context=trust_context,
        fact_verifier=_synthetic_fact_verifier,
        evidence_verifier=_synthetic_completeness_verifier,
        known_obligation_ids={item.obligation_id for item in rules.obligations},
        known_condition_ids=set(rules.conditions),
    )
    ledger = _evidence_ledger_from_spec01(
        snapshot,
        source_manifest,
        validation,
        trust_context,
        _synthetic_completeness_verifier,
    )
    verified_bundle = verify_v3_p_bundle(
        bundle_root,
        evidence_ledger=ledger,
        trust_context=trust_context,
        fact_verifier=_synthetic_fact_verifier,
        completeness_verifier=_synthetic_completeness_verifier,
    )
    assert verified_bundle.bundle_provenance == "VERIFIED_V3"
    assert verified_bundle.trust_scope == "TEST_ONLY"
    assert verified_bundle.trace_graph.inventory_complete is True
    assert verified_bundle.snapshot_validation.authority_status is ValidationStatus.VALID
    assert after_sha == verified_bundle.manifest["architecture_source_sha"]
    return verified_bundle, trust_context, evaluator_artifact


def _scoped_sidecar_proof(
    *,
    bundle: Any,
    subject: Mapping[str, Any],
    scope: str,
    architecture_shas: tuple[str, ...],
    source_ids: list[str],
) -> dict[str, Any]:
    return {
        "status": "VALID",
        "subject_sha256": sha256_bytes(canonical_json_bytes(dict(subject))),
        "scope": scope,
        "architecture_source_shas": list(dict.fromkeys(architecture_shas)),
        "verifier_id": "synthetic_adaptation_test_verifier_v1",
        "source_bindings": [
            {"source_id": source_id, "sha256": bundle.source_digests[source_id]}
            for source_id in sorted(set(source_ids))
        ],
        "evidence_refs": sorted(set(source_ids)),
    }


def _positive_adaptation_sidecar(
    bundle: Any,
    trust_context: _SyntheticTrustContext,
    evaluator_artifact: bytes,
    work_root: Path,
    *,
    use_add_template: bool = False,
) -> dict[str, Any]:
    """Sign a complete, exact-context TEST_ONLY evidence sidecar after a real evaluator run."""
    before_sha = str(bundle.snapshot["architecture"]["before_commit"])
    after_sha = str(bundle.snapshot["architecture"]["after_commit"])
    scope = str(bundle.snapshot["policy_registry"]["scope"])
    verifier_id = "synthetic_adaptation_test_verifier_v1"
    representations = bundle.templates if use_add_template else bundle.representations
    representation = next(
        row
        for item in representations
        for row in ([item["representation"]] if use_add_template else [item])
        if row["id"]
        == ("REP_SYNTHETIC_ARCH_CI_LAYERING" if use_add_template else "REP_A0_ARCH_CI_LAYERING")
    )
    obligation = next(row for row in bundle.obligations if row["id"] == "AC_LAYERING")
    artifact = representation["evaluator_artifact"]
    assert artifact["sha256"] == sha256_bytes(evaluator_artifact)
    script_path = work_root / "scope_probe.py"
    script_path.write_bytes(evaluator_artifact)
    completed = subprocess.run(  # noqa: S603 - fixed Python executable, test-authored script and bundle path
        [sys.executable, str(script_path), str(bundle.root / "architecture/after")],
        check=False,
        capture_output=True,
        timeout=10,
    )
    output = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert output["configured_targets"]
    assert output["resolved_targets"]
    assert output["inspected_subjects"]
    evidence_path = "synthetic/evidence/scope_probe.json"
    evidence_bytes = completed.stdout
    evidence = {
        "schema_version": 1,
        "representation_id": representation["id"],
        "architecture_source_sha": after_sha,
        "evaluator_id": representation["evaluator"],
        "infrastructure_status": "completed",
        "process_exit_code": completed.returncode,
        "configured_targets": output["configured_targets"],
        "resolved_targets": output["resolved_targets"],
        "inspected_subjects": output["inspected_subjects"],
        "missing_targets": [],
        "inspected_edge_count": output["inspected_edge_count"],
        "stage_applicable": True,
        "semantic_compatible": True,
        "mapping_resolved": True,
        "evidence_contract_satisfied": True,
        "adequacy_proven": True,
        "evidence_artifacts": [{"path": evidence_path, "sha256": sha256_bytes(evidence_bytes)}],
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
    }
    pair_subject = pair_proof_subject(representation, obligation, after_sha, evidence)
    pair_sources = ["P_CAPABILITIES", "P_TRACEABILITY"]
    pair_proof = {
        "representation_id": representation["id"],
        "obligation_id": obligation["id"],
        "status": "VALID",
        "subject_sha256": sha256_bytes(canonical_json_bytes(pair_subject)),
        "verifier_id": verifier_id,
        "source_bindings": [
            {"source_id": source_id, "sha256": bundle.source_digests[source_id]}
            for source_id in sorted(pair_sources)
        ],
        "evidence_refs": ["P_TRACEABILITY"],
        "reason_codes": [],
    }
    policy_source_ids = {
        str(bundle.snapshot["policy_registry"]["source_id"]),
        str(bundle.snapshot["policy_registry"]["authority_charter_source_id"]),
    }
    for policy in bundle.snapshot["policies"]:
        if isinstance(policy, Mapping):
            for key in ("source_id", "approval_source_id"):
                if isinstance(policy.get(key), str):
                    policy_source_ids.add(str(policy[key]))
    policy_rows = [dict(row) for row in bundle.snapshot["policies"]]
    policy_inventories = []
    for state, revision in (("before", before_sha), ("after", after_sha)):
        subject = {
            "claim_type": "policy_inventory",
            "state": state,
            "scope": scope,
            "architecture_source_sha": revision,
            "policy_source_revision": bundle.manifest["policy_source_revision"],
            "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
            "rows_sha256": sha256_bytes(canonical_json_bytes(policy_rows)),
        }
        policy_inventories.append(
            {
                "state": state,
                "scope": scope,
                "architecture_source_sha": revision,
                "rows": policy_rows,
                "proof": _scoped_sidecar_proof(
                    bundle=bundle,
                    subject=subject,
                    scope=scope,
                    architecture_shas=(revision,),
                    source_ids=sorted(policy_source_ids),
                ),
            }
        )

    required_stages = {obligation["id"]: [str(representation["stage"])]}
    stage_subject = {
        "claim_type": "required_stages",
        "required_stages_sha256": sha256_bytes(canonical_json_bytes(required_stages)),
        "input_bundle_sha256": bundle.manifest["bundle_sha256"],
    }
    trace_subject = {
        "claim_type": "trace_inventory",
        "trace_graph_sha256": bundle.trace_graph.graph_sha256,
        "input_bundle_sha256": bundle.manifest["bundle_sha256"],
    }
    change_subject = {
        "claim_type": "change_inventory",
        "snapshot_sha256": bundle.snapshot_validation.snapshot_digest,
        "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        "policy_source_revision": bundle.manifest["policy_source_revision"],
        "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
    }
    change_source_ids = (
        {
            str(source_id)
            for fact in bundle.snapshot["facts"]
            for source_id in fact.get("source_ids", [])
        }
        | policy_source_ids
        | {
            str(source_id)
            for claim in bundle.snapshot["completeness_claims"]
            for source_id in claim.get("evidence_source_ids", [])
        }
    )
    stage_proof = _scoped_sidecar_proof(
        bundle=bundle,
        subject=stage_subject,
        scope=scope,
        architecture_shas=(after_sha,),
        source_ids=["P_CAPABILITIES"],
    )
    trace_proof = _scoped_sidecar_proof(
        bundle=bundle,
        subject=trace_subject,
        scope=scope,
        architecture_shas=(before_sha, after_sha),
        source_ids=["P_TRACEABILITY"],
    )
    change_proof = _scoped_sidecar_proof(
        bundle=bundle,
        subject=change_subject,
        scope=scope,
        architecture_shas=(before_sha, after_sha),
        source_ids=sorted(change_source_ids),
    )
    cost_subject = {
        "claim_type": "cost_model_authority",
        "cost_model_sha256": sha256_bytes(canonical_json_bytes(bundle.cost_model)),
        "capabilities_sha256": bundle.source_digests["P_CAPABILITIES"],
        "input_bundle_sha256": bundle.manifest["bundle_sha256"],
    }
    cost_proof = _scoped_sidecar_proof(
        bundle=bundle,
        subject=cost_subject,
        scope=scope,
        architecture_shas=(after_sha,),
        source_ids=["P_CAPABILITIES"],
    )

    classification_rows = [
        {"obligation_id": str(row["id"]), "mandatory": row["id"] == obligation["id"]}
        for row in bundle.obligations
    ]
    classification_subject = {
        "claim_type": "test_only_mandatory_classification",
        "rows_sha256": sha256_bytes(canonical_json_bytes(classification_rows)),
        "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        "policy_source_revision": bundle.manifest["policy_source_revision"],
        "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
    }
    classification_proof = _scoped_sidecar_proof(
        bundle=bundle,
        subject=classification_subject,
        scope=scope,
        architecture_shas=(before_sha, after_sha),
        source_ids=sorted(policy_source_ids),
    )
    fact_absence_proofs = []
    for claim in bundle.snapshot.get("completeness_claims", []):
        if (
            not isinstance(claim, Mapping)
            or claim.get("kind") != "EXACT_ENUMERATION"
            or claim.get("state") != "before"
        ):
            continue
        predicate = str(claim["fact_type"])
        claim_scope = str(claim["scope"])
        absence_subject = {
            "claim_type": "fact_absence",
            "state": "before",
            "predicate": predicate,
            "scope": claim_scope,
            "architecture_source_sha": before_sha,
            "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        }
        fact_absence_proofs.append(
            {
                "state": "before",
                "predicate": predicate,
                "scope": claim_scope,
                "architecture_source_sha": before_sha,
                "proof": _scoped_sidecar_proof(
                    bundle=bundle,
                    subject=absence_subject,
                    scope=claim_scope,
                    architecture_shas=(before_sha,),
                    source_ids=list(claim["evidence_source_ids"]),
                ),
            }
        )
    payload = {
        "evaluator_evidence": [
            {
                "representation_id": representation["id"],
                "obligation_id": obligation["id"],
                "evidence": evidence,
            }
        ],
        "pair_proofs": [pair_proof],
        "artifact_bytes": [
            {
                "path": artifact["path"],
                "sha256": artifact["sha256"],
                "content_base64": base64.b64encode(evaluator_artifact).decode("ascii"),
            },
            {
                "path": evidence_path,
                "sha256": sha256_bytes(evidence_bytes),
                "content_base64": base64.b64encode(evidence_bytes).decode("ascii"),
            },
        ],
        "fact_absence_proofs": fact_absence_proofs,
        "policy_inventories": policy_inventories,
        "trace_inventory_proof": trace_proof,
        "change_inventory_proof": change_proof,
        "required_stages": required_stages,
        "stage_contract_proof": stage_proof,
        "test_only_mandatory_classification": {
            "rows": classification_rows,
            "proof": classification_proof,
        },
        "adjustment_rules": [],
        "authorized_template_descriptor_sha256": [
            template_descriptor_sha256(template) for template in bundle.templates
        ],
        "cost_model_proof": cost_proof,
    }
    sidecar = {
        "schema_version": 2,
        "contract_id": "P_ADAPTATION_EVIDENCE_V2",
        "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        "architecture_before_sha": before_sha,
        "architecture_after_sha": after_sha,
        "policy_source_revision": bundle.manifest["policy_source_revision"],
        "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
        "evaluation_as_of": bundle.snapshot["architecture"]["evaluation_as_of"],
        "scope": scope,
        "source_bindings": [
            {"source_id": source_id, "sha256": digest}
            for source_id, digest in sorted(bundle.source_digests.items())
        ],
        "verifier_id": verifier_id,
        "payload": payload,
    }
    unsigned = dict(sidecar)
    content_digest = sha256_bytes(canonical_json_bytes(unsigned))
    sidecar["sidecar_sha256"] = content_digest
    sidecar["signature"] = hmac.new(
        trust_context.adaptation_key,
        content_digest.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return sidecar


def test_v3_synthetic_noop_accepts_with_independent_before_after_closure_claims(
    tmp_path: Path,
) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        tmp_path, architecture_noop=True
    )
    sidecar = _positive_adaptation_sidecar(bundle, trust_context, evaluator_artifact, tmp_path)

    result = run_adaptation(bundle, evidence_context=sidecar)
    assert result.evidence_trust_scope == "TEST_ONLY"
    assert bundle.snapshot["schema_version"] == "1.2"
    assert result.governance.result.value == "ACCEPT", result.governance.to_dict()
    assert result.before_applicability.input_validation["completeness_status"] == "VALID"
    before = {row.obligation_id: row.status.value for row in result.before_applicability.results}
    after = {row.obligation_id: row.status.value for row in result.after_applicability.results}
    assert before["AC_LAYERING"] == "ACTIVE"
    assert after["AC_LAYERING"] == "ACTIVE"
    before_row = next(
        row for row in result.before_applicability.results if row.obligation_id == "AC_LAYERING"
    )
    after_row = next(
        row for row in result.after_applicability.results if row.obligation_id == "AC_LAYERING"
    )
    assert "SYNTHETIC_POLICY_CLOSURE_BEFORE" in before_row.evidence_refs
    assert "SYNTHETIC_POLICY_CLOSURE_AFTER" in after_row.evidence_refs
    assert result.current_coverage.status.value == "COMPLETE"
    assert result.candidate_coverage is not None
    assert result.candidate_coverage.status.value == "COMPLETE"
    assert any(
        row.obligation_id == "AC_LAYERING" and row.status.value == "VALID"
        for row in result.current_pairs
    )
    assert any(
        row.obligation_id == "AC_LAYERING" and row.status.value == "VALID"
        for row in result.candidate_pairs
    )
    assert result.candidate is not None
    assert result.candidate["candidate_validation"]["status"] == "valid"
    assert result.candidate_sha256 == candidate_sha256(result.candidate)
    assert result.candidate_v1 is not None
    assert result.prediction_v1 is not None
    assert result.candidate_v1["configuration_version"] == result.candidate["configuration_version"]
    assert result.candidate_v1["candidate_validation"] == result.candidate["candidate_validation"]
    assert (
        result.candidate_v1["architecture_source_sha"]
        == bundle.snapshot["architecture"]["after_commit"]
    )
    assert (
        result.prediction_v1["architecture_source_sha"]
        == bundle.snapshot["architecture"]["after_commit"]
    )
    assert result.prediction_v1["input_bundle_sha256"] == bundle.manifest["bundle_sha256"]
    operation_rows = [row.to_dict() for row in result.operation_plan.operations]
    assert governance_authorizes_outputs(
        result.governance,
        candidate_configuration_sha256=str(result.candidate_sha256),
        architecture_source_sha=str(bundle.snapshot["architecture"]["after_commit"]),
        input_bundle_sha256=str(bundle.manifest["bundle_sha256"]),
        operations=result.candidate["changes"],
    )
    assert governance_authorizes_outputs(
        result.governance,
        candidate_configuration_sha256=str(result.candidate_sha256),
        architecture_source_sha=str(bundle.snapshot["architecture"]["after_commit"]),
        input_bundle_sha256=str(bundle.manifest["bundle_sha256"]),
        operations=operation_rows,
    )
    invariant_verdicts = result.governance.to_dict()["invariant_verdicts"]
    assert len(invariant_verdicts) == 12
    assert set(invariant_verdicts.values()) == {"PASS"}
    operation_kinds = [row.operation.value for row in result.operation_plan.operations]
    assert "retain" in operation_kinds
    assert not {"add", "replace", "deactivate", "adjust"}.intersection(operation_kinds)
    assert next(
        row for row in result.candidate["representations"] if row["id"] == "REP_A0_ARCH_CI_LAYERING"
    ) == next(
        row
        for row in bundle.parent_configuration["representations"]
        if row["id"] == "REP_A0_ARCH_CI_LAYERING"
    )
    replay = run_adaptation(bundle, evidence_context=sidecar)
    assert replay.candidate_sha256 == result.candidate_sha256
    assert replay.operation_plan.plan_sha256 == result.operation_plan.plan_sha256
    assert (
        replay.governance.to_dict()["decision_sha256"]
        == result.governance.to_dict()["decision_sha256"]
    )
    assert replay.candidate_v1 == result.candidate_v1
    assert replay.prediction_v1 == result.prediction_v1


def test_v3_equivalent_sidecar_orderings_preserve_semantic_hashes(tmp_path: Path) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        tmp_path, architecture_noop=True
    )
    sidecar = _positive_adaptation_sidecar(bundle, trust_context, evaluator_artifact, tmp_path)
    baseline = run_adaptation(bundle, evidence_context=sidecar)

    reordered = deepcopy(sidecar)
    payload = reordered["payload"]
    payload["artifact_bytes"].reverse()
    payload["policy_inventories"].reverse()

    reordered.pop("sidecar_sha256")
    reordered.pop("signature")
    content_digest = sha256_bytes(canonical_json_bytes(reordered))
    reordered["sidecar_sha256"] = content_digest
    reordered["signature"] = hmac.new(
        trust_context.adaptation_key,
        content_digest.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    replay = run_adaptation(bundle, evidence_context=reordered)

    assert replay.governance.result.value == baseline.governance.result.value == "ACCEPT"
    assert replay.impact.assessment_sha256 == baseline.impact.assessment_sha256
    assert replay.current_coverage.assessment_sha256 == baseline.current_coverage.assessment_sha256
    assert replay.operation_plan.plan_sha256 == baseline.operation_plan.plan_sha256
    assert replay.candidate_sha256 == baseline.candidate_sha256
    assert (
        replay.governance.to_dict()["decision_sha256"]
        == baseline.governance.to_dict()["decision_sha256"]
    )
    assert replay.candidate_v1 == baseline.candidate_v1
    assert replay.prediction_v1 == baseline.prediction_v1


def test_v3_synthetic_add_uses_authorized_descriptor_and_accepts_with_scoped_closure_claims(
    tmp_path: Path,
) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        tmp_path,
        include_parent_representation=False,
        include_add_template=True,
    )
    template = bundle.templates[0]
    descriptor_digest = template_descriptor_sha256(template)
    sidecar = _positive_adaptation_sidecar(
        bundle,
        trust_context,
        evaluator_artifact,
        tmp_path,
        use_add_template=True,
    )

    assert sidecar["payload"]["authorized_template_descriptor_sha256"] == [descriptor_digest]
    assert {row["source_id"] for row in sidecar["source_bindings"]} >= {"P_CAPABILITIES"}
    result = run_adaptation(bundle, evidence_context=sidecar)

    assert result.evidence_trust_scope == "TEST_ONLY"
    assert len(result.governance.to_dict()["invariant_verdicts"]) == 12
    assert set(result.governance.to_dict()["invariant_verdicts"].values()) == {"PASS"}
    add_operations = [
        row for row in result.operation_plan.operations if row.operation.value == "add"
    ]
    assert len(add_operations) == 1
    assert add_operations[0].target_id == "AC_LAYERING"
    assert add_operations[0].artifact_sha256 == sha256_bytes(evaluator_artifact)
    assert result.current_coverage.status.value == "INCOMPLETE"
    assert result.candidate_coverage is not None
    assert result.candidate_coverage.status.value == "COMPLETE"
    assert result.candidate is not None
    assert result.candidate["candidate_validation"]["status"] == "valid"
    assert any(
        row.representation_id == "REP_SYNTHETIC_ARCH_CI_LAYERING"
        and row.obligation_id == "AC_LAYERING"
        and row.status.value == "VALID"
        for row in result.candidate_pairs
    )
    assert result.governance.result.value == "ACCEPT"
    assert result.candidate_v1 is not None
    assert result.prediction_v1 is not None
    assert result.candidate_v1["candidate_validation"]["status"] == "valid"
    assert result.prediction_v1["input_bundle_sha256"] == bundle.manifest["bundle_sha256"]
    operations = [row.operation.value for row in result.operation_plan.operations]
    assert operations.count("add") == 1
    assert not {"replace", "deactivate", "adjust"}.intersection(operations)


def test_v3_synthetic_noop_holds_when_legacy_registry_has_one_closure_claim_id(
    tmp_path: Path,
) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        tmp_path, multi_state_closure=False
    )
    sidecar = _positive_adaptation_sidecar(bundle, trust_context, evaluator_artifact, tmp_path)

    result = run_adaptation(bundle, evidence_context=sidecar)
    assert bundle.snapshot["schema_version"] == "1.1"
    before = {row.obligation_id: row.status.value for row in result.before_applicability.results}
    after = {row.obligation_id: row.status.value for row in result.after_applicability.results}
    assert before["AC_LAYERING"] == "UNKNOWN"
    assert after["AC_LAYERING"] == "ACTIVE"
    assert result.governance.result.value == "HOLD"
    assert result.candidate_v1 is None
    assert result.prediction_v1 is None


@pytest.mark.parametrize(
    ("state", "field", "value"),
    [
        ("before", "architecture_revision", "0" * 40),
        ("after", "architecture_revision", "0" * 40),
        ("before", "scope", "service:other"),
        ("after", "policy_registry_version", "SYNTHETIC_STALE_REGISTRY"),
    ],
)
def test_v3_export_rejects_mismatched_state_scoped_closure_bindings(
    tmp_path: Path,
    state: str,
    field: str,
    value: str,
) -> None:
    with pytest.raises(ContractValidationError, match="SPEC 01 semantic validation"):
        _synthetic_positive_bundle(
            tmp_path,
            closure_binding_override=(state, field, value),
        )


def test_v1_artifact_hash_sidecar_does_not_authorize_template_descriptor(
    tmp_path: Path,
) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        tmp_path,
        include_parent_representation=False,
        include_add_template=True,
    )
    sidecar = _positive_adaptation_sidecar(
        bundle,
        trust_context,
        evaluator_artifact,
        tmp_path,
        use_add_template=True,
    )
    sidecar.pop("sidecar_sha256")
    sidecar.pop("signature")
    sidecar["schema_version"] = 1
    sidecar["contract_id"] = "P_ADAPTATION_EVIDENCE_V1"
    sidecar["payload"].pop("authorized_template_descriptor_sha256")
    sidecar["payload"].pop("test_only_mandatory_classification")
    sidecar["payload"]["authorized_template_artifact_sha256"] = [sha256_bytes(evaluator_artifact)]
    sidecar["sidecar_sha256"] = sha256_bytes(canonical_json_bytes(sidecar))
    sidecar["signature"] = hmac.new(
        trust_context.adaptation_key,
        sidecar["sidecar_sha256"].encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    verified = _verify_adaptation_evidence(
        bundle,
        sidecar,
        policy_revision=str(bundle.manifest["policy_source_revision"]),
        policy_digest=str(bundle.manifest["policy_bundle_sha256"]),
    )
    assert verified is not None
    assert verified.schema_version == 1
    side_inputs = _side_evidence_inputs(
        thaw_verified_payload(verified),
        bundle,
        str(bundle.snapshot["architecture"]["before_commit"]),
        str(bundle.snapshot["architecture"]["after_commit"]),
        verified,
    )
    assert side_inputs["authorized_template_descriptor_sha256"] == frozenset()


@pytest.mark.parametrize(
    "missing_proof",
    ("policy_inventory", "pair_semantics", "cost_model", "required_stage"),
)
def test_missing_scoped_adaptation_proof_holds_without_legacy_outputs(
    tmp_path: Path,
    missing_proof: str,
) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(tmp_path)
    sidecar = _positive_adaptation_sidecar(bundle, trust_context, evaluator_artifact, tmp_path)
    payload = sidecar["payload"]
    if missing_proof == "policy_inventory":
        for inventory in payload["policy_inventories"]:
            inventory["proof"]["status"] = "UNDETERMINED"
    elif missing_proof == "pair_semantics":
        payload["pair_proofs"][0]["status"] = "UNDETERMINED"
    elif missing_proof == "cost_model":
        payload["cost_model_proof"]["status"] = "UNDETERMINED"
    else:
        payload["stage_contract_proof"]["status"] = "UNDETERMINED"

    sidecar.pop("sidecar_sha256")
    sidecar.pop("signature")
    content_digest = sha256_bytes(canonical_json_bytes(sidecar))
    sidecar["sidecar_sha256"] = content_digest
    sidecar["signature"] = hmac.new(
        trust_context.adaptation_key,
        content_digest.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    result = run_adaptation(bundle, evidence_context=sidecar)

    assert result.governance.result.value == "HOLD"
    assert result.candidate_v1 is None
    assert result.prediction_v1 is None


def test_v3_spec01_evidence_ledger_and_applicability_pipeline(tmp_path: Path) -> None:
    repository, before_sha, after_sha = _synthetic_architecture_repository(tmp_path)
    policy_source, closure_id = _synthetic_policy_source_for_pipeline(
        tmp_path, after_sha, multi_state_closure=False
    )
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
