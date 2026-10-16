"""Typed diffs, criterion graph reachability and conservative impact tests."""

from __future__ import annotations

import copy

import pytest

from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.p_impact import (
    ChangeKind,
    ChangeRecord,
    ImpactStatus,
    analyze_impact,
    diff_snapshot,
    parse_trace_graph,
)
from tests.unit.p_spec03_support import load_synthetic_fixture


def test_typed_fact_diff_preserves_values_scope_and_source_versions() -> None:
    fixture = load_synthetic_fixture()
    fact = fixture["fact"]
    snapshot = {
        "facts": [
            {
                "id": fact["id"] + "_BEFORE",
                "state": "before",
                "predicate": fact["predicate"],
                "subject": fact["subject"],
                "scope": fact["scope"],
                "value": fact["before_value"],
                "epistemic_kind": "DECLARED",
                "source_ids": ["SYN_SOURCE_FACT"],
            },
            {
                "id": fact["id"],
                "state": "after",
                "predicate": fact["predicate"],
                "subject": fact["subject"],
                "scope": fact["scope"],
                "value": fact["after_value"],
                "epistemic_kind": "DECLARED",
                "source_ids": ["SYN_SOURCE_FACT"],
            },
        ],
        "policies": [],
    }
    records = diff_snapshot(snapshot, source_digests={"SYN_SOURCE_FACT": fixture["source_sha256"]})
    assert len(records) == 1
    assert records[0].change_kind is ChangeKind.VALUE_CHANGED
    assert records[0].old_scope == records[0].new_scope == "service:synth"
    assert records[0].old_value_sha256 != records[0].new_value_sha256
    assert records[0].old_version == "SYN_SOURCE_FACT=" + fixture["source_sha256"]


def test_missing_fact_is_indeterminate_until_exact_scoped_completeness() -> None:
    fact = load_synthetic_fixture()["fact"]
    snapshot = {
        "facts": [
            {
                "id": fact["id"],
                "state": "before",
                "predicate": fact["predicate"],
                "subject": fact["subject"],
                "scope": fact["scope"],
                "value": False,
                "epistemic_kind": "DECLARED",
                "source_ids": ["SYN_SOURCE_FACT"],
            },
        ],
        "policies": [],
    }
    unresolved = diff_snapshot(snapshot)[0]
    proved = diff_snapshot(
        snapshot,
        fact_absence_proofs={
            ("after", fact["predicate"], fact["scope"]): True,
        },
    )[0]
    assert unresolved.change_kind is ChangeKind.INDETERMINATE
    assert proved.change_kind is ChangeKind.REMOVED


def test_fact_scope_shift_is_not_reported_as_removal_plus_addition() -> None:
    fact = load_synthetic_fixture()["fact"]
    snapshot = {
        "facts": [
            {
                "id": "SYN_SCOPE_BEFORE",
                "state": "before",
                "predicate": fact["predicate"],
                "subject": fact["subject"],
                "scope": "service:old",
                "value": False,
                "epistemic_kind": "DECLARED",
                "source_ids": ["SYN_SOURCE_FACT"],
            },
            {
                "id": "SYN_SCOPE_AFTER",
                "state": "after",
                "predicate": fact["predicate"],
                "subject": fact["subject"],
                "scope": "service:new",
                "value": False,
                "epistemic_kind": "DECLARED",
                "source_ids": ["SYN_SOURCE_FACT"],
            },
        ],
        "policies": [],
    }
    records = diff_snapshot(snapshot)
    assert len(records) == 1
    assert records[0].change_kind is ChangeKind.SCOPE_CHANGED
    assert (records[0].old_scope, records[0].new_scope) == ("service:old", "service:new")


def test_policy_only_change_is_detected_with_identical_architecture_revision() -> None:
    fixture = load_synthetic_fixture()
    before = fixture["policy_before"]
    after = fixture["policy_after"]
    result = diff_snapshot(
        {"facts": [], "policies": []},
        policy_before_rows=[before],
        policy_after_rows=[after],
        policy_inventory_complete={"before": True, "after": True},
        source_digests={"SYN_POLICY_SOURCE": fixture["source_sha256"]},
    )
    assert len(result) == 1
    assert result[0].entity_kind == "policy"
    assert result[0].change_kind is ChangeKind.VALUE_CHANGED
    impact = analyze_impact(
        architecture_before_sha=fixture["architecture_after_sha"],
        architecture_after_sha=fixture["architecture_after_sha"],
        policy_source_revision=fixture["policy_source_revision"],
        policy_bundle_sha256=fixture["policy_bundle_sha256"],
        ruleset_sha256=fixture["ruleset_sha256"],
        snapshot_sha256=fixture["snapshot_sha256"],
        changes=result,
        graph=parse_trace_graph(fixture["trace_graph"]),
        representation_ids=["REP_SYNTH_TRACE"],
        applicability_after={"SYN_OBL_TRACE": "ACTIVE"},
        mandatory_obligations=["SYN_OBL_TRACE"],
        covered_obligations=[],
    )
    assert impact.representations[0].status is ImpactStatus.PROVEN_AFFECTED


def test_policy_addition_requires_proven_prior_inventory_completeness() -> None:
    policy = load_synthetic_fixture()["policy_before"]
    unknown = diff_snapshot(
        {"facts": [], "policies": []}, policy_before_rows=[], policy_after_rows=[policy]
    )
    proven = diff_snapshot(
        {"facts": [], "policies": []},
        policy_before_rows=[],
        policy_after_rows=[policy],
        policy_inventory_complete={"before": True},
    )
    assert unknown[0].change_kind is ChangeKind.INDETERMINATE
    assert proven[0].change_kind is ChangeKind.ADDED


def test_policy_diff_rejects_single_sided_version_input() -> None:
    with pytest.raises(ContractValidationError, match="P03_POLICY_DIFF_REQUIRES_BOTH_VERSIONS"):
        diff_snapshot({"facts": [], "policies": []}, policy_before_rows=[])


def test_policy_duplicate_identity_is_indeterminate_not_last_write_wins() -> None:
    policy = load_synthetic_fixture()["policy_before"]
    duplicate = dict(policy, proposition="conflicting duplicate")
    result = diff_snapshot(
        {"facts": [], "policies": []},
        policy_before_rows=[policy, duplicate],
        policy_after_rows=[policy],
    )
    assert result[0].change_kind is ChangeKind.INDETERMINATE
    assert "CONTRADICTORY_POLICY_IDENTITY" in result[0].reason_codes


def test_trace_graph_keeps_typed_reachability_and_source_path() -> None:
    fixture = load_synthetic_fixture()
    graph = parse_trace_graph(fixture["trace_graph"])
    change = ChangeRecord(
        "change:fact",
        "fact",
        "SYN_FACT_CAPABILITY_BOUNDARY",
        ChangeKind.VALUE_CHANGED,
        evidence_refs=("SYN_SOURCE_FACT",),
    )
    result = analyze_impact(
        architecture_before_sha=fixture["architecture_before_sha"],
        architecture_after_sha=fixture["architecture_after_sha"],
        policy_source_revision=fixture["policy_source_revision"],
        policy_bundle_sha256=fixture["policy_bundle_sha256"],
        ruleset_sha256=fixture["ruleset_sha256"],
        snapshot_sha256=fixture["snapshot_sha256"],
        changes=[change],
        graph=graph,
        representation_ids=["REP_SYNTH_TRACE"],
        applicability_after={"SYN_OBL_TRACE": "ACTIVE"},
        mandatory_obligations=["SYN_OBL_TRACE"],
        covered_obligations=["SYN_OBL_TRACE"],
    )
    impact = result.representations[0]
    assert impact.status is ImpactStatus.PROVEN_AFFECTED
    assert impact.causal_paths[0] == (
        "SYN_FACT_CAPABILITY_BOUNDARY",
        "SYN_OBL_TRACE",
        "SYN_CRIT_AUDIT",
        "REP_SYNTH_TRACE",
    )
    assert impact.evidence_refs == ("SYN_SOURCE_CATALOG", "SYN_SOURCE_CONFIG", "SYN_SOURCE_FACT")


def test_unknown_fact_change_yields_possible_not_proven_impact() -> None:
    fixture = load_synthetic_fixture()
    graph = parse_trace_graph(fixture["trace_graph"])
    result = analyze_impact(
        architecture_before_sha=fixture["architecture_before_sha"],
        architecture_after_sha=fixture["architecture_after_sha"],
        policy_source_revision=fixture["policy_source_revision"],
        policy_bundle_sha256=fixture["policy_bundle_sha256"],
        ruleset_sha256=fixture["ruleset_sha256"],
        snapshot_sha256=fixture["snapshot_sha256"],
        changes=[
            ChangeRecord(
                "change:unknown", "fact", "SYN_FACT_CAPABILITY_BOUNDARY", ChangeKind.INDETERMINATE
            )
        ],
        graph=graph,
        representation_ids=["REP_SYNTH_TRACE"],
        applicability_after={"SYN_OBL_TRACE": "ACTIVE"},
        mandatory_obligations=["SYN_OBL_TRACE"],
        covered_obligations=[],
    )
    assert result.representations[0].status is ImpactStatus.POSSIBLY_AFFECTED
    assert result.uncovered_obligations == ("SYN_OBL_TRACE",)


def test_dangling_duplicate_and_mistyped_edges_remain_unresolved() -> None:
    graph = load_synthetic_fixture()["trace_graph"]
    damaged = copy.deepcopy(graph)
    damaged["edges"].extend(
        [
            {
                "source_id": "SYN_FACT_CAPABILITY_BOUNDARY",
                "target_id": "MISSING_NODE",
                "kind": "fact_to_obligation",
                "source_refs": [],
            },
            copy.deepcopy(damaged["edges"][0]),
            {
                "source_id": "SYN_FACT_CAPABILITY_BOUNDARY",
                "target_id": "REP_SYNTH_TRACE",
                "kind": "fact_to_obligation",
                "source_refs": [],
            },
        ]
    )
    parsed = parse_trace_graph(damaged)
    assert {"DANGLING_TRACE_LINK", "DUPLICATE_TRACE_EDGE", "TRACE_EDGE_TYPE_MISMATCH"} <= set(
        parsed.unresolved_links
    )


def test_incomplete_graph_cannot_prove_no_impact_and_active_q_is_still_found() -> None:
    fixture = load_synthetic_fixture()
    payload = copy.deepcopy(fixture["trace_graph"])
    payload["inventory_complete"] = False
    parsed = parse_trace_graph(payload)
    result = analyze_impact(
        architecture_before_sha=fixture["architecture_before_sha"],
        architecture_after_sha=fixture["architecture_after_sha"],
        policy_source_revision=fixture["policy_source_revision"],
        policy_bundle_sha256=fixture["policy_bundle_sha256"],
        ruleset_sha256=fixture["ruleset_sha256"],
        snapshot_sha256=fixture["snapshot_sha256"],
        changes=[],
        graph=parsed,
        representation_ids=["REP_SYNTH_TRACE"],
        applicability_after={"SYN_OBL_LATENCY": "ACTIVE"},
        mandatory_obligations=["SYN_OBL_LATENCY"],
        covered_obligations=[],
    )
    assert result.representations[0].status is ImpactStatus.UNRESOLVED
    assert result.uncovered_obligations == ("SYN_OBL_LATENCY",)


def test_irrelevant_isolated_component_does_not_change_existing_impact() -> None:
    fixture = load_synthetic_fixture()
    baseline = copy.deepcopy(fixture["trace_graph"])
    expanded = copy.deepcopy(baseline)
    expanded["nodes"].append(
        {"id": "SYN_UNRELATED_REP", "kind": "representation", "source_refs": []}
    )
    first = analyze_impact(
        architecture_before_sha=fixture["architecture_before_sha"],
        architecture_after_sha=fixture["architecture_after_sha"],
        policy_source_revision=fixture["policy_source_revision"],
        policy_bundle_sha256=fixture["policy_bundle_sha256"],
        ruleset_sha256=fixture["ruleset_sha256"],
        snapshot_sha256=fixture["snapshot_sha256"],
        changes=[
            ChangeRecord(
                "change:fact", "fact", "SYN_FACT_CAPABILITY_BOUNDARY", ChangeKind.VALUE_CHANGED
            )
        ],
        graph=parse_trace_graph(baseline),
        representation_ids=["REP_SYNTH_TRACE"],
        applicability_after={"SYN_OBL_TRACE": "ACTIVE"},
        mandatory_obligations=[],
        covered_obligations=[],
    )
    second = analyze_impact(
        architecture_before_sha=fixture["architecture_before_sha"],
        architecture_after_sha=fixture["architecture_after_sha"],
        policy_source_revision=fixture["policy_source_revision"],
        policy_bundle_sha256=fixture["policy_bundle_sha256"],
        ruleset_sha256=fixture["ruleset_sha256"],
        snapshot_sha256=fixture["snapshot_sha256"],
        changes=[
            ChangeRecord(
                "change:fact", "fact", "SYN_FACT_CAPABILITY_BOUNDARY", ChangeKind.VALUE_CHANGED
            )
        ],
        graph=parse_trace_graph(expanded),
        representation_ids=["REP_SYNTH_TRACE"],
        applicability_after={"SYN_OBL_TRACE": "ACTIVE"},
        mandatory_obligations=[],
        covered_obligations=[],
    )
    assert first.representations == second.representations


def test_input_permutations_preserve_graph_and_impact_digests() -> None:
    fixture = load_synthetic_fixture()
    graph = copy.deepcopy(fixture["trace_graph"])
    reversed_graph = copy.deepcopy(graph)
    reversed_graph["nodes"].reverse()
    reversed_graph["edges"].reverse()
    change = ChangeRecord(
        "change:fact", "fact", "SYN_FACT_CAPABILITY_BOUNDARY", ChangeKind.VALUE_CHANGED
    )
    values = dict(
        architecture_before_sha=fixture["architecture_before_sha"],
        architecture_after_sha=fixture["architecture_after_sha"],
        policy_source_revision=fixture["policy_source_revision"],
        policy_bundle_sha256=fixture["policy_bundle_sha256"],
        ruleset_sha256=fixture["ruleset_sha256"],
        snapshot_sha256=fixture["snapshot_sha256"],
        representation_ids=["REP_SYNTH_TRACE"],
        applicability_after={"SYN_OBL_TRACE": "ACTIVE"},
        mandatory_obligations=["SYN_OBL_TRACE"],
        covered_obligations=["SYN_OBL_TRACE"],
    )
    left = analyze_impact(changes=[change], graph=parse_trace_graph(graph), **values)
    right = analyze_impact(changes=[change], graph=parse_trace_graph(reversed_graph), **values)
    assert left.assessment_sha256 == right.assessment_sha256
