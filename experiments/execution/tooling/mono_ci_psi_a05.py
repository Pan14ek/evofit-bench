"""Bounded A0.4→A0.5 adapter over the existing isolated Method Ψ runner."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed Git argv only
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

import experiments.execution.tooling.mono_ci_psi_transition as transition
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
)
from experiments.execution.tooling.mono_ci_psi_coverage import (
    _REQUIREMENT_CAPABILITY_MAPPINGS,
    assess_adaptation_necessity,
    verify_inspection_coverage,
)
from experiments.execution.tooling.mono_ci_psi_evidence import (
    build_inspection_scope_artifact,
    evaluator_source_artifacts,
    run_fresh_evaluator,
)
from experiments.execution.tooling.p_candidate import candidate_sha256

BEFORE_COMMIT = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
BEFORE_REPOSITORY_TREE = "2b436e0aaf09403ea516d73d20a466a122f86592"
BEFORE_APPLICATION_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
BEFORE_STATE = "A0_4_REPORT_QUERY_PORT"
AFTER_STATE = "A0_5_MODULE_DATA_OWNERSHIP"
BASELINE_NAME = "RECONSTRUCTED_B0_A04_V1.json"
BASELINE_SCHEMA = "mono_ci_b0_psi_reconstructed_baseline_a04_v1.schema.json"
BASELINE_RELATIVE = "experiments/execution/mono-ci-b0-psi-execution-a05-v1"
BASELINE_ID = "MONO_CI_RECONSTRUCTED_B0_A04_V1"
OWNERSHIP_EVALUATOR = "AC_DATA_OWNERSHIP"
PROBE_PATH = "app/modules/tasks/repository.py"
PROBE_SOURCE = (
    "\n\nfrom sqlalchemy import MetaData, Table\n\n"
    "def _a05_probe_foreign_notification_table(session):\n"
    '    foreign_table = Table("notifications", MetaData(), autoload_with=session.bind)\n'
    "    return session.execute(select(foreign_table)).all()\n"
)
PROBE_RELATIVE_ROOT = "probes/ownership-negative"
PROBE_COMMIT_MESSAGE = "isolated A0.5 ownership violation probe"
PROBE_AUTHOR = "EvoFitBench A05 Probe"
PROBE_EMAIL = "a05-probe@example.invalid"
PROBE_COMMIT_DATE = "2026-10-26T00:00:00+0000"


def _git_text(repository: Path, *args: str) -> str:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv only
        [git_binary, "-C", str(repository), *args],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
    )
    if result.returncode:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_READ_FAILED")
    return result.stdout.strip()


def _git_bytes(repository: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv only
        [git_binary, "-C", str(repository), *args],
        check=False,
        capture_output=True,
        input=input_bytes,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
    )
    if result.returncode:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_READ_FAILED")
    return result.stdout


def _safe_probe_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATH_INVALID")
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATH_INVALID")
    return path.as_posix()


def _deterministic_probe_commit(checkout: Path) -> str:
    environment = {
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
        "GIT_AUTHOR_DATE": PROBE_COMMIT_DATE,
        "GIT_COMMITTER_DATE": PROBE_COMMIT_DATE,
    }
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_EXECUTABLE_MISSING")
    add = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv only
        [git_binary, "-C", str(checkout), "add", "--", PROBE_PATH],
        check=False,
        capture_output=True,
        env=environment,
    )
    if add.returncode:
        raise ProtocolError("MONO_CI_PSI_A05_PROBE_STAGE_FAILED")
    commit = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv only
        [
            git_binary,
            "-C",
            str(checkout),
            "-c",
            f"user.name={PROBE_AUTHOR}",
            "-c",
            f"user.email={PROBE_EMAIL}",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "-m",
            PROBE_COMMIT_MESSAGE,
        ],
        check=False,
        capture_output=True,
        env=environment,
    )
    if commit.returncode:
        raise ProtocolError("MONO_CI_PSI_A05_PROBE_COMMIT_FAILED")
    return _git_text(checkout, "rev-parse", "HEAD")


def _probe_patch_paths(patch_bytes: bytes) -> list[str]:
    try:
        patch_text = patch_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_INVALID") from error
    paths: list[str] = []
    old_paths: list[str] = []
    new_paths: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            match = re.fullmatch(r"diff --git a/(.+) b/(.+)", line)
            if match is None:
                raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_PATH_INVALID")
            left, right = (_safe_probe_path(match.group(1)), _safe_probe_path(match.group(2)))
            if left != right:
                raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_PATH_INVALID")
            paths.append(left)
        elif line.startswith("--- "):
            header_path = line[4:].split("\t", maxsplit=1)[0]
            expected_prefix = "a/"
            if not header_path.startswith(expected_prefix):
                raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_PATH_INVALID")
            old_paths.append(_safe_probe_path(header_path.removeprefix(expected_prefix)))
        elif line.startswith("+++ "):
            header_path = line[4:].split("\t", maxsplit=1)[0]
            expected_prefix = "b/"
            if not header_path.startswith(expected_prefix):
                raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_PATH_INVALID")
            new_paths.append(_safe_probe_path(header_path.removeprefix(expected_prefix)))
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_PATH_INVALID")
    if not paths or len(paths) != len(set(paths)) or old_paths != paths or new_paths != paths:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_INVALID")
    return sorted(paths)


@contextlib.contextmanager
def replay_negative_probe(
    repository: Path,
    probe_artifact_root: Path,
    *,
    expected_parent_commit: str,
    expected_parent_tree: str,
    expected_parent_application_tree: str,
    output: Path | None = None,
) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Recreate and verify the archived negative source from its committed parent.

    The synthesized probe commit is deterministic and local to the checkout. It is
    recreated from the archived patch; no remote probe commit object is required.
    """
    repo = repository.resolve(strict=True)
    if probe_artifact_root.is_symlink() or probe_artifact_root.parent.is_symlink():
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_ARTIFACT_SYMLINK_FORBIDDEN")
    artifact_root = probe_artifact_root.resolve(strict=True)
    if any(path.is_symlink() for path in artifact_root.rglob("*")):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_ARTIFACT_SYMLINK_FORBIDDEN")
    manifest_path = artifact_root / "probe-manifest.json"
    patch_path = artifact_root / "source.patch"
    if any(path.is_symlink() or not path.is_file() for path in (manifest_path, patch_path)):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_ARTIFACT_MISSING")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        patch_bytes = patch_path.read_bytes()
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_ARTIFACT_INVALID") from error
    validate_payload("mono_ci_psi_a05_probe_manifest_v1.schema.json", manifest)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != "MONO_CI_PSI_A05_PROBE_MANIFEST_V1"
        or sha256_bytes(patch_bytes) != manifest.get("patch_sha256")
        or manifest.get("parent_commit_sha") != expected_parent_commit
        or manifest.get("parent_repository_tree_sha") != expected_parent_tree
        or manifest.get("parent_application_tree_sha") != expected_parent_application_tree
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_MANIFEST_BINDING_MISMATCH")
    source_rows = manifest.get("changed_sources")
    if not isinstance(source_rows, list) or len(source_rows) != 1:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_SOURCE_INVENTORY_INVALID")
    source_row = source_rows[0]
    path = _safe_probe_path(source_row.get("path"))
    if path != PROBE_PATH or _probe_patch_paths(patch_bytes) != [path]:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATH_INVENTORY_MISMATCH")
    source_relpath = source_row.get("artifact_path")
    if source_relpath != f"source-files/{path}":
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_SOURCE_ARTIFACT_PATH_INVALID")
    source_file = artifact_root / source_relpath
    if source_file.is_symlink() or not source_file.is_file():
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_SOURCE_ARTIFACT_MISSING")
    modified_bytes = source_file.read_bytes()
    if (
        sha256_bytes(modified_bytes) != source_row.get("modified_file_sha256")
        or PROBE_SOURCE.encode("utf-8") not in modified_bytes
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_SOURCE_DIGEST_MISMATCH")
    actual_parent_tree = _git_text(repo, "rev-parse", f"{expected_parent_commit}^{{tree}}")
    actual_parent_app = _git_text(repo, "rev-parse", f"{expected_parent_commit}:app")
    original_bytes = _git_bytes(repo, "show", f"{expected_parent_commit}:{path}")
    if (
        actual_parent_tree != expected_parent_tree
        or actual_parent_app != expected_parent_application_tree
        or sha256_bytes(original_bytes) != source_row.get("original_file_sha256")
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PARENT_SOURCE_MISMATCH")

    if (
        re.fullmatch(r"[a-f0-9]{40}", expected_parent_commit) is None
        or _git_text(repo, "rev-parse", f"{expected_parent_commit}^{{commit}}")
        != expected_parent_commit
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PARENT_COMMIT_NOT_CANONICAL")

    temporary: tempfile.TemporaryDirectory[str] | None = None
    publication_staging: tempfile.TemporaryDirectory[str] | None = None
    output_target: Path | None = None
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_EXECUTABLE_MISSING")
    if output is None:
        temporary = tempfile.TemporaryDirectory(prefix="mono-ci-a05-probe-replay-")
        checkout = Path(temporary.name) / "source"
    else:
        if output.name in {"", ".", ".."}:
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_OUTPUT_PATH_INVALID")
        output_target = output.parent.resolve(strict=True) / output.name
        if output_target.exists() or output_target.is_symlink():
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_OUTPUT_MUST_BE_NEW")
        publication_staging = tempfile.TemporaryDirectory(
            prefix=".mono-ci-a05-probe-replay-", dir=output_target.parent
        )
        checkout = Path(publication_staging.name) / "source"
    clone = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv only
        [git_binary, "clone", "--quiet", "--shared", "--no-checkout", str(repo), str(checkout)],
        check=False,
        capture_output=True,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
    )
    try:
        if clone.returncode:
            raise ProtocolError("MONO_CI_PSI_A05_PROBE_REPLAY_CLONE_FAILED")
        _git_text(checkout, "checkout", "--quiet", "--detach", expected_parent_commit)
        checked = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv; patch is stdin only
            [git_binary, "-C", str(checkout), "apply", "--check", "--binary"],
            input=patch_bytes,
            check=False,
            capture_output=True,
            env={"PATH": os.defpath, "LANG": "C.UTF-8"},
        )
        if checked.returncode:
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_DOES_NOT_APPLY")
        applied = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv; patch is stdin only
            [git_binary, "-C", str(checkout), "apply", "--binary"],
            input=patch_bytes,
            check=False,
            capture_output=True,
            env={"PATH": os.defpath, "LANG": "C.UTF-8"},
        )
        if applied.returncode:
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_APPLY_FAILED")
        changed_paths = _git_text(
            checkout, "diff", "--name-only", "--diff-filter=ACDMRTUXB"
        ).splitlines()
        replayed_file = checkout / path
        if (
            changed_paths != [path]
            or replayed_file.is_symlink()
            or not replayed_file.is_file()
            or replayed_file.read_bytes() != modified_bytes
            or sha256_bytes(replayed_file.read_bytes()) != source_row["modified_file_sha256"]
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PATCH_SOURCE_DISAGREEMENT")
        _git_text(checkout, "diff", "--check")
        commit_sha = _deterministic_probe_commit(checkout)
        tree_sha = _git_text(checkout, "rev-parse", "HEAD^{tree}")
        app_tree_sha = _git_text(checkout, "rev-parse", "HEAD:app")
        if (
            commit_sha != manifest["probe_commit_sha"]
            or tree_sha != manifest["probe_repository_tree_sha"]
            or app_tree_sha != manifest["probe_application_tree_sha"]
            or _git_text(checkout, "rev-parse", "HEAD^") != expected_parent_commit
            or _git_text(checkout, "status", "--porcelain")
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_REPLAY_IDENTITY_MISMATCH")
        published_checkout = checkout
        if output_target is not None:
            try:
                os.rename(checkout, output_target)
            except OSError as error:
                raise ContractValidationError(
                    "MONO_CI_PSI_A05_PROBE_OUTPUT_PUBLICATION_FAILED"
                ) from error
            published_checkout = output_target
        yield published_checkout, manifest
    finally:
        if temporary is not None:
            temporary.cleanup()
        if publication_staging is not None:
            publication_staging.cleanup()


def _validate_a04_proposal(repository: Path) -> dict[str, Any]:
    proposal_root = repository / BASELINE_RELATIVE
    checksum_path = proposal_root / "SHA256SUMS"
    if not checksum_path.is_file() or checksum_path.is_symlink():
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_INVENTORY_MISSING")
    declared: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if match is None or match.group(2) in declared:
            raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_INVENTORY_INVALID")
        declared[match.group(2)] = match.group(1)
    actual: dict[str, str] = {}
    for path in proposal_root.rglob("*"):
        if path.is_symlink():
            raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_SYMLINK_FORBIDDEN")
        if path.is_file() and path != checksum_path:
            actual[path.relative_to(proposal_root).as_posix()] = sha256_file(path)
    if declared != actual:
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_INVENTORY_MISMATCH")
    proposal_path = proposal_root / BASELINE_NAME
    proposal_bytes = proposal_path.read_bytes()
    proposal = json.loads(proposal_bytes)
    validate_payload(BASELINE_SCHEMA, proposal)
    digest = sha256_bytes(proposal_bytes)
    sidecar = (proposal_root / f"{BASELINE_NAME}.sha256").read_text(encoding="utf-8").strip()
    if sidecar != f"{digest}  {BASELINE_NAME}":
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_SIDECAR_MISMATCH")
    if (
        _git_text(repository, "rev-parse", f"{BEFORE_COMMIT}^{{tree}}") != BEFORE_REPOSITORY_TREE
        or _git_text(repository, "rev-parse", f"{BEFORE_COMMIT}:app") != BEFORE_APPLICATION_TREE
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_A04_BASELINE_SOURCE_MISMATCH")
    manifest_bytes = transition._git_bytes(
        repository, BEFORE_COMMIT, f"architecture/states/{BEFORE_STATE}.yaml"
    )
    if sha256_bytes(manifest_bytes) != proposal["derivation"]["state_manifest_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_MANIFEST_DIGEST_MISMATCH")
    rows = {row["evaluator_id"]: row for row in proposal["representations"]}
    if set(rows) != {"AC_PUBLIC_API", "AC_MODULE_GRAPH"}:
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_CONTROL_SET_MISMATCH")
    for evaluator_id, config_path in transition.EVALUATOR_CONFIGS.items():
        source_rows, _source_manifest, source_digest = evaluator_source_artifacts(repository)
        row = rows[evaluator_id]
        if (
            row["evaluator_source_sha256"] != source_digest
            or row["evaluator_configuration_sha256"] != sha256_file(repository / config_path)
            or not source_rows
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_EVALUATOR_BINDING_MISMATCH")
    return {
        "baseline_id": BASELINE_ID,
        "baseline_configuration_sha256": digest,
        "identity_status": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
        "approval_status": "NOT_APPROVED",
    }


def _candidate_obligation_coverage(
    representations: list[dict[str, Any]], obligation_id: str
) -> list[str]:
    """Return active candidate representation IDs that explicitly cover an obligation."""
    return sorted(
        str(row["id"])
        for row in representations
        if row.get("active") is True
        and isinstance(row.get("covers"), list)
        and obligation_id in row["covers"]
    )


def _prepare_candidate_bindings(
    *,
    candidate_value: Any,
    repository: Path,
    run_root: Path,
    after_commit: str,
    method_input_bundle_sha256: str,
    evaluator_source_manifest_bytes: bytes,
    evaluator_source_sha256: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Materialize the exact Method Ψ candidate and independently check active bindings."""
    if candidate_value is None:
        return None, []
    if not isinstance(candidate_value, dict):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_SHAPE_INVALID")
    validate_payload("p_candidate_configuration_v1.schema.json", candidate_value)
    candidate_digest = candidate_sha256(candidate_value)
    if (
        candidate_value.get("architecture_source_sha") != after_commit
        or candidate_value.get("input_bundle_sha256") != method_input_bundle_sha256
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_SOURCE_BINDING_MISMATCH")
    parent = candidate_value.get("parent_configuration")
    if not isinstance(parent, dict):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_PARENT_BINDING_INVALID")
    parent_path = parent.get("path")
    parent_sha256 = parent.get("sha256")
    parent_bytes = (
        run_root / "PSI/method-input" / str(parent_path) if isinstance(parent_path, str) else None
    )
    if (
        parent_bytes is None
        or parent_bytes.is_symlink()
        or not parent_bytes.is_file()
        or sha256_file(parent_bytes) != parent_sha256
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_PARENT_BINDING_MISMATCH")

    candidate_path = run_root / "diagnostics/materialized-method-candidate.json"
    candidate_bytes = pretty_json_bytes(candidate_value)
    transition._write_new_file(candidate_path, candidate_bytes)
    if candidate_sha256(json.loads(candidate_path.read_text(encoding="utf-8"))) != candidate_digest:
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_MATERIALIZATION_MISMATCH")

    active_bindings: list[dict[str, Any]] = []
    representation_rows = candidate_value.get("representations")
    if not isinstance(representation_rows, list):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_REPRESENTATIONS_INVALID")
    for representation in representation_rows:
        if not isinstance(representation, dict):
            raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_REPRESENTATIONS_INVALID")
        if representation.get("active") is not True:
            continue
        evaluator_id = representation.get("evaluator")
        evidence_contract = representation.get("evidence_contract")
        evaluator_artifact = representation.get("evaluator_artifact")
        if (
            not isinstance(evaluator_id, str)
            or not isinstance(evidence_contract, dict)
            or not isinstance(evaluator_artifact, dict)
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_ACTIVE_BINDING_INVALID")
        expected_config_path = transition.EVALUATOR_CONFIGS.get(
            evaluator_id,
            "architecture/acceptance/a1/data_ownership_v1.yaml"
            if evaluator_id == OWNERSHIP_EVALUATOR
            else None,
        )
        config_path = evidence_contract.get("configuration_path")
        config_sha256 = evidence_contract.get("configuration_sha256")
        source_sha256 = evidence_contract.get("evaluator_source_sha256")
        artifact_path = evaluator_artifact.get("path")
        artifact_sha256 = evaluator_artifact.get("sha256")
        if (
            expected_config_path is None
            or config_path != expected_config_path
            or not isinstance(config_sha256, str)
            or not isinstance(source_sha256, str)
            or not isinstance(artifact_path, str)
            or not isinstance(artifact_sha256, str)
            or config_sha256 != sha256_file(repository / expected_config_path)
            or source_sha256 != evaluator_source_sha256
            or artifact_sha256 != evaluator_source_sha256
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_EVALUATOR_BINDING_MISMATCH")
        artifact_file = run_root / artifact_path
        if (
            artifact_file.is_symlink()
            or not artifact_file.is_file()
            or sha256_file(artifact_file) != artifact_sha256
            or artifact_file.read_bytes() != evaluator_source_manifest_bytes
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_EVALUATOR_ARTIFACT_MISMATCH")
        config_bytes = (repository / expected_config_path).read_bytes()
        active_bindings.append(
            {
                "representation_id": representation.get("id"),
                "evaluator_id": evaluator_id,
                "covers": list(representation.get("covers", [])),
                "configuration_path": expected_config_path,
                "configuration_sha256": config_sha256,
                "evaluator_source_sha256": source_sha256,
                "evaluator_artifact_path": artifact_file.relative_to(run_root).as_posix(),
                "evaluator_artifact_sha256": artifact_sha256,
                "configuration_bytes": config_bytes,
            }
        )
    return (
        {
            "path": candidate_path.relative_to(run_root).as_posix(),
            "file_sha256": sha256_file(candidate_path),
            "candidate_sha256": candidate_digest,
            "configuration_version": candidate_value.get("configuration_version"),
            "validation_status": candidate_value.get("candidate_validation", {}).get("status"),
            "active_representations": [
                {key: value for key, value in binding.items() if key != "configuration_bytes"}
                for binding in active_bindings
            ],
            "representation_rows": representation_rows,
        },
        active_bindings,
    )


@contextmanager
def a05_transition_context(
    repository: Path,
    *,
    extension_builder: Any,
    after_commit: str | None = None,
    run_schema_version: str = "MONO_CI_PSI_TRANSITION_RUN_V4",
    extension_schema: str = "mono_ci_psi_a05_experiment_evidence_v2.schema.json",
) -> Iterator[None]:
    """Temporarily configure the immutable A0.4→A0.5 source pair."""
    repo = repository.resolve(strict=True)
    after_commit = after_commit or _git_text(repo, "rev-parse", "HEAD")
    if re.fullmatch(r"[a-f0-9]{40}", after_commit) is None:
        raise ContractValidationError("MONO_CI_PSI_A05_AFTER_COMMIT_INVALID")
    resolved_commit = _git_text(repo, "rev-parse", f"{after_commit}^{{commit}}")
    if resolved_commit != after_commit:
        raise ContractValidationError("MONO_CI_PSI_A05_AFTER_COMMIT_NOT_CANONICAL")
    after_repository_tree = _git_text(repo, "rev-parse", f"{after_commit}^{{tree}}")
    after_application_tree = _git_text(repo, "rev-parse", f"{after_commit}:app")
    assignments = {
        "BEFORE_COMMIT": BEFORE_COMMIT,
        "AFTER_COMMIT": after_commit,
        "BEFORE_REPOSITORY_TREE": BEFORE_REPOSITORY_TREE,
        "AFTER_REPOSITORY_TREE": after_repository_tree,
        "BEFORE_APP_TREE": BEFORE_APPLICATION_TREE,
        "AFTER_APP_TREE": after_application_tree,
        "BEFORE_STATE": BEFORE_STATE,
        "AFTER_STATE": AFTER_STATE,
        "BASELINE_NAME": BASELINE_NAME,
        "PROPOSAL_RELATIVE": BASELINE_RELATIVE,
        "verify_execution_proposal": _validate_a04_proposal,
        "TRANSITION_RUN_SCHEMA_VERSION": run_schema_version,
        "TRANSITION_UNIT_OF_ANALYSIS": "ONE_A0_4_TO_A0_5_ARCHITECTURE_TRANSITION",
        "ADAPTATION_NECESSITY_SCHEMA_VERSION": "MONO_CI_PSI_ADAPTATION_NECESSITY_V3",
        "TRANSITION_RUN_EXTENSION_BUILDER": extension_builder,
        "A05_EXPERIMENT_EVIDENCE_SCHEMA": extension_schema,
        "REPOSITORY_ROOT": repo,
    }
    previous = {name: getattr(transition, name) for name in assignments}
    try:
        for name, value in assignments.items():
            setattr(transition, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(transition, name, value)


def run_a05_transition(
    repository: Path,
    output_root: Path,
    execution_id: str,
    *,
    isolation_backend: str | None = None,
    preserve_partial_evidence: bool = False,
    sandbox_preflight_id: str | None = None,
) -> dict[str, Any]:
    """Execute the existing isolated P runner against the pinned ΔA5 transition."""
    repo = repository.resolve(strict=True)
    _validate_a04_proposal(repo)
    with a05_transition_context(repo, extension_builder=_build_a05_extension):
        return transition.run_transition(
            repo,
            output_root,
            execution_id,
            isolation_backend=isolation_backend,
            preserve_partial_evidence=preserve_partial_evidence,
            sandbox_preflight_id=sandbox_preflight_id,
        )


def _build_a05_extension(
    repository: Path, run_root: Path, run_record: dict[str, Any]
) -> dict[str, str]:
    repo = repository.resolve(strict=True)
    after_commit = run_record["transition"]["after_commit_sha"]
    after_tree = run_record["transition"]["after_repository_tree_sha"]
    after_app_tree = run_record["transition"]["after_application_tree_sha"]
    manifest_bytes = transition._git_bytes(
        repo, after_commit, f"architecture/states/{AFTER_STATE}.yaml"
    )
    manifest = yaml.safe_load(manifest_bytes)
    ownership = manifest["persistence_ownership"]
    model_registry_exception = ownership["shared_infrastructure"]["model_registry_exception"]
    requirement_value = {
        "table_owners": ownership["table_owners"],
        "model_modules": ownership["model_modules"],
        "repository_modules": ownership["repository_modules"],
        "reporting_table_owner": ownership["reporting_table_owner"],
        "prohibited_access_patterns": ownership["prohibited_access_patterns"],
        "model_registry_exception": model_registry_exception,
    }

    implementation_root = run_root / "PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP"
    source_rows, source_manifest_bytes, evaluator_source_sha256 = evaluator_source_artifacts(repo)
    source_manifest_path = implementation_root / "source-manifest.json"
    transition._write_new_file(source_manifest_path, source_manifest_bytes)
    for source_row in source_rows:
        source_path = repo / "architecture/acceptance/a1" / source_row["path"]
        source_bytes = source_path.read_bytes()
        if sha256_bytes(source_bytes) != source_row["sha256"]:
            raise ContractValidationError("MONO_CI_PSI_A05_EVALUATOR_SOURCE_CHANGED")
        transition._write_new_file(
            implementation_root / "source" / source_row["path"], source_bytes
        )
    config_relative = "architecture/acceptance/a1/data_ownership_v1.yaml"
    config_bytes = (repo / config_relative).read_bytes()
    config_sha256 = sha256_bytes(config_bytes)
    transition._write_new_file(implementation_root / "data_ownership_v1.yaml", config_bytes)
    evaluator_config = yaml.safe_load(config_bytes)
    evaluator_version = str(evaluator_config["evaluator"]["version"])

    _positive_run, positive_row = _run_bound_evaluator(
        repository=repo,
        source_checkout=repo,
        source_commit=after_commit,
        architecture_state=AFTER_STATE,
        evaluator_id=OWNERSHIP_EVALUATOR,
        output_directory=run_root / "PSI/evaluator-observations/a05-positive/AC_DATA_OWNERSHIP",
        configuration_bytes=config_bytes,
        state_manifest_bytes=manifest_bytes,
    )

    baseline_bytes = (run_root / "provenance/reconstructed-b0-proposal.json").read_bytes()
    baseline = json.loads(baseline_bytes)
    method_result = json.loads(
        (run_root / run_record["psi"]["raw_result_path"]).read_text(encoding="utf-8")
    )
    candidate_info, candidate_bindings = _prepare_candidate_bindings(
        candidate_value=method_result.get("candidate"),
        repository=repo,
        run_root=run_root,
        after_commit=after_commit,
        method_input_bundle_sha256=run_record["method_input"]["bundle_sha256"],
        evaluator_source_manifest_bytes=source_manifest_bytes,
        evaluator_source_sha256=evaluator_source_sha256,
    )
    if candidate_info is not None and candidate_info["candidate_sha256"] != method_result.get(
        "governance", {}
    ).get("candidate_configuration_sha256"):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_GOVERNANCE_DIGEST_MISMATCH")

    candidate_positive_rows = []
    for binding in candidate_bindings:
        _candidate_run, candidate_row = _run_bound_evaluator(
            repository=repo,
            source_checkout=repo,
            source_commit=after_commit,
            architecture_state=AFTER_STATE,
            evaluator_id=binding["evaluator_id"],
            output_directory=(
                run_root
                / "PSI/evaluator-observations/candidate-positive"
                / binding["representation_id"]
            ),
            configuration_bytes=binding["configuration_bytes"],
            state_manifest_bytes=manifest_bytes,
        )
        candidate_row["representation_id"] = binding["representation_id"]
        candidate_positive_rows.append(candidate_row)

    probe_dir: Path | None = None
    temporary: tempfile.TemporaryDirectory[str] | None = None
    probe_artifact_root = run_root / PROBE_RELATIVE_ROOT
    evaluator_configs: dict[str, dict[str, str]] = {}
    try:
        temporary = tempfile.TemporaryDirectory(prefix="mono-ci-psi-a05-probe-")
        probe_dir = Path(temporary.name) / "source"
        transition._git_worktree(repo, "add", "--detach", str(probe_dir), after_commit)
        probe_file = probe_dir / PROBE_PATH
        probe_file.write_text(
            probe_file.read_text(encoding="utf-8") + PROBE_SOURCE,
            encoding="utf-8",
        )
        probe_commit = _deterministic_probe_commit(probe_dir)
        probe_parent = _git_text(probe_dir, "rev-parse", "HEAD^")
        if probe_parent != after_commit:
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PARENT_MISMATCH")
        changed_paths = _git_text(
            probe_dir, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"
        ).splitlines()
        if changed_paths != [PROBE_PATH]:
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_SCOPE_INVALID")
        probe_tree = _git_text(probe_dir, "rev-parse", "HEAD^{tree}")
        probe_app_tree = _git_text(probe_dir, "rev-parse", "HEAD:app")
        patch_bytes = _git_bytes(
            probe_dir,
            "diff",
            "--binary",
            "--no-ext-diff",
            probe_parent,
            probe_commit,
            "--",
            PROBE_PATH,
        )
        modified_source = (probe_dir / PROBE_PATH).read_bytes()
        parent_source = _git_bytes(repo, "show", f"{after_commit}:{PROBE_PATH}")
        transition._write_new_file(probe_artifact_root / "source.patch", patch_bytes)
        transition._write_new_file(
            probe_artifact_root / "source-files" / PROBE_PATH,
            modified_source,
        )
        negative_rows = []
        candidate_negative_rows = []
        negative_ids = ("AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP")
        for evaluator_id in negative_ids:
            config_path = transition.EVALUATOR_CONFIGS.get(
                evaluator_id, "architecture/acceptance/a1/data_ownership_v1.yaml"
            )
            negative_config_bytes = (repo / config_path).read_bytes()
            config_artifact_path = f"{PROBE_RELATIVE_ROOT}/evaluator-configs/{evaluator_id}.yaml"
            transition._write_new_file(run_root / config_artifact_path, negative_config_bytes)
            evaluator_configs[evaluator_id] = {
                "evaluator_id": evaluator_id,
                "configuration_path": config_path,
                "artifact_path": config_artifact_path,
                "configuration_sha256": sha256_bytes(negative_config_bytes),
            }
            _run, row = _run_bound_evaluator(
                repository=repo,
                source_checkout=probe_dir,
                source_commit=probe_commit,
                architecture_state=AFTER_STATE,
                evaluator_id=evaluator_id,
                output_directory=(
                    run_root / "PSI/evaluator-observations/a05-negative" / evaluator_id
                ),
                configuration_bytes=negative_config_bytes,
                state_manifest_bytes=manifest_bytes,
            )
            negative_rows.append(row)
        for binding in candidate_bindings:
            _candidate_run, candidate_row = _run_bound_evaluator(
                repository=repo,
                source_checkout=probe_dir,
                source_commit=probe_commit,
                architecture_state=AFTER_STATE,
                evaluator_id=binding["evaluator_id"],
                output_directory=(
                    run_root
                    / "PSI/evaluator-observations/candidate-negative"
                    / binding["representation_id"]
                ),
                configuration_bytes=binding["configuration_bytes"],
                state_manifest_bytes=manifest_bytes,
            )
            candidate_row["representation_id"] = binding["representation_id"]
            candidate_negative_rows.append(candidate_row)
        if _git_text(probe_dir, "status", "--porcelain"):
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_WORKTREE_DIRTY")
        probe_manifest = {
            "schema_version": "MONO_CI_PSI_A05_PROBE_MANIFEST_V1",
            "source_provenance": (
                "DETERMINISTIC_LOCAL_PROBE_COMMIT_RECONSTRUCTED_FROM_ARCHIVED_PATCH"
            ),
            "remote_commit_required": False,
            "parent_commit_sha": after_commit,
            "parent_repository_tree_sha": after_tree,
            "parent_application_tree_sha": after_app_tree,
            "probe_commit_sha": probe_commit,
            "probe_repository_tree_sha": probe_tree,
            "probe_application_tree_sha": probe_app_tree,
            "probe_commit_provenance": {
                "availability": "LOCAL_ONLY_RECREATED_FROM_PATCH",
                "author": PROBE_AUTHOR,
                "email": PROBE_EMAIL,
                "commit_date": PROBE_COMMIT_DATE,
                "message": PROBE_COMMIT_MESSAGE,
            },
            "changed_paths": changed_paths,
            "changed_sources": [
                {
                    "path": PROBE_PATH,
                    "artifact_path": f"source-files/{PROBE_PATH}",
                    "original_file_sha256": sha256_bytes(parent_source),
                    "modified_file_sha256": sha256_bytes(modified_source),
                }
            ],
            "patch_path": f"{PROBE_RELATIVE_ROOT}/source.patch",
            "patch_sha256": sha256_bytes(patch_bytes),
            "evaluator_configurations": [
                evaluator_configs[key] for key in sorted(evaluator_configs)
            ],
            "evaluator_evidence_bindings": [
                {
                    key: row[key]
                    for key in (
                        "source_commit_sha",
                        "source_tree_sha",
                        "application_tree_sha",
                        "evaluator_id",
                        "process_exit_code",
                        "execution_status",
                        "compliance",
                        "configuration_sha256",
                        "evaluator_source_sha256",
                        "output_path",
                        "output_sha256",
                        "coverage_path",
                        "coverage_sha256",
                        "stdout_path",
                        "stdout_sha256",
                        "stderr_path",
                        "stderr_sha256",
                    )
                }
                for row in sorted(negative_rows, key=lambda item: item["evaluator_id"])
            ],
        }
        validate_payload("mono_ci_psi_a05_probe_manifest_v1.schema.json", probe_manifest)
        probe_manifest_path = probe_artifact_root / "probe-manifest.json"
        transition._write_new_file(probe_manifest_path, pretty_json_bytes(probe_manifest))
        transition._write_new_file(
            probe_artifact_root / "reproduction.json",
            pretty_json_bytes(
                {
                    "schema_version": "MONO_CI_PSI_A05_PROBE_REPRODUCTION_V1",
                    "command": (
                        "python -m experiments.execution.tooling.mono_ci_psi_a05 replay-probe "
                        "--repository <checkout> --run <verified-run> --output <new-checkout>"
                    ),
                    "expected_parent_commit_sha": after_commit,
                    "expected_parent_repository_tree_sha": after_tree,
                    "expected_parent_application_tree_sha": after_app_tree,
                    "patch_path": "source.patch",
                    "modified_source_path": f"source-files/{PROBE_PATH}",
                    "remote_probe_commit_required": False,
                    "production_database_access": "NOT_USED_SOURCE_LEVEL_STATIC_EVALUATION_ONLY",
                }
            ),
        )
    finally:
        if probe_dir is not None:
            transition._git_worktree(repo, "remove", "--force", str(probe_dir), check=False)
        if temporary is not None:
            temporary.cleanup()

    requirement = {
        "control_id": "architecture.data_ownership.persistence_ownership",
        "requirement_type": "architecture.data_ownership.persistence_ownership",
        "detail_status": "SPECIFIED",
        "value": requirement_value,
        "source_kind": "VERSIONED_ARCHITECTURE_STATE_MANIFEST",
        "source_ref": {
            "path": f"architecture/states/{AFTER_STATE}.yaml",
            "sha256": sha256_bytes(manifest_bytes),
        },
    }
    mapping_spec = _REQUIREMENT_CAPABILITY_MAPPINGS[
        "architecture.data_ownership.persistence_ownership"
    ]
    mapping = {
        "requirement_type": "architecture.data_ownership.persistence_ownership",
        **mapping_spec,
        "status": "VERIFIED_RULE_IMPLEMENTATION",
    }
    old_diagnostic = json.loads(
        (run_root / "diagnostics/adaptation-necessity-assessment.json").read_text(encoding="utf-8")
    )
    old_capabilities: dict[str, dict[str, Any]] = {}
    for assessment in old_diagnostic.get("assessments", []):
        for row in assessment.get("capability_inventory", {}).get("capabilities_after", []):
            old_capabilities[row["capability_type"]] = row
    active_evaluators = ["AC_PUBLIC_API", "AC_MODULE_GRAPH"]
    probe_by_id = {row["evaluator_id"]: row for row in negative_rows}
    detection_diagnostic = _recompute_probe_detection_diagnostic(
        run_root, list(probe_by_id.values()), source_condition_verified=True
    )
    detection_rows = detection_diagnostic["per_evaluator_detection"]
    old_detection = detection_diagnostic["old_baseline_detection"]
    case_interpretation = detection_diagnostic["case_interpretation"]
    before_observations = [
        row
        for row in run_record["evaluator_observations"]
        if row["architecture_state"] == BEFORE_STATE
    ]
    after_observations = [
        row
        for row in run_record["evaluator_observations"]
        if row["architecture_state"] == AFTER_STATE
    ]
    before_coverage = [
        json.loads(
            (
                run_root / transition._coverage_assessment_path(BEFORE_STATE, row["evaluator_id"])
            ).read_text(encoding="utf-8")
        )
        for row in before_observations
    ]
    before_scope_complete = bool(before_coverage) and all(
        row.get("source_inspection_status") == "COMPLETE" for row in before_coverage
    )
    before_compliance = (
        "COMPLIANT"
        if before_observations
        and all(
            row["execution_status"] == "COMPLETED" and row["compliance"] == "COMPLIANT"
            for row in before_observations
        )
        else "NOT_EVALUABLE"
    )
    old_capability_scope_verified = bool(old_capabilities) and all(
        row.get("verification_status") == "VERIFIED_STATIC_SCOPE"
        for row in old_capabilities.values()
    )
    adaptation_assessment = assess_adaptation_necessity(
        {
            "configuration_sha256_before": sha256_bytes(baseline_bytes),
            "configuration_sha256_after": sha256_bytes(baseline_bytes),
            "requirements_after": [requirement],
            "capabilities_after": list(old_capabilities.values()),
            "requirement_capability_mappings": [mapping],
            "unresolved_requirements_after": [],
            "evaluator_identity_verified": bool(positive_row["evaluator_source_sha256"])
            and all(bool(row["evaluator_source_sha256"]) for row in before_observations),
            "architecture_identity_verified": all(
                row["source_commit_sha"] == BEFORE_COMMIT for row in before_observations
            )
            and all(row["source_commit_sha"] == after_commit for row in after_observations)
            and positive_row["source_commit_sha"] == after_commit,
            "configuration_identity_verified": sha256_bytes(baseline_bytes)
            == run_record["baseline"]["configuration_sha256"],
            "source_inspection_before": "COMPLETE" if before_scope_complete else "INCOMPLETE",
            "source_inspection_after": positive_row["inspection_status"],
            "evaluator_compliance_before": before_compliance,
            "evaluator_compliance_after": positive_row["compliance"],
            "rule_scope_match_before": before_scope_complete,
            "rule_scope_match_after": positive_row["inspection_status"] == "COMPLETE",
            "requirement_inventory_status_after": "COMPLETE_FOR_DECLARED_MANIFEST_TYPES",
            "requirement_universe_completeness_after": "UNKNOWN",
            "capability_inventory_status_after": (
                "VERIFIED_FOR_DECLARED_STATIC_SCOPE"
                if old_capability_scope_verified
                else "INCOMPLETE_OR_UNVERIFIED"
            ),
            "architecture_state_after": AFTER_STATE,
            "pair_semantic_validity": "UNKNOWN",
            "normative_applicability": "DECLARED_NOT_APPROVED",
            "baseline_identity": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
            "independent_review": False,
        }
    )
    candidate_verification = _build_candidate_verification(
        candidate_info=candidate_info,
        candidate_bindings=candidate_bindings,
        positive_rows=candidate_positive_rows,
        negative_rows=candidate_negative_rows,
        original_positive_rows=run_record["evaluator_observations"],
        original_negative_rows=negative_rows,
        baseline=baseline,
        run_root=run_root,
    )
    positive = {
        "condition_status": "A0_5_SOURCE",
        "evaluator": positive_row,
    }
    negative = {
        "condition_status": "ISOLATED_TASKS_FOREIGN_NOTIFICATIONS_TABLE_ACCESS",
        "source_commit_sha": probe_commit,
        "changed_paths": changed_paths,
        "evaluators": sorted(negative_rows, key=lambda row: row["evaluator_id"]),
    }
    extension = {
        "schema_version": "MONO_CI_PSI_A05_EXPERIMENT_EVIDENCE_V2",
        "execution_id": run_record["execution_id"],
        "transition": {
            "before_state": BEFORE_STATE,
            "after_state": AFTER_STATE,
            "before_commit_sha": run_record["transition"]["before_commit_sha"],
            "after_commit_sha": after_commit,
            "after_repository_tree_sha": after_tree,
            "after_application_tree_sha": after_app_tree,
            "probe_parent_commit_sha": probe_parent,
            "probe_commit_sha": probe_commit,
            "probe_repository_tree_sha": probe_tree,
            "probe_application_tree_sha": probe_app_tree,
            "probe_changed_paths": changed_paths,
            "probe_manifest_path": f"{PROBE_RELATIVE_ROOT}/probe-manifest.json",
            "probe_manifest_sha256": sha256_file(probe_manifest_path),
            "probe_patch_path": f"{PROBE_RELATIVE_ROOT}/source.patch",
            "probe_patch_sha256": sha256_bytes(patch_bytes),
            "probe_source_path": f"{PROBE_RELATIVE_ROOT}/source-files/{PROBE_PATH}",
            "probe_source_sha256": sha256_bytes(modified_source),
            "probe_commit_provenance": "LOCAL_ONLY_RECREATED_FROM_ARCHIVED_PATCH",
        },
        "baseline": {
            "configuration_id": BASELINE_ID,
            "configuration_sha256": sha256_bytes(baseline_bytes),
            "historical_identity": baseline["historical_identity"],
            "approval_status": "NOT_APPROVED",
            "active_representations": active_evaluators,
            "ownership_representation_active": False,
        },
        "independent_requirement": {
            "requirement_id": requirement["control_id"],
            "requirement_type": requirement["requirement_type"],
            "source_path": requirement["source_ref"]["path"],
            "source_sha256": requirement["source_ref"]["sha256"],
            "source_kind": requirement["source_kind"],
            "authority_status": manifest["authority_status"],
            "value": requirement_value,
            "mapping_id": mapping_spec["mapping_id"],
            "mapping_status": "VERIFIED_RULE_IMPLEMENTATION_NOT_SEMANTIC_APPROVAL",
        },
        "ownership_evaluator": {
            "evaluator_id": OWNERSHIP_EVALUATOR,
            "version": evaluator_version,
            "source_sha256": evaluator_source_sha256,
            "configuration_path": config_relative,
            "configuration_sha256": config_sha256,
            "a04_applicability": "NOT_APPLICABLE",
            "a05_applicability": "ACTIVE",
            "coverage_limits": evaluator_config.get("coverage_limits", []),
        },
        "positive_condition": positive,
        "negative_condition": negative,
        "adequacy_diagnostic": {
            "assessment_status": adaptation_assessment["assessment_status"],
            "missing_post_transition_controls": adaptation_assessment[
                "missing_post_transition_controls"
            ],
            "requirement_capability_comparison": adaptation_assessment[
                "requirement_capability_comparison"
            ],
            "evidence_integrity": "VERIFIED_BY_SOURCE_REPLAY_AND_RAW_EVIDENCE_READBACK",
            "per_evaluator_detection": detection_rows,
            "old_baseline_detection": old_detection,
            "case_interpretation": case_interpretation,
            "known_limitations": list(evaluator_config.get("coverage_limits", []))
            + [
                "The A0.5 requirement is a declared engineering policy, not independently "
                "approved normative authority.",
                "The ownership capability was evaluated prospectively but was not active in "
                "the reconstructed A0.4 baseline.",
                "This static source probe does not establish runtime enforcement or semantic "
                "adequacy beyond the recorded detector scope.",
            ],
        },
        "candidate_verification": candidate_verification,
        "scientific_boundary": {
            "method_decision": run_record["psi"]["decision"],
            "operation_plan": method_result.get("operation_plan", {}).get("operations", []),
            "candidate_status": (
                "MATERIALIZED" if method_result.get("candidate") is not None else "NOT_MATERIALIZED"
            ),
            "study_readiness": run_record["study_readiness"],
            "measurement_status": run_record["measurement_status"],
            "p_algorithm_status": run_record["p_algorithm_status"],
            "g1": run_record["g1"],
            "g4": run_record["g4"],
            "reference_gate": run_record["reference_gate"],
            "scoring": run_record["psi"]["scoring"],
        },
    }
    extension_path = run_root / "diagnostics/a05-experiment-evidence.json"
    extension_bytes = pretty_json_bytes(extension)
    transition._write_new_file(extension_path, extension_bytes)
    validate_payload(
        transition.A05_EXPERIMENT_EVIDENCE_SCHEMA,
        extension,
    )
    return {
        "path": "diagnostics/a05-experiment-evidence.json",
        "sha256": sha256_bytes(extension_bytes),
    }


def _run_bound_evaluator(
    *,
    repository: Path,
    source_checkout: Path,
    source_repository: Path | None = None,
    source_commit: str,
    architecture_state: str,
    evaluator_id: str,
    output_directory: Path,
    configuration_bytes: bytes,
    state_manifest_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    run = run_fresh_evaluator(
        repository=repository,
        source_checkout=source_checkout,
        evaluator_id=evaluator_id,
        architecture_state=architecture_state,
        source_commit_sha=source_commit,
        output_directory=output_directory,
    )
    run_root = output_directory.parents[3]
    output_path = run_root / run["output_path"]
    stdout_path = run_root / run["stdout_path"]
    stderr_path = run_root / run["stderr_path"]
    output_bytes = output_path.read_bytes()
    coverage = verify_inspection_coverage(
        repository=source_repository or repository,
        source_commit_sha=source_commit,
        source_tree_sha=run["source_tree_sha"],
        architecture_state=architecture_state,
        evaluator_id=evaluator_id,
        evaluator_configuration_bytes=configuration_bytes,
        state_manifest_bytes=state_manifest_bytes,
        evaluator_output_bytes=output_bytes,
        evaluator_evidence=run["evidence"],
    )
    coverage_path = output_directory / "inspection-coverage.json"
    transition._write_new_file(coverage_path, pretty_json_bytes(coverage))
    coverage_sha = sha256_file(coverage_path)
    inspection_path = output_directory / "inspection-scope.json"
    transition._write_new_file(
        inspection_path,
        pretty_json_bytes(
            build_inspection_scope_artifact(run["evidence"], sha256_file(output_path), coverage)
        ),
    )
    diagnostics = run["evidence"].get("diagnostics", {})
    finding_codes = sorted(
        {
            item["code"]
            for item in diagnostics.get("policy_findings", [])
            if isinstance(item, dict) and isinstance(item.get("code"), str)
        }
    )
    if not finding_codes:
        finding_codes = sorted(
            {
                item["code"]
                for value in diagnostics.values()
                if isinstance(value, list)
                for item in value
                if isinstance(item, dict) and isinstance(item.get("code"), str)
            }
        )
    evidence = run["evidence"]
    result = evidence.get("result", {})
    row = {
        "source_commit_sha": source_commit,
        "source_tree_sha": run["source_tree_sha"],
        "application_tree_sha": run["target_application_tree_sha"],
        "evaluator_id": evaluator_id,
        "execution_status": result.get("execution_status"),
        "compliance": result.get("compliance"),
        "process_exit_code": run["process_exit_code"],
        "configuration_sha256": run["configuration_sha256"],
        "evaluator_source_sha256": run["evaluator_source_sha256"],
        "output_path": run["output_path"],
        "output_sha256": sha256_file(output_path),
        "stdout_path": run["stdout_path"],
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_path": run["stderr_path"],
        "stderr_sha256": sha256_file(stderr_path),
        "coverage_path": coverage_path.relative_to(run_root).as_posix(),
        "coverage_sha256": coverage_sha,
        "inspection_status": coverage["source_inspection_status"],
        "finding_codes": finding_codes,
        "duration_ms": run["duration_ms"],
    }
    return run, row


def _raw_findings(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = evidence.get("diagnostics", {})
    result = evidence.get("result", {})
    if not isinstance(diagnostics, dict) or not isinstance(result, dict):
        return []
    candidates = [
        result.get("violations"),
        diagnostics.get("observed_policy_findings"),
        diagnostics.get("policy_findings"),
    ]
    findings: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, list):
            continue
        for item in candidate:
            if isinstance(item, dict) and isinstance(item.get("code"), str):
                findings[json.dumps(item, sort_keys=True)] = item
    return [findings[key] for key in sorted(findings)]


def _added_probe_lines(patch_bytes: bytes) -> set[int]:
    """Return new-file line numbers introduced by the single-file probe patch."""
    try:
        patch_text = patch_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("PROBE_PATCH_ENCODING_INVALID") from error
    if _probe_patch_paths(patch_bytes) != [PROBE_PATH]:
        raise ValueError("PROBE_PATCH_PATH_MISMATCH")

    added_lines: set[int] = set()
    new_line: int | None = None
    saw_hunk = False
    for line in patch_text.splitlines():
        if line.startswith("@@"):
            match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if match is None:
                raise ValueError("PROBE_PATCH_HUNK_INVALID")
            new_line = int(match.group(1))
            saw_hunk = True
            continue
        if new_line is None:
            continue
        if line.startswith("+"):
            added_lines.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            continue
        elif line.startswith(" "):
            new_line += 1
        elif line.startswith("\\"):
            continue
        else:
            raise ValueError("PROBE_PATCH_LINE_INVALID")
    if not saw_hunk or not added_lines:
        raise ValueError("PROBE_PATCH_HAS_NO_ADDED_SOURCE_LINES")
    return added_lines


def _probe_change_context(run_root: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    """Load the digest-bound source path and added lines used for attribution."""
    try:
        root = run_root.resolve(strict=True)
        manifest_path = root / PROBE_RELATIVE_ROOT / "probe-manifest.json"
        if (
            manifest_path.is_symlink()
            or not manifest_path.is_file()
            or not manifest_path.resolve().is_relative_to(root)
        ):
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return None
        changed_sources = manifest.get("changed_sources")
        if (
            manifest.get("schema_version") != "MONO_CI_PSI_A05_PROBE_MANIFEST_V1"
            or manifest.get("changed_paths") != [PROBE_PATH]
            or not isinstance(changed_sources, list)
            or len(changed_sources) != 1
            or not isinstance(changed_sources[0], dict)
        ):
            return None
        source = changed_sources[0]
        if (
            source.get("path") != PROBE_PATH
            or source.get("artifact_path") != f"source-files/{PROBE_PATH}"
            or manifest.get("patch_path") != f"{PROBE_RELATIVE_ROOT}/source.patch"
            or manifest.get("probe_commit_sha") != row.get("source_commit_sha")
            or manifest.get("probe_repository_tree_sha") != row.get("source_tree_sha")
            or manifest.get("probe_application_tree_sha") != row.get("application_tree_sha")
        ):
            return None

        source_path = root / PROBE_RELATIVE_ROOT / source["artifact_path"]
        patch_path = root / manifest["patch_path"]
        for artifact_path in (source_path, patch_path):
            if (
                artifact_path.is_symlink()
                or not artifact_path.is_file()
                or not artifact_path.resolve().is_relative_to(root)
            ):
                return None
        source_bytes = source_path.read_bytes()
        patch_bytes = patch_path.read_bytes()
        if sha256_bytes(source_bytes) != source.get("modified_file_sha256") or sha256_bytes(
            patch_bytes
        ) != manifest.get("patch_sha256"):
            return None
        added_lines = _added_probe_lines(patch_bytes)
        source_parts = Path(PROBE_PATH).with_suffix("").parts
        if len(source_parts) < 4 or source_parts[:2] != ("app", "modules"):
            return None
        source_capability = source_parts[2]
        source_module = ".".join(source_parts)
        return {
            "path": PROBE_PATH,
            "added_lines": added_lines,
            "source_capability": source_capability,
            "source_module": source_module,
        }
    except (OSError, ValueError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _finding_location_is_probe_change(finding: dict[str, Any], change: dict[str, Any]) -> bool:
    line = finding.get("line")
    return (
        finding.get("source_path") == change["path"]
        and isinstance(line, int)
        and not isinstance(line, bool)
        and line in change["added_lines"]
        and finding.get("source_capability") == change["source_capability"]
    )


def _finding_is_attributable(
    evaluator_id: str, finding: dict[str, Any], evidence: dict[str, Any], change: dict[str, Any]
) -> bool:
    diagnostics = evidence.get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        return False

    if evaluator_id == "AC_PUBLIC_API" and finding.get("code") == "CROSS_MODULE_IMPORT_NOT_PUBLIC":
        target_capability = finding.get("target_capability")
        target_module = finding.get("imported_module")
        if (
            not _finding_location_is_probe_change(finding, change)
            or not isinstance(target_capability, str)
            or target_capability == change["source_capability"]
            or not isinstance(target_module, str)
            or not (
                target_module == f"app.modules.{target_capability}"
                or target_module.startswith(f"app.modules.{target_capability}.")
            )
        ):
            return False
        imports = diagnostics.get("cross_capability_imports", [])
        return isinstance(imports, list) and any(
            isinstance(item, dict)
            and item.get("source_path") == change["path"]
            and item.get("line") == finding.get("line")
            and item.get("source_module") == change["source_module"]
            and item.get("target_module") == target_module
            and item.get("target_capability") == target_capability
            and item.get("imported_name") == finding.get("imported_name")
            and item.get("classification") == "private_or_undeclared_contract"
            for item in imports
        )

    if evaluator_id == "AC_MODULE_GRAPH" and finding.get("code") in {
        "FORBIDDEN_DEPENDENCY",
        "UNDECLARED_DEPENDENCY",
    }:
        source_capability = finding.get("source_capability")
        target_capability = finding.get("target_capability")
        if (
            source_capability != change["source_capability"]
            or not isinstance(target_capability, str)
            or target_capability == source_capability
        ):
            return False
        pair = {"from": source_capability, "to": target_capability}
        forbidden = diagnostics.get("forbidden_edges", [])
        allowed = diagnostics.get("allowed_edges", [])
        if finding["code"] == "FORBIDDEN_DEPENDENCY":
            if not isinstance(forbidden, list) or pair not in forbidden:
                return False
        elif (
            not isinstance(allowed, list)
            or pair in allowed
            or (isinstance(forbidden, list) and pair in forbidden)
        ):
            return False
        edges = diagnostics.get("edges", [])
        return isinstance(edges, list) and any(
            isinstance(edge, dict)
            and edge.get("from") == source_capability
            and edge.get("to") == target_capability
            and isinstance(edge.get("references"), list)
            and any(
                isinstance(reference, dict)
                and reference.get("source_path") == change["path"]
                and reference.get("line") in change["added_lines"]
                and reference.get("source_module") == change["source_module"]
                and isinstance(reference.get("target_module"), str)
                and (
                    reference["target_module"] == f"app.modules.{target_capability}"
                    or reference["target_module"].startswith(f"app.modules.{target_capability}.")
                )
                for reference in edge["references"]
            )
            for edge in edges
        )

    if evaluator_id == OWNERSHIP_EVALUATOR and finding.get("code") == "FOREIGN_TABLE_ACCESS":
        if not _finding_location_is_probe_change(finding, change):
            return False
        accesses = diagnostics.get("foreign_table_accesses", [])
        table_owners = diagnostics.get("table_owners", {})
        return (
            isinstance(accesses, list)
            and isinstance(table_owners, dict)
            and any(
                isinstance(access, dict)
                and access.get("source_path") == change["path"]
                and access.get("line") == finding.get("line")
                and isinstance(access.get("table"), str)
                and access.get("owner") == table_owners.get(access.get("table"))
                and access.get("owner") == finding.get("target_capability")
                and access.get("owner") != change["source_capability"]
                for access in accesses
            )
        )
    return False


def _classify_probe_detection(
    run_root: Path, row: dict[str, Any], *, source_condition_verified: bool = False
) -> dict[str, Any]:
    """Attribute evaluator findings only when they bind to the digest-verified probe delta."""
    try:
        output_path = run_root / row["output_path"]
        coverage_path = run_root / row["coverage_path"]
        if (
            output_path.is_symlink()
            or coverage_path.is_symlink()
            or not output_path.is_file()
            or not coverage_path.is_file()
            or sha256_file(output_path) != row["output_sha256"]
            or sha256_file(coverage_path) != row["coverage_sha256"]
        ):
            raise ValueError("RAW_EVIDENCE_MISSING_OR_MISMATCHED")
        evidence = json.loads(output_path.read_text(encoding="utf-8"))
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        if not isinstance(evidence, dict) or not isinstance(coverage, dict):
            raise ValueError("RAW_EVIDENCE_SHAPE_INVALID")
    except (OSError, ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return {
            "evaluator_id": row.get("evaluator_id"),
            "detection_status": "NOT_EVALUABLE",
            "reason_codes": ["RAW_EVIDENCE_UNVERIFIED"],
        }

    result = evidence.get("result", {})
    compliance = result.get("compliance")
    expected_exit = (
        2
        if result.get("execution_status") == "FAILED"
        else {
            "COMPLIANT": 0,
            "NON_COMPLIANT": 1,
            "NOT_EVALUABLE": 2,
            "UNKNOWN": 2,
            "NOT_APPLICABLE": 3,
        }.get(compliance)
    )
    identities_valid = (
        evidence.get("evaluator", {}).get("id") == row.get("evaluator_id")
        and evidence.get("evaluator", {}).get("configuration_digest")
        == row.get("configuration_sha256")
        and evidence.get("evaluator", {}).get("source_digest") == row.get("evaluator_source_sha256")
        and evidence.get("architecture", {}).get("target_source_sha")
        == row.get("source_commit_sha")
        and row.get("execution_status") == result.get("execution_status")
        and row.get("compliance") == compliance
        and row.get("process_exit_code") == expected_exit
        and row.get("inspection_status") == coverage.get("source_inspection_status")
    )
    if (
        not source_condition_verified
        or not identities_valid
        or result.get("execution_status") != "COMPLETED"
        or coverage.get("source_inspection_status") != "COMPLETE"
        or evidence.get("architecture", {}).get("source_sha_status") != "MATCHED"
        or evidence.get("architecture", {}).get("manifest_state_status") != "MATCHED"
    ):
        status = "NOT_EVALUABLE"
        reasons = ["EXECUTION_IDENTITY_OR_SCOPE_UNRESOLVED"]
    else:
        change = _probe_change_context(run_root, row)
        findings = _raw_findings(evidence)
        if change is None:
            status = "NOT_EVALUABLE"
            reasons = ["PROBE_SOURCE_EVIDENCE_UNVERIFIED"]
        else:
            attributable = [
                finding
                for finding in findings
                if _finding_is_attributable(row["evaluator_id"], finding, evidence, change)
            ]
            if attributable and compliance == "NON_COMPLIANT":
                status = "DETECTED"
                reasons = sorted(
                    {
                        "ATTRIBUTABLE_FOREIGN_TABLE_ACCESS_FINDING"
                        if finding["code"] == "FOREIGN_TABLE_ACCESS"
                        else f"ATTRIBUTABLE_{finding['code']}_FINDING"
                        for finding in attributable
                    }
                )
            elif compliance == "COMPLIANT" and not findings:
                status = "NOT_DETECTED"
                reasons = ["COMPLETE_SCOPE_WITHOUT_ATTRIBUTABLE_FINDING"]
            else:
                status = "NOT_EVALUABLE"
                reasons = ["RESULT_DOES_NOT_ESTABLISH_ATTRIBUTION"]
    return {
        "evaluator_id": row["evaluator_id"],
        "detection_status": status,
        "reason_codes": reasons,
    }


def _recompute_probe_detection_diagnostic(
    run_root: Path, rows: list[dict[str, Any]], *, source_condition_verified: bool
) -> dict[str, Any]:
    classifications = [
        _classify_probe_detection(
            run_root, row, source_condition_verified=source_condition_verified
        )
        for row in sorted(rows, key=lambda item: item["evaluator_id"])
    ]
    by_id = {row["evaluator_id"]: row["detection_status"] for row in classifications}
    old_detection = _combine_old_detection(by_id["AC_PUBLIC_API"], by_id["AC_MODULE_GRAPH"])
    return {
        "per_evaluator_detection": classifications,
        "old_baseline_detection": old_detection,
        "case_interpretation": _probe_case_interpretation(
            old_detection, by_id[OWNERSHIP_EVALUATOR]
        ),
    }


def _verify_probe_detection_diagnostic(
    run_root: Path,
    rows: list[dict[str, Any]],
    diagnostic: dict[str, Any],
    *,
    source_condition_verified: bool,
) -> dict[str, Any]:
    recomputed = _recompute_probe_detection_diagnostic(
        run_root, rows, source_condition_verified=source_condition_verified
    )
    if any(diagnostic.get(key) != recomputed[key] for key in recomputed):
        raise ContractValidationError("MONO_CI_PSI_A05_DERIVED_DIAGNOSTIC_MISMATCH")
    return recomputed


def _combine_old_detection(public_api: str, module_graph: str) -> str:
    outcomes = {public_api, module_graph}
    if "DETECTED" in outcomes:
        return "DETECTED"
    if outcomes == {"NOT_DETECTED"}:
        return "NOT_DETECTED"
    return "NOT_EVALUABLE"


def _probe_case_interpretation(old_detection: str, ownership_detection: str) -> str:
    if old_detection == "DETECTED":
        return "NO_OLD_BASELINE_GAP_DEMONSTRATED"
    if old_detection == "NOT_EVALUABLE" or ownership_detection == "NOT_EVALUABLE":
        return "NOT_EVALUABLE"
    if ownership_detection == "DETECTED":
        return "OLD_BASELINE_GAP_SUPPORTED"
    return "PROBE_NOT_VALIDATED_BY_ANY_CONTROL"


def _observation_outcome(run_root: Path, row: dict[str, Any]) -> dict[str, Any]:
    evidence = json.loads((run_root / row["output_path"]).read_text(encoding="utf-8"))
    diagnostics = evidence.get("diagnostics", {})
    codes = sorted(
        {
            item["code"]
            for item in diagnostics.get("policy_findings", [])
            if isinstance(item, dict) and isinstance(item.get("code"), str)
        }
    )
    if not codes:
        codes = sorted(
            {
                item["code"]
                for value in diagnostics.values()
                if isinstance(value, list)
                for item in value
                if isinstance(item, dict) and isinstance(item.get("code"), str)
            }
        )
    return {
        "evaluator_id": row["evaluator_id"],
        "execution_status": evidence.get("result", {}).get("execution_status"),
        "compliance": evidence.get("result", {}).get("compliance"),
        "finding_codes": codes,
    }


def _build_candidate_verification(
    *,
    candidate_info: dict[str, Any] | None,
    candidate_bindings: list[dict[str, Any]],
    positive_rows: list[dict[str, Any]],
    negative_rows: list[dict[str, Any]],
    original_positive_rows: list[dict[str, Any]],
    original_negative_rows: list[dict[str, Any]],
    baseline: dict[str, Any],
    run_root: Path,
) -> dict[str, Any]:
    if candidate_info is None:
        return {
            "status": "NOT_EXECUTED",
            "candidate_present": False,
            "reason": "Method Ψ did not materialize a candidate configuration.",
        }

    by_positive = {row["representation_id"]: row for row in positive_rows}
    by_negative = {row["representation_id"]: row for row in negative_rows}
    baseline_representations = {
        row["representation_id"]: row for row in baseline["representations"]
    }
    candidate_representation_ids = sorted(
        binding["representation_id"] for binding in candidate_bindings
    )
    baseline_representation_ids = sorted(baseline_representations)
    added = sorted(set(candidate_representation_ids) - set(baseline_representation_ids))
    removed = sorted(set(baseline_representation_ids) - set(candidate_representation_ids))
    changed = sorted(
        representation_id
        for representation_id in set(candidate_representation_ids)
        & set(baseline_representation_ids)
        if (
            next(
                binding
                for binding in candidate_bindings
                if binding["representation_id"] == representation_id
            )["evaluator_id"]
            != baseline_representations[representation_id]["evaluator_id"]
            or next(
                binding
                for binding in candidate_bindings
                if binding["representation_id"] == representation_id
            )["configuration_sha256"]
            != baseline_representations[representation_id]["evaluator_configuration_sha256"]
        )
    )
    baseline_positive_by_id = {
        row["evaluator_id"]: row
        for row in original_positive_rows
        if row["architecture_state"] == AFTER_STATE
    }
    baseline_negative_by_id = {row["evaluator_id"]: row for row in original_negative_rows}
    outcome_comparisons = []
    for binding in candidate_bindings:
        representation_id = binding["representation_id"]
        candidate_positive = by_positive[representation_id]
        candidate_negative = by_negative[representation_id]
        baseline_representation = baseline_representations.get(representation_id)
        baseline_binding_matches = bool(
            baseline_representation is not None
            and baseline_representation["evaluator_id"] == binding["evaluator_id"]
            and baseline_representation["evaluator_configuration_sha256"]
            == binding["configuration_sha256"]
            and baseline_representation["evaluator_source_sha256"]
            == binding["evaluator_source_sha256"]
        )
        original_positive = baseline_positive_by_id.get(binding["evaluator_id"])
        original_negative = baseline_negative_by_id.get(binding["evaluator_id"])
        positive_outcome = _observation_outcome(run_root, candidate_positive)
        negative_outcome = _observation_outcome(run_root, candidate_negative)
        positive_reference = (
            _observation_outcome(run_root, original_positive)
            if baseline_binding_matches and original_positive is not None
            else None
        )
        negative_reference = (
            _observation_outcome(run_root, original_negative)
            if baseline_binding_matches and original_negative is not None
            else None
        )
        outcome_comparisons.append(
            {
                "representation_id": representation_id,
                "baseline_binding_matches": baseline_binding_matches,
                "candidate_positive_outcome": positive_outcome,
                "reconstructed_b0_positive_outcome": positive_reference,
                "positive_outcome_parity": (
                    positive_outcome == positive_reference
                    if positive_reference is not None
                    else None
                ),
                "candidate_negative_outcome": negative_outcome,
                "reconstructed_b0_negative_outcome": negative_reference,
                "negative_outcome_parity": (
                    negative_outcome == negative_reference
                    if negative_reference is not None
                    else None
                ),
            }
        )

    all_candidate_rows = [*positive_rows, *negative_rows]
    runs_complete = bool(candidate_bindings) and all(
        row["execution_status"] == "COMPLETED" and row["inspection_status"] == "COMPLETE"
        for row in all_candidate_rows
    )
    positive_controls_compliant = all(
        _observation_outcome(run_root, row)["compliance"] == "COMPLIANT" for row in positive_rows
    )
    comparable = [row for row in outcome_comparisons if row["baseline_binding_matches"]]
    parity = all(
        row["positive_outcome_parity"] is True and row["negative_outcome_parity"] is True
        for row in comparable
    )
    changed_control_set = bool(added or removed or changed)
    uncovered_ids = _candidate_obligation_coverage(
        candidate_info["representation_rows"], "AC_DATA_OWNERSHIP"
    )
    positive_cost = round(sum(float(row["duration_ms"]) for row in positive_rows), 3)
    negative_cost = round(sum(float(row["duration_ms"]) for row in negative_rows), 3)
    added_cost = round(
        sum(
            float(row["duration_ms"])
            for binding, row in zip(candidate_bindings, positive_rows, strict=True)
            if binding["representation_id"] in added
        ),
        3,
    )
    status = (
        "PASS"
        if candidate_info["validation_status"] == "valid"
        and runs_complete
        and positive_controls_compliant
        and parity
        else "FAIL"
    )
    return {
        "status": status,
        "candidate_present": True,
        "reason": "The exact Method Ψ candidate passed source/configuration readback and its "
        "active controls were independently executed on both source conditions."
        if status == "PASS"
        else (
            "Candidate validation, independent execution, or reconstructed-baseline parity failed."
        ),
        "candidate_configuration_sha256": candidate_info["candidate_sha256"],
        "materialized_candidate_path": candidate_info["path"],
        "materialized_candidate_file_sha256": candidate_info["file_sha256"],
        "configuration_version": candidate_info["configuration_version"],
        "method_candidate_validation_status": candidate_info["validation_status"],
        "active_representations": candidate_info["active_representations"],
        "target_obligation": {
            "obligation_id": "AC_DATA_OWNERSHIP",
            "coverage_status": "COVERED" if uncovered_ids else "NOT_COVERED",
            "representation_ids": uncovered_ids,
            "adequacy_status": (
                "NOT_ESTABLISHED_BY_STATIC_EXECUTION" if uncovered_ids else "NOT_COVERED"
            ),
        },
        "positive_evaluations": positive_rows,
        "negative_evaluations": negative_rows,
        "outcome_comparisons": outcome_comparisons,
        "reconstructed_b0_comparison": {
            "baseline_identity": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
            "baseline_active_representation_ids": baseline_representation_ids,
            "candidate_active_representation_ids": candidate_representation_ids,
            "added_representation_ids": added,
            "removed_representation_ids": removed,
            "changed_representation_ids": changed,
            "active_control_set_unchanged": not changed_control_set,
            "matching_control_outcomes_equal": parity,
        },
        "execution_cost": {
            "measurement": "single-run evaluator subprocess wall-clock samples",
            "candidate_positive_total_ms": positive_cost,
            "candidate_negative_total_ms": negative_cost,
            "candidate_validation_total_ms": round(positive_cost + negative_cost, 3),
            "additional_active_representations_per_ci_build": len(added),
            "estimated_additional_ci_execution_ms_per_build": added_cost,
            "estimate_scope": (
                "New candidate controls only; one positive-source execution per build. "
                "Single-run samples are not a performance benchmark."
            ),
        },
    }


def _git_run(repository: Path, *args: str) -> None:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv only
        [git_binary, "-C", str(repository), *args],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
    )
    if result.returncode:
        raise ProtocolError("MONO_CI_PSI_A05_PROBE_GIT_COMMAND_FAILED")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "replay-probe":
        replay_parser = argparse.ArgumentParser(
            description="Reconstruct an archived ΔA5 probe source."
        )
        replay_parser.add_argument("--repository", type=Path, required=True)
        replay_parser.add_argument("--run", type=Path, required=True)
        replay_parser.add_argument("--output", type=Path, required=True)
        replay_args = replay_parser.parse_args(arguments[1:])
        try:
            record = transition.verify_transition_run(
                replay_args.run, repository=replay_args.repository
            )
            extension_path = replay_args.run / record["a05_extension"]["path"]
            extension = json.loads(extension_path.read_text(encoding="utf-8"))
            binding = extension["transition"]
            with replay_negative_probe(
                replay_args.repository,
                replay_args.run / PROBE_RELATIVE_ROOT,
                expected_parent_commit=binding["after_commit_sha"],
                expected_parent_tree=binding["after_repository_tree_sha"],
                expected_parent_application_tree=binding["after_application_tree_sha"],
                output=replay_args.output,
            ) as (checkout, probe_manifest):
                print(
                    json.dumps(
                        {
                            "verification_status": "PASS",
                            "source_checkout": str(checkout),
                            "probe_commit_sha": probe_manifest["probe_commit_sha"],
                            "probe_repository_tree_sha": probe_manifest[
                                "probe_repository_tree_sha"
                            ],
                            "probe_application_tree_sha": probe_manifest[
                                "probe_application_tree_sha"
                            ],
                            "remote_probe_commit_required": False,
                        },
                        sort_keys=True,
                        indent=2,
                    )
                )
            return 0
        except (ContractValidationError, ProtocolError, OSError, json.JSONDecodeError) as error:
            print(json.dumps({"verification_status": "FAIL", "error": str(error)}, sort_keys=True))
            return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    args = parser.parse_args(arguments)
    try:
        result = run_a05_transition(args.repository, args.output, args.execution_id)
    except (ContractValidationError, ProtocolError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
