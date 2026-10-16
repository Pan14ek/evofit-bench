"""Development-only, fail-closed exporter for the P input contract v1.1."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess  # nosec B404 - fixed Git executable and validated argv, no shell
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.inputs import FITNESS_INPUTS, TRACEABILITY_INPUT
from experiments.execution.tooling.p_input_validation import (
    P_INPUT_SNAPSHOT_PATH,
    ValidationStatus,
    load_and_validate_snapshot,
    validate_snapshot_schema,
    validate_source_references,
)

MethodIdV2 = Literal["B1", "P"]
V2_ALLOWLIST_VERSION = "DA01_METHOD_INPUTS_V2_CANDIDATE"
V2_PROFILE_STATUS = "DEVELOPMENT_UNFROZEN"
V2_MANIFEST_PATH = "method_input_v2.json"
V2_SNAPSHOT_PATH = P_INPUT_SNAPSHOT_PATH
STRUCTURAL_SOURCE_PATH = "architecture/structural-observations.json"
BEFORE_INVENTORY_PATH = "architecture/before-inventory.json"
AFTER_INVENTORY_PATH = "architecture/after-inventory.json"
STRUCTURAL_MANIFEST_PATH = "architecture/states/A0_1_CAPABILITY_MODULES.yaml"
CHARTER_PATH = "fitness/policy/authority-charter.json"
REGISTRY_PATH = "fitness/policy/registry.json"
APPROVALS_PREFIX = "fitness/policy/approvals/"
EVIDENCE_PREFIX = "fitness/policy/evidence/"
CAPABILITIES_PATH = "fitness/evaluator-capabilities.json"

_POLICY_PROPERTY_NAMES = {
    "id",
    "kind",
    "normative_status",
    "obligation_ids",
    "proposition",
    "scope",
    "issuer_role",
    "approval_source_id",
    "source_id",
    "effective_from",
    "effective_until",
    "applies_to_states",
    "target_policy_ids",
    "condition_ref",
    "proposition_polarity",
}
_POLICY_REQUIRED_PROPERTIES = _POLICY_PROPERTY_NAMES - {
    "condition_ref",
    "proposition_polarity",
}
_CLAIM_PROPERTY_NAMES = {
    "id",
    "kind",
    "state",
    "fact_type",
    "scope",
    "architecture_revision",
    "method_id",
    "evidence_source_ids",
    "assumptions",
    "procedure_ref",
    "policy_registry_version",
    "as_of",
}
_CLAIM_REQUIRED_PROPERTIES = _CLAIM_PROPERTY_NAMES - {"policy_registry_version", "as_of"}
_SOURCE_PROPERTY_NAMES = {"id", "path", "sha256", "kind", "producer"}
_REGISTRY_PROPERTY_NAMES = {
    "schema_version",
    "registry_version",
    "scope",
    "as_of",
    "closure",
    "closure_claim_id",
    "authority_charter_source_id",
    "policies",
}
_REGISTRY_V12_PROPERTY_NAMES = (_REGISTRY_PROPERTY_NAMES - {"closure_claim_id"}) | {
    "closure_claim_ids"
}
_REGISTRY_SNAPSHOT_PROPERTY_NAMES = {
    "scope",
    "source_id",
    "closure",
    "closure_claim_id",
    "authority_charter_source_id",
    "registry_version",
    "as_of",
}
_FORBIDDEN_CONTENT_MARKERS = (
    b"expected_operations",
    b"affected_targets",
    b"ground_truth_path",
    b"new_obligations",
)
_FIXED_ROLES = {
    BEFORE_INVENTORY_PATH: "architecture_inventory",
    AFTER_INVENTORY_PATH: "architecture_inventory",
    STRUCTURAL_SOURCE_PATH: "structural_observations",
    V2_SNAPSHOT_PATH: "architecture_policy_snapshot",
    "fitness/a0-monolith.yaml": "fitness_configuration",
    "fitness/a0-representations.yaml": "representation_catalog",
    "fitness/obligations.yaml": "obligation_registry",
    "fitness/a0-importlinter.toml": "legacy_evaluator",
    CAPABILITIES_PATH: "evaluator_capabilities",
    TRACEABILITY_INPUT[1]: "traceability",
    CHARTER_PATH: "policy_charter",
    REGISTRY_PATH: "policy_registry",
}


def build_normalized_snapshot(
    *,
    architecture: Mapping[str, Any],
    before_module_names: Sequence[str],
    after_module_names: Sequence[str],
    structural_manifest: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    registry_artifact: Mapping[str, Any],
    completeness_claims: Sequence[Mapping[str, Any]] = (),
    allow_snapshot_v1_2: bool = False,
) -> dict[str, Any]:
    """Build a deterministic Snapshot from typed, explicitly allowlisted fields.

    This function never accepts or serializes the source YAML document. Its
    ``structural_manifest`` argument must already be the strict projection
    returned by :func:`_project_structural_manifest`.
    """
    architecture_keys = {
        "before_commit",
        "after_commit",
        "before_tree",
        "after_tree",
        "evaluation_as_of",
    }
    if set(architecture) != architecture_keys:
        raise ContractValidationError("architecture projection has unexpected fields")
    if set(structural_manifest) - {
        "deployment",
        "shared_infrastructure",
        "modules",
        "preserved_cross_module_dependencies",
    }:
        raise ContractValidationError("structural projection has unexpected fields")
    registry_v11 = (
        registry_artifact.get("schema_version") == "1.1"
        and set(registry_artifact) == _REGISTRY_PROPERTY_NAMES
    )
    registry_v12 = (
        allow_snapshot_v1_2
        and registry_artifact.get("schema_version") == "1.2"
        and set(registry_artifact) == _REGISTRY_V12_PROPERTY_NAMES
    )
    if not (registry_v11 or registry_v12):
        raise ContractValidationError("policy registry artifact has unexpected fields")

    projected_sources = [_project_source(source) for source in sources]
    source_ids = {str(source["id"]) for source in projected_sources}
    if len(source_ids) != len(projected_sources):
        raise ContractValidationError("source identifiers must be unique")
    if not {"ARCH_BEFORE", "ARCH_AFTER", "ARCH_OBS", "CHARTER", "REGISTRY"}.issubset(source_ids):
        raise ContractValidationError("Snapshot source inventory is incomplete")

    policies_value = registry_artifact.get("policies")
    if not isinstance(policies_value, list):
        raise ContractValidationError("policy registry policies must be an array")
    policies = [_project_policy(policy) for policy in policies_value]
    policies.sort(key=lambda item: str(item["id"]))
    claims = [_project_claim(claim) for claim in completeness_claims]
    claims.sort(key=lambda item: str(item["id"]))

    before_modules = _normalized_module_names(before_module_names)
    after_modules = _normalized_module_names(after_module_names)
    facts: list[dict[str, Any]] = []
    for state, modules, source_id in (
        ("before", before_modules, "ARCH_BEFORE"),
        ("after", after_modules, "ARCH_AFTER"),
    ):
        facts.append(
            _fact(
                f"FV01_{state.upper()}",
                state,
                "component.python_module_identity",
                "app",
                "source:app",
                modules,
                "EXTRACTED",
                [source_id],
                method_id="git_tree_py_module_inventory_v1",
            )
        )
    facts.extend(
        [
            _fact(
                "FV02_MODULES_ADDED",
                "after",
                "component.module_added",
                "app",
                "source:app",
                sorted(set(after_modules) - set(before_modules)),
                "EXTRACTED",
                ["ARCH_BEFORE", "ARCH_AFTER"],
                method_id="git_tree_py_module_inventory_v1",
            ),
            _fact(
                "FV03_MODULES_REMOVED",
                "after",
                "component.module_removed",
                "app",
                "source:app",
                sorted(set(before_modules) - set(after_modules)),
                "EXTRACTED",
                ["ARCH_BEFORE", "ARCH_AFTER"],
                method_id="git_tree_py_module_inventory_v1",
            ),
        ]
    )
    facts.extend(_facts_from_structural_manifest(structural_manifest))

    registry: dict[str, Any] = {
        "scope": registry_artifact["scope"],
        "source_id": "REGISTRY",
        "closure": registry_artifact["closure"],
        "authority_charter_source_id": registry_artifact["authority_charter_source_id"],
        "registry_version": registry_artifact["registry_version"],
        "as_of": registry_artifact["as_of"],
    }
    if registry_v12:
        closure_claim_ids = registry_artifact.get("closure_claim_ids")
        if not isinstance(closure_claim_ids, list) or any(
            not isinstance(claim_id, str) for claim_id in closure_claim_ids
        ):
            raise ContractValidationError("policy registry closure_claim_ids must be strings")
        registry["closure_claim_ids"] = sorted(closure_claim_ids)
        schema_version = "1.2"
        contract_id = "VERSIONED_ARCH_POLICY_SNAPSHOT_V1_2"
    else:
        registry["closure_claim_id"] = registry_artifact["closure_claim_id"]
        schema_version = "1.1"
        contract_id = "VERSIONED_ARCH_POLICY_SNAPSHOT_V1_1"
    snapshot = {
        "schema_version": schema_version,
        "contract_id": contract_id,
        "fact_vocabulary_version": "FV_CORE_V1",
        "architecture": dict(architecture),
        "sources": sorted(projected_sources, key=lambda item: str(item["id"])),
        "facts": sorted(facts, key=lambda item: str(item["id"])),
        "policies": policies,
        "policy_registry": registry,
        "completeness_claims": claims,
    }
    validate_snapshot_schema(snapshot)
    return snapshot


def export_method_inputs_v2(
    repository: Path,
    output_directory: Path,
    method_id: MethodIdV2,
    architecture_before_sha: str,
    architecture_source_sha: str,
    evaluation_as_of: str,
) -> dict[str, Any]:
    """Export a synthetic/development V2 bundle from pinned local Git blobs.

    An explicit reviewable policy registry and authority charter are mandatory.
    Existing A0 ``governance`` fields are never read for policy status.
    """
    root = repository.resolve(strict=True)
    destination = output_directory.resolve()
    _validate_repository_root(root)
    _validate_commit_id(architecture_before_sha, "architecture_before_sha")
    _validate_commit_id(architecture_source_sha, "architecture_source_sha")
    if method_id not in {"B1", "P"}:
        raise ProtocolError("V2 candidate export supports only B1 and P")
    if destination.exists():
        raise ProtocolError(f"Bundle output already exists: {destination}")
    if destination.is_relative_to(root):
        raise ProtocolError("Method input bundles must be created outside the repository checkout")
    if "," in str(destination):
        raise ProtocolError("Docker bind-mount paths cannot contain commas")

    try:
        charter_bytes = _git_blob(root, architecture_source_sha, CHARTER_PATH)
        registry_bytes = _git_blob(root, architecture_source_sha, REGISTRY_PATH)
    except ProtocolError as error:
        raise ContractValidationError(
            "MISSING_AUTHORITY: a pinned local policy charter and registry are required"
        ) from error
    charter = _decode_json_object(charter_bytes, "policy charter")
    registry_artifact = _decode_json_object(registry_bytes, "policy registry")
    if set(registry_artifact) != _REGISTRY_PROPERTY_NAMES:
        raise ContractValidationError("policy registry artifact has unexpected fields")
    if registry_artifact.get("authority_charter_source_id") != "CHARTER":
        raise ContractValidationError("MISSING_AUTHORITY: registry must pin source id CHARTER")
    policy_rows = registry_artifact.get("policies")
    if not isinstance(policy_rows, list):
        raise ContractValidationError("policy registry policies must be an array")

    before_tree_sha = _git_text(root, "rev-parse", f"{architecture_before_sha}:app").strip()
    after_tree_sha = _git_text(root, "rev-parse", f"{architecture_source_sha}:app").strip()
    before_paths = _git_app_python_paths(root, architecture_before_sha)
    after_paths = _git_app_python_paths(root, architecture_source_sha)
    before_modules = _module_names_from_git_paths(before_paths)
    after_modules = _module_names_from_git_paths(after_paths)
    before_inventory_files = _git_inventory_file_records(
        root, architecture_before_sha, before_paths
    )
    after_inventory_files = _git_inventory_file_records(root, architecture_source_sha, after_paths)
    manifest_bytes = _git_blob(root, architecture_source_sha, STRUCTURAL_MANIFEST_PATH)
    raw_manifest = yaml.safe_load(manifest_bytes)
    if not isinstance(raw_manifest, Mapping):
        raise ContractValidationError("Architecture state manifest must be a mapping")
    structural_manifest = _project_structural_manifest(raw_manifest)

    source_blobs: list[tuple[str, str, str, bytes, str]] = []
    before_inventory_bytes = pretty_json_bytes(
        {
            "schema_version": "1.1",
            "state": "before",
            "commit_sha": architecture_before_sha,
            "tree_sha": before_tree_sha,
            "files": before_inventory_files,
        }
    )
    after_inventory_bytes = pretty_json_bytes(
        {
            "schema_version": "1.1",
            "state": "after",
            "commit_sha": architecture_source_sha,
            "tree_sha": after_tree_sha,
            "files": after_inventory_files,
        }
    )
    observation_bytes = pretty_json_bytes(
        {
            "schema_version": "1.1",
            "source_state": "after",
            "source_commit_sha": architecture_source_sha,
            "source_tree_sha": after_tree_sha,
            "target_structural_manifest": structural_manifest,
        }
    )
    source_blobs.extend(
        [
            (
                "ARCH_BEFORE",
                BEFORE_INVENTORY_PATH,
                "ARCHITECTURE_SOURCE",
                before_inventory_bytes,
                "git_tree_inventory_v1",
            ),
            (
                "ARCH_AFTER",
                AFTER_INVENTORY_PATH,
                "ARCHITECTURE_SOURCE",
                after_inventory_bytes,
                "git_tree_inventory_v1",
            ),
            (
                "ARCH_OBS",
                STRUCTURAL_SOURCE_PATH,
                "STRUCTURAL_OBSERVATION",
                observation_bytes,
                "strict_structural_projection_v1",
            ),
            (
                "CHARTER",
                CHARTER_PATH,
                "POLICY_CHARTER",
                charter_bytes,
                "pinned_policy_authority_source",
            ),
            (
                "REGISTRY",
                REGISTRY_PATH,
                "POLICY_REGISTRY",
                registry_bytes,
                "pinned_policy_registry_source",
            ),
        ]
    )
    source_blobs.extend(_policy_sidecar_blobs(root, architecture_source_sha, charter, policy_rows))

    source_records = [
        {
            "id": source_id,
            "path": path,
            "sha256": sha256_bytes(content),
            "kind": kind,
            "producer": producer,
        }
        for source_id, path, kind, content, producer in source_blobs
    ]
    architecture = {
        "before_commit": architecture_before_sha,
        "after_commit": architecture_source_sha,
        "before_tree": before_tree_sha,
        "after_tree": after_tree_sha,
        "evaluation_as_of": evaluation_as_of,
    }
    snapshot = build_normalized_snapshot(
        architecture=architecture,
        before_module_names=before_modules,
        after_module_names=after_modules,
        structural_manifest=structural_manifest,
        sources=source_records,
        registry_artifact=registry_artifact,
    )
    snapshot_bytes = pretty_json_bytes(snapshot)

    files: list[dict[str, Any]] = []
    destination_identity: tuple[int, int] | None = None
    try:
        destination.mkdir(parents=True)
        destination_info = destination.lstat()
        destination_identity = (destination_info.st_dev, destination_info.st_ino)
        _write_new_file(destination / V2_SNAPSHOT_PATH, snapshot_bytes)
        for state, paths, revision in (
            ("before", before_paths, architecture_before_sha),
            ("after", after_paths, architecture_source_sha),
        ):
            for git_path in paths:
                relative = git_path.removeprefix("app/")
                content = _git_blob(root, revision, git_path)
                output_path = f"architecture/{state}/{relative}"
                _write_new_file(destination / output_path, content)

        for source_path, bundle_path, _role in FITNESS_INPUTS:
            _write_new_file(
                destination / bundle_path,
                _git_blob(root, architecture_source_sha, source_path),
            )
        capabilities = {
            "schema_version": 1,
            "inventory_version": "EVALUATOR_CAPABILITIES_V1",
            "evaluators": [
                {"id": "import_linter", "stages": ["ci"]},
                {"id": "pytest", "stages": ["test"]},
                {"id": "locust", "stages": ["test"]},
                {"id": "prometheus", "stages": ["runtime"]},
            ],
            "generic_candidate_templates": [],
            "prepared_reference_checkers_included": False,
        }
        _write_new_file(destination / CAPABILITIES_PATH, pretty_json_bytes(capabilities))
        if method_id == "P":
            traceability_source, traceability_bundle, _role = TRACEABILITY_INPUT
            _write_new_file(
                destination / traceability_bundle,
                _git_blob(root, architecture_source_sha, traceability_source),
            )
        for _source_id, path, _kind, content, _producer in source_blobs:
            _write_new_file(destination / path, content)

        for state, paths in (("before", before_paths), ("after", after_paths)):
            for git_path in paths:
                relative = git_path.removeprefix("app/")
                file_path = destination / "architecture" / state / relative
                files.append(_file_record(file_path, destination, f"architecture_{state}_source"))
        for path, role in _FIXED_ROLES.items():
            if (destination / path).is_file():
                files.append(_file_record(destination / path, destination, role))
        for _source_id, path, kind, _content, _producer in source_blobs:
            if path in _FIXED_ROLES:
                continue
            role = _role_for_source_kind(kind)
            files.append(_file_record(destination / path, destination, role))
        files.sort(key=lambda record: str(record["path"]))
        manifest: dict[str, Any] = {
            "schema_version": 2,
            "allowlist_version": V2_ALLOWLIST_VERSION,
            "profile_status": V2_PROFILE_STATUS,
            "method_id": method_id,
            "architecture_before_sha": architecture_before_sha,
            "architecture_source_sha": architecture_source_sha,
            "before_tree_sha": before_tree_sha,
            "after_tree_sha": after_tree_sha,
            "common_snapshot_sha256": sha256_bytes(snapshot_bytes),
            "files": files,
        }
        manifest["bundle_sha256"] = bundle_sha256(files)
        validate_payload("method_input_v2.schema.json", manifest)
        _write_new_file(destination / V2_MANIFEST_PATH, pretty_json_bytes(manifest))
        verify_method_bundle_v2(destination, expected_method_id=method_id)
        known_obligation_ids = _load_obligation_ids(destination / "fitness/obligations.yaml")
        validation = load_and_validate_snapshot(
            destination,
            manifest,
            known_obligation_ids=known_obligation_ids,
        )
        invalid_statuses = {
            validation.schema_status,
            validation.integrity_status,
            validation.authority_status,
            validation.fact_status,
            validation.completeness_status,
        }
        if ValidationStatus.INVALID in invalid_statuses:
            raise ContractValidationError(
                "V2 snapshot failed semantic validation: " + ", ".join(validation.reason_codes)
            )
        return manifest
    except Exception:
        if destination_identity is not None:
            _remove_owned_partial_bundle(destination, destination_identity)
        raise


def verify_method_bundle_v2(
    bundle_directory: Path,
    expected_method_id: MethodIdV2 | None = None,
) -> dict[str, Any]:
    """Verify V2 manifest, exact inventory, source bindings and clean projection."""
    try:
        if bundle_directory.is_symlink():
            raise ProtocolError("V2 bundle root must not be a symlink")
        root = bundle_directory.resolve(strict=True)
        manifest_path = root / V2_MANIFEST_PATH
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ProtocolError("V2 method bundle manifest must be a regular file")
        manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    except ProtocolError:
        raise
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError("V2 method bundle manifest is missing or invalid JSON") from error
    validate_payload("method_input_v2.schema.json", manifest)
    method_id = cast(MethodIdV2, manifest["method_id"])
    if expected_method_id is not None and method_id != expected_method_id:
        raise ProtocolError(f"Expected {expected_method_id} V2 bundle, found {method_id}")

    declared: dict[str, dict[str, Any]] = {}
    for entry in cast(list[dict[str, Any]], manifest["files"]):
        path = PurePosixPath(str(entry["path"]))
        _validate_bundle_path(path)
        relative = path.as_posix()
        _verify_v2_path_role(path, str(entry["role"]), method_id)
        if relative in declared:
            raise ProtocolError(f"Duplicate V2 bundle manifest path: {relative}")
        declared[relative] = entry

    actual_files: set[str] = set()
    for bundle_file in root.rglob("*"):
        if bundle_file.is_symlink():
            raise ProtocolError(f"V2 bundle contains a symlink: {bundle_file.relative_to(root)}")
        if bundle_file.is_file() and bundle_file != manifest_path:
            relative = bundle_file.relative_to(root).as_posix()
            _validate_bundle_path(PurePosixPath(relative))
            actual_files.add(relative)
    if actual_files != set(declared):
        raise ProtocolError(
            "V2 bundle inventory mismatch; "
            f"missing={sorted(set(declared) - actual_files)}, "
            f"unexpected={sorted(actual_files - set(declared))}"
        )

    for relative, entry in declared.items():
        content = (root / relative).read_bytes()
        if len(content) != entry["size_bytes"] or sha256_bytes(content) != entry["sha256"]:
            raise ProtocolError(f"V2 method input hash mismatch: {relative}")
        if any(marker in content.lower() for marker in _FORBIDDEN_CONTENT_MARKERS):
            raise ProtocolError(f"Forbidden oracle-field marker in V2 input: {relative}")
    if bundle_sha256(manifest["files"]) != manifest["bundle_sha256"]:
        raise ProtocolError("V2 method bundle hash does not match its manifest")

    required_roles = {
        "architecture_before_source",
        "architecture_after_source",
        "architecture_inventory",
        "structural_observations",
        "architecture_policy_snapshot",
        "fitness_configuration",
        "representation_catalog",
        "obligation_registry",
        "legacy_evaluator",
        "evaluator_capabilities",
        "policy_charter",
        "policy_registry",
        "completeness_evidence",
    }
    if method_id == "P":
        required_roles.add("traceability")
    observed_roles = {str(entry["role"]) for entry in manifest["files"]}
    if observed_roles != required_roles and not (
        observed_roles == required_roles | {"approval_evidence"}
    ):
        raise ProtocolError(
            f"V2 roles do not match {method_id} profile; "
            f"expected={sorted(required_roles)} plus optional approvals, "
            f"observed={sorted(observed_roles)}"
        )

    snapshot_path = root / V2_SNAPSHOT_PATH
    snapshot_bytes = snapshot_path.read_bytes()
    if sha256_bytes(snapshot_bytes) != manifest["common_snapshot_sha256"]:
        raise ProtocolError("COMMON_PROJECTION_MISMATCH: Snapshot digest differs from manifest")
    try:
        snapshot = json.loads(snapshot_bytes)
    except json.JSONDecodeError as error:
        raise ProtocolError("V2 Snapshot must be valid JSON") from error
    if not isinstance(snapshot, Mapping):
        raise ProtocolError("V2 Snapshot must be a JSON object")
    validate_snapshot_schema(snapshot)
    _verify_architecture_inventories(root, manifest, snapshot)
    _verify_structural_observation(root, manifest, snapshot)
    source_report = validate_source_references(snapshot, manifest, root)
    if source_report.status is not ValidationStatus.VALID:
        raise ProtocolError(
            "V2 source reference validation failed: " + ", ".join(source_report.reason_codes)
        )
    _verify_normalized_snapshot_projection(root, snapshot, snapshot_bytes)
    return manifest


def _project_source(source: Mapping[str, Any]) -> dict[str, Any]:
    if set(source) != _SOURCE_PROPERTY_NAMES:
        raise ContractValidationError("Snapshot source has unexpected fields")
    return {key: source[key] for key in ("id", "path", "sha256", "kind", "producer")}


def _project_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, Mapping):
        raise ContractValidationError("policy registry entry must be an object")
    if set(policy) - _POLICY_PROPERTY_NAMES or not _POLICY_REQUIRED_PROPERTIES.issubset(policy):
        raise ContractValidationError("policy entry has missing or unexpected fields")
    return {key: policy[key] for key in sorted(policy)}


def _project_claim(claim: Any) -> dict[str, Any]:
    if not isinstance(claim, Mapping):
        raise ContractValidationError("completeness claim must be an object")
    if set(claim) - _CLAIM_PROPERTY_NAMES or not _CLAIM_REQUIRED_PROPERTIES.issubset(claim):
        raise ContractValidationError("completeness claim has missing or unexpected fields")
    return {key: claim[key] for key in sorted(claim)}


def _fact(
    identifier: str,
    state: str,
    predicate: str,
    subject: str,
    scope: str,
    value: Any,
    epistemic_kind: str,
    source_ids: list[str],
    *,
    method_id: str | None = None,
) -> dict[str, Any]:
    fact: dict[str, Any] = {
        "id": identifier,
        "state": state,
        "predicate": predicate,
        "subject": subject,
        "scope": scope,
        "value": value,
        "epistemic_kind": epistemic_kind,
        "source_ids": sorted(source_ids),
    }
    if method_id is not None:
        fact["method_id"] = method_id
    return fact


def _facts_from_structural_manifest(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    modules = manifest.get("modules")
    if isinstance(modules, Mapping):
        for identifier, module in sorted(modules.items(), key=lambda item: str(item[0])):
            if not isinstance(module, Mapping):
                raise ContractValidationError("projected module must be an object")
            package = module.get("package")
            if not isinstance(package, str):
                raise ContractValidationError("projected module package must be a string")
            facts.append(
                _fact(
                    f"FV04_{_fact_suffix(str(identifier))}",
                    "after",
                    "component.capability_module",
                    package,
                    "application",
                    {"name": str(identifier), "package": package},
                    "DECLARED",
                    ["ARCH_OBS"],
                )
            )
    dependencies = manifest.get("preserved_cross_module_dependencies")
    if isinstance(dependencies, list):
        for index, dependency in enumerate(dependencies):
            if not isinstance(dependency, Mapping):
                raise ContractValidationError("projected dependency must be an object")
            facts.append(
                _fact(
                    f"FV05_DEPENDENCY_{index + 1:03d}",
                    "after",
                    "component.declared_cross_module_dependency",
                    str(dependency["from"]),
                    "application",
                    {"from": dependency["from"], "to": dependency["to"]},
                    "DECLARED",
                    ["ARCH_OBS"],
                )
            )
    shared = manifest.get("shared_infrastructure")
    if isinstance(shared, list):
        facts.append(
            _fact(
                "FV06_SHARED_INFRASTRUCTURE",
                "after",
                "component.shared_infrastructure",
                "application",
                "application",
                shared,
                "DECLARED",
                ["ARCH_OBS"],
            )
        )
    deployment = manifest.get("deployment")
    if isinstance(deployment, Mapping):
        deployment_predicates = (
            ("deployment_units", "deployment.unit_count_declared", "UNIT_COUNT"),
            ("application_processes", "deployment.process_count_declared", "PROCESS_COUNT"),
            (
                "database_instances",
                "deployment.database_instance_count_declared",
                "DATABASE_INSTANCE_COUNT",
            ),
            ("database_product", "deployment.database_product_declared", "DATABASE_PRODUCT"),
            (
                "internal_communication",
                "communication.internal_mode_declared",
                "INTERNAL_COMMUNICATION",
            ),
            ("message_broker", "communication.broker_declared", "MESSAGE_BROKER"),
        )
        for source_key, predicate, suffix in deployment_predicates:
            if source_key not in deployment:
                continue
            facts.append(
                _fact(
                    f"FV_{suffix}",
                    "after",
                    predicate,
                    "application",
                    "application",
                    deployment[source_key],
                    "DECLARED",
                    ["ARCH_OBS"],
                )
            )
    return facts


def _project_structural_manifest(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Select and type-check only facts authorized by the current FV registry."""
    result: dict[str, Any] = {}
    deployment = raw.get("deployment")
    if deployment is not None:
        if not isinstance(deployment, Mapping):
            raise ContractValidationError("deployment projection must be an object")
        allowed = {
            "deployment_units",
            "application_processes",
            "database_instances",
            "database_product",
            "internal_communication",
            "message_broker",
        }
        projected: dict[str, Any] = {}
        for key in allowed.intersection(deployment):
            value = deployment[key]
            if key in {"deployment_units", "application_processes", "database_instances"}:
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ContractValidationError(f"deployment.{key} must be a nonnegative integer")
            elif not isinstance(value, str) or not value.strip():
                raise ContractValidationError(f"deployment.{key} must be a non-empty string")
            projected[key] = value
        result["deployment"] = {key: projected[key] for key in sorted(projected)}

    shared = raw.get("shared_infrastructure")
    if shared is not None:
        if not isinstance(shared, list) or any(
            not isinstance(item, str) or not _is_python_module(item) for item in shared
        ):
            raise ContractValidationError("shared_infrastructure must contain Python module names")
        if len(shared) != len(set(shared)):
            raise ContractValidationError("shared_infrastructure contains duplicates")
        result["shared_infrastructure"] = sorted(shared)

    modules = raw.get("modules")
    if modules is not None:
        if not isinstance(modules, Mapping):
            raise ContractValidationError("modules projection must be an object")
        projected_modules: dict[str, dict[str, str]] = {}
        for name, value in modules.items():
            if not isinstance(name, str) or not _is_identifier_path(name):
                raise ContractValidationError("module names must be identifiers")
            if not isinstance(value, Mapping):
                raise ContractValidationError("module projection entries must be objects")
            package = value.get("package")
            if not isinstance(package, str) or not _is_python_module(package):
                raise ContractValidationError("module package must be a Python module name")
            projected_modules[name] = {"package": package}
        result["modules"] = {name: projected_modules[name] for name in sorted(projected_modules)}

    dependencies = raw.get("preserved_cross_module_dependencies")
    if dependencies is not None:
        if not isinstance(dependencies, list):
            raise ContractValidationError("preserved dependencies must be an array")
        projected_dependencies: list[dict[str, str]] = []
        for dependency in dependencies:
            if not isinstance(dependency, Mapping):
                raise ContractValidationError("preserved dependency must be an object")
            source = dependency.get("from")
            target = dependency.get("to")
            if (
                not isinstance(source, str)
                or not _is_python_module(source)
                or not isinstance(target, str)
                or not _is_python_module(target)
            ):
                raise ContractValidationError("preserved dependency endpoints must be module names")
            projected_dependencies.append({"from": source, "to": target})
        projected_dependencies.sort(key=lambda item: (item["from"], item["to"]))
        result["preserved_cross_module_dependencies"] = projected_dependencies
    return result


def _policy_sidecar_blobs(
    repository: Path,
    revision: str,
    charter: Mapping[str, Any],
    policies: list[Any],
) -> list[tuple[str, str, str, bytes, str]]:
    result: list[tuple[str, str, str, bytes, str]] = []
    evidence_ids = charter.get("evidence_source_ids")
    precedence = charter.get("precedence", [])
    if not isinstance(evidence_ids, list) or not evidence_ids:
        raise ContractValidationError("MISSING_AUTHORITY: Charter must name evidence sources")
    if not isinstance(precedence, list):
        raise ContractValidationError("Charter precedence must be an array")
    referenced_evidence = list(evidence_ids)
    for entry in precedence:
        if not isinstance(entry, Mapping):
            raise ContractValidationError("Charter precedence entries must be objects")
        evidence_refs = entry.get("evidence_source_ids")
        if not isinstance(evidence_refs, list):
            raise ContractValidationError("Charter precedence evidence references must be arrays")
        referenced_evidence.extend(evidence_refs)
    for source_id in sorted(_validated_source_ids(referenced_evidence)):
        path = f"{EVIDENCE_PREFIX}{source_id}.json"
        content = _git_blob(repository, revision, path)
        result.append((source_id, path, "EVIDENCE", content, "pinned_authority_evidence"))
    for policy in policies:
        if not isinstance(policy, Mapping):
            raise ContractValidationError("policy registry entry must be an object")
        approval_id = policy.get("approval_source_id")
        if approval_id is None:
            if policy.get("normative_status") != "DRAFT":
                raise ContractValidationError("MISSING_AUTHORITY: non-draft policy needs approval")
            continue
        if not isinstance(approval_id, str) or not _is_source_id(approval_id):
            raise ContractValidationError("policy approval source id is invalid")
        path = f"{APPROVALS_PREFIX}{approval_id}.json"
        content = _git_blob(repository, revision, path)
        result.append((approval_id, path, "APPROVAL", content, "pinned_policy_approval"))
    return result


def _verify_architecture_inventories(
    root: Path, manifest: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> None:
    architecture = snapshot.get("architecture")
    if not isinstance(architecture, Mapping):
        raise ProtocolError("V2 Snapshot architecture is missing")
    expected = {
        "before_commit": manifest.get("architecture_before_sha"),
        "after_commit": manifest.get("architecture_source_sha"),
        "before_tree": manifest.get("before_tree_sha"),
        "after_tree": manifest.get("after_tree_sha"),
    }
    if any(architecture.get(key) != value for key, value in expected.items()):
        raise ProtocolError("VERSION_MISMATCH: manifest and Snapshot revisions differ")
    for path, state, commit_key, tree_key, role in (
        (
            BEFORE_INVENTORY_PATH,
            "before",
            "before_commit",
            "before_tree",
            "architecture_before_source",
        ),
        (AFTER_INVENTORY_PATH, "after", "after_commit", "after_tree", "architecture_after_source"),
    ):
        try:
            inventory = json.loads((root / path).read_bytes())
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ProtocolError(f"Architecture inventory is missing or invalid: {path}") from error
        if not isinstance(inventory, Mapping) or set(inventory) != {
            "schema_version",
            "state",
            "commit_sha",
            "tree_sha",
            "files",
        }:
            raise ProtocolError(f"Architecture inventory has unexpected fields: {path}")
        if (
            inventory.get("schema_version") != "1.1"
            or inventory.get("state") != state
            or inventory.get("commit_sha") != architecture.get(commit_key)
            or inventory.get("tree_sha") != architecture.get(tree_key)
        ):
            raise ProtocolError(f"VERSION_MISMATCH: architecture inventory differs: {path}")
        listed_files = inventory.get("files")
        if not isinstance(listed_files, list) or any(
            not isinstance(item, Mapping)
            or set(item) != {"path", "git_blob_sha1"}
            or not isinstance(item.get("path"), str)
            or not isinstance(item.get("git_blob_sha1"), str)
            or re.fullmatch(r"[a-f0-9]{40}", str(item.get("git_blob_sha1"))) is None
            for item in listed_files
        ):
            raise ProtocolError(f"Architecture inventory file list is malformed: {path}")
        listed_paths = [str(item["path"]) for item in listed_files]
        if listed_paths != sorted(set(listed_paths)):
            raise ProtocolError(
                f"Architecture inventory file list is not unique and sorted: {path}"
            )
        observed_files: dict[str, str] = {}
        for item in manifest["files"]:
            if not isinstance(item, Mapping) or item.get("role") != role:
                continue
            bundled_path = PurePosixPath(str(item.get("path", "")))
            try:
                relative_path = bundled_path.relative_to(PurePosixPath(f"architecture/{state}"))
            except ValueError as error:
                raise ProtocolError(
                    f"Architecture file role has a mismatched path: {path}"
                ) from error
            git_path = f"app/{relative_path.as_posix()}"
            try:
                content = (root / bundled_path).read_bytes()
            except OSError as error:
                raise ProtocolError(
                    f"Architecture source file is missing: {bundled_path}"
                ) from error
            observed_files[git_path] = _git_blob_object_sha1(content)
        if listed_paths != sorted(observed_files):
            raise ProtocolError(f"Architecture inventory does not match bundled source: {state}")
        for item in listed_files:
            git_path = str(item["path"])
            if item["git_blob_sha1"] != observed_files[git_path]:
                raise ProtocolError(f"Git blob mismatch for architecture source: {git_path}")


def _verify_structural_observation(
    root: Path, manifest: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> None:
    try:
        payload = json.loads((root / STRUCTURAL_SOURCE_PATH).read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError("Structural observation is missing or invalid JSON") from error
    if not isinstance(payload, Mapping) or set(payload) != {
        "schema_version",
        "source_state",
        "source_commit_sha",
        "source_tree_sha",
        "target_structural_manifest",
    }:
        raise ProtocolError("Structural observation has unexpected fields")
    if payload.get("schema_version") != "1.1" or payload.get("source_state") != "after":
        raise ProtocolError("Structural observation version or source state is invalid")
    architecture = snapshot.get("architecture")
    if not isinstance(architecture, Mapping) or (
        payload.get("source_commit_sha") != manifest.get("architecture_source_sha")
        or payload.get("source_commit_sha") != architecture.get("after_commit")
        or payload.get("source_tree_sha") != manifest.get("after_tree_sha")
        or payload.get("source_tree_sha") != architecture.get("after_tree")
    ):
        raise ProtocolError("VERSION_MISMATCH: structural observation source pin differs")
    structural = payload.get("target_structural_manifest")
    if not isinstance(structural, Mapping) or set(structural) - {
        "deployment",
        "shared_infrastructure",
        "modules",
        "preserved_cross_module_dependencies",
    }:
        raise ProtocolError("Structural observation projection has unexpected fields")
    if isinstance(structural.get("modules"), Mapping):
        for item in structural["modules"].values():
            if not isinstance(item, Mapping) or set(item) != {"package"}:
                raise ProtocolError("Structural module projection must contain package only")
    deployment = structural.get("deployment")
    if deployment is not None:
        allowed_deployment_keys = {
            "deployment_units",
            "application_processes",
            "database_instances",
            "database_product",
            "internal_communication",
            "message_broker",
        }
        if not isinstance(deployment, Mapping) or set(deployment) - allowed_deployment_keys:
            raise ProtocolError("Structural deployment projection has unexpected fields")
        for key, value in deployment.items():
            if key in {"deployment_units", "application_processes", "database_instances"}:
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ProtocolError("Structural deployment count is invalid")
            elif not isinstance(value, str) or not value.strip():
                raise ProtocolError("Structural deployment string is invalid")
    shared = structural.get("shared_infrastructure")
    if shared is not None:
        if (
            not isinstance(shared, list)
            or any(not isinstance(item, str) for item in shared)
            or shared != sorted(set(shared))
            or any(not _is_python_module(item) for item in shared)
        ):
            raise ProtocolError("Structural shared infrastructure projection is invalid")
    dependencies = structural.get("preserved_cross_module_dependencies", [])
    if not isinstance(dependencies, list) or any(
        not isinstance(item, Mapping) or set(item) != {"from", "to"} for item in dependencies
    ):
        raise ProtocolError("Structural dependencies must contain only from and to")
    if "governance" in structural or "scenario_id" in structural:
        raise ProtocolError("Structural observation contains a forbidden source field")


def _verify_normalized_snapshot_projection(
    root: Path,
    snapshot: Mapping[str, Any],
    snapshot_bytes: bytes,
    *,
    allow_snapshot_v1_2: bool = False,
) -> None:
    try:
        before_inventory = json.loads((root / BEFORE_INVENTORY_PATH).read_bytes())
        after_inventory = json.loads((root / AFTER_INVENTORY_PATH).read_bytes())
        observation = json.loads((root / STRUCTURAL_SOURCE_PATH).read_bytes())
        registry_artifact = json.loads((root / REGISTRY_PATH).read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError("V2 normalized projection sources are missing or invalid") from error
    if not all(
        isinstance(payload, Mapping)
        for payload in (before_inventory, after_inventory, observation, registry_artifact)
    ):
        raise ProtocolError("V2 normalized projection source must be a JSON object")
    structural_value = observation.get("target_structural_manifest")
    if not isinstance(structural_value, Mapping):
        raise ProtocolError("V2 structural projection source is malformed")
    structural = _project_structural_manifest(structural_value)
    architecture = snapshot.get("architecture")
    sources = snapshot.get("sources")
    claims = snapshot.get("completeness_claims")
    before_files = before_inventory.get("files")
    after_files = after_inventory.get("files")
    if (
        not isinstance(architecture, Mapping)
        or not isinstance(sources, list)
        or not isinstance(claims, list)
        or not isinstance(before_files, list)
        or not isinstance(after_files, list)
        or any(
            not isinstance(entry, Mapping)
            or set(entry) != {"path", "git_blob_sha1"}
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("git_blob_sha1"), str)
            for entry in [*before_files, *after_files]
        )
    ):
        raise ProtocolError("V2 Snapshot projection inputs are malformed")
    before_paths = [str(entry["path"]) for entry in before_files]
    after_paths = [str(entry["path"]) for entry in after_files]
    normalized = build_normalized_snapshot(
        architecture=architecture,
        before_module_names=_module_names_from_git_paths(before_paths),
        after_module_names=_module_names_from_git_paths(after_paths),
        structural_manifest=structural,
        sources=sources,
        registry_artifact=registry_artifact,
        completeness_claims=claims,
        allow_snapshot_v1_2=allow_snapshot_v1_2,
    )
    if pretty_json_bytes(normalized) != snapshot_bytes:
        raise ProtocolError("COMMON_PROJECTION_MISMATCH: Snapshot differs from typed projection")


def _verify_v2_path_role(path: PurePosixPath, role: str, method_id: MethodIdV2) -> None:
    relative = path.as_posix()
    fixed_role = _FIXED_ROLES.get(relative)
    if fixed_role == role:
        if role == "traceability" and method_id != "P":
            raise ProtocolError("Only P may receive the traceability input")
        return
    if relative.startswith("architecture/before/") and relative.endswith(".py"):
        expected = "architecture_before_source"
    elif relative.startswith("architecture/after/") and relative.endswith(".py"):
        expected = "architecture_after_source"
    elif relative.startswith(APPROVALS_PREFIX) and relative.endswith(".json"):
        expected = "approval_evidence"
    elif relative.startswith(EVIDENCE_PREFIX) and relative.endswith(".json"):
        expected = "completeness_evidence"
    else:
        expected = ""
    if expected != role:
        raise ProtocolError(f"Path and role are not in the V2 allowlist: {relative} ({role})")


def _validate_bundle_path(path: PurePosixPath) -> None:
    forbidden_parts = {
        ".git",
        "experiments",
        "ground_truth",
        "groundtruth",
        "oracle",
        "reference",
        "scorer",
        "scenario",
        "results",
        "acceptance",
    }
    lowered_parts = {part.lower() for part in path.parts}
    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\\" in path.as_posix()
        or bool(lowered_parts.intersection(forbidden_parts))
    ):
        raise ProtocolError(f"Forbidden or unsafe V2 bundle path: {path.as_posix()}")


def _git_app_python_paths(repository: Path, revision: str) -> list[str]:
    output = _git_bytes(repository, "ls-tree", "-rz", "--full-tree", revision, "--", "app")
    paths: list[str] = []
    for record in output.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, _object_id = metadata.decode("ascii").split(" ", 2)
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise ProtocolError("Git app tree listing is malformed") from error
        if not path.endswith(".py"):
            continue
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise ProtocolError(f"Architecture source is not a regular Git blob: {path}")
        relative = PurePosixPath(path)
        if not relative.parts or relative.parts[0] != "app" or ".." in relative.parts:
            raise ProtocolError(f"Unexpected architecture source path: {path}")
        paths.append(relative.as_posix())
    if not paths:
        raise ProtocolError(
            f"No Python application files found at architecture revision {revision}"
        )
    return sorted(paths)


def _git_inventory_file_records(
    repository: Path, revision: str, paths: Sequence[str]
) -> list[dict[str, str]]:
    output = _git_bytes(repository, "ls-tree", "-rz", "--full-tree", revision, "--", "app")
    blob_ids: dict[str, str] = {}
    for record in output.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ", 2)
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise ProtocolError("Git app tree listing is malformed") from error
        if path in paths:
            if object_type != "blob" or mode not in {"100644", "100755"}:
                raise ProtocolError(f"Architecture source is not a regular Git blob: {path}")
            if re.fullmatch(r"[a-f0-9]{40}", object_id) is None:
                raise ProtocolError(f"Git blob object id is malformed: {path}")
            blob_ids[path] = object_id
    if set(blob_ids) != set(paths):
        raise ProtocolError("Git app tree listing does not match the requested Python inventory")
    return [{"path": path, "git_blob_sha1": blob_ids[path]} for path in sorted(paths)]


def _module_names_from_git_paths(paths: Sequence[str]) -> list[str]:
    modules: set[str] = set()
    for path in paths:
        relative = PurePosixPath(path)
        if not relative.parts or relative.parts[0] != "app" or relative.suffix != ".py":
            raise ProtocolError(f"Malformed committed Python path: {path}")
        module_parts = [*relative.parts[1:-1], relative.stem]
        if module_parts[-1] == "__init__":
            module_parts.pop()
        name = "app" if not module_parts else f"app.{'.'.join(module_parts)}"
        if not _is_python_module(name):
            raise ProtocolError(f"Malformed Python module identity: {name}")
        modules.add(name)
    return sorted(modules)


def _normalized_module_names(values: Sequence[str]) -> list[str]:
    if any(not isinstance(value, str) or not _is_python_module(value) for value in values):
        raise ContractValidationError("module inventories must contain Python module names")
    if len(values) != len(set(values)):
        raise ContractValidationError("module inventories must not contain duplicates")
    return sorted(values)


def _is_python_module(value: str) -> bool:
    parts = value.split(".")
    return parts[0] == "app" and all(part.isidentifier() for part in parts)


def _is_identifier_path(value: str) -> bool:
    return bool(value) and all(part.isidentifier() for part in value.split("."))


def _fact_suffix(value: str) -> str:
    suffix = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    if not suffix or not suffix[0].isalpha():
        raise ContractValidationError("module identifier cannot form a stable fact id")
    return suffix


def _validated_source_ids(values: Sequence[Any]) -> set[str]:
    result: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not _is_source_id(value):
            raise ContractValidationError("policy source id is invalid")
        if value in result:
            raise ContractValidationError("policy source ids must be unique")
        result.add(value)
    return result


def _is_source_id(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}", value) is not None


def _decode_json_object(content: bytes, description: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractValidationError(f"{description} must be valid UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise ContractValidationError(f"{description} must be a JSON object")
    return payload


def _role_for_source_kind(kind: str) -> str:
    roles = {
        "ARCHITECTURE_SOURCE": "architecture_inventory",
        "STRUCTURAL_OBSERVATION": "structural_observations",
        "POLICY_CHARTER": "policy_charter",
        "POLICY_REGISTRY": "policy_registry",
        "EVIDENCE": "completeness_evidence",
        "APPROVAL": "approval_evidence",
    }
    try:
        return roles[kind]
    except KeyError as error:
        raise ContractValidationError(f"Unsupported source kind: {kind}") from error


def _load_obligation_ids(path: Path) -> set[str]:
    try:
        payload = yaml.safe_load(path.read_bytes())
    except (OSError, yaml.YAMLError) as error:
        raise ContractValidationError("Obligation registry is missing or invalid YAML") from error
    if not isinstance(payload, Mapping) or not isinstance(payload.get("obligations"), list):
        raise ContractValidationError("Obligation registry has no obligations array")
    identifiers: set[str] = set()
    for obligation in payload["obligations"]:
        if not isinstance(obligation, Mapping) or not isinstance(obligation.get("id"), str):
            raise ContractValidationError("Obligation registry contains a malformed identifier")
        identifiers.add(str(obligation["id"]))
    return identifiers


def _remove_owned_partial_bundle(destination: Path, identity: tuple[int, int]) -> None:
    """Remove only the new directory inode created by this exporter.

    Walk without following symlinks and refuse cleanup if the output path no
    longer names the directory this call created.
    """
    try:
        current = destination.lstat()
    except OSError:
        return
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISDIR(current.st_mode)
        or (current.st_dev, current.st_ino) != identity
    ):
        return
    for current_root, directory_names, file_names in os.walk(
        destination, topdown=False, followlinks=False
    ):
        current_path = Path(current_root)
        for name in file_names:
            child = current_path / name
            try:
                if child.is_symlink() or child.is_file():
                    child.unlink()
            except OSError:
                continue
        for name in directory_names:
            child = current_path / name
            try:
                if child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            except OSError:
                continue
    try:
        destination.rmdir()
    except OSError:
        pass


def _file_record(path: Path, bundle_root: Path, role: str) -> dict[str, Any]:
    relative = path.relative_to(bundle_root).as_posix()
    _validate_bundle_path(PurePosixPath(relative))
    content = path.read_bytes()
    return {
        "path": relative,
        "role": role,
        "size_bytes": len(content),
        "sha256": sha256_bytes(content),
    }


def _write_new_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(content)


def _validate_repository_root(repository: Path) -> None:
    top_level = Path(_git_text(repository, "rev-parse", "--show-toplevel").strip()).resolve()
    if top_level != repository:
        raise ProtocolError(f"Repository path must be the Git root: {top_level}")


def _validate_commit_id(revision: str, field_name: str) -> None:
    if re.fullmatch(r"[a-f0-9]{40}", revision) is None:
        raise ProtocolError(f"{field_name} must be a full lowercase Git commit SHA")


def _git_blob_object_sha1(content: bytes) -> str:
    git_object = b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    return hashlib.sha1(git_object, usedforsecurity=False).hexdigest()


def _git_text(repository: Path, *arguments: str) -> str:
    return _git_run(repository, arguments).decode("utf-8").strip()


def _git_bytes(repository: Path, *arguments: str) -> bytes:
    return _git_run(repository, arguments)


def _git_run(repository: Path, arguments: Sequence[str]) -> bytes:
    executable = shutil.which("git")
    if executable is None:
        raise ProtocolError("Git executable is unavailable")
    try:
        return subprocess.run(  # noqa: S603  # nosec B603 - fixed Git executable and argv
            [executable, "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise ProtocolError(f"Git command failed: git {' '.join(arguments)}") from error


def _git_blob(repository: Path, revision: str, relative_path: str) -> bytes:
    pure_path = PurePosixPath(relative_path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ProtocolError(f"Unsafe Git path: {relative_path}")
    entry = _git_text(repository, "ls-tree", revision, "--", relative_path)
    if not entry or not entry.startswith(("100644 blob ", "100755 blob ")):
        raise ProtocolError(
            f"Allowlisted Git path is missing or not a regular file: {relative_path}"
        )
    return _git_bytes(repository, "show", f"{revision}:{relative_path}")


__all__ = [
    "MethodIdV2",
    "V2_ALLOWLIST_VERSION",
    "V2_PROFILE_STATUS",
    "build_normalized_snapshot",
    "export_method_inputs_v2",
    "verify_method_bundle_v2",
]
