"""Narrow TEST_ONLY profile and versioned input-role checks for the ΔA5 study."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

import experiments.execution.tooling.mono_ci_psi_a05_positive_add as positive_add
import experiments.execution.tooling.mono_ci_psi_a05_positive_add_study as positive_add_study
import experiments.execution.tooling.mono_ci_psi_transition as psi_transition
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import sha256_file
from experiments.execution.tooling.mono_ci_psi_a05_positive_add import (
    PROFILE_ID,
    SCOPE_EVIDENCE_ID,
    TEMPLATE_ARTIFACT_PATH,
    _validate_policy_claim_scope,
    _validate_profile_binding,
    _validate_static_profile,
)
from experiments.execution.tooling.mono_ci_psi_a05_positive_add_study import (
    _candidate_exercise,
)
from experiments.execution.tooling.mono_ci_psi_evidence import evaluator_source_artifacts
from experiments.execution.tooling.mono_ci_psi_transition import (
    RUNTIME_SOURCE,
    _expected_evidence_obligation_ids,
)
from experiments.execution.tooling.p_input_validation import SourceReference
from experiments.execution.tooling.p_operations import template_descriptor_sha256
from experiments.execution.tooling.p_policy_source_v3 import (
    _verify_v3_path_role,
)

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = (
    ROOT / "experiments/execution/mono-ci-b0-psi-delta-a5-positive-add-v1/inputs/"
    "POSITIVE_ADD_PROFILE_V1.json"
)


def _profile() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(PROFILE_PATH.read_text(encoding="utf-8")))


def test_docker_preflight_failure_emits_record_and_returns_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record = {
        "verification_status": "FAIL",
        "probes": {"runtime_started": False},
        "error": {"type": "ProtocolError", "message": "probe failure detail"},
    }
    monkeypatch.setattr(
        positive_add_study,
        "run_preflight",
        lambda repository, output: record,
    )

    status = positive_add_study.main(
        ["preflight", "--repository", str(ROOT), "--output", str(tmp_path / "preflight")]
    )

    assert status == 1
    assert json.loads(capsys.readouterr().out) == record


def test_hosted_study_pulls_pinned_runtime_before_preflight() -> None:
    workflow = (ROOT / ".github/workflows/mono-ci-psi-a05-positive-add.yml").read_text(
        encoding="utf-8"
    )
    image_pull = "docker pull --platform linux/amd64 python:3.12.15-slim-bookworm@sha256:"

    assert workflow.index(image_pull) < workflow.index("Run same-runner Docker isolation preflight")


def test_isolated_runtime_creates_optional_package_parent_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(psi_transition, "RUNTIME_MODULES", ())
    monkeypatch.setattr(psi_transition, "RUNTIME_VENDOR_PACKAGES", ())
    runtime_root = tmp_path / "method-runtime"

    inventory = psi_transition._build_isolated_runtime(ROOT, runtime_root)

    assert (runtime_root / "experiments/pilots/__init__.py").is_file()
    assert (runtime_root / "experiments/pilots/pilot02_testonly_execution.py").is_file()
    profile_schema = "mono_ci_psi_positive_add_profile_v1.schema.json"
    assert profile_schema in psi_transition.RUNTIME_SCHEMAS
    assert (runtime_root / "experiments/execution/schemas" / profile_schema).read_bytes() == (
        ROOT / "experiments/execution/schemas" / profile_schema
    ).read_bytes()
    assert inventory["files"]


def test_positive_input_diagnostic_keeps_raw_streams_at_digest_bound_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import experiments.execution.tooling.mono_ci_psi_coverage as coverage_module

    run_root = tmp_path
    source_rows, source_manifest_bytes, source_digest = evaluator_source_artifacts(ROOT)
    implementation_root = run_root / "PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP"
    source_root = implementation_root / "source"
    source_root.mkdir(parents=True)
    (implementation_root / "source-manifest.json").write_bytes(source_manifest_bytes)
    for row in source_rows:
        source = ROOT / "architecture/acceptance/a1" / row["path"]
        destination = source_root / row["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    configuration = ROOT / positive_add.CONFIGURATION_PATH
    configuration_destination = implementation_root / configuration.name
    configuration_destination.write_bytes(configuration.read_bytes())
    template_artifact = run_root / positive_add.TEMPLATE_ARTIFACT_PATH
    template_artifact.parent.mkdir(parents=True, exist_ok=True)
    template_artifact.write_bytes(source_manifest_bytes)

    raw_stdout = b'{"raw":"evaluator stdout"}\n'
    raw_stderr = b"raw evaluator stderr\n"
    evidence = {
        "architecture": {
            "state": "A0_5_MODULE_DATA_OWNERSHIP",
            "target_source_sha": "a" * 40,
            "manifest_state_status": "MATCHED",
            "source_sha_status": "MATCHED",
        },
        "source_scope": {"modules": []},
        "evaluator": {"id": "AC_DATA_OWNERSHIP"},
        "result": {"compliance": "COMPLIANT", "execution_status": "COMPLETED"},
        "applicability": "ACTIVE",
    }

    def fake_run_fresh_evaluator(**kwargs: Any) -> dict[str, Any]:
        output_directory = kwargs["output_directory"]
        output_directory.mkdir(parents=True)
        output_path = output_directory / "evaluator-output.json"
        stdout_path = output_directory / "stdout.bin"
        stderr_path = output_directory / "stderr.bin"
        output_path.write_text(json.dumps(evidence), encoding="utf-8")
        stdout_path.write_bytes(raw_stdout)
        stderr_path.write_bytes(raw_stderr)

        def relative(path: Path) -> str:
            return path.relative_to(run_root).as_posix()

        return {
            "evaluator_id": "AC_DATA_OWNERSHIP",
            "architecture_state": "A0_5_MODULE_DATA_OWNERSHIP",
            "source_commit_sha": "a" * 40,
            "source_tree_sha": "b" * 40,
            "target_application_tree_sha": "c" * 40,
            "evaluator_source_sha256": source_digest,
            "configuration_sha256": sha256_file(configuration),
            "output_path": relative(output_path),
            "stdout_path": relative(stdout_path),
            "stderr_path": relative(stderr_path),
            "stdout_sha256": hashlib.sha256(raw_stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(raw_stderr).hexdigest(),
            "execution_status": "COMPLETED",
            "compliance": "COMPLIANT",
            "duration_ms": 1.0,
            "evidence": evidence,
            "raw_stdout": raw_stdout,
            "raw_stderr": raw_stderr,
        }

    inspection_coverage = {
        "evaluator_id": "AC_DATA_OWNERSHIP",
        "architecture_state": "A0_5_MODULE_DATA_OWNERSHIP",
        "source_inspection_status": "COMPLETE",
        "counts": {"inspected_count": 1},
        "expected_subjects": ["app/modules/audit/model.py"],
        "inspected_subjects": ["app/modules/audit/model.py"],
        "inspection_unit": "file",
    }
    monkeypatch.setattr(positive_add, "run_fresh_evaluator", fake_run_fresh_evaluator)
    monkeypatch.setattr(
        coverage_module,
        "verify_inspection_coverage",
        lambda **_kwargs: inspection_coverage,
    )
    monkeypatch.setattr(
        positive_add,
        "build_inspection_scope_artifact",
        lambda *_args: {"schema_version": 1, "scope": "TEST_ONLY"},
    )

    positive_add._run_positive_input_evaluator(ROOT, run_root, "a" * 40)

    diagnostic = json.loads(
        (run_root / "diagnostics/positive-add-input-evaluator.json").read_text(encoding="utf-8")
    )
    evaluator_run = diagnostic["evaluator_run"]
    assert "raw_stdout" not in evaluator_run
    assert "raw_stderr" not in evaluator_run
    assert (run_root / evaluator_run["stdout_path"]).read_bytes() == raw_stdout
    assert (run_root / evaluator_run["stderr_path"]).read_bytes() == raw_stderr
    assert evaluator_run["stdout_sha256"] == hashlib.sha256(raw_stdout).hexdigest()
    assert evaluator_run["stderr_sha256"] == hashlib.sha256(raw_stderr).hexdigest()


def _policy_scope_validation_fixture(
    *, registry_schema_version: str = "1.2", registry_version: str = PROFILE_ID
) -> tuple[dict[str, Any], dict[str, SourceReference], dict[str, Any]]:
    claim_ids = ["PILOT02_TEST_ONLY_CLOSURE_BEFORE", "PILOT02_TEST_ONLY_CLOSURE_AFTER"]
    claims = [
        {
            "id": claim_id,
            "kind": "AUTHORITATIVE_POLICY_REGISTRY",
            "fact_type": "obligation:AC_DATA_OWNERSHIP",
            "scope": "application",
            "evidence_source_ids": [SCOPE_EVIDENCE_ID],
        }
        for claim_id in claim_ids
    ]
    registry_bytes = json.dumps(
        {"schema_version": registry_schema_version, "registry_version": registry_version}
    ).encode("utf-8")
    declaration_bytes = json.dumps(
        {
            "profile_id": PROFILE_ID,
            "selected_obligation_id": "AC_DATA_OWNERSHIP",
            "global_denominator_or_coverage_claim": False,
            "claims": [{"claim_id": claim_id} for claim_id in claim_ids],
        }
    ).encode("utf-8")
    sources = {
        "REGISTRY": SourceReference(
            source_id="REGISTRY",
            kind="POLICY_REGISTRY",
            path="fitness/policy/registry.json",
            sha256=hashlib.sha256(registry_bytes).hexdigest(),
            content=registry_bytes,
        ),
        SCOPE_EVIDENCE_ID: SourceReference(
            source_id=SCOPE_EVIDENCE_ID,
            kind="completeness_evidence",
            path="fitness/policy/evidence/POSITIVE_ADD_SCOPE_DECLARATION.json",
            sha256=hashlib.sha256(declaration_bytes).hexdigest(),
            content=declaration_bytes,
        ),
    }
    snapshot = {
        "policy_registry": {
            "source_id": "REGISTRY",
            "closure": "CLAIMED_CLOSED",
            "registry_version": PROFILE_ID,
        },
        "completeness_claims": claims,
    }
    return snapshot, sources, _profile()


def test_policy_scope_accepts_normalized_v12_registry_projection() -> None:
    snapshot, sources, profile = _policy_scope_validation_fixture()

    _validate_policy_claim_scope(snapshot, sources, profile)


@pytest.mark.parametrize(
    ("registry_schema_version", "registry_version"),
    [("1.1", PROFILE_ID), ("1.2", "UNEXPECTED_REGISTRY_VERSION")],
)
def test_policy_scope_rejects_wrong_source_registry_contract(
    registry_schema_version: str, registry_version: str
) -> None:
    snapshot, sources, profile = _policy_scope_validation_fixture(
        registry_schema_version=registry_schema_version,
        registry_version=registry_version,
    )

    with pytest.raises(ContractValidationError, match="POSITIVE_ADD_POLICY_SCOPE_NOT_BOUNDED"):
        _validate_policy_claim_scope(snapshot, sources, profile)


def test_positive_add_profile_schema_accepts_the_frozen_scope() -> None:
    _validate_static_profile(_profile())


@pytest.mark.parametrize(
    ("path", "role"),
    [
        ("evidence/POSITIVE_ADD_PROFILE_V1.json", "study_profile"),
        (
            "PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP/source-manifest.json",
            "evaluator_artifact",
        ),
    ],
)
def test_v3_path_role_allowlist_does_not_include_positive_add_artifacts(
    path: str, role: str
) -> None:
    with pytest.raises(ProtocolError):
        _verify_v3_path_role(PurePosixPath(path), role, "P")


def test_v3_schema_rejects_positive_add_file_roles() -> None:
    manifest: dict[str, Any] = {
        "schema_version": 3,
        "allowlist_version": "DA01_METHOD_INPUTS_V3_CANDIDATE",
        "profile_status": "DEVELOPMENT_UNFROZEN",
        "method_id": "P",
        "architecture_before_sha": "a" * 40,
        "architecture_source_sha": "b" * 40,
        "before_tree_sha": "c" * 40,
        "after_tree_sha": "d" * 40,
        "common_snapshot_sha256": "e" * 64,
        "policy_source_revision": "TEST_ONLY_POSITIVE_ADD_V1",
        "policy_bundle_sha256": "f" * 64,
        "policy_ruleset_sha256": "1" * 64,
        "files": [
            {
                "path": "evidence/POSITIVE_ADD_PROFILE_V1.json",
                "role": "study_profile",
                "size_bytes": 1,
                "sha256": "2" * 64,
            }
        ],
        "bundle_sha256": "3" * 64,
    }

    with pytest.raises(ContractValidationError):
        validate_payload("method_input_v3_candidate.schema.json", manifest)


def test_isolated_runtime_selects_the_profile_builder_from_v3_capabilities() -> None:
    assert '"positive_add_test_only_profile_v1" in capabilities' in RUNTIME_SOURCE
    assert "evidence/POSITIVE_ADD_PROFILE_V1.json" not in RUNTIME_SOURCE


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
    configuration = b"data_ownership: true\n"
    profile_bytes = PROFILE_PATH.read_bytes()
    artifact_digest = hashlib.sha256(artifact).hexdigest()
    configuration_digest = hashlib.sha256(configuration).hexdigest()
    capabilities_path = tmp_path / "fitness/evaluator-capabilities.json"
    capabilities_path.parent.mkdir(parents=True)
    template = {
        "template_id": "TEMPLATE_POSITIVE_ADD_AC_DATA_OWNERSHIP_V1",
        "representation": {
            "id": "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP",
            "active": True,
            "criterion": "architecture_compliance",
            "stage": "ci_test",
            "evaluator": "AC_DATA_OWNERSHIP",
            "covers": ["AC_DATA_OWNERSHIP"],
            "evaluator_artifact": {
                "path": TEMPLATE_ARTIFACT_PATH,
                "sha256": artifact_digest,
            },
            "applicability_scope": {
                "scope_id": "architecture.data_ownership.persistence_ownership",
                "architecture_scope": "app.modules",
                "architecture_state": "A0_5_MODULE_DATA_OWNERSHIP",
            },
            "evidence_contract": {
                "configuration_path": "architecture/acceptance/a1/data_ownership_v1.yaml",
                "configuration_sha256": configuration_digest,
                "evaluator_source_sha256": artifact_digest,
            },
        },
    }
    cost_model = {
        "max_incremental_cost": 225,
        "max_search_nodes": 2,
        "candidate_costs": {artifact_digest: 225},
    }
    capabilities = {
        "generic_candidate_templates": [template],
        "p_cost_model_v1": cost_model,
        "positive_add_test_only_profile_v1": {
            "profile_id": "MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_PROFILE_V1",
            "study_profile_base64": base64.b64encode(profile_bytes).decode("ascii"),
            "study_profile_sha256": hashlib.sha256(profile_bytes).hexdigest(),
            "classification": "TEST_ONLY_AUTHOR_DECLARED_SCOPED_INPUT",
            "scope": "application",
            "template": template,
            "template_descriptor_sha256": template_descriptor_sha256(template),
            "evaluator_artifact_path": TEMPLATE_ARTIFACT_PATH,
            "evaluator_artifact_base64": base64.b64encode(artifact).decode("ascii"),
            "configuration_path": "architecture/acceptance/a1/data_ownership_v1.yaml",
            "configuration_bytes_base64": base64.b64encode(configuration).decode("ascii"),
            "configuration_sha256": configuration_digest,
            "source_manifest_sha256": artifact_digest,
            "selected_obligation_id": "AC_DATA_OWNERSHIP",
            "cost_model": cost_model,
        },
    }
    capabilities_path.write_text(json.dumps(capabilities), encoding="utf-8")
    files: list[dict[str, Any]] = [
        {
            "path": "fitness/evaluator-capabilities.json",
            "role": "evaluator_capabilities",
            "sha256": sha256_file(capabilities_path),
            "size_bytes": capabilities_path.stat().st_size,
        },
    ]
    _validate_profile_binding(tmp_path, {"files": files})
    profile_capability = cast(dict[str, Any], capabilities["positive_add_test_only_profile_v1"])
    profile_capability["study_profile_sha256"] = "0" * 64
    capabilities_path.write_text(json.dumps(capabilities), encoding="utf-8")
    files[0]["sha256"] = sha256_file(capabilities_path)
    files[0]["size_bytes"] = capabilities_path.stat().st_size
    with pytest.raises(ContractValidationError, match="POSITIVE_ADD_PROFILE_ARTIFACT_BINDING"):
        _validate_profile_binding(tmp_path, {"files": files})

    profile_capability["study_profile_sha256"] = hashlib.sha256(profile_bytes).hexdigest()
    profile_capability["evaluator_artifact_base64"] = base64.b64encode(b"changed").decode("ascii")
    capabilities_path.write_text(json.dumps(capabilities), encoding="utf-8")
    files[0]["sha256"] = sha256_file(capabilities_path)
    files[0]["size_bytes"] = capabilities_path.stat().st_size
    with pytest.raises(
        ContractValidationError, match="POSITIVE_ADD_EVALUATOR_OR_CONFIGURATION_BINDING_MISMATCH"
    ):
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
