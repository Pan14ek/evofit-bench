"""C2 V2 exact-set adapter over the unchanged DEVELOPMENT Method Ψ engine."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

from experiments.execution.tooling import p_adaptation as _v1
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.p_adaptation_evidence import VerifiedAdaptationEvidence
from experiments.execution.tooling.p_applicability import ApplicabilityAssessment
from experiments.execution.tooling.p_applicability_c2_v2 import (
    evaluate_obligations_exact_test_only_set,
)

PROFILE_ID = "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_PROFILE_V2"
METHOD_VERSION = "P_GOVERNED_ADAPTATION_DEVELOPMENT_V2_TEST_ONLY_EXACT_SET"
_ENGINE_MODULE_NAME = "_evofit_p_adaptation_c2_v2_engine"
_SHARED_VERIFICATION_REGISTRIES = (
    "_VERIFIED_V3_BUNDLE_DIGESTS",
    "_TEST_ONLY_BUNDLE_DIGESTS",
    "_BUNDLE_EVIDENCE_VERIFIER_REGISTRIES",
)
_ENGINE: ModuleType | None = None


def run_adaptation_c2_v2(bundle: Any, *, evidence_context: Mapping[str, Any] | None = None) -> Any:
    """Run the frozen core with exact-set applicability and scoped invariants."""
    if (
        bundle.trust_scope != "TEST_ONLY"
        or bundle.manifest.get("policy_source_revision") != PROFILE_ID
    ):
        raise ContractValidationError("P03_TEST_ONLY_EXACT_METHOD_IDENTITY_INVALID")
    engine = _load_engine()
    return engine.run_adaptation(bundle, evidence_context=evidence_context)


def _load_engine() -> ModuleType:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    source_path = Path(_v1.__file__).resolve(strict=True)
    spec = importlib.util.spec_from_file_location(_ENGINE_MODULE_NAME, source_path)
    if spec is None or spec.loader is None:
        raise ContractValidationError("P03_TEST_ONLY_EXACT_METHOD_SOURCE_UNAVAILABLE")
    engine = importlib.util.module_from_spec(spec)
    sys.modules[_ENGINE_MODULE_NAME] = engine
    try:
        spec.loader.exec_module(engine)
    except Exception:
        sys.modules.pop(_ENGINE_MODULE_NAME, None)
        raise

    for name in _SHARED_VERIFICATION_REGISTRIES:
        setattr(engine, name, getattr(_v1, name))
    original_effective = engine._effective_obligations
    original_invariants = engine._invariant_verdicts
    selected_scope: set[str] = set()

    def scoped_effective_obligations(
        obligations: Sequence[Mapping[str, Any]],
        classifications: Mapping[str, bool],
        verified_evidence: VerifiedAdaptationEvidence | None,
    ) -> tuple[Mapping[str, Any], ...]:
        effective = original_effective(obligations, classifications, verified_evidence)
        if (
            verified_evidence is None
            or verified_evidence.trust_scope != "TEST_ONLY"
            or verified_evidence.schema_version != 2
        ):
            raise ContractValidationError("P03_TEST_ONLY_EXACT_APPLICABILITY_SCOPE_INVALID")
        selected_scope.clear()
        selected_scope.update(
            obligation_id
            for obligation_id, mandatory in classifications.items()
            if mandatory is True
        )
        if not selected_scope:
            raise ContractValidationError("P03_TEST_ONLY_EXACT_APPLICABILITY_SCOPE_INVALID")
        return tuple(row for row in effective if str(row.get("id")) in selected_scope)

    def exact_evaluate_obligations(
        snapshot: Mapping[str, Any],
        compiled_rules: Any,
        evidence_ledger: Any,
        target_state: str,
        input_validation: Any,
        **kwargs: Any,
    ) -> ApplicabilityAssessment:
        policy_revision = kwargs.get("policy_source_revision")
        if policy_revision != PROFILE_ID or not selected_scope:
            raise ContractValidationError("P03_TEST_ONLY_EXACT_APPLICABILITY_SCOPE_INVALID")
        return evaluate_obligations_exact_test_only_set(
            snapshot,
            compiled_rules,
            evidence_ledger,
            target_state,
            input_validation,
            policy_source_revision=str(policy_revision),
            policy_bundle_sha256=kwargs.get("policy_bundle_sha256"),
            exact_obligation_ids=frozenset(selected_scope),
            profile_id=PROFILE_ID,
            target_scope=kwargs.get("target_scope"),
        )

    def scoped_invariants(**kwargs: Any) -> dict[str, str]:
        if not selected_scope:
            raise ContractValidationError("P03_TEST_ONLY_EXACT_APPLICABILITY_SCOPE_INVALID")
        scoped = dict(kwargs)
        for key in ("before_applicability", "after_applicability"):
            assessment = scoped[key]
            scoped[key] = replace(
                assessment,
                results=tuple(
                    row for row in assessment.results if row.obligation_id in selected_scope
                ),
            )
        if {str(row.get("id")) for row in scoped["obligations"]} != selected_scope:
            raise ContractValidationError("P03_TEST_ONLY_EXACT_INVARIANT_SCOPE_MISMATCH")
        return original_invariants(**scoped)

    engine._effective_obligations = scoped_effective_obligations
    engine.evaluate_obligations = exact_evaluate_obligations
    engine._invariant_verdicts = scoped_invariants
    engine.METHOD_VERSION = METHOD_VERSION
    _ENGINE = engine
    return engine
