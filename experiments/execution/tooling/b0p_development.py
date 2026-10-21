"""Fail-closed preparation and evidence checks for the B0/P DEVELOPMENT comparison."""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, cast

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes
from experiments.execution.tooling.inputs import export_method_inputs, verify_method_bundle
from experiments.execution.tooling.p_policy_source_v3 import (
    export_method_inputs_v3,
    package_policy_source_v3,
    verify_method_bundle_v3,
)
from scripts.verify_b0p_git_inventory import actual_inventory, assess_observations

RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$", re.ASCII)
SHA40_PATTERN = re.compile(r"^[a-f0-9]{40}$", re.ASCII)
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$", re.ASCII)
STUDY_SCHEMA = "b0p_development_study_v1.schema.json"
POLICY_SOURCE_PATH = "experiments/execution/policy-pilot/v1/source"
P_SOURCE_PREFIX = "experiments/execution/tooling/p_"
P_SOURCE_SUPPORT_FILES = (
    "experiments/execution/tooling/contracts.py",
    "experiments/execution/tooling/errors.py",
    "experiments/execution/tooling/hashing.py",
    "experiments/execution/tooling/inputs.py",
)
PINNED_B0_SOURCE_SHA = "165a7d6ef31adbe8ce3abe9f72e59d74692c987e"
PINNED_P_SOURCE_SHA = "984f75b11b3153c52275e223ce8ec23b8d0dd0e5"
PINNED_POLICY_SOURCE_SHA = "165a7d6ef31adbe8ce3abe9f72e59d74692c987e"
SCORING_SUPPORT_FILES = {
    "method_input_exporter_v1": ("experiments/execution/tooling/inputs.py", PINNED_B0_SOURCE_SHA),
    "method_input_exporter_v3": (
        "experiments/execution/tooling/p_policy_source_v3.py",
        PINNED_P_SOURCE_SHA,
    ),
    "prediction_sealer": ("experiments/execution/tooling/sealing.py", PINNED_B0_SOURCE_SHA),
    "rq1_rq2_scorer": ("experiments/execution/tooling/scoring.py", PINNED_B0_SOURCE_SHA),
    "semantic_validity": ("experiments/execution/tooling/validity.py", PINNED_B0_SOURCE_SHA),
    "b0_builder": ("experiments/execution/tooling/b0.py", PINNED_B0_SOURCE_SHA),
    "development_protocol": ("docs/g1/B0P_DEVELOPMENT_PROTOCOL_V1.md", PINNED_B0_SOURCE_SHA),
}
B0_SOURCE_FILES = (
    "experiments/execution/tooling/b0.py",
    "experiments/execution/tooling/contracts.py",
    "experiments/execution/tooling/errors.py",
    "experiments/execution/tooling/hashing.py",
)
FROZEN_B0_CONFIG_PATH = "fitness/configs/a0-monolith.yaml"
FROZEN_B0_EVALUATOR_PATH = "fitness/evaluators/a0/importlinter.toml"


class B0PPreparationError(ProtocolError):
    """A requested study cannot be prepared without violating a pinned contract."""


def prepare_development_study(
    repository: Path,
    *,
    run_id: str,
    architecture_before_sha: str,
    architecture_after_sha: str,
    b0_source_sha: str,
    p_source_sha: str,
    policy_source_sha: str,
    exposure_class: str = "CALIBRATION_EXPOSED",
) -> dict[str, Any]:
    """Prepare pinned B0/P inputs and independent Git facts without scoring or running a method.

    The output directory is write-once. The preparation stage never opens the
    reference oracle, never emits predictions, and records the current blockers
    rather than substituting prior-run evidence.
    """
    root = repository.resolve(strict=True)
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise B0PPreparationError(
            "Run ID must be 3-96 lowercase ASCII letters, digits, dot, dash or underscore"
        )
    for name, revision in (
        ("architecture_before_sha", architecture_before_sha),
        ("architecture_after_sha", architecture_after_sha),
        ("b0_source_sha", b0_source_sha),
        ("p_source_sha", p_source_sha),
        ("policy_source_sha", policy_source_sha),
    ):
        if SHA40_PATTERN.fullmatch(revision) is None:
            raise B0PPreparationError(f"{name} must be a full lowercase Git SHA")
    if exposure_class not in {"CALIBRATION_EXPOSED", "PROSPECTIVE_HELD_OUT"}:
        raise B0PPreparationError("Unsupported exposure classification")
    if exposure_class == "PROSPECTIVE_HELD_OUT":
        raise B0PPreparationError(
            "PROSPECTIVE_HELD_OUT requires independently prepared and sealed reference custody"
        )
    if b0_source_sha != PINNED_B0_SOURCE_SHA:
        raise B0PPreparationError("B0 source revision differs from the declared study baseline")
    if p_source_sha != PINNED_P_SOURCE_SHA:
        raise B0PPreparationError(
            "Method P source revision differs from its frozen PILOT-02 baseline"
        )
    if policy_source_sha != PINNED_POLICY_SOURCE_SHA:
        raise B0PPreparationError("Policy source revision differs from the declared study baseline")

    results_root = (root / "experiments/results").resolve(strict=True)
    destination = results_root / run_id
    if destination.exists() or destination.is_symlink():
        raise B0PPreparationError(f"Run output already exists and is write-once: {destination}")
    if destination.parent != results_root:
        raise B0PPreparationError("Run output must be a direct child of experiments/results")

    _require_commit(root, architecture_before_sha, "architecture before")
    _require_commit(root, architecture_after_sha, "architecture after")
    _require_commit(root, b0_source_sha, "B0 source")
    _require_commit(root, p_source_sha, "Method P source")
    if architecture_before_sha == architecture_after_sha:
        raise B0PPreparationError(
            "Architecture transition requires distinct before and after revisions"
        )

    p_source_inventory = _source_inventory(root, p_source_sha, P_SOURCE_PREFIX)
    p_source_inventory.extend(
        _source_file_record(root, p_source_sha, relative) for relative in P_SOURCE_SUPPORT_FILES
    )
    p_source_inventory.sort(key=lambda item: str(item["path"]))
    current_p_differences = _compare_workspace_to_git(root, p_source_sha, p_source_inventory)
    if current_p_differences:
        raise B0PPreparationError(
            "Current P source differs from the requested frozen revision: "
            + ", ".join(current_p_differences)
        )

    b0_source_inventory = [
        _source_file_record(root, b0_source_sha, relative) for relative in B0_SOURCE_FILES
    ]
    current_b0_differences = _compare_workspace_to_git(root, b0_source_sha, b0_source_inventory)
    if current_b0_differences:
        raise B0PPreparationError(
            "Current B0 source differs from the requested frozen revision: "
            + ", ".join(current_b0_differences)
        )
    b0_config = _git_blob(root, b0_source_sha, FROZEN_B0_CONFIG_PATH)
    b0_evaluator = _git_blob(root, b0_source_sha, FROZEN_B0_EVALUATOR_PATH)
    b0_config_sha256 = sha256_bytes(b0_config)
    b0_evaluator_sha256 = sha256_bytes(b0_evaluator)
    before_config = _git_blob(root, architecture_before_sha, FROZEN_B0_CONFIG_PATH)
    after_config = _git_blob(root, architecture_after_sha, FROZEN_B0_CONFIG_PATH)
    after_evaluator = _git_blob(root, architecture_after_sha, FROZEN_B0_EVALUATOR_PATH)
    if sha256_bytes(before_config) != b0_config_sha256:
        raise B0PPreparationError("B0 source does not preserve the frozen A0 configuration bytes")
    if sha256_bytes(after_config) != b0_config_sha256:
        raise B0PPreparationError("Target revision does not preserve frozen B0 configuration bytes")
    if sha256_bytes(after_evaluator) != b0_evaluator_sha256:
        raise B0PPreparationError("Target revision does not preserve frozen B0 evaluator bytes")

    source_facts = actual_inventory(root, architecture_before_sha, architecture_after_sha)
    facts_bytes = pretty_json_bytes(
        {
            "schema_version": 1,
            "before_sha": architecture_before_sha,
            "after_sha": architecture_after_sha,
            "exposure_class": exposure_class,
            **source_facts,
        }
    )
    facts_digest = sha256_bytes(facts_bytes)
    inventory_verification = assess_observations(
        root,
        architecture_before_sha,
        architecture_after_sha,
        source_facts,
        sha256_bytes(pretty_json_bytes(source_facts)),
    )
    if inventory_verification["assessment"] != "VERIFIED_GIT_INVENTORY":
        raise B0PPreparationError("Independent Git inventory verification did not pass")

    destination.mkdir(mode=0o755)
    (destination / "method_inputs").mkdir()
    try:
        with tempfile.TemporaryDirectory(prefix="b0p-input-export-") as temporary:
            temp_root = Path(temporary)
            b0_bundle_path = temp_root / "b0-input"
            b0_bundle = export_method_inputs(
                root,
                b0_bundle_path,
                "B0",
                architecture_before_sha,
                architecture_after_sha,
            )
            if b0_bundle["files"] is None:
                raise B0PPreparationError("B0 input exporter returned an incomplete manifest")
            b0_config_record = next(
                row for row in b0_bundle["files"] if row["role"] == "fitness_configuration"
            )
            if b0_config_record["sha256"] != b0_config_sha256:
                raise B0PPreparationError("B0 method input is not the frozen A0 configuration")

            policy_source_tree = temp_root / "policy-source-tree"
            _export_git_subtree(root, policy_source_sha, POLICY_SOURCE_PATH, policy_source_tree)
            policy_bundle_path = temp_root / "policy-source-bundle"
            policy_manifest = package_policy_source_v3(
                policy_source_tree,
                policy_bundle_path,
                f"DEV_B0P_{architecture_after_sha[:12]}",
            )
            registry = json.loads((policy_bundle_path / "fitness/policy/registry.json").read_text())
            as_of = registry.get("as_of")
            if not isinstance(as_of, str) or not as_of:
                raise B0PPreparationError("Pinned policy registry has no evaluation date")
            p_bundle_path = temp_root / "p-input"
            p_bundle = export_method_inputs_v3(
                root,
                policy_bundle_path,
                p_bundle_path,
                "P",
                architecture_before_sha,
                architecture_after_sha,
                as_of,
            )
            verify_method_bundle(b0_bundle_path, expected_method_id="B0")
            verify_method_bundle_v3(p_bundle_path, expected_method_id="P")
            shutil.copytree(b0_bundle_path, destination / "method_inputs/b0")
            shutil.copytree(p_bundle_path, destination / "method_inputs/p")

        (destination / "architecture_facts.json").write_bytes(facts_bytes)
        (destination / "git_inventory_verification.json").write_bytes(
            pretty_json_bytes(inventory_verification)
        )
        p_algorithm_sha256 = _inventory_digest(p_source_inventory)
        b0_method_sha256 = _inventory_digest(b0_source_inventory)
        source_revisions = {
            "study_base_sha": _git_text(root, "rev-parse", "HEAD"),
            "architecture_before_sha": architecture_before_sha,
            "architecture_after_sha": architecture_after_sha,
            "b0_source_sha": b0_source_sha,
            "p_source_sha": p_source_sha,
            "policy_source_sha": policy_source_sha,
        }
        instrumentation = _instrumentation_record(root, source_revisions)
        p_manifest = p_bundle
        b0_manifest = b0_bundle
        blockers = [
            "CURRENT_A0_TO_A0_1_TRANSITION_IS_CALIBRATION_EXPOSED",
            "DELTA_A2_SCENARIO_AND_REFERENCE_NOT_FROZEN_OR_INDEPENDENTLY_CUSTODIED",
            "METHOD_RUNTIME_IMAGE_NOT_BUILT_OR_PINNED",
            "EVALUATOR_RUNTIME_AND_SOURCE_TO_IMAGE_PROVENANCE_NOT_PINNED",
            "P_POLICY_SOURCE_IS_DRAFT_OPEN_WITHOUT_AUTHORITY",
            "INDEPENDENT_EXACT_PAIR_EVIDENCE_NOT_GENERATED_FOR_THIS_RUN",
            "RQ1_RESULTS_NOT_AVAILABLE_UNTIL_BOTH_ARM_PREDICTIONS_ARE_SEALED",
            "RQ2_RESULTS_NOT_AVAILABLE_UNTIL_SEALED_PREDICTIONS_AND_CURRENT_RUN_PAIR_EVIDENCE_EXIST",
        ]
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "study_id": "DEV-B0P-V1",
            "run_id": run_id,
            "execution_status": "PREPARED_NOT_EXECUTED",
            "exposure_class": exposure_class,
            "source_revisions": source_revisions,
            "b0": {
                "method_version": "B0_UNCHANGED_V1",
                "source_inventory": b0_source_inventory,
                "source_sha256": b0_method_sha256,
                "configuration_path": FROZEN_B0_CONFIG_PATH,
                "configuration_sha256": b0_config_sha256,
                "evaluator_configuration_path": FROZEN_B0_EVALUATOR_PATH,
                "evaluator_configuration_sha256": b0_evaluator_sha256,
                "input_bundle_path": "method_inputs/b0",
                "input_bundle_sha256": b0_manifest["bundle_sha256"],
            },
            "method_p": {
                "method_version": "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
                "source_inventory": p_source_inventory,
                "algorithm_sha256": p_algorithm_sha256,
                "input_bundle_path": "method_inputs/p",
                "input_bundle_sha256": p_manifest["bundle_sha256"],
                "policy_source_revision": p_manifest["policy_source_revision"],
                "policy_bundle_sha256": policy_manifest["policy_bundle_sha256"],
                "governance_status": "NOT_RUN",
                "algorithm_status": "NOT_READY",
            },
            "architecture_facts": {
                "path": "architecture_facts.json",
                "sha256": facts_digest,
                "assessment": inventory_verification["assessment"],
                "verification_path": "git_inventory_verification.json",
                "verification_sha256": sha256_bytes(pretty_json_bytes(inventory_verification)),
            },
            "instrumentation": instrumentation,
            "reference": {
                "custody": "SCORER_ONLY_NOT_OPENED_DURING_PREPARATION",
                "read_during_preparation": False,
                "required_obligation_count": 6,
                "denominator_source_path": "docs/g1/B0P_DEVELOPMENT_PROTOCOL_V1.md",
                "denominator_source_sha256": instrumentation["development_protocol_sha256"],
                "oracle_identifiers_read_during_preparation": False,
            },
            "research_gates": {"G1": "INCOMPLETE", "G4": "NOT AUTHORIZED"},
            "blockers": blockers,
        }
        validate_payload(STUDY_SCHEMA, manifest)
        (destination / "study_manifest.json").write_bytes(pretty_json_bytes(manifest))
        _write_preparation_report(destination, manifest, facts_digest)
        _write_sha256sums(destination)
        _make_files_read_only(destination)
        return manifest
    except Exception as error:
        failure_path = destination / "preparation_failure.json"
        if not failure_path.exists():
            failure = {
                "schema_version": 1,
                "run_id": run_id,
                "execution_status": "PREPARATION_FAILED",
                "error_type": type(error).__name__,
                "error": str(error),
            }
            failure_path.write_bytes(pretty_json_bytes(failure))
            _write_sha256sums(destination)
        raise


def verify_study_manifest(
    run_directory: Path,
    repository: Path | None = None,
) -> dict[str, Any]:
    """Verify prepared manifest, input bundles, source facts, and run inventory."""
    if run_directory.is_symlink():
        raise B0PPreparationError("Study directory must not be a symlink")
    root = run_directory.resolve(strict=True)
    manifest_path = root / "study_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise B0PPreparationError("Study manifest is missing or is a symlink")
    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    validate_payload(STUDY_SCHEMA, manifest)
    if manifest["run_id"] != root.name:
        raise B0PPreparationError("Study run ID does not match its output directory")
    if (
        root.parent.name != "results"
        or root.parent.parent.name != "experiments"
        or root.name in {"", ".", ".."}
    ):
        raise B0PPreparationError("Study directory must be a direct child of experiments/results")
    repository_root = repository.resolve(strict=True) if repository is not None else root.parents[2]
    expected_results_root = (repository_root / "experiments/results").resolve(strict=True)
    if root.parent != expected_results_root:
        raise B0PPreparationError("Study directory does not belong to the supplied repository")
    _verify_source_inventories(repository_root, manifest)
    _verify_frozen_b0_configuration(repository_root, manifest)
    _verify_instrumentation(repository_root, manifest)
    b0_bundle = verify_method_bundle(
        _run_artifact_path(root, manifest["b0"]["input_bundle_path"], "B0 input bundle"),
        expected_method_id="B0",
    )
    p_bundle = verify_method_bundle_v3(
        _run_artifact_path(root, manifest["method_p"]["input_bundle_path"], "P input bundle"),
        expected_method_id="P",
    )
    if b0_bundle["bundle_sha256"] != manifest["b0"]["input_bundle_sha256"]:
        raise B0PPreparationError("B0 input bundle digest differs from study manifest")
    if p_bundle["bundle_sha256"] != manifest["method_p"]["input_bundle_sha256"]:
        raise B0PPreparationError("P input bundle digest differs from study manifest")
    source_revisions = manifest["source_revisions"]
    for label, bundle in (("b0", b0_bundle), ("method_p", p_bundle)):
        if bundle.get("architecture_before_sha") != source_revisions["architecture_before_sha"]:
            raise B0PPreparationError(f"{label} input has the wrong before architecture SHA")
        if bundle.get("architecture_source_sha") != source_revisions["architecture_after_sha"]:
            raise B0PPreparationError(f"{label} input has the wrong after architecture SHA")
    facts_path = _run_artifact_path(
        root, manifest["architecture_facts"]["path"], "architecture facts"
    )
    if not facts_path.is_file():
        raise B0PPreparationError("Architecture facts are missing or a symlink")
    facts_bytes = facts_path.read_bytes()
    if sha256_bytes(facts_bytes) != manifest["architecture_facts"]["sha256"]:
        raise B0PPreparationError("Architecture fact digest differs from study manifest")
    facts = cast(dict[str, Any], json.loads(facts_bytes))
    if facts.get("before_sha") != source_revisions["architecture_before_sha"]:
        raise B0PPreparationError("Architecture facts have the wrong before architecture SHA")
    if facts.get("after_sha") != source_revisions["architecture_after_sha"]:
        raise B0PPreparationError("Architecture facts have the wrong after architecture SHA")
    for field in ("before_module_names", "after_module_names"):
        if not isinstance(facts.get(field), list) or not facts[field]:
            raise B0PPreparationError(f"Architecture facts are missing a non-empty {field}")
    for field in ("added_module_names", "removed_module_names"):
        if not isinstance(facts.get(field), list):
            raise B0PPreparationError(f"Architecture facts are missing {field}")
    verification_path = _run_artifact_path(
        root, manifest["architecture_facts"]["verification_path"], "Git inventory verification"
    )
    if not verification_path.is_file():
        raise B0PPreparationError("Independent Git inventory record is missing or a symlink")
    verification = cast(dict[str, Any], json.loads(verification_path.read_text(encoding="utf-8")))
    if verification.get("assessment") != "VERIFIED_GIT_INVENTORY":
        raise B0PPreparationError("Independent Git inventory is not verified")
    if verification.get("before_sha") != source_revisions["architecture_before_sha"]:
        raise B0PPreparationError("Independent Git inventory uses the wrong before SHA")
    if verification.get("after_sha") != source_revisions["architecture_after_sha"]:
        raise B0PPreparationError("Independent Git inventory uses the wrong after SHA")
    if verification.get("observations_sha256") != sha256_bytes(
        pretty_json_bytes(
            {
                field: facts[field]
                for field in (
                    "before_module_names",
                    "after_module_names",
                    "added_module_names",
                    "removed_module_names",
                )
            }
        )
    ):
        raise B0PPreparationError("Independent Git inventory observations digest differs")
    if (
        sha256_bytes(verification_path.read_bytes())
        != manifest["architecture_facts"]["verification_sha256"]
    ):
        raise B0PPreparationError("Independent Git inventory digest differs from study manifest")
    if facts.get("exposure_class") != manifest["exposure_class"]:
        raise B0PPreparationError("Architecture facts have the wrong exposure classification")
    expected_observations = actual_inventory(
        repository_root,
        source_revisions["architecture_before_sha"],
        source_revisions["architecture_after_sha"],
    )
    if any(facts.get(field) != value for field, value in expected_observations.items()):
        raise B0PPreparationError(
            "Architecture facts differ from independently recomputed Git inventory"
        )
    _verify_sha256sums(root)
    return manifest


def _verify_source_inventories(repository: Path, manifest: Mapping[str, Any]) -> None:
    revisions = manifest["source_revisions"]
    if (
        revisions["b0_source_sha"] != PINNED_B0_SOURCE_SHA
        or revisions["p_source_sha"] != PINNED_P_SOURCE_SHA
        or revisions["policy_source_sha"] != PINNED_POLICY_SOURCE_SHA
    ):
        raise B0PPreparationError("Study manifest contains an unapproved source revision")
    b0_expected = [
        _source_file_record(repository, revisions["b0_source_sha"], path)
        for path in B0_SOURCE_FILES
    ]
    p_expected = _source_inventory(repository, revisions["p_source_sha"], P_SOURCE_PREFIX)
    p_expected.extend(
        _source_file_record(repository, revisions["p_source_sha"], path)
        for path in P_SOURCE_SUPPORT_FILES
    )
    p_expected.sort(key=lambda item: str(item["path"]))
    for label, expected, digest_field in (
        ("B0", b0_expected, "source_sha256"),
        ("P", p_expected, "algorithm_sha256"),
    ):
        section = manifest["b0"] if label == "B0" else manifest["method_p"]
        recorded = section["source_inventory"]
        if recorded != expected or section[digest_field] != _inventory_digest(expected):
            raise B0PPreparationError(
                f"{label} source inventory differs from its pinned Git revision"
            )
    with tempfile.TemporaryDirectory(prefix="b0p-policy-verify-") as temporary:
        temp_root = Path(temporary)
        policy_tree = temp_root / "policy-source-tree"
        _export_git_subtree(
            repository,
            revisions["policy_source_sha"],
            POLICY_SOURCE_PATH,
            policy_tree,
        )
        policy_bundle = package_policy_source_v3(
            policy_tree,
            temp_root / "policy-source-bundle",
            f"DEV_B0P_{revisions['policy_source_sha'][:12]}",
        )
    if policy_bundle["policy_bundle_sha256"] != manifest["method_p"]["policy_bundle_sha256"]:
        raise B0PPreparationError("Policy bundle differs from its pinned Git source revision")


def _instrumentation_record(
    repository: Path,
    source_revisions: Mapping[str, str],
) -> dict[str, Any]:
    worktree_root = Path(__file__).resolve().parents[3]
    current_revision = _git_text(worktree_root, "rev-parse", "HEAD")
    runner_paths = (
        "experiments/execution/tooling/b0p_development.py",
        "scripts/verify_b0p_git_inventory.py",
        "scripts/prepare_b0p_development_comparison.py",
        "scripts/verify_b0p_development_comparison.py",
        f"experiments/execution/schemas/{STUDY_SCHEMA}",
    )
    runner_state = (
        "UNCOMMITTED_WORKTREE"
        if _git_text(worktree_root, "status", "--porcelain", "--", *runner_paths)
        else "COMMITTED"
    )
    source_hashes = {
        name: sha256_bytes(_git_blob(repository, revision, path))
        for name, (path, revision) in SCORING_SUPPORT_FILES.items()
    }
    worktree_hashes = {
        "runner_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "independent_inventory_verifier_sha256": sha256_bytes(
            (worktree_root / "scripts/verify_b0p_git_inventory.py").read_bytes()
        ),
        "preparation_cli_sha256": sha256_bytes(
            (worktree_root / "scripts/prepare_b0p_development_comparison.py").read_bytes()
        ),
        "readback_cli_sha256": sha256_bytes(
            (worktree_root / "scripts/verify_b0p_development_comparison.py").read_bytes()
        ),
        "study_manifest_schema_sha256": sha256_bytes(
            (worktree_root / "experiments/execution/schemas" / STUDY_SCHEMA).read_bytes()
        ),
    }
    return {
        "runner_revision": current_revision,
        "runner_source_state": runner_state,
        "study_base_sha": source_revisions["study_base_sha"],
        "method_input_exporter_v1_sha256": source_hashes["method_input_exporter_v1"],
        "method_input_exporter_v3_sha256": source_hashes["method_input_exporter_v3"],
        "prediction_sealer_sha256": source_hashes["prediction_sealer"],
        "scorer_sha256": source_hashes["rq1_rq2_scorer"],
        "semantic_validity_sha256": source_hashes["semantic_validity"],
        "b0_builder_sha256": source_hashes["b0_builder"],
        "development_protocol_sha256": source_hashes["development_protocol"],
        **worktree_hashes,
        "p_runtime_image_digest": None,
        "evaluator_runtime_pins_status": "NOT_PINNED",
    }


def _verify_instrumentation(repository: Path, manifest: Mapping[str, Any]) -> None:
    instrumentation = manifest["instrumentation"]
    pinned_fields = {
        "method_input_exporter_v1_sha256": SCORING_SUPPORT_FILES["method_input_exporter_v1"],
        "method_input_exporter_v3_sha256": SCORING_SUPPORT_FILES["method_input_exporter_v3"],
        "prediction_sealer_sha256": SCORING_SUPPORT_FILES["prediction_sealer"],
        "scorer_sha256": SCORING_SUPPORT_FILES["rq1_rq2_scorer"],
        "semantic_validity_sha256": SCORING_SUPPORT_FILES["semantic_validity"],
        "b0_builder_sha256": SCORING_SUPPORT_FILES["b0_builder"],
        "development_protocol_sha256": SCORING_SUPPORT_FILES["development_protocol"],
    }
    for field, (path, revision) in pinned_fields.items():
        if instrumentation[field] != sha256_bytes(_git_blob(repository, revision, path)):
            raise B0PPreparationError(f"Pinned instrumentation source differs: {path}")

    worktree_root = Path(__file__).resolve().parents[3]
    runner_files = {
        "runner_sha256": "experiments/execution/tooling/b0p_development.py",
        "independent_inventory_verifier_sha256": "scripts/verify_b0p_git_inventory.py",
        "preparation_cli_sha256": "scripts/prepare_b0p_development_comparison.py",
        "readback_cli_sha256": "scripts/verify_b0p_development_comparison.py",
        "study_manifest_schema_sha256": f"experiments/execution/schemas/{STUDY_SCHEMA}",
    }

    def read_runner_source(path: str) -> bytes:
        if instrumentation["runner_source_state"] == "COMMITTED":
            return _git_blob(repository, instrumentation["runner_revision"], path)
        return (worktree_root / path).read_bytes()

    for field, path in runner_files.items():
        if instrumentation[field] != sha256_bytes(read_runner_source(path)):
            raise B0PPreparationError(f"Recorded study runner source digest differs: {path}")


def _verify_frozen_b0_configuration(repository: Path, manifest: Mapping[str, Any]) -> None:
    revisions = manifest["source_revisions"]
    b0 = manifest["b0"]
    frozen_config = sha256_bytes(
        _git_blob(repository, revisions["b0_source_sha"], FROZEN_B0_CONFIG_PATH)
    )
    frozen_evaluator = sha256_bytes(
        _git_blob(repository, revisions["b0_source_sha"], FROZEN_B0_EVALUATOR_PATH)
    )
    before_config = sha256_bytes(
        _git_blob(repository, revisions["architecture_before_sha"], FROZEN_B0_CONFIG_PATH)
    )
    after_config = sha256_bytes(
        _git_blob(repository, revisions["architecture_after_sha"], FROZEN_B0_CONFIG_PATH)
    )
    after_evaluator = sha256_bytes(
        _git_blob(repository, revisions["architecture_after_sha"], FROZEN_B0_EVALUATOR_PATH)
    )
    if (
        before_config != b0["configuration_sha256"]
        or before_config != frozen_config
        or after_config != frozen_config
        or frozen_evaluator != b0["evaluator_configuration_sha256"]
        or after_evaluator != frozen_evaluator
    ):
        raise B0PPreparationError(
            "Frozen B0 configuration or evaluator differs across architecture revisions"
        )


def _run_artifact_path(root: Path, value: object, label: str) -> Path:
    if not isinstance(value, str):
        raise B0PPreparationError(f"{label} path must be a string")
    relative = PurePosixPath(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts or "\\" in value:
        raise B0PPreparationError(f"{label} path is unsafe")
    target = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise B0PPreparationError(f"{label} path traverses a symlink")
    if not target.resolve(strict=True).is_relative_to(root):
        raise B0PPreparationError(f"{label} path escapes the study directory")
    return target


def _require_commit(repository: Path, revision: str, label: str) -> None:
    if _git_text(repository, "cat-file", "-t", revision) != "commit":
        raise B0PPreparationError(f"{label} revision is not an available Git commit")


def _git_text(repository: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise B0PPreparationError("Git executable is required")
    result = subprocess.run(  # noqa: S603  # nosec B603
        [executable, "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return result.stdout.strip()


def _git_blob(repository: Path, revision: str, relative_path: str) -> bytes:
    executable = shutil.which("git")
    if executable is None:
        raise B0PPreparationError("Git executable is required")
    result = subprocess.run(  # noqa: S603  # nosec B603
        [executable, "-C", str(repository), "show", f"{revision}:{relative_path}"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return result.stdout


def _source_inventory(repository: Path, revision: str, prefix: str) -> list[dict[str, Any]]:
    names = _git_text(
        repository,
        "ls-tree",
        "-r",
        "--name-only",
        revision,
        "--",
        "experiments/execution/tooling",
    )
    files = [
        name for name in names.splitlines() if name.startswith(prefix) and name.endswith(".py")
    ]
    if not files:
        raise B0PPreparationError(f"Pinned source inventory is empty: {prefix}")
    return [_source_file_record(repository, revision, relative) for relative in files]


def _source_file_record(repository: Path, revision: str, relative: str) -> dict[str, Any]:
    content = _git_blob(repository, revision, relative)
    return {"path": relative, "size_bytes": len(content), "sha256": sha256_bytes(content)}


def _compare_workspace_to_git(
    repository: Path,
    revision: str,
    source_inventory: Sequence[Mapping[str, Any]],
) -> list[str]:
    differences: list[str] = []
    for record in source_inventory:
        relative = str(record["path"])
        path = repository / relative
        if path.is_symlink() or not path.is_file():
            differences.append(relative)
            continue
        content = path.read_bytes()
        if sha256_bytes(content) != record["sha256"]:
            differences.append(relative)
    return differences


def _inventory_digest(inventory: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(pretty_json_bytes([dict(item) for item in inventory]))


def _export_git_subtree(
    repository: Path,
    revision: str,
    subtree: str,
    destination: Path,
) -> None:
    """Export a pinned Git subtree without reading the mutable worktree."""
    executable = shutil.which("git")
    if executable is None:
        raise B0PPreparationError("Git executable is required")
    result = subprocess.run(  # noqa: S603  # nosec B603
        [executable, "-C", str(repository), "ls-tree", "-r", "-z", revision, "--", subtree],
        check=True,
        capture_output=True,
        timeout=30,
    )
    entries: list[tuple[str, str]] = []
    for raw_entry in result.stdout.split(b"\0"):
        if not raw_entry:
            continue
        try:
            metadata, raw_path = raw_entry.split(b"\t", 1)
            git_mode, object_type, _object_sha = metadata.split(b" ", 2)
            relative = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise B0PPreparationError("Malformed pinned policy source tree") from error
        if (
            git_mode == b"120000"
            or object_type != b"blob"
            or git_mode not in {b"100644", b"100755"}
        ):
            raise B0PPreparationError("Pinned policy source must contain regular files only")
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or not relative.startswith(subtree + "/"):
            raise B0PPreparationError("Pinned policy source contains an unsafe path")
        entries.append((relative, git_mode.decode("ascii")))
    if not entries:
        raise B0PPreparationError("Pinned policy source tree is empty")
    destination.mkdir(parents=True)
    for relative, file_mode in entries:
        output = destination.joinpath(
            *PurePosixPath(relative).parts[len(PurePosixPath(subtree).parts) :]
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        content = _git_blob(repository, revision, relative)
        output.write_bytes(content)
        output.chmod(0o755 if file_mode == "100755" else 0o644)


def _write_preparation_report(
    destination: Path,
    manifest: Mapping[str, Any],
    architecture_facts_sha256: str,
) -> None:
    lines = [
        "# B0/P DEVELOPMENT preparation report",
        "",
        f"Run ID: `{manifest['run_id']}`",
        f"Execution status: **{manifest['execution_status']}**",
        f"Exposure classification: **{manifest['exposure_class']}**",
        f"Architecture-facts SHA-256: `{architecture_facts_sha256}`",
        "",
        "## Verified preparation",
        "",
        (
            "- B0 and P method-input bundles were exported from the recorded Git revisions "
            "and verified against their versioned allowlists."
        ),
        (
            "- Python-module inventories were independently recomputed from the before and after "
            "Git trees."
        ),
        (
            "- Frozen B0 configuration and Import Linter configuration bytes match in both "
            "architecture revisions."
        ),
        "- The reference oracle and scorer were not opened during preparation.",
        "- Existing PILOT-02 artifacts were not imported or reused.",
        "",
        "## Execution status",
        "",
        (
            "No B0 or P prediction was produced by this preparation command. No evaluator was "
            "run and no RQ1/RQ2 score is reported."
        ),
        (
            "The P bundle carries the source-pinned DRAFT/OPEN policy source; policy authority "
            "and semantic coverage remain unresolved."
        ),
        (
            "The full RQ2 denominator is six obligations per the frozen DEVELOPMENT protocol; "
            "no oracle identifiers were read during preparation."
        ),
        "",
        "## Remaining blockers",
        "",
    ]
    lines.extend(f"- `{blocker}`" for blocker in manifest["blockers"])
    lines.extend(
        [
            "",
            (
                "G1 remains INCOMPLETE and G4 remains NOT AUTHORIZED. This preparation is "
                "DEVELOPMENT-only and does not amend either gate."
            ),
            "",
        ]
    )
    (destination / "experiment_report.md").write_text("\n".join(lines), encoding="utf-8")


def _write_sha256sums(root: Path) -> None:
    rows: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "SHA256SUMS":
            continue
        relative = path.relative_to(root).as_posix()
        rows.append(f"{sha256_bytes(path.read_bytes())}  {relative}")
    sums_path = root / "SHA256SUMS"
    if sums_path.exists():
        raise B0PPreparationError("SHA256SUMS already exists; run output is write-once")
    sums_path.write_text("\n".join(rows) + "\n", encoding="ascii")


def _verify_sha256sums(root: Path) -> None:
    sums_path = root / "SHA256SUMS"
    if sums_path.is_symlink() or not sums_path.is_file():
        raise B0PPreparationError("Run SHA256SUMS file is missing")
    declared: dict[str, str] = {}
    for line in sums_path.read_text(encoding="ascii").splitlines():
        try:
            digest, relative = line.split("  ", 1)
        except ValueError as error:
            raise B0PPreparationError("Malformed SHA256SUMS row") from error
        if SHA256_PATTERN.fullmatch(digest) is None or relative in declared:
            raise B0PPreparationError("Malformed or duplicate SHA256SUMS row")
        path_part = PurePosixPath(relative)
        if path_part.is_absolute() or ".." in path_part.parts or relative == "SHA256SUMS":
            raise B0PPreparationError("Unsafe SHA256SUMS path")
        path = root.joinpath(*path_part.parts)
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise B0PPreparationError(f"Missing or unsafe run artifact: {relative}")
        actual = sha256_bytes(path.read_bytes())
        if actual != digest:
            raise B0PPreparationError(f"Run artifact digest mismatch: {relative}")
        declared[relative] = digest
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    if actual_files != set(declared):
        raise B0PPreparationError("Run inventory differs from SHA256SUMS")


def _make_files_read_only(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(path.stat().st_mode & ~0o222)


__all__ = [
    "B0PPreparationError",
    "prepare_development_study",
    "verify_study_manifest",
]
