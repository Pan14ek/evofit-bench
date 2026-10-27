"""Narrow TEST_ONLY profile and V3 input-role checks for the ΔA5 study."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import sha256_file
from experiments.execution.tooling.mono_ci_psi_a05_positive_add import (
    PROFILE_RELATIVE,
    TEMPLATE_ARTIFACT_PATH,
    _validate_profile_binding,
    _validate_static_profile,
)
from experiments.execution.tooling.mono_ci_psi_a05_positive_add_study import (
    _candidate_exercise,
)
from experiments.execution.tooling.mono_ci_psi_transition import (
    _expected_evidence_obligation_ids,
)
from experiments.execution.tooling.p_operations import template_descriptor_sha256
from experiments.execution.tooling.p_policy_source_v3 import _verify_v3_path_role

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = (
    ROOT / "experiments/execution/mono-ci-b0-psi-delta-a5-positive-add-v1/inputs/"
    "POSITIVE_ADD_PROFILE_V1.json"
)


def _profile() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(PROFILE_PATH.read_text(encoding="utf-8")))


def test_positive_add_profile_schema_accepts_the_frozen_scope() -> None:
    _validate_static_profile(_profile())


@pytest.mark.parametrize(
    ("path", "role", "method_id"),
    [
        ("evidence/POSITIVE_ADD_PROFILE_V1.json", "study_profile", "P"),
        (
            "PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP/source-manifest.json",
            "evaluator_artifact",
            "P",
        ),
    ],
)
def test_positive_add_v3_roles_accept_only_the_two_exact_p_paths(
    path: str, role: str, method_id: str
) -> None:
    _verify_v3_path_role(Path(path), role, method_id)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("path", "role", "method_id"),
    [
        ("evidence/OTHER_PROFILE.json", "study_profile", "P"),
        ("evidence/POSITIVE_ADD_PROFILE_V1.json", "completeness_evidence", "P"),
        ("evidence/POSITIVE_ADD_PROFILE_V1.json", "study_profile", "B1"),
    ],
)
def test_positive_add_v3_roles_reject_path_role_or_method_substitution(
    path: str, role: str, method_id: str
) -> None:
    with pytest.raises(ProtocolError):
        _verify_v3_path_role(Path(path), role, method_id)  # type: ignore[arg-type]


def test_positive_add_profile_rejects_global_denominator_expansion() -> None:
    profile = copy.deepcopy(_profile())
    profile["canonical_mandatory_projection"]["global_denominator_or_coverage_claim"] = True
    with pytest.raises(ContractValidationError):
        _validate_static_profile(profile)


def test_positive_add_profile_rejects_unknown_other_obligations_as_false() -> None:
    profile = copy.deepcopy(_profile())
    profile["canonical_mandatory_projection"]["other_applicability_status"] = "INACTIVE"
    with pytest.raises(ContractValidationError):
        _validate_static_profile(profile)


def test_positive_add_bundle_rejects_an_unpinned_study_profile(tmp_path: Path) -> None:
    artifact = b"[]\n"
    profile_bytes = PROFILE_PATH.read_bytes()
    template = {
        "template_id": "TEMPLATE_POSITIVE_ADD_AC_DATA_OWNERSHIP_V1",
        "representation": {},
    }
    source_digest_path = tmp_path / TEMPLATE_ARTIFACT_PATH
    source_digest_path.parent.mkdir(parents=True)
    source_digest_path.write_bytes(artifact)
    profile_path = tmp_path / PROFILE_RELATIVE
    profile_path.parent.mkdir(parents=True)
    profile_path.write_bytes(profile_bytes)
    artifact_digest = sha256_file(source_digest_path)
    capabilities = {
        "generic_candidate_templates": [template],
        "p_cost_model_v1": {
            "max_incremental_cost": 225,
            "max_search_nodes": 2,
            "candidate_costs": {artifact_digest: 225},
        },
        "positive_add_test_only_profile_v1": {
            "profile_id": "MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_PROFILE_V1",
            "study_profile_sha256": sha256_file(profile_path),
            "template": template,
            "template_descriptor_sha256": template_descriptor_sha256(template),
            "evaluator_artifact_path": TEMPLATE_ARTIFACT_PATH,
            "source_manifest_sha256": artifact_digest,
            "selected_obligation_id": "AC_DATA_OWNERSHIP",
            "cost_model": {
                "max_incremental_cost": 225,
                "max_search_nodes": 2,
                "candidate_costs": {artifact_digest: 225},
            },
        },
    }
    (tmp_path / "fitness").mkdir()
    (tmp_path / "fitness/evaluator-capabilities.json").write_text(
        json.dumps(capabilities), encoding="utf-8"
    )
    files = [
        {
            "path": TEMPLATE_ARTIFACT_PATH,
            "role": "evaluator_artifact",
            "sha256": artifact_digest,
            "size_bytes": len(artifact),
        },
        {
            "path": PROFILE_RELATIVE,
            "role": "study_profile",
            "sha256": sha256_file(profile_path),
            "size_bytes": profile_path.stat().st_size,
        },
    ]
    _validate_profile_binding(tmp_path, {"files": files})
    files[1]["sha256"] = "0" * 64
    with pytest.raises(ContractValidationError, match="POSITIVE_ADD_PROFILE_ARTIFACT"):
        _validate_profile_binding(tmp_path, {"files": files})


def _candidate_verification(*, present: bool = True) -> dict[str, Any]:
    return {
        "candidate_present": present,
        "method_candidate_validation_status": "valid",
        "active_representations": [
            {
                "representation_id": "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP",
                "evaluator_id": "AC_DATA_OWNERSHIP",
                "covers": ["AC_DATA_OWNERSHIP"],
            }
        ],
        "positive_evaluations": [
            {
                "representation_id": "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP",
                "execution_status": "COMPLETED",
                "inspection_status": "COMPLETE",
            }
        ],
        "negative_evaluations": [
            {
                "representation_id": "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP",
                "execution_status": "COMPLETED",
                "inspection_status": "COMPLETE",
            }
        ],
    }


def test_positive_add_counts_only_a_valid_owner_add_with_both_candidate_evaluations() -> None:
    operations = [
        {
            "operation": "add",
            "target_type": "representation",
            "target_id": "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP",
        }
    ]

    owner_adds, owner_active, exercised, state = _candidate_exercise(
        operations, _candidate_verification()
    )

    assert len(owner_adds) == 1
    assert owner_active is True
    assert exercised is True
    assert state == "MATERIALIZED_AND_EXERCISED"


def test_positive_add_does_not_count_a_materialized_candidate_without_an_add() -> None:
    owner_adds, owner_active, exercised, state = _candidate_exercise([], _candidate_verification())

    assert owner_adds == []
    assert owner_active is True
    assert exercised is False
    assert state == "MATERIALIZED_NOT_EXERCISED"


def test_positive_add_does_not_count_a_different_representation_add() -> None:
    operations = [{"operation": "add", "target_type": "representation", "target_id": "OTHER"}]

    owner_adds, _owner_active, exercised, state = _candidate_exercise(
        operations, _candidate_verification(present=False)
    )

    assert owner_adds == []
    assert exercised is False
    assert state == "NOT_MATERIALIZED"


def test_positive_add_rejects_candidate_exercise_without_complete_inspection() -> None:
    verification = _candidate_verification()
    verification["negative_evaluations"][0]["inspection_status"] = "INCOMPLETE"
    operations = [
        {
            "operation": "add",
            "target_type": "representation",
            "target_id": "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP",
        }
    ]

    _owner_adds, _owner_active, exercised, state = _candidate_exercise(operations, verification)

    assert exercised is False
    assert state == "MATERIALIZED_NOT_EXERCISED"


def test_positive_add_transition_readback_includes_only_the_scoped_owner_obligation() -> None:
    assert _expected_evidence_obligation_ids(positive_add=True) == {
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
        "AC_DATA_OWNERSHIP",
    }
    assert _expected_evidence_obligation_ids(positive_add=False) == {
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
    }
