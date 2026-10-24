"""Execute and score the TEST_ONLY MONO-E1 Method P decision rehearsal."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_adaptation import (
    METHOD_VERSION,
    run_adaptation,
    verify_v3_p_bundle,
)
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3
from experiments.execution.tooling.p_semantic import pair_proof_subject
from tests.integration import test_p_applicability_v3 as fixtures

EXPERIMENT_DIR = Path(__file__).resolve().parent
SCENARIO_PATH = EXPERIMENT_DIR / "scenarios_v1.json"
SCENARIO_SCHEMA_PATH = EXPERIMENT_DIR / "scenario.schema.json"
REFERENCE_PATH = EXPERIMENT_DIR / "reference_v1.json"
REFERENCE_SHA_PATH = EXPERIMENT_DIR / "reference_v1.sha256"
EXPECTED_SCENARIO_IDS = {f"{group}{number}" for group in "ABCD" for number in (1, 2)}
SCIENTIFIC_STATUS_EFFECT = "NONE"
P_METHOD_FILES = (
    "experiments/execution/tooling/contracts.py",
    "experiments/execution/tooling/errors.py",
    "experiments/execution/tooling/hashing.py",
    "experiments/execution/tooling/inputs.py",
    "experiments/execution/tooling/p_adaptation.py",
    "experiments/execution/tooling/p_adaptation_evidence.py",
    "experiments/execution/tooling/p_applicability.py",
    "experiments/execution/tooling/p_candidate.py",
    "experiments/execution/tooling/p_governance.py",
    "experiments/execution/tooling/p_impact.py",
    "experiments/execution/tooling/p_input_export_v2.py",
    "experiments/execution/tooling/p_input_validation.py",
    "experiments/execution/tooling/p_operations.py",
    "experiments/execution/tooling/p_policy_source_v3.py",
    "experiments/execution/tooling/p_semantic.py",
    "tests/integration/test_p_applicability_v3.py",
    "experiments/pilots/mono_e1_dev_p_decisions_v1/runner.py",
)
P_METHOD_SCHEMA_FILES = (
    "experiments/execution/schemas/applicability_ruleset_v1.schema.json",
    "experiments/execution/schemas/architecture_policy_snapshot_v1_1.schema.json",
    "experiments/execution/schemas/architecture_policy_snapshot_v1_2.schema.json",
    "experiments/execution/schemas/evaluator_evidence.schema.json",
    "experiments/execution/schemas/method_input_v3_candidate.schema.json",
    "experiments/execution/schemas/p_adaptation_evidence_v1.schema.json",
    "experiments/execution/schemas/p_adaptation_evidence_v2.schema.json",
    "experiments/execution/schemas/p_adaptation_trace_v1.schema.json",
    "experiments/execution/schemas/p_candidate_configuration_v1.schema.json",
    "experiments/execution/schemas/p_coverage_assessment_v1.schema.json",
    "experiments/execution/schemas/p_governance_decision_v1.schema.json",
    "experiments/execution/schemas/p_impact_assessment_v1.schema.json",
    "experiments/execution/schemas/p_operation_plan_v1.schema.json",
    "experiments/execution/schemas/p_pair_assessment_v1.schema.json",
    "experiments/execution/schemas/pilot02_method_input_profile_v1.schema.json",
    "experiments/execution/schemas/pilot02_method_input_profile_v2.schema.json",
)
P_METHOD_DATA_FILES = (
    "experiments/execution/contracts/fact_vocabulary_v1.json",
    "fitness/catalog/architectural-obligations.yaml",
)
RUN_CONTEXT = """# Context — `run_v1`

Generated outputs for MONO_E1_DEV_P_DECISIONS_V1. `execution_manifest.json` binds
the pre-registration commit, Method P source identity, environment, and scenario
bundle digests. `raw_records_manifest.json` binds every retained raw file. The
scorer writes `results_v1.json`, `report_v1.md`, and `score_manifest.json` only
after all raw execution records exist.

The `raw/` directory stores scenario-prefixed records and deterministic ZIP
archives of the exact V3 method input bundles. Extract a bundle archive to a new
directory and run `verify_method_bundle_v3()` before reuse. Do not overwrite this
run; use a new versioned output directory for a reproduction.
"""
RAW_CONTEXT = """# Context — `run_v1/raw`

This directory contains the exact TEST_ONLY method input bundle archives,
adaptation sidecars, evaluator outputs, B0_SYNTH baselines, and three raw Method
P records per scenario. Files use the scenario ID as a prefix. The parent
`raw_records_manifest.json` records each file's byte size and SHA-256 digest.
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    )


def _archive_method_bundle(bundle_root: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(item for item in bundle_root.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(path.relative_to(bundle_root).as_posix())
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, path.read_bytes())
    return _sha256(destination)


def _git(*args: str, cwd: Path = EXPERIMENT_DIR.parents[2]) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise RuntimeError("Git executable is unavailable")
    completed = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [git_executable, "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def validate_scenario_catalog() -> dict[str, Any]:
    schema = _read_json(SCENARIO_SCHEMA_PATH)
    catalog = _read_json(SCENARIO_PATH)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(catalog), key=lambda error: list(error.path)
    )
    if errors:
        raise ValueError(
            "Scenario catalog schema invalid: " + "; ".join(error.message for error in errors)
        )
    ids = [str(row["scenario_id"]) for row in catalog["scenarios"]]
    if len(ids) != len(set(ids)) or set(ids) != EXPECTED_SCENARIO_IDS:
        raise ValueError("Scenario identities must be exactly A1-A2, B1-B2, C1-C2, and D1-D2")
    if any(
        "expected_operation" in row or "expected_governance" in row for row in catalog["scenarios"]
    ):
        raise ValueError("Expected decisions must remain scorer-side")
    return catalog


def _fixture_arguments(scenario: Mapping[str, Any]) -> dict[str, Any]:
    fixture = scenario["fixture"]
    before_files = {
        str(path): str(content).encode() for path, content in fixture["before_files"].items()
    }
    after_files = {
        str(path): str(content).encode() for path, content in fixture["after_files"].items()
    }
    parent_targets = list(fixture["parent_targets"])
    template_targets = list(fixture["template_targets"])
    return {
        "include_parent_representation": bool(fixture["include_parent_representation"]),
        "include_add_template": bool(fixture["include_successor_template"]),
        "architecture_noop": False,
        "before_files": before_files,
        "after_files": after_files,
        "removed_after_paths": list(fixture["removed_after_paths"]),
        "complete_fact_inventory": bool(fixture["complete_module_inventory"]),
        "active_policy_states": tuple(fixture["active_policy_states"]),
        "parent_scope": {"scope": "source:app", "targets": parent_targets}
        if parent_targets
        else None,
        "template_scope": (
            {"scope": "source:app", "targets": template_targets} if template_targets else None
        ),
    }


def _run_evaluator(
    artifact: bytes,
    architecture_root: Path,
    work_root: Path,
    *,
    configured_targets: Sequence[str] | None = None,
    required_targets: Sequence[str] | None = None,
) -> tuple[subprocess.CompletedProcess[bytes], bytes]:
    script_path = work_root / "synthetic_scope_probe.py"
    script_path.write_bytes(artifact)
    command = [sys.executable, str(script_path), str(architecture_root)]
    if configured_targets is not None and required_targets is not None:
        command.extend(
            [
                json.dumps(list(configured_targets), separators=(",", ":")),
                json.dumps(list(required_targets), separators=(",", ":")),
            ]
        )
    completed = subprocess.run(  # noqa: S603 - test-authored evaluator, fixed interpreter, verified source tree
        command,
        check=False,
        capture_output=True,
        timeout=10,
    )
    return completed, completed.stdout


def _pair_observation(
    *,
    bundle: Any,
    representation: Mapping[str, Any],
    obligation: Mapping[str, Any],
    artifact: bytes,
    architecture_root: Path,
    architecture_sha: str,
    work_root: Path,
    tag: str,
    configured_targets: Sequence[str] | None = None,
    required_targets: Sequence[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes], dict[str, Any]]:
    completed, stdout = _run_evaluator(
        artifact,
        architecture_root,
        work_root,
        configured_targets=configured_targets,
        required_targets=required_targets,
    )
    try:
        report = json.loads(stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError(f"SYNTHETIC_EVALUATOR_OUTPUT_INVALID:{tag}") from error
    if not isinstance(report, Mapping):
        raise ProtocolError(f"SYNTHETIC_EVALUATOR_OUTPUT_INVALID:{tag}")

    artifact_path = str(representation["evaluator_artifact"]["path"])
    evidence_path = f"synthetic/evidence/{tag}.json"
    stdout_digest = sha256_bytes(stdout)
    required = list(report.get("expected_subjects", [])) if configured_targets is not None else []
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "representation_id": str(representation["id"]),
        "architecture_source_sha": architecture_sha,
        "evaluator_id": str(representation["evaluator"]),
        "infrastructure_status": "completed",
        "process_exit_code": completed.returncode,
        "configured_targets": list(report.get("configured_targets", [])),
        "resolved_targets": list(report.get("resolved_targets", [])),
        "inspected_subjects": list(report.get("inspected_subjects", [])),
        "missing_targets": list(report.get("missing_targets", [])),
        "inspected_edge_count": None
        if configured_targets is not None
        else report.get("inspected_edge_count"),
        "stage_applicable": True,
        "semantic_compatible": not report.get("missing_targets", []),
        "mapping_resolved": True,
        "evidence_contract_satisfied": True,
        "adequacy_proven": True,
        "evidence_artifacts": [{"path": evidence_path, "sha256": stdout_digest}],
        "stdout_sha256": stdout_digest,
        "stderr_sha256": sha256_bytes(completed.stderr),
    }
    if configured_targets is not None:
        evidence["inspection_scope"] = {
            "unit": "file",
            "expected_subjects": required,
            "measured_count": len(required),
            "evidence_artifact": {"path": evidence_path, "sha256": stdout_digest},
        }
    subject = pair_proof_subject(representation, obligation, architecture_sha, evidence)
    invalid = bool(evidence["missing_targets"]) or completed.returncode != 0
    proof = {
        "representation_id": str(representation["id"]),
        "obligation_id": str(obligation["id"]),
        "status": "INVALID" if invalid else "VALID",
        "subject_sha256": sha256_bytes(canonical_json_bytes(subject)),
        "verifier_id": "synthetic_adaptation_test_verifier_v1",
        "source_bindings": [
            {"source_id": source_id, "sha256": bundle.source_digests[source_id]}
            for source_id in ("P_CAPABILITIES", "P_TRACEABILITY")
        ],
        "evidence_refs": ["P_TRACEABILITY"],
        "reason_codes": ["SYNTHETIC_REQUIRED_SCOPE_MISSING"] if invalid else [],
    }
    artifact_bytes = {
        artifact_path: artifact,
        evidence_path: stdout,
    }
    raw = {
        "tag": tag,
        "representation_id": str(representation["id"]),
        "architecture_source_sha": architecture_sha,
        "process_exit_code": completed.returncode,
        "command": ["python", Path(artifact_path).name, "<synthetic-architecture-root>"]
        + (
            [list(configured_targets or []), list(required_targets or [])]
            if configured_targets is not None
            else []
        ),
        "stdout_sha256": stdout_digest,
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": completed.stderr.decode("utf-8", errors="replace"),
        "evaluator_report": dict(report),
    }
    return evidence, proof, artifact_bytes, raw


def _resign_sidecar(sidecar: dict[str, Any], trust_context: Any) -> dict[str, Any]:
    sidecar.pop("sidecar_sha256", None)
    sidecar.pop("signature", None)
    digest = sha256_bytes(canonical_json_bytes(sidecar))
    sidecar["sidecar_sha256"] = digest
    sidecar["signature"] = hmac.new(
        trust_context.adaptation_key,
        digest.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return sidecar


def _encode_artifacts(artifacts: Mapping[str, bytes]) -> list[dict[str, str]]:
    return [
        {
            "path": path,
            "sha256": sha256_bytes(content),
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
        for path, content in sorted(artifacts.items())
    ]


def _prepare_sidecar(
    scenario: Mapping[str, Any],
    bundle: Any,
    trust_context: Any,
    evaluator_artifact: bytes,
    work_root: Path,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    mode = scenario["evidence"]["mode"]
    if mode == "missing":
        return None, []

    use_template = bool(scenario["fixture"]["include_successor_template"])
    work_root.mkdir(parents=True, exist_ok=True)
    foundation = fixtures._positive_adaptation_sidecar(
        bundle,
        trust_context,
        evaluator_artifact,
        work_root,
        use_add_template=use_template,
    )
    raw_evaluator_records: list[dict[str, Any]] = []
    if mode not in {"pair_scope", "stale"}:
        return foundation, raw_evaluator_records

    payload = foundation["payload"]
    payload["evaluator_evidence"] = []
    payload["pair_proofs"] = []
    artifact_representation = (
        bundle.templates[0]["representation"] if bundle.templates else bundle.representations[0]
    )
    artifact_bytes: dict[str, bytes] = {
        str(artifact_representation["evaluator_artifact"]["path"]): evaluator_artifact
    }
    after_sha = str(bundle.snapshot["architecture"]["after_commit"])
    before_sha = str(bundle.snapshot["architecture"]["before_commit"])
    obligation = next(row for row in bundle.obligations if row["id"] == "AC_LAYERING")

    if mode == "pair_scope":
        parent = next(
            row for row in bundle.representations if row["id"] == "REP_A0_ARCH_CI_LAYERING"
        )
        template = bundle.templates[0]["representation"]
        required_targets = list(scenario["evidence"]["required_targets_after"])
        pair_rows = [
            (parent, list(scenario["fixture"]["parent_targets"]), "after", after_sha, "current"),
            (
                template,
                list(scenario["fixture"]["template_targets"]),
                "after",
                after_sha,
                "successor",
            ),
        ]
    elif mode == "stale":
        parent = next(
            row for row in bundle.representations if row["id"] == "REP_A0_ARCH_CI_LAYERING"
        )
        pair_rows = [(parent, None, "before", before_sha, "stale_before")]
        required_targets = []
    else:
        raise ValueError(f"Unsupported evidence mode: {mode}")

    for representation, configured, state, source_sha, label in pair_rows:
        architecture_root = bundle.root / "architecture" / state
        evidence, proof, extra_artifacts, raw = _pair_observation(
            bundle=bundle,
            representation=representation,
            obligation=obligation,
            artifact=evaluator_artifact,
            architecture_root=architecture_root,
            architecture_sha=source_sha,
            work_root=work_root,
            tag=label,
            configured_targets=configured,
            required_targets=required_targets if configured is not None else None,
        )
        payload["evaluator_evidence"].append(
            {
                "representation_id": str(representation["id"]),
                "obligation_id": str(obligation["id"]),
                "evidence": evidence,
            }
        )
        payload["pair_proofs"].append(proof)
        artifact_bytes.update(extra_artifacts)
        raw_evaluator_records.append(raw)
    payload["artifact_bytes"] = _encode_artifacts(artifact_bytes)
    return _resign_sidecar(foundation, trust_context), raw_evaluator_records


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_plain(item) for item in value]
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    return value


def _method_identity(repo_root: Path) -> dict[str, Any]:
    return {
        "method_version": METHOD_VERSION,
        "files": {relative: _sha256(repo_root / relative) for relative in P_METHOD_FILES},
        "schemas": {relative: _sha256(repo_root / relative) for relative in P_METHOD_SCHEMA_FILES},
        "catalogs": {relative: _sha256(repo_root / relative) for relative in P_METHOD_DATA_FILES},
        "scenario_catalog_sha256": _sha256(SCENARIO_PATH),
        "scenario_schema_sha256": _sha256(SCENARIO_SCHEMA_PATH),
    }


def _git_blob_sha256(repo_root: Path, commit_sha: str, relative_path: str) -> str:
    if len(commit_sha) != 40 or any(
        character not in "0123456789abcdef" for character in commit_sha
    ):
        raise ProtocolError("METHOD_SOURCE_COMMIT_INVALID")
    path_parts = PurePosixPath(relative_path).parts
    if PurePosixPath(relative_path).is_absolute() or ".." in path_parts:
        raise ProtocolError("METHOD_SOURCE_PATH_INVALID")
    git_executable = shutil.which("git")
    if git_executable is None:
        raise RuntimeError("Git executable is unavailable")
    completed = subprocess.run(  # noqa: S603 - fixed Git executable and validated commit/path arguments
        [git_executable, "-C", str(repo_root), "show", f"{commit_sha}:{relative_path}"],
        check=True,
        capture_output=True,
    )
    return sha256_bytes(completed.stdout)


def _method_identity_at_commit(repo_root: Path, commit_sha: str) -> dict[str, Any]:
    def digest(relative: str) -> str:
        return _git_blob_sha256(repo_root, commit_sha, relative)

    return {
        "method_version": METHOD_VERSION,
        "files": {relative: digest(relative) for relative in P_METHOD_FILES},
        "schemas": {relative: digest(relative) for relative in P_METHOD_SCHEMA_FILES},
        "catalogs": {relative: digest(relative) for relative in P_METHOD_DATA_FILES},
        "scenario_catalog_sha256": digest(SCENARIO_PATH.relative_to(repo_root).as_posix()),
        "scenario_schema_sha256": digest(SCENARIO_SCHEMA_PATH.relative_to(repo_root).as_posix()),
    }


def _execute(output_dir: Path) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Execution output already exists: {output_dir}")
    catalog = validate_scenario_catalog()
    repo_root = EXPERIMENT_DIR.parents[2]
    if _git("status", "--porcelain", cwd=repo_root):
        raise RuntimeError("Execute from a clean pre-registration commit")
    source_commit = _git("rev-parse", "HEAD", cwd=repo_root)
    method_identity = _method_identity(repo_root)
    output_dir.mkdir(parents=True)
    raw_root = output_dir / "raw"
    raw_root.mkdir()
    (output_dir / "CONTEXT.md").write_text(RUN_CONTEXT, encoding="utf-8")
    (raw_root / "CONTEXT.md").write_text(RAW_CONTEXT, encoding="utf-8")
    records: list[dict[str, Any]] = []
    baseline_records: list[dict[str, Any]] = []
    input_bundle_archives: dict[str, str] = {}
    environment = {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": sys.platform,
        "git_version": _git("--version", cwd=repo_root),
        "method_version": METHOD_VERSION,
        "repetitions_per_scenario": int(catalog["repetitions"]),
    }

    for scenario in catalog["scenarios"]:
        scenario_id = str(scenario["scenario_id"])
        fixture_kwargs = _fixture_arguments(scenario)
        with tempfile.TemporaryDirectory(prefix=f"mono-e1-{scenario_id.lower()}-") as temp_dir:
            temp_root = Path(temp_dir)
            bundle, trust_context, evaluator_artifact = fixtures._synthetic_positive_bundle(
                temp_root,
                **fixture_kwargs,
            )
            preserved_bundle = temp_root / "preserved-method-input-v3"
            shutil.copytree(bundle.root, preserved_bundle)
            sidecar, evaluator_records = _prepare_sidecar(
                scenario,
                bundle,
                trust_context,
                evaluator_artifact,
                temp_root / "sidecar-evaluator",
            )
            if evaluator_records:
                _write_json(
                    raw_root / f"{scenario_id}_sidecar_evaluator_records.json", evaluator_records
                )
            if sidecar is not None:
                _write_json(raw_root / f"{scenario_id}_adaptation_evidence_test_only.json", sidecar)
            bundle_manifest = verify_method_bundle_v3(preserved_bundle, expected_method_id="P")
            if "reference_v1.json" in " ".join(
                str(row["path"]) for row in bundle_manifest["files"]
            ):
                raise ProtocolError("Scorer reference unexpectedly included in Method P inputs")

            baseline_written = False
            for repetition in range(1, int(catalog["repetitions"]) + 1):
                started = time.perf_counter_ns()
                try:
                    verified = verify_v3_p_bundle(
                        preserved_bundle,
                        evidence_ledger=bundle.evidence_ledger,
                        trust_context=trust_context,
                        fact_verifier=fixtures._synthetic_fact_verifier,
                        completeness_verifier=fixtures._synthetic_completeness_verifier,
                    )
                    p_result = run_adaptation(verified, evidence_context=sidecar)
                    result = {
                        "execution_status": "COMPLETED",
                        "bundle_provenance": verified.bundle_provenance,
                        "trust_scope": verified.trust_scope,
                        "operation_plan": p_result.operation_plan.to_dict(),
                        "proposed_operations": [
                            row.operation.value for row in p_result.operation_plan.operations
                        ],
                        "candidate": _plain(p_result.candidate),
                        "candidate_sha256": p_result.candidate_sha256,
                        "candidate_validation": (
                            _plain(p_result.candidate.get("candidate_validation"))
                            if p_result.candidate is not None
                            else None
                        ),
                        "governance": p_result.governance.to_dict(),
                        "before_applicability": p_result.before_applicability.to_dict(),
                        "after_applicability": p_result.after_applicability.to_dict(),
                        "current_pairs": [row.to_dict() for row in p_result.current_pairs],
                        "candidate_pairs": [row.to_dict() for row in p_result.candidate_pairs],
                        "current_coverage": p_result.current_coverage.to_dict(),
                        "candidate_coverage": (
                            p_result.candidate_coverage.to_dict()
                            if p_result.candidate_coverage is not None
                            else None
                        ),
                        "impact": p_result.impact.to_dict(),
                        "evidence_trust_scope": p_result.evidence_trust_scope,
                    }
                    if not baseline_written:
                        baseline = {
                            "schema_version": 1,
                            "experiment_id": "MONO_E1_DEV_P_DECISIONS_V1",
                            "scenario_id": scenario_id,
                            "method": "B0_SYNTH",
                            "operation": "UNCHANGED_CONFIGURATION",
                            "governance": "NOT_RUN",
                            "initial_configuration_sha256": verified.parent_configuration_sha256,
                            "architecture_before_sha": verified.manifest["architecture_before_sha"],
                            "architecture_after_sha": verified.manifest["architecture_source_sha"],
                            "input_bundle_sha256": verified.manifest["bundle_sha256"],
                            "coverage": p_result.current_coverage.to_dict(),
                            "interpretation": (
                                "Synthetic no-op configuration assessed on the same after-state "
                                "and obligation universe; no semantic adaptation is applied."
                            ),
                        }
                        baseline_records.append(baseline)
                        _write_json(raw_root / f"{scenario_id}_b0_synth.json", baseline)
                        baseline_written = True
                except (
                    Exception
                ) as error:  # preserve typed failure instead of converting it to HOLD
                    code = getattr(error, "code", None)
                    if code is None and isinstance(error, (ProtocolError, ContractValidationError)):
                        code = str(error)
                    result = {
                        "execution_status": "FAILED",
                        "failure_type": type(error).__name__,
                        "failure_reason_code": str(code or type(error).__name__),
                        "failure_message": str(error),
                        "bundle_provenance": None,
                        "trust_scope": None,
                        "operation_plan": None,
                        "proposed_operations": [],
                        "candidate": None,
                        "candidate_sha256": None,
                        "candidate_validation": None,
                        "governance": None,
                        "current_pairs": [],
                        "candidate_pairs": [],
                        "current_coverage": None,
                        "candidate_coverage": None,
                        "impact": None,
                        "evidence_trust_scope": None,
                    }
                elapsed = time.perf_counter_ns() - started
                record = {
                    "schema_version": 1,
                    "experiment_id": "MONO_E1_DEV_P_DECISIONS_V1",
                    "scenario_id": scenario_id,
                    "repetition": repetition,
                    "source_commit_sha": source_commit,
                    "method_identity": method_identity,
                    "input_bundle_sha256": bundle_manifest["bundle_sha256"],
                    "architecture_before_sha": bundle_manifest["architecture_before_sha"],
                    "architecture_after_sha": bundle_manifest["architecture_source_sha"],
                    "sidecar_sha256": sidecar.get("sidecar_sha256") if sidecar else None,
                    "duration_ns": elapsed,
                    "runner_rss_high_water_bytes": _rss_high_water_bytes(),
                    "result": result,
                }
                records.append(record)
                _write_json(raw_root / f"{scenario_id}_method_p_rep_{repetition:02d}.json", record)
            input_bundle_archives[scenario_id] = _archive_method_bundle(
                preserved_bundle, raw_root / f"{scenario_id}_method_input_v3.zip"
            )

    _write_json(
        output_dir / "execution_manifest.json",
        {
            "schema_version": 1,
            "experiment_id": "MONO_E1_DEV_P_DECISIONS_V1",
            "source_commit_sha": source_commit,
            "method_identity": method_identity,
            "environment": environment,
            "scenario_count": len(catalog["scenarios"]),
            "method_p_execution_count": len(records),
            "b0_synth_scenario_count": len(baseline_records),
            "reference_was_read_by_execution_phase": False,
            "scientific_status_effect": SCIENTIFIC_STATUS_EFFECT,
            "method_input_bundle_digests": {
                scenario_id: next(
                    row["input_bundle_sha256"]
                    for row in records
                    if row["scenario_id"] == scenario_id
                )
                for scenario_id in sorted(EXPECTED_SCENARIO_IDS)
            },
            "method_input_bundle_archive_sha256": input_bundle_archives,
            "execution_command": [
                sys.executable,
                "-m",
                "experiments.pilots.mono_e1_dev_p_decisions_v1.runner",
                "execute",
                "--output-dir",
                output_dir.relative_to(repo_root).as_posix(),
            ],
            "scoring_command": [
                sys.executable,
                "-m",
                "experiments.pilots.mono_e1_dev_p_decisions_v1.runner",
                "score",
                "--output-dir",
                output_dir.relative_to(repo_root).as_posix(),
            ],
        },
    )
    _write_raw_manifest(raw_root)
    _write_checksum_inventory(output_dir)


def _rss_high_water_bytes() -> int | None:
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value if sys.platform == "darwin" else value * 1024
    except (ImportError, OSError, ValueError):
        return None


def _write_raw_manifest(raw_root: Path) -> None:
    rows = []
    for path in sorted(item for item in raw_root.rglob("*") if item.is_file()):
        rows.append(
            {
                "path": path.relative_to(raw_root.parent).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    _write_json(raw_root.parent / "raw_records_manifest.json", {"schema_version": 1, "files": rows})


def _verify_raw_manifest(output_dir: Path) -> list[dict[str, Any]]:
    manifest = _read_json(output_dir / "raw_records_manifest.json")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise ProtocolError("RAW_MANIFEST_INVALID")
    actual_paths = {
        path.relative_to(output_dir).as_posix()
        for path in (output_dir / "raw").rglob("*")
        if path.is_file()
    }
    declared_paths = {str(row.get("path")) for row in rows if isinstance(row, Mapping)}
    if actual_paths != declared_paths:
        raise ProtocolError("RAW_FILE_INVENTORY_MISMATCH")
    for row in rows:
        if not isinstance(row, Mapping):
            raise ProtocolError("RAW_MANIFEST_INVALID")
        path = output_dir / str(row["path"])
        if (
            not path.is_file()
            or _sha256(path) != row.get("sha256")
            or path.stat().st_size != row.get("size_bytes")
        ):
            raise ProtocolError("RAW_DIGEST_MISMATCH:" + str(row.get("path")))
    return rows


def _verify_method_input_archives(output_dir: Path, execution_manifest: Mapping[str, Any]) -> None:
    expected_archives = execution_manifest.get("method_input_bundle_archive_sha256")
    expected_bundles = execution_manifest.get("method_input_bundle_digests")
    if not isinstance(expected_archives, Mapping) or not isinstance(expected_bundles, Mapping):
        raise ProtocolError("INPUT_BUNDLE_ARCHIVE_MANIFEST_INVALID")
    if (
        set(expected_archives) != EXPECTED_SCENARIO_IDS
        or set(expected_bundles) != EXPECTED_SCENARIO_IDS
    ):
        raise ProtocolError("INPUT_BUNDLE_ARCHIVE_INVENTORY_INVALID")
    for scenario_id in sorted(EXPECTED_SCENARIO_IDS):
        archive_path = output_dir / "raw" / f"{scenario_id}_method_input_v3.zip"
        if not archive_path.is_file() or _sha256(archive_path) != expected_archives[scenario_id]:
            raise ProtocolError(f"INPUT_BUNDLE_ARCHIVE_DIGEST_MISMATCH:{scenario_id}")
        try:
            with (
                zipfile.ZipFile(archive_path) as archive,
                tempfile.TemporaryDirectory(
                    prefix=f"mono-e1-verify-{scenario_id.lower()}-"
                ) as temp_dir,
            ):
                for member in archive.infolist():
                    member_path = PurePosixPath(member.filename)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise ProtocolError(f"INPUT_BUNDLE_ARCHIVE_PATH_INVALID:{scenario_id}")
                archive.extractall(temp_dir)
                manifest = verify_method_bundle_v3(Path(temp_dir), expected_method_id="P")
        except (OSError, zipfile.BadZipFile, RuntimeError) as error:
            raise ProtocolError(f"INPUT_BUNDLE_ARCHIVE_INVALID:{scenario_id}") from error
        if manifest["bundle_sha256"] != expected_bundles[scenario_id]:
            raise ProtocolError(f"INPUT_BUNDLE_DIGEST_MISMATCH:{scenario_id}")


def _expected_reference() -> tuple[dict[str, Any], str]:
    reference_bytes = REFERENCE_PATH.read_bytes()
    reference_digest = sha256_bytes(reference_bytes)
    sidecar_value = REFERENCE_SHA_PATH.read_text(encoding="utf-8").split()[0]
    if sidecar_value != reference_digest:
        raise ProtocolError("REFERENCE_FREEZE_DIGEST_MISMATCH")
    reference = json.loads(reference_bytes)
    if (
        reference.get("reference_status") != "AUTHOR_DECLARED"
        or reference.get("scope") != "DEVELOPMENT"
        or reference.get("independence") != "NON_INDEPENDENT"
        or reference.get("created_before_execution") is not True
    ):
        raise ProtocolError("REFERENCE_DECLARATION_INVALID")
    cases = reference.get("cases")
    ids = {str(row.get("scenario_id")) for row in cases or [] if isinstance(row, Mapping)}
    if ids != EXPECTED_SCENARIO_IDS or len(cases or []) != 8:
        raise ProtocolError("REFERENCE_CASE_INVENTORY_INVALID")
    return {str(row["scenario_id"]): dict(row) for row in cases}, reference_digest


def _operation(result: Mapping[str, Any]) -> str:
    if result.get("execution_status") != "COMPLETED":
        return "execution_failure"
    operations = result.get("proposed_operations", [])
    if len(operations) == 1:
        return str(operations[0])
    if len(operations) > 1:
        return "mixed"
    plan = result.get("operation_plan") or {}
    if plan.get("hold_reasons") or plan.get("reject_reasons"):
        return "hold"
    return "none"


def _is_semantically_supported(record: Mapping[str, Any]) -> bool:
    candidate_validation = record.get("candidate_validation")
    candidate_coverage = record.get("candidate_coverage")
    if candidate_coverage is not None:
        return (
            candidate_validation is not None
            and candidate_validation.get("status") == "valid"
            and candidate_coverage.get("status") == "COMPLETE"
        )
    current_coverage = record.get("current_coverage")
    return bool(
        current_coverage
        and current_coverage.get("status") == "COMPLETE"
        and record.get("governance", {}).get("result") == "ACCEPT"
    )


def _classify(reference: Mapping[str, Any], record: Mapping[str, Any]) -> str:
    if record.get("result", {}).get("execution_status") != "COMPLETED":
        return "NOT_EVALUABLE"
    actual_operation = _operation(record["result"])
    governance = record["result"].get("governance", {}).get("result")
    if (
        actual_operation != reference["expected_operation"]
        or governance != reference["expected_governance"]
    ):
        return "INCORRECT"
    if reference["expected_operation"] in {
        "add",
        "replace",
        "retain",
    } and not _is_semantically_supported(record["result"]):
        return "INCORRECT"
    return "CORRECT"


def _score(output_dir: Path) -> None:
    raw_manifest = _verify_raw_manifest(output_dir)
    execution_manifest = _read_json(output_dir / "execution_manifest.json")
    _verify_method_input_archives(output_dir, execution_manifest)
    source_commit_sha = str(execution_manifest.get("source_commit_sha", ""))
    committed_method_identity = _method_identity_at_commit(
        EXPERIMENT_DIR.parents[2], source_commit_sha
    )
    if execution_manifest.get("method_identity") != committed_method_identity:
        raise ProtocolError("METHOD_IDENTITY_MISMATCH")
    references, reference_digest = _expected_reference()
    record_paths = [
        str(row["path"]) for row in raw_manifest if "_method_p_rep_" in Path(str(row["path"])).name
    ]
    if any(not path.endswith(".json") for path in record_paths):
        raise ProtocolError("METHOD_P_RECORD_PATH_INVALID")
    records_with_paths = [(path, _read_json(output_dir / path)) for path in sorted(record_paths)]
    records = [record for _path, record in records_with_paths]
    if len(records) != 24:
        raise ProtocolError(f"METHOD_P_RECORD_COUNT_INVALID:{len(records)}")
    records_by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    digest_by_path = {str(row["path"]): str(row["sha256"]) for row in raw_manifest}
    for raw_path, record in records_with_paths:
        scenario_id = str(record["scenario_id"])
        if scenario_id not in references:
            raise ProtocolError("UNREGISTERED_SCENARIO_IN_RAW_RECORD")
        record_path = f"raw/{scenario_id}_method_p_rep_{int(record['repetition']):02d}.json"
        if raw_path != record_path:
            raise ProtocolError("RAW_RECORD_PATH_IDENTITY_MISMATCH")
        if record.get("source_commit_sha") != execution_manifest.get("source_commit_sha"):
            raise ProtocolError("RAW_SOURCE_COMMIT_MISMATCH")
        if record.get("input_bundle_sha256") != execution_manifest.get(
            "method_input_bundle_digests", {}
        ).get(scenario_id):
            raise ProtocolError(f"RAW_INPUT_BUNDLE_MISMATCH:{scenario_id}")
        record["raw_record_sha256"] = digest_by_path[record_path]
        record["classification"] = _classify(references[scenario_id], record)
        records_by_scenario[scenario_id].append(record)
    for scenario_id, scenario_records in records_by_scenario.items():
        repetitions = [int(row["repetition"]) for row in scenario_records]
        if sorted(repetitions) != [1, 2, 3]:
            raise ProtocolError(f"METHOD_P_REPETITION_INVENTORY_INVALID:{scenario_id}")

    confusion: dict[str, dict[str, int]] = {
        op: defaultdict(int) for op in ("retain", "add", "replace", "hold")
    }
    governance_counts: Counter[str] = Counter()
    score_rows: list[dict[str, Any]] = []
    all_counts: Counter[str] = Counter()
    operation_matches = operation_evaluable = 0
    unnecessary = nonadaptation_evaluable = 0
    missed = required_adaptation_evaluable = 0
    appropriate_holds = inappropriate_holds = missed_holds = hold_governance_mismatches = 0
    b0_difference_count = 0
    duration_by_operation: dict[str, list[int]] = defaultdict(list)
    for scenario_id in sorted(EXPECTED_SCENARIO_IDS):
        reference = references[scenario_id]
        scenario_records = sorted(
            records_by_scenario[scenario_id], key=lambda row: int(row["repetition"])
        )
        observed_ops = [_operation(row["result"]) for row in scenario_records]
        correct = sum(row["classification"] == "CORRECT" for row in scenario_records)
        incorrect = sum(row["classification"] == "INCORRECT" for row in scenario_records)
        not_evaluable = sum(row["classification"] == "NOT_EVALUABLE" for row in scenario_records)
        all_counts.update(
            {"CORRECT": correct, "INCORRECT": incorrect, "NOT_EVALUABLE": not_evaluable}
        )
        scenario_unnecessary = 0
        scenario_missed = 0
        scenario_appropriate_holds = 0
        scenario_inappropriate_holds = 0
        scenario_missed_holds = 0
        scenario_hold_governance_mismatches = 0
        governance_by_repetition: list[str] = []
        reason_codes_by_repetition: list[list[str]] = []
        for record, observed in zip(scenario_records, observed_ops, strict=True):
            expected = str(reference["expected_operation"])
            p_result = record["result"]
            governance = p_result.get("governance")
            governance_result = (
                str(governance.get("result"))
                if isinstance(governance, Mapping)
                else "EXECUTION_FAILURE"
            )
            governance_by_repetition.append(governance_result)
            reason_codes_by_repetition.append(
                sorted(str(code) for code in (governance or {}).get("reason_codes", []))
                if isinstance(governance, Mapping)
                else [str(record["result"].get("failure_reason_code", "EXECUTION_FAILURE"))]
            )
            if expected in confusion and observed in {"retain", "add", "replace", "hold"}:
                confusion[expected][observed] += 1
            governance_counts[governance_result] += 1
            if record["result"].get("execution_status") == "COMPLETED":
                operation_evaluable += 1
                operation_matches += observed == expected
                if expected in {"hold", "retain"}:
                    nonadaptation_evaluable += 1
                if expected in {"hold", "retain"} and observed in {
                    "add",
                    "replace",
                    "deactivate",
                    "adjust",
                    "mixed",
                }:
                    unnecessary += 1
                    scenario_unnecessary += 1
                if expected in {"add", "replace"}:
                    required_adaptation_evaluable += 1
                if expected in {"add", "replace"} and (
                    observed not in {"add", "replace"} or governance_result != "ACCEPT"
                ):
                    missed += 1
                    scenario_missed += 1
                if expected == "hold":
                    if observed == "hold" and governance_result == reference["expected_governance"]:
                        appropriate_holds += 1
                        scenario_appropriate_holds += 1
                    elif observed == "hold":
                        hold_governance_mismatches += 1
                        scenario_hold_governance_mismatches += 1
                    else:
                        missed_holds += 1
                        scenario_missed_holds += 1
                elif observed == "hold":
                    inappropriate_holds += 1
                    scenario_inappropriate_holds += 1
            duration_by_operation[observed].append(int(record["duration_ns"]))

        baseline_path = output_dir / "raw" / f"{scenario_id}_b0_synth.json"
        b0 = _read_json(baseline_path) if baseline_path.is_file() else None
        observed_candidates = [row["result"].get("candidate_sha256") for row in scenario_records]
        observed_plans = [
            (row["result"].get("operation_plan") or {}).get("plan_sha256")
            for row in scenario_records
        ]
        decision_signatures = {
            (
                _operation(row["result"]),
                (row["result"].get("governance") or {}).get("result"),
                (row["result"].get("operation_plan") or {}).get("plan_sha256"),
                row["result"].get("candidate_sha256"),
            )
            for row in scenario_records
        }
        p_differs_from_b0 = any(
            operation in {"add", "replace", "deactivate", "adjust", "mixed"}
            for operation in observed_ops
        )
        b0_difference_count += p_differs_from_b0
        combined_reason_codes = sorted(
            {code for repetition_codes in reason_codes_by_repetition for code in repetition_codes}
        )
        score_rows.append(
            {
                "scenario_id": scenario_id,
                "expected_operation": reference["expected_operation"],
                "expected_governance": reference["expected_governance"],
                "b0_synth_operation": b0["operation"] if b0 else "NOT_EVALUABLE",
                "b0_synth_coverage_status": (b0["coverage"]["status"] if b0 else "NOT_EVALUABLE"),
                "b0_synth_configuration_sha256": (
                    b0["initial_configuration_sha256"] if b0 else None
                ),
                "method_p_proposed_operation": (
                    Counter(observed_ops).most_common(1)[0][0] if observed_ops else "none"
                ),
                "method_p_observed_operations_by_repetition": observed_ops,
                "method_p_governance_by_repetition": governance_by_repetition,
                "actual_reason_codes": combined_reason_codes,
                "actual_reason_codes_by_repetition": reason_codes_by_repetition,
                "decision_repetition_consistent": len(decision_signatures) == 1,
                "candidate_configuration_sha256_by_repetition": observed_candidates,
                "operation_plan_sha256_by_repetition": observed_plans,
                "operation_match_count": sum(
                    _operation(row["result"]) == reference["expected_operation"]
                    for row in scenario_records
                    if row["result"].get("execution_status") == "COMPLETED"
                ),
                "operation_mismatch_count": sum(
                    _operation(row["result"]) != reference["expected_operation"]
                    for row in scenario_records
                    if row["result"].get("execution_status") == "COMPLETED"
                ),
                "operation_not_evaluable_count": sum(
                    row["result"].get("execution_status") != "COMPLETED" for row in scenario_records
                ),
                "correct_incorrect_not_evaluable": {
                    "correct": correct,
                    "incorrect": incorrect,
                    "not_evaluable": not_evaluable,
                },
                "unnecessary_adaptation_count": scenario_unnecessary,
                "missed_required_adaptation_count": scenario_missed,
                "hold_decisions": {
                    "appropriate": scenario_appropriate_holds,
                    "inappropriate": scenario_inappropriate_holds,
                    "missed_expected_hold": scenario_missed_holds,
                    "operation_hold_with_governance_mismatch": scenario_hold_governance_mismatches,
                },
                "b0_synth_differs_from_method_p": p_differs_from_b0,
                "duration_ns": [int(row["duration_ns"]) for row in scenario_records],
                "duration_ns_min": min(int(row["duration_ns"]) for row in scenario_records),
                "duration_ns_max": max(int(row["duration_ns"]) for row in scenario_records),
                "evidence_completeness": [
                    (row["result"].get("current_coverage") or {}).get("status", "NOT_EVALUABLE")
                    for row in scenario_records
                ],
                "raw_result_sha256": [row["raw_record_sha256"] for row in scenario_records],
                "bundle_sha256": scenario_records[0]["input_bundle_sha256"],
            }
        )

    total = len(records)
    execution_failures = sum(
        row["result"].get("execution_status") != "COMPLETED" for row in records
    )
    holds = governance_counts.get("HOLD", 0)
    decision_evaluable = all_counts["CORRECT"] + all_counts["INCORRECT"]
    results = {
        "schema_version": 1,
        "experiment_id": "MONO_E1_DEV_P_DECISIONS_V1",
        "reference_status": "AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT",
        "scientific_status_effect": SCIENTIFIC_STATUS_EFFECT,
        "reference_sha256": reference_digest,
        "scorer_source_commit_sha": _git("rev-parse", "HEAD"),
        "scorer_code_sha256": _sha256(Path(__file__)),
        "execution_manifest_sha256": _sha256(output_dir / "execution_manifest.json"),
        "raw_records_manifest_sha256": _sha256(output_dir / "raw_records_manifest.json"),
        "method_input_bundle_archive_sha256": execution_manifest[
            "method_input_bundle_archive_sha256"
        ],
        "source_commit_sha": _read_json(output_dir / "execution_manifest.json")[
            "source_commit_sha"
        ],
        "method_identity": _read_json(output_dir / "execution_manifest.json")["method_identity"],
        "scenario_count": len(score_rows),
        "technical_repetition_count": total,
        "summary_counts": {
            "correct": all_counts["CORRECT"],
            "incorrect": all_counts["INCORRECT"],
            "not_evaluable": all_counts["NOT_EVALUABLE"],
            "governance_hold": holds,
            "execution_failures": execution_failures,
        },
        "operation_decision_accuracy": {
            "correct_operation_count": operation_matches,
            "evaluable_execution_count": operation_evaluable,
            "not_evaluable_execution_count": execution_failures,
            "rate": operation_matches / operation_evaluable if operation_evaluable else None,
        },
        "combined_decision_accuracy": {
            "correct_count": all_counts["CORRECT"],
            "evaluable_execution_count": decision_evaluable,
            "not_evaluable_execution_count": all_counts["NOT_EVALUABLE"],
            "rate": all_counts["CORRECT"] / decision_evaluable if decision_evaluable else None,
        },
        "operation_confusion_matrix": {key: dict(value) for key, value in confusion.items()},
        "unnecessary_adaptation_rate": {
            "count": unnecessary,
            "eligible_nonadaptation_execution_count": nonadaptation_evaluable,
            "rate": unnecessary / nonadaptation_evaluable if nonadaptation_evaluable else None,
        },
        "missed_required_adaptation_rate": {
            "count": missed,
            "eligible_required_adaptation_execution_count": required_adaptation_evaluable,
            "rate": missed / required_adaptation_evaluable
            if required_adaptation_evaluable
            else None,
        },
        "hold_decision_counts": {
            "appropriate": appropriate_holds,
            "inappropriate": inappropriate_holds,
            "missed_expected_hold": missed_holds,
            "operation_hold_with_governance_mismatch": hold_governance_mismatches,
        },
        "governance_distribution": dict(sorted(governance_counts.items())),
        "execution_duration_by_observed_operation_ns": {
            key: {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
            }
            for key, values in sorted(duration_by_operation.items())
        },
        "b0_synth_vs_method_p": {
            "baseline_operation": "UNCHANGED_CONFIGURATION",
            "scenario_count": len(score_rows),
            "scenarios_with_configuration_change_proposal": b0_difference_count,
            "scenario_ids_with_configuration_change_proposal": [
                row["scenario_id"] for row in score_rows if row["b0_synth_differs_from_method_p"]
            ],
        },
        "scenario_results": score_rows,
        "interpretation_limits": [
            "Three repetitions are technical repetitions, not independent cases.",
            "AUTHOR_DECLARED labels are not independent ground truth.",
            (
                "TEST_ONLY policy and exact-pair proof do not establish production authority "
                "or scientific readiness."
            ),
            (
                "No Coverage_P, Coverage_ref, statistical significance, generalizable "
                "superiority, or DA01 claim is made."
            ),
        ],
    }
    _write_json(output_dir / "results_v1.json", results)
    report = _render_report(results, score_rows, holds, execution_failures)
    report_path = output_dir / "report_v1.md"
    report_path.write_text(report, encoding="utf-8")
    _write_json(
        output_dir / "score_manifest.json",
        {
            "schema_version": 1,
            "reference_sha256": reference_digest,
            "scorer_source_commit_sha": _git("rev-parse", "HEAD"),
            "scorer_code_sha256": _sha256(Path(__file__)),
            "execution_manifest_sha256": _sha256(output_dir / "execution_manifest.json"),
            "raw_manifest_sha256": _sha256(output_dir / "raw_records_manifest.json"),
            "scored_record_count": total,
            "result_sha256": _sha256(output_dir / "results_v1.json"),
            "report_sha256": _sha256(report_path),
        },
    )
    _write_checksum_inventory(output_dir)


def _render_report(
    results: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], holds: int, failures: int
) -> str:
    operation_accuracy = results["operation_decision_accuracy"]
    combined_accuracy = results["combined_decision_accuracy"]
    unnecessary_rate = results["unnecessary_adaptation_rate"]
    missed_rate = results["missed_required_adaptation_rate"]
    lines = [
        "# MONO_E1_DEV_P_DECISIONS_V1 — DEVELOPMENT report",
        "",
        "## Status and provenance",
        "",
        (
            "The synthetic experiment executed through the existing V3 verified-input path "
            "under TEST_ONLY trust. It is independent of official MONO-E1 A0.3→A0.4 execution."
        ),
        "",
        (
            f"- Scenarios: {results['scenario_count']}; technical Method P repetitions: "
            f"{results['technical_repetition_count']}; "
            f"B0_SYNTH baselines: {results['scenario_count']}"
        ),
        f"- Author-declared reference SHA-256: `{results['reference_sha256']}`",
        f"- Pre-registration source commit: `{results['source_commit_sha']}`",
        f"- Scorer source commit: `{results['scorer_source_commit_sha']}`",
        f"- Method version: `{results['method_identity']['method_version']}`",
        "- Reference scope: AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT",
        "",
        "## Observations",
        "",
        (
            "| Scenario | Expected op/gov | B0_SYNTH | Differs? | P operation / governance | "
            "Reason codes | Correct / incorrect / not evaluable | "
            "Unnecessary / missed | Duration min–max (ms) | Evidence completeness | "
            "Raw Method P SHA-256 digests |"
        ),
        "|---|---|---|---|---|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        governance = ", ".join(row["method_p_governance_by_repetition"])
        counts = row["correct_incorrect_not_evaluable"]
        duration_min = row["duration_ns_min"] / 1_000_000
        duration_max = row["duration_ns_max"] / 1_000_000
        reasons = ", ".join(row["actual_reason_codes"]) or "none"
        unnecessary = row["unnecessary_adaptation_count"]
        missed = row["missed_required_adaptation_count"]
        evidence = ", ".join(row["evidence_completeness"])
        digests = "<br>".join(row["raw_result_sha256"])
        lines.append(
            f"| {row['scenario_id']} | {row['expected_operation']} / "
            f"{row['expected_governance']} | {row['b0_synth_operation']} | "
            f"{row['b0_synth_differs_from_method_p']} | "
            f"{row['method_p_proposed_operation']} / {governance} | {reasons} | "
            f"{counts['correct']} / {counts['incorrect']} / {counts['not_evaluable']} | "
            f"{unnecessary} / {missed} | {duration_min:.2f}–{duration_max:.2f} | "
            f"{evidence} | {digests} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate descriptive metrics",
            "",
            (
                f"- Correct / incorrect / not evaluable: "
                f"{results['summary_counts']['correct']} / "
                f"{results['summary_counts']['incorrect']} / "
                f"{results['summary_counts']['not_evaluable']} of "
                f"{results['technical_repetition_count']} technical repetitions."
            ),
            (
                f"- Operation decision accuracy: {operation_accuracy['correct_operation_count']} / "
                f"{operation_accuracy['evaluable_execution_count']} = "
                f"{operation_accuracy['rate']} (execution failures: "
                f"{operation_accuracy['not_evaluable_execution_count']})."
            ),
            (
                f"- Combined operation/governance/semantic accuracy: "
                f"{combined_accuracy['correct_count']} / "
                f"{combined_accuracy['evaluable_execution_count']} = "
                f"{combined_accuracy['rate']} (not evaluable: "
                f"{combined_accuracy['not_evaluable_execution_count']})."
            ),
            (
                f"- Unnecessary adaptation: {unnecessary_rate['count']} / "
                f"{unnecessary_rate['eligible_nonadaptation_execution_count']} = "
                f"{unnecessary_rate['rate']}."
            ),
            (
                f"- Missed required adaptation: {missed_rate['count']} / "
                f"{missed_rate['eligible_required_adaptation_execution_count']} = "
                f"{missed_rate['rate']}."
            ),
            (
                f"- HOLD outcomes: governance HOLD={holds}; appropriate HOLD operation="
                f"{results['hold_decision_counts']['appropriate']}; inappropriate HOLD="
                f"{results['hold_decision_counts']['inappropriate']}; missed expected HOLD="
                f"{results['hold_decision_counts']['missed_expected_hold']}; HOLD operation "
                f"with registered-governance mismatch="
                f"{results['hold_decision_counts']['operation_hold_with_governance_mismatch']}."
            ),
            f"- Execution failures: {failures}.",
            (
                "- Repetition decision stability: "
                f"{sum(row['decision_repetition_consistent'] for row in rows)} / "
                f"{len(rows)} scenarios had identical operation, governance, plan digest, "
                "and candidate digest across technical repetitions."
            ),
            "- Operation confusion matrix (rows are author-declared expected operations):",
            "",
            "```json",
            json.dumps(results["operation_confusion_matrix"], indent=2, sort_keys=True),
            "```",
            "- Execution duration by observed operation (nanoseconds):",
            "",
            "```json",
            json.dumps(
                results["execution_duration_by_observed_operation_ns"],
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
            "## B0_SYNTH comparison",
            "",
            (
                "B0_SYNTH preserved each initial representation catalog and recorded the "
                "current after-state coverage assessment without semantic adaptation. Its "
                "operation is `UNCHANGED_CONFIGURATION`; it is not an official or historical "
                "B0. Method P proposals, governance outcomes, candidate validation, and "
                "coverage remain separate in `results_v1.json` and the raw traces."
            ),
            (
                "Scenarios with a Method P configuration-change proposal relative to B0_SYNTH: "
                + ", ".join(
                    results["b0_synth_vs_method_p"][
                        "scenario_ids_with_configuration_change_proposal"
                    ]
                )
            ),
            "",
            "## Reproduction and evidence",
            "",
            (
                "Run `execute` from the clean pre-registration commit, then run `score` on "
                "the resulting directory. `execute` never reads the reference. Scoring checks "
                "the frozen reference digest and every raw record, then writes the descriptive "
                "results."
            ),
            "",
            (
                "See `execution_manifest.json`, `raw_records_manifest.json`, `results_v1.json`, "
                "`raw/`, and `SHA256SUMS` for input, implementation, output and checksum "
                "evidence."
            ),
            "",
            "## Limitations and next step",
            "",
            (
                "All policy, evaluator, and exact-pair trust is synthetic TEST_ONLY evidence. "
                "Repeated runs reuse each scenario fixture and do not increase the independent "
                "sample count. Author-declared decisions are not independently validated labels. "
                "This experiment does not change P readiness, G1/G4, MONO-E1 `NO_GO`, or any "
                "DA01 authority."
            ),
            "",
            (
                "The next official MONO-E1 step remains resolving and documenting the "
                "reference-freeze gate, independent evaluator/source evidence, G1 completeness, "
                "and separate G4 authorization before any canonical B0/P execution."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _write_checksum_inventory(root: Path) -> None:
    entries = []
    for path in sorted(
        item for item in root.rglob("*") if item.is_file() and item.name != "SHA256SUMS"
    ):
        entries.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    (root / "SHA256SUMS").write_text("\n".join(entries) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    execute_parser = subparsers.add_parser("execute", help="run the preregistered Method P cases")
    execute_parser.add_argument("--output-dir", required=True, type=Path)
    score_parser = subparsers.add_parser(
        "score", help="compare raw runs with the frozen scorer reference"
    )
    score_parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    args.output_dir = args.output_dir.resolve()
    if args.command == "execute":
        _execute(args.output_dir)
    else:
        _score(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
