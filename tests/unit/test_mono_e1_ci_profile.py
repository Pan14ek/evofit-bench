"""Structural safeguards for the public, non-authoritative MONO-E1 CI profile.

These tests do not produce a reference, run Method P, or approve a scientific
experiment. No private oracle data is read.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "docs" / "mono_e1_ci_fitness_profile_v1.json"
CATALOG = ROOT / "fitness" / "catalog" / "architectural-obligations.yaml"
CHECKPOINT = ROOT / "architecture" / "acceptance" / "a1" / "a0_4_canonical_checkpoint.json"

BEFORE_SHA = "26a9bb667da7d0938e38aca15d2bf29fd1de4829"
AFTER_SHA = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"


def load_profile() -> dict:
    return json.loads(PROFILE.read_text(encoding="utf-8"))


def catalog_ids() -> list[str]:
    # This deliberately mirrors the existing ordered catalog's simple `- id:`
    # rows; it does not infer any obligation's normative applicability.
    content = CATALOG.read_text(encoding="utf-8")
    return re.findall(r"(?m)^  - id: ([A-Z][A-Z0-9_]+)\\s*$", content)


def validate_preparation_only(profile: dict) -> list[str]:
    """Report fail-closed violations in the candidate public protocol."""
    problems: list[str] = []
    if profile.get("profile_status") != "DRAFT_NON_AUTHORITATIVE":
        problems.append("unsupported_profile_approval")
    if profile.get("experimental_go") != "NO_GO" or profile.get("measured_run_status") != "NOT_EXECUTED":
        problems.append("unapproved_experiment")
    if not profile.get("proposal_only") or profile.get("confidentiality", {}).get("method_input_authorized") is not False:
        problems.append("incorrect_scope")
    if (profile.get("source_pair", {}).get("before", {}).get("commit") != BEFORE_SHA
        or profile.get("source_pair", {}).get("after", {}).get("commit") != AFTER_SHA):
        problems.append("wrong_source_revision")
    lc = profile.get("lifecycle", {})
    if (lc.get("candidate_stage") != "CI_TEST" or lc.get("stage_scope_approved") is not False
        or lc.get("approved_registry_id") is not None):
        problems.append("unreviewed_stage_approval")
    fs = profile.get("fitness_scope", {})
    actual = fs.get("obligations", [])
    if [row.get("id") for row in actual] != catalog_ids() or len(actual) != 18:
        problems.append("catalog_universe_mismatch")
    if any(
        row.get("applicability") != "UNKNOWN"
        or row.get("mandatory") != "UNRESOLVED"
        or row.get("required_stages") != "UNDECIDED"
        or row.get("policy_authority") != "NOT_APPROVED"
        or row.get("exact_pair_proof") != "NOT_ESTABLISHED"
        for row in actual
    ):
        problems.append("invented_obligation_decision")
    if fs.get("scientific_q_a04_denominator") != "NOT_ESTABLISHED" or fs.get("catalog_closure") != "UNVERIFIED":
        problems.append("unsupported_complete_denominator")
    evs = fs.get("engineering_evaluators", [])
    if [v.get("id") for v in evs] != ["AC_PUBLIC_API", "AC_MODULE_GRAPH"]:
        problems.append("unexpected_evaluator_inventory")
    if any(v.get("representation_id") is not None or v.get("semantic_pair_review") != "PENDING"
           or v.get("evidence_status") != "BOUNDED_ENGINEERING_ONLY" for v in evs):
        problems.append("invented_exact_pair_proof")
    if profile.get("endpoints", {}).get("architectural_coverage", {}).get("status") != "NOT_EVALUABLE":
        problems.append("unsupported_coverage_claim")
    if profile.get("arms", {}).get("common_after_sha") != AFTER_SHA:
        problems.append("inconsistent_target")
    if any(profile.get("arms", {}).get(arm, {}).get("input_bundle_digest") is not None
           or profile.get("arms", {}).get(arm, {}).get("allowlist_digest") is not None
           for arm in ("B0", "P")):
        problems.append("fabricated_inputs")
    ready = profile.get("readiness", {})
    if (ready.get("G1") != "INCOMPLETE" or ready.get("G4") != "NOT_AUTHORIZED"
        or ready.get("reference") != "NOT_FROZEN"
        or ready.get("method_p_status") != "NOT_READY"):
        problems.append("unauthorized_gate")
    conf = profile.get("confidentiality", {})
    if conf.get("oracle_labels_included") is not False or conf.get("scorer_reference_included") is not False:
        problems.append("oracle_exposure")
    return problems


def test_profile_is_catalog_complete_but_never_scientifically_approved() -> None:
    profile = load_profile()
    ids = catalog_ids()
    assert len(ids) == len(set(ids)) == 18
    assert validate_preparation_only(profile) == []


def test_canonical_source_pair_matches_readback() -> None:
    profile = load_profile()
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    bound = checkpoint["source_pair"]
    assert profile["source_pair"]["before"]["commit"] == bound["before"]["source_sha"]
    assert profile["source_pair"]["before"]["tree"] == bound["before"]["repository_tree_sha"]
    assert profile["source_pair"]["after"]["commit"] == bound["after"]["source_sha"]
    assert profile["source_pair"]["after"]["tree"] == bound["after"]["repository_tree_sha"]


@pytest.mark.parametrize(
    ("location", "value", "expected"),
    [
        (("profile_status",), "APPROVED", "unsupported_profile_approval"),
        (("experimental_go",), "GO", "unapproved_experiment"),
        (("lifecycle", "stage_scope_approved"), True, "unreviewed_stage_approval"),
        (("fitness_scope", "scientific_q_a04_denominator"), 2, "unsupported_complete_denominator"),
        (("fitness_scope", "obligations", 0, "mandatory"), "MANDATORY", "invented_obligation_decision"),
        (("fitness_scope", "engineering_evaluators", 0, "semantic_pair_review"), "APPROVED", "invented_exact_pair_proof"),
        (("readiness", "G1"), "COMPLETE", "unauthorized_gate"),
        (("readiness", "reference"), "FROZEN", "unauthorized_gate"),
        (("arms", "B0", "input_bundle_digest"), "0" * 64, "fabricated_inputs"),
        (("confidentiality", "oracle_labels_included"), True, "oracle_exposure"),
    ],
)
def test_illicit_approval_or_fabricated_readiness_is_rejected(
    location: tuple, value: object, expected: str,
) -> None:
    profile = copy.deepcopy(load_profile())
    cursor = profile
    for key in location[:-1]:
        cursor = cursor[key]
    cursor[location[-1]] = value
    assert expected in validate_preparation_only(profile)
