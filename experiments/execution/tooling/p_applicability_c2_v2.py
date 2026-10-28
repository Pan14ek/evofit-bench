"""Versioned exact-set closure hook for the C2 V2 TEST_ONLY lane."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

from experiments.execution.tooling import p_applicability as core
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.p_applicability import (
    ApplicabilityAssessment,
    CompiledRuleset,
    EvidenceLedger,
    ProofStatus,
)
from experiments.execution.tooling.p_input_validation import SnapshotValidationResult


def verify_exact_test_only_claims(
    snapshot: Mapping[str, Any],
    exact_obligation_ids: frozenset[str],
    profile_id: str,
    target_scope: str,
    ledger: EvidenceLedger,
) -> tuple[bool, set[str], set[str], set[str]]:
    """Require exactly one source-bound claim per selected obligation and state."""
    refs: set[str] = set()
    claims_value = snapshot.get("completeness_claims", [])
    registry = snapshot.get("policy_registry")
    claim_ids_value = registry.get("closure_claim_ids") if isinstance(registry, Mapping) else None
    if (
        not exact_obligation_ids
        or not profile_id
        or not isinstance(registry, Mapping)
        or snapshot.get("schema_version") != "1.2"
        or registry.get("closure") != "CLAIMED_CLOSED"
        or registry.get("registry_version") != profile_id
        or registry.get("scope") != target_scope
        or not isinstance(claims_value, list)
        or not isinstance(claim_ids_value, list)
    ):
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, set()

    claim_ids = [value for value in claim_ids_value if isinstance(value, str)]
    claim_rows = [value for value in claims_value if isinstance(value, Mapping)]
    unresolved = set(claim_ids)
    if (
        len(claim_ids) != len(claim_ids_value)
        or len(claim_ids) != len(set(claim_ids))
        or len(claim_rows) != len(claims_value)
        or len(claim_rows) != 2 * len(exact_obligation_ids)
        or set(claim_ids) != {str(row.get("id", "")) for row in claim_rows}
    ):
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, unresolved

    architecture = snapshot.get("architecture")
    if not isinstance(architecture, Mapping):
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, unresolved
    as_of = registry.get("as_of")
    if as_of != architecture.get("evaluation_as_of"):
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, unresolved

    allowed_fact_types = {f"obligation:{item}" for item in exact_obligation_ids}
    seen_pairs: set[tuple[str, str]] = set()
    valid_refs: set[str] = set()
    for claim in claim_rows:
        claim_id = str(claim.get("id", ""))
        fact_type = claim.get("fact_type")
        q = fact_type.removeprefix("obligation:") if isinstance(fact_type, str) else ""
        state = claim.get("state")
        source_ids = claim.get("evidence_source_ids")
        if (
            claim.get("kind") != "AUTHORITATIVE_POLICY_REGISTRY"
            or fact_type not in allowed_fact_types
            or state not in {"before", "after"}
            or (q, str(state)) in seen_pairs
            or claim.get("scope") != target_scope
            or claim.get("architecture_revision")
            != architecture.get("before_commit" if state == "before" else "after_commit")
            or claim.get("policy_registry_version") != profile_id
            or claim.get("as_of") != as_of
            or claim.get("assumptions") != [f"bounded_obligation_universe:{q}"]
            or not isinstance(source_ids, list)
            or not source_ids
            or any(not isinstance(source_id, str) for source_id in source_ids)
        ):
            return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, unresolved
        expected_sources = core._source_bindings(snapshot, source_ids)
        proof = ledger.completeness_proofs.get(claim_id)
        if (
            len(expected_sources) != len(source_ids)
            or proof is None
            or proof.status is not ProofStatus.VALID
            or proof.verifier_id != profile_id
            or not core._proof_matches(proof, claim, expected_sources)
            or not proof.evidence_refs
        ):
            return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, unresolved
        seen_pairs.add((q, str(state)))
        valid_refs.update(proof.evidence_refs)
        valid_refs.update(core._stable_refs(source_ids))
        valid_refs.add(claim_id)

    expected_pairs = {
        (obligation_id, state)
        for obligation_id in exact_obligation_ids
        for state in ("before", "after")
    }
    if seen_pairs != expected_pairs:
        return False, {"POLICY_CLOSURE_UNVERIFIED"}, refs, unresolved
    return True, set(), valid_refs, set()


def evaluate_obligations_exact_test_only_set(
    snapshot: Mapping[str, Any],
    compiled_rules: CompiledRuleset,
    evidence_ledger: EvidenceLedger,
    target_state: str,
    input_validation: SnapshotValidationResult,
    *,
    policy_source_revision: str,
    policy_bundle_sha256: str | None,
    exact_obligation_ids: frozenset[str],
    profile_id: str,
    target_scope: str | None = None,
) -> ApplicabilityAssessment:
    """Use a versioned closure hook while preserving the original snapshot bytes."""
    global _EXACT_OBLIGATION_IDS, _EXACT_PROFILE_ID
    catalog_ids = {row.obligation_id for row in compiled_rules.obligations}
    if (
        not exact_obligation_ids
        or not exact_obligation_ids.issubset(catalog_ids)
        or policy_source_revision != profile_id
    ):
        raise ContractValidationError("P03_TEST_ONLY_EXACT_APPLICABILITY_SCOPE_INVALID")
    registry = snapshot.get("policy_registry")
    if not isinstance(registry, Mapping):
        raise ContractValidationError("P03_TEST_ONLY_EXACT_APPLICABILITY_REGISTRY_INVALID")
    scope = target_scope or str(registry.get("scope", ""))
    previous_ids, previous_profile = _EXACT_OBLIGATION_IDS, _EXACT_PROFILE_ID
    _EXACT_OBLIGATION_IDS, _EXACT_PROFILE_ID = exact_obligation_ids, profile_id
    try:
        assessment = _load_engine().evaluate_obligations(
            snapshot,
            compiled_rules,
            evidence_ledger,
            target_state,
            input_validation,
            policy_source_revision=policy_source_revision,
            policy_bundle_sha256=policy_bundle_sha256,
            target_scope=scope,
        )
    finally:
        _EXACT_OBLIGATION_IDS, _EXACT_PROFILE_ID = previous_ids, previous_profile
    if any(
        row.obligation_id not in exact_obligation_ids and row.status.value != "UNKNOWN"
        for row in assessment.results
    ):
        raise ContractValidationError("P03_TEST_ONLY_OUTSIDE_SCOPE_NOT_UNKNOWN")
    return assessment


def _load_engine() -> ModuleType:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    source_path = Path(core.__file__).resolve(strict=True)
    spec = importlib.util.spec_from_file_location(_ENGINE_MODULE_NAME, source_path)
    if spec is None or spec.loader is None:
        raise ContractValidationError("P03_TEST_ONLY_EXACT_APPLICABILITY_ENGINE_UNAVAILABLE")
    engine = importlib.util.module_from_spec(spec)
    sys.modules[_ENGINE_MODULE_NAME] = engine
    try:
        spec.loader.exec_module(engine)
    except Exception:
        sys.modules.pop(_ENGINE_MODULE_NAME, None)
        raise

    for name in (
        "TruthValue",
        "ApplicabilityStatus",
        "ProofStatus",
        "Obligation",
        "EvidenceProof",
        "EvidenceLedger",
        "CompiledRuleset",
        "ConditionResult",
        "ObligationResult",
        "ApplicabilityAssessment",
    ):
        setattr(engine, name, getattr(core, name))
    original_closure = engine._registry_closed_for

    def exact_registry_closed_for(
        obligation_id: str,
        criterion: str,
        obligation_catalog_sha256: str,
        target_state: str,
        target_scope: str,
        snapshot: Mapping[str, Any],
        registry: Mapping[str, Any],
        ledger: EvidenceLedger,
    ) -> tuple[bool, set[str], set[str], set[str]]:
        if obligation_id not in _EXACT_OBLIGATION_IDS:
            return original_closure(
                obligation_id,
                criterion,
                obligation_catalog_sha256,
                target_state,
                target_scope,
                snapshot,
                registry,
                ledger,
            )
        if registry.get("registry_version") != _EXACT_PROFILE_ID:
            return False, {"POLICY_CLOSURE_UNVERIFIED"}, set(), set()
        valid, reasons, refs, unresolved = verify_exact_test_only_claims(
            snapshot,
            _EXACT_OBLIGATION_IDS,
            _EXACT_PROFILE_ID,
            target_scope,
            ledger,
        )
        if not valid:
            return False, reasons, refs, unresolved
        return True, set(), refs, set()

    engine._registry_closed_for = exact_registry_closed_for
    _ENGINE = engine
    return engine


_ENGINE_MODULE_NAME = "_evofit_p_applicability_c2_v2_engine"
_ENGINE: ModuleType | None = None
_EXACT_OBLIGATION_IDS: frozenset[str] = frozenset()
_EXACT_PROFILE_ID = ""
