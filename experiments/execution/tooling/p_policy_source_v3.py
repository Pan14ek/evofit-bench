"""Versioned V3 candidate exporter with policy artifacts pinned separately from architecture."""

from __future__ import annotations

import json
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Literal, cast

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import bundle_sha256, pretty_json_bytes, sha256_bytes
from experiments.execution.tooling.inputs import FITNESS_INPUTS, TRACEABILITY_INPUT
from experiments.execution.tooling.p_applicability import (
    CompiledRuleset,
    load_and_validate_ruleset,
)
from experiments.execution.tooling.p_input_export_v2 import (
    _FIXED_ROLES,
    _FORBIDDEN_CONTENT_MARKERS,
    _REGISTRY_PROPERTY_NAMES,
    AFTER_INVENTORY_PATH,
    BEFORE_INVENTORY_PATH,
    CAPABILITIES_PATH,
    CHARTER_PATH,
    REGISTRY_PATH,
    STRUCTURAL_MANIFEST_PATH,
    STRUCTURAL_SOURCE_PATH,
    V2_SNAPSHOT_PATH,
    _file_record,
    _git_app_python_paths,
    _git_blob,
    _git_inventory_file_records,
    _git_text,
    _module_names_from_git_paths,
    _project_structural_manifest,
    _remove_owned_partial_bundle,
    _validate_bundle_path,
    _validate_commit_id,
    _validate_repository_root,
    _verify_architecture_inventories,
    _verify_normalized_snapshot_projection,
    _verify_structural_observation,
    _write_new_file,
    build_normalized_snapshot,
)
from experiments.execution.tooling.p_input_validation import (
    _SOURCE_KIND_TO_ROLE,
    P_INPUT_SNAPSHOT_PATH,
    ValidationStatus,
    load_and_validate_snapshot,
    load_fact_vocabulary,
    validate_snapshot_schema,
    validate_source_references,
)

PolicyMethodIdV3 = Literal["B1", "P"]
POLICY_SOURCE_SCHEMA = "policy_source_v3.schema.json"
METHOD_INPUT_SCHEMA = "method_input_v3_candidate.schema.json"
POLICY_SOURCE_MANIFEST = "policy_source_v3.json"
METHOD_INPUT_MANIFEST = "method_input_v3.json"
POLICY_SOURCE_PROFILE = "P_POLICY_SOURCE_V3_CANDIDATE"
METHOD_INPUT_PROFILE = "DA01_METHOD_INPUTS_V3_CANDIDATE"
V3_PROFILE_STATUS = "DEVELOPMENT_UNFROZEN"
RULESET_PATH = "policy/applicability_ruleset_v1.json"
POLICY_CLAIMS_PATH = "fitness/policy/completeness-claims.json"
METHOD_POLICY_MANIFEST_PATH = "policy/policy_source_v3.json"
_POLICY_FILE_ROLES = {
    "policy_charter",
    "policy_registry",
    "approval_evidence",
    "completeness_evidence",
    "applicability_ruleset",
    "policy_completeness_claims",
}
_METHOD_EXTRA_ROLES = {
    "applicability_ruleset",
    "policy_completeness_claims",
    "policy_source_manifest",
}
_REGISTRY_V12_PROPERTY_NAMES = (_REGISTRY_PROPERTY_NAMES - {"closure_claim_id"}) | {
    "closure_claim_ids"
}
_FORBIDDEN_POLICY_MARKERS = (
    b"expected_operations",
    b"ground_truth",
    b"groundtruth",
    b"scenario_id",
    b"expected_status",
    b"expected_operation",
    b"expected_applicability",
    b"da01_positive",
    b"next_scenario",
    b"reference_target",
    b"private_checker",
    b"scorer",
)
_SAFE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True)
class PolicySourceBundleV3:
    """Verified local policy-only bundle; paths and bytes remain pinned by its manifest."""

    root: Path
    manifest: Mapping[str, Any]
    registry: Mapping[str, Any]
    charter: Mapping[str, Any]
    completeness_claims: tuple[Mapping[str, Any], ...]
    ruleset: CompiledRuleset
    files: Mapping[str, bytes]


def package_policy_source_v3(
    source_directory: Path,
    output_directory: Path,
    policy_source_revision: str,
) -> dict[str, Any]:
    """Package only the explicitly allowlisted governance inputs into a pinned bundle."""
    source = source_directory.resolve(strict=True)
    destination = output_directory.resolve()
    if destination.exists():
        raise ProtocolError(f"Policy bundle output already exists: {destination}")
    if destination.is_relative_to(source):
        raise ProtocolError("Policy source output must be outside its source directory")
    if not policy_source_revision or len(policy_source_revision) > 128:
        raise ContractValidationError("POLICY_SOURCE_INVALID: revision label is invalid")
    expected_paths = _expected_policy_paths(source)
    observed_paths: set[str] = set()
    for item in source.rglob("*"):
        if item.is_symlink():
            raise ProtocolError(f"Policy source contains a symlink: {item.relative_to(source)}")
        if item.is_file():
            observed_paths.add(item.relative_to(source).as_posix())
    if observed_paths != set(expected_paths):
        raise ProtocolError(
            "Policy source allowlist mismatch; "
            f"missing={sorted(set(expected_paths) - observed_paths)}, "
            f"unexpected={sorted(observed_paths - set(expected_paths))}"
        )
    records: list[dict[str, Any]] = []
    try:
        destination.mkdir(parents=True)
        identity_info = destination.lstat()
        identity = (identity_info.st_dev, identity_info.st_ino)
    except OSError as error:
        raise ProtocolError("Unable to create policy source bundle") from error
    try:
        for relative, role in sorted(expected_paths.items()):
            content = (source / relative).read_bytes()
            _reject_oracle_fields(content, relative)
            _write_new_file(destination / relative, content)
            record = _policy_file_record(destination / relative, destination, role)
            records.append(record)
        records.sort(key=lambda item: str(item["path"]))
        manifest = {
            "schema_version": 3,
            "profile_id": POLICY_SOURCE_PROFILE,
            "policy_source_revision": policy_source_revision,
            "files": records,
            "policy_bundle_sha256": bundle_sha256(records),
        }
        validate_payload(POLICY_SOURCE_SCHEMA, manifest)
        _write_new_file(destination / POLICY_SOURCE_MANIFEST, pretty_json_bytes(manifest))
        verify_policy_source_bundle_v3(destination)
        return manifest
    except Exception:
        _remove_owned_partial_bundle(destination, identity)
        raise


def verify_policy_source_bundle_v3(bundle_directory: Path) -> dict[str, Any]:
    """Verify exact inventory, file hashes, version, allowlist and typed AR-DSL."""
    root, manifest = _read_manifest(bundle_directory, POLICY_SOURCE_MANIFEST, POLICY_SOURCE_SCHEMA)
    declared = _records_by_path(manifest.get("files"), root)
    expected_roles = _expected_policy_paths(root)
    if set(declared) != set(expected_roles):
        raise ProtocolError("Policy source bundle files do not match the versioned allowlist")
    for relative, record in declared.items():
        if record.get("role") != expected_roles[relative]:
            raise ProtocolError(f"Policy source path/role mismatch: {relative}")
        content = (root / relative).read_bytes()
        _reject_oracle_fields(content, relative)
    _verify_inventory(root, POLICY_SOURCE_MANIFEST, declared)
    if bundle_sha256(list(cast(list[dict[str, Any]], manifest["files"]))) != manifest.get(
        "policy_bundle_sha256"
    ):
        raise ProtocolError("Policy bundle digest does not match its manifest")
    registry = _read_json_object(root / REGISTRY_PATH, "policy registry")
    _read_json_object(root / CHARTER_PATH, "policy charter")
    _validate_registry_source(registry)
    if registry.get("authority_charter_source_id") != "CHARTER":
        raise ContractValidationError("POLICY_SOURCE_INVALID: registry must reference CHARTER")
    if registry.get("policies") is None or not isinstance(registry.get("policies"), list):
        raise ContractValidationError("POLICY_SOURCE_INVALID: registry policies must be an array")
    claims = _read_json_array(root / POLICY_CLAIMS_PATH, "policy completeness claims")
    for claim in claims:
        if not isinstance(claim, Mapping):
            raise ContractValidationError(
                "POLICY_SOURCE_INVALID: completeness claim must be an object"
            )
    closure_claim_ids = _registry_closure_claim_ids(registry)
    if closure_claim_ids:
        claims_by_id: dict[str, list[Mapping[str, Any]]] = {}
        for claim in claims:
            if isinstance(claim, Mapping) and isinstance(claim.get("id"), str):
                claims_by_id.setdefault(str(claim["id"]), []).append(claim)
        if any(
            len(claims_by_id.get(claim_id, [])) != 1
            or claims_by_id[claim_id][0].get("kind") != "AUTHORITATIVE_POLICY_REGISTRY"
            for claim_id in closure_claim_ids
        ):
            raise ContractValidationError(
                "POLICY_SOURCE_INVALID: registry closure references must bind "
                "unique registry claims"
            )
    load_and_validate_ruleset(
        root / RULESET_PATH,
        load_fact_vocabulary(),
    )
    return manifest


def load_policy_source_bundle_v3(bundle_directory: Path) -> PolicySourceBundleV3:
    """Return parsed policy content after independent source bundle verification."""
    manifest = verify_policy_source_bundle_v3(bundle_directory)
    root = bundle_directory.resolve(strict=True)
    registry = _read_json_object(root / REGISTRY_PATH, "policy registry")
    charter = _read_json_object(root / CHARTER_PATH, "policy charter")
    claims_value = _read_json_array(root / POLICY_CLAIMS_PATH, "policy completeness claims")
    claims = tuple(cast(Mapping[str, Any], item) for item in claims_value)
    ruleset = load_and_validate_ruleset(root / RULESET_PATH, load_fact_vocabulary())
    files = {
        str(record["path"]): (root / str(record["path"])).read_bytes()
        for record in cast(list[dict[str, Any]], manifest["files"])
    }
    return PolicySourceBundleV3(
        root=root,
        manifest=manifest,
        registry=registry,
        charter=charter,
        completeness_claims=claims,
        ruleset=ruleset,
        files=MappingProxyType(files),
    )


def _expected_policy_paths(source: Path) -> dict[str, str]:
    base = {
        CHARTER_PATH: "policy_charter",
        REGISTRY_PATH: "policy_registry",
        RULESET_PATH: "applicability_ruleset",
        POLICY_CLAIMS_PATH: "policy_completeness_claims",
    }
    charter = _read_json_object(source / CHARTER_PATH, "policy charter")
    registry = _read_json_object(source / REGISTRY_PATH, "policy registry")
    claims = _read_json_array(source / POLICY_CLAIMS_PATH, "policy completeness claims")
    referenced_evidence: set[str] = set()
    for entry in charter.get("evidence_source_ids", []):
        referenced_evidence.add(_safe_identifier(entry))
    for precedence in charter.get("precedence", []):
        if isinstance(precedence, Mapping):
            referenced_evidence.update(
                _safe_identifier(item) for item in precedence.get("evidence_source_ids", [])
            )
    for claim in claims:
        if isinstance(claim, Mapping):
            referenced_evidence.update(
                _safe_identifier(item) for item in claim.get("evidence_source_ids", [])
            )
    policies = registry.get("policies", [])
    if not isinstance(policies, list):
        raise ContractValidationError("POLICY_SOURCE_INVALID: registry policies must be an array")
    approvals: set[str] = set()
    for policy in policies:
        if not isinstance(policy, Mapping):
            raise ContractValidationError(
                "POLICY_SOURCE_INVALID: registry policy must be an object"
            )
        approval_id = policy.get("approval_source_id")
        if approval_id is not None:
            approvals.add(_safe_identifier(approval_id))
    for identifier in approvals:
        base[f"fitness/policy/approvals/{identifier}.json"] = "approval_evidence"
    for identifier in referenced_evidence:
        base[f"fitness/policy/evidence/{identifier}.json"] = "completeness_evidence"
    return base


def _safe_identifier(value: Any) -> str:
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise ContractValidationError("POLICY_SOURCE_INVALID: source identifier is unsafe")
    return value


def _read_manifest(
    bundle_directory: Path, filename: str, schema_name: str
) -> tuple[Path, dict[str, Any]]:
    if bundle_directory.is_symlink():
        raise ProtocolError("Policy/method bundle root must not be a symlink")
    try:
        root = bundle_directory.resolve(strict=True)
        manifest_path = root / filename
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise OSError("manifest is missing")
        manifest = json.loads(manifest_path.read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError(f"{filename} is missing or invalid JSON") from error
    if not isinstance(manifest, dict):
        raise ProtocolError(f"{filename} must contain an object")
    validate_payload(schema_name, manifest)
    return root, manifest


def _records_by_path(records_value: Any, root: Path) -> dict[str, Mapping[str, Any]]:
    if not isinstance(records_value, list):
        raise ProtocolError("Bundle manifest files must be an array")
    records: dict[str, Mapping[str, Any]] = {}
    for record in records_value:
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            raise ProtocolError("Bundle file record is malformed")
        path = PurePosixPath(str(record["path"]))
        _validate_bundle_path(path)
        relative = path.as_posix()
        if relative in records:
            raise ProtocolError(f"Duplicate bundle path: {relative}")
        file_path = root.joinpath(*path.parts)
        if _contains_symlink(file_path, root):
            raise ProtocolError(f"Bundle path traverses a symlink: {relative}")
        try:
            content = file_path.read_bytes()
        except OSError as error:
            raise ProtocolError(f"Bundle file is missing: {relative}") from error
        if len(content) != record.get("size_bytes") or sha256_bytes(content) != record.get(
            "sha256"
        ):
            raise ProtocolError(f"Bundle file hash mismatch: {relative}")
        records[relative] = record
    return records


def _verify_inventory(root: Path, manifest_name: str, declared: Mapping[str, Any]) -> None:
    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ProtocolError(f"Bundle contains a symlink: {path.relative_to(root)}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative != manifest_name:
                actual.add(relative)
    if actual != set(declared):
        raise ProtocolError(
            "Bundle inventory mismatch; "
            f"missing={sorted(set(declared) - actual)}, unexpected={sorted(actual - set(declared))}"
        )


def _policy_file_record(path: Path, root: Path, role: str) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "role": role,
        "size_bytes": len(content),
        "sha256": sha256_bytes(content),
    }


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError(
            f"POLICY_SOURCE_INVALID: {label} is missing or invalid JSON"
        ) from error
    if not isinstance(value, dict):
        raise ContractValidationError(f"POLICY_SOURCE_INVALID: {label} must be an object")
    return value


def _validate_registry_source(registry: Mapping[str, Any]) -> None:
    """Accept the legacy registry v1.1 shape and the additive v1.2 closure list."""
    schema_version = registry.get("schema_version")
    if schema_version == "1.1":
        valid_shape = set(registry) == _REGISTRY_PROPERTY_NAMES
        closure_claims = [registry.get("closure_claim_id")]
    elif schema_version == "1.2":
        valid_shape = set(registry) == _REGISTRY_V12_PROPERTY_NAMES
        value = registry.get("closure_claim_ids")
        valid_shape = valid_shape and isinstance(value, list)
        closure_claims = value if isinstance(value, list) else []
    else:
        valid_shape = False
        closure_claims = []
    if not valid_shape:
        raise ContractValidationError("POLICY_SOURCE_INVALID: registry has unexpected fields")

    closure = registry.get("closure")
    if closure not in {"OPEN", "CLAIMED_CLOSED"}:
        raise ContractValidationError("POLICY_SOURCE_INVALID: registry closure is invalid")
    if schema_version == "1.1":
        claim_id = closure_claims[0]
        valid_claims = claim_id is None or (
            isinstance(claim_id, str)
            and bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}", claim_id))
        )
        if (closure == "OPEN" and claim_id is not None) or (
            closure == "CLAIMED_CLOSED" and not isinstance(claim_id, str)
        ):
            valid_claims = False
    else:
        valid_claims = all(
            isinstance(claim_id, str)
            and bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}", claim_id))
            for claim_id in closure_claims
        ) and len(closure_claims) == len(set(closure_claims))
        if (closure == "OPEN" and closure_claims) or (
            closure == "CLAIMED_CLOSED" and not closure_claims
        ):
            valid_claims = False
    if not valid_claims:
        raise ContractValidationError(
            "POLICY_SOURCE_INVALID: registry closure claim binding is invalid"
        )


def _registry_closure_claim_ids(registry: Mapping[str, Any]) -> list[str]:
    """Return the registry's explicitly referenced closure claim IDs."""
    if registry.get("schema_version") == "1.1":
        claim_id = registry.get("closure_claim_id")
        return [claim_id] if isinstance(claim_id, str) else []
    claim_ids = registry.get("closure_claim_ids")
    return (
        [claim_id for claim_id in claim_ids if isinstance(claim_id, str)]
        if isinstance(claim_ids, list)
        else []
    )


def _read_json_array(path: Path, label: str) -> list[Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError(
            f"POLICY_SOURCE_INVALID: {label} is missing or invalid JSON"
        ) from error
    if not isinstance(value, list):
        raise ContractValidationError(f"POLICY_SOURCE_INVALID: {label} must be an array")
    return value


def _reject_oracle_fields(content: bytes, relative_path: str) -> None:
    lowered = content.lower()
    if any(marker in lowered for marker in _FORBIDDEN_CONTENT_MARKERS + _FORBIDDEN_POLICY_MARKERS):
        raise ProtocolError(f"Forbidden oracle/answer marker in policy bundle: {relative_path}")


def _contains_symlink(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise ProtocolError("Bundle path escapes its root") from error
    current = root
    for part in relative.parts:
        current = current / part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                return True
        except OSError:
            return False
    return False


def export_method_inputs_v3(
    repository: Path,
    policy_source_bundle: Path,
    output_directory: Path,
    method_id: PolicyMethodIdV3,
    architecture_before_sha: str,
    architecture_source_sha: str,
    evaluation_as_of: str,
    *,
    structural_manifest_path: str = STRUCTURAL_MANIFEST_PATH,
) -> dict[str, Any]:
    """Export a V3 method bundle while keeping architecture and policy revisions distinct."""
    root = repository.resolve(strict=True)
    destination = output_directory.resolve()
    _validate_repository_root(root)
    _validate_commit_id(architecture_before_sha, "architecture_before_sha")
    _validate_commit_id(architecture_source_sha, "architecture_source_sha")
    manifest_path = PurePosixPath(structural_manifest_path)
    if (
        manifest_path.is_absolute()
        or ".." in manifest_path.parts
        or manifest_path.parts[:2] != ("architecture", "states")
        or manifest_path.suffix not in {".yaml", ".yml"}
    ):
        raise ProtocolError("V3 structural manifest path is not allowlisted")
    if method_id not in {"B1", "P"}:
        raise ProtocolError("V3 candidate export supports only B1 and P")
    if destination.exists():
        raise ProtocolError(f"Bundle output already exists: {destination}")
    if destination.is_relative_to(root):
        raise ProtocolError("Method input bundles must be created outside the repository checkout")
    if "," in str(destination):
        raise ProtocolError("Docker bind-mount paths cannot contain commas")

    policy_source = load_policy_source_bundle_v3(policy_source_bundle)
    registry_artifact = dict(policy_source.registry)
    if registry_artifact.get("as_of") != evaluation_as_of:
        raise ContractValidationError("POLICY_SOURCE_INVALID: registry and evaluation as-of differ")
    charter_bytes = policy_source.files[CHARTER_PATH]
    registry_bytes = policy_source.files[REGISTRY_PATH]
    rulebook_bytes = policy_source.files[RULESET_PATH]
    claims_bytes = policy_source.files[POLICY_CLAIMS_PATH]
    ruleset_source_manifest_bytes = (policy_source.root / POLICY_SOURCE_MANIFEST).read_bytes()

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
    manifest_bytes = _git_blob(root, architecture_source_sha, manifest_path.as_posix())
    import yaml

    raw_manifest = yaml.safe_load(manifest_bytes)
    if not isinstance(raw_manifest, Mapping):
        raise ContractValidationError("Architecture state manifest must be a mapping")
    structural_manifest = _project_structural_manifest(raw_manifest)
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
    source_blobs: list[tuple[str, str, str, bytes, str]] = [
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
            "separately_pinned_policy_source_v3",
        ),
        (
            "REGISTRY",
            REGISTRY_PATH,
            "POLICY_REGISTRY",
            registry_bytes,
            "separately_pinned_policy_source_v3",
        ),
    ]
    for record in cast(list[dict[str, Any]], policy_source.manifest["files"]):
        role = str(record["role"])
        if role not in {"approval_evidence", "completeness_evidence"}:
            continue
        relative = str(record["path"])
        source_id = PurePosixPath(relative).stem
        kind = "APPROVAL" if role == "approval_evidence" else "EVIDENCE"
        source_blobs.append(
            (
                source_id,
                relative,
                kind,
                policy_source.files[relative],
                "separately_pinned_policy_source_v3",
            )
        )

    source_ids = [item[0] for item in source_blobs]
    if len(source_ids) != len(set(source_ids)):
        raise ContractValidationError("POLICY_SOURCE_INVALID: duplicate policy source IDs")
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
        completeness_claims=list(policy_source.completeness_claims),
        allow_snapshot_v1_2=True,
    )
    snapshot_bytes = pretty_json_bytes(snapshot)

    files: list[dict[str, Any]] = []
    identity: tuple[int, int] | None = None
    try:
        destination.mkdir(parents=True)
        info = destination.lstat()
        identity = (info.st_dev, info.st_ino)
        _write_new_file(destination / V2_SNAPSHOT_PATH, snapshot_bytes)
        for state, paths, revision in (
            ("before", before_paths, architecture_before_sha),
            ("after", after_paths, architecture_source_sha),
        ):
            for git_path in paths:
                relative = git_path.removeprefix("app/")
                content = _git_blob(root, revision, git_path)
                _write_new_file(destination / f"architecture/{state}/{relative}", content)
        for source_path, bundle_path, _role in FITNESS_INPUTS:
            _write_new_file(
                destination / bundle_path, _git_blob(root, architecture_source_sha, source_path)
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
        _write_new_file(destination / RULESET_PATH, rulebook_bytes)
        _write_new_file(destination / POLICY_CLAIMS_PATH, claims_bytes)
        _write_new_file(destination / METHOD_POLICY_MANIFEST_PATH, ruleset_source_manifest_bytes)
        for _source_id, path, _kind, content, _producer in source_blobs:
            _write_new_file(destination / path, content)

        for state, paths in (("before", before_paths), ("after", after_paths)):
            for git_path in paths:
                relative = git_path.removeprefix("app/")
                output_path = destination / "architecture" / state / relative
                files.append(_file_record(output_path, destination, f"architecture_{state}_source"))
        for path, role in _FIXED_ROLES.items():
            if (destination / path).is_file():
                files.append(_file_record(destination / path, destination, role))
        for _source_id, path, kind, _content, _producer in source_blobs:
            if path in _FIXED_ROLES:
                continue
            files.append(_file_record(destination / path, destination, _SOURCE_KIND_TO_ROLE[kind]))
        files.extend(
            [
                _file_record(destination / RULESET_PATH, destination, "applicability_ruleset"),
                _file_record(
                    destination / POLICY_CLAIMS_PATH, destination, "policy_completeness_claims"
                ),
                _file_record(
                    destination / METHOD_POLICY_MANIFEST_PATH, destination, "policy_source_manifest"
                ),
            ]
        )
        files.sort(key=lambda record: str(record["path"]))
        policy_files = [record for record in files if record["role"] in _POLICY_FILE_ROLES]
        policy_bundle_digest = bundle_sha256(policy_files)
        if policy_bundle_digest != policy_source.manifest["policy_bundle_sha256"]:
            raise ContractValidationError("POLICY_SOURCE_INVALID: copied policy digest changed")
        manifest: dict[str, Any] = {
            "schema_version": 3,
            "allowlist_version": METHOD_INPUT_PROFILE,
            "profile_status": V3_PROFILE_STATUS,
            "method_id": method_id,
            "architecture_before_sha": architecture_before_sha,
            "architecture_source_sha": architecture_source_sha,
            "before_tree_sha": before_tree_sha,
            "after_tree_sha": after_tree_sha,
            "common_snapshot_sha256": sha256_bytes(snapshot_bytes),
            "policy_source_revision": policy_source.manifest["policy_source_revision"],
            "policy_bundle_sha256": policy_bundle_digest,
            "policy_ruleset_sha256": sha256_bytes(rulebook_bytes),
            "files": files,
        }
        manifest["bundle_sha256"] = bundle_sha256(files)
        validate_payload(METHOD_INPUT_SCHEMA, manifest)
        _write_new_file(destination / METHOD_INPUT_MANIFEST, pretty_json_bytes(manifest))
        verify_method_bundle_v3(destination, expected_method_id=method_id)
        known_obligation_ids = _load_obligation_ids(destination / "fitness/obligations.yaml")
        validation = load_and_validate_snapshot(
            destination,
            manifest,
            known_obligation_ids=known_obligation_ids,
            known_condition_ids=set(policy_source.ruleset.conditions),
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
                "V3 snapshot failed SPEC 01 semantic validation: "
                + ", ".join(validation.reason_codes)
                + (" at " + ", ".join(validation.details) if validation.details else "")
            )
        return manifest
    except Exception:
        if identity is not None:
            _remove_owned_partial_bundle(destination, identity)
        raise


def verify_method_bundle_v3(
    bundle_directory: Path,
    expected_method_id: PolicyMethodIdV3 | None = None,
) -> dict[str, Any]:
    """Verify the V3 profile and prove the companion policy source stays separate."""
    root, manifest = _read_manifest(bundle_directory, METHOD_INPUT_MANIFEST, METHOD_INPUT_SCHEMA)
    method_id = cast(PolicyMethodIdV3, manifest["method_id"])
    if expected_method_id is not None and method_id != expected_method_id:
        raise ProtocolError(f"Expected {expected_method_id} V3 bundle, found {method_id}")
    declared = _records_by_path(manifest.get("files"), root)
    for relative, record in declared.items():
        _verify_v3_path_role(PurePosixPath(relative), str(record.get("role")), method_id)
        content = (root / relative).read_bytes()
        if any(
            marker in content.lower()
            for marker in _FORBIDDEN_CONTENT_MARKERS + _FORBIDDEN_POLICY_MARKERS
        ):
            raise ProtocolError(f"Forbidden oracle-field marker in V3 input: {relative}")
    _verify_inventory(root, METHOD_INPUT_MANIFEST, declared)
    files = cast(list[dict[str, Any]], manifest["files"])
    if bundle_sha256(files) != manifest.get("bundle_sha256"):
        raise ProtocolError("V3 method input bundle digest mismatch")
    policy_files = [record for record in files if record.get("role") in _POLICY_FILE_ROLES]
    if bundle_sha256(policy_files) != manifest.get("policy_bundle_sha256"):
        raise ProtocolError("POLICY_SOURCE_INVALID: V3 policy bundle digest mismatch")
    nested_manifest = _read_json_object(
        root / METHOD_POLICY_MANIFEST_PATH, "nested policy manifest"
    )
    validate_payload(POLICY_SOURCE_SCHEMA, nested_manifest)
    if (
        nested_manifest.get("policy_source_revision") != manifest.get("policy_source_revision")
        or nested_manifest.get("policy_bundle_sha256") != manifest.get("policy_bundle_sha256")
        or nested_manifest.get("files") != policy_files
    ):
        raise ProtocolError("POLICY_SOURCE_INVALID: method V3 and policy source pins differ")
    if sha256_bytes((root / RULESET_PATH).read_bytes()) != manifest.get("policy_ruleset_sha256"):
        raise ProtocolError("RULEBOOK_VERSION_MISMATCH: V3 rulebook digest differs")
    policy_claims = _read_json_array(root / POLICY_CLAIMS_PATH, "policy completeness claims")

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
        "applicability_ruleset",
        "policy_completeness_claims",
        "policy_source_manifest",
    }
    if method_id == "P":
        required_roles.add("traceability")
    observed_roles = {str(record.get("role")) for record in files}
    if observed_roles != required_roles and observed_roles != required_roles | {
        "approval_evidence"
    }:
        raise ProtocolError("V3 method bundle roles differ from the candidate profile")
    if "architecture/state-manifests.json" in declared:
        _verify_transition_state_manifests(root, manifest, declared)
    snapshot_bytes = (root / P_INPUT_SNAPSHOT_PATH).read_bytes()
    if sha256_bytes(snapshot_bytes) != manifest.get("common_snapshot_sha256"):
        raise ProtocolError("COMMON_PROJECTION_MISMATCH: V3 Snapshot digest differs")
    try:
        snapshot = json.loads(snapshot_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError("V3 Snapshot must be valid JSON") from error
    if not isinstance(snapshot, Mapping):
        raise ProtocolError("V3 Snapshot must be an object")
    validate_snapshot_schema(snapshot)
    if policy_claims != snapshot.get("completeness_claims"):
        raise ProtocolError(
            "POLICY_SOURCE_INVALID: policy completeness claims differ from Snapshot"
        )
    _verify_architecture_inventories(root, manifest, snapshot)
    _verify_structural_observation(root, manifest, snapshot)
    source_report = validate_source_references(snapshot, manifest, root)
    if source_report.status is not ValidationStatus.VALID:
        raise ProtocolError(
            "V3 source references invalid: " + ", ".join(source_report.reason_codes)
        )
    _verify_normalized_snapshot_projection(root, snapshot, snapshot_bytes, allow_snapshot_v1_2=True)
    compiled = load_and_validate_ruleset(
        root / RULESET_PATH,
        load_fact_vocabulary(),
        root / "fitness/obligations.yaml",
    )
    if compiled.ruleset_source_sha256 != manifest.get("policy_ruleset_sha256"):
        raise ProtocolError("RULEBOOK_VERSION_MISMATCH: compiled V3 ruleset differs")
    return manifest


def _verify_v3_path_role(path: PurePosixPath, role: str, method_id: PolicyMethodIdV3) -> None:
    relative = path.as_posix()
    extra_paths = {
        RULESET_PATH: "applicability_ruleset",
        POLICY_CLAIMS_PATH: "policy_completeness_claims",
        METHOD_POLICY_MANIFEST_PATH: "policy_source_manifest",
        "architecture/state-manifests.json": "structural_observations",
    }
    if relative in extra_paths:
        if relative == "architecture/state-manifests.json" and method_id != "P":
            raise ProtocolError("TRANSITION_STATE_MANIFESTS_REQUIRE_P_METHOD")
        if extra_paths[relative] != role:
            raise ProtocolError(f"V3 path/role mismatch: {relative}")
        return
    from experiments.execution.tooling.p_input_export_v2 import _verify_v2_path_role

    _verify_v2_path_role(path, role, method_id)


def _verify_transition_state_manifests(
    root: Path,
    method_manifest: Mapping[str, Any],
    declared: Mapping[str, Mapping[str, Any]],
) -> None:
    """Verify optional exact state-manifest bytes bound to a V3 transition."""
    import yaml

    relative = "architecture/state-manifests.json"
    record = declared.get(relative)
    if not isinstance(record, Mapping) or record.get("role") != "structural_observations":
        raise ProtocolError("TRANSITION_STATE_MANIFEST_ROLE_INVALID")
    try:
        payload = _read_json_object(root / relative, "transition state manifests")
    except ProtocolError as error:
        raise ProtocolError("TRANSITION_STATE_MANIFESTS_INVALID") from error
    if (
        set(payload) != {"schema_version", "transition", "manifests"}
        or payload.get("schema_version") != "MONO_CI_B0_PSI_ARCHITECTURE_STATE_MANIFESTS_V1"
    ):
        raise ProtocolError("TRANSITION_STATE_MANIFESTS_INVALID")
    transition = payload.get("transition")
    manifests = payload.get("manifests")
    if not isinstance(transition, Mapping) or set(transition) != {
        "before_state",
        "after_state",
        "before_commit_sha",
        "after_commit_sha",
        "before_tree_sha",
        "after_tree_sha",
    }:
        raise ProtocolError("TRANSITION_STATE_MANIFESTS_INVALID")
    if (
        transition.get("before_commit_sha") != method_manifest.get("architecture_before_sha")
        or transition.get("after_commit_sha") != method_manifest.get("architecture_source_sha")
        or transition.get("before_tree_sha") != method_manifest.get("before_tree_sha")
        or transition.get("after_tree_sha") != method_manifest.get("after_tree_sha")
        or not isinstance(manifests, list)
        or len(manifests) != 2
    ):
        raise ProtocolError("TRANSITION_STATE_MANIFEST_SOURCE_BINDING_MISMATCH")
    expected = (
        ("before", "before_state", "before_commit_sha"),
        ("after", "after_state", "after_commit_sha"),
    )
    for row, (state, state_key, commit_key) in zip(manifests, expected, strict=True):
        if not isinstance(row, Mapping) or set(row) != {
            "state",
            "path",
            "source_commit_sha",
            "sha256",
            "content",
        }:
            raise ProtocolError("TRANSITION_STATE_MANIFEST_ROW_INVALID")
        content = row.get("content")
        if (
            row.get("state") != state
            or row.get("source_commit_sha") != transition.get(commit_key)
            or row.get("path") != f"architecture/states/{transition.get(state_key)}.yaml"
            or not isinstance(content, str)
            or sha256_bytes(content.encode("utf-8")) != row.get("sha256")
        ):
            raise ProtocolError("TRANSITION_STATE_MANIFEST_SOURCE_BINDING_MISMATCH")
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as error:
            raise ProtocolError("TRANSITION_STATE_MANIFEST_CONTENT_INVALID") from error
        if not isinstance(parsed, Mapping) or parsed.get("architecture_state") != transition.get(
            state_key
        ):
            raise ProtocolError("TRANSITION_STATE_MANIFEST_CONTENT_INVALID")


def _load_obligation_ids(path: Path) -> set[str]:
    from experiments.execution.tooling.p_input_export_v2 import _load_obligation_ids as load_ids

    return load_ids(path)
