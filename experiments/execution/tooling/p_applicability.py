"""Evidence-aware applicability evaluation for P, separate from adaptation/scoring."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_input_validation import (
    SnapshotValidationResult,
    ValidationStatus,
    validate_snapshot_schema,
)

RULESET_SCHEMA = "applicability_ruleset_v1.schema.json"
OBLIGATION_CATALOG_PATH = (
    Path(__file__).resolve().parents[3] / "fitness/catalog/architectural-obligations.yaml"
)
MAX_RULESET_BYTES = 1_048_576
MAX_AST_DEPTH = 12
MAX_AST_NODES = 128
MAX_CONDITIONS = 128
MAX_FACT_ROWS = 4096
MAX_POLICY_ROWS = 4096
MAX_COMPLETENESS_ROWS = 4096
ENGINE_VERSION = "P_APPLICABILITY_ENGINE_V1"
_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_SOURCE_REF_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _deep_freeze(value: Any) -> Any:
    """Recursively freeze JSON-shaped inputs retained by public result objects."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_deep_freeze(item) for item in value)
    return value


class TruthValue(StrEnum):
    """Strong Kleene truth values used only for expression evaluation."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class ApplicabilityStatus(StrEnum):
    """Three-way normative applicability result for one obligation."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


class ProofStatus(StrEnum):
    """External verifier result; never supplied as a Snapshot field."""

    VALID = "VALID"
    INVALID = "INVALID"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True)
class Obligation:
    """Public catalog entry used to preserve the full reporting denominator."""

    obligation_id: str
    criterion: str


@dataclass(frozen=True)
class EvidenceProof:
    """Read-only result from an external verifier, bound to exact objects/sources."""

    status: ProofStatus
    subject_sha256: str
    source_bindings: tuple[tuple[str, str], ...]
    verifier_id: str
    evidence_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if _SHA256_PATTERN.fullmatch(self.subject_sha256) is None:
            raise ValueError("EvidenceProof subject_sha256 must be a lowercase SHA-256 digest")
        if not self.verifier_id or len(self.verifier_id) > 128:
            raise ValueError("EvidenceProof verifier_id must be a bounded non-empty identifier")
        for source_id, digest in self.source_bindings:
            if _SOURCE_REF_PATTERN.fullmatch(source_id) is None:
                raise ValueError("EvidenceProof source ids must be stable identifiers")
            if _SHA256_PATTERN.fullmatch(digest) is None:
                raise ValueError("EvidenceProof source bindings must be SHA-256 digests")
        if tuple(sorted(set(self.source_bindings))) != self.source_bindings:
            raise ValueError("EvidenceProof source_bindings must be unique and sorted")
        for reference in (*self.evidence_refs, *self.reason_codes):
            if _SOURCE_REF_PATTERN.fullmatch(reference) is None:
                raise ValueError("EvidenceProof references/codes must not contain paths or secrets")


@dataclass(frozen=True)
class EvidenceLedger:
    """Per-object trust outcomes produced outside the method and frozen at invocation."""

    fact_proofs: Mapping[str, EvidenceProof]
    policy_proofs: Mapping[str, EvidenceProof]
    completeness_proofs: Mapping[str, EvidenceProof]
    registry_proof: EvidenceProof | None = None
    charter_proof: EvidenceProof | None = None
    authorized_overrides: Mapping[tuple[str, str], EvidenceProof] | None = None
    policy_precedence: Mapping[tuple[str, str], EvidenceProof] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fact_proofs", MappingProxyType(dict(self.fact_proofs)))
        object.__setattr__(self, "policy_proofs", MappingProxyType(dict(self.policy_proofs)))
        object.__setattr__(
            self, "completeness_proofs", MappingProxyType(dict(self.completeness_proofs))
        )
        object.__setattr__(
            self, "authorized_overrides", MappingProxyType(dict(self.authorized_overrides or {}))
        )
        object.__setattr__(
            self, "policy_precedence", MappingProxyType(dict(self.policy_precedence or {}))
        )


@dataclass(frozen=True)
class CompiledRuleset:
    """Validated, bounded AR-DSL with deterministic identities and dependencies."""

    ruleset_version: str
    fact_vocabulary_version: str
    obligation_catalog_sha256: str
    ruleset_sha256: str
    ruleset_source_sha256: str
    conditions: Mapping[str, Mapping[str, Any]]
    predicate_descriptors: Mapping[str, Mapping[str, Any]]
    obligations: tuple[Obligation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "conditions", _deep_freeze(self.conditions))
        object.__setattr__(self, "predicate_descriptors", _deep_freeze(self.predicate_descriptors))


@dataclass(frozen=True)
class ConditionResult:
    """Truth value with stable reasons, fact IDs, and source/verifier references."""

    condition_id: str
    state: str
    truth: TruthValue
    reason_codes: tuple[str, ...] = ()
    fact_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ObligationResult:
    """Diagnostic applicability result; does not encode an adaptation operation."""

    obligation_id: str
    status: ApplicabilityStatus
    reason_codes: tuple[str, ...]
    contributing_policy_ids: tuple[str, ...]
    condition_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "status": self.status.value,
            "reason_codes": list(self.reason_codes),
            "contributing_policy_ids": list(self.contributing_policy_ids),
            "condition_ids": list(self.condition_ids),
            "evidence_refs": list(self.evidence_refs),
            "unresolved_refs": list(self.unresolved_refs),
        }


@dataclass(frozen=True)
class ApplicabilityAssessment:
    """Canonical development-only assessment for one architecture state."""

    ruleset_version: str
    fact_vocabulary_version: str
    policy_registry_version: str
    policy_source_revision: str
    policy_as_of: str
    architecture_source_sha: str
    architecture_state: str
    common_input_sha256: str
    ruleset_sha256: str
    policy_bundle_sha256: str | None
    input_validation: Mapping[str, Any]
    results: tuple[ObligationResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_validation", _deep_freeze(self.input_validation))

    def to_dict(self) -> dict[str, Any]:
        validation = dict(self.input_validation)
        validation["reason_codes"] = list(validation["reason_codes"])
        return {
            "schema_version": 1,
            "engine_version": ENGINE_VERSION,
            "ruleset_version": self.ruleset_version,
            "fact_vocabulary_version": self.fact_vocabulary_version,
            "policy_registry_version": self.policy_registry_version,
            "policy_source_revision": self.policy_source_revision,
            "policy_as_of": self.policy_as_of,
            "architecture_source_sha": self.architecture_source_sha,
            "architecture_state": self.architecture_state,
            "common_input_sha256": self.common_input_sha256,
            "ruleset_sha256": self.ruleset_sha256,
            "policy_bundle_sha256": self.policy_bundle_sha256,
            "input_validation": validation,
            "results": [result.to_dict() for result in self.results],
        }


def tri_not(value: TruthValue) -> TruthValue:
    """Return Strong Kleene negation."""
    return {
        TruthValue.TRUE: TruthValue.FALSE,
        TruthValue.FALSE: TruthValue.TRUE,
        TruthValue.UNKNOWN: TruthValue.UNKNOWN,
    }[value]


def tri_and(values: Sequence[TruthValue]) -> TruthValue:
    """Return Strong Kleene conjunction for a non-empty sequence."""
    if not values:
        raise ValueError("Strong Kleene all requires at least one value")
    if TruthValue.FALSE in values:
        return TruthValue.FALSE
    if TruthValue.UNKNOWN in values:
        return TruthValue.UNKNOWN
    return TruthValue.TRUE


def tri_or(values: Sequence[TruthValue]) -> TruthValue:
    """Return Strong Kleene disjunction for a non-empty sequence."""
    if not values:
        raise ValueError("Strong Kleene any requires at least one value")
    if TruthValue.TRUE in values:
        return TruthValue.TRUE
    if TruthValue.UNKNOWN in values:
        return TruthValue.UNKNOWN
    return TruthValue.FALSE


def load_and_validate_ruleset(
    path: Path,
    vocabulary: Mapping[str, Any],
    obligation_catalog: Path = OBLIGATION_CATALOG_PATH,
) -> CompiledRuleset:
    """Load a strict AR-DSL JSON document and type-check it against pinned FV/catalog."""
    if path.is_symlink() or obligation_catalog.is_symlink():
        raise ContractValidationError("RULESET_INVALID: symlinked source files are forbidden")
    try:
        rule_bytes = path.read_bytes()
        catalog_bytes = obligation_catalog.read_bytes()
    except OSError as error:
        raise ContractValidationError(
            "RULESET_INVALID: ruleset or obligation catalog is missing"
        ) from error
    if len(rule_bytes) > MAX_RULESET_BYTES:
        raise ContractValidationError("RULESET_INVALID: ruleset exceeds the byte limit")
    try:
        raw = json.loads(rule_bytes)
        catalog_payload = yaml.safe_load(catalog_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ContractValidationError("RULESET_INVALID: malformed JSON/YAML source") from error
    if not isinstance(raw, Mapping) or not isinstance(catalog_payload, Mapping):
        raise ContractValidationError("RULESET_INVALID: ruleset/catalog root must be an object")
    try:
        validate_payload(RULESET_SCHEMA, dict(raw))
    except ContractValidationError as error:
        raise ContractValidationError(f"RULESET_INVALID: {error}") from error
    schema = _load_ruleset_schema()
    Draft202012Validator.check_schema(schema)

    catalog_rows = catalog_payload.get("obligations")
    if catalog_payload.get("schema_version") != 1 or not isinstance(catalog_rows, list):
        raise ContractValidationError("RULESET_INVALID: obligation catalog shape is unsupported")
    obligations: list[Obligation] = []
    seen_obligations: set[str] = set()
    for row in catalog_rows:
        if not isinstance(row, Mapping):
            raise ContractValidationError("RULESET_INVALID: malformed obligation catalog row")
        obligation_id, criterion = row.get("id"), row.get("criterion")
        if (
            not isinstance(obligation_id, str)
            or _ID_PATTERN.fullmatch(obligation_id) is None
            or not isinstance(criterion, str)
            or not criterion
            or obligation_id in seen_obligations
        ):
            raise ContractValidationError("RULESET_INVALID: obligation IDs/criteria are invalid")
        seen_obligations.add(obligation_id)
        obligations.append(Obligation(obligation_id, criterion))
    obligations.sort(key=lambda item: item.obligation_id)
    if not obligations:
        raise ContractValidationError("RULESET_INVALID: obligation catalog is empty")

    if vocabulary.get("vocabulary_version") != "FV_CORE_V1":
        raise ContractValidationError("RULEBOOK_VERSION_MISMATCH: expected FV_CORE_V1")
    descriptors_value = vocabulary.get("predicates")
    if not isinstance(descriptors_value, list) or len(descriptors_value) != 12:
        raise ContractValidationError(
            "RULEBOOK_VERSION_MISMATCH: FV_CORE_V1 must contain 12 predicates"
        )
    descriptors = {
        str(item.get("name")): dict(item)
        for item in descriptors_value
        if isinstance(item, Mapping) and isinstance(item.get("name"), str)
    }
    if len(descriptors) != 12:
        raise ContractValidationError(
            "RULEBOOK_VERSION_MISMATCH: FV predicate names are not unique"
        )
    if raw.get("fact_vocabulary_version") != vocabulary.get("vocabulary_version"):
        raise ContractValidationError("RULEBOOK_VERSION_MISMATCH: ruleset vocabulary differs")
    catalog_digest = sha256_bytes(catalog_bytes)
    if raw.get("obligation_catalog_sha256") != catalog_digest:
        raise ContractValidationError("RULESET_INVALID: obligation catalog digest differs")

    conditions_value = raw.get("conditions")
    if not isinstance(conditions_value, list) or len(conditions_value) > MAX_CONDITIONS:
        raise ContractValidationError("RULESET_INVALID: condition count exceeds the limit")
    conditions: dict[str, Mapping[str, Any]] = {}
    previous_id = ""
    normalized_conditions: list[dict[str, Any]] = []
    for condition in conditions_value:
        if not isinstance(condition, Mapping):
            raise ContractValidationError("RULESET_INVALID: condition must be an object")
        condition_id = condition.get("id")
        if not isinstance(condition_id, str) or condition_id in conditions:
            raise ContractValidationError("RULESET_INVALID: condition IDs must be unique strings")
        if condition_id <= previous_id:
            raise ContractValidationError("RULESET_INVALID: conditions must be sorted by ID")
        previous_id = condition_id
        expression = condition.get("expression")
        dependencies: set[str] = set()
        _validate_expression(expression, descriptors, 1, [0], dependencies)
        declared = condition.get("fact_dependencies")
        if not isinstance(declared, list) or declared != sorted(set(declared)):
            raise ContractValidationError(
                "RULESET_INVALID: fact_dependencies must be sorted and unique"
            )
        if set(str(item) for item in declared) != dependencies:
            raise ContractValidationError(
                f"RULESET_INVALID: declared dependencies differ for condition {condition_id}"
            )
        copied = dict(condition)
        conditions[condition_id] = copied
        normalized_conditions.append(copied)

    normalized = dict(raw)
    normalized["conditions"] = normalized_conditions
    ruleset_digest = sha256_bytes(canonical_json_bytes(normalized))
    return CompiledRuleset(
        ruleset_version=str(raw["ruleset_version"]),
        fact_vocabulary_version=str(raw["fact_vocabulary_version"]),
        obligation_catalog_sha256=catalog_digest,
        ruleset_sha256=ruleset_digest,
        ruleset_source_sha256=sha256_bytes(rule_bytes),
        conditions=conditions,
        predicate_descriptors=descriptors,
        obligations=tuple(obligations),
    )


def evaluate_condition(
    condition_id: str,
    state: str,
    snapshot: Mapping[str, Any],
    compiled_rules: CompiledRuleset,
    evidence_ledger: EvidenceLedger,
) -> ConditionResult:
    """Evaluate one condition with exact state/scope facts and externally verified evidence."""
    condition = compiled_rules.conditions.get(condition_id)
    if condition is None:
        return ConditionResult(
            condition_id,
            state,
            TruthValue.UNKNOWN,
            ("CONDITION_MISSING",),
            evidence_refs=(),
        )
    if state not in {"before", "after"}:
        raise ContractValidationError("INVALID_INPUT: architecture state must be before/after")
    facts = snapshot.get("facts")
    if not isinstance(facts, list) or len(facts) > MAX_FACT_ROWS:
        raise ContractValidationError("INVALID_INPUT: fact inventory exceeds supported bounds")
    evaluation = _evaluate_expression(
        cast(Mapping[str, Any], condition["expression"]),
        state,
        snapshot,
        compiled_rules,
        evidence_ledger,
    )
    reasons = set(evaluation[1])
    if "FACT_CONFLICT" in reasons or "INPUT_CONFLICT" in reasons:
        truth = TruthValue.UNKNOWN
    else:
        truth = evaluation[0]
    return ConditionResult(
        condition_id=condition_id,
        state=state,
        truth=truth,
        reason_codes=tuple(sorted(reasons)),
        fact_ids=tuple(sorted(evaluation[2])),
        evidence_refs=tuple(sorted(evaluation[3])),
    )


def _load_ruleset_schema() -> dict[str, Any]:
    from experiments.execution.tooling.contracts import load_schema

    return load_schema(RULESET_SCHEMA)


def _validate_expression(
    expression: Any,
    descriptors: Mapping[str, Mapping[str, Any]],
    depth: int,
    node_count: list[int],
    dependencies: set[str],
) -> None:
    if depth > MAX_AST_DEPTH:
        raise ContractValidationError("RULESET_INVALID: AST depth exceeds 12")
    node_count[0] += 1
    if node_count[0] > MAX_AST_NODES:
        raise ContractValidationError("RULESET_INVALID: AST node count exceeds 128")
    if not isinstance(expression, Mapping):
        raise ContractValidationError("RULESET_INVALID: AST node must be an object")
    op = expression.get("op")
    if op in {"all", "any"}:
        args = expression.get("args")
        if not isinstance(args, list) or not args:
            raise ContractValidationError("RULESET_INVALID: all/any require at least one child")
        for child in args:
            _validate_expression(child, descriptors, depth + 1, node_count, dependencies)
        return
    if op == "not":
        _validate_expression(
            expression.get("arg"), descriptors, depth + 1, node_count, dependencies
        )
        return
    if op not in {"compare", "set_size", "exists"}:
        raise ContractValidationError(f"RULESET_INVALID: unsupported operator {op!r}")
    selector = expression.get("selector")
    if not isinstance(selector, Mapping):
        raise ContractValidationError("RULESET_INVALID: selector must be an object")
    predicate = selector.get("predicate")
    descriptor = descriptors.get(str(predicate))
    if descriptor is None:
        raise ContractValidationError("PREDICATE_NOT_SUPPORTED: predicate is not in FV_CORE_V1")
    scope = selector.get("scope")
    if scope not in descriptor.get("allowed_scopes", []):
        raise ContractValidationError(
            "RULESET_INVALID: predicate/scope combination is not approved"
        )
    state = selector.get("state")
    allowed_states = descriptor.get("source_states", [])
    if state not in {"before", "after"} or (
        allowed_states != ["fact_state"] and state not in allowed_states
    ):
        raise ContractValidationError(
            "RULESET_INVALID: predicate/state combination is not approved"
        )
    value_type = descriptor.get("value_type")
    comparator = expression.get("comparator")
    if op == "compare":
        expected = expression.get("expected")
        if value_type == "nonnegative_integer":
            if type(expected) is not int:
                raise ContractValidationError(
                    "RULESET_INVALID: numeric comparison requires an integer"
                )
        elif value_type == "string":
            if comparator not in {"eq", "neq"} or not isinstance(expected, str):
                raise ContractValidationError("RULESET_INVALID: strings support eq/neq only")
        else:
            raise ContractValidationError(
                "RULESET_INVALID: compare is not defined for this FV type"
            )
    elif op == "set_size":
        if value_type != "string_set" or type(expression.get("expected")) is not int:
            raise ContractValidationError(
                "RULESET_INVALID: set_size requires a string_set predicate"
            )
    dependencies.add(str(predicate))


def _evaluate_expression(
    expression: Mapping[str, Any],
    target_state: str,
    snapshot: Mapping[str, Any],
    compiled_rules: CompiledRuleset,
    ledger: EvidenceLedger,
) -> tuple[TruthValue, set[str], set[str], set[str]]:
    op = expression.get("op")
    if op in {"all", "any"}:
        args = cast(list[Mapping[str, Any]], expression["args"])
        outcomes = [
            _evaluate_expression(child, target_state, snapshot, compiled_rules, ledger)
            for child in args
        ]
        truth_values = [outcome[0] for outcome in outcomes]
        truth = tri_and(truth_values) if op == "all" else tri_or(truth_values)
        return (
            truth,
            set().union(*(outcome[1] for outcome in outcomes)),
            set().union(*(outcome[2] for outcome in outcomes)),
            set().union(*(outcome[3] for outcome in outcomes)),
        )
    if op == "not":
        truth, reasons, fact_ids, refs = _evaluate_expression(
            cast(Mapping[str, Any], expression["arg"]),
            target_state,
            snapshot,
            compiled_rules,
            ledger,
        )
        return tri_not(truth), reasons, fact_ids, refs

    selector = cast(Mapping[str, Any], expression["selector"])
    if selector.get("state") != target_state:
        return (
            TruthValue.UNKNOWN,
            {"FACT_SCOPE_MISMATCH"},
            set(),
            set(),
        )
    selected, selection_reasons, fact_ids, refs = _resolve_selector(
        selector, str(op), snapshot, compiled_rules, ledger
    )
    if selected is None:
        if op == "exists" and "FACT_ABSENCE_PROVEN" in selection_reasons:
            return TruthValue.FALSE, selection_reasons, fact_ids, refs
        return TruthValue.UNKNOWN, selection_reasons, fact_ids, refs
    if op == "exists":
        return TruthValue.TRUE, selection_reasons, fact_ids, refs
    if op == "set_size":
        if not isinstance(selected, list) or any(not isinstance(item, str) for item in selected):
            return TruthValue.UNKNOWN, {"PREDICATE_NOT_SUPPORTED"}, fact_ids, refs
        actual: Any = len(selected)
    else:
        actual = selected
    expected = expression.get("expected")
    try:
        comparison = _compare(actual, expected, str(expression.get("comparator")))
    except (TypeError, ValueError):
        return TruthValue.UNKNOWN, {"PREDICATE_NOT_SUPPORTED"}, fact_ids, refs
    return (
        TruthValue.TRUE if comparison else TruthValue.FALSE,
        selection_reasons,
        fact_ids,
        refs,
    )


def _resolve_selector(
    selector: Mapping[str, Any],
    operation: str,
    snapshot: Mapping[str, Any],
    compiled_rules: CompiledRuleset,
    ledger: EvidenceLedger,
) -> tuple[Any | None, set[str], set[str], set[str]]:
    predicate = str(selector["predicate"])
    state = str(selector["state"])
    scope = str(selector["scope"])
    subject = selector.get("subject")
    facts_value = snapshot.get("facts")
    if not isinstance(facts_value, list):
        raise ContractValidationError("INVALID_INPUT: Snapshot fact inventory is malformed")
    all_rows = [row for row in facts_value if isinstance(row, Mapping)]
    matching = [
        row
        for row in all_rows
        if row.get("predicate") == predicate
        and row.get("state") == state
        and row.get("scope") == scope
        and (subject is None or row.get("subject") == subject)
    ]
    reasons: set[str] = set()
    fact_ids: set[str] = set()
    evidence_refs: set[str] = set()
    if not matching:
        near = [row for row in all_rows if row.get("predicate") == predicate]
        if near:
            reasons.add("FACT_SCOPE_MISMATCH")
        absence_proven, absence_refs = (
            _fact_absence_proof(selector, snapshot, ledger)
            if operation == "exists"
            else (False, set())
        )
        if absence_proven:
            reasons.add("FACT_ABSENCE_PROVEN")
            return None, reasons, fact_ids, absence_refs
        reasons.add("FACT_MISSING")
        reasons.add("NEGATIVE_EVIDENCE_INSUFFICIENT")
        return None, reasons, fact_ids, evidence_refs

    descriptor = compiled_rules.predicate_descriptors[predicate]
    if subject is None and operation in {"compare", "set_size"}:
        subjects = {str(row.get("subject")) for row in matching}
        if len(subjects) != 1:
            return None, {"FACT_SCOPE_MISMATCH", "FACT_CONFLICT"}, fact_ids, evidence_refs

    admissible: list[tuple[Mapping[str, Any], EvidenceProof]] = []
    for row in sorted(matching, key=lambda item: str(item.get("id", ""))):
        fact_id = row.get("id")
        if not isinstance(fact_id, str):
            reasons.add("FACT_UNVERIFIED")
            continue
        fact_ids.add(fact_id)
        epistemic_kind = row.get("epistemic_kind")
        if epistemic_kind == "UNKNOWN":
            reasons.add("FACT_MISSING")
            continue
        if epistemic_kind not in descriptor.get("allowed_epistemic_kinds", []):
            reasons.add("FACT_UNVERIFIED")
            continue
        if not _fact_value_matches_type(descriptor, row.get("value")):
            reasons.add("FACT_CONFLICT")
            continue
        proof = ledger.fact_proofs.get(fact_id)
        expected_sources = _source_bindings(snapshot, row.get("source_ids"))
        if len(expected_sources) != len(set(cast(list[str], row.get("source_ids", [])))):
            reasons.add("EVIDENCE_VERSION_MISMATCH")
            continue
        if proof is None:
            reasons.add("FACT_UNVERIFIED")
            continue
        if not _proof_matches(proof, row, expected_sources):
            reasons.add("EVIDENCE_VERSION_MISMATCH")
            continue
        if proof.status is ProofStatus.INVALID:
            reasons.add(
                "FACT_CONFLICT" if "FACT_CONFLICT" in proof.reason_codes else "FACT_UNVERIFIED"
            )
            continue
        if proof.status is ProofStatus.UNDETERMINED:
            reasons.add("FACT_UNVERIFIED")
            continue
        refs = set(_stable_refs(row.get("source_ids", [])))
        refs.update(proof.evidence_refs)
        evidence_refs.update(refs)
        admissible.append((row, proof))

    if operation == "exists":
        if admissible:
            return True, reasons, fact_ids, evidence_refs
        if not reasons:
            reasons.add("FACT_UNVERIFIED")
        return None, reasons, fact_ids, evidence_refs
    if not admissible:
        if not reasons:
            reasons.add("FACT_UNVERIFIED")
        return None, reasons, fact_ids, evidence_refs
    if operation != "exists" and reasons.intersection(
        {"FACT_MISSING", "FACT_UNVERIFIED", "EVIDENCE_VERSION_MISMATCH"}
    ):
        return None, reasons, fact_ids, evidence_refs

    values = [row.get("value") for row, _proof in admissible]
    value_type = str(descriptor.get("value_type"))
    if value_type in {"nonnegative_integer", "string"}:
        distinct = {canonical_json_bytes(value) for value in values}
        if len(distinct) > 1:
            reasons.add("FACT_CONFLICT")
            return None, reasons, fact_ids, evidence_refs
        return values[0], reasons, fact_ids, evidence_refs
    if len(admissible) != 1:
        reasons.add("FACT_CONFLICT")
        return None, reasons, fact_ids, evidence_refs
    return values[0], reasons, fact_ids, evidence_refs


def _fact_absence_proof(
    selector: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    ledger: EvidenceLedger,
) -> tuple[bool, set[str]]:
    architecture = snapshot.get("architecture")
    claims = snapshot.get("completeness_claims", [])
    if not isinstance(architecture, Mapping) or not isinstance(claims, list):
        return False, set()
    state = str(selector["state"])
    expected_revision = architecture.get("before_commit" if state == "before" else "after_commit")
    for claim in claims:
        if not isinstance(claim, Mapping):
            continue
        if (
            claim.get("kind") not in {"EXACT_ENUMERATION", "SOUND_OVERAPPROXIMATION"}
            or claim.get("state") != state
            or claim.get("fact_type") != selector.get("predicate")
            or claim.get("scope") != selector.get("scope")
            or claim.get("architecture_revision") != expected_revision
        ):
            continue
        claim_id = claim.get("id")
        proof = ledger.completeness_proofs.get(str(claim_id))
        expected_sources = _source_bindings(snapshot, claim.get("evidence_source_ids"))
        if not expected_sources or len(expected_sources) != len(
            set(cast(list[str], claim.get("evidence_source_ids", [])))
        ):
            continue
        if (
            proof
            and proof.status is ProofStatus.VALID
            and _proof_matches(proof, claim, expected_sources)
        ):
            refs = set(proof.evidence_refs)
            refs.update(_stable_refs(claim.get("evidence_source_ids", [])))
            refs.update(_stable_refs([str(claim_id)]))
            return True, refs
    return False, set()


def _compare(actual: Any, expected: Any, comparator: str) -> bool:
    if type(actual) is not type(expected):
        raise TypeError("typed values differ")
    if comparator == "eq":
        return bool(actual == expected)
    if comparator == "neq":
        return bool(actual != expected)
    if comparator == "lt":
        return bool(actual < expected)
    if comparator == "lte":
        return bool(actual <= expected)
    if comparator == "gt":
        return bool(actual > expected)
    if comparator == "gte":
        return bool(actual >= expected)
    raise ValueError("unsupported comparator")


def _fact_value_matches_type(descriptor: Mapping[str, Any], value: Any) -> bool:
    value_type = descriptor.get("value_type")
    if value_type == "nonnegative_integer":
        return type(value) is int and value >= 0
    if value_type == "string":
        return isinstance(value, str) and bool(value.strip())
    if value_type == "string_set":
        return (
            isinstance(value, list)
            and all(isinstance(item, str) and item for item in value)
            and value == sorted(value)
            and len(value) == len(set(value))
        )
    if value_type == "capability_module":
        return (
            isinstance(value, Mapping)
            and set(value) == {"name", "package"}
            and isinstance(value.get("name"), str)
            and isinstance(value.get("package"), str)
        )
    if value_type == "module_dependency":
        return (
            isinstance(value, Mapping)
            and set(value) == {"from", "to"}
            and isinstance(value.get("from"), str)
            and isinstance(value.get("to"), str)
        )
    return False


def _source_bindings(
    snapshot: Mapping[str, Any], source_ids_value: Any
) -> tuple[tuple[str, str], ...]:
    if not isinstance(source_ids_value, list):
        return ()
    sources_value = snapshot.get("sources")
    if not isinstance(sources_value, list):
        return ()
    sources = {
        str(source.get("id")): str(source.get("sha256"))
        for source in sources_value
        if isinstance(source, Mapping)
        and isinstance(source.get("id"), str)
        and isinstance(source.get("sha256"), str)
    }
    pairs = [
        (str(source_id), sources[str(source_id)])
        for source_id in source_ids_value
        if str(source_id) in sources
    ]
    return tuple(sorted(set(pairs)))


def _proof_matches(
    proof: EvidenceProof,
    subject: Mapping[str, Any],
    expected_sources: tuple[tuple[str, str], ...],
) -> bool:
    return (
        proof.subject_sha256 == sha256_bytes(canonical_json_bytes(subject))
        and proof.source_bindings == expected_sources
    )


def _stable_refs(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    return tuple(
        sorted(
            {
                str(value)
                for value in values
                if isinstance(value, str) and _SOURCE_REF_PATTERN.fullmatch(value)
            }
        )
    )


def evaluate_obligations(
    snapshot: Mapping[str, Any],
    compiled_rules: CompiledRuleset,
    evidence_ledger: EvidenceLedger,
    target_state: str,
    input_validation: SnapshotValidationResult,
    *,
    policy_source_revision: str = "snapshot-pinned",
    policy_bundle_sha256: str | None = None,
    target_scope: str | None = None,
) -> ApplicabilityAssessment:
    """Resolve normative applicability for every catalog obligation.

    Structural and source validation must be completed by SPEC 01 first. Per-object
    trust outcomes arrive as immutable ``EvidenceLedger`` entries; Snapshot data
    never self-asserts verifier status.
    """
    validate_snapshot_schema(snapshot)
    if input_validation.schema_status is ValidationStatus.INVALID:
        raise ContractValidationError("INVALID_INPUT: SPEC 01 rejected Snapshot schema")
    if input_validation.integrity_status is ValidationStatus.INVALID:
        raise ContractValidationError("INVALID_INPUT: SPEC 01 rejected Snapshot integrity")
    rejected_gates = {
        "authority": input_validation.authority_status,
        "facts": input_validation.fact_status,
        "completeness": input_validation.completeness_status,
    }
    invalid_gates = sorted(
        name for name, status in rejected_gates.items() if status is ValidationStatus.INVALID
    )
    if invalid_gates:
        raise ContractValidationError(
            "INVALID_INPUT: SPEC 01 rejected semantic gates: " + ", ".join(invalid_gates)
        )
    if snapshot.get("fact_vocabulary_version") != compiled_rules.fact_vocabulary_version:
        raise ContractValidationError("RULEBOOK_VERSION_MISMATCH: Snapshot vocabulary differs")
    if target_state not in {"before", "after"}:
        raise ContractValidationError("INVALID_INPUT: architecture state must be before/after")
    if policy_bundle_sha256 is not None and _SHA256_PATTERN.fullmatch(policy_bundle_sha256) is None:
        raise ContractValidationError("INVALID_INPUT: policy bundle digest is malformed")
    if not policy_source_revision or len(policy_source_revision) > 128:
        raise ContractValidationError("INVALID_INPUT: policy source revision is invalid")

    architecture = snapshot.get("architecture")
    registry = snapshot.get("policy_registry")
    policies_value = snapshot.get("policies")
    if not isinstance(architecture, Mapping) or not isinstance(registry, Mapping):
        raise ContractValidationError("INVALID_INPUT: Snapshot architecture/registry is malformed")
    if not isinstance(policies_value, list) or len(policies_value) > MAX_POLICY_ROWS:
        raise ContractValidationError("INVALID_INPUT: policy inventory exceeds supported bounds")
    facts_value = snapshot.get("facts")
    if not isinstance(facts_value, list) or len(facts_value) > MAX_FACT_ROWS:
        raise ContractValidationError("INVALID_INPUT: fact inventory exceeds supported bounds")
    claims = snapshot.get("completeness_claims", [])
    if not isinstance(claims, list) or len(claims) > MAX_COMPLETENESS_ROWS:
        raise ContractValidationError(
            "INVALID_INPUT: completeness inventory exceeds supported bounds"
        )
    evaluation_as_of = registry.get("as_of")
    if not isinstance(evaluation_as_of, str) or evaluation_as_of != architecture.get(
        "evaluation_as_of"
    ):
        raise ContractValidationError("INVALID_INPUT: policy and architecture as-of differ")
    registry_version = registry.get("registry_version")
    if not isinstance(registry_version, str) or not registry_version:
        raise ContractValidationError("INVALID_INPUT: policy registry version is missing")
    scope = target_scope or str(registry.get("scope", ""))
    if not scope:
        raise ContractValidationError("INVALID_INPUT: target policy scope is missing")

    policy_rows: dict[str, Mapping[str, Any]] = {}
    duplicate_policy_rows: dict[str, list[Mapping[str, Any]]] = {}
    for row in policies_value:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            continue
        policy_id = str(row["id"])
        if policy_id in policy_rows:
            duplicate_policy_rows.setdefault(policy_id, [policy_rows[policy_id]]).append(row)
        else:
            policy_rows[policy_id] = row
    duplicate_policy_obligations: dict[str, set[str]] = {}
    for policy_id, duplicate_rows in duplicate_policy_rows.items():
        for row in duplicate_rows:
            for obligation_id in _string_set(row.get("obligation_ids")):
                duplicate_policy_obligations.setdefault(obligation_id, set()).add(policy_id)

    results: list[ObligationResult] = []
    for obligation in compiled_rules.obligations:
        results.append(
            _evaluate_one_obligation(
                obligation,
                compiled_rules.obligation_catalog_sha256,
                snapshot,
                compiled_rules,
                evidence_ledger,
                input_validation,
                policy_rows,
                duplicate_policy_obligations,
                target_state,
                scope,
                evaluation_as_of,
            )
        )

    source_sha_key = "before_commit" if target_state == "before" else "after_commit"
    source_sha = architecture.get(source_sha_key)
    if not isinstance(source_sha, str) or re.fullmatch(r"[a-f0-9]{40}", source_sha) is None:
        raise ContractValidationError("INVALID_INPUT: architecture source revision is malformed")
    validation_summary = {
        "schema_status": input_validation.schema_status.value,
        "integrity_status": input_validation.integrity_status.value,
        "authority_status": input_validation.authority_status.value,
        "fact_status": input_validation.fact_status.value,
        "completeness_status": input_validation.completeness_status.value,
        "reason_codes": sorted(set(input_validation.reason_codes)),
    }
    return ApplicabilityAssessment(
        ruleset_version=compiled_rules.ruleset_version,
        fact_vocabulary_version=compiled_rules.fact_vocabulary_version,
        policy_registry_version=registry_version,
        policy_source_revision=policy_source_revision,
        policy_as_of=evaluation_as_of,
        architecture_source_sha=source_sha,
        architecture_state=target_state,
        common_input_sha256=_semantic_snapshot_sha256(snapshot),
        ruleset_sha256=compiled_rules.ruleset_sha256,
        policy_bundle_sha256=policy_bundle_sha256,
        input_validation=MappingProxyType(validation_summary),
        results=tuple(sorted(results, key=lambda item: item.obligation_id)),
    )


def _evaluate_one_obligation(
    obligation: Obligation,
    obligation_catalog_sha256: str,
    snapshot: Mapping[str, Any],
    compiled_rules: CompiledRuleset,
    ledger: EvidenceLedger,
    input_validation: SnapshotValidationResult,
    policy_rows: Mapping[str, Mapping[str, Any]],
    duplicate_policy_obligations: Mapping[str, set[str]],
    target_state: str,
    target_scope: str,
    evaluation_as_of: str,
) -> ObligationResult:
    q = obligation.obligation_id
    reasons: set[str] = set()
    policies_used: set[str] = set()
    condition_ids: set[str] = set()
    evidence_refs: set[str] = set()
    unresolved: set[str] = set()
    catalog_ids = {item.obligation_id for item in compiled_rules.obligations}
    if q not in catalog_ids:
        return _obligation_result(q, ApplicabilityStatus.UNKNOWN, {"UNKNOWN_OBLIGATION"})
    if input_validation.schema_status is not ValidationStatus.VALID:
        reasons.add("RULESET_INVALID")
        return _obligation_result(q, ApplicabilityStatus.UNKNOWN, reasons)

    registry = cast(Mapping[str, Any], snapshot["policy_registry"])
    charter_id = registry.get("authority_charter_source_id")
    registry_id = registry.get("source_id")
    authority_ok, authority_reasons, authority_refs = _shared_authority_status(
        snapshot, registry, ledger, str(charter_id), str(registry_id)
    )
    reasons.update(authority_reasons)
    evidence_refs.update(authority_refs)
    if not authority_ok:
        unresolved.update({f"registry:{registry_id}", f"charter:{charter_id}"})

    closure_ok, closure_reasons, closure_refs, closure_claim_id = _registry_closed_for(
        q,
        obligation.criterion,
        obligation_catalog_sha256,
        target_state,
        target_scope,
        snapshot,
        registry,
        ledger,
    )
    reasons.update(closure_reasons)
    evidence_refs.update(closure_refs)
    if not closure_ok:
        unresolved.add(f"registry:{registry_id}")
        if closure_claim_id:
            unresolved.add(f"claim:{closure_claim_id}")

    if q in duplicate_policy_obligations:
        reasons.add("INPUT_CONFLICT")
        unresolved.update(f"policy:{policy_id}" for policy_id in duplicate_policy_obligations[q])
        return _obligation_result(
            q,
            ApplicabilityStatus.UNKNOWN,
            reasons,
            policies_used,
            condition_ids,
            evidence_refs,
            unresolved,
        )

    mandates: list[tuple[Mapping[str, Any], TruthValue]] = []
    unresolved_mandate = False
    for policy_id, policy in sorted(policy_rows.items()):
        if q not in _string_set(policy.get("obligation_ids")):
            continue
        kind = policy.get("kind")
        status = policy.get("normative_status")
        if kind not in {"UNCONDITIONAL_MANDATE", "CONDITIONAL_MANDATE"}:
            continue
        if status == "DRAFT":
            continue
        if status not in {"APPROVED", "REVOKED", "SUPERSEDED"}:
            reasons.add("POLICY_APPROVAL_UNVERIFIED")
            unresolved.add(f"policy:{policy_id}")
            unresolved_mandate = True
            continue
        if target_state not in _string_set(policy.get("applies_to_states")):
            continue
        proof_status, proof_reasons, proof_refs = _policy_proof_status(
            snapshot, registry, ledger, policy, str(charter_id), str(registry_id)
        )
        reasons.update(proof_reasons)
        evidence_refs.update(proof_refs)
        if proof_status is not ProofStatus.VALID:
            unresolved.add(f"policy:{policy_id}")
            unresolved_mandate = True
            continue
        if status in {"REVOKED", "SUPERSEDED"}:
            continue
        if not _policy_effective_at(policy, evaluation_as_of):
            continue
        if policy.get("scope") != target_scope:
            reasons.add("AUTHORITY_SCOPE_MISMATCH")
            unresolved.add(f"policy:{policy_id}")
            unresolved_mandate = True
            continue
        trigger = _policy_trigger(
            policy,
            target_state,
            snapshot,
            compiled_rules,
            ledger,
            reasons,
            condition_ids,
            evidence_refs,
            unresolved,
        )
        if trigger is None:
            unresolved_mandate = True
            continue
        if trigger[0] is TruthValue.UNKNOWN:
            unresolved_mandate = True
        mandates.append((policy, trigger[0]))

    # A valid exception/retirement suppresses only a named, verified target policy.
    suppressed: set[str] = set()
    unresolved_overrides: set[str] = set()
    for mandate, mandate_truth in mandates:
        if mandate_truth is TruthValue.FALSE:
            continue
        mandate_id = str(mandate.get("id"))
        for override_id, override in sorted(policy_rows.items()):
            if override.get("kind") not in {"EXCEPTION", "RETIREMENT"}:
                continue
            if mandate_id not in _string_set(override.get("target_policy_ids")):
                continue
            if override.get("normative_status") == "DRAFT":
                continue
            if override.get("normative_status") in {"REVOKED", "SUPERSEDED"}:
                override_status, override_reasons, _override_refs = _policy_proof_status(
                    snapshot, registry, ledger, override, str(charter_id), str(registry_id)
                )
                if override_status is not ProofStatus.VALID:
                    reasons.update(override_reasons or {"POLICY_APPROVAL_UNVERIFIED"})
                    unresolved.add(f"policy:{override_id}")
                    unresolved_overrides.add(mandate_id)
                continue
            override_status, override_reasons, override_refs = _policy_proof_status(
                snapshot, registry, ledger, override, str(charter_id), str(registry_id)
            )
            if (
                override_status is ProofStatus.INVALID
                and "POLICY_ISSUER_UNAUTHORIZED" in override_reasons
            ):
                reasons.add("POLICY_APPROVAL_UNVERIFIED")
                continue
            if override_status is not ProofStatus.VALID:
                reasons.update(override_reasons or {"POLICY_APPROVAL_UNVERIFIED"})
                unresolved.add(f"policy:{override_id}")
                unresolved_overrides.add(mandate_id)
                continue
            evidence_refs.update(override_refs)
            if target_state not in _string_set(override.get("applies_to_states")):
                continue
            if not _policy_effective_at(override, evaluation_as_of):
                continue
            if override.get("scope") != target_scope:
                reasons.add("AUTHORITY_SCOPE_MISMATCH")
                unresolved.add(f"policy:{override_id}")
                unresolved_overrides.add(mandate_id)
                continue
            override_trigger = _policy_trigger(
                override,
                target_state,
                snapshot,
                compiled_rules,
                ledger,
                reasons,
                condition_ids,
                evidence_refs,
                unresolved,
                unconditional_when_missing=True,
            )
            if override_trigger is None or override_trigger[0] is TruthValue.UNKNOWN:
                unresolved_overrides.add(mandate_id)
                reasons.add("OVERRIDE_UNRESOLVED")
                continue
            if override_trigger[0] is TruthValue.FALSE:
                continue
            pair = (override_id, mandate_id)
            pair_proof = (ledger.authorized_overrides or {}).get(pair)
            pair_subject = _override_binding(override, mandate)
            pair_sources = _combined_policy_bindings(snapshot, override, mandate)
            if pair_proof is None or not _proof_matches(pair_proof, pair_subject, pair_sources):
                reasons.add("OVERRIDE_UNRESOLVED")
                unresolved.add(f"override:{override_id}:{mandate_id}")
                unresolved_overrides.add(mandate_id)
            elif pair_proof.status is ProofStatus.VALID:
                suppressed.add(mandate_id)
                evidence_refs.update(pair_proof.evidence_refs)
            elif (
                pair_proof.status is ProofStatus.INVALID
                and "OVERRIDE_UNAUTHORIZED" in pair_proof.reason_codes
            ):
                reasons.add("POLICY_APPROVAL_UNVERIFIED")
                evidence_refs.update(pair_proof.evidence_refs)
            else:
                reasons.add("OVERRIDE_UNRESOLVED")
                unresolved.add(f"override:{override_id}:{mandate_id}")
                unresolved_overrides.add(mandate_id)

    effective = [
        policy
        for policy, trigger in mandates
        if trigger is TruthValue.TRUE
        and str(policy.get("id")) not in suppressed
        and str(policy.get("id")) not in unresolved_overrides
    ]
    effective, conflict, precedence_reasons, precedence_refs = _resolve_policy_conflicts(
        effective, snapshot, ledger, target_scope
    )
    reasons.update(precedence_reasons)
    evidence_refs.update(precedence_refs)
    if conflict:
        reasons.add("POLICY_CONFLICT")
        unresolved.update(f"policy:{policy.get('id')}" for policy in effective)
        return _obligation_result(
            q,
            ApplicabilityStatus.UNKNOWN,
            reasons,
            policies_used,
            condition_ids,
            evidence_refs,
            unresolved,
        )

    if not closure_ok:
        if registry.get("closure") == "OPEN":
            reasons.add("POLICY_REGISTRY_OPEN")
            if effective:
                reasons.add("OVERRIDE_UNRESOLVED")
        else:
            reasons.add("POLICY_CLOSURE_UNVERIFIED")
        return _obligation_result(
            q,
            ApplicabilityStatus.UNKNOWN,
            reasons,
            policies_used,
            condition_ids,
            evidence_refs,
            unresolved,
        )
    if not authority_ok:
        return _obligation_result(
            q,
            ApplicabilityStatus.UNKNOWN,
            reasons,
            policies_used,
            condition_ids,
            evidence_refs,
            unresolved,
        )
    unknown_condition = any(
        trigger is TruthValue.UNKNOWN and str(policy.get("id")) not in suppressed
        for policy, trigger in mandates
    )
    if unknown_condition:
        reasons.add("CONDITION_UNKNOWN")
    if effective:
        policies_used.update(str(policy.get("id")) for policy in effective)
        reasons.add("APPLICABILITY_ACTIVE_PROVEN")
        return _obligation_result(
            q,
            ApplicabilityStatus.ACTIVE,
            reasons,
            policies_used,
            condition_ids,
            evidence_refs,
            unresolved,
        )
    if unresolved_mandate or unresolved_overrides or unknown_condition:
        return _obligation_result(
            q,
            ApplicabilityStatus.UNKNOWN,
            reasons,
            policies_used,
            condition_ids,
            evidence_refs,
            unresolved,
        )
    reasons.add("NO_APPLICABLE_POLICY_PROVEN")
    reasons.add("APPLICABILITY_INACTIVE_PROVEN")
    return _obligation_result(
        q,
        ApplicabilityStatus.INACTIVE,
        reasons,
        policies_used,
        condition_ids,
        evidence_refs,
        unresolved,
    )


def _shared_authority_status(
    snapshot: Mapping[str, Any],
    registry: Mapping[str, Any],
    ledger: EvidenceLedger,
    charter_id: str,
    registry_id: str,
) -> tuple[bool, set[str], set[str]]:
    reasons: set[str] = set()
    refs: set[str] = set()
    registry_proof = ledger.registry_proof
    registry_sources = _source_bindings(snapshot, [registry_id])
    if (
        len(registry_sources) != 1
        or registry_proof is None
        or not _proof_matches(registry_proof, registry, registry_sources)
    ):
        reasons.add("POLICY_AUTHORITY_UNVERIFIED")
    elif registry_proof.status is ProofStatus.VALID:
        refs.update(registry_proof.evidence_refs)
        refs.update(_stable_refs([registry_id]))
    else:
        reasons.add("POLICY_AUTHORITY_UNVERIFIED")
        if registry_proof.status is ProofStatus.INVALID:
            reasons.add("INPUT_CONFLICT")

    charter_source_digest = dict(_source_bindings(snapshot, [charter_id])).get(charter_id)
    charter_proof = ledger.charter_proof
    charter_subject = {"source_id": charter_id, "sha256": charter_source_digest}
    charter_sources = _source_bindings(snapshot, [charter_id])
    if (
        charter_source_digest is None
        or charter_proof is None
        or not _proof_matches(charter_proof, charter_subject, charter_sources)
        or charter_proof.status is not ProofStatus.VALID
    ):
        reasons.add("POLICY_AUTHORITY_UNVERIFIED")
        if charter_proof is not None and charter_proof.status is ProofStatus.INVALID:
            reasons.add("INPUT_CONFLICT")
    else:
        refs.update(charter_proof.evidence_refs)
        refs.update(_stable_refs([charter_id]))
    return not reasons, reasons, refs


def _registry_closed_for(
    obligation_id: str,
    criterion: str,
    obligation_catalog_sha256: str,
    target_state: str,
    target_scope: str,
    snapshot: Mapping[str, Any],
    registry: Mapping[str, Any],
    ledger: EvidenceLedger,
) -> tuple[bool, set[str], set[str], str | None]:
    reasons: set[str] = set()
    refs: set[str] = set()
    if registry.get("closure") == "OPEN":
        return False, {"POLICY_REGISTRY_OPEN"}, refs, None
    if registry.get("closure") != "CLAIMED_CLOSED":
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, None
    claim_id = registry.get("closure_claim_id")
    if not isinstance(claim_id, str):
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, None
    claims = snapshot.get("completeness_claims", [])
    architecture = snapshot.get("architecture", {})
    if not isinstance(claims, list) or not isinstance(architecture, Mapping):
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, claim_id
    expected_revision = architecture.get(
        "before_commit" if target_state == "before" else "after_commit"
    )
    expected_as_of = registry.get("as_of")
    matching = [
        claim for claim in claims if isinstance(claim, Mapping) and claim.get("id") == claim_id
    ]
    if len(matching) != 1:
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, claim_id
    claim = matching[0]
    expected_scope = target_scope
    assumptions = claim.get("assumptions", [])
    universal_marker = f"obligation_catalog_sha256:{obligation_catalog_sha256}"
    claim_type_matches = claim.get("fact_type") in {
        f"obligation:{obligation_id}",
        f"obligation_family:{criterion}",
    } or (
        claim.get("fact_type") == "obligation:all"
        and isinstance(assumptions, list)
        and universal_marker in assumptions
    )
    if (
        claim.get("kind") != "AUTHORITATIVE_POLICY_REGISTRY"
        or not claim_type_matches
        or claim.get("state") != target_state
        or claim.get("scope") != expected_scope
        or claim.get("architecture_revision") != expected_revision
        or claim.get("policy_registry_version") != registry.get("registry_version")
        or claim.get("as_of") != expected_as_of
        or expected_as_of != snapshot.get("architecture", {}).get("evaluation_as_of")
        or registry.get("scope") != target_scope
    ):
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, claim_id
    proof = ledger.completeness_proofs.get(claim_id)
    expected_sources = _source_bindings(snapshot, claim.get("evidence_source_ids"))
    expected_source_ids = claim.get("evidence_source_ids")
    if (
        not isinstance(expected_source_ids, list)
        or not expected_sources
        or len(expected_sources) != len(set(expected_source_ids))
        or proof is None
        or not _proof_matches(proof, claim, expected_sources)
    ):
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, claim_id
    if proof.status is not ProofStatus.VALID:
        reasons.add("POLICY_CLOSURE_UNVERIFIED")
        if proof.status is ProofStatus.INVALID:
            reasons.add("INPUT_CONFLICT")
        return False, reasons, refs, claim_id
    refs.update(proof.evidence_refs)
    refs.update(_stable_refs(claim.get("evidence_source_ids", [])))
    refs.add(claim_id)
    return True, reasons, refs, claim_id


def _policy_proof_status(
    snapshot: Mapping[str, Any],
    registry: Mapping[str, Any],
    ledger: EvidenceLedger,
    policy: Mapping[str, Any],
    charter_id: str,
    registry_id: str,
) -> tuple[ProofStatus, set[str], set[str]]:
    policy_id = str(policy.get("id", ""))
    proof = ledger.policy_proofs.get(policy_id)
    approval_id = policy.get("approval_source_id")
    if not isinstance(approval_id, str):
        return ProofStatus.UNDETERMINED, {"POLICY_APPROVAL_UNVERIFIED"}, set()
    expected_sources = _source_bindings(snapshot, [registry_id, approval_id, charter_id])
    if len(expected_sources) != 3 or proof is None:
        return ProofStatus.UNDETERMINED, {"POLICY_APPROVAL_UNVERIFIED"}, set()
    if not _proof_matches(proof, policy, expected_sources):
        return ProofStatus.UNDETERMINED, {"EVIDENCE_VERSION_MISMATCH"}, set()
    if proof.status is ProofStatus.INVALID:
        return (
            proof.status,
            set(proof.reason_codes or ("POLICY_APPROVAL_UNVERIFIED",)),
            set(proof.evidence_refs),
        )
    if proof.status is ProofStatus.UNDETERMINED:
        return proof.status, set(proof.reason_codes or ("POLICY_APPROVAL_UNVERIFIED",)), set()
    # A valid policy proof is useful only when the authority chain is also valid.
    authority_ok, authority_reasons, authority_refs = _shared_authority_status(
        snapshot, registry, ledger, charter_id, registry_id
    )
    if not authority_ok:
        return ProofStatus.UNDETERMINED, authority_reasons, authority_refs
    return (
        ProofStatus.VALID,
        set(),
        set(proof.evidence_refs) | authority_refs | {policy_id, approval_id},
    )


def _policy_trigger(
    policy: Mapping[str, Any],
    target_state: str,
    snapshot: Mapping[str, Any],
    compiled_rules: CompiledRuleset,
    ledger: EvidenceLedger,
    reasons: set[str],
    condition_ids: set[str],
    evidence_refs: set[str],
    unresolved: set[str],
    *,
    unconditional_when_missing: bool = False,
) -> tuple[TruthValue, ConditionResult | None] | None:
    kind = policy.get("kind")
    if kind == "UNCONDITIONAL_MANDATE" or (
        unconditional_when_missing and policy.get("condition_ref") is None
    ):
        return TruthValue.TRUE, None
    condition_id = policy.get("condition_ref")
    if kind != "CONDITIONAL_MANDATE" and condition_id is None:
        return TruthValue.TRUE, None
    if not isinstance(condition_id, str):
        reasons.add("CONDITION_MISSING")
        unresolved.add(f"policy:{policy.get('id')}")
        return None
    condition_ids.add(condition_id)
    result = evaluate_condition(condition_id, target_state, snapshot, compiled_rules, ledger)
    reasons.update(result.reason_codes)
    evidence_refs.update(result.evidence_refs)
    unresolved.update(
        f"fact:{fact_id}" for fact_id in result.fact_ids if result.truth is TruthValue.UNKNOWN
    )
    if result.truth is TruthValue.UNKNOWN:
        reasons.add("CONDITION_UNKNOWN")
        unresolved.add(f"condition:{condition_id}")
    return result.truth, result


def _resolve_policy_conflicts(
    policies: list[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
    ledger: EvidenceLedger,
    scope: str,
) -> tuple[list[Mapping[str, Any]], bool, set[str], set[str]]:
    dominated: set[str] = set()
    reasons: set[str] = set()
    refs: set[str] = set()
    conflict = False
    for index, left in enumerate(policies):
        for right in policies[index + 1 :]:
            if left.get("scope") != scope or right.get("scope") != scope:
                continue
            left_polarity = left.get("proposition_polarity", "REQUIRED")
            right_polarity = right.get("proposition_polarity", "REQUIRED")
            if left_polarity == right_polarity:
                continue
            left_id, right_id = str(left.get("id")), str(right.get("id"))
            left_over_right = _precedence_proof(snapshot, ledger, left, right)
            right_over_left = _precedence_proof(snapshot, ledger, right, left)
            left_dominates = (
                left_over_right is not None and left_over_right.status is ProofStatus.VALID
            )
            right_dominates = (
                right_over_left is not None and right_over_left.status is ProofStatus.VALID
            )
            if left_dominates and not right_dominates:
                dominated.add(right_id)
                if left_over_right is not None:
                    refs.update(left_over_right.evidence_refs)
            elif right_dominates and not left_dominates:
                dominated.add(left_id)
                if right_over_left is not None:
                    refs.update(right_over_left.evidence_refs)
            else:
                conflict = True
                reasons.add("POLICY_CONFLICT")
                reasons.add("INPUT_CONFLICT")
                refs.update({left_id, right_id})
    return (
        [policy for policy in policies if str(policy.get("id")) not in dominated],
        conflict,
        reasons,
        refs,
    )


def _precedence_proof(
    snapshot: Mapping[str, Any],
    ledger: EvidenceLedger,
    higher: Mapping[str, Any],
    lower: Mapping[str, Any],
) -> EvidenceProof | None:
    high_id, low_id = str(higher.get("id")), str(lower.get("id"))
    proof = (ledger.policy_precedence or {}).get((high_id, low_id))
    if proof is None:
        return None
    subject = {"higher_policy_id": high_id, "lower_policy_id": low_id}
    sources = _combined_policy_bindings(snapshot, higher, lower)
    if not _proof_matches(proof, subject, sources):
        return None
    return proof


def _override_binding(override: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, str]:
    return {
        "override_policy_id": str(override.get("id")),
        "target_policy_id": str(target.get("id")),
        "override_policy_sha256": sha256_bytes(canonical_json_bytes(override)),
        "target_policy_sha256": sha256_bytes(canonical_json_bytes(target)),
    }


def _combined_policy_bindings(
    snapshot: Mapping[str, Any], first: Mapping[str, Any], second: Mapping[str, Any]
) -> tuple[tuple[str, str], ...]:
    ids = {
        str(first.get("source_id")),
        str(first.get("approval_source_id")),
        str(second.get("source_id")),
        str(second.get("approval_source_id")),
        str(snapshot.get("policy_registry", {}).get("authority_charter_source_id", "")),
    }
    return _source_bindings(snapshot, sorted(ids))


def _policy_effective_at(policy: Mapping[str, Any], evaluation_as_of: str) -> bool:
    try:
        current = _parse_datetime(evaluation_as_of)
        start = _parse_datetime(str(policy.get("effective_from")))
        until_value = policy.get("effective_until")
        until = _parse_datetime(str(until_value)) if until_value is not None else None
    except ValueError:
        return False
    return start <= current and (until is None or current < until)


def _parse_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def _obligation_result(
    obligation_id: str,
    status: ApplicabilityStatus,
    reasons: set[str],
    policy_ids: set[str] | None = None,
    condition_ids: set[str] | None = None,
    evidence_refs: set[str] | None = None,
    unresolved_refs: set[str] | None = None,
) -> ObligationResult:
    return ObligationResult(
        obligation_id=obligation_id,
        status=status,
        reason_codes=tuple(sorted(reasons)),
        contributing_policy_ids=tuple(sorted(policy_ids or set())),
        condition_ids=tuple(sorted(condition_ids or set())),
        evidence_refs=tuple(sorted(evidence_refs or set())),
        unresolved_refs=tuple(sorted(unresolved_refs or set())),
    )


def _semantic_snapshot_sha256(snapshot: Mapping[str, Any]) -> str:
    """Hash normalized common data, independent of JSON keys and row ordering."""
    normalized = dict(snapshot)
    for key in ("sources", "facts", "policies", "completeness_claims"):
        rows = snapshot.get(key)
        if isinstance(rows, list):
            copied = [dict(row) for row in rows if isinstance(row, Mapping)]
            if key == "policies":
                for row in copied:
                    for field_name in ("obligation_ids", "target_policy_ids", "applies_to_states"):
                        if isinstance(row.get(field_name), list):
                            row[field_name] = sorted(row[field_name])
            elif key == "facts":
                for row in copied:
                    if isinstance(row.get("source_ids"), list):
                        row["source_ids"] = sorted(row["source_ids"])
            elif key == "sources":
                copied.sort(key=lambda row: str(row.get("id", "")))
            else:
                for row in copied:
                    if isinstance(row.get("evidence_source_ids"), list):
                        row["evidence_source_ids"] = sorted(row["evidence_source_ids"])
            if key != "sources":
                copied.sort(key=lambda row: str(row.get("id", "")))
            normalized[key] = copied
    return sha256_bytes(canonical_json_bytes(normalized))


def canonical_assessment_bytes(assessment: ApplicabilityAssessment) -> bytes:
    """Return deterministic UTF-8 bytes for the diagnostic artifact."""
    return canonical_json_bytes(assessment.to_dict())
