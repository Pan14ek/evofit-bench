"""Execute the bounded PILOT-02 A0.1 profile and existing Method P pipeline."""

from __future__ import annotations

import argparse
import base64
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess  # nosec B404 - fixed Git/evaluator argv, no shell
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import bundle_sha256, pretty_json_bytes, sha256_bytes
from experiments.execution.tooling.p_adaptation import (
    PILOT02_PROFILE_DEFINITION_PATH,
    PILOT02_PROFILE_DEFINITION_SHA256,
    run_adaptation,
    verify_v3_p_bundle,
)
from experiments.execution.tooling.p_applicability import EvidenceLedger
from experiments.execution.tooling.p_policy_source_v3 import (
    export_method_inputs_v3,
    package_policy_source_v3,
    verify_method_bundle_v3,
)
from experiments.execution.tooling.p_semantic import assess_pair
from scripts import exp02_fitness_evidence as exp02
from scripts.exp01_evidence_contract import BUNDLE_FILENAME, _safe_relative_path, validate_bundle
from scripts.exp03_method_bridge import _adaptation_trace

ROOT = Path(__file__).resolve().parents[2]
POLICY_SOURCE = ROOT / "experiments/execution/policy-pilot/v1/source"
FROZEN_A0_SHA = "b78b0967be937634b7762baccf5ac6892b279a73"
PILOT02_SOURCE_BASE_SHA = "3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306"
FROZEN_B0_CONFIG_SHA256 = "5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb"
FROZEN_B0_EVALUATOR = "fitness/evaluators/a0/importlinter.toml"
FROZEN_B0_EVALUATOR_SHA256 = "88ff64a4792c6048a6ab0686ddf9326ebbee49f76996933845a6142cc1a2ba27"
IMPORT_LINTER_ENTRYPOINT = "import importlinter.cli as c; c.lint_imports_command()"
GIT_EXECUTABLE = shutil.which("git")


def _git(*arguments: str) -> str:
    """Run a fixed, read-only Git query against the selected repository."""
    if GIT_EXECUTABLE is None:
        raise RuntimeError("git executable is unavailable")
    result = subprocess.run(  # noqa: S603 - fixed read-only Git query
        [GIT_EXECUTABLE, *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip()


def _read_exp02_artifact(run_dir: Path, reference: dict[str, Any]) -> bytes:
    """Read and recheck one artifact from an already validated EXP-02 bundle."""
    relative = _safe_relative_path(str(reference["path"]))
    root = run_dir.resolve(strict=True)
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError(f"unsafe EXP-02 artifact: {reference['path']}")
    content = path.read_bytes()
    if len(content) != reference["size_bytes"] or sha256_bytes(content) != reference["sha256"]:
        raise ValueError(f"EXP-02 artifact digest mismatch: {reference['path']}")
    return content


def _source_blob(revision: str, path: str) -> bytes:
    """Read one exact tracked blob from a validated clean source revision."""
    if GIT_EXECUTABLE is None:
        raise RuntimeError("git executable is unavailable")
    result = subprocess.run(  # noqa: S603 - exact source blob from pinned revision
        [GIT_EXECUTABLE, "show", f"{revision}:{path}"],  # nosec S603 - fixed Git subcommand
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=15,
    )
    return result.stdout


def _embedded_artifacts(profile: dict[str, Any], source_revision: str) -> None:
    """Pin every profile definition, source, configuration and evaluator byte."""
    references: dict[str, str] = {
        PILOT02_PROFILE_DEFINITION_PATH: PILOT02_PROFILE_DEFINITION_SHA256,
        str(profile["fitness_configuration_artifact"]["path"]): str(
            profile["fitness_configuration_artifact"]["sha256"]
        ),
        str(profile["obligation_catalog_artifact"]["path"]): str(
            profile["obligation_catalog_artifact"]["sha256"]
        ),
    }
    for mapping in profile["mappings"]:
        for item in [
            mapping["configuration_artifact"],
            *mapping["evaluator_source_artifacts"],
            mapping["candidate_template"]["representation"]["evaluator_artifact"],
        ]:
            path, digest = str(item["path"]), str(item["sha256"])
            previous = references.get(path)
            if previous is not None and previous != digest:
                raise ProtocolError("PILOT02_PROFILE_ARTIFACT_CONFLICT")
            references[path] = digest

    embedded: list[dict[str, Any]] = []
    for path, expected_digest in sorted(references.items()):
        content = _source_blob(source_revision, path)
        if sha256_bytes(content) != expected_digest:
            raise ProtocolError(f"PILOT02_SOURCE_ARTIFACT_MISMATCH:{path}")
        embedded.append(
            {
                "path": path,
                "size_bytes": len(content),
                "sha256": expected_digest,
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        )
    profile["profile_definition_artifact"] = {
        "path": PILOT02_PROFILE_DEFINITION_PATH,
        "sha256": PILOT02_PROFILE_DEFINITION_SHA256,
    }
    profile["embedded_evaluator_artifacts"] = embedded


def _install_profile(bundle_dir: Path, profile: dict[str, Any]) -> dict[str, Any]:
    """Attach the versioned profile to the existing V3 capabilities file and reseal."""
    manifest_path = bundle_dir / "method_input_v3.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    capabilities_path = bundle_dir / "fitness/evaluator-capabilities.json"
    capabilities = json.loads(capabilities_path.read_text(encoding="utf-8"))
    capabilities["generic_candidate_templates"] = [
        mapping["candidate_template"] for mapping in profile["mappings"]
    ]
    capabilities["pilot02_method_input_profile"] = profile
    capabilities_bytes = pretty_json_bytes(capabilities)
    capabilities_path.write_bytes(capabilities_bytes)
    record = next(
        item for item in manifest["files"] if item["path"] == "fitness/evaluator-capabilities.json"
    )
    record["size_bytes"] = len(capabilities_bytes)
    record["sha256"] = sha256_bytes(capabilities_bytes)
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    manifest_path.write_bytes(pretty_json_bytes(manifest))
    verify_method_bundle_v3(bundle_dir, expected_method_id="P")
    return manifest


def _copy_pair_evidence(
    *,
    run_dir: Path,
    record: dict[str, Any],
    destination: Path,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Preserve actual EXP-02 raw output bytes for one separately assessed pair."""
    references = record.get("raw_output_artifacts", [])
    if not isinstance(references, list) or not references:
        raise ValueError(f"EXP-02 raw output is absent for {record.get('record_id')}")
    raw_dir = destination / "raw" / "exp02"
    raw_dir.mkdir(parents=True, exist_ok=True)
    evidence_refs: list[dict[str, str]] = []
    artifact_bytes: dict[str, bytes] = {}
    stdout_digest: str | None = None
    stderr_digest: str | None = None
    for index, reference in enumerate(references):
        if not isinstance(reference, dict):
            raise ValueError("invalid EXP-02 raw output reference")
        content = _read_exp02_artifact(run_dir, reference)
        suffix = "stdout" if "stdout" in str(reference["path"]).lower() else "stderr"
        relative = f"raw/exp02/{record['record_id']}-{index}-{suffix}.txt"
        output_path = destination / relative
        output_path.write_bytes(content)
        digest = sha256_bytes(content)
        evidence_refs.append({"path": relative, "sha256": digest})
        artifact_bytes[relative] = content
        if suffix == "stdout":
            stdout_digest = digest
        else:
            stderr_digest = digest
    if stdout_digest is None or stderr_digest is None:
        raise ValueError(f"stdout/stderr pair is incomplete for {record['record_id']}")
    return {
        "evidence_artifacts": evidence_refs,
        "stdout_sha256": stdout_digest,
        "stderr_sha256": stderr_digest,
    }, artifact_bytes


def _assess_profile_pairs(
    *,
    profile: dict[str, Any],
    exp02_run_dir: Path,
    exp02_bundle: dict[str, Any],
    exp02_evidence: dict[str, Any],
    p_bundle: Any,
    output_dir: Path,
) -> list[dict[str, Any]]:
    """Use authentic validated runs in the existing exact-pair assessment function."""
    source_revision = str(exp02_evidence["source_revision"])
    records = {str(row["record_id"]): row for row in exp02_bundle["records"]}
    observations = {str(row["representation_id"]): row for row in exp02_evidence["representations"]}
    obligations = {str(row["id"]): row for row in p_bundle.obligations}
    embedded_bytes = dict(p_bundle.artifact_bytes)
    assessments: list[dict[str, Any]] = []
    for mapping in profile["mappings"]:
        source_id = str(mapping["source_representation_id"])
        observation = observations[source_id]
        record_id = str(observation["evaluator_execution"]["record_id"])
        record = records[record_id]
        raw_evidence, raw_bytes = _copy_pair_evidence(
            run_dir=exp02_run_dir,
            record=record,
            destination=output_dir,
        )
        pair_evidence = {
            "schema_version": 1,
            "representation_id": source_id,
            "architecture_source_sha": source_revision,
            "evaluator_id": str(mapping["source_evaluator_id"]),
            "infrastructure_status": "completed"
            if isinstance(record.get("exit_status"), int)
            else "infrastructure_failure",
            "process_exit_code": record.get("exit_status"),
            "configured_targets": [],
            "resolved_targets": [],
            "inspected_subjects": [],
            "missing_targets": [],
            "inspected_edge_count": None,
            "stage_applicable": True,
            "semantic_compatible": None,
            "mapping_resolved": True,
            "evidence_contract_satisfied": True,
            "adequacy_proven": False,
            "evidence_artifacts": raw_evidence["evidence_artifacts"],
            "stdout_sha256": raw_evidence["stdout_sha256"],
            "stderr_sha256": raw_evidence["stderr_sha256"],
            "failure_reason_code": None,
        }
        all_bytes = embedded_bytes | raw_bytes
        assessment = assess_pair(
            representation=mapping["candidate_template"]["representation"],
            obligation=obligations[str(mapping["obligation_id"])],
            architecture_source_sha=source_revision,
            evaluator_evidence=pair_evidence,
            semantic_proof=None,
            artifact_bytes=all_bytes,
            source_digests=p_bundle.source_digests,
        )
        assessments.append(
            {
                "assessment": assessment.to_dict(),
                "source_representation_id": source_id,
                "source_evaluator_record_id": record_id,
                "source_lifecycle_stage": observation["lifecycle_stage"],
                "method_lifecycle_stage": mapping["candidate_template"]["representation"]["stage"],
                "source_scope_id": mapping["source_scope_id"],
                "metric": mapping["metric"],
                "observed_execution_verdict": record["execution_verdict"],
                "observed_exit_status": record["exit_status"],
                "observed_metric": observation["metrics"],
                "assessment_role": "post-run exact-pair diagnostic; not supplied to P adaptation",
                "semantic_adequacy": "pending_independent_assessment",
            }
        )
    return assessments


def _run_b0_evaluator(output_dir: Path) -> dict[str, Any]:
    """Run the unchanged frozen A0 Import Linter artifact against this source."""
    config_path = ROOT / FROZEN_B0_EVALUATOR
    config_bytes = config_path.read_bytes()
    frozen_bytes = _source_blob(PILOT02_SOURCE_BASE_SHA, FROZEN_B0_EVALUATOR)
    if (
        sha256_bytes(frozen_bytes) != sha256_bytes(config_bytes)
        or sha256_bytes(frozen_bytes) != FROZEN_B0_EVALUATOR_SHA256
    ):
        raise ProtocolError("PILOT02_FROZEN_B0_EVALUATOR_MISMATCH")
    if sha256_bytes(_source_blob(FROZEN_A0_SHA, "fitness/configs/a0-monolith.yaml")) != (
        FROZEN_B0_CONFIG_SHA256
    ):
        raise ProtocolError("PILOT02_FROZEN_B0_CONFIGURATION_MISMATCH")
    command = [
        sys.executable,
        "-c",
        IMPORT_LINTER_ENTRYPOINT,
        "--config",
        str(config_path),
        "--no-cache",
        "--no-logo",
    ]
    started_ns = time.perf_counter_ns()
    completed = subprocess.run(  # noqa: S603 - fixed evaluator command and configuration path
        command,
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=120,
    )
    duration_ns = time.perf_counter_ns() - started_ns
    stdout_path = output_dir / "raw" / "b0-evaluator.stdout.txt"
    stderr_path = output_dir / "raw" / "b0-evaluator.stderr.txt"
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    output = completed.stdout.decode("utf-8", errors="replace")
    match = re.search(r"(\d+) broken", output, re.IGNORECASE)
    return {
        "status": "completed" if match or completed.returncode == 0 else "inconclusive",
        "configuration_path": FROZEN_B0_EVALUATOR,
        "configuration_sha256": sha256_bytes(config_bytes),
        "command": command,
        "exit_status": completed.returncode,
        "broken_contracts": int(match.group(1)) if match else "not reported",
        "duration_ns": duration_ns,
        "duration_seconds": duration_ns / 1_000_000_000,
        "stdout": {"path": "raw/b0-evaluator.stdout.txt", "sha256": sha256_bytes(completed.stdout)},
        "stderr": {"path": "raw/b0-evaluator.stderr.txt", "sha256": sha256_bytes(completed.stderr)},
        "evaluator_version": importlib.metadata.version("import-linter"),
    }


def run_pilot(exp02_run_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Validate authentic EXP-02 evidence, execute P, and write a reproducible trace."""
    root = ROOT.resolve(strict=True)
    exp02_path = exp02_run_dir.resolve(strict=True)
    destination = output_dir.resolve()
    if destination.exists() or destination.is_relative_to(root):
        raise ValueError("output directory must be new and outside the repository")
    source_revision = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("source checkout must be clean before the PILOT-02 Method P run")
    if _git("rev-parse", f"{source_revision}:app") != "cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08":
        raise ValueError("A0.1 app tree differs from the protocol-pinned source tree")

    exp02_bundle = validate_bundle(exp02_path)
    exp02_evidence = exp02.validate_representation_evidence(exp02_path, exp02_bundle)
    if exp02_bundle["source_revision"]["commit_sha"] != source_revision:
        raise ValueError("EXP-02 source revision is not the clean Method P source revision")
    if exp02_bundle["source_revision"]["git_dirty"]:
        raise ValueError("EXP-02 source worktree was dirty")
    if exp02_bundle["architecture"]["state"] != "A0_1_CAPABILITY_MODULES":
        raise ValueError("EXP-02 architecture state is not A0.1")

    destination.mkdir(parents=True)
    raw_dir = destination / "raw"
    raw_dir.mkdir()
    with tempfile.TemporaryDirectory(prefix="pilot02-method-input-") as temporary:
        temporary_root = Path(temporary)
        policy_bundle = temporary_root / "policy-source-v3"
        p_input_dir = temporary_root / "method-input-p"
        registry = json.loads(
            (POLICY_SOURCE / "fitness/policy/registry.json").read_text(encoding="utf-8")
        )
        policy_revision = f"PILOT02_DRAFT_OPEN_{source_revision[:12]}"
        policy_manifest = package_policy_source_v3(POLICY_SOURCE, policy_bundle, policy_revision)
        v3_manifest = export_method_inputs_v3(
            root,
            policy_bundle,
            p_input_dir,
            "P",
            FROZEN_A0_SHA,
            source_revision,
            str(registry["as_of"]),
        )
        profile = json.loads(_source_blob(source_revision, PILOT02_PROFILE_DEFINITION_PATH))
        if sha256_bytes(_source_blob(source_revision, PILOT02_PROFILE_DEFINITION_PATH)) != (
            PILOT02_PROFILE_DEFINITION_SHA256
        ):
            raise ProtocolError("PILOT02_PROFILE_DEFINITION_SOURCE_MISMATCH")
        profile["architecture_source_sha"] = source_revision
        profile["a0_1_app_tree_sha"] = v3_manifest["after_tree_sha"]
        _embedded_artifacts(profile, source_revision)
        _install_profile(p_input_dir, profile)
        p_bundle = verify_v3_p_bundle(
            p_input_dir,
            evidence_ledger=EvidenceLedger({}, {}, {}),
        )

        started_ns = time.perf_counter_ns()
        result = run_adaptation(p_bundle)
        adaptation_duration_ns = time.perf_counter_ns() - started_ns
        trace = _adaptation_trace(p_bundle, result)
        trace["pilot02_profile_pair_assessments"] = _assess_profile_pairs(
            profile=profile,
            exp02_run_dir=exp02_path,
            exp02_bundle=exp02_bundle,
            exp02_evidence=exp02_evidence,
            p_bundle=p_bundle,
            output_dir=destination,
        )
        trace["pilot02_profile_pair_assessments_not_used_for_adaptation"] = True
        trace["method_p_computation_duration_ns"] = adaptation_duration_ns
        trace["method_p_computation_duration_seconds"] = adaptation_duration_ns / 1_000_000_000
        (destination / "method_p_trace.json").write_bytes(pretty_json_bytes(trace))
        shutil.copytree(p_input_dir, destination / "verified_method_input")

    b0_evaluation = _run_b0_evaluator(destination)
    candidate = result.candidate
    candidate_status = (
        candidate.get("candidate_validation", {}).get("status")
        if isinstance(candidate, dict)
        else "not_materialized"
    )
    p_evaluation = {
        "status": "not_measured",
        "reason": (
            "The existing Method P result did not provide a valid, publishable candidate "
            "with an independently authorized evaluator configuration."
        ),
        "candidate_validation_status": candidate_status,
    }
    if isinstance(candidate, dict):
        (destination / "candidate_configuration.json").write_bytes(pretty_json_bytes(candidate))

    artifacts = []
    for path in sorted(destination.rglob("*")):
        if path.is_file() and path.name not in {"run_manifest.json", "run_manifest.sha256"}:
            relative = path.relative_to(destination).as_posix()
            content = path.read_bytes()
            artifacts.append(
                {"path": relative, "size_bytes": len(content), "sha256": sha256_bytes(content)}
            )
    manifest = {
        "schema_version": 1,
        "pilot_id": "PILOT-02",
        "execution_status": "completed_development_only",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "architecture": {
            "before_sha": FROZEN_A0_SHA,
            "after_sha": source_revision,
            "after_app_tree_sha": v3_manifest["after_tree_sha"],
            "transition": "A0_MONOLITH -> A0_1_CAPABILITY_MODULES",
        },
        "source_revision": {
            "commit_sha": source_revision,
            "app_tree_sha": v3_manifest["after_tree_sha"],
            "git_dirty": False,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "p_method_input": {
            "bundle_sha256": p_bundle.manifest["bundle_sha256"],
            "policy_bundle_sha256": policy_manifest["policy_bundle_sha256"],
            "policy_source_revision": policy_revision,
            "policy_registry_closure": registry["closure"],
            "policy_normative_statuses": sorted(
                {str(row.get("normative_status")) for row in registry["policies"]}
            ),
            "profile_definition_sha256": PILOT02_PROFILE_DEFINITION_SHA256,
        },
        "exp02": {
            "run_id": exp02_bundle["run_id"],
            "bundle_status": exp02_bundle["bundle_status"],
            "bundle_sha256": sha256_bytes((exp02_path / BUNDLE_FILENAME).read_bytes()),
            "representation_evidence_sha256": exp02_bundle["fitness_representation_evidence"][
                "sha256"
            ],
            "source_revision": exp02_evidence["source_revision"],
            "validated_by": ["scripts.exp01_evidence_contract.validate_bundle", "EXP-02"],
            "Coverage_P": exp02_evidence["coverage_claims"]["Coverage_P"],
            "Coverage_ref": exp02_evidence["coverage_claims"]["Coverage_ref"],
        },
        "method_p": {
            "algorithm_status": "NOT_READY",
            "computation_duration_ns": adaptation_duration_ns,
            "governance_result": result.governance.result.value,
            "governance_reason_codes": list(result.governance.reason_codes),
            "after_applicability": result.after_applicability.to_dict(),
            "current_pairs": [item.to_dict() for item in result.current_pairs],
            "operation_plan": result.operation_plan.to_dict(),
            "candidate_status": candidate_status,
            "candidate_sha256": result.candidate_sha256,
            "candidate_evaluation": p_evaluation,
            "trace_path": "method_p_trace.json",
        },
        "b0": {
            "fitness_configuration_sha256": FROZEN_B0_CONFIG_SHA256,
            "architecture_representation_ids": ["REP_A0_ARCH_CI_LAYERING"],
            "evaluation": b0_evaluation,
        },
        "independent_assessment": "pending",
        "research_gates": {"G1": "INCOMPLETE", "G4": "NOT AUTHORIZED"},
        "artifact_inventory": artifacts,
    }
    manifest_bytes = pretty_json_bytes(manifest)
    (destination / "run_manifest.json").write_bytes(manifest_bytes)
    digest = sha256_bytes(manifest_bytes)
    (destination / "run_manifest.sha256").write_text(
        f"{digest}  run_manifest.json\n", encoding="ascii"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Run PILOT-02 using one digest-validated EXP-02 source bundle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exp02-run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = run_pilot(args.exp02_run_dir, args.output_dir)
    except (OSError, ValueError, KeyError, ProtocolError) as error:
        print(json.dumps({"status": "rejected", "reason": str(error)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": manifest["execution_status"],
                "run_id": manifest["exp02"]["run_id"],
                "source_revision": manifest["source_revision"]["commit_sha"],
                "governance": manifest["method_p"]["governance_result"],
                "output_dir": str(args.output_dir.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
