"""Unit tests for closed AR-DSL compilation and Strong Kleene fact evaluation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import load_schema
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.p_applicability import (
    CompiledRuleset,
    ProofStatus,
    TruthValue,
    evaluate_condition,
    load_and_validate_ruleset,
    tri_and,
    tri_not,
    tri_or,
)
from experiments.execution.tooling.p_input_validation import load_fact_vocabulary
from tests.unit.p_applicability_support import (
    add_fact,
    close_facts_for,
    evidence_ledger,
    proof_for,
    snapshot_fixture,
)

RULESET_PATH = Path("experiments/execution/contracts/applicability_ruleset_v1.json")
CATALOG_PATH = Path("fitness/catalog/architectural-obligations.yaml")


def _compiled(path: Path = RULESET_PATH) -> CompiledRuleset:
    return load_and_validate_ruleset(path, load_fact_vocabulary(), CATALOG_PATH)


def _write_ruleset(tmp_path: Path, mutate: Any) -> Path:
    raw = json.loads(RULESET_PATH.read_text(encoding="utf-8"))
    mutate(raw)
    path = tmp_path / "rules.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return path


def test_strong_kleene_tables_are_complete_and_commutative() -> None:
    values = [TruthValue.TRUE, TruthValue.FALSE, TruthValue.UNKNOWN]
    and_expected = {
        (TruthValue.TRUE, TruthValue.TRUE): TruthValue.TRUE,
        (TruthValue.TRUE, TruthValue.FALSE): TruthValue.FALSE,
        (TruthValue.TRUE, TruthValue.UNKNOWN): TruthValue.UNKNOWN,
        (TruthValue.FALSE, TruthValue.TRUE): TruthValue.FALSE,
        (TruthValue.FALSE, TruthValue.FALSE): TruthValue.FALSE,
        (TruthValue.FALSE, TruthValue.UNKNOWN): TruthValue.FALSE,
        (TruthValue.UNKNOWN, TruthValue.TRUE): TruthValue.UNKNOWN,
        (TruthValue.UNKNOWN, TruthValue.FALSE): TruthValue.FALSE,
        (TruthValue.UNKNOWN, TruthValue.UNKNOWN): TruthValue.UNKNOWN,
    }
    or_expected = {
        (TruthValue.TRUE, TruthValue.TRUE): TruthValue.TRUE,
        (TruthValue.TRUE, TruthValue.FALSE): TruthValue.TRUE,
        (TruthValue.TRUE, TruthValue.UNKNOWN): TruthValue.TRUE,
        (TruthValue.FALSE, TruthValue.TRUE): TruthValue.TRUE,
        (TruthValue.FALSE, TruthValue.FALSE): TruthValue.FALSE,
        (TruthValue.FALSE, TruthValue.UNKNOWN): TruthValue.UNKNOWN,
        (TruthValue.UNKNOWN, TruthValue.TRUE): TruthValue.TRUE,
        (TruthValue.UNKNOWN, TruthValue.FALSE): TruthValue.UNKNOWN,
        (TruthValue.UNKNOWN, TruthValue.UNKNOWN): TruthValue.UNKNOWN,
    }
    for left in values:
        for right in values:
            assert tri_and([left, right]) is and_expected[(left, right)]
            assert tri_and([left, right]) is tri_and([right, left])
            assert tri_or([left, right]) is or_expected[(left, right)]
            assert tri_or([left, right]) is tri_or([right, left])
    assert [tri_not(value) for value in values] == [
        TruthValue.FALSE,
        TruthValue.TRUE,
        TruthValue.UNKNOWN,
    ]
    assert tri_not(tri_not(TruthValue.UNKNOWN)) is TruthValue.UNKNOWN
    assert tri_or([TruthValue.UNKNOWN, tri_not(TruthValue.UNKNOWN)]) is TruthValue.UNKNOWN
    assert tri_and([TruthValue.FALSE, TruthValue.UNKNOWN]) is TruthValue.FALSE
    assert tri_or([TruthValue.TRUE, TruthValue.UNKNOWN]) is TruthValue.TRUE


def test_ruleset_schema_and_catalog_are_pinned_and_generic() -> None:
    rules = _compiled()
    Draft202012Validator.check_schema(load_schema("applicability_ruleset_v1.schema.json"))
    assert len(rules.obligations) == 18
    assert len(rules.conditions) == 5
    assert rules.ruleset_version == "AR_V1_CANDIDATE_PILOT_1"
    assert "AC_PUBLIC_API" not in rules.conditions
    assert "scenario_id" not in RULESET_PATH.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: raw.update({"scenario_id": "NO"}),
        lambda raw: raw["conditions"][0]["expression"].update({"op": "fact_eq"}),
        lambda raw: raw["conditions"][0]["expression"].update({"hidden": "NO"}),
        lambda raw: raw["conditions"][0]["expression"]["selector"].update(
            {"predicate": "communication.remote_synchronous_call"}
        ),
        lambda raw: raw["conditions"][0]["expression"]["selector"].update({"scope": "source:app"}),
        lambda raw: raw["conditions"][0].update({"fact_dependencies": []}),
    ],
)
def test_ruleset_rejects_unknown_fields_operator_reserved_predicates_and_bad_types(
    tmp_path: Path, mutate: Any
) -> None:
    path = _write_ruleset(tmp_path, mutate)
    with pytest.raises(ContractValidationError):
        load_and_validate_ruleset(path, load_fact_vocabulary(), CATALOG_PATH)


def test_ruleset_rejects_bool_numeric_literal_and_ast_resource_overflow(tmp_path: Path) -> None:
    bad_literal = _write_ruleset(
        tmp_path / "literal",
        lambda raw: raw["conditions"][0]["expression"].update({"expected": True}),
    )
    with pytest.raises(ContractValidationError):
        load_and_validate_ruleset(bad_literal, load_fact_vocabulary(), CATALOG_PATH)

    def deep_not(raw: dict[str, Any]) -> None:
        expression = raw["conditions"][0]["expression"]
        for _ in range(12):
            expression = {"op": "not", "arg": expression}
        raw["conditions"][0]["expression"] = expression

    deep = _write_ruleset(tmp_path / "depth", deep_not)
    with pytest.raises(ContractValidationError, match="depth"):
        load_and_validate_ruleset(deep, load_fact_vocabulary(), CATALOG_PATH)


def test_ruleset_digest_is_stable_under_json_object_key_reordering(tmp_path: Path) -> None:
    raw = json.loads(RULESET_PATH.read_text(encoding="utf-8"))
    reordered = dict(reversed(list(raw.items())))
    path = tmp_path / "reordered.json"
    path.write_text(json.dumps(reordered, ensure_ascii=False), encoding="utf-8")
    assert _compiled().ruleset_sha256 == _compiled(path).ruleset_sha256


def test_compiled_ruleset_ast_is_recursively_immutable() -> None:
    compiled = _compiled()
    with pytest.raises(TypeError):
        compiled.conditions["COND_DECLARED_MULTI_UNIT"]["id"] = "MUTATED"  # type: ignore[index]
    expression = compiled.conditions["COND_DECLARED_MULTI_UNIT"]["expression"]
    with pytest.raises(TypeError):
        expression["expected"] = 0


def test_declared_numeric_fact_can_answer_only_its_declared_predicate() -> None:
    snapshot = snapshot_fixture()
    ledger = evidence_ledger(snapshot)
    result = evaluate_condition("COND_DECLARED_MULTI_UNIT", "after", snapshot, _compiled(), ledger)
    assert result.truth is TruthValue.FALSE
    assert result.fact_ids == ("F_DEPLOYMENT",)
    assert "ARCH_OBS" in result.evidence_refs


def test_missing_fact_is_unknown_until_exact_scope_closure_is_verified() -> None:
    snapshot = snapshot_fixture()
    ledger = evidence_ledger(snapshot)
    missing = evaluate_condition(
        "COND_HAS_CAPABILITY_MODULE", "after", snapshot, _compiled(), ledger
    )
    assert missing.truth is TruthValue.UNKNOWN
    assert "FACT_MISSING" in missing.reason_codes
    assert "NEGATIVE_EVIDENCE_INSUFFICIENT" in missing.reason_codes

    claim = close_facts_for(snapshot, "component.capability_module")
    closed_ledger = evidence_ledger(snapshot)
    absence = evaluate_condition(
        "COND_HAS_CAPABILITY_MODULE", "after", snapshot, _compiled(), closed_ledger
    )
    assert absence.truth is TruthValue.FALSE
    assert claim["id"] in absence.evidence_refs


def test_unverified_unknown_and_wrong_state_facts_do_not_collapse_to_false() -> None:
    snapshot = snapshot_fixture()
    unknown_fact = next(row for row in snapshot["facts"] if row["id"] == "F_BROKER")
    result = evaluate_condition(
        "COND_HAS_SHARED_INFRASTRUCTURE", "after", snapshot, _compiled(), evidence_ledger(snapshot)
    )
    assert result.truth is TruthValue.UNKNOWN

    ledger = evidence_ledger(snapshot)
    from dataclasses import replace

    unverified = replace(ledger, fact_proofs={})
    numeric = evaluate_condition(
        "COND_DECLARED_MULTI_UNIT", "after", snapshot, _compiled(), unverified
    )
    assert numeric.truth is TruthValue.UNKNOWN
    assert "FACT_UNVERIFIED" in numeric.reason_codes

    wrong_state = evaluate_condition(
        "COND_DECLARED_MULTI_UNIT", "before", snapshot, _compiled(), ledger
    )
    assert wrong_state.truth is TruthValue.UNKNOWN
    assert "FACT_SCOPE_MISMATCH" in wrong_state.reason_codes
    assert unknown_fact["value"] is None


def test_contradictory_functional_facts_force_unknown_and_conflict() -> None:
    snapshot = snapshot_fixture()
    add_fact(
        snapshot,
        fact_id="F_DEPLOYMENT_CONFLICT",
        predicate="deployment.unit_count_declared",
        value=2,
    )
    result = evaluate_condition(
        "COND_DECLARED_MULTI_UNIT", "after", snapshot, _compiled(), evidence_ledger(snapshot)
    )
    assert result.truth is TruthValue.UNKNOWN
    assert "FACT_CONFLICT" in result.reason_codes


def test_bool_is_not_accepted_as_an_integer_fact() -> None:
    snapshot = snapshot_fixture()
    fact = next(row for row in snapshot["facts"] if row["id"] == "F_DEPLOYMENT")
    fact["value"] = True
    source_binding = ["ARCH_OBS"]
    ledger = evidence_ledger(snapshot)
    from dataclasses import replace

    invalid_proof = proof_for(
        ProofStatus.VALID,
        fact,
        snapshot,
        source_binding,
    )
    ledger = replace(ledger, fact_proofs={"F_DEPLOYMENT": invalid_proof})
    result = evaluate_condition("COND_DECLARED_MULTI_UNIT", "after", snapshot, _compiled(), ledger)
    assert result.truth is TruthValue.UNKNOWN
    assert "FACT_CONFLICT" in result.reason_codes


def test_set_size_uses_the_typed_declared_set() -> None:
    snapshot = snapshot_fixture()
    add_fact(
        snapshot,
        fact_id="F_SHARED_INFRA",
        predicate="component.shared_infrastructure",
        value=["app.config", "app.database"],
    )
    result = evaluate_condition(
        "COND_SHARED_INFRASTRUCTURE_NONEMPTY",
        "after",
        snapshot,
        _compiled(),
        evidence_ledger(snapshot),
    )
    assert result.truth is TruthValue.TRUE


def test_assessment_digest_ignores_fact_order_and_paths_are_not_emitted() -> None:
    from experiments.execution.tooling.p_applicability import (
        canonical_assessment_bytes,
        evaluate_obligations,
    )
    from tests.unit.p_applicability_support import validation_result

    snapshot = snapshot_fixture()
    rules = _compiled()
    report_a = evaluate_obligations(
        snapshot, rules, evidence_ledger(snapshot), "after", validation_result(snapshot)
    )
    reordered = copy.deepcopy(snapshot)
    reordered["facts"].reverse()
    reordered["sources"].reverse()
    report_b = evaluate_obligations(
        reordered, rules, evidence_ledger(reordered), "after", validation_result(reordered)
    )
    assert report_a.common_input_sha256 == report_b.common_input_sha256
    assert canonical_assessment_bytes(report_a) == canonical_assessment_bytes(report_b)
    assert b"/private/tmp" not in canonical_assessment_bytes(report_a)
