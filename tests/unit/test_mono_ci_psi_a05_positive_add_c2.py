"""TEST_ONLY input and source-bound policy checks for the C2 condition."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from experiments.execution.tooling import mono_ci_psi_a05_positive_add as positive_add
from experiments.execution.tooling import mono_ci_psi_a05_positive_add_c2 as c2_study
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.p_policy_source_v3 import verify_policy_source_bundle_v3

ROOT = Path(__file__).resolve().parents[2]
C2_PROFILE_PATH = ROOT / c2_study.PROFILE_PATH
C2_PROTOCOL_PATH = ROOT / c2_study.PROTOCOL_JSON


def _profile() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(C2_PROFILE_PATH.read_text(encoding="utf-8")))


def test_c2_profile_and_protocol_are_versioned_and_fail_closed() -> None:
    profile = _profile()
    protocol = json.loads(C2_PROTOCOL_PATH.read_text(encoding="utf-8"))

    positive_add._validate_static_profile(profile)
    validate_payload(c2_study.PROTOCOL_SCHEMA, protocol)
    assert profile["profile_id"] == "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_PROFILE_V1"
    assert profile["canonical_mandatory_projection"]["other_applicability_status"] == "UNKNOWN"
    assert profile["comparison"]["c0_reference"].endswith("OWNER_AUTHORIZED_RESULTS_UK_V2.md")
    assert [row["id"] for row in profile["additional_retain_obligations"]] == [
        "AC_MODULE_GRAPH",
        "AC_PUBLIC_API",
    ]
    assert protocol["repetitions"] == {"warmup": 1, "measured": 3}
    assert protocol["method"]["algorithm_changed"] is False
    assert protocol["c0_reference"]["transition_summary"]["operations"] == []


def test_c2_retain_profile_rejects_changed_configuration_binding() -> None:
    profile = copy.deepcopy(_profile())
    profile["additional_retain_obligations"][0]["configuration_sha256"] = "0" * 64

    with pytest.raises(ContractValidationError):
        positive_add._validate_static_profile(profile)


def test_c2_policy_input_has_only_three_scoped_active_obligations(tmp_path: Path) -> None:
    profile = _profile()
    result = positive_add.create_policy_source(
        ROOT,
        tmp_path / "working",
        tmp_path / "policy-bundle",
        evaluation_as_of=profile["evaluation_as_of"],
        before_sha="d3101c0d3aa9b7b709253b6ec7518416f05f65b9",
        after_sha="37176a42cc099f1f159dc137b85fe3e32b8290d5",
        obligation_catalog_sha256="a" * 64,
        policy_source_revision=positive_add.PROFILE_C2_ID,
    )
    bundle_root = tmp_path / "policy-bundle"
    verified = verify_policy_source_bundle_v3(bundle_root)
    registry = json.loads((bundle_root / "fitness/policy/registry.json").read_text())
    claims = json.loads((bundle_root / "fitness/policy/completeness-claims.json").read_text())
    selected_ids = {
        obligation_id
        for policy in registry["policies"]
        for obligation_id in policy["obligation_ids"]
    }

    assert result["policy_bundle_sha256"] == verified["policy_bundle_sha256"]
    assert registry["closure"] == "CLAIMED_CLOSED"
    assert selected_ids == {"AC_DATA_OWNERSHIP", "AC_MODULE_GRAPH", "AC_PUBLIC_API"}
    assert len(claims) == len(registry["closure_claim_ids"]) == 6
    assert {row["fact_type"] for row in claims} == {
        "obligation:AC_DATA_OWNERSHIP",
        "obligation:AC_MODULE_GRAPH",
        "obligation:AC_PUBLIC_API",
    }


def test_c2_method_runtime_keeps_c1_profile_capability_backward_compatible() -> None:
    from experiments.execution.tooling.mono_ci_psi_transition import RUNTIME_SCHEMAS, RUNTIME_SOURCE

    assert "positive_add_test_only_profile_v1" in RUNTIME_SOURCE
    assert "positive_add_test_only_profile_v2" in RUNTIME_SOURCE
    assert c2_study.PROFILE_SCHEMA in RUNTIME_SCHEMAS
