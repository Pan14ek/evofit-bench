"""Validation helpers for the versioned P input contract v1.1."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import load_schema
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    sha256_bytes,
)

P_INPUT_SCHEMA_NAME = "architecture_policy_snapshot_v1_1.schema.json"
P_INPUT_SNAPSHOT_PATH = "architecture-policy-snapshot.json"
FACT_VOCABULARY_PATH = Path(__file__).resolve().parents[1] / "contracts" / "fact_vocabulary_v1.json"
_FV_CORE_V1_NAMES = (
    "component.python_module_identity",
    "component.module_added",
    "component.module_removed",
    "component.capability_module",
    "component.declared_cross_module_dependency",
    "component.shared_infrastructure",
    "deployment.unit_count_declared",
    "deployment.process_count_declared",
    "deployment.database_instance_count_declared",
    "deployment.database_product_declared",
    "communication.internal_mode_declared",
    "communication.broker_declared",
)
_SOURCE_KIND_TO_ROLE = {
    "ARCHITECTURE_SOURCE": "architecture_inventory",
    "STRUCTURAL_OBSERVATION": "structural_observations",
    "POLICY_CHARTER": "policy_charter",
    "POLICY_REGISTRY": "policy_registry",
    "EVIDENCE": "completeness_evidence",
    "APPROVAL": "approval_evidence",
}
_RFC3339_DATETIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)
_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("date-time", raises=(ValueError, OverflowError))  # type: ignore[untyped-decorator]
def _is_rfc3339_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if _RFC3339_DATETIME.fullmatch(value) is None:
        return False
    normalized = value[:-1] + "+00:00" if value[-1:].lower() == "z" else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


class ValidationStatus(StrEnum):
    """Three-valued status for structural and evidence validation reports."""

    VALID = "VALID"
    INVALID = "INVALID"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True)
class ValidationReport:
    """Serialization-friendly outcome with stable codes and bounded references."""

    status: ValidationStatus
    reason_codes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    details: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation of the report."""
        return {
            "status": self.status.value,
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
            "details": list(self.details),
        }


@dataclass(frozen=True)
class SourceReference:
    """A source row already matched to a typed outer-manifest file record."""

    source_id: str
    kind: str
    path: str
    sha256: str
    state: str | None = None
    revision: str | None = None
    content: bytes | None = field(default=None, repr=False, compare=False)


class FactVerifier(Protocol):
    """Independently check an extracted fact against its pinned source bytes."""

    def __call__(
        self,
        fact: Mapping[str, Any],
        sources: Mapping[str, SourceReference],
        snapshot: Mapping[str, Any],
    ) -> bool | None: ...


class AuthorityTrustContext(Protocol):
    """Externally configured trust anchors and cryptographic proof verifiers."""

    def verify_charter(
        self,
        charter: Mapping[str, Any],
        source: SourceReference,
        evaluation_as_of: str,
    ) -> bool | None: ...

    def verify_approval(
        self,
        policy: Mapping[str, Any],
        charter: Mapping[str, Any],
        source: SourceReference,
        evaluation_as_of: str,
    ) -> bool | None: ...


class CompletenessVerifier(Protocol):
    """Check one claim within its exact predicate/scope/revision/time bounds."""

    def __call__(
        self,
        claim: Mapping[str, Any],
        sources: Mapping[str, SourceReference],
        snapshot: Mapping[str, Any],
    ) -> bool | None: ...


def validate_snapshot_schema(payload: Mapping[str, Any]) -> None:
    """Validate a Snapshot against the canonical Draft 2020-12 schema.

    The shared schema loader checks the schema itself. The standard format
    checker has a strict RFC 3339 date-time assertion for this contract, and
    validation errors include the failing JSON path.
    """
    if not isinstance(payload, Mapping):
        raise ContractValidationError("P input Snapshot must be a JSON object")
    validator = Draft202012Validator(
        load_schema(P_INPUT_SCHEMA_NAME), format_checker=_FORMAT_CHECKER
    )
    errors = sorted(
        validator.iter_errors(dict(payload)), key=lambda error: list(error.absolute_path)
    )
    if errors:
        details = "; ".join(
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise ContractValidationError(f"{P_INPUT_SCHEMA_NAME} validation failed: {details}")


def load_fact_vocabulary() -> dict[str, Any]:
    """Load the source-controlled FV_CORE_V1 registry and enforce its boundary."""
    payload = json.loads(FACT_VOCABULARY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("vocabulary_version") != "FV_CORE_V1":
        raise ContractValidationError("Fact vocabulary version must be FV_CORE_V1")
    predicates = payload.get("predicates")
    if not isinstance(predicates, list):
        raise ContractValidationError("Fact vocabulary predicates must be a list")
    names = [item.get("name") for item in predicates if isinstance(item, dict)]
    if len(predicates) != 12 or tuple(names) != _FV_CORE_V1_NAMES:
        raise ContractValidationError(
            "FV_CORE_V1 must contain exactly the twelve ordered activation-grade predicates"
        )
    return payload


def validate_facts(
    snapshot: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    allowed_sources: Mapping[str, SourceReference],
    fact_verifier: FactVerifier | None = None,
) -> ValidationReport:
    """Check FV types, epistemic kinds, scope, source roles, and pinned revisions.

    ``allowed_sources`` must come from source-reference validation. Extracted
    facts remain UNDETERMINED until ``fact_verifier`` independently checks the
    extraction against those pinned source bytes.
    """
    if vocabulary.get("vocabulary_version") != "FV_CORE_V1":
        return _report(ValidationStatus.INVALID, "VERSION_MISMATCH", "/fact_vocabulary_version")
    predicates = vocabulary.get("predicates")
    if not isinstance(predicates, list) or len(predicates) != 12:
        return _report(ValidationStatus.INVALID, "VERSION_MISMATCH", "/vocabulary/predicates")
    by_name = {str(item.get("name")): item for item in predicates if isinstance(item, Mapping)}
    facts = snapshot.get("facts")
    architecture = snapshot.get("architecture")
    if not isinstance(facts, list) or not isinstance(architecture, Mapping):
        return _report(ValidationStatus.INVALID, "SCHEMA_INVALID", "/facts")

    invalid_codes: set[str] = set()
    undetermined_codes: set[str] = set()
    evidence_refs: set[str] = set()
    details: set[str] = set()
    seen_ids: set[str] = set()
    for index, fact in enumerate(facts):
        location = f"/facts/{index}"
        if not isinstance(fact, Mapping):
            invalid_codes.add("SCHEMA_INVALID")
            details.add(location)
            continue
        fact_id = fact.get("id")
        if not isinstance(fact_id, str) or fact_id in seen_ids:
            invalid_codes.add("DUPLICATE_IDENTIFIER")
            details.add(f"{location}/id")
        else:
            seen_ids.add(fact_id)

        predicate_name = fact.get("predicate")
        descriptor = by_name.get(str(predicate_name))
        if descriptor is None:
            invalid_codes.add("UNKNOWN_PREDICATE")
            details.add(f"{location}/predicate")
            continue

        epistemic_kind = fact.get("epistemic_kind")
        if epistemic_kind not in descriptor.get("allowed_epistemic_kinds", []):
            invalid_codes.add("FACT_EPISTEMIC_KIND_INVALID")
            details.add(f"{location}/epistemic_kind")
        value = fact.get("value")
        if epistemic_kind == "UNKNOWN":
            if value is not None:
                invalid_codes.add("FACT_TYPE_MISMATCH")
                details.add(f"{location}/value")
        elif not _fact_value_matches(str(descriptor.get("value_type")), value, str(predicate_name)):
            invalid_codes.add("FACT_TYPE_MISMATCH")
            details.add(f"{location}/value")

        scope = fact.get("scope")
        if scope not in descriptor.get("allowed_scopes", []):
            invalid_codes.add("FACT_SCOPE_INVALID")
            details.add(f"{location}/scope")

        source_ids = fact.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            invalid_codes.add("MISSING_SOURCE_REF")
            details.add(f"{location}/source_ids")
            continue
        fact_state = fact.get("state")
        observed_states: set[str] = set()
        referenced_sources: dict[str, SourceReference] = {}
        for source_id in source_ids:
            source = allowed_sources.get(str(source_id))
            if source is None:
                invalid_codes.add("MISSING_SOURCE_REF")
                details.add(f"{location}/source_ids")
                continue
            referenced_sources[str(source_id)] = source
            if source.kind not in descriptor.get("allowed_source_kinds", []):
                invalid_codes.add("SOURCE_NOT_ALLOWLISTED")
                details.add(f"{location}/source_ids")
            if source.state is not None:
                observed_states.add(source.state)
                if source.revision != architecture.get(f"{source.state}_commit"):
                    invalid_codes.add("VERSION_MISMATCH")
                    details.add(f"{location}/source_ids")

        required_states = descriptor.get("source_states", [])
        if required_states == ["fact_state"]:
            if observed_states and observed_states != {str(fact_state)}:
                invalid_codes.add("VERSION_MISMATCH")
                details.add(f"{location}/state")
        elif isinstance(required_states, list) and not set(required_states).issubset(
            observed_states
        ):
            invalid_codes.add("VERSION_MISMATCH")
            details.add(f"{location}/source_ids")

        if epistemic_kind == "EXTRACTED":
            expected_method = descriptor.get("method_id")
            if not isinstance(expected_method, str) or fact.get("method_id") != expected_method:
                invalid_codes.add("FACT_METHOD_INVALID")
                details.add(f"{location}/method_id")
            elif fact_verifier is None:
                undetermined_codes.add("EXTRACTED_FACT_UNVERIFIED")
                details.add(location)
            else:
                try:
                    verdict = fact_verifier(fact, referenced_sources, snapshot)
                except Exception:
                    verdict = None
                if verdict is True:
                    evidence_refs.update(referenced_sources)
                elif verdict is False:
                    invalid_codes.add("EXTRACTED_FACT_REJECTED")
                    details.add(location)
                else:
                    undetermined_codes.add("EXTRACTED_FACT_UNVERIFIED")
                    details.add(location)
        elif epistemic_kind != "UNKNOWN":
            evidence_refs.update(referenced_sources)

    if invalid_codes:
        return ValidationReport(
            ValidationStatus.INVALID,
            tuple(sorted(invalid_codes)),
            tuple(sorted(evidence_refs)),
            tuple(sorted(details)),
        )
    if undetermined_codes:
        return ValidationReport(
            ValidationStatus.UNDETERMINED,
            tuple(sorted(undetermined_codes)),
            tuple(sorted(evidence_refs)),
            tuple(sorted(details)),
        )
    return ValidationReport(ValidationStatus.VALID, evidence_refs=tuple(sorted(evidence_refs)))


def _fact_value_matches(value_type: str, value: Any, predicate: str) -> bool:
    if value_type == "nonnegative_integer":
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0
    if value_type == "string":
        return isinstance(value, str) and bool(value.strip())
    if value_type == "string_set":
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item for item in value
        ):
            return False
        if value != sorted(value) or len(value) != len(set(value)):
            return False
        if predicate in {
            "component.python_module_identity",
            "component.module_added",
            "component.module_removed",
            "component.shared_infrastructure",
        }:
            return all(_is_python_module(item) for item in value)
        return True
    if value_type == "capability_module":
        if not isinstance(value, Mapping) or set(value) != {"name", "package"}:
            return False
        name = value.get("name")
        package = value.get("package")
        if not isinstance(name, str) or not name or not isinstance(package, str):
            return False
        return all(part.isidentifier() for part in name.split(".")) and _is_python_module(package)
    if value_type == "module_dependency":
        if not isinstance(value, Mapping) or set(value) != {"from", "to"}:
            return False
        values = list(value.values())
        return all(isinstance(item, str) and _is_python_module(item) for item in values)
    return False


def _is_python_module(value: str) -> bool:
    parts = value.split(".")
    return parts[0] == "app" and all(part.isidentifier() for part in parts)


def _report(status: ValidationStatus, reason_code: str, detail: str) -> ValidationReport:
    return ValidationReport(status, (reason_code,), details=(detail,))


def validate_source_references(
    snapshot: Mapping[str, Any],
    method_manifest: Mapping[str, Any],
    bundle_root: Path,
) -> ValidationReport:
    """Verify typed source references, exact bytes, paths, and pinned revision IDs."""
    _, report = _verified_source_manifest(snapshot, method_manifest, bundle_root)
    return report


def load_verified_source_manifest(
    snapshot: Mapping[str, Any],
    method_manifest: Mapping[str, Any],
    bundle_root: Path,
) -> tuple[dict[str, SourceReference], ValidationReport]:
    """Return source metadata and bytes only after path/hash/type checks."""
    return _verified_source_manifest(snapshot, method_manifest, bundle_root)


def _verified_source_manifest(
    snapshot: Mapping[str, Any],
    method_manifest: Mapping[str, Any],
    bundle_root: Path,
) -> tuple[dict[str, SourceReference], ValidationReport]:
    invalid_codes: set[str] = set()
    details: set[str] = set()
    references: dict[str, SourceReference] = {}
    if bundle_root.is_symlink():
        return {}, _report(ValidationStatus.INVALID, "FORBIDDEN_INPUT", "/bundle_root")
    try:
        root = bundle_root.resolve(strict=True)
    except OSError:
        return {}, _report(ValidationStatus.INVALID, "MISSING_SOURCE_REF", "/bundle_root")

    files_value = method_manifest.get("files")
    if not isinstance(files_value, list):
        return {}, _report(ValidationStatus.INVALID, "SCHEMA_INVALID", "/files")
    files: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(files_value):
        location = f"/files/{index}"
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            invalid_codes.add("SCHEMA_INVALID")
            details.add(location)
            continue
        path = str(record["path"])
        if not _safe_relative_path(path):
            invalid_codes.add("FORBIDDEN_INPUT")
            details.add(f"{location}/path")
            continue
        if path in files:
            invalid_codes.add("DUPLICATE_IDENTIFIER")
            details.add(f"{location}/path")
            continue
        files[path] = record

    architecture = snapshot.get("architecture")
    if not isinstance(architecture, Mapping):
        invalid_codes.add("SCHEMA_INVALID")
        details.add("/architecture")
    else:
        pairs = (
            ("before_commit", "architecture_before_sha"),
            ("after_commit", "architecture_source_sha"),
            ("before_tree", "before_tree_sha"),
            ("after_tree", "after_tree_sha"),
        )
        for snapshot_key, manifest_key in pairs:
            if architecture.get(snapshot_key) != method_manifest.get(manifest_key):
                invalid_codes.add("VERSION_MISMATCH")
                details.add(f"/architecture/{snapshot_key}")

    source_values = snapshot.get("sources")
    if not isinstance(source_values, list):
        invalid_codes.add("SCHEMA_INVALID")
        details.add("/sources")
        source_values = []
    seen_ids: set[str] = set()
    for index, source in enumerate(source_values):
        location = f"/sources/{index}"
        if not isinstance(source, Mapping):
            invalid_codes.add("SCHEMA_INVALID")
            details.add(location)
            continue
        source_id = source.get("id")
        source_path_value = source.get("path")
        kind = source.get("kind")
        if not isinstance(source_id, str) or source_id in seen_ids:
            invalid_codes.add("DUPLICATE_IDENTIFIER")
            details.add(f"{location}/id")
            continue
        seen_ids.add(source_id)
        if not isinstance(source_path_value, str) or not _safe_relative_path(source_path_value):
            invalid_codes.add("FORBIDDEN_INPUT")
            details.add(f"{location}/path")
            continue
        if source_path_value in {
            P_INPUT_SNAPSHOT_PATH,
            "method_input.json",
            "method_input_v2.json",
        }:
            invalid_codes.add("FORBIDDEN_INPUT")
            details.add(f"{location}/path")
            continue
        expected_role = _SOURCE_KIND_TO_ROLE.get(str(kind))
        record = files.get(source_path_value)
        if expected_role is None or record is None or record.get("role") != expected_role:
            invalid_codes.add("SOURCE_NOT_ALLOWLISTED")
            details.add(f"{location}/kind")
            continue
        file_path = root.joinpath(*PurePosixPath(source_path_value).parts)
        if _contains_symlink(file_path, root):
            invalid_codes.add("FORBIDDEN_INPUT")
            details.add(f"{location}/path")
            continue
        try:
            resolved_path = file_path.resolve(strict=True)
            if not resolved_path.is_relative_to(root) or not resolved_path.is_file():
                raise OSError("source path is not a regular file within the bundle")
            content = resolved_path.read_bytes()
        except OSError:
            invalid_codes.add("MISSING_SOURCE_REF")
            details.add(f"{location}/path")
            continue
        digest = sha256_bytes(content)
        if (
            type(record.get("size_bytes")) is not int
            or record.get("size_bytes") != len(content)
            or record.get("sha256") != digest
            or source.get("sha256") != digest
        ):
            invalid_codes.add("SOURCE_HASH_MISMATCH")
            details.add(f"{location}/sha256")
            continue
        source_state, revision = _inventory_provenance(kind, content)
        references[source_id] = SourceReference(
            source_id=source_id,
            kind=str(kind),
            path=source_path_value,
            sha256=digest,
            state=source_state,
            revision=revision,
            content=content,
        )

    if bundle_sha256([dict(record) for record in files.values()]) != method_manifest.get(
        "bundle_sha256"
    ):
        invalid_codes.add("SOURCE_HASH_MISMATCH")
        details.add("/bundle_sha256")

    facts = snapshot.get("facts", [])
    policies = snapshot.get("policies", [])
    claims = snapshot.get("completeness_claims", [])
    if (
        not isinstance(facts, list)
        or not isinstance(policies, list)
        or not isinstance(claims, list)
    ):
        invalid_codes.add("SCHEMA_INVALID")
        facts, policies, claims = [], [], []
    identifiers: set[str] = set(seen_ids)
    fact_ids: set[str] = set()
    policy_ids: set[str] = set()
    claim_ids: set[str] = set()
    for collection, collection_ids, location in (
        (facts, fact_ids, "facts"),
        (policies, policy_ids, "policies"),
        (claims, claim_ids, "completeness_claims"),
    ):
        for index, item in enumerate(collection):
            if not isinstance(item, Mapping):
                invalid_codes.add("SCHEMA_INVALID")
                details.add(f"/{location}/{index}")
                continue
            identifier = item.get("id")
            if not isinstance(identifier, str) or identifier in identifiers:
                invalid_codes.add("DUPLICATE_IDENTIFIER")
                details.add(f"/{location}/{index}/id")
                continue
            identifiers.add(identifier)
            collection_ids.add(identifier)

    def require_source(source_id: Any, expected_kind: str | None, location: str) -> None:
        source = references.get(str(source_id))
        if source is None:
            invalid_codes.add("MISSING_SOURCE_REF")
            details.add(location)
        elif expected_kind is not None and source.kind != expected_kind:
            invalid_codes.add("SOURCE_NOT_ALLOWLISTED")
            details.add(location)

    for index, fact in enumerate(facts):
        if isinstance(fact, Mapping):
            source_ids = fact.get("source_ids", [])
            if isinstance(source_ids, list):
                for source_id in source_ids:
                    require_source(source_id, None, f"/facts/{index}/source_ids")
    for index, policy in enumerate(policies):
        if not isinstance(policy, Mapping):
            continue
        require_source(policy.get("source_id"), "POLICY_REGISTRY", f"/policies/{index}/source_id")
        approval_id = policy.get("approval_source_id")
        if approval_id is not None:
            require_source(approval_id, "APPROVAL", f"/policies/{index}/approval_source_id")
        targets = policy.get("target_policy_ids", [])
        if isinstance(targets, list) and any(target not in policy_ids for target in targets):
            invalid_codes.add("MISSING_SOURCE_REF")
            details.add(f"/policies/{index}/target_policy_ids")
    for index, claim in enumerate(claims):
        if isinstance(claim, Mapping):
            source_ids = claim.get("evidence_source_ids", [])
            if isinstance(source_ids, list):
                for source_id in source_ids:
                    require_source(
                        source_id,
                        "EVIDENCE",
                        f"/completeness_claims/{index}/evidence_source_ids",
                    )

    registry = snapshot.get("policy_registry")
    if isinstance(registry, Mapping):
        require_source(registry.get("source_id"), "POLICY_REGISTRY", "/policy_registry/source_id")
        require_source(
            registry.get("authority_charter_source_id"),
            "POLICY_CHARTER",
            "/policy_registry/authority_charter_source_id",
        )
        closure_claim_id = registry.get("closure_claim_id")
        if closure_claim_id is not None:
            claim = next(
                (
                    item
                    for item in claims
                    if isinstance(item, Mapping) and item.get("id") == closure_claim_id
                ),
                None,
            )
            if claim is None or claim.get("kind") != "AUTHORITATIVE_POLICY_REGISTRY":
                invalid_codes.add("MISSING_SOURCE_REF")
                details.add("/policy_registry/closure_claim_id")

    if invalid_codes:
        report = ValidationReport(
            ValidationStatus.INVALID,
            tuple(sorted(invalid_codes)),
            details=tuple(sorted(details)),
        )
    else:
        report = ValidationReport(ValidationStatus.VALID)
    return references, report


def _safe_relative_path(path: str) -> bool:
    if not path or "\\" in path:
        return False
    relative = PurePosixPath(path)
    return (
        not relative.is_absolute()
        and ".." not in relative.parts
        and "." not in relative.parts
        and relative.as_posix() == path
    )


def _safe_source_prefix(prefix: str) -> bool:
    if not prefix or prefix.startswith("/") or "\\" in prefix:
        return False
    normalized = prefix[:-1] if prefix.endswith("/") else prefix
    relative = PurePosixPath(normalized)
    return (
        bool(normalized)
        and relative.as_posix() == normalized
        and not relative.is_absolute()
        and "." not in relative.parts
        and ".." not in relative.parts
        and re.fullmatch(r"[A-Za-z0-9_./-]+", normalized) is not None
    )


def _contains_symlink(path: Path, root: Path) -> bool:
    current = path
    while current != root and root in current.parents:
        if current.is_symlink():
            return True
        current = current.parent
    return False


def _inventory_provenance(kind: Any, content: bytes) -> tuple[str | None, str | None]:
    try:
        inventory = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, None
    if not isinstance(inventory, Mapping):
        return None, None
    if kind == "ARCHITECTURE_SOURCE" and inventory.get("state") in {"before", "after"}:
        state = str(inventory["state"])
        revision = inventory.get("commit_sha")
        return state, revision if isinstance(revision, str) else None
    if kind == "STRUCTURAL_OBSERVATION" and inventory.get("source_state") == "after":
        revision = inventory.get("source_commit_sha")
        return "after", revision if isinstance(revision, str) else None
    return None, None


def verify_policy_authority(
    snapshot: Mapping[str, Any],
    charter: Mapping[str, Any],
    source_manifest: Mapping[str, SourceReference],
    trust_context: AuthorityTrustContext | None,
    known_obligation_ids: set[str] | None = None,
    known_condition_ids: set[str] | None = None,
    completeness_report: ValidationReport | None = None,
) -> ValidationReport:
    """Verify Charter authority, policy provenance, time/scope, and conflicts.

    Trust is supplied by an external verifier object. Input flags, issuer role
    names, and hashes alone never make a policy authoritative.
    """
    invalid_codes: set[str] = set()
    undetermined_codes: set[str] = set()
    evidence_refs: set[str] = set()
    details: set[str] = set()
    registry = snapshot.get("policy_registry")
    policies_value = snapshot.get("policies")
    architecture = snapshot.get("architecture")
    if not isinstance(registry, Mapping) or not isinstance(policies_value, list):
        return _report(ValidationStatus.INVALID, "SCHEMA_INVALID", "/policy_registry")
    if not isinstance(architecture, Mapping) or not isinstance(
        architecture.get("evaluation_as_of"), str
    ):
        return _report(ValidationStatus.INVALID, "SCHEMA_INVALID", "/architecture/evaluation_as_of")
    evaluation_as_of = str(architecture["evaluation_as_of"])
    if registry.get("as_of") != evaluation_as_of:
        invalid_codes.add("VERSION_MISMATCH")
        details.add("/policy_registry/as_of")
    charter_source_id = registry.get("authority_charter_source_id")
    charter_source = source_manifest.get(str(charter_source_id))
    registry_source = source_manifest.get(str(registry.get("source_id")))
    if charter_source is None or charter_source.kind != "POLICY_CHARTER":
        invalid_codes.add("MISSING_SOURCE_REF")
        details.add("/policy_registry/authority_charter_source_id")
    if registry_source is None or registry_source.kind != "POLICY_REGISTRY":
        invalid_codes.add("MISSING_SOURCE_REF")
        details.add("/policy_registry/source_id")

    charter_errors = _validate_charter_contract(charter)
    if charter_errors:
        invalid_codes.add("AUTHORITY_CHARTER_INVALID")
        details.update(charter_errors)
    if charter_source is not None:
        file_charter = _source_json(charter_source)
        if file_charter is None or dict(file_charter) != dict(charter):
            invalid_codes.add("SOURCE_HASH_MISMATCH")
            details.add("/policy_registry/authority_charter_source_id")
    if not _policy_is_effective(
        {
            "effective_from": charter.get("effective_from"),
            "effective_until": charter.get("effective_until"),
        },
        evaluation_as_of,
    ):
        invalid_codes.add("VERSION_MISMATCH")
        details.add("/charter/effective_from")
    if registry_source is not None:
        artifact = _source_json(registry_source)
        if artifact is None or not _registry_artifact_matches(artifact, snapshot, registry):
            invalid_codes.add("SOURCE_HASH_MISMATCH")
            details.add("/policy_registry/source_id")

    _validate_charter_references(charter, source_manifest, invalid_codes, details)
    if not charter_errors and charter_source is not None and trust_context is not None:
        try:
            charter_verdict = trust_context.verify_charter(
                charter, charter_source, evaluation_as_of
            )
        except Exception:
            charter_verdict = None
        if charter_verdict is True:
            evidence_refs.add(str(charter_source_id))
        elif charter_verdict is False:
            invalid_codes.add("POLICY_APPROVAL_UNVERIFIED")
            details.add("/policy_registry/authority_charter_source_id")
        else:
            undetermined_codes.add("POLICY_APPROVAL_UNVERIFIED")
            details.add("/policy_registry/authority_charter_source_id")
    else:
        undetermined_codes.add("POLICY_APPROVAL_UNVERIFIED")
        details.add("/policy_registry/authority_charter_source_id")

    policy_by_id = {
        str(policy.get("id")): policy
        for policy in policies_value
        if isinstance(policy, Mapping) and isinstance(policy.get("id"), str)
    }
    for index, policy in enumerate(policies_value):
        location = f"/policies/{index}"
        if not isinstance(policy, Mapping):
            invalid_codes.add("SCHEMA_INVALID")
            details.add(location)
            continue
        status = policy.get("normative_status")
        if status == "DRAFT":
            undetermined_codes.add("POLICY_DRAFT_NON_NORMATIVE")
            details.add(location)
            continue

        role = policy.get("issuer_role")
        required_permission = {
            "APPROVED": "APPROVE_POLICY",
            "REVOKED": "REVOKE_POLICY",
            "SUPERSEDED": "SUPERSEDE_POLICY",
        }.get(str(status))
        permissions = charter.get("role_permissions", {})
        if (
            required_permission is None
            or not isinstance(permissions, Mapping)
            or required_permission not in permissions.get(role, [])
        ):
            invalid_codes.add("POLICY_ISSUER_UNAUTHORIZED")
            details.add(f"{location}/issuer_role")

        policy_scope = str(policy.get("scope", ""))
        registry_scope = str(registry.get("scope", ""))
        if not _scope_is_within(charter, registry_scope, policy_scope):
            invalid_codes.add("POLICY_SCOPE_INVALID")
            details.add(f"{location}/scope")

        source_id = str(policy.get("source_id"))
        if source_id != registry.get("source_id"):
            invalid_codes.add("SOURCE_NOT_ALLOWLISTED")
            details.add(f"{location}/source_id")

        obligation_ids = policy.get("obligation_ids", [])
        if known_obligation_ids is None:
            undetermined_codes.add("OBLIGATION_REFERENCE_UNVERIFIED")
            details.add(f"{location}/obligation_ids")
        elif isinstance(obligation_ids, list) and not set(obligation_ids).issubset(
            known_obligation_ids
        ):
            invalid_codes.add("MISSING_SOURCE_REF")
            details.add(f"{location}/obligation_ids")

        condition_ref = policy.get("condition_ref")
        if condition_ref is not None:
            if known_condition_ids is None:
                undetermined_codes.add("CONDITION_REFERENCE_UNVERIFIED")
                details.add(f"{location}/condition_ref")
            elif condition_ref not in known_condition_ids:
                invalid_codes.add("MISSING_SOURCE_REF")
                details.add(f"{location}/condition_ref")

        interval_valid = _policy_is_effective(policy, evaluation_as_of)
        if not interval_valid:
            invalid_codes.add("VERSION_MISMATCH")
            details.add(location)

        approval_id = policy.get("approval_source_id")
        approval_source = source_manifest.get(str(approval_id))
        if approval_source is None or approval_source.kind != "APPROVAL":
            invalid_codes.add("MISSING_SOURCE_REF")
            details.add(f"{location}/approval_source_id")
            continue
        approval = _source_json(approval_source)
        if approval is None or not _approval_binds_policy(
            approval, policy, registry, str(status), policy_by_id
        ):
            invalid_codes.add("POLICY_APPROVAL_UNVERIFIED")
            details.add(f"{location}/approval_source_id")
            continue
        if trust_context is None or charter_source is None or charter_errors:
            undetermined_codes.add("POLICY_APPROVAL_UNVERIFIED")
            details.add(f"{location}/approval_source_id")
            continue
        try:
            approval_verdict = trust_context.verify_approval(
                policy, charter, approval_source, evaluation_as_of
            )
        except Exception:
            approval_verdict = None
        if approval_verdict is True:
            evidence_refs.add(str(approval_id))
        elif approval_verdict is False:
            invalid_codes.add("POLICY_APPROVAL_UNVERIFIED")
            details.add(f"{location}/approval_source_id")
        else:
            undetermined_codes.add("POLICY_APPROVAL_UNVERIFIED")
            details.add(f"{location}/approval_source_id")

        if status in {"REVOKED", "SUPERSEDED"}:
            history = approval.get("historical_consequence")
            if not isinstance(history, str) or not history.strip():
                invalid_codes.add("POLICY_HISTORY_UNJUSTIFIED")
                details.add(f"{location}/approval_source_id")
            if status == "SUPERSEDED":
                successors = approval.get("superseded_by_policy_ids")
                if (
                    not isinstance(successors, list)
                    or not successors
                    or any(successor not in policy_by_id for successor in successors)
                ):
                    invalid_codes.add("POLICY_HISTORY_UNJUSTIFIED")
                    details.add(f"{location}/approval_source_id")

        if policy.get("kind") in {"EXCEPTION", "RETIREMENT"}:
            targets = policy.get("target_policy_ids", [])
            for target_id in targets if isinstance(targets, list) else []:
                target = policy_by_id.get(str(target_id))
                if target is None:
                    invalid_codes.add("MISSING_SOURCE_REF")
                    details.add(f"{location}/target_policy_ids")
                    continue
                if not _policy_scope_and_state_subset(policy, target, charter):
                    invalid_codes.add("POLICY_SCOPE_INVALID")
                    details.add(f"{location}/target_policy_ids")
                if not _authority_precedes(
                    charter, str(role), str(target.get("issuer_role")), policy_scope
                ):
                    undetermined_codes.add("POLICY_CONFLICT")
                    details.add(f"{location}/target_policy_ids")

    for left_index, left in enumerate(policies_value):
        if not isinstance(left, Mapping) or left.get("normative_status") != "APPROVED":
            continue
        for right_index, right in enumerate(policies_value[left_index + 1 :], start=left_index + 1):
            if not isinstance(right, Mapping) or right.get("normative_status") != "APPROVED":
                continue
            if not _policies_conflict(left, right, evaluation_as_of):
                continue
            if not _policy_scopes_overlap(charter, str(left.get("scope")), str(right.get("scope"))):
                continue
            if not _authority_precedes(
                charter,
                str(left.get("issuer_role")),
                str(right.get("issuer_role")),
                str(left.get("scope")),
            ) and not _authority_precedes(
                charter,
                str(right.get("issuer_role")),
                str(left.get("issuer_role")),
                str(right.get("scope")),
            ):
                undetermined_codes.add("POLICY_CONFLICT")
                details.update({f"/policies/{left_index}", f"/policies/{right_index}"})

    closure = registry.get("closure")
    if closure == "OPEN":
        undetermined_codes.add("REGISTRY_CLOSURE_UNVERIFIED")
        details.add("/policy_registry/closure")
    elif closure == "CLAIMED_CLOSED":
        closure_id = str(registry.get("closure_claim_id"))
        if completeness_report is None or (
            completeness_report.status is not ValidationStatus.VALID
            or closure_id not in completeness_report.evidence_refs
        ):
            undetermined_codes.add("REGISTRY_CLOSURE_UNVERIFIED")
            details.add("/policy_registry/closure_claim_id")

    if invalid_codes:
        return ValidationReport(
            ValidationStatus.INVALID,
            tuple(sorted(invalid_codes | undetermined_codes)),
            tuple(sorted(evidence_refs)),
            tuple(sorted(details)),
        )
    if undetermined_codes:
        return ValidationReport(
            ValidationStatus.UNDETERMINED,
            tuple(sorted(undetermined_codes)),
            tuple(sorted(evidence_refs)),
            tuple(sorted(details)),
        )
    return ValidationReport(ValidationStatus.VALID, evidence_refs=tuple(sorted(evidence_refs)))


def _validate_charter_contract(charter: Mapping[str, Any]) -> set[str]:
    errors: set[str] = set()
    required = {
        "schema_version",
        "charter_id",
        "version",
        "effective_from",
        "effective_until",
        "role_permissions",
        "scope_hierarchy",
        "source_allowlist",
        "precedence",
        "evidence_source_ids",
    }
    if set(charter) != required or charter.get("schema_version") != "1.1":
        errors.add("/charter")
        return errors
    if not isinstance(charter.get("charter_id"), str) or not isinstance(
        charter.get("version"), str
    ):
        errors.add("/charter/charter_id")
    if not _is_rfc3339_datetime(charter.get("effective_from")):
        errors.add("/charter/effective_from")
    until = charter.get("effective_until")
    if until is not None and not _is_rfc3339_datetime(until):
        errors.add("/charter/effective_until")
    roles = charter.get("role_permissions")
    if not isinstance(roles, Mapping) or any(
        not isinstance(role, str)
        or not isinstance(permissions, list)
        or any(not isinstance(permission, str) for permission in permissions)
        or len(permissions) != len(set(permissions))
        for role, permissions in roles.items()
    ):
        errors.add("/charter/role_permissions")
    for key in ("scope_hierarchy", "source_allowlist", "precedence", "evidence_source_ids"):
        if not isinstance(charter.get(key), list):
            errors.add(f"/charter/{key}")
    scope_edges = charter.get("scope_hierarchy")
    if isinstance(scope_edges, list) and any(
        not isinstance(edge, Mapping)
        or set(edge) != {"parent", "child"}
        or not isinstance(edge.get("parent"), str)
        or not isinstance(edge.get("child"), str)
        for edge in scope_edges
    ):
        errors.add("/charter/scope_hierarchy")
    allowlist = charter.get("source_allowlist")
    allowed_kinds = set(_SOURCE_KIND_TO_ROLE)
    if isinstance(allowlist, list) and any(
        not isinstance(item, Mapping)
        or set(item) != {"kind", "path_prefix"}
        or item.get("kind") not in allowed_kinds
        or not isinstance(item.get("path_prefix"), str)
        or not _safe_source_prefix(str(item.get("path_prefix", "")))
        for item in allowlist
    ):
        errors.add("/charter/source_allowlist")
    precedence = charter.get("precedence")
    if isinstance(precedence, list) and any(
        not isinstance(item, Mapping)
        or set(item) != {"higher_role", "lower_role", "scope", "evidence_source_ids"}
        or not isinstance(item.get("higher_role"), str)
        or not isinstance(item.get("lower_role"), str)
        or not isinstance(item.get("scope"), str)
        or not isinstance(item.get("evidence_source_ids"), list)
        or not item.get("evidence_source_ids")
        for item in precedence
    ):
        errors.add("/charter/precedence")
    evidence = charter.get("evidence_source_ids")
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(not isinstance(item, str) for item in evidence)
    ):
        errors.add("/charter/evidence_source_ids")
    return errors


def _validate_charter_references(
    charter: Mapping[str, Any],
    sources: Mapping[str, SourceReference],
    invalid_codes: set[str],
    details: set[str],
) -> None:
    evidence_ids = charter.get("evidence_source_ids", [])
    if isinstance(evidence_ids, list):
        for source_id in evidence_ids:
            source = sources.get(str(source_id))
            if source is None or source.kind != "EVIDENCE":
                invalid_codes.add("MISSING_SOURCE_REF")
                details.add("/charter/evidence_source_ids")
    precedence = charter.get("precedence", [])
    if isinstance(precedence, list):
        for index, item in enumerate(precedence):
            if not isinstance(item, Mapping):
                continue
            for source_id in item.get("evidence_source_ids", []):
                source = sources.get(str(source_id))
                if source is None or source.kind != "EVIDENCE":
                    invalid_codes.add("MISSING_SOURCE_REF")
                    details.add(f"/charter/precedence/{index}/evidence_source_ids")
    allowlist = charter.get("source_allowlist", [])
    if isinstance(allowlist, list):
        for source in sources.values():
            if source.kind in {"POLICY_CHARTER", "EVIDENCE"}:
                continue
            if not any(
                isinstance(rule, Mapping)
                and rule.get("kind") == source.kind
                and source.path.startswith(str(rule.get("path_prefix", "")))
                for rule in allowlist
            ):
                invalid_codes.add("SOURCE_NOT_ALLOWLISTED")
                details.add(f"/sources/{source.source_id}")


def _source_json(source: SourceReference) -> Mapping[str, Any] | None:
    if source.content is None:
        return None
    try:
        payload = json.loads(source.content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _registry_artifact_matches(
    artifact: Mapping[str, Any], snapshot: Mapping[str, Any], registry: Mapping[str, Any]
) -> bool:
    allowed_keys = {
        "schema_version",
        "registry_version",
        "scope",
        "as_of",
        "closure",
        "closure_claim_id",
        "authority_charter_source_id",
        "policies",
    }
    if set(artifact) != allowed_keys or artifact.get("schema_version") != "1.1":
        return False
    expected_registry = {
        "scope": artifact.get("scope"),
        "source_id": registry.get("source_id"),
        "closure": artifact.get("closure"),
        "closure_claim_id": artifact.get("closure_claim_id"),
        "authority_charter_source_id": artifact.get("authority_charter_source_id"),
        "registry_version": artifact.get("registry_version"),
        "as_of": artifact.get("as_of"),
    }
    return dict(registry) == expected_registry and snapshot.get("policies") == artifact.get(
        "policies"
    )


def _scope_is_within(charter: Mapping[str, Any], outer_scope: str, inner_scope: str) -> bool:
    if outer_scope == inner_scope:
        return True
    edges = charter.get("scope_hierarchy", [])
    if not isinstance(edges, list):
        return False
    children: dict[str, set[str]] = {}
    for edge in edges:
        if isinstance(edge, Mapping):
            children.setdefault(str(edge.get("parent")), set()).add(str(edge.get("child")))
    visited = {outer_scope}
    pending = [outer_scope]
    while pending:
        parent = pending.pop()
        for child in children.get(parent, set()):
            if child == inner_scope:
                return True
            if child not in visited:
                visited.add(child)
                pending.append(child)
    return False


def _policy_is_effective(policy: Mapping[str, Any], evaluation_as_of: str) -> bool:
    start = policy.get("effective_from")
    until = policy.get("effective_until")
    if not _is_rfc3339_datetime(start) or not _is_rfc3339_datetime(evaluation_as_of):
        return False
    evaluation = datetime.fromisoformat(
        str(evaluation_as_of)[:-1] + "+00:00"
        if str(evaluation_as_of)[-1:].lower() == "z"
        else str(evaluation_as_of)
    )
    start_value = datetime.fromisoformat(
        str(start)[:-1] + "+00:00" if str(start)[-1:].lower() == "z" else str(start)
    )
    if start_value > evaluation:
        return False
    if until is None:
        return True
    if not _is_rfc3339_datetime(until):
        return False
    end_value = datetime.fromisoformat(
        str(until)[:-1] + "+00:00" if str(until)[-1:].lower() == "z" else str(until)
    )
    return evaluation < end_value


def _approval_binds_policy(
    approval: Mapping[str, Any],
    policy: Mapping[str, Any],
    registry: Mapping[str, Any],
    normative_status: str,
    policy_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    required = {
        "schema_version",
        "action",
        "policy_id",
        "policy_registry_version",
        "policy_source_id",
        "issuer_role",
        "scope",
        "effective_from",
        "effective_until",
        "policy_sha256",
        "historical_consequence",
        "superseded_by_policy_ids",
        "signer_key_id",
        "signature",
    }
    if set(approval) != required or approval.get("schema_version") != "1.1":
        return False
    if not isinstance(approval.get("signer_key_id"), str) or not isinstance(
        approval.get("signature"), str
    ):
        return False
    if (
        approval.get("action") != normative_status
        or approval.get("policy_id") != policy.get("id")
        or approval.get("policy_registry_version") != registry.get("registry_version")
        or approval.get("policy_source_id") != policy.get("source_id")
        or approval.get("issuer_role") != policy.get("issuer_role")
        or approval.get("scope") != policy.get("scope")
        or approval.get("effective_from") != policy.get("effective_from")
        or approval.get("effective_until") != policy.get("effective_until")
        or approval.get("policy_sha256") != sha256_bytes(canonical_json_bytes(dict(policy)))
    ):
        return False
    history = approval.get("historical_consequence")
    successors = approval.get("superseded_by_policy_ids")
    if normative_status in {"REVOKED", "SUPERSEDED"}:
        if not isinstance(history, str) or not history.strip():
            return False
    elif history not in {None, ""} or successors not in (None, []):
        return False
    if normative_status == "SUPERSEDED":
        return (
            isinstance(successors, list)
            and bool(successors)
            and all(successor in policy_by_id for successor in successors)
        )
    return successors in (None, [])


def _policy_scope_and_state_subset(
    exception: Mapping[str, Any], target: Mapping[str, Any], charter: Mapping[str, Any]
) -> bool:
    if not _scope_is_within(charter, str(target.get("scope")), str(exception.get("scope"))):
        return False
    exception_states = exception.get("applies_to_states", [])
    target_states = target.get("applies_to_states", [])
    return (
        isinstance(exception_states, list)
        and isinstance(target_states, list)
        and set(exception_states).issubset(target_states)
    )


def _authority_precedes(
    charter: Mapping[str, Any], higher_role: str, lower_role: str, scope: str
) -> bool:
    precedence = charter.get("precedence", [])
    if not isinstance(precedence, list):
        return False
    return any(
        isinstance(item, Mapping)
        and item.get("higher_role") == higher_role
        and item.get("lower_role") == lower_role
        and _scope_is_within(charter, str(item.get("scope")), scope)
        for item in precedence
    )


def _policies_conflict(
    left: Mapping[str, Any], right: Mapping[str, Any], evaluation_as_of: str
) -> bool:
    if left.get("kind") not in {"UNCONDITIONAL_MANDATE", "CONDITIONAL_MANDATE"}:
        return False
    if right.get("kind") not in {"UNCONDITIONAL_MANDATE", "CONDITIONAL_MANDATE"}:
        return False
    if not _policy_is_effective(left, evaluation_as_of) or not _policy_is_effective(
        right, evaluation_as_of
    ):
        return False
    left_obligations = left.get("obligation_ids", [])
    right_obligations = right.get("obligation_ids", [])
    if not isinstance(left_obligations, list) or not isinstance(right_obligations, list):
        return False
    if not set(left_obligations).intersection(right_obligations):
        return False
    left_states = left.get("applies_to_states", [])
    right_states = right.get("applies_to_states", [])
    if not isinstance(left_states, list) or not isinstance(right_states, list):
        return False
    if not set(left_states).intersection(right_states):
        return False
    left_polarity = left.get("proposition_polarity", "REQUIRED")
    right_polarity = right.get("proposition_polarity", "REQUIRED")
    return (
        isinstance(left_polarity, str)
        and isinstance(right_polarity, str)
        and (left_polarity != right_polarity)
    )


def _policy_scopes_overlap(charter: Mapping[str, Any], left_scope: str, right_scope: str) -> bool:
    return _scope_is_within(charter, left_scope, right_scope) or _scope_is_within(
        charter, right_scope, left_scope
    )


def verify_completeness_claims(
    snapshot: Mapping[str, Any],
    evidence_verifier: CompletenessVerifier | None,
    source_manifest: Mapping[str, SourceReference] | None = None,
) -> ValidationReport:
    """Check bounded completeness evidence without inferring global closure."""
    claims = snapshot.get("completeness_claims", [])
    architecture = snapshot.get("architecture", {})
    if not isinstance(claims, list) or not isinstance(architecture, Mapping):
        return _report(ValidationStatus.INVALID, "SCHEMA_INVALID", "/completeness_claims")
    if not claims:
        return ValidationReport(ValidationStatus.VALID)
    vocabulary = load_fact_vocabulary()
    predicate_names = {item["name"] for item in vocabulary["predicates"]}
    references = source_manifest or {}
    invalid_codes: set[str] = set()
    undetermined_codes: set[str] = set()
    details: set[str] = set()
    verified_claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        location = f"/completeness_claims/{index}"
        if not isinstance(claim, Mapping):
            invalid_codes.add("SCHEMA_INVALID")
            details.add(location)
            continue
        state = claim.get("state")
        revision_field = f"{state}_commit"
        if state not in {"before", "after"} or claim.get(
            "architecture_revision"
        ) != architecture.get(revision_field):
            invalid_codes.add("VERSION_MISMATCH")
            details.add(f"{location}/architecture_revision")
        kind = claim.get("kind")
        fact_type = claim.get("fact_type")
        if kind == "AUTHORITATIVE_POLICY_REGISTRY":
            registry = snapshot.get("policy_registry", {})
            if not isinstance(registry, Mapping):
                invalid_codes.add("SCHEMA_INVALID")
                details.add("/policy_registry")
            elif (
                claim.get("scope") != registry.get("scope")
                or claim.get("policy_registry_version") != registry.get("registry_version")
                or claim.get("as_of") != registry.get("as_of")
            ):
                invalid_codes.add("VERSION_MISMATCH")
                details.add(location)
        elif fact_type not in predicate_names:
            invalid_codes.add("UNKNOWN_PREDICATE")
            details.add(f"{location}/fact_type")

        source_ids = claim.get("evidence_source_ids", [])
        claim_sources: dict[str, SourceReference] = {}
        if not isinstance(source_ids, list):
            invalid_codes.add("MISSING_SOURCE_REF")
            details.add(f"{location}/evidence_source_ids")
        else:
            for source_id in source_ids:
                source = references.get(str(source_id))
                if source is None:
                    undetermined_codes.add("COMPLETENESS_UNVERIFIED")
                    details.add(f"{location}/evidence_source_ids")
                elif source.kind != "EVIDENCE":
                    invalid_codes.add("SOURCE_NOT_ALLOWLISTED")
                    details.add(f"{location}/evidence_source_ids")
                elif source.content is None:
                    undetermined_codes.add("COMPLETENESS_UNVERIFIED")
                    details.add(f"{location}/evidence_source_ids")
                else:
                    claim_sources[str(source_id)] = source
        if evidence_verifier is None or len(claim_sources) != len(source_ids):
            undetermined_codes.add("COMPLETENESS_UNVERIFIED")
            details.add(location)
            continue
        try:
            verdict = evidence_verifier(claim, claim_sources, snapshot)
        except Exception:
            verdict = None
        if verdict is True:
            identifier = claim.get("id")
            if isinstance(identifier, str):
                verified_claim_ids.add(identifier)
        else:
            # A failed or unavailable proof does not establish the opposite claim.
            undetermined_codes.add("COMPLETENESS_UNVERIFIED")
            details.add(location)

    if invalid_codes:
        return ValidationReport(
            ValidationStatus.INVALID,
            tuple(sorted(invalid_codes | undetermined_codes)),
            tuple(sorted(verified_claim_ids)),
            tuple(sorted(details)),
        )
    if undetermined_codes:
        return ValidationReport(
            ValidationStatus.UNDETERMINED,
            tuple(sorted(undetermined_codes)),
            tuple(sorted(verified_claim_ids)),
            tuple(sorted(details)),
        )
    return ValidationReport(
        ValidationStatus.VALID,
        evidence_refs=tuple(sorted(verified_claim_ids)),
    )


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Serializable statuses for the non-algorithmic P input validation gate."""

    schema_status: ValidationStatus
    integrity_status: ValidationStatus
    authority_status: ValidationStatus
    fact_status: ValidationStatus
    completeness_status: ValidationStatus
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    snapshot_digest: str | None
    details: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible validation result without P decisions."""
        return {
            "schema_status": self.schema_status.value,
            "integrity_status": self.integrity_status.value,
            "authority_status": self.authority_status.value,
            "fact_status": self.fact_status.value,
            "completeness_status": self.completeness_status.value,
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
            "snapshot_digest": self.snapshot_digest,
            "details": list(self.details),
        }


def load_and_validate_snapshot(
    bundle_root: Path,
    method_manifest: Mapping[str, Any],
    trust_context: AuthorityTrustContext | None = None,
    fact_verifier: FactVerifier | None = None,
    evidence_verifier: CompletenessVerifier | None = None,
    known_obligation_ids: set[str] | None = None,
    known_condition_ids: set[str] | None = None,
) -> SnapshotValidationResult:
    """Load, validate, and hash a v1.1 Snapshot before any method is invoked."""
    if bundle_root.is_symlink():
        return _snapshot_failure("FORBIDDEN_INPUT", "/bundle_root")
    try:
        root = bundle_root.resolve(strict=True)
        snapshot_path = root / P_INPUT_SNAPSHOT_PATH
        if snapshot_path.is_symlink() or not snapshot_path.is_file():
            raise OSError("snapshot file is missing or not a regular file")
        snapshot_bytes = snapshot_path.read_bytes()
        snapshot = json.loads(snapshot_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return _snapshot_failure("SCHEMA_INVALID", "/architecture-policy-snapshot.json")
    if not isinstance(snapshot, Mapping):
        return _snapshot_failure("SCHEMA_INVALID", "/")
    digest = sha256_bytes(snapshot_bytes)
    try:
        validate_snapshot_schema(snapshot)
    except ContractValidationError:
        return SnapshotValidationResult(
            ValidationStatus.INVALID,
            ValidationStatus.UNDETERMINED,
            ValidationStatus.UNDETERMINED,
            ValidationStatus.UNDETERMINED,
            ValidationStatus.UNDETERMINED,
            ("SCHEMA_INVALID",),
            (),
            digest,
            ("/architecture-policy-snapshot.json",),
        )

    source_manifest, integrity_report = _verified_source_manifest(snapshot, method_manifest, root)
    if method_manifest.get("common_snapshot_sha256") != digest:
        integrity_report = _merge_reports(
            integrity_report,
            _report(
                ValidationStatus.INVALID,
                "COMMON_PROJECTION_MISMATCH",
                "/common_snapshot_sha256",
            ),
        )
    if integrity_report.status is not ValidationStatus.VALID:
        unresolved = ValidationStatus.UNDETERMINED
        reports = [integrity_report]
        return SnapshotValidationResult(
            ValidationStatus.VALID,
            integrity_report.status,
            unresolved,
            unresolved,
            unresolved,
            _combined_reason_codes(reports),
            _combined_evidence_refs(reports),
            digest,
            _combined_details(reports),
        )

    fact_report = validate_facts(snapshot, load_fact_vocabulary(), source_manifest, fact_verifier)
    completeness_report = verify_completeness_claims(snapshot, evidence_verifier, source_manifest)
    registry = snapshot.get("policy_registry", {})
    charter_id = (
        registry.get("authority_charter_source_id") if isinstance(registry, Mapping) else None
    )
    charter_source = source_manifest.get(str(charter_id))
    charter = _source_json(charter_source) if charter_source is not None else None
    if charter is None:
        authority_report = _report(
            ValidationStatus.INVALID,
            "MISSING_SOURCE_REF",
            "/policy_registry/authority_charter_source_id",
        )
    else:
        authority_report = verify_policy_authority(
            snapshot,
            charter,
            source_manifest,
            trust_context,
            known_obligation_ids,
            known_condition_ids,
            completeness_report,
        )
    reports = [integrity_report, fact_report, completeness_report, authority_report]
    return SnapshotValidationResult(
        ValidationStatus.VALID,
        integrity_report.status,
        authority_report.status,
        fact_report.status,
        completeness_report.status,
        _combined_reason_codes(reports),
        _combined_evidence_refs(reports),
        digest,
        _combined_details(reports),
    )


def _snapshot_failure(reason_code: str, detail: str) -> SnapshotValidationResult:
    return SnapshotValidationResult(
        ValidationStatus.INVALID,
        ValidationStatus.INVALID,
        ValidationStatus.UNDETERMINED,
        ValidationStatus.UNDETERMINED,
        ValidationStatus.UNDETERMINED,
        (reason_code,),
        (),
        None,
        (detail,),
    )


def _merge_reports(left: ValidationReport, right: ValidationReport) -> ValidationReport:
    status = (
        ValidationStatus.INVALID
        if ValidationStatus.INVALID in {left.status, right.status}
        else ValidationStatus.UNDETERMINED
        if ValidationStatus.UNDETERMINED in {left.status, right.status}
        else ValidationStatus.VALID
    )
    return ValidationReport(
        status,
        tuple(sorted(set(left.reason_codes) | set(right.reason_codes))),
        tuple(sorted(set(left.evidence_refs) | set(right.evidence_refs))),
        tuple(sorted(set(left.details) | set(right.details))),
    )


def _combined_reason_codes(reports: list[ValidationReport]) -> tuple[str, ...]:
    return tuple(sorted({code for report in reports for code in report.reason_codes}))


def _combined_evidence_refs(reports: list[ValidationReport]) -> tuple[str, ...]:
    return tuple(sorted({ref for report in reports for ref in report.evidence_refs}))


def _combined_details(reports: list[ValidationReport]) -> tuple[str, ...]:
    return tuple(sorted({detail for report in reports for detail in report.details}))


__all__ = [
    "FACT_VOCABULARY_PATH",
    "P_INPUT_SCHEMA_NAME",
    "P_INPUT_SNAPSHOT_PATH",
    "AuthorityTrustContext",
    "CompletenessVerifier",
    "FactVerifier",
    "SnapshotValidationResult",
    "SourceReference",
    "ValidationReport",
    "ValidationStatus",
    "load_and_validate_snapshot",
    "load_fact_vocabulary",
    "load_verified_source_manifest",
    "validate_source_references",
    "validate_facts",
    "validate_snapshot_schema",
    "verify_completeness_claims",
    "verify_policy_authority",
]
