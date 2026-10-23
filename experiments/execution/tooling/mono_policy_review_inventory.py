"""Read-only structural checks for a non-authoritative MONO-E1 Q proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypeGuard

import yaml
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY = ROOT / "docs/mono_e1_policy_review_inventory_v1.json"
DEFAULT_SCHEMA = ROOT / "docs/mono_e1_policy_review_inventory_v1.schema.json"
DEFAULT_CATALOG = ROOT / "fitness/catalog/architectural-obligations.yaml"
LIFECYCLE_STAGES = frozenset({"CI_TEST", "DEPLOYMENT", "RUNTIME"})
APPLICABILITY_STATES = frozenset({"ACTIVE", "INACTIVE", "UNKNOWN"})
MANDATORY_STATES = frozenset({"MANDATORY", "OPTIONAL"})
SHA1_PATTERN = re.compile(r"^[a-f0-9]{40}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _is_mapping(value: object) -> TypeGuard[Mapping[str, Any]]:
    return isinstance(value, Mapping)


def _is_sequence(value: object) -> TypeGuard[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _all_rows(obligations: object) -> list[Mapping[str, Any]]:
    if not _is_sequence(obligations):
        return []
    return [row for row in obligations if _is_mapping(row)]


def _catalog_entries(catalog: object) -> list[Mapping[str, Any]]:
    if not _is_mapping(catalog):
        return []
    return _all_rows(catalog.get("obligations"))


def _role_assigned(roles: object, key: str) -> bool:
    if not _is_mapping(roles):
        return False
    value = roles.get(key)
    return isinstance(value, str) and bool(value.strip()) and value != "UNASSIGNED"


def _dimension_state(rows: list[Mapping[str, Any]], key: str) -> list[object]:
    states: list[object] = []
    for row in rows:
        decision = row.get("decision_state")
        states.append(decision.get(key) if _is_mapping(decision) else None)
    return states


def _has_lifecycle_decision(value: object) -> bool:
    if not _is_mapping(value):
        return False
    status = value.get("status")
    rationale = value.get("rationale")
    stages = value.get("required_stages")
    if status == "REQUIRED":
        return (
            _is_sequence(stages)
            and len(stages) > 0
            and all(isinstance(stage, str) and stage in LIFECYCLE_STAGES for stage in stages)
            and isinstance(rationale, str)
            and bool(rationale.strip())
        )
    return status == "NOT_REQUIRED" and isinstance(rationale, str) and bool(rationale.strip())


def _has_source_fact_bindings(value: object) -> str:
    if not _is_mapping(value):
        return "INCOMPLETE"
    status = value.get("status")
    facts = value.get("facts")
    if status == "CONFLICTING":
        return "CONFLICTING"
    if status != "BOUND" or not _is_sequence(facts) or len(facts) == 0:
        return "INCOMPLETE"

    seen: dict[str, tuple[str, ...]] = {}
    for fact in facts:
        if not _is_mapping(fact):
            return "INCOMPLETE"
        fact_id = fact.get("fact_id")
        architecture_state = fact.get("architecture_state")
        source_sha = fact.get("architecture_source_sha")
        source_locator = fact.get("source_locator")
        claim = fact.get("claim")
        observation_type = fact.get("observation_type")
        artifact_sha = fact.get("evidence_sha256")
        verification_sha = fact.get("verification_artifact_sha256")
        fact_status = fact.get("status")
        freshness_status = fact.get("freshness_status")
        if fact_status == "CONFLICTING":
            return "CONFLICTING"
        if (
            not isinstance(fact_id, str)
            or not fact_id
            or not isinstance(architecture_state, str)
            or not architecture_state
            or not isinstance(source_sha, str)
            or SHA1_PATTERN.fullmatch(source_sha) is None
            or not isinstance(source_locator, str)
            or not source_locator
            or not isinstance(claim, str)
            or not claim
            or not isinstance(observation_type, str)
            or not observation_type
            or not isinstance(artifact_sha, str)
            or SHA256_PATTERN.fullmatch(artifact_sha) is None
            or not isinstance(verification_sha, str)
            or SHA256_PATTERN.fullmatch(verification_sha) is None
            or fact_status != "VERIFIED"
            or freshness_status != "CURRENT"
        ):
            return "INCOMPLETE"
        identity = (
            architecture_state,
            source_sha,
            source_locator,
            claim,
            observation_type,
            artifact_sha,
            verification_sha,
        )
        previous = seen.get(fact_id)
        if previous is not None and previous != identity:
            return "CONFLICTING"
        seen[fact_id] = identity
    return "SUPPLIED_UNVERIFIED"


def _pair_is_structurally_bound(pair: object, obligation_id: object) -> bool:
    if not _is_mapping(pair):
        return False
    required_text = (
        "representation_id",
        "architecture_state",
        "evaluator_id",
        "evaluator_version",
        "evidence_scope",
        "independent_reviewer_role",
    )
    if any(not isinstance(pair.get(key), str) or not pair[key].strip() for key in required_text):
        return False
    if pair.get("obligation_id") != obligation_id:
        return False
    source_sha = pair.get("architecture_source_sha")
    if not isinstance(source_sha, str) or SHA1_PATTERN.fullmatch(source_sha) is None:
        return False
    evaluator_source_sha = pair.get("evaluator_source_sha")
    evaluator_tree_sha = pair.get("evaluator_tree_sha")
    if (
        not isinstance(evaluator_source_sha, str)
        or SHA1_PATTERN.fullmatch(evaluator_source_sha) is None
        or not isinstance(evaluator_tree_sha, str)
        or SHA1_PATTERN.fullmatch(evaluator_tree_sha) is None
    ):
        return False
    sha256_fields = (
        "evaluator_artifact_sha256",
        "evaluator_configuration_sha256",
        "evidence_scope_sha256",
    )
    if any(
        not isinstance(pair.get(key), str) or SHA256_PATTERN.fullmatch(pair[key]) is None
        for key in sha256_fields
    ):
        return False
    stage = pair.get("lifecycle_stage")
    if not isinstance(stage, str) or stage not in LIFECYCLE_STAGES:
        return False
    raw_digests = pair.get("raw_artifact_sha256s")
    if (
        not _is_sequence(raw_digests)
        or len(raw_digests) == 0
        or any(
            not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None
            for digest in raw_digests
        )
    ):
        return False
    digest_fields = (
        "semantic_assessment_sha256",
        "positive_control_sha256",
        "negative_control_sha256",
        "independent_review_artifact_sha256",
    )
    return all(
        isinstance(pair.get(key), str) and SHA256_PATTERN.fullmatch(pair[key]) is not None
        for key in digest_fields
    )


def _has_representation_evidence(
    value: object, obligation_id: object, lifecycle_decision: object
) -> str:
    if not _is_mapping(value):
        return "INCOMPLETE"
    status = value.get("status")
    pairs = value.get("pairs")
    if status == "CONFLICTING":
        return "CONFLICTING"
    if status == "NOT_REQUIRED":
        rationale = value.get("rationale")
        return (
            "SUPPLIED_UNVERIFIED"
            if isinstance(rationale, str) and rationale.strip()
            else "INCOMPLETE"
        )
    if status != "DEFINED" or not _is_sequence(pairs) or len(pairs) == 0:
        return "INCOMPLETE"
    if not all(_pair_is_structurally_bound(pair, obligation_id) for pair in pairs):
        return "INCOMPLETE"
    if not _is_mapping(lifecycle_decision) or lifecycle_decision.get("status") != "REQUIRED":
        return "INCOMPLETE"
    required_stages = lifecycle_decision.get("required_stages")
    if (
        not _is_sequence(required_stages)
        or len(required_stages) == 0
        or any(
            not isinstance(stage, str) or stage not in LIFECYCLE_STAGES for stage in required_stages
        )
    ):
        return "INCOMPLETE"
    pair_stages = {
        pair.get("lifecycle_stage")
        for pair in pairs
        if _is_mapping(pair) and isinstance(pair.get("lifecycle_stage"), str)
    }
    if not set(required_stages).issubset(pair_stages):
        return "INCOMPLETE"
    return "SUPPLIED_UNVERIFIED"


def assess_decision_readiness(inventory: Mapping[str, Any]) -> dict[str, str]:
    """Report structural readiness dimensions without authenticating any decision."""
    rows = _all_rows(inventory.get("obligations"))
    roles = inventory.get("review_roles")
    authority_assigned = _role_assigned(roles, "accountable_policy_authority")
    methods_reviewer_assigned = _role_assigned(roles, "independent_methods_reviewer")
    lifecycle_reviewer_assigned = _role_assigned(roles, "lifecycle_protocol_reviewer")

    applicability = _dimension_state(rows, "applicability")
    mandatory = _dimension_state(rows, "mandatory_status")
    lifecycle = _dimension_state(rows, "lifecycle_stage_requirements")
    source_facts = _dimension_state(rows, "source_fact_bindings")
    representation = _dimension_state(rows, "representation_evidence_requirements")

    applicability_supplied = bool(rows) and all(
        isinstance(value, str) and value in APPLICABILITY_STATES for value in applicability
    )
    mandatory_supplied = bool(rows) and all(
        isinstance(value, str) and value in MANDATORY_STATES for value in mandatory
    )
    lifecycle_supplied = bool(rows) and all(_has_lifecycle_decision(value) for value in lifecycle)
    fact_states = [_has_source_fact_bindings(value) for value in source_facts]
    evidence_states = [
        _has_representation_evidence(
            value,
            row.get("obligation_id"),
            lifecycle_decision,
        )
        for row, value, lifecycle_decision in zip(rows, representation, lifecycle, strict=False)
    ]

    if not rows:
        authority_backed_applicability = "INCOMPLETE"
        mandatory_status = "INCOMPLETE"
        lifecycle_status = "INCOMPLETE"
        source_fact_status = "INCOMPLETE"
        representation_status = "INCOMPLETE"
    else:
        authority_backed_applicability = (
            "SUPPLIED_UNVERIFIED"
            if applicability_supplied and authority_assigned
            else "UNVERIFIED_AUTHORITY"
            if applicability_supplied
            else "INCOMPLETE"
        )
        mandatory_status = (
            "SUPPLIED_UNVERIFIED"
            if mandatory_supplied and authority_assigned
            else "UNVERIFIED_AUTHORITY"
            if mandatory_supplied
            else "INCOMPLETE"
        )
        lifecycle_status = (
            "SUPPLIED_UNVERIFIED"
            if lifecycle_supplied and lifecycle_reviewer_assigned
            else "UNVERIFIED_REVIEW"
            if lifecycle_supplied
            else "INCOMPLETE"
        )
        source_fact_status = (
            "CONFLICTING"
            if "CONFLICTING" in fact_states
            else "INCOMPLETE"
            if "INCOMPLETE" in fact_states
            else "SUPPLIED_UNVERIFIED"
        )
        representation_status = (
            "CONFLICTING"
            if "CONFLICTING" in evidence_states
            else "INCOMPLETE"
            if "INCOMPLETE" in evidence_states
            else "SUPPLIED_UNVERIFIED"
        )

    authority_status = "SUPPLIED_UNVERIFIED" if authority_assigned else "UNASSIGNED"
    reviewer_status = "SUPPLIED_UNVERIFIED" if methods_reviewer_assigned else "UNASSIGNED"
    return {
        "policy_authority": authority_status,
        "independent_methods_reviewer": reviewer_status,
        "authority_backed_applicability_decisions": authority_backed_applicability,
        "mandatory_status_decisions": mandatory_status,
        "lifecycle_stage_requirements": lifecycle_status,
        "source_fact_bindings": source_fact_status,
        "representation_evidence_requirements": representation_status,
        "policy_universe_closure": "PENDING_EXTERNAL_AUTHORITY",
        "approved_scientific_denominator": "NOT_ESTABLISHED",
        "scientific_approval": "NOT_CERTIFIED",
    }


def validate_inventory_object(
    inventory: object,
    catalog: object,
    catalog_bytes: bytes,
    schema: object,
) -> dict[str, Any]:
    """Compare a proposal to the exact pinned catalog; never certify policy authority."""
    issue_codes: set[str] = set()
    schema_errors: list[str] = []
    if _is_mapping(schema):
        validator = Draft202012Validator(schema)
        if not _is_mapping(inventory):
            issue_codes.add("inventory_must_be_object")
        else:
            for error in validator.iter_errors(inventory):
                issue_codes.add("schema_validation_failed")
                path = "/".join(str(part) for part in error.absolute_path)
                schema_errors.append(f"{path}: {error.message}")
    else:
        issue_codes.add("schema_must_be_object")

    catalog_version = catalog.get("schema_version") if _is_mapping(catalog) else None
    catalog_rows = _catalog_entries(catalog)
    expected_ids = [entry.get("id") for entry in catalog_rows]
    expected_by_id = {
        entry.get("id"): entry for entry in catalog_rows if isinstance(entry.get("id"), str)
    }

    catalog_pin = inventory.get("catalog_pin") if _is_mapping(inventory) else None
    if not _is_mapping(catalog_pin) or catalog_pin.get("schema_version") != catalog_version:
        issue_codes.add("catalog_version_mismatch")
    actual_digest = hashlib.sha256(catalog_bytes).hexdigest()
    if not _is_mapping(catalog_pin) or catalog_pin.get("sha256") != actual_digest:
        issue_codes.add("catalog_digest_mismatch")

    inventory_rows = _all_rows(inventory.get("obligations") if _is_mapping(inventory) else None)
    inventory_ids = [row.get("obligation_id") for row in inventory_rows]
    string_ids = [value for value in inventory_ids if isinstance(value, str)]
    policy_sources = _all_rows(
        inventory.get("existing_policy_sources") if _is_mapping(inventory) else None
    )
    policy_source_ids = [source.get("source_id") for source in policy_sources]
    string_policy_source_ids = [value for value in policy_source_ids if isinstance(value, str)]
    if len(string_policy_source_ids) != len(set(string_policy_source_ids)):
        issue_codes.add("duplicate_policy_source_id")
    known_policy_source_ids = set(string_policy_source_ids)
    for row in inventory_rows:
        refs = row.get("policy_source_refs")
        if not _is_sequence(refs) or any(
            not isinstance(reference, str) or reference not in known_policy_source_ids
            for reference in refs
        ):
            issue_codes.add("unknown_policy_source_reference")
    if len(string_ids) != len(set(string_ids)):
        issue_codes.add("duplicate_obligation")
    known_ids = set(expected_by_id)
    for obligation_id in string_ids:
        if obligation_id not in known_ids:
            issue_codes.add("unknown_obligation_id")
    if set(string_ids) != known_ids:
        issue_codes.add("missing_obligation")
    if string_ids != expected_ids:
        issue_codes.add("catalog_order_mismatch")

    for index, row in enumerate(inventory_rows, start=1):
        row_id = row.get("obligation_id")
        source_entry = row.get("catalog_entry")
        if (
            isinstance(row_id, str)
            and row_id in expected_by_id
            and source_entry != expected_by_id[row_id]
        ):
            issue_codes.add("catalog_entry_mismatch")
        if row.get("catalog_order") != index:
            issue_codes.add("catalog_order_mismatch")

    complete = not issue_codes
    readiness = (
        assess_decision_readiness(inventory)
        if _is_mapping(inventory)
        else {
            "policy_authority": "UNASSIGNED",
            "independent_methods_reviewer": "UNASSIGNED",
            "authority_backed_applicability_decisions": "INCOMPLETE",
            "mandatory_status_decisions": "INCOMPLETE",
            "lifecycle_stage_requirements": "INCOMPLETE",
            "source_fact_bindings": "INCOMPLETE",
            "representation_evidence_requirements": "INCOMPLETE",
            "policy_universe_closure": "PENDING_EXTERNAL_AUTHORITY",
            "approved_scientific_denominator": "NOT_ESTABLISHED",
            "scientific_approval": "NOT_CERTIFIED",
        }
    )
    return {
        "validator": "MONO_E1_POLICY_REVIEW_INVENTORY_STRUCTURAL_V1",
        "result": "PASS_CATALOG_INVENTORY_ONLY" if complete else "FAIL_CATALOG_INVENTORY",
        "catalog_inventory_status": "COMPLETE_AGAINST_PINNED_CATALOG" if complete else "INCOMPLETE",
        "catalog_row_count": len(string_ids),
        "catalog_sha256": actual_digest,
        "issue_codes": sorted(issue_codes),
        "schema_errors": sorted(schema_errors),
        "decision_dimensions": readiness,
        "scientific_approval": "NOT_CERTIFIED",
    }


def validate_inventory_paths(
    inventory_path: Path = DEFAULT_INVENTORY,
    catalog_path: Path = DEFAULT_CATALOG,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    catalog_bytes = catalog_path.read_bytes()
    catalog = yaml.safe_load(catalog_bytes)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return validate_inventory_object(inventory, catalog, catalog_bytes, schema)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args(argv)
    try:
        report = validate_inventory_paths(args.inventory, args.catalog, args.schema)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(json.dumps({"result": "INPUT_ERROR", "error": str(error)}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["catalog_inventory_status"] == "COMPLETE_AGAINST_PINNED_CATALOG" else 1


if __name__ == "__main__":
    raise SystemExit(main())
