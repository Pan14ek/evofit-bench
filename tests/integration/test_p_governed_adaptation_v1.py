"""End-to-end synthetic orchestration through SPEC 02 without DA01 sources."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.p_adaptation import VerifiedPBundle, run_adaptation
from experiments.execution.tooling.p_applicability import (
    CompiledRuleset,
    EvidenceLedger,
    Obligation,
)
from experiments.execution.tooling.p_impact import parse_trace_graph
from experiments.execution.tooling.p_input_validation import (
    SnapshotValidationResult,
    ValidationStatus,
)
from tests.unit.p_spec03_support import FIXTURE_PATH, make_obligation


def synthetic_verified_bundle(*, tamper_validation_digest: bool = False) -> VerifiedPBundle:
    """Use only independent TEST_ONLY inputs; OPEN authority should remain UNKNOWN."""
    snapshot = {
        "schema_version": "1.1",
        "contract_id": "VERSIONED_ARCH_POLICY_SNAPSHOT_V1_1",
        "architecture": {
            "before_commit": "1" * 40,
            "after_commit": "2" * 40,
            "before_tree": "3" * 40,
            "after_tree": "4" * 40,
            "evaluation_as_of": "2026-01-01T00:00:00Z",
        },
        "sources": [
            {
                "id": "SYN_SOURCE_ARCH",
                "path": "synthetic/architecture.json",
                "sha256": "6" * 64,
                "kind": "ARCHITECTURE_SOURCE",
                "producer": "TEST_ONLY",
            }
        ],
        "facts": [],
        "policies": [],
        "policy_registry": {
            "scope": "service:synth",
            "source_id": "SYN_REGISTRY_SOURCE",
            "closure": "OPEN",
            "closure_claim_id": None,
            "authority_charter_source_id": "SYN_CHARTER_SOURCE",
            "registry_version": "SYN_REGISTRY_V1",
            "as_of": "2026-01-01T00:00:00Z",
        },
        "completeness_claims": [],
        "fact_vocabulary_version": "FV_CORE_V1",
    }
    obligation = make_obligation()
    ruleset = CompiledRuleset(
        "SYN_RULESET_V1",
        "FV_CORE_V1",
        "5" * 64,
        "7" * 64,
        "8" * 64,
        {},
        {},
        (Obligation(obligation["id"], obligation["criterion"]),),
    )
    snapshot_digest = sha256_bytes(pretty_json_bytes(snapshot))
    validation = SnapshotValidationResult(
        ValidationStatus.VALID,
        ValidationStatus.VALID,
        ValidationStatus.VALID,
        ValidationStatus.VALID,
        ValidationStatus.VALID,
        (),
        (),
        snapshot_digest,
    )
    if tamper_validation_digest:
        validation = replace(validation, snapshot_digest="9" * 64)
    bundle_digest = bundle_sha256([])
    manifest: dict[str, Any] = {
        "method_id": "P",
        "files": [],
        "bundle_sha256": bundle_digest,
        "policy_bundle_sha256": bundle_digest,
        "common_snapshot_sha256": validation.snapshot_digest,
        "policy_ruleset_sha256": ruleset.ruleset_source_sha256,
        "policy_source_revision": "SYN_POLICY_REV_1",
    }
    parent = {"configuration_version": "SYN_CONFIG_1", "representations": []}
    parent_bytes = canonical_json_bytes(parent)
    return VerifiedPBundle(
        Path("."),
        manifest,
        snapshot,
        validation,
        ruleset,
        EvidenceLedger({}, {}, {}),
        (obligation,),
        (),
        parse_trace_graph(
            {
                "schema_version": 1,
                "inventory_complete": False,
                "nodes": [],
                "edges": [],
            }
        ),
        (),
        {},
        {},
        parent,
        parent_bytes,
        "configs/synthetic-parent.json",
        sha256_bytes(parent_bytes),
        {
            "schema_version": 1,
            "model_version": "SYN_COST_V1",
            "authority_status": "TEST_ONLY",
            "max_incremental_cost": 10,
            "max_search_nodes": 10,
            "candidate_costs": {},
        },
        "TEST_ONLY",
    )


def test_synthetic_pipeline_runs_spec02_and_holds_open_authority_unknown() -> None:
    result = run_adaptation(synthetic_verified_bundle())
    assert result.before_applicability.results[0].status.value == "UNKNOWN"
    assert result.after_applicability.results[0].status.value == "UNKNOWN"
    assert result.current_coverage.status.value == "UNKNOWN"
    assert result.candidate_coverage is not None
    assert result.candidate_coverage.status.value == "UNKNOWN"
    assert result.governance.result.value == "HOLD"
    assert result.candidate is not None
    assert result.candidate["configuration_version"] != "SYN_CONFIG_1"
    assert result.prediction_v1 is None


def test_preflight_rejects_snapshot_validation_from_another_exact_revision() -> None:
    with pytest.raises(ContractValidationError, match="P03_PREFLIGHT_SNAPSHOT_BINDING_MISMATCH"):
        run_adaptation(synthetic_verified_bundle(tamper_validation_digest=True))


def test_preflight_rejects_policy_and_ruleset_digest_substitution() -> None:
    bundle = synthetic_verified_bundle()
    with pytest.raises(ContractValidationError, match="P03_POLICY_BUNDLE_DIGEST_MISMATCH"):
        run_adaptation(
            replace(
                bundle,
                manifest={**bundle.manifest, "policy_bundle_sha256": "9" * 64},
            )
        )
    with pytest.raises(ContractValidationError, match="P03_RULESET_MANIFEST_BINDING_MISMATCH"):
        run_adaptation(
            replace(
                bundle,
                compiled_ruleset=replace(bundle.compiled_ruleset, ruleset_source_sha256="9" * 64),
            )
        )


def test_synthetic_fixture_is_independent_and_contains_no_forbidden_oracle_markers() -> None:
    raw = FIXTURE_PATH.read_bytes().lower()
    forbidden = (
        b"ground_truth",
        b"groundtruth",
        b"expected_operations",
        b"private_checker",
        b"scorer",
    )
    assert not any(marker in raw for marker in forbidden)
    assert b"test_only" in raw
