"""Adversarial synthetic tests for MONO-A1 evidence custody and scoring gates."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - test-only Git object identity lookup
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import load_schema
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from experiments.execution.tooling.mono_a1 import (
    MonoA1Error,
    W2A1ExactPairReadbackVerifier,
    assess_mono_rq3,
    create_mono_archive,
    freeze_reference,
    load_verified_reference,
    score_mono_rq1,
    score_mono_rq2,
    validate_mono_reference,
    validate_mono_study,
    validate_source_image_provenance,
    verify_exact_pair_evidence,
    verify_method_input_isolation,
    verify_mono_archive,
    write_evidence_inventory,
)
from experiments.execution.tooling.sealing import seal_prediction

ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "a" * 64
SHA256_B = "b" * 64
SHA256_C = "c" * 64
SHA256_D = "d" * 64
SHA256_E = "e" * 64
SHA256_F = "f" * 64
SHA256_G = "1" * 64


def _git_text(*arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - synthetic test uses fixed Git argv
        ["git", "-C", str(ROOT), *arguments],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _initialize_test_repository(repository: Path) -> None:
    repository.mkdir(parents=True, exist_ok=True)
    _run_fixture_git(repository, "init", "--quiet")
    _run_fixture_git(repository, "add", "--all")
    _run_fixture_git(
        repository,
        "-c",
        "user.name=MONO synthetic test",
        "-c",
        "user.email=mono-test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "synthetic fixture",
    )


def _run_fixture_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed Git executable and test-controlled argv
        ["git", "-C", str(repository), *arguments],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )


def _repository_identity(repository: Path) -> tuple[str, str]:
    commit_sha = _run_fixture_git(repository, "rev-parse", "HEAD").stdout.strip()
    tree_sha = _run_fixture_git(repository, "rev-parse", "HEAD^{tree}").stdout.strip()
    return commit_sha, tree_sha


def _source_revision(commit_sha: str) -> dict[str, str]:
    tree_sha = _git_text("rev-parse", f"{commit_sha}^{{tree}}")
    return {"state_id": f"STATE_{commit_sha[:8]}", "commit_sha": commit_sha, "tree_sha": tree_sha}


def _source_pair() -> tuple[dict[str, str], dict[str, str]]:
    after_sha = _git_text("rev-parse", "HEAD")
    before_sha = _git_text("rev-parse", "HEAD^")
    return _source_revision(before_sha), _source_revision(after_sha)


def _reference() -> dict[str, Any]:
    before, after = _source_pair()
    return {
        "schema_version": "mono-a1-reference-v1",
        "study_id": "MONO-E1",
        "reference_id": "MONO_E1_REFERENCE_V1",
        "exposure": "KNOWN_SCENARIO_AUTHOR_DECLARED",
        "custody_status": "AUTHOR_DECLARED",
        "author_id": "synthetic-test-author",
        "prepared_before_method_execution": True,
        "architecture": {"before": before, "after": after},
        "methods": {
            "B0": {
                "version": "synthetic-frozen-b0",
                "source_sha": before["commit_sha"],
                "configuration_id": "B0_FROZEN",
                "configuration_sha256": SHA256_B,
            },
            "P": {
                "version": "synthetic-frozen-p",
                "source_sha": after["commit_sha"],
                "configuration_id": "P_FROZEN",
                "configuration_sha256": SHA256_C,
            },
        },
        "architecture_facts": [
            {
                "fact_id": "FACT_BEFORE",
                "architecture_source_sha": before["commit_sha"],
                "claim": "synthetic before-state fact",
                "status": "VERIFIED",
                "evidence_artifact_id": "FACT_BEFORE_BYTES",
                "evidence_sha256": SHA256_D,
            },
            {
                "fact_id": "FACT_AFTER",
                "architecture_source_sha": after["commit_sha"],
                "claim": "synthetic after-state fact",
                "status": "VERIFIED",
                "evidence_artifact_id": "FACT_AFTER_BYTES",
                "evidence_sha256": SHA256_E,
            },
        ],
        "target_universe": [
            {
                "target_type": "representation",
                "target_id": "REP_SYNTHETIC",
                "expected_disposition": "UNAFFECTED",
                "expected_operation": "retain",
                "rationale": "synthetic unaffected target",
                "source_fact_ids": ["FACT_BEFORE", "FACT_AFTER"],
            },
            {
                "target_type": "obligation",
                "target_id": "OBL_SYNTHETIC",
                "expected_disposition": "AFFECTED",
                "expected_operation": "add",
                "rationale": "synthetic applicable obligation",
                "source_fact_ids": ["FACT_AFTER"],
            },
        ],
        "obligation_universe": [
            {
                "obligation_id": "OBL_SYNTHETIC",
                "applicability": "ACTIVE",
                "mandatory": True,
                "rationale": "synthetic applicable obligation",
                "applicability_fact_ids": ["FACT_AFTER"],
                "evidence_requirements": ["source-pinned evaluator and raw inspection artifact"],
                "required_exact_pairs": [
                    {
                        "representation_id": "REP_SYNTHETIC",
                        "evaluator_id": "EVAL_SYNTHETIC",
                        "inspection_scope": "app/modules",
                    }
                ],
            }
        ],
        "obligation_denominator": {
            "required_obligation_ids": ["OBL_SYNTHETIC"],
            "unresolved_obligation_ids": [],
            "complete": True,
        },
        "evaluator_artifacts": [
            {
                "evaluator_id": "EVAL_SYNTHETIC",
                "version": "1.0.0-test",
                "source_sha": after["commit_sha"],
                "tree_sha": after["tree_sha"],
                "artifact_sha256": SHA256_D,
                "configuration_sha256": SHA256_E,
                "capabilities": ["static-import-inspection"],
                "inspection_scope": "app/modules",
            }
        ],
    }


def _mono_e2_reference() -> dict[str, Any]:
    """Return a schema fixture with Git-object stand-ins, not verified A1 evidence."""
    reference = _reference()
    before = reference["architecture"]["before"]
    after = reference["architecture"]["after"]
    a0_sha = "b78b0967be937634b7762baccf5ac6892b279a73"
    before.update(
        state_id="A0_MONOLITH",
        commit_sha=a0_sha,
        tree_sha=_git_text("rev-parse", f"{a0_sha}^{{tree}}"),
    )
    # HEAD supplies a real Git object solely to make the fixture structurally complete.
    # It is not asserted to be the final A1 source or used as experimental evidence.
    after.update(state_id="A1_MODULAR_MONOLITH")
    reference.update(study_id="MONO-E2", reference_id="MONO_E2_REFERENCE_V1")
    reference["methods"]["B0"]["source_sha"] = before["commit_sha"]
    reference["methods"]["P"]["source_sha"] = after["commit_sha"]
    for fact in reference["architecture_facts"]:
        fact["architecture_source_sha"] = (
            before["commit_sha"] if fact["fact_id"] == "FACT_BEFORE" else after["commit_sha"]
        )
    evaluator = reference["evaluator_artifacts"][0]
    evaluator.update(source_sha=after["commit_sha"], tree_sha=after["tree_sha"])
    return reference


@pytest.fixture
def frozen_reference(tmp_path: Path) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    reference = _reference()
    directory = tmp_path / "reference-custody"
    seal = freeze_reference(
        reference,
        directory,
        repository=ROOT,
        frozen_at_utc="2026-10-21T08:00:00Z",
    )
    return reference, directory, seal


def _freeze_test_reference(tmp_path: Path, reference: dict[str, Any], name: str) -> Path:
    directory = tmp_path / name
    freeze_reference(
        reference,
        directory,
        repository=ROOT,
        frozen_at_utc="2026-10-21T08:00:00Z",
    )
    return directory


def _pair_evidence(
    reference: dict[str, Any],
    evidence_root: Path,
    *,
    run_id: str = "mono-run-b0",
    arm: str = "B0",
    role: str = "B0_FROZEN",
    configuration_sha256: str = SHA256_B,
    trust_scope: str = "DEVELOPMENT",
) -> dict[str, Any]:
    evidence_root.mkdir(parents=True, exist_ok=True)
    raw_contents = {
        "execution.json": b'{"status":"VERIFIED","synthetic":true}\n',
        "inspection.json": b'{"inspected_item_count":3,"synthetic":true}\n',
        "semantic-assessment.json": b'{"status":"SUITABLE","synthetic":true}\n',
        "evaluator.stdout": b"synthetic non-empty evaluator output\n",
    }
    raw_paths = {}
    for name, content in raw_contents.items():
        raw_path = evidence_root / name
        raw_path.write_bytes(content)
        raw_paths[name] = raw_path
    after_sha = reference["architecture"]["after"]["commit_sha"]
    evaluator = reference["evaluator_artifacts"][0]
    return {
        "schema_version": "mono-a1-exact-pair-evidence-v1",
        "evidence_id": f"PAIR_{arm}_{role}",
        "study_id": reference["study_id"],
        "run_id": run_id,
        "arm": arm,
        "configuration_role": role,
        "configuration_sha256": configuration_sha256,
        "representation_id": "REP_SYNTHETIC",
        "obligation_id": "OBL_SYNTHETIC",
        "architecture_state": reference["architecture"]["after"]["state_id"],
        "architecture_source_sha": after_sha,
        "evaluator": {
            "evaluator_id": "EVAL_SYNTHETIC",
            "version": evaluator["version"],
            "source_sha": evaluator["source_sha"],
            "tree_sha": evaluator["tree_sha"],
            "artifact_sha256": evaluator["artifact_sha256"],
            "configuration_sha256": evaluator["configuration_sha256"],
        },
        "execution": {
            "status": "VERIFIED",
            "execution_sha256": sha256_file(raw_paths["execution.json"]),
        },
        "inspection": {
            "scope": "app/modules",
            "inspected_item_count": 3,
            "scope_sha256": sha256_file(raw_paths["inspection.json"]),
        },
        "semantic_suitability": {
            "status": "SUITABLE",
            "assessment_sha256": sha256_file(raw_paths["semantic-assessment.json"]),
        },
        "compliance": "COMPLIANT",
        "trust_scope": trust_scope,
        "raw_evidence_artifacts": [
            {
                "artifact_id": "SYNTHETIC_STDOUT",
                "path": raw_path.name,
                "sha256": sha256_file(raw_path),
            }
            for raw_path in raw_paths.values()
        ],
    }


class _SyntheticExactPairVerifier:
    """Test-only stand-in for a separately pinned W2 evaluator readback adapter."""

    def __init__(self, identity: dict[str, Any], verdict: bool = True) -> None:
        self.evaluator_id = identity["evaluator_id"]
        self.version = identity["version"]
        self.source_sha = identity["source_sha"]
        self.tree_sha = identity["tree_sha"]
        self.artifact_sha256 = identity["artifact_sha256"]
        self.configuration_sha256 = identity["configuration_sha256"]
        self.verdict = verdict

    def verify(self, evidence: Mapping[str, Any], *, artifact_root: Path) -> bool | None:
        return self.verdict and artifact_root.is_dir() and evidence["study_id"] == "MONO-E1"


def _null_score() -> dict[str, Any]:
    return {
        "TP": None,
        "FP_in": None,
        "FP_extra": None,
        "FN": None,
        "TN": None,
        "precision": None,
        "recall": None,
        "F1": None,
        "operation_accuracy": None,
        "operation_confusion": {
            expected: {
                predicted: None
                for predicted in ("retain", "add", "replace", "deactivate", "adjust")
            }
            for expected in ("retain", "add", "replace", "deactivate", "adjust")
        },
        "target_count": None,
    }


def _study(reference: dict[str, Any]) -> dict[str, Any]:
    before = reference["architecture"]["before"]
    after = reference["architecture"]["after"]
    return {
        "schema_version": "mono-a1-study-v1",
        "study_id": "MONO-E1",
        "study_status": "EXECUTED",
        "exposure": "KNOWN_SCENARIO_AUTHOR_DECLARED",
        "architecture": {"before": before, "after": after},
        "methods": {
            "B0": {
                "version": "synthetic-frozen-b0",
                "source_sha": before["commit_sha"],
                "configuration_id": "B0_FROZEN",
                "configuration_sha256": SHA256_B,
            },
            "P": {
                "version": "synthetic-frozen-p",
                "source_sha": after["commit_sha"],
                "configuration_id": "P_FROZEN",
                "configuration_sha256": SHA256_C,
            },
        },
        "architecture_facts": [],
        "obligations": {
            "universe": reference["obligation_universe"],
            "required_obligation_ids": ["OBL_SYNTHETIC"],
            "unresolved_obligation_ids": [],
            "denominator_complete": True,
            "universe_sha256": SHA256_D,
        },
        "method_input_bundles": [
            {
                "arm": arm,
                "bundle_id": f"INPUT_{arm}",
                "bundle_sha256": SHA256_E if arm == "B0" else SHA256_F,
                "allowlist_sha256": SHA256_G,
                "reference_excluded": True,
                "oracle_excluded": True,
                "other_arm_excluded": True,
            }
            for arm in ("B0", "P")
        ],
        "evaluator_artifacts": [],
        "reference": {
            "status": "SEALED",
            "custody_status": "AUTHOR_DECLARED",
            "reference_sha256": SHA256_A,
            "seal_path": "reference/reference.seal.json",
            "frozen_at_utc": "2026-10-21T08:00:00Z",
        },
        "arms": {
            "B0": {
                "run_id": "mono-b0",
                "execution_started_at_utc": "2026-10-21T08:30:00Z",
                "execution_status": "COMPLETED",
                "prediction_status": "SEALED",
                "prediction_sha256": SHA256_B,
                "candidate_validation": "VALID",
                "governance_status": "NOT_RUN",
                "source_image_provenance": {
                    "status": "UNVERIFIED",
                    "source_sha": after["commit_sha"],
                    "image_digest": None,
                    "attestation_sha256": None,
                    "reason": "synthetic test does not provide image provenance",
                },
            },
            "P": {
                "run_id": "mono-p",
                "execution_started_at_utc": "2026-10-21T09:00:00Z",
                "execution_status": "COMPLETED",
                "prediction_status": "NOT_EMITTED_GOVERNANCE_HOLD",
                "prediction_sha256": None,
                "candidate_validation": "VALID",
                "governance_status": "HOLD",
                "source_image_provenance": {
                    "status": "UNVERIFIED",
                    "source_sha": after["commit_sha"],
                    "image_digest": None,
                    "attestation_sha256": None,
                    "reason": "synthetic test does not provide image provenance",
                },
            },
        },
        "exact_pair_evidence": [],
        "rq_mapping": {
            "version": "MONO_A1_RQ_CROSSWALK_V1",
            "manuscript_RQ1": "impact_identification_and_operation_correctness",
            "manuscript_RQ2": "valid_obligation_coverage",
            "manuscript_RQ3": "adaptation_evaluation_verification_overhead",
            "manuscript_RQ4": "architecture_controls_negative_control_and_governance",
            "legacy_executable_RQ3": "controlled_degradation_detection",
            "legacy_executable_RQ4": "runtime_and_CI_overhead",
        },
        "endpoints": {
            "RQ1": {
                "status": "NOT_EVALUABLE",
                "scorer_invoked": False,
                "reason": "P_HOLD_WITHOUT_SEALED_PREDICTION",
                "B0": _null_score(),
                "P": _null_score(),
            },
            "RQ2": {
                "status": "UNKNOWN",
                "denominator_complete": True,
                "denominator_obligation_ids": ["OBL_SYNTHETIC"],
                "B0_coverage_percentage": None,
                "P_candidate_potential_coverage_percentage": None,
                "P_governance_accepted_coverage_percentage": None,
                "rows": [
                    {
                        "obligation_id": "OBL_SYNTHETIC",
                        "B0": "UNKNOWN",
                        "P_candidate_potential": "UNKNOWN",
                        "P_governance_accepted": "ABSENT",
                    }
                ],
            },
            "RQ3": {
                "status": "UNKNOWN",
                "timing_boundary_id": None,
                "B0": {
                    "adaptation_ns": None,
                    "evaluator_ns": None,
                    "verification_ns": None,
                    "total_ns": None,
                },
                "P": {
                    "adaptation_ns": None,
                    "evaluator_ns": None,
                    "verification_ns": None,
                    "total_ns": None,
                },
                "resource_measurements": {
                    "cpu_status": "UNKNOWN",
                    "cpu_millicores": None,
                    "rss_status": "UNKNOWN",
                    "rss_bytes": None,
                },
            },
            "RQ4": {"status": "UNKNOWN", "controls": []},
        },
        "evidence_archive": {
            "status": "NOT_CREATED",
            "archive_sha256": None,
            "inventory": [],
            "clean_extraction_readback": "NOT_RUN",
        },
    }


def test_all_mono_schemas_are_valid_json_schema_contracts() -> None:
    schema_names = (
        "mono_a1_reference_v1.schema.json",
        "mono_a1_exact_pair_evidence_v1.schema.json",
        "mono_a1_study_v1.schema.json",
    )
    for schema_name in schema_names:
        Draft202012Validator.check_schema(load_schema(schema_name))


def test_mono_e2_schema_rejects_a0_1_predecessor() -> None:
    reference = _mono_e2_reference()
    reference["architecture"]["before"]["state_id"] = "A0_1_CAPABILITY_MODULES"

    with pytest.raises(ContractValidationError):
        validate_mono_reference(reference)


def test_mono_e2_schema_rejects_incorrect_a0_commit_sha() -> None:
    reference = _mono_e2_reference()
    reference["architecture"]["before"]["commit_sha"] = "0" * 40

    with pytest.raises(ContractValidationError):
        validate_mono_reference(reference)


def test_mono_e2_schema_rejects_incorrect_final_architecture_state() -> None:
    reference = _mono_e2_reference()
    reference["architecture"]["after"]["state_id"] = "A0_1_CAPABILITY_MODULES"

    with pytest.raises(ContractValidationError):
        validate_mono_reference(reference)


@pytest.mark.parametrize(
    ("identity_case", "expected_error"),
    [
        ("missing_commit", ContractValidationError),
        ("missing_tree", ContractValidationError),
        ("unavailable_commit_and_tree", MonoA1Error),
        ("mismatched_tree", MonoA1Error),
    ],
)
def test_mono_e2_reference_cannot_be_sealed_without_real_final_a1_identities(
    tmp_path: Path,
    identity_case: str,
    expected_error: type[Exception],
) -> None:
    reference = _mono_e2_reference()
    after = reference["architecture"]["after"]
    if identity_case == "missing_commit":
        after["commit_sha"] = None
    elif identity_case == "missing_tree":
        after["tree_sha"] = None
    elif identity_case == "unavailable_commit_and_tree":
        after.update(commit_sha="1" * 40, tree_sha="2" * 40)
    else:
        after["tree_sha"] = "0" * 40

    # Keep source-bound fixture records consistent so the final A1 revision check is decisive.
    reference["architecture_facts"][1]["architecture_source_sha"] = after["commit_sha"]
    reference["methods"]["P"]["source_sha"] = after["commit_sha"]
    reference["evaluator_artifacts"][0].update(
        source_sha=after["commit_sha"], tree_sha=after["tree_sha"]
    )
    destination = tmp_path / "unverified-mono-e2-reference"

    with pytest.raises(expected_error):
        freeze_reference(reference, destination, repository=ROOT)

    assert not destination.exists()


def test_reference_freeze_is_source_pinned_and_precedes_method_execution(
    frozen_reference: tuple[dict[str, Any], Path, dict[str, Any]],
) -> None:
    reference, directory, seal = frozen_reference

    loaded, digest, loaded_seal = load_verified_reference(
        directory,
        repository=ROOT,
        expected_study_id="MONO-E1",
        method_execution_started_at_utc="2026-10-21T09:00:00Z",
    )

    assert loaded == reference
    assert digest == seal["reference_sha256"]
    assert loaded_seal == seal


def test_freeze_rejects_incorrect_source_tree_sha(tmp_path: Path) -> None:
    reference = _reference()
    reference["architecture"]["after"]["tree_sha"] = "0" * 40

    with pytest.raises(MonoA1Error, match="source commit or tree SHA"):
        freeze_reference(reference, tmp_path / "bad-reference", repository=ROOT)


@pytest.mark.parametrize("seal_case", ["missing", "forged"])
def test_reference_readback_rejects_missing_or_forged_seal(
    frozen_reference: tuple[dict[str, Any], Path, dict[str, Any]],
    seal_case: str,
) -> None:
    _, directory, _ = frozen_reference
    seal_path = directory / "reference.seal.json"
    if seal_case == "missing":
        seal_path.chmod(0o644)
        seal_path.unlink()
    else:
        seal_path.chmod(0o644)
        forged = json.loads(seal_path.read_text())
        forged["reference_sha256"] = "0" * 64
        seal_path.write_text(json.dumps(forged), encoding="utf-8")

    with pytest.raises(MonoA1Error):
        load_verified_reference(directory, repository=ROOT)


def test_reference_is_write_once_and_post_seal_mutation_is_detected(
    frozen_reference: tuple[dict[str, Any], Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    reference, directory, _ = frozen_reference
    with pytest.raises(MonoA1Error, match="write-once"):
        freeze_reference(reference, directory, repository=ROOT)

    payload_path = directory / "reference.json"
    payload_path.chmod(0o644)
    payload_path.write_bytes(payload_path.read_bytes() + b" ")

    with pytest.raises(MonoA1Error, match="digest seal"):
        load_verified_reference(directory, repository=ROOT)


@pytest.mark.parametrize("forbidden_key", ["expected_operation", "expected_operations"])
def test_reference_labels_cannot_enter_method_input_bundle(
    frozen_reference: tuple[dict[str, Any], Path, dict[str, Any]],
    tmp_path: Path,
    forbidden_key: str,
) -> None:
    _, reference_directory, _ = frozen_reference
    input_root = tmp_path / "method-input"
    input_root.mkdir()
    (input_root / "public_fact.json").write_text(
        json.dumps({"fact_id": "F1", "claim": "source-pinned fact"}),
        encoding="utf-8",
    )
    assert (
        verify_method_input_isolation(input_root, reference_directory)[0]["path"]
        == "public_fact.json"
    )

    (input_root / "bad_bundle.json").write_text(
        json.dumps({forbidden_key: {"REP_SYNTHETIC": "replace"}}),
        encoding="utf-8",
    )
    with pytest.raises(MonoA1Error, match="oracle"):
        verify_method_input_isolation(input_root, reference_directory)


def test_exact_pair_requires_exact_mapping_raw_bytes_and_non_vacuous_proof(
    tmp_path: Path,
) -> None:
    reference = _reference()
    evidence_root = tmp_path / "raw-evidence"
    evidence = _pair_evidence(reference, evidence_root)
    evaluator = reference["evaluator_artifacts"][0]
    shared = {
        "study_id": "MONO-E1",
        "run_id": "mono-run-b0",
        "architecture_state": reference["architecture"]["after"]["state_id"],
        "architecture_source_sha": reference["architecture"]["after"]["commit_sha"],
        "representation_id": "REP_SYNTHETIC",
        "obligation_id": "OBL_SYNTHETIC",
        "configuration_role": "B0_FROZEN",
        "configuration_sha256": SHA256_B,
        "expected_evaluator": evaluator,
        "independent_verifier": _SyntheticExactPairVerifier(evaluator),
        "artifact_root": evidence_root,
    }

    assert verify_exact_pair_evidence(evidence, **shared) == "VERIFIED"
    assert (
        verify_exact_pair_evidence(
            evidence,
            **{key: value for key, value in shared.items() if key != "independent_verifier"},
        )
        == "UNKNOWN"
    )
    assert (
        verify_exact_pair_evidence({**evidence, "trust_scope": "TEST_ONLY"}, **shared)
        == "DIAGNOSTIC_ONLY"
    )
    with pytest.raises(ContractValidationError):
        verify_exact_pair_evidence({**evidence, "trust_scope": "PRODUCTION_AUTHORITY"}, **shared)

    forged = {**evidence, "inspection": {**evidence["inspection"], "inspected_item_count": 0}}
    assert verify_exact_pair_evidence(forged, **shared) == "UNKNOWN"

    wrong_evaluator = {**evaluator, "artifact_sha256": SHA256_A}
    assert (
        verify_exact_pair_evidence(evidence, **{**shared, "expected_evaluator": wrong_evaluator})
        == "UNKNOWN"
    )

    with pytest.raises(MonoA1Error, match="different study, run, source, or pair"):
        verify_exact_pair_evidence(evidence, **{**shared, "architecture_source_sha": "0" * 40})

    missing_raw_root = tmp_path / "empty"
    missing_raw_root.mkdir()
    assert (
        verify_exact_pair_evidence(evidence, **{**shared, "artifact_root": missing_raw_root})
        == "UNKNOWN"
    )


def test_exact_pair_rejects_cross_run_evidence_reuse(tmp_path: Path) -> None:
    reference = _reference()
    evidence = _pair_evidence(reference, tmp_path / "raw-evidence")
    with pytest.raises(MonoA1Error, match="different study, run, source, or pair"):
        verify_exact_pair_evidence(
            evidence,
            study_id="MONO-E1",
            run_id="mono-run-p",
            architecture_state=reference["architecture"]["after"]["state_id"],
            architecture_source_sha=reference["architecture"]["after"]["commit_sha"],
            representation_id="REP_SYNTHETIC",
            obligation_id="OBL_SYNTHETIC",
            configuration_role="B0_FROZEN",
            configuration_sha256=SHA256_B,
            expected_evaluator=reference["evaluator_artifacts"][0],
            artifact_root=tmp_path / "raw-evidence",
        )


def test_rq2_uses_one_full_denominator_and_separates_three_coverage_views(
    tmp_path: Path,
) -> None:
    reference = _reference()
    raw_root = tmp_path / "evidence"
    b0 = _pair_evidence(reference, raw_root / "b0", run_id="mono-b0", arm="B0")
    candidate = _pair_evidence(
        reference,
        raw_root / "p",
        run_id="mono-p",
        arm="P",
        role="P_PROPOSED_CANDIDATE",
        configuration_sha256=SHA256_F,
    )
    result = score_mono_rq2(
        _freeze_test_reference(tmp_path, reference, "reference"),
        [b0, candidate],
        repository=ROOT,
        method_execution_started_at_utc={
            "B0": "2026-10-21T08:30:00Z",
            "P": "2026-10-21T09:00:00Z",
        },
        declared_denominator_ids=["OBL_SYNTHETIC"],
        run_ids={"B0": "mono-b0", "P": "mono-p"},
        candidate_validation="VALID",
        candidate_configuration_sha256=SHA256_F,
        governance_status="HOLD",
        evidence_root_by_arm={"B0": raw_root / "b0", "P": raw_root / "p"},
        independent_verifier=_SyntheticExactPairVerifier(reference["evaluator_artifacts"][0]),
    )

    assert result["denominator_obligation_ids"] == ["OBL_SYNTHETIC"]
    assert len(result["reference_sha256"]) == 64
    assert result["B0_coverage_percentage"] == 100.0
    assert result["P_candidate_potential_coverage_percentage"] == 100.0
    assert result["P_governance_accepted_coverage_percentage"] is None
    assert result["rows"][0]["P_governance_accepted"] == "ABSENT"
    assert result["status"] == "UNKNOWN"


def test_rq2_rejects_duplicate_exact_pair_rows(tmp_path: Path) -> None:
    reference = _reference()
    b0 = _pair_evidence(reference, tmp_path / "raw-b0", run_id="mono-b0", arm="B0")

    with pytest.raises(MonoA1Error, match="Duplicate evidence rows"):
        score_mono_rq2(
            _freeze_test_reference(tmp_path, reference, "reference"),
            [b0, dict(b0)],
            repository=ROOT,
            method_execution_started_at_utc={
                "B0": "2026-10-21T08:30:00Z",
                "P": "2026-10-21T09:00:00Z",
            },
            declared_denominator_ids=["OBL_SYNTHETIC"],
            run_ids={"B0": "mono-b0", "P": "mono-p"},
            candidate_validation="UNKNOWN",
            candidate_configuration_sha256=None,
            governance_status="HOLD",
        )


@pytest.mark.parametrize(
    ("trust_scope", "expected_accepted_state", "expected_percentage"),
    [
        ("DEVELOPMENT", "COVERED", 100.0),
        ("TEST_ONLY", "DIAGNOSTIC_ONLY", None),
    ],
)
def test_rq2_keeps_governance_acceptance_separate_from_test_only_proof(
    tmp_path: Path,
    trust_scope: str,
    expected_accepted_state: str,
    expected_percentage: float | None,
) -> None:
    reference = _reference()
    b0_root = tmp_path / "raw-b0"
    p_root = tmp_path / "raw-p"
    b0 = _pair_evidence(reference, b0_root, run_id="mono-b0", arm="B0")
    candidate = _pair_evidence(
        reference,
        p_root,
        run_id="mono-p",
        arm="P",
        role="P_PROPOSED_CANDIDATE",
        configuration_sha256=SHA256_F,
    )
    accepted = _pair_evidence(
        reference,
        p_root,
        run_id="mono-p",
        arm="P",
        role="P_GOVERNANCE_ACCEPTED",
        configuration_sha256=SHA256_F,
        trust_scope=trust_scope,
    )
    result = score_mono_rq2(
        _freeze_test_reference(tmp_path, reference, "reference"),
        [b0, candidate, accepted],
        repository=ROOT,
        method_execution_started_at_utc={
            "B0": "2026-10-21T08:30:00Z",
            "P": "2026-10-21T09:00:00Z",
        },
        declared_denominator_ids=["OBL_SYNTHETIC"],
        run_ids={"B0": "mono-b0", "P": "mono-p"},
        candidate_validation="VALID",
        candidate_configuration_sha256=SHA256_F,
        governance_status="ACCEPT",
        accepted_configuration_sha256=SHA256_F,
        evidence_root_by_arm={"B0": b0_root, "P": p_root},
        independent_verifier=_SyntheticExactPairVerifier(reference["evaluator_artifacts"][0]),
    )

    assert result["rows"][0]["P_governance_accepted"] == expected_accepted_state
    assert result["P_governance_accepted_coverage_percentage"] == expected_percentage


def test_rq2_rejects_a_wrong_denominator_and_keeps_unknown_applicability(
    tmp_path: Path,
) -> None:
    reference = _reference()
    reference_directory = _freeze_test_reference(tmp_path, reference, "reference")
    with pytest.raises(MonoA1Error, match="denominator"):
        score_mono_rq2(
            reference_directory,
            [],
            repository=ROOT,
            method_execution_started_at_utc={
                "B0": "2026-10-21T08:30:00Z",
                "P": "2026-10-21T09:00:00Z",
            },
            declared_denominator_ids=["WRONG_OBLIGATION"],
            run_ids={"B0": "mono-b0", "P": "mono-p"},
            candidate_validation="UNKNOWN",
            candidate_configuration_sha256=None,
            governance_status="HOLD",
        )

    unresolved = json.loads(json.dumps(reference))
    unresolved["obligation_universe"].append(
        {
            "obligation_id": "OBL_UNRESOLVED",
            "applicability": "UNKNOWN",
            "mandatory": True,
            "rationale": "synthetic unresolved applicability",
            "applicability_fact_ids": [],
            "evidence_requirements": ["source evidence"],
            "required_exact_pairs": [],
        }
    )
    unresolved["obligation_denominator"] = {
        "required_obligation_ids": ["OBL_SYNTHETIC"],
        "unresolved_obligation_ids": ["OBL_UNRESOLVED"],
        "complete": False,
    }
    unresolved_directory = _freeze_test_reference(tmp_path, unresolved, "unresolved-reference")
    result = score_mono_rq2(
        unresolved_directory,
        [],
        repository=ROOT,
        method_execution_started_at_utc={
            "B0": "2026-10-21T08:30:00Z",
            "P": "2026-10-21T09:00:00Z",
        },
        declared_denominator_ids=["OBL_SYNTHETIC"],
        run_ids={"B0": "mono-b0", "P": "mono-p"},
        candidate_validation="UNKNOWN",
        candidate_configuration_sha256=None,
        governance_status="HOLD",
    )
    assert result["status"] == "UNKNOWN"
    assert result["B0_coverage_percentage"] is None
    assert result["P_candidate_potential_coverage_percentage"] is None
    assert result["P_governance_accepted_coverage_percentage"] is None


def test_p_hold_without_prediction_preserves_rq1_not_evaluable(
    frozen_reference: tuple[dict[str, Any], Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    _, reference_directory, _ = frozen_reference
    result = score_mono_rq1(
        reference_directory,
        tmp_path / "no-b0-output-needed",
        None,
        repository=ROOT,
        b0_prediction_status="SEALED",
        p_prediction_status="NOT_EMITTED_GOVERNANCE_HOLD",
        input_bundle_sha256={"B0": SHA256_B, "P": SHA256_C},
        method_execution_started_at_utc={
            "B0": "2026-10-21T08:30:00Z",
            "P": "2026-10-21T09:00:00Z",
        },
    )
    assert result["status"] == "NOT_EVALUABLE"
    assert result["scorer_invoked"] is False
    assert result["P"] is None


def test_rq1_scores_only_sealed_predictions_and_reports_operation_confusion(
    frozen_reference: tuple[dict[str, Any], Path, dict[str, Any]],
    tmp_path: Path,
) -> None:
    reference, reference_directory, _ = frozen_reference
    after_sha = reference["architecture"]["after"]["commit_sha"]
    predictions: dict[str, Path] = {}
    for arm in ("B0", "P"):
        directory = tmp_path / f"{arm.lower()}-prediction"
        payload = {
            "schema_version": 1,
            "method_id": arm,
            "architecture_source_sha": after_sha,
            "method_version": f"synthetic-{arm.lower()}-v1",
            "input_bundle_sha256": SHA256_B if arm == "B0" else SHA256_C,
            "predicted_affected": [
                {
                    "target_type": "obligation",
                    "target_id": "OBL_SYNTHETIC",
                    "predicted_operation": "add",
                }
            ],
            "proposed_operations": [
                {
                    "target_type": "obligation",
                    "target_id": "OBL_SYNTHETIC",
                    "operation": "add",
                }
            ],
            "explanations": [],
            "artifact_hashes": {},
        }
        seal_prediction(payload, directory, sealed_at_utc="2026-10-21T09:10:00Z")
        predictions[arm] = directory

    result = score_mono_rq1(
        reference_directory,
        predictions["B0"],
        predictions["P"],
        repository=ROOT,
        b0_prediction_status="SEALED",
        p_prediction_status="SEALED",
        input_bundle_sha256={"B0": SHA256_B, "P": SHA256_C},
        method_execution_started_at_utc={
            "B0": "2026-10-21T08:30:00Z",
            "P": "2026-10-21T09:00:00Z",
        },
    )

    assert result["status"] == "SCORED"
    assert result["scorer_invoked"] is True
    assert result["B0"]["TP"] == 1
    assert result["B0"]["TN"] == 1
    assert result["B0"]["operation_accuracy"] == 1.0
    assert result["B0"]["operation_confusion"]["add"]["add"] == 1
    assert result["B0"]["operation_confusion"]["retain"]["retain"] == 1


def test_study_gate_rejects_scoring_when_p_hold_has_no_prediction() -> None:
    study = _study(_reference())
    validate_mono_study(study)

    study["endpoints"]["RQ1"]["status"] = "SCORED"
    study["endpoints"]["RQ1"]["scorer_invoked"] = True
    with pytest.raises(MonoA1Error, match="HOLD without a sealed prediction"):
        validate_mono_study(study)


def test_study_gate_rejects_wrong_rq2_denominator() -> None:
    study = _study(_reference())
    study["endpoints"]["RQ2"]["denominator_obligation_ids"] = ["OTHER"]
    with pytest.raises(MonoA1Error, match="RQ2 denominator"):
        validate_mono_study(study)


def test_incomplete_runtime_metrics_and_invalid_image_binding_remain_unknown() -> None:
    source_sha = _source_pair()[1]["commit_sha"]
    timings = {
        "adaptation_ns": 10,
        "evaluator_ns": 20,
        "verification_ns": 30,
        "total_ns": 60,
    }
    provenance = {
        arm: {
            "status": "VERIFIED",
            "source_sha": source_sha,
            "image_digest": f"registry.invalid/evofit@sha256:{SHA256_A}",
            "attestation_sha256": SHA256_B,
        }
        for arm in ("B0", "P")
    }
    assert validate_source_image_provenance(provenance["B0"], source_sha)

    invalid = {**provenance["P"], "source_sha": "0" * 40}
    assert not validate_source_image_provenance(invalid, source_sha)
    incomplete = assess_mono_rq3(
        timing_boundary_ids={"B0": "MONO_TIMER_V1", "P": "MONO_TIMER_V1"},
        timings_ns={
            "B0": timings,
            "P": {**timings, "verification_ns": None},
        },
        source_image_provenance={"B0": provenance["B0"], "P": invalid},
        architecture_source_sha=source_sha,
    )
    assert incomplete["status"] == "UNKNOWN"
    assert incomplete["P"]["verification_ns"] is None
    assert "P_TIMINGS_INCOMPLETE" in incomplete["reason_codes"]
    assert "P_SOURCE_TO_IMAGE_UNVERIFIED" in incomplete["reason_codes"]

    complete = assess_mono_rq3(
        timing_boundary_ids={"B0": "MONO_TIMER_V1", "P": "MONO_TIMER_V1"},
        timings_ns={"B0": timings, "P": timings},
        source_image_provenance=provenance,
        architecture_source_sha=source_sha,
    )
    assert complete["status"] == "DESCRIPTIVE"
    assert complete["inference_limit"] == "single transition; descriptive only"

    negative = assess_mono_rq3(
        timing_boundary_ids={"B0": "MONO_TIMER_V1", "P": "MONO_TIMER_V1"},
        timings_ns={"B0": {**timings, "total_ns": -1}, "P": timings},
        source_image_provenance=provenance,
        architecture_source_sha=source_sha,
    )
    assert negative["status"] == "UNKNOWN"
    assert "B0_TIMINGS_INVALID" in negative["reason_codes"]


def test_evidence_archive_integrity_and_clean_extraction_readback(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "run"
    evidence.mkdir()
    (evidence / "execution.json").write_text(
        json.dumps({"status": "SYNTHETIC_TEST_ONLY"}),
        encoding="utf-8",
    )
    inventory = write_evidence_inventory(evidence)
    assert len(inventory["entries"]) == 1

    archive = tmp_path / "mono-a1-evidence.zip"
    digest, readback = create_mono_archive(evidence, archive)
    assert readback["readback"]["verified"] is True
    assert readback["readback"]["archive_sha256"] == digest
    assert verify_mono_archive(archive, expected_sha256=digest)["verified"] is True

    archive.chmod(0o644)
    archive.write_bytes(archive.read_bytes() + b"tamper")
    with pytest.raises(MonoA1Error, match="digest mismatch"):
        verify_mono_archive(archive)


def test_reference_unknown_fields_cannot_hide_post_run_oracle_data() -> None:
    reference = _reference()
    reference["oracle_labels"] = {"unexpected": "must not enter the contract"}
    with pytest.raises(ContractValidationError):
        validate_mono_reference(reference)


def test_w2_readback_binds_the_pinned_evaluator_state_and_source(tmp_path: Path) -> None:
    evaluator_repository = tmp_path / "w2-checkout"
    evaluator_root = evaluator_repository / "architecture/acceptance/a1"
    evaluator_root.mkdir(parents=True)
    engine_path = evaluator_root / "engine.py"
    engine_path.write_text(
        """import hashlib
import json

def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_evidence(evidence, repo_root, config_path, evaluator_root=None):
    failures = []
    if _sha(config_path) != evidence['evaluator']['configuration_digest']:
        failures.append('CONFIGURATION_DIGEST_MISMATCH')
    root = evaluator_root or repo_root / evidence['evaluator']['source_artifact_root']
    artifacts = evidence['evaluator']['source_artifacts']
    observed = []
    for item in artifacts:
        path = root / item['path']
        if not path.is_file() or _sha(path) != item['sha256']:
            failures.append('EVALUATOR_ARTIFACT_DIGEST_MISMATCH')
        else:
            observed.append({'path': item['path'], 'sha256': _sha(path)})
    canonical = json.dumps(
        observed, sort_keys=True, separators=(',', ':'), ensure_ascii=False
    ).encode()
    if hashlib.sha256(canonical).hexdigest() != evidence['evaluator']['source_digest']:
        failures.append('EVALUATOR_SOURCE_DIGEST_MISMATCH')
    for item in evidence['source_scope']['source_file_digests']:
        path = repo_root / item['path']
        if not path.is_file() or _sha(path) != item['sha256']:
            failures.append('SUBJECT_SOURCE_DIGEST_MISMATCH')
    return failures
""",
        encoding="utf-8",
    )
    (evaluator_root / "evidence.schema.json").write_text('{"type":"object"}\n', encoding="utf-8")
    config_path = evaluator_root / "module_graph_v1.yaml"
    config_path.write_text("schema_version: 1\nevaluator: AC_MODULE_GRAPH\n", encoding="utf-8")
    _initialize_test_repository(evaluator_repository)
    evaluator_sha, evaluator_tree = _repository_identity(evaluator_repository)
    evaluator_artifacts = [{"path": "engine.py", "sha256": sha256_file(engine_path)}]
    evaluator_digest = sha256_bytes(canonical_json_bytes(evaluator_artifacts))

    subject_repository = tmp_path / "a1-subject"
    subject_file = subject_repository / "app/modules/tasks/query.py"
    subject_file.parent.mkdir(parents=True)
    subject_file.write_text("def query():\n    return []\n", encoding="utf-8")
    _initialize_test_repository(subject_repository)
    subject_sha, _ = _repository_identity(subject_repository)

    diagnostics: dict[str, Any] = {"imports": []}
    report: dict[str, Any] = {
        "schema_version": 1,
        "evaluator": {
            "id": "AC_MODULE_GRAPH",
            "obligation_id": "AC_MODULE_GRAPH",
            "version": "1.0.0",
            "source_digest": evaluator_digest,
            "source_artifact_root": "architecture/acceptance/a1",
            "source_artifacts": evaluator_artifacts,
            "configuration_digest": sha256_file(config_path),
        },
        "architecture": {
            "state": "A1_SYNTHETIC",
            "manifest_state_status": "MATCHED",
            "target_source_sha": subject_sha,
            "expected_source_sha": subject_sha,
            "source_sha_status": "MATCHED",
            "subject_source_dirty": False,
        },
        "source_scope": {
            "complete": True,
            "inspected_paths": ["app/modules/tasks/query.py"],
            "source_file_digests": [
                {"path": "app/modules/tasks/query.py", "sha256": sha256_file(subject_file)}
            ],
            "uncertainties": [],
        },
        "applicability": "ACTIVE",
        "result": {
            "execution_status": "COMPLETED",
            "compliance": "COMPLIANT",
            "violation_count": 0,
            "violations": [],
            "configuration_errors": [],
        },
        "diagnostics": diagnostics,
        "raw_output": {
            "available": True,
            "format": "application/json",
            "sha256": sha256_bytes(canonical_json_bytes(diagnostics)),
        },
        "coverage_limits": [],
        "generated_at": "2026-10-21T09:00:00Z",
    }
    artifact_root = tmp_path / "w2-raw"
    artifact_root.mkdir()
    report_path = artifact_root / "evaluator.json"
    report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    exact_pair: dict[str, Any] = {
        "architecture_state": "A1_SYNTHETIC",
        "architecture_source_sha": subject_sha,
        "obligation_id": "AC_MODULE_GRAPH",
        "evaluator": {
            "evaluator_id": "AC_MODULE_GRAPH",
            "version": "1.0.0",
            "source_sha": evaluator_sha,
            "tree_sha": evaluator_tree,
            "artifact_sha256": evaluator_digest,
            "configuration_sha256": sha256_file(config_path),
        },
        "raw_evidence_artifacts": [
            {
                "artifact_id": "W2_A1_EVALUATOR_EVIDENCE",
                "path": "evaluator.json",
                "sha256": sha256_file(report_path),
            }
        ],
    }
    verifier = W2A1ExactPairReadbackVerifier(
        evaluator_id="AC_MODULE_GRAPH",
        version="1.0.0",
        source_sha=evaluator_sha,
        tree_sha=evaluator_tree,
        artifact_sha256=evaluator_digest,
        configuration_sha256=sha256_file(config_path),
        evaluator_repository=evaluator_repository,
        evaluator_package_root=evaluator_root,
        configuration_path=config_path,
        subject_repository=subject_repository,
    )

    assert verifier.verify(exact_pair, artifact_root=artifact_root) is True

    wrong_state_report = {**report, "architecture": {**report["architecture"], "state": "A0"}}
    report_path.write_text(json.dumps(wrong_state_report, sort_keys=True), encoding="utf-8")
    wrong_state_pair = {
        **exact_pair,
        "raw_evidence_artifacts": [
            {**exact_pair["raw_evidence_artifacts"][0], "sha256": sha256_file(report_path)}
        ],
    }
    assert verifier.verify(wrong_state_pair, artifact_root=artifact_root) is False
