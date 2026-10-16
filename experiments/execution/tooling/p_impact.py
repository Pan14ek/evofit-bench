"""Typed, conservative architecture and policy change impact analysis.

The module operates on supplied, versioned facts and trace links. It never
infers missing facts from an incomplete inventory or assigns meaning based on
an architecture name.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes

_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_EDGE_ENDPOINTS: dict[str, tuple[str, str]] = {
    "fact_to_obligation": ("fact", "obligation"),
    "policy_to_obligation": ("policy", "obligation"),
    "element_to_obligation": ("architectural_element", "obligation"),
    "element_to_representation": ("architectural_element", "representation"),
    "obligation_to_criterion": ("obligation", "criterion"),
    "criterion_to_representation": ("criterion", "representation"),
    "representation_to_evaluator": ("representation", "evaluator"),
    "representation_to_evidence_contract": ("representation", "evidence_contract"),
    "evaluator_to_evidence_contract": ("evaluator", "evidence_contract"),
}


class ChangeKind(StrEnum):
    """Observable fact, policy, or applicability transition kinds."""

    ADDED = "ADDED"
    REMOVED = "REMOVED"
    VALUE_CHANGED = "VALUE_CHANGED"
    SCOPE_CHANGED = "SCOPE_CHANGED"
    VERSION_CHANGED = "VERSION_CHANGED"
    UNCHANGED = "UNCHANGED"
    INDETERMINATE = "INDETERMINATE"


class ImpactStatus(StrEnum):
    """Conservative classification for a fitness representation."""

    PROVEN_AFFECTED = "PROVEN_AFFECTED"
    POSSIBLY_AFFECTED = "POSSIBLY_AFFECTED"
    NOT_AFFECTED_WITH_PROOF = "NOT_AFFECTED_WITH_PROOF"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class ChangeRecord:
    """A deterministic before/after change with its evidence references."""

    change_id: str
    entity_kind: str
    entity_id: str
    change_kind: ChangeKind
    predicate: str | None = None
    subject: str | None = None
    old_scope: str | None = None
    new_scope: str | None = None
    old_value_sha256: str | None = None
    new_value_sha256: str | None = None
    old_version: str | None = None
    new_version: str | None = None
    evidence_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a canonical JSON-compatible change record."""
        return {
            "change_id": self.change_id,
            "entity_kind": self.entity_kind,
            "entity_id": self.entity_id,
            "change_kind": self.change_kind.value,
            "predicate": self.predicate,
            "subject": self.subject,
            "old_scope": self.old_scope,
            "new_scope": self.new_scope,
            "old_value_sha256": self.old_value_sha256,
            "new_value_sha256": self.new_value_sha256,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "evidence_refs": list(self.evidence_refs),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class TraceNode:
    """A typed node in the criterion-centric trace graph."""

    node_id: str
    kind: str
    scope: str | None = None
    version: str | None = None
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class TraceEdge:
    """A typed, source-backed relationship between trace nodes."""

    source_id: str
    target_id: str
    kind: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class TraceGraph:
    """Validated graph data plus whether the declared inventory is complete."""

    nodes: tuple[TraceNode, ...]
    edges: tuple[TraceEdge, ...]
    inventory_complete: bool
    graph_sha256: str
    unresolved_links: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImpactRecord:
    """Representation impact classification with causal paths."""

    representation_id: str
    status: ImpactStatus
    causal_paths: tuple[tuple[str, ...], ...] = ()
    reason_codes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible impact record."""
        return {
            "representation_id": self.representation_id,
            "status": self.status.value,
            "causal_paths": [list(path) for path in self.causal_paths],
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class ImpactAssessment:
    """Canonical typed difference and conservative impact result."""

    schema_version: int
    architecture_before_sha: str
    architecture_after_sha: str
    policy_source_revision: str
    policy_bundle_sha256: str
    ruleset_sha256: str
    snapshot_sha256: str
    trace_graph_sha256: str
    changes: tuple[ChangeRecord, ...]
    representations: tuple[ImpactRecord, ...]
    uncovered_obligations: tuple[str, ...]
    unresolved_links: tuple[str, ...]
    assessment_sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Return the exact semantic content used by the assessment digest."""
        return {
            "schema_version": self.schema_version,
            "algorithm_version": "P_IMPACT_V1",
            "architecture_before_sha": self.architecture_before_sha,
            "architecture_after_sha": self.architecture_after_sha,
            "policy_source_revision": self.policy_source_revision,
            "policy_bundle_sha256": self.policy_bundle_sha256,
            "ruleset_sha256": self.ruleset_sha256,
            "snapshot_sha256": self.snapshot_sha256,
            "trace_graph_sha256": self.trace_graph_sha256,
            "changes": [change.to_dict() for change in self.changes],
            "representations": [record.to_dict() for record in self.representations],
            "uncovered_obligations": list(self.uncovered_obligations),
            "unresolved_links": list(self.unresolved_links),
            "assessment_sha256": self.assessment_sha256,
        }


def diff_snapshot(
    snapshot: Mapping[str, Any],
    *,
    fact_absence_proofs: Mapping[tuple[str, str, str], bool | None] | None = None,
    policy_inventory_complete: Mapping[str, bool | None] | None = None,
    source_digests: Mapping[str, str] | None = None,
    policy_before_rows: Sequence[Mapping[str, Any]] | None = None,
    policy_after_rows: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[ChangeRecord, ...]:
    """Diff before/after facts and policies without guessing absent rows.

    `fact_absence_proofs` is keyed by `(state, predicate, scope)` and must be
    supplied from exact SPEC 01 completeness evidence. `policy_inventory_complete`
    is keyed by `before`/`after`; absent or unresolved proof never authorizes an
    ADDED/REMOVED conclusion.
    """
    facts = snapshot.get("facts")
    policies = snapshot.get("policies")
    if not isinstance(facts, list) or not isinstance(policies, list):
        raise ContractValidationError("P03_DIFF_INPUT_INVALID: facts/policies must be arrays")
    absence = fact_absence_proofs or {}
    policy_complete = policy_inventory_complete or {}
    if (policy_before_rows is None) != (policy_after_rows is None):
        raise ContractValidationError("P03_POLICY_DIFF_REQUIRES_BOTH_VERSIONS")
    changes = _diff_facts(facts, absence, source_digests or {})
    changes.extend(
        _diff_policies(
            policies if policy_before_rows is None else policy_before_rows,
            policies if policy_after_rows is None else policy_after_rows,
            policy_complete,
            source_digests or {},
        )
    )
    changes.sort(key=lambda item: (item.entity_kind, item.entity_id, item.change_kind.value))
    return tuple(changes)


def parse_trace_graph(payload: Mapping[str, Any]) -> TraceGraph:
    """Validate a versioned typed trace graph while retaining incomplete links."""
    if payload.get("schema_version") != 1:
        raise ContractValidationError("P03_TRACE_GRAPH_VERSION_UNSUPPORTED")
    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    complete = payload.get("inventory_complete")
    if (
        not isinstance(raw_nodes, list)
        or not isinstance(raw_edges, list)
        or not isinstance(complete, bool)
    ):
        raise ContractValidationError("P03_TRACE_GRAPH_INVALID")
    nodes: list[TraceNode] = []
    unresolved: set[str] = set()
    by_id: dict[str, TraceNode] = {}
    duplicate_ids: set[str] = set()
    for row in raw_nodes:
        if not isinstance(row, Mapping):
            unresolved.add("TRACE_NODE_INVALID")
            continue
        node_id, kind = row.get("id"), row.get("kind")
        if not isinstance(node_id, str) or _ID_PATTERN.fullmatch(node_id) is None:
            unresolved.add("TRACE_NODE_ID_INVALID")
            continue
        if not isinstance(kind, str) or kind not in {
            "fact",
            "policy",
            "architectural_element",
            "obligation",
            "criterion",
            "representation",
            "evaluator",
            "evidence_contract",
        }:
            unresolved.add("TRACE_NODE_KIND_INVALID")
            continue
        refs = _string_tuple(
            row.get("source_refs", []), "TRACE_NODE_SOURCE_REFS_INVALID", unresolved
        )
        node = TraceNode(
            node_id,
            kind,
            _optional_string(row.get("scope")),
            _optional_string(row.get("version")),
            refs,
        )
        if node_id in by_id or node_id in duplicate_ids:
            unresolved.add("DUPLICATE_TRACE_NODE")
            by_id.pop(node_id, None)
            duplicate_ids.add(node_id)
            continue
        by_id[node_id] = node
        nodes.append(node)

    edges: list[TraceEdge] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for row in raw_edges:
        if not isinstance(row, Mapping):
            unresolved.add("TRACE_EDGE_INVALID")
            continue
        source, target, kind = row.get("source_id"), row.get("target_id"), row.get("kind")
        if not all(isinstance(value, str) for value in (source, target, kind)):
            unresolved.add("TRACE_EDGE_INVALID")
            continue
        edge_key = (str(source), str(target), str(kind))
        if edge_key in seen_edges:
            unresolved.add("DUPLICATE_TRACE_EDGE")
            continue
        seen_edges.add(edge_key)
        if edge_key[2] not in _EDGE_ENDPOINTS:
            unresolved.add("TRACE_EDGE_KIND_INVALID")
            continue
        source_node, target_node = by_id.get(edge_key[0]), by_id.get(edge_key[1])
        if source_node is None or target_node is None:
            unresolved.add("DANGLING_TRACE_LINK")
            continue
        expected = _EDGE_ENDPOINTS[edge_key[2]]
        if (source_node.kind, target_node.kind) != expected:
            unresolved.add("TRACE_EDGE_TYPE_MISMATCH")
            continue
        refs = _string_tuple(
            row.get("source_refs", []), "TRACE_EDGE_SOURCE_REFS_INVALID", unresolved
        )
        edges.append(TraceEdge(edge_key[0], edge_key[1], edge_key[2], refs))

    nodes.sort(key=lambda item: (item.kind, item.node_id))
    edges.sort(key=lambda item: (item.kind, item.source_id, item.target_id))
    serialized = {
        "schema_version": 1,
        "inventory_complete": complete,
        "nodes": [
            {
                "id": item.node_id,
                "kind": item.kind,
                "scope": item.scope,
                "version": item.version,
                "source_refs": list(item.source_refs),
            }
            for item in nodes
        ],
        "edges": [
            {
                "source_id": item.source_id,
                "target_id": item.target_id,
                "kind": item.kind,
                "source_refs": list(item.source_refs),
            }
            for item in edges
        ],
    }
    return TraceGraph(
        tuple(nodes),
        tuple(edges),
        complete,
        sha256_bytes(canonical_json_bytes(serialized)),
        tuple(sorted(unresolved)),
    )


def legacy_trace_graph(
    payload: Mapping[str, Any],
    *,
    representations: Sequence[Mapping[str, Any]],
    obligations: Sequence[Mapping[str, Any]],
) -> TraceGraph:
    """Project the existing partial A0 trace map into typed, incomplete links."""
    elements = payload.get("elements")
    if payload.get("schema_version") != 1 or not isinstance(elements, list):
        raise ContractValidationError("P03_LEGACY_TRACEABILITY_INVALID")
    representation_by_id = {
        str(row.get("id")): row for row in representations if isinstance(row.get("id"), str)
    }
    obligation_by_id = {
        str(row.get("id")): row for row in obligations if isinstance(row.get("id"), str)
    }
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    unresolved: set[str] = {"LEGACY_TRACEABILITY_PARTIAL"}
    for obligation_id, obligation in obligation_by_id.items():
        criterion_id = obligation.get("criterion")
        if isinstance(criterion_id, str) and _ID_PATTERN.fullmatch(criterion_id):
            nodes.setdefault(obligation_id, {"id": obligation_id, "kind": "obligation"})
            nodes.setdefault(criterion_id, {"id": criterion_id, "kind": "criterion"})
            edges.append(
                {
                    "source_id": obligation_id,
                    "target_id": criterion_id,
                    "kind": "obligation_to_criterion",
                }
            )
        else:
            unresolved.add("OBLIGATION_CRITERION_UNRESOLVED")
    for element in elements:
        if not isinstance(element, Mapping) or not isinstance(element.get("id"), str):
            unresolved.add("TRACE_ELEMENT_INVALID")
            continue
        element_id = str(element["id"])
        nodes[element_id] = {"id": element_id, "kind": "architectural_element"}
        for obligation_id in _as_string_list(element.get("obligations")):
            if obligation_id not in obligation_by_id:
                unresolved.add("UNRESOLVED_OBLIGATION_LINK")
                continue
            nodes.setdefault(obligation_id, {"id": obligation_id, "kind": "obligation"})
            edges.append(
                {
                    "source_id": element_id,
                    "target_id": obligation_id,
                    "kind": "element_to_obligation",
                }
            )
        for representation in element.get("representations", []):
            if not isinstance(representation, Mapping) or not isinstance(
                representation.get("id"), str
            ):
                unresolved.add("UNRESOLVED_REPRESENTATION_LINK")
                continue
            representation_id = str(representation["id"])
            definition = representation_by_id.get(representation_id)
            if definition is None:
                unresolved.add("UNRESOLVED_REPRESENTATION_LINK")
                continue
            nodes.setdefault(representation_id, {"id": representation_id, "kind": "representation"})
            edges.append(
                {
                    "source_id": element_id,
                    "target_id": representation_id,
                    "kind": "element_to_representation",
                }
            )
            criterion_id = definition.get("criterion")
            if isinstance(criterion_id, str):
                nodes.setdefault(criterion_id, {"id": criterion_id, "kind": "criterion"})
                edges.append(
                    {
                        "source_id": criterion_id,
                        "target_id": representation_id,
                        "kind": "criterion_to_representation",
                    }
                )
            evaluator_id = definition.get("evaluator")
            if isinstance(evaluator_id, str):
                nodes.setdefault(evaluator_id, {"id": evaluator_id, "kind": "evaluator"})
                edges.append(
                    {
                        "source_id": representation_id,
                        "target_id": evaluator_id,
                        "kind": "representation_to_evaluator",
                    }
                )
    parsed = parse_trace_graph(
        {
            "schema_version": 1,
            "inventory_complete": False,
            "nodes": list(nodes.values()),
            "edges": edges,
        }
    )
    return TraceGraph(
        nodes=parsed.nodes,
        edges=parsed.edges,
        inventory_complete=False,
        graph_sha256=parsed.graph_sha256,
        unresolved_links=tuple(sorted(set(parsed.unresolved_links) | unresolved)),
    )


def analyze_impact(
    *,
    architecture_before_sha: str,
    architecture_after_sha: str,
    policy_source_revision: str,
    policy_bundle_sha256: str,
    ruleset_sha256: str,
    snapshot_sha256: str,
    changes: Sequence[ChangeRecord],
    graph: TraceGraph,
    representation_ids: Sequence[str],
    applicability_after: Mapping[str, str],
    mandatory_obligations: Sequence[str],
    covered_obligations: Sequence[str],
) -> ImpactAssessment:
    """Trace typed changes conservatively and identify uncovered active controls."""
    for name, value, length in (
        ("architecture_before_sha", architecture_before_sha, 40),
        ("architecture_after_sha", architecture_after_sha, 40),
        ("snapshot_sha256", snapshot_sha256, 64),
    ):
        if (
            not isinstance(value, str)
            or len(value) != length
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ContractValidationError(f"P03_IDENTITY_INVALID: {name}")
    if not policy_source_revision or len(policy_source_revision) > 128:
        raise ContractValidationError("P03_IDENTITY_INVALID: policy_source_revision")
    for name, value in (
        ("policy_bundle_sha256", policy_bundle_sha256),
        ("ruleset_sha256", ruleset_sha256),
    ):
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ContractValidationError(f"P03_IDENTITY_INVALID: {name}")

    node_by_id = {node.node_id: node for node in graph.nodes}
    adjacency: dict[str, list[str]] = defaultdict(list)
    edge_refs: dict[tuple[str, str], tuple[str, ...]] = {}
    for edge in graph.edges:
        adjacency[edge.source_id].append(edge.target_id)
        edge_refs[(edge.source_id, edge.target_id)] = edge.source_refs
    for key in adjacency:
        adjacency[key].sort()

    proven_seed_ids: set[str] = set()
    possible_seed_ids: set[str] = set()
    unresolved: set[str] = set(graph.unresolved_links)
    uncertain_seed = False
    for change in changes:
        if change.change_kind is ChangeKind.UNCHANGED:
            continue
        if change.change_kind is ChangeKind.INDETERMINATE:
            unresolved.add("INDETERMINATE_CHANGE:" + change.change_id)
            uncertain_seed = True
        if change.entity_id in node_by_id:
            if change.change_kind is ChangeKind.INDETERMINATE:
                possible_seed_ids.add(change.entity_id)
            else:
                proven_seed_ids.add(change.entity_id)
        else:
            unresolved.add("UNMAPPED_CHANGE:" + change.change_id)
            uncertain_seed = True

    def reachable(seeds: set[str]) -> dict[str, tuple[str, ...]]:
        paths: dict[str, tuple[str, ...]] = {}
        queue: deque[tuple[str, tuple[str, ...]]] = deque(
            (node_id, (node_id,)) for node_id in sorted(seeds)
        )
        while queue:
            current, path = queue.popleft()
            if current in paths:
                continue
            paths[current] = path
            for next_id in adjacency.get(current, []):
                queue.append((next_id, path + (next_id,)))
        return paths

    proven_reach = reachable(proven_seed_ids)
    possible_reach = reachable(possible_seed_ids)
    representation_nodes = {
        node_id for node_id, node in node_by_id.items() if node.kind == "representation"
    }
    declared_representations = set(representation_ids)
    mapped_representations = representation_nodes & declared_representations
    records: list[ImpactRecord] = []
    for representation_id in sorted(declared_representations):
        if representation_id in proven_reach:
            path = proven_reach[representation_id]
            refs = {
                ref
                for left, right in zip(path, path[1:], strict=False)
                for ref in edge_refs.get((left, right), ())
            }
            refs.update(
                ref
                for change in changes
                if change.entity_id == path[0]
                for ref in change.evidence_refs
            )
            records.append(
                ImpactRecord(
                    representation_id,
                    ImpactStatus.PROVEN_AFFECTED,
                    (path,),
                    ("TYPED_CAUSAL_PATH",),
                    tuple(sorted(refs)),
                )
            )
        elif representation_id in possible_reach:
            path = possible_reach[representation_id]
            refs = {
                ref
                for left, right in zip(path, path[1:], strict=False)
                for ref in edge_refs.get((left, right), ())
            }
            refs.update(
                ref
                for change in changes
                if change.entity_id == path[0]
                for ref in change.evidence_refs
            )
            records.append(
                ImpactRecord(
                    representation_id,
                    ImpactStatus.POSSIBLY_AFFECTED,
                    (path,),
                    ("CHANGE_NOT_PROVEN",),
                    tuple(sorted(refs)),
                )
            )
        elif not graph.inventory_complete:
            status = (
                ImpactStatus.POSSIBLY_AFFECTED
                if uncertain_seed or proven_seed_ids or possible_seed_ids
                else ImpactStatus.UNRESOLVED
            )
            records.append(
                ImpactRecord(
                    representation_id, status, (), ("TRACEABILITY_INVENTORY_INCOMPLETE",), ()
                )
            )
        elif uncertain_seed or graph.unresolved_links:
            records.append(
                ImpactRecord(
                    representation_id,
                    ImpactStatus.UNRESOLVED,
                    (),
                    ("IMPACT_EVIDENCE_UNRESOLVED",),
                    (),
                )
            )
        else:
            records.append(
                ImpactRecord(
                    representation_id,
                    ImpactStatus.NOT_AFFECTED_WITH_PROOF,
                    (),
                    ("COMPLETE_TYPED_GRAPH_NO_PATH",),
                    (),
                )
            )

    if declared_representations - mapped_representations:
        unresolved.update(
            "REPRESENTATION_MISSING_FROM_GRAPH:" + rid
            for rid in declared_representations - mapped_representations
        )
    covered = set(covered_obligations)
    mandatory = set(mandatory_obligations)
    uncovered = tuple(
        sorted(
            obligation_id
            for obligation_id in mandatory
            if applicability_after.get(obligation_id) == "ACTIVE" and obligation_id not in covered
        )
    )
    for obligation_id, status in applicability_after.items():
        if status == "UNKNOWN" and obligation_id in mandatory:
            unresolved.add("MANDATORY_APPLICABILITY_UNKNOWN:" + obligation_id)
        if obligation_id not in node_by_id and status == "ACTIVE":
            unresolved.add("ACTIVE_OBLIGATION_MISSING_FROM_GRAPH:" + obligation_id)

    content: dict[str, Any] = {
        "schema_version": 1,
        "algorithm_version": "P_IMPACT_V1",
        "architecture_before_sha": architecture_before_sha,
        "architecture_after_sha": architecture_after_sha,
        "policy_source_revision": policy_source_revision,
        "policy_bundle_sha256": policy_bundle_sha256,
        "ruleset_sha256": ruleset_sha256,
        "snapshot_sha256": snapshot_sha256,
        "trace_graph_sha256": graph.graph_sha256,
        "changes": [
            change.to_dict()
            for change in sorted(
                changes, key=lambda item: (item.entity_kind, item.entity_id, item.change_kind.value)
            )
        ],
        "representations": [record.to_dict() for record in records],
        "uncovered_obligations": list(uncovered),
        "unresolved_links": sorted(unresolved),
    }
    digest = sha256_bytes(canonical_json_bytes(content))
    assessment = ImpactAssessment(
        schema_version=1,
        architecture_before_sha=architecture_before_sha,
        architecture_after_sha=architecture_after_sha,
        policy_source_revision=policy_source_revision,
        policy_bundle_sha256=policy_bundle_sha256,
        ruleset_sha256=ruleset_sha256,
        snapshot_sha256=snapshot_sha256,
        trace_graph_sha256=graph.graph_sha256,
        changes=tuple(
            sorted(
                changes, key=lambda item: (item.entity_kind, item.entity_id, item.change_kind.value)
            )
        ),
        representations=tuple(records),
        uncovered_obligations=uncovered,
        unresolved_links=tuple(sorted(unresolved)),
        assessment_sha256=digest,
    )
    validate_payload("p_impact_assessment_v1.schema.json", assessment.to_dict())
    return assessment


def _diff_facts(
    rows: Sequence[Any],
    absence: Mapping[tuple[str, str, str], bool | None],
    source_digests: Mapping[str, str],
) -> list[ChangeRecord]:
    indexed: dict[tuple[str, str, str], dict[str, list[Mapping[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        if not isinstance(row, Mapping) or row.get("state") not in {"before", "after"}:
            continue
        key_fields = row.get("predicate"), row.get("subject"), row.get("scope")
        if not all(isinstance(value, str) and value for value in key_fields):
            continue
        indexed[(str(key_fields[0]), str(key_fields[1]), str(key_fields[2]))][
            str(row["state"])
        ].append(row)
    output: list[ChangeRecord] = []
    matched_scope_keys: set[tuple[str, str, str]] = set()
    groups: dict[
        tuple[str, str], dict[str, list[tuple[tuple[str, str, str], Mapping[str, Any]]]]
    ] = defaultdict(lambda: defaultdict(list))
    for key, states in indexed.items():
        for state, state_rows in states.items():
            for row in state_rows:
                groups[(key[0], key[1])][state].append((key, row))
    for (predicate, subject), states in sorted(groups.items()):
        before_rows, after_rows = states.get("before", []), states.get("after", [])
        by_scope_before = {key[2]: (key, row) for key, row in before_rows}
        by_scope_after = {key[2]: (key, row) for key, row in after_rows}
        if (
            len(before_rows) > 1
            and len(by_scope_before) != len(before_rows)
            or len(after_rows) > 1
            and len(by_scope_after) != len(after_rows)
        ):
            output.append(
                _fact_record(
                    predicate,
                    subject,
                    None,
                    None,
                    ChangeKind.INDETERMINATE,
                    "CONTRADICTORY_FACT_IDENTITY",
                    source_digests=source_digests,
                )
            )
            continue
        for scope in sorted(set(by_scope_before) & set(by_scope_after)):
            b_key, before = by_scope_before[scope]
            a_key, after = by_scope_after[scope]
            matched_scope_keys.update({b_key, a_key})
            if _unknown_fact(before) or _unknown_fact(after):
                output.append(
                    _fact_record(
                        predicate,
                        subject,
                        scope,
                        scope,
                        ChangeKind.INDETERMINATE,
                        "FACT_VALUE_UNKNOWN",
                        before,
                        after,
                        source_digests,
                    )
                )
            elif before.get("value") != after.get("value"):
                output.append(
                    _fact_record(
                        predicate,
                        subject,
                        scope,
                        scope,
                        ChangeKind.VALUE_CHANGED,
                        "FACT_VALUE_CHANGED",
                        before,
                        after,
                        source_digests,
                    )
                )
            elif _source_version(before, source_digests) != _source_version(after, source_digests):
                output.append(
                    _fact_record(
                        predicate,
                        subject,
                        scope,
                        scope,
                        ChangeKind.VERSION_CHANGED,
                        "FACT_SOURCE_VERSION_CHANGED",
                        before,
                        after,
                        source_digests,
                    )
                )
            else:
                output.append(
                    _fact_record(
                        predicate,
                        subject,
                        scope,
                        scope,
                        ChangeKind.UNCHANGED,
                        "FACT_UNCHANGED",
                        before,
                        after,
                        source_digests,
                    )
                )
        remaining_before = [item for item in before_rows if item[0] not in matched_scope_keys]
        remaining_after = [item for item in after_rows if item[0] not in matched_scope_keys]
        if len(remaining_before) == 1 and len(remaining_after) == 1:
            b_key, before = remaining_before[0]
            a_key, after = remaining_after[0]
            matched_scope_keys.update({b_key, a_key})
            kind = (
                ChangeKind.INDETERMINATE
                if _unknown_fact(before) or _unknown_fact(after)
                else ChangeKind.SCOPE_CHANGED
            )
            code = (
                "FACT_SCOPE_CHANGE_UNPROVEN"
                if kind is ChangeKind.INDETERMINATE
                else "FACT_SCOPE_CHANGED"
            )
            output.append(
                _fact_record(
                    predicate,
                    subject,
                    b_key[2],
                    a_key[2],
                    kind,
                    code,
                    before,
                    after,
                    source_digests,
                )
            )
            continue
        for key, row in remaining_before:
            is_complete = absence.get(("after", predicate, key[2]))
            kind = (
                ChangeKind.REMOVED
                if is_complete is True and not _unknown_fact(row)
                else ChangeKind.INDETERMINATE
            )
            code = (
                "FACT_REMOVED_WITH_SCOPED_COMPLETENESS"
                if kind is ChangeKind.REMOVED
                else "FACT_ABSENCE_UNPROVEN"
            )
            output.append(
                _fact_record(
                    predicate, subject, key[2], None, kind, code, row, None, source_digests
                )
            )
        for key, row in remaining_after:
            is_complete = absence.get(("before", predicate, key[2]))
            kind = (
                ChangeKind.ADDED
                if is_complete is True and not _unknown_fact(row)
                else ChangeKind.INDETERMINATE
            )
            code = (
                "FACT_ADDED_WITH_SCOPED_COMPLETENESS"
                if kind is ChangeKind.ADDED
                else "FACT_ABSENCE_UNPROVEN"
            )
            output.append(
                _fact_record(
                    predicate, subject, None, key[2], kind, code, None, row, source_digests
                )
            )
    return output


def _diff_policies(
    before_rows: Sequence[Any],
    after_rows: Sequence[Any],
    complete: Mapping[str, bool | None],
    source_digests: Mapping[str, str],
) -> list[ChangeRecord]:
    indexed: dict[str, dict[str, Mapping[str, Any]]] = {"before": {}, "after": {}}
    duplicates: set[tuple[str, str]] = set()
    for state, rows in (("before", before_rows), ("after", after_rows)):
        for row in rows:
            if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
                continue
            policy_id = str(row["id"])
            if policy_id in indexed[state]:
                duplicates.add((state, policy_id))
            indexed[state][policy_id] = row
    ids = sorted(set(indexed["before"]) | set(indexed["after"]))
    result: list[ChangeRecord] = []
    for policy_id in ids:
        before, after = indexed["before"].get(policy_id), indexed["after"].get(policy_id)
        if ("before", policy_id) in duplicates or ("after", policy_id) in duplicates:
            result.append(
                ChangeRecord(
                    f"policy:{policy_id}",
                    "policy",
                    policy_id,
                    ChangeKind.INDETERMINATE,
                    reason_codes=("CONTRADICTORY_POLICY_IDENTITY",),
                )
            )
        elif before is None:
            kind = ChangeKind.ADDED if complete.get("before") is True else ChangeKind.INDETERMINATE
            result.append(
                ChangeRecord(
                    f"policy:{policy_id}",
                    "policy",
                    policy_id,
                    kind,
                    new_version=_policy_version_bound(after, source_digests),
                    evidence_refs=_policy_refs(after),
                    reason_codes=(
                        "POLICY_ADDED" if kind is ChangeKind.ADDED else "POLICY_ABSENCE_UNPROVEN",
                    ),
                )
            )
        elif after is None:
            kind = ChangeKind.REMOVED if complete.get("after") is True else ChangeKind.INDETERMINATE
            result.append(
                ChangeRecord(
                    f"policy:{policy_id}",
                    "policy",
                    policy_id,
                    kind,
                    old_version=_policy_version_bound(before, source_digests),
                    evidence_refs=_policy_refs(before),
                    reason_codes=(
                        "POLICY_REMOVED"
                        if kind is ChangeKind.REMOVED
                        else "POLICY_ABSENCE_UNPROVEN",
                    ),
                )
            )
        elif _policy_semantics(before, source_digests) == _policy_semantics(after, source_digests):
            result.append(
                ChangeRecord(
                    f"policy:{policy_id}",
                    "policy",
                    policy_id,
                    ChangeKind.UNCHANGED,
                    old_version=_policy_version_bound(before, source_digests),
                    new_version=_policy_version_bound(after, source_digests),
                    evidence_refs=_policy_refs(before),
                    reason_codes=("POLICY_UNCHANGED",),
                )
            )
        else:
            result.append(
                ChangeRecord(
                    f"policy:{policy_id}",
                    "policy",
                    policy_id,
                    ChangeKind.VALUE_CHANGED,
                    old_version=_policy_version_bound(before, source_digests),
                    new_version=_policy_version_bound(after, source_digests),
                    evidence_refs=tuple(
                        sorted(set(_policy_refs(before)) | set(_policy_refs(after)))
                    ),
                    reason_codes=("POLICY_CONTENT_CHANGED",),
                )
            )
    return result


def _fact_record(
    predicate: str,
    subject: str,
    old_scope: str | None,
    new_scope: str | None,
    kind: ChangeKind,
    reason: str,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
    source_digests: Mapping[str, str] | None = None,
) -> ChangeRecord:
    refs = tuple(
        sorted(
            set(_as_string_list(before.get("source_ids") if before else []))
            | set(_as_string_list(after.get("source_ids") if after else []))
        )
    )
    return ChangeRecord(
        change_id=f"fact:{predicate}:{subject}:{old_scope or '-'}:{new_scope or '-'}",
        entity_kind="fact",
        entity_id=str((after or before or {}).get("id", f"{predicate}:{subject}")),
        change_kind=kind,
        predicate=predicate,
        subject=subject,
        old_scope=old_scope,
        new_scope=new_scope,
        old_value_sha256=_value_digest(before.get("value"))
        if before and before.get("value") is not None
        else None,
        new_value_sha256=_value_digest(after.get("value"))
        if after and after.get("value") is not None
        else None,
        old_version=_source_version(before, source_digests or {}),
        new_version=_source_version(after, source_digests or {}),
        evidence_refs=refs,
        reason_codes=(reason,),
    )


def _value_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _source_version(
    row: Mapping[str, Any] | None, source_digests: Mapping[str, str] | None = None
) -> str | None:
    if row is None:
        return None
    sources = _as_string_list(row.get("source_ids"))
    digests = source_digests or {}
    return ",".join(f"{source}={digests.get(source, 'UNBOUND')}" for source in sources) or None


def _policy_semantics(row: Mapping[str, Any] | None, source_digests: Mapping[str, str]) -> Any:
    if row is None:
        return None
    payload = dict(row)
    for key in ("source_id", "approval_source_id"):
        source_id = payload.get(key)
        if isinstance(source_id, str):
            payload[key] = {"id": source_id, "sha256": source_digests.get(source_id, "UNBOUND")}
    return payload


def _policy_version_bound(
    row: Mapping[str, Any] | None, source_digests: Mapping[str, str]
) -> str | None:
    if row is None:
        return None
    source_ids = [row.get(key) for key in ("source_id", "approval_source_id")]
    refs = sorted(
        f"{source_id}={source_digests.get(source_id, 'UNBOUND')}"
        for source_id in source_ids
        if isinstance(source_id, str)
    )
    return _policy_version(row) + ":" + ",".join(refs)


def _unknown_fact(row: Mapping[str, Any]) -> bool:
    return row.get("epistemic_kind") == "UNKNOWN" or row.get("value") is None


def _policy_version(row: Mapping[str, Any] | None) -> str | None:
    if row is None:
        return None
    return str(row.get("normative_status", "")) + ":" + str(row.get("effective_from", ""))


def _policy_refs(row: Mapping[str, Any] | None) -> tuple[str, ...]:
    if row is None:
        return ()
    return tuple(
        sorted(
            str(row[key])
            for key in ("source_id", "approval_source_id")
            if isinstance(row.get(key), str)
        )
    )


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return sorted(set(item for item in value if isinstance(item, str)))


def _string_tuple(value: Any, reason: str, unresolved: set[str]) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        unresolved.add(reason)
        return ()
    return tuple(sorted(set(value)))


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "ChangeKind",
    "ChangeRecord",
    "ImpactAssessment",
    "ImpactRecord",
    "ImpactStatus",
    "TraceEdge",
    "TraceGraph",
    "TraceNode",
    "analyze_impact",
    "diff_snapshot",
    "legacy_trace_graph",
    "parse_trace_graph",
]
