"""Deterministic, evidence-gated operation planning for development Method P."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_impact import ImpactAssessment, ImpactStatus
from experiments.execution.tooling.p_semantic import CoverageAssessment, PairAssessment, PairStatus

_SAFE_PATH = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9_./-]+$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class OperationKind(StrEnum):
    """Supported configuration operations; none edits application architecture."""

    RETAIN = "retain"
    REPLACE = "replace"
    ADD = "add"
    DEACTIVATE = "deactivate"
    ADJUST = "adjust"


@dataclass(frozen=True)
class PlannedOperation:
    """One typed operation and any exact materialization payload it requires."""

    target_type: str
    target_id: str
    operation: OperationKind
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    payload: Mapping[str, Any] | None = None
    artifact_sha256: str | None = None
    incremental_cost: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "operation": self.operation.value,
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
            "payload": dict(self.payload) if self.payload is not None else None,
            "artifact_sha256": self.artifact_sha256,
            "incremental_cost": self.incremental_cost,
        }


@dataclass(frozen=True)
class OperationPlan:
    """Stable operation set plus blockers and proven candidate failures."""

    operations: tuple[PlannedOperation, ...]
    hold_reasons: tuple[str, ...]
    reject_reasons: tuple[str, ...]
    plan_sha256: str

    @property
    def ready(self) -> bool:
        return not self.hold_reasons and not self.reject_reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "operations": [operation.to_dict() for operation in self.operations],
            "hold_reasons": list(self.hold_reasons),
            "reject_reasons": list(self.reject_reasons),
            "plan_sha256": self.plan_sha256,
        }


def validate_materializable_template(
    template: Mapping[str, Any],
    *,
    artifact_bytes: Mapping[str, bytes],
    authorized_artifact_digests: frozenset[str] = frozenset(),
) -> tuple[Mapping[str, Any] | None, str | None, str | None]:
    """Return a template only when signed authority evidence binds its artifact."""
    representation = template.get("representation")
    if not isinstance(representation, Mapping):
        return None, None, "TEMPLATE_REPRESENTATION_MISSING"
    artifact = representation.get("evaluator_artifact")
    if not isinstance(artifact, Mapping):
        return None, None, "TEMPLATE_ARTIFACT_MISSING"
    digest = artifact.get("sha256")
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        return None, None, "TEMPLATE_ARTIFACT_DIGEST_INVALID"
    if digest not in authorized_artifact_digests:
        return None, None, "TEMPLATE_AUTHORITY_UNVERIFIED"
    path, digest = artifact.get("path"), artifact.get("sha256")
    if not isinstance(path, str) or _SAFE_PATH.fullmatch(path) is None:
        return None, None, "TEMPLATE_ARTIFACT_PATH_INVALID"
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        return None, None, "TEMPLATE_ARTIFACT_DIGEST_INVALID"
    content = artifact_bytes.get(path)
    if content is None:
        return None, None, "TEMPLATE_ARTIFACT_BYTES_MISSING"
    if sha256_bytes(content) != digest:
        return None, None, "TEMPLATE_ARTIFACT_DIGEST_MISMATCH"
    if not _valid_representation(representation):
        return None, None, "TEMPLATE_REPRESENTATION_INVALID"
    allowed = {
        "id",
        "active",
        "criterion",
        "stage",
        "evaluator",
        "evaluator_artifact",
        "covers",
        "applicability_scope",
        "evidence_contract",
        "soft_parameters",
    }
    normalized = {key: value for key, value in representation.items() if key in allowed}
    return normalized, digest, None


def build_operation_plan(
    *,
    representations: Sequence[Mapping[str, Any]],
    obligations: Sequence[Mapping[str, Any]],
    applicability: Mapping[str, str],
    pair_assessments: Sequence[PairAssessment],
    coverage: CoverageAssessment,
    impact: ImpactAssessment,
    templates: Sequence[Mapping[str, Any]] = (),
    artifact_bytes: Mapping[str, bytes] | None = None,
    authorized_artifact_digests: frozenset[str] = frozenset(),
    adjustment_rules: Sequence[Mapping[str, Any]] = (),
    cost_model: Mapping[str, Any] | None = None,
    cost_model_authorized: bool = False,
    adjustments_authorized: bool = False,
) -> OperationPlan:
    """Plan justified edits without converting unknown evidence to inactivity.

    Template labels are never authority. A digest becomes admissible only
    after the caller verifies a signed, input-bound authority sidecar. The
    planner never authors evaluator code.
    """
    by_obligation = {_required_id(row.get("id"), "obligation"): row for row in obligations}
    if len(by_obligation) != len(obligations):
        raise ContractValidationError("P03_DUPLICATE_OBLIGATION")
    by_representation = {
        _required_id(row.get("id"), "representation"): row for row in representations
    }
    if len(by_representation) != len(representations):
        raise ContractValidationError("P03_DUPLICATE_REPRESENTATION")
    if impact.architecture_after_sha != coverage.architecture_source_sha:
        raise ContractValidationError("P03_IMPACT_COVERAGE_REVISION_MISMATCH")
    if not _impact_digest_is_valid(impact):
        raise ContractValidationError("P03_IMPACT_ASSESSMENT_DIGEST_MISMATCH")
    impact_by_representation = {row.representation_id: row for row in impact.representations}
    if len(impact_by_representation) != len(impact.representations):
        raise ContractValidationError("P03_DUPLICATE_IMPACT_REPRESENTATION")
    representation_ids = set(by_representation)
    if set(impact_by_representation) != representation_ids:
        raise ContractValidationError("P03_IMPACT_REPRESENTATION_SET_MISMATCH")
    pair_index: dict[tuple[str, str], list[PairAssessment]] = {}
    unverified_pairs: set[tuple[str, str]] = set()
    for pair in pair_assessments:
        key = (pair.representation_id, pair.obligation_id)
        if (
            pair.architecture_source_sha != coverage.architecture_source_sha
            or not _pair_digest_is_valid(pair)
        ):
            unverified_pairs.add(key)
        pair_index.setdefault(key, []).append(pair)
    conflicted_pairs = {
        key
        for key, assessments in pair_index.items()
        if len({pair.status for pair in assessments}) > 1
        or len({pair.assessment_sha256 for pair in assessments}) > 1
    }
    coverage_by_id = {row.obligation_id: row for row in coverage.obligations}
    bytes_by_path = artifact_bytes or {}
    usable_templates: list[tuple[Mapping[str, Any], str]] = []
    unusable_template_reasons: set[str] = set()
    hold: set[str] = set()
    reject: set[str] = set()
    for template in templates:
        representation, digest, issue = validate_materializable_template(
            template,
            artifact_bytes=bytes_by_path,
            authorized_artifact_digests=authorized_artifact_digests,
        )
        if issue is not None:
            unusable_template_reasons.add(issue)
        elif representation is not None and digest is not None:
            usable_templates.append((representation, digest))
    usable_templates.sort(key=lambda item: (str(item[0].get("id")), item[1]))
    template_ids = [str(item[0].get("id")) for item in usable_templates]
    if len(template_ids) != len(set(template_ids)):
        reject.add("DUPLICATE_TEMPLATE_REPRESENTATION_ID")

    operations: list[PlannedOperation] = []
    planned_covered: set[str] = set()
    active_mandatory: set[str] = set()
    unknown_mandatory: set[str] = set()
    inactive: set[str] = set()
    for obligation_id, obligation in by_obligation.items():
        mandatory = obligation.get("mandatory")
        status = applicability.get(obligation_id, "UNKNOWN")
        if status not in {"ACTIVE", "INACTIVE", "UNKNOWN"}:
            reject.add("APPLICABILITY_STATUS_INVALID")
        elif status == "UNKNOWN":
            if mandatory is not False:
                unknown_mandatory.add(obligation_id)
        elif status == "ACTIVE" and mandatory is True:
            active_mandatory.add(obligation_id)
        elif status == "INACTIVE":
            inactive.add(obligation_id)
        if not isinstance(mandatory, bool):
            unknown_mandatory.add(obligation_id)
    if unknown_mandatory:
        hold.add("MANDATORY_APPLICABILITY_UNKNOWN")

    # Existing representations can be retained only on positive exact-pair
    # evidence when they participate in an active mandatory control.
    for representation_id, representation in sorted(by_representation.items()):
        if representation.get("active") is False:
            continue
        covers = _string_set(representation.get("covers"))
        linked = covers & (active_mandatory | unknown_mandatory)
        impact_record = impact_by_representation.get(representation_id)
        impact_status = (
            impact_record.status if impact_record is not None else ImpactStatus.UNRESOLVED
        )
        if not linked:
            active_links = covers & {
                obligation_id
                for obligation_id, status in applicability.items()
                if status == "ACTIVE"
            }
            if impact_status is ImpactStatus.UNRESOLVED:
                hold.add("REPRESENTATION_IMPACT_UNRESOLVED")
                continue
            if impact_status in {
                ImpactStatus.PROVEN_AFFECTED,
                ImpactStatus.POSSIBLY_AFFECTED,
            } and (
                not active_links
                or any(
                    not any(
                        pair.status is PairStatus.VALID
                        and pair.architecture_source_sha == impact.architecture_after_sha
                        for pair in pair_index.get((representation_id, obligation_id), ())
                    )
                    for obligation_id in active_links
                )
            ):
                hold.add("IMPACTED_RETAIN_REASSESSMENT_MISSING")
                continue
            if covers and covers.issubset(inactive):
                operations.append(
                    PlannedOperation(
                        "representation",
                        representation_id,
                        OperationKind.DEACTIVATE,
                        ("ALL_LINKED_OBLIGATIONS_VERIFIED_INACTIVE",),
                    )
                )
            else:
                operations.append(
                    PlannedOperation(
                        "representation",
                        representation_id,
                        OperationKind.RETAIN,
                        ("NO_ACTIVE_MANDATORY_LINK_REQUIRES_CHANGE",),
                    )
                )
            continue
        if linked & unknown_mandatory:
            hold.add("UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION")
            continue
        if impact_status is ImpactStatus.UNRESOLVED:
            hold.add("MANDATORY_IMPACT_UNRESOLVED")
            continue
        unresolved_pairs = {
            obligation_id
            for obligation_id in linked
            if (representation_id, obligation_id) not in unverified_pairs
            and (representation_id, obligation_id) not in conflicted_pairs
            and not any(
                pair.status is PairStatus.VALID
                for pair in pair_index.get((representation_id, obligation_id), ())
            )
            and not any(
                pair.status is PairStatus.INVALID
                for pair in pair_index.get((representation_id, obligation_id), ())
            )
        }
        if any((representation_id, obligation_id) in unverified_pairs for obligation_id in linked):
            hold.add("PAIR_ASSESSMENT_PROVENANCE_INVALID")
        if any((representation_id, obligation_id) in conflicted_pairs for obligation_id in linked):
            hold.add("PAIR_ASSESSMENT_CONFLICT")
        invalid_pairs = {
            obligation_id
            for obligation_id in linked
            if (representation_id, obligation_id) not in unverified_pairs
            and (representation_id, obligation_id) not in conflicted_pairs
            if any(
                pair.status is PairStatus.INVALID
                for pair in pair_index.get((representation_id, obligation_id), ())
            )
            and not any(
                pair.status is PairStatus.VALID
                for pair in pair_index.get((representation_id, obligation_id), ())
            )
        }
        if unresolved_pairs:
            hold.add("PAIR_VALIDITY_UNRESOLVED")
        if invalid_pairs:
            replacement_templates = _templates_for_required(usable_templates, linked, by_obligation)
            successors, issue = _choose_templates(
                linked,
                replacement_templates,
                cost_model,
                cost_model_authorized=cost_model_authorized,
                max_count=1,
                existing_ids=set(by_representation),
            )
            if issue == "AUTHORIZED_COST_LIMIT_EXCEEDED":
                reject.add(issue)
            elif issue is not None or not successors:
                hold.add("REPLACEMENT_NOT_MATERIALIZABLE")
                if issue == "MATERIALIZABLE_TEMPLATE_MISSING":
                    hold.update(unusable_template_reasons)
                if issue in {"COST_MODEL_UNRESOLVED", "BUDGET_EXHAUSTED"}:
                    hold.add(issue)
            else:
                successor_rep, digest, cost = successors[0]
                operations.append(
                    PlannedOperation(
                        "representation",
                        representation_id,
                        OperationKind.REPLACE,
                        ("EXACT_PAIR_INADEQUACY_PROVEN",),
                        tuple(sorted(_pair_refs(pair_index, representation_id, linked))),
                        successor_rep,
                        digest,
                        cost,
                    )
                )
                planned_covered.update(linked & _string_set(successor_rep.get("covers")))
        retained = linked - invalid_pairs - unresolved_pairs if not invalid_pairs else set()
        if retained:
            if impact_status in {
                ImpactStatus.PROVEN_AFFECTED,
                ImpactStatus.POSSIBLY_AFFECTED,
            } and any(
                not any(
                    pair.status is PairStatus.VALID
                    for pair in pair_index.get((representation_id, obligation_id), ())
                )
                for obligation_id in retained
            ):
                hold.add("IMPACTED_RETAIN_REASSESSMENT_MISSING")
                continue
            operations.append(
                PlannedOperation(
                    "representation",
                    representation_id,
                    OperationKind.RETAIN,
                    ("EXACT_PAIR_VALIDITY_PROVEN",),
                    tuple(sorted(_pair_refs(pair_index, representation_id, retained))),
                )
            )

    covered = {
        obligation_id
        for obligation_id in active_mandatory
        if coverage_by_id.get(obligation_id) is not None
        and coverage_by_id[obligation_id].status == "COVERED"
    }
    uncovered = active_mandatory - covered - planned_covered
    additions, add_issue = (
        _choose_templates(
            uncovered,
            _templates_for_required(usable_templates, uncovered, by_obligation),
            cost_model,
            cost_model_authorized=cost_model_authorized,
            max_count=None,
            existing_ids=set(by_representation),
        )
        if uncovered
        else ((), None)
    )
    if add_issue == "AUTHORIZED_COST_LIMIT_EXCEEDED":
        reject.add(add_issue)
    elif add_issue is not None:
        hold.add("ACTIVE_MANDATORY_CONTROL_UNCOVERED")
        hold.add(add_issue)
        if add_issue == "MATERIALIZABLE_TEMPLATE_MISSING":
            hold.update(unusable_template_reasons)
    else:
        assigned: set[str] = set()
        for representation, digest, cost in additions:
            owner_candidates = sorted(
                uncovered & _string_set(representation.get("covers")) - assigned
            )
            if not owner_candidates:
                reject.add("TEMPLATE_COVERAGE_INCONSISTENT")
                continue
            owner = owner_candidates[0]
            assigned.update(_string_set(representation.get("covers")) & uncovered)
            refs = template_evidence(representation)
            artifact = representation.get("evaluator_artifact")
            artifact_path = artifact.get("path") if isinstance(artifact, Mapping) else None
            if isinstance(artifact_path, str):
                refs = tuple(sorted(set(refs) | {artifact_path}))
            operations.append(
                PlannedOperation(
                    "obligation",
                    owner,
                    OperationKind.ADD,
                    ("ACTIVE_MANDATORY_CONTROL_UNCOVERED",),
                    refs,
                    representation,
                    digest,
                    cost,
                )
            )

    if adjustment_rules and not adjustments_authorized:
        hold.add("ADJUSTMENT_AUTHORITY_UNVERIFIED")
    else:
        for rule in adjustment_rules:
            adjustment, issue = _authorized_adjustment(rule, by_representation)
            if issue:
                reject.add(issue)
            elif adjustment is not None:
                operations.append(adjustment)

    operations.sort(
        key=lambda item: (
            item.target_type,
            item.target_id,
            item.operation.value,
            str(item.artifact_sha256 or ""),
        )
    )
    keys = [(item.target_type, item.target_id) for item in operations]
    if len(keys) != len(set(keys)):
        reject.add("CONTRADICTORY_OPERATION_TARGET")
    semantic = {
        "operations": [item.to_dict() for item in operations],
        "hold_reasons": sorted(hold),
        "reject_reasons": sorted(reject),
    }
    plan = OperationPlan(
        tuple(operations),
        tuple(sorted(hold)),
        tuple(sorted(reject)),
        sha256_bytes(canonical_json_bytes(semantic)),
    )
    validate_payload("p_operation_plan_v1.schema.json", plan.to_dict())
    return plan


def choose_candidate_plan(
    candidates: Sequence[Mapping[str, Any]],
    cost_model: Mapping[str, Any],
    *,
    cost_model_authorized: bool = False,
) -> Mapping[str, Any] | None:
    """Choose a fully cost-bound plan by count, cost, then canonical IDs.

    Returns ``None`` on unknown authority/cost or search-budget exhaustion; it
    does not claim optimality when the declared bounded search was not complete.
    """
    if not cost_model_authorized:
        return None
    limit = cost_model.get("max_search_nodes")
    budget = cost_model.get("max_incremental_cost")
    costs = cost_model.get("candidate_costs")
    if not isinstance(limit, int) or limit < 1 or len(candidates) > limit:
        return None
    if not isinstance(budget, int | float) or not isinstance(costs, Mapping):
        return None
    ranked: list[tuple[int, float, tuple[str, ...], Mapping[str, Any]]] = []
    for candidate in candidates:
        operations = candidate.get("operations")
        if not isinstance(operations, list):
            return None
        digests = tuple(
            sorted(
                {
                    str(op.get("artifact_sha256"))
                    for op in operations
                    if isinstance(op, Mapping) and op.get("artifact_sha256")
                }
            )
        )
        if any(_SHA256.fullmatch(digest) is None or digest not in costs for digest in digests):
            return None
        cost = sum(float(costs[digest]) for digest in digests)
        if cost > budget:
            continue
        non_retain = sum(
            1
            for op in operations
            if isinstance(op, Mapping) and op.get("operation") != OperationKind.RETAIN.value
        )
        canonical_ids = tuple(
            sorted(
                str(op.get("target_id", "")) + ":" + str(op.get("artifact_sha256", ""))
                for op in operations
                if isinstance(op, Mapping)
            )
        )
        ranked.append((non_retain, cost, canonical_ids, candidate))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return ranked[0][3]


def template_evidence(representation: Mapping[str, Any]) -> tuple[str, ...]:
    """Return explicit references supplied with a template, never inferred paths."""
    refs = representation.get("evidence_refs", [])
    return (
        tuple(sorted(item for item in refs if isinstance(item, str)))
        if isinstance(refs, list)
        else ()
    )


def _choose_templates(
    required: set[str],
    templates: Sequence[tuple[Mapping[str, Any], str]],
    cost_model: Mapping[str, Any] | None,
    *,
    cost_model_authorized: bool,
    max_count: int | None,
    existing_ids: set[str],
) -> tuple[tuple[tuple[Mapping[str, Any], str, float], ...], str | None]:
    """Find a bounded minimum-count, then minimum-cost deterministic template set."""
    if not required:
        return (), None
    candidates = [
        item
        for item in templates
        if required & _string_set(item[0].get("covers"))
        and str(item[0].get("id")) not in existing_ids
    ]
    if not candidates:
        return (), "MATERIALIZABLE_TEMPLATE_MISSING"
    if cost_model is None or not cost_model_authorized:
        return (), "COST_MODEL_UNRESOLVED"
    node_limit = cost_model.get("max_search_nodes")
    max_cost = cost_model.get("max_incremental_cost")
    costs = cost_model.get("candidate_costs")
    if (
        not isinstance(node_limit, int)
        or node_limit < 1
        or not isinstance(max_cost, int | float)
        or not isinstance(costs, Mapping)
    ):
        return (), "COST_MODEL_UNRESOLVED"
    if any(
        digest not in costs or not isinstance(costs[digest], int | float) or costs[digest] < 0
        for _representation, digest in candidates
    ):
        return (), "COST_MODEL_UNRESOLVED"
    candidates.sort(key=lambda item: (str(item[0].get("id")), item[1]))
    visited = 0
    exhausted = False
    solutions: list[tuple[tuple[Any, ...], tuple[int, ...]]] = []

    def visit(start: int, remaining: set[str], selected: tuple[int, ...]) -> None:
        nonlocal visited, exhausted
        if exhausted:
            return
        visited += 1
        if visited > node_limit:
            exhausted = True
            return
        if not remaining:
            selected_cost = sum(float(costs[candidates[index][1]]) for index in selected)
            ids = tuple(sorted(str(candidates[index][0].get("id")) for index in selected))
            solutions.append(((len(selected), selected_cost, ids), selected))
            return
        if max_count is not None and len(selected) >= max_count:
            return
        for index in range(start, len(candidates)):
            representation, _digest = candidates[index]
            next_remaining = remaining - _string_set(representation.get("covers"))
            if next_remaining == remaining:
                continue
            visit(index + 1, next_remaining, (*selected, index))
            if exhausted:
                return

    visit(0, set(required), ())
    if exhausted:
        return (), "BUDGET_EXHAUSTED"
    if not solutions:
        return (), "MATERIALIZABLE_TEMPLATE_MISSING"
    in_budget = [solution for solution in solutions if solution[0][1] <= float(max_cost)]
    if not in_budget:
        return (), "AUTHORIZED_COST_LIMIT_EXCEEDED"
    _, selected = min(in_budget, key=lambda item: item[0])
    return tuple(
        (candidates[index][0], candidates[index][1], float(costs[candidates[index][1]]))
        for index in selected
    ), None


def _authorized_adjustment(
    rule: Mapping[str, Any], representations: Mapping[str, Mapping[str, Any]]
) -> tuple[PlannedOperation | None, str | None]:
    required = (
        "target_id",
        "parameter",
        "old_value",
        "new_value",
        "rule_id",
        "rule_sha256",
        "evidence_refs",
    )
    if any(key not in rule for key in required):
        return None, "ADJUSTMENT_AUTHORITY_MISSING"
    parameter = rule.get("parameter")
    target_id = rule.get("target_id")
    current = representations.get(str(target_id))
    soft_parameters = current.get("soft_parameters") if current is not None else None
    if (
        not isinstance(parameter, str)
        or not parameter
        or rule.get("hard_constraint") is True
        or rule.get("criterion_intent_change") is True
        or not isinstance(soft_parameters, Mapping)
        or parameter not in soft_parameters
        or soft_parameters.get(parameter) != rule.get("old_value")
    ):
        return None, "UNAUTHORIZED_HARD_OR_INTENT_ADJUSTMENT"
    bounds = rule.get("bounds")
    value = rule.get("new_value")
    if not isinstance(bounds, Mapping) or not isinstance(value, int | float):
        return None, "ADJUSTMENT_BOUNDS_UNRESOLVED"
    minimum, maximum = bounds.get("minimum"), bounds.get("maximum")
    if (
        not isinstance(minimum, int | float)
        or not isinstance(maximum, int | float)
        or not minimum <= value <= maximum
    ):
        return None, "ADJUSTMENT_OUT_OF_BOUNDS"
    digest = rule.get("rule_sha256")
    unsigned_rule = {key: value for key, value in rule.items() if key != "rule_sha256"}
    if (
        not isinstance(digest, str)
        or _SHA256.fullmatch(digest) is None
        or sha256_bytes(canonical_json_bytes(unsigned_rule)) != digest
    ):
        return None, "ADJUSTMENT_RULE_DIGEST_INVALID"
    refs = rule.get("evidence_refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
        return None, "ADJUSTMENT_EVIDENCE_MISSING"
    payload = {
        "parameter": parameter,
        "old_value": rule.get("old_value"),
        "new_value": value,
        "rule_id": rule.get("rule_id"),
        "rule_sha256": digest,
    }
    return PlannedOperation(
        "representation",
        _required_id(rule.get("target_id"), "adjustment target"),
        OperationKind.ADJUST,
        ("AUTHORIZED_BOUNDED_SOFT_ADJUSTMENT",),
        tuple(sorted(set(refs))),
        payload,
    ), None


def _templates_for_required(
    templates: Sequence[tuple[Mapping[str, Any], str]],
    required: set[str],
    obligations: Mapping[str, Mapping[str, Any]],
) -> tuple[tuple[Mapping[str, Any], str], ...]:
    permitted: list[tuple[Mapping[str, Any], str]] = []
    for representation, digest in templates:
        covered = _string_set(representation.get("covers"))
        if not covered or not covered.issubset(required):
            continue
        if any(
            obligation_id not in obligations
            or representation.get("criterion") != obligations[obligation_id].get("criterion")
            for obligation_id in covered
        ):
            continue
        permitted.append((representation, digest))
    return tuple(permitted)


def _valid_representation(row: Mapping[str, Any]) -> bool:
    return (
        isinstance(row.get("id"), str)
        and bool(row.get("id"))
        and isinstance(row.get("criterion"), str)
        and bool(row.get("criterion"))
        and isinstance(row.get("stage"), str)
        and bool(row.get("stage"))
        and isinstance(row.get("evaluator"), str)
        and bool(row.get("evaluator"))
        and isinstance(row.get("covers"), list)
        and bool(row.get("covers"))
        and isinstance(row.get("applicability_scope"), Mapping)
        and isinstance(row.get("evidence_contract"), Mapping)
    )


def _pair_refs(
    index: Mapping[tuple[str, str], Sequence[PairAssessment]],
    representation_id: str,
    obligations: set[str],
) -> set[str]:
    return {
        ref
        for obligation_id in obligations
        for pair in index.get((representation_id, obligation_id), ())
        for ref in pair.evidence_refs
    }


def _string_set(value: Any) -> set[str]:
    return (
        {item for item in value if isinstance(item, str)}
        if isinstance(value, list | tuple)
        else set()
    )


def _required_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ContractValidationError("P03_ID_INVALID: " + label)
    return value


def _impact_digest_is_valid(impact: ImpactAssessment) -> bool:
    payload = impact.to_dict()
    claimed = payload.pop("assessment_sha256", None)
    return isinstance(claimed, str) and claimed == sha256_bytes(canonical_json_bytes(payload))


def _pair_digest_is_valid(pair: PairAssessment) -> bool:
    payload = pair.to_dict()
    claimed = payload.pop("assessment_sha256", None)
    return isinstance(claimed, str) and claimed == sha256_bytes(canonical_json_bytes(payload))


__all__ = [
    "OperationKind",
    "OperationPlan",
    "PlannedOperation",
    "build_operation_plan",
    "choose_candidate_plan",
    "validate_materializable_template",
]
