"""Source-bound evaluator adapters and TEST_ONLY evidence loading for Ψ."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed repository-owned evaluator CLI with explicit arguments
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.p_adaptation_evidence import (
    AdaptationEvidenceVerifierRegistry,
)
from experiments.execution.tooling.p_applicability import EvidenceLedger, EvidenceProof, ProofStatus
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3
from experiments.execution.tooling.p_semantic import pair_proof_subject

TEST_ONLY_VERIFIER_ID = "DEV_PSI_HMAC_EVIDENCE_TEST_ONLY_V1"
SOURCE_INVENTORY_VERIFIER_ID = "DEV_SOURCE_INVENTORY_READBACK_V1"
EVALUATOR_IDS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH")
EVALUATOR_CONFIGS = {
    "AC_PUBLIC_API": "architecture/acceptance/a1/public_api_v1.yaml",
    "AC_MODULE_GRAPH": "architecture/acceptance/a1/module_graph_v1.yaml",
}
EVALUATOR_SOURCE_ROOT = "architecture/acceptance/a1"


class TestOnlyHmacVerifier:
    """A run-local integrity verifier that never represents production authority."""

    trust_scope: Literal["TEST_ONLY"] = "TEST_ONLY"

    def __init__(self, key: bytes) -> None:
        if len(key) < 32:
            raise ContractValidationError("PSI_TEST_ONLY_VERIFIER_KEY_TOO_SHORT")
        self._key = bytes(key)

    def verify(self, verifier_id: str, content_sha256: str, signature: str) -> bool | None:
        if verifier_id != TEST_ONLY_VERIFIER_ID:
            return None
        expected = hmac.new(self._key, content_sha256.encode("ascii"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


class TestOnlyEvidenceTrustContext:
    """No policy authority is configured; only a run-local TEST_ONLY verifier exists."""

    trust_scope: Literal["TEST_ONLY"] = "TEST_ONLY"

    def __init__(self, key: bytes) -> None:
        verifier = TestOnlyHmacVerifier(key)
        self.adaptation_evidence_verifiers = AdaptationEvidenceVerifierRegistry(
            {TEST_ONLY_VERIFIER_ID: verifier}
        )

    def verify_charter(self, charter: Any, source: Any, evaluation_as_of: str) -> None:
        return None

    def verify_approval(
        self, policy: Any, charter: Any, source: Any, evaluation_as_of: str
    ) -> None:
        return None


def evaluator_source_artifacts(repository: Path) -> tuple[list[dict[str, str]], bytes, str]:
    """Return the exact source inventory and digest emitted by the A1 evaluator."""
    evaluator_root = repository / EVALUATOR_SOURCE_ROOT
    artifacts = [
        {"path": path.name, "sha256": _sha256_file(path)}
        for path in sorted(evaluator_root.glob("*.py"))
    ]
    if not artifacts:
        raise ContractValidationError("PSI_EVALUATOR_SOURCE_ARTIFACTS_MISSING")
    encoded = canonical_json_bytes(artifacts)
    return artifacts, encoded, sha256_bytes(encoded)


def create_test_only_sidecar(
    *,
    bundle: Any,
    pair_evidence: list[dict[str, Any]],
    pair_proofs: list[dict[str, Any]],
    artifact_bytes: Mapping[str, bytes],
    key: bytes,
) -> dict[str, Any]:
    """Create V2 evidence bound to the exact verified bundle under TEST_ONLY scope."""
    if len(key) < 32:
        raise ContractValidationError("PSI_TEST_ONLY_VERIFIER_KEY_TOO_SHORT")
    before_sha = str(bundle.snapshot["architecture"]["before_commit"])
    after_sha = str(bundle.snapshot["architecture"]["after_commit"])
    registry = bundle.snapshot["policy_registry"]
    source_ids = ("ARCH_AFTER", "ARCH_BEFORE", "P_CAPABILITIES", "P_TRACEABILITY")
    source_bindings = [
        {"source_id": source_id, "sha256": bundle.source_digests[source_id]}
        for source_id in source_ids
    ]
    source_bindings.sort(key=lambda row: row["source_id"])
    payload = {
        "evaluator_evidence": pair_evidence,
        "pair_proofs": pair_proofs,
        "artifact_bytes": [
            {
                "path": path,
                "sha256": sha256_bytes(content),
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
            for path, content in sorted(artifact_bytes.items())
        ],
        "fact_absence_proofs": [],
        "policy_inventories": [],
        "trace_inventory_proof": _undetermined_scoped_proof(
            {
                "claim_type": "trace_inventory",
                "trace_graph_sha256": bundle.trace_graph.graph_sha256,
                "input_bundle_sha256": bundle.manifest["bundle_sha256"],
            },
            str(registry["scope"]),
            (before_sha, after_sha),
            TEST_ONLY_VERIFIER_ID,
        ),
        "change_inventory_proof": _undetermined_scoped_proof(
            {
                "claim_type": "change_inventory",
                "snapshot_sha256": bundle.snapshot_validation.snapshot_digest,
                "input_bundle_sha256": bundle.manifest["bundle_sha256"],
                "policy_source_revision": bundle.manifest["policy_source_revision"],
                "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
            },
            str(registry["scope"]),
            (before_sha, after_sha),
            TEST_ONLY_VERIFIER_ID,
        ),
        "required_stages": {},
        "stage_contract_proof": _undetermined_scoped_proof(
            {
                "claim_type": "required_stages",
                "required_stages_sha256": sha256_bytes(canonical_json_bytes({})),
                "input_bundle_sha256": bundle.manifest["bundle_sha256"],
            },
            str(registry["scope"]),
            (after_sha,),
            TEST_ONLY_VERIFIER_ID,
        ),
        "adjustment_rules": [],
        "authorized_template_descriptor_sha256": [],
        "cost_model_proof": _undetermined_scoped_proof(
            {
                "claim_type": "cost_model_authority",
                "cost_model_sha256": sha256_bytes(canonical_json_bytes(bundle.cost_model)),
                "capabilities_sha256": bundle.source_digests["P_CAPABILITIES"],
                "input_bundle_sha256": bundle.manifest["bundle_sha256"],
            },
            str(registry["scope"]),
            (after_sha,),
            TEST_ONLY_VERIFIER_ID,
        ),
    }
    sidecar: dict[str, Any] = {
        "schema_version": 2,
        "contract_id": "P_ADAPTATION_EVIDENCE_V2",
        "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        "architecture_before_sha": before_sha,
        "architecture_after_sha": after_sha,
        "policy_source_revision": bundle.manifest["policy_source_revision"],
        "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
        "evaluation_as_of": bundle.snapshot["architecture"]["evaluation_as_of"],
        "scope": str(registry["scope"]),
        "source_bindings": source_bindings,
        "verifier_id": TEST_ONLY_VERIFIER_ID,
        "payload": payload,
    }
    content_sha256 = sha256_bytes(canonical_json_bytes(sidecar))
    sidecar["sidecar_sha256"] = content_sha256
    sidecar["signature"] = hmac.new(key, content_sha256.encode("ascii"), hashlib.sha256).hexdigest()
    return sidecar


def build_source_inventory_fact_ledger(bundle_path: Path) -> tuple[EvidenceLedger, dict[str, Any]]:
    """Recompute Git-tree module facts from the bundle's digest-pinned inventories."""
    manifest = verify_method_bundle_v3(bundle_path, expected_method_id="P")
    root = bundle_path.resolve(strict=True)
    records = {row["path"]: row for row in manifest["files"]}
    snapshot_path = root / "architecture-policy-snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    source_rows = {row["id"]: row for row in snapshot.get("sources", [])}
    facts = snapshot.get("facts", [])
    inventories: dict[str, tuple[str, list[str]]] = {}
    for state, source_id, path in (
        ("before", "ARCH_BEFORE", "architecture/before-inventory.json"),
        ("after", "ARCH_AFTER", "architecture/after-inventory.json"),
    ):
        if path not in records or source_id not in source_rows:
            raise ContractValidationError("PSI_SOURCE_INVENTORY_BINDING_MISSING")
        raw = (root / path).read_bytes()
        if sha256_bytes(raw) != records[path]["sha256"]:
            raise ContractValidationError("PSI_SOURCE_INVENTORY_DIGEST_MISMATCH")
        inventory = json.loads(raw)
        if not isinstance(inventory, Mapping):
            raise ContractValidationError("PSI_SOURCE_INVENTORY_REVISION_MISMATCH")
        architecture = snapshot["architecture"]
        expected_commit = (
            architecture["before_commit"] if state == "before" else architecture["after_commit"]
        )
        expected_tree = (
            manifest["before_tree_sha"] if state == "before" else manifest["after_tree_sha"]
        )
        file_rows = inventory.get("files")
        if (
            inventory.get("state") != state
            or inventory.get("schema_version") != "1.1"
            or inventory.get("commit_sha") != expected_commit
            or inventory.get("tree_sha") != expected_tree
            or source_rows[source_id].get("path") != path
            or source_rows[source_id].get("sha256") != records[path]["sha256"]
            or not isinstance(file_rows, list)
            or not file_rows
        ):
            raise ContractValidationError("PSI_SOURCE_INVENTORY_REVISION_MISMATCH")
        paths: list[str] = []
        for row in file_rows:
            if (
                not isinstance(row, Mapping)
                or not isinstance(row.get("path"), str)
                or not isinstance(row.get("git_blob_sha1"), str)
                or re.fullmatch(r"[a-f0-9]{40}", row["git_blob_sha1"]) is None
            ):
                raise ContractValidationError("PSI_SOURCE_INVENTORY_FILE_RECORD_INVALID")
            paths.append(row["path"])
        if paths != sorted(set(paths)):
            raise ContractValidationError("PSI_SOURCE_INVENTORY_FILE_LIST_INVALID")
        modules = _module_names_from_paths(paths)
        inventories[state] = (records[path]["sha256"], modules)

    fact_proofs: dict[str, EvidenceProof] = {}
    for fact in facts:
        if (
            not isinstance(fact, Mapping)
            or fact.get("method_id") != "git_tree_py_module_inventory_v1"
        ):
            continue
        predicate = fact.get("predicate")
        state = fact.get("state")
        source_ids = fact.get("source_ids")
        if predicate == "component.python_module_identity" and state in inventories:
            expected_sources = ("ARCH_BEFORE",) if state == "before" else ("ARCH_AFTER",)
            expected_value = inventories[str(state)][1]
        elif (
            predicate in {"component.module_added", "component.module_removed"} and state == "after"
        ):
            expected_sources = ("ARCH_AFTER", "ARCH_BEFORE")
            before, after = inventories["before"][1], inventories["after"][1]
            expected_value = (
                sorted(set(after) - set(before))
                if predicate.endswith("added")
                else sorted(set(before) - set(after))
            )
        else:
            continue
        if tuple(source_ids or ()) != expected_sources or fact.get("value") != expected_value:
            raise ContractValidationError("PSI_SOURCE_INVENTORY_FACT_MISMATCH")
        bindings = tuple(
            sorted(
                (source_id, inventories["before" if source_id == "ARCH_BEFORE" else "after"][0])
                for source_id in expected_sources
            )
        )
        fact_proofs[str(fact["id"])] = EvidenceProof(
            ProofStatus.VALID,
            sha256_bytes(canonical_json_bytes(dict(fact))),
            bindings,
            SOURCE_INVENTORY_VERIFIER_ID,
            ("SOURCE_INVENTORY_READBACK",),
        )
    return (
        EvidenceLedger(fact_proofs, {}, {}),
        {
            "trust_scope": "DEVELOPMENT_SOURCE_INVENTORY_READBACK_ONLY",
            "verifier_id": SOURCE_INVENTORY_VERIFIER_ID,
            "verified_fact_ids": sorted(fact_proofs),
            "unverified_policy_proofs": True,
            "unverified_completeness_proofs": True,
        },
    )


def run_fresh_evaluator(
    *,
    repository: Path,
    source_checkout: Path,
    evaluator_id: str,
    architecture_state: str,
    source_commit_sha: str,
    output_directory: Path,
) -> dict[str, Any]:
    """Execute one evaluator process against a clean exact-revision worktree."""
    if evaluator_id not in EVALUATOR_IDS:
        raise ProtocolError("PSI_EVALUATOR_ID_UNSUPPORTED")
    config_relative = EVALUATOR_CONFIGS[evaluator_id]
    config_path = repository / config_relative
    state_manifest = f"architecture/states/{architecture_state}.yaml"
    output_directory.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC)
    start_perf = time.perf_counter()
    cli_path = repository / "architecture/acceptance/a1/cli.py"
    if not cli_path.is_file():
        raise ProtocolError("PSI_EVALUATOR_IMPLEMENTATION_MISSING")
    command = [
        sys.executable,
        str(cli_path),
        evaluator_id,
        "--repo-root",
        str(source_checkout),
        "--config",
        str(config_path),
        "--state-manifest",
        state_manifest,
        "--architecture-state",
        architecture_state,
        "--expected-source-sha",
        source_commit_sha,
    ]
    environment = {
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
        "PYTHONPATH": str(repository),
    }
    result = subprocess.run(  # nosec B603 # noqa: S603 - fixed repository-owned evaluator CLI
        command,
        cwd=source_checkout,
        env=environment,
        check=False,
        capture_output=True,
        timeout=180,
    )
    duration_ms = round((time.perf_counter() - start_perf) * 1000, 3)
    ended = datetime.now(UTC)
    if result.returncode not in {0, 1, 2, 3}:
        raise ProtocolError("PSI_EVALUATOR_PROCESS_FAILED")
    stdout_path = output_directory / "stdout.bin"
    stderr_path = output_directory / "stderr.bin"
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    try:
        evidence = json.loads(result.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError("PSI_EVALUATOR_OUTPUT_INVALID_JSON") from error
    if not isinstance(evidence, dict):
        raise ProtocolError("PSI_EVALUATOR_OUTPUT_INVALID_SHAPE")
    output_path = output_directory / "evaluator-output.json"
    output_path.write_bytes(pretty_json_bytes(evidence))
    return {
        "evaluator_id": evaluator_id,
        "architecture_state": architecture_state,
        "source_commit_sha": source_commit_sha,
        "source_tree_sha": _git_text(source_checkout, "rev-parse", "HEAD^{tree}"),
        "target_application_tree_sha": _git_text(source_checkout, "rev-parse", "HEAD:app"),
        "configuration_path": config_relative,
        "configuration_sha256": _sha256_file(config_path),
        "evaluator_source_sha256": evidence.get("evaluator", {}).get("source_digest"),
        "target_state_manifest_sha256": evidence.get("architecture", {}).get("manifest_digest"),
        "target_source_sha256": evidence.get("architecture", {}).get("target_source_sha"),
        "execution_status": evidence.get("result", {}).get("execution_status"),
        "compliance": evidence.get("result", {}).get("compliance"),
        "process_exit_code": result.returncode,
        "stdout_sha256": sha256_bytes(result.stdout),
        "stderr_sha256": sha256_bytes(result.stderr),
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
        "duration_ms": duration_ms,
        "output_path": output_path.relative_to(output_directory.parents[3]).as_posix(),
        "stdout_path": stdout_path.relative_to(output_directory.parents[3]).as_posix(),
        "stderr_path": stderr_path.relative_to(output_directory.parents[3]).as_posix(),
        "evidence": evidence,
        "raw_stdout": result.stdout,
        "raw_stderr": result.stderr,
    }


def adapt_evaluator_evidence(
    *,
    representation: Mapping[str, Any],
    obligation_id: str,
    run: Mapping[str, Any],
    artifact_refs: list[dict[str, str]],
    coverage_verification: Mapping[str, Any],
) -> dict[str, Any]:
    """Map only observed evaluator output and explicit unknown semantic fields."""
    evidence = run["evidence"]
    architecture = evidence["architecture"]
    source_scope = evidence["source_scope"]
    evaluator = evidence["evaluator"]
    result = evidence["result"]
    modules = source_scope.get("modules", [])
    expected_modules = sorted(
        str(row["name"])
        for row in modules
        if isinstance(row, Mapping) and row.get("expected") is True
    )
    resolved_modules = sorted(
        str(row["name"])
        for row in modules
        if isinstance(row, Mapping) and row.get("discovered") is True
    )
    _, _, _, reported_edge_count, _ = _inspection_scope_values(evidence)
    coverage_counts = coverage_verification.get("counts")
    if (
        coverage_verification.get("evaluator_id") != evaluator.get("id")
        or coverage_verification.get("architecture_state") != architecture.get("state")
        or not isinstance(coverage_counts, Mapping)
        or not isinstance(coverage_verification.get("expected_subjects"), list)
        or not isinstance(coverage_verification.get("inspected_subjects"), list)
    ):
        raise ContractValidationError("PSI_ADAPTER_INDEPENDENT_SCOPE_MISMATCH")
    expected_subjects = coverage_verification["expected_subjects"]
    inspected_subjects = coverage_verification["inspected_subjects"]
    measured_count = coverage_counts.get("inspected_count")
    if type(measured_count) is not int:
        raise ContractValidationError("PSI_ADAPTER_INDEPENDENT_SCOPE_MISMATCH")
    inspection_unit = str(coverage_verification.get("inspection_unit"))
    # V2 file-scope evidence records dependency edges in the bound inspection
    # artifact; this legacy scalar remains meaningful only for edge scope.
    inspected_edge_count = reported_edge_count if inspection_unit == "dependency_edge" else None
    output_record = next(
        (item for item in artifact_refs if item["path"].endswith("evaluator-output.json")), None
    )
    if output_record is None:
        raise ContractValidationError("PSI_EVALUATOR_OUTPUT_ARTIFACT_MISSING")
    scope_record = next(
        (item for item in artifact_refs if item["path"].endswith("inspection-scope.json")), None
    )
    if scope_record is None:
        raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_ARTIFACT_MISSING")
    return {
        "schema_version": 2,
        "representation_id": representation["id"],
        "architecture_source_sha": architecture["target_source_sha"],
        "evaluator_id": evaluator["id"],
        "infrastructure_status": "completed"
        if run["execution_status"] == "COMPLETED"
        else "infrastructure_failure",
        "process_exit_code": run["process_exit_code"],
        "configured_targets": sorted(f"app.modules.{name}" for name in expected_modules),
        "resolved_targets": sorted(f"app.modules.{name}" for name in resolved_modules),
        "inspected_subjects": inspected_subjects,
        "missing_targets": sorted(set(expected_modules) - set(resolved_modules)),
        "inspected_edge_count": inspected_edge_count,
        "inspection_scope": {
            "unit": inspection_unit,
            "expected_subjects": expected_subjects,
            "measured_count": measured_count,
            "evidence_artifact": scope_record,
        },
        "stage_applicable": (
            representation.get("stage") == "ci_test"
            and architecture.get("state") == run["architecture_state"]
            and architecture.get("source_sha_status") == "MATCHED"
            and evidence.get("applicability") == "ACTIVE"
        ),
        "semantic_compatible": None,
        "mapping_resolved": (
            evaluator.get("id") == obligation_id
            and evaluator.get("obligation_id") == obligation_id
            and obligation_id in representation.get("covers", [])
        ),
        "evidence_contract_satisfied": (
            result.get("execution_status") == "COMPLETED"
            and architecture.get("manifest_state_status") == "MATCHED"
            and architecture.get("source_sha_status") == "MATCHED"
            and coverage_verification.get("source_inspection_status") == "COMPLETE"
            and (
                coverage_verification.get("dependency_analysis") is None
                or coverage_verification["dependency_analysis"].get(
                    "static_relationship_comparison"
                )
                == "MATCHED"
            )
            and bool(inspected_subjects)
            and len(artifact_refs) >= 3
        ),
        "adequacy_proven": False,
        "evidence_artifacts": artifact_refs,
        "stdout_sha256": run["stdout_sha256"],
        "stderr_sha256": run["stderr_sha256"],
        "started_at_utc": run["started_at_utc"],
        "ended_at_utc": run["ended_at_utc"],
        "failure_reason_code": None
        if run["execution_status"] == "COMPLETED"
        else "EVALUATOR_EXECUTION_INCOMPLETE",
    }


def adapt_legacy_evaluator_evidence(
    *,
    representation: Mapping[str, Any],
    obligation_id: str,
    run: Mapping[str, Any],
    artifact_refs: list[dict[str, str]],
) -> dict[str, Any]:
    """Reconstruct the original evidence projection for existing run archives."""
    evidence = run["evidence"]
    architecture = evidence["architecture"]
    source_scope = evidence["source_scope"]
    evaluator = evidence["evaluator"]
    result = evidence["result"]
    modules = source_scope.get("modules", [])
    expected_modules = sorted(
        str(row["name"])
        for row in modules
        if isinstance(row, Mapping) and row.get("expected") is True
    )
    resolved_modules = sorted(
        str(row["name"])
        for row in modules
        if isinstance(row, Mapping) and row.get("discovered") is True
    )
    inspection_unit, inspected, measured_count, inspected_edge_count, _ = _inspection_scope_values(
        evidence
    )
    scope_record = next(
        (item for item in artifact_refs if item["path"].endswith("inspection-scope.json")), None
    )
    if scope_record is None:
        raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_ARTIFACT_MISSING")
    return {
        "schema_version": 1,
        "representation_id": representation["id"],
        "architecture_source_sha": architecture["target_source_sha"],
        "evaluator_id": evaluator["id"],
        "infrastructure_status": "completed"
        if run["execution_status"] == "COMPLETED"
        else "infrastructure_failure",
        "process_exit_code": run["process_exit_code"],
        "configured_targets": sorted(f"app.modules.{name}" for name in expected_modules),
        "resolved_targets": sorted(f"app.modules.{name}" for name in resolved_modules),
        "inspected_subjects": inspected,
        "missing_targets": sorted(set(expected_modules) - set(resolved_modules)),
        "inspected_edge_count": inspected_edge_count,
        "inspection_scope": {
            "unit": inspection_unit,
            "expected_subjects": inspected,
            "measured_count": measured_count,
            "evidence_artifact": scope_record,
        },
        "stage_applicable": (
            representation.get("stage") == "ci_test"
            and architecture.get("state") == run["architecture_state"]
            and architecture.get("source_sha_status") == "MATCHED"
            and evidence.get("applicability") == "ACTIVE"
        ),
        "semantic_compatible": None,
        "mapping_resolved": (
            evaluator.get("id") == obligation_id
            and evaluator.get("obligation_id") == obligation_id
            and obligation_id in representation.get("covers", [])
        ),
        "evidence_contract_satisfied": (
            result.get("execution_status") == "COMPLETED"
            and architecture.get("manifest_state_status") == "MATCHED"
            and architecture.get("source_sha_status") == "MATCHED"
            and source_scope.get("complete") is True
            and bool(inspected)
            and len(artifact_refs) >= 3
        ),
        "adequacy_proven": False,
        "evidence_artifacts": artifact_refs,
        "stdout_sha256": run["stdout_sha256"],
        "stderr_sha256": run["stderr_sha256"],
        "started_at_utc": run["started_at_utc"],
        "ended_at_utc": run["ended_at_utc"],
        "failure_reason_code": None
        if run["execution_status"] == "COMPLETED"
        else "EVALUATOR_EXECUTION_INCOMPLETE",
    }


def build_inspection_scope_artifact(
    evidence: Mapping[str, Any],
    evaluator_output_sha256: str,
    coverage_verification: Mapping[str, Any],
) -> dict[str, Any]:
    """Project the independently verified source scope into the typed contract."""
    source_scope = evidence.get("source_scope")
    source_bindings = coverage_verification.get("evidence_sources")
    if (
        not isinstance(source_scope, Mapping)
        or not isinstance(source_bindings, Mapping)
        or re.fullmatch(r"[a-f0-9]{64}", evaluator_output_sha256) is None
        or coverage_verification.get("evaluator_id") != evidence.get("evaluator", {}).get("id")
        or source_bindings.get("evaluator_output_sha256") != evaluator_output_sha256
        or source_bindings.get("source_scope_sha256")
        != sha256_bytes(canonical_json_bytes(dict(source_scope)))
    ):
        raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
    counts = coverage_verification.get("counts")
    if not isinstance(counts, Mapping) or type(counts.get("inspected_count")) is not int:
        raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
    diagnostics = evidence.get("diagnostics")
    edges = diagnostics.get("edges") if isinstance(diagnostics, Mapping) else None
    return {
        "schema_version": 2,
        "inspection_unit": "file",
        "expected_subjects": coverage_verification["expected_subjects"],
        "inspected_subjects": coverage_verification["inspected_subjects"],
        "measured_count": counts["inspected_count"],
        "source_evaluator_output_sha256": evaluator_output_sha256,
        "source_scope_sha256": source_bindings["source_scope_sha256"],
        "observed_edges": edges if isinstance(edges, list) else None,
    }


def build_legacy_inspection_scope_artifact(
    evidence: Mapping[str, Any], evaluator_output_sha256: str
) -> dict[str, Any]:
    """Reconstruct the original V1 projection for historical V1/V2 readback."""
    source_scope = evidence.get("source_scope")
    if (
        not isinstance(source_scope, Mapping)
        or re.fullmatch(r"[a-f0-9]{64}", evaluator_output_sha256) is None
    ):
        raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
    unit, subjects, measured_count, _, observed_edges = _inspection_scope_values(evidence)
    return {
        "schema_version": 1,
        "inspection_unit": unit,
        "expected_subjects": subjects,
        "inspected_subjects": subjects,
        "measured_count": measured_count,
        "source_evaluator_output_sha256": evaluator_output_sha256,
        "source_scope_sha256": sha256_bytes(canonical_json_bytes(dict(source_scope))),
        "observed_edges": observed_edges,
    }


def _inspection_scope_values(
    evidence: Mapping[str, Any],
) -> tuple[str, list[str], int, int | None, list[dict[str, Any]] | None]:
    source_scope = evidence.get("source_scope")
    if not isinstance(source_scope, Mapping) or source_scope.get("complete") is not True:
        raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
    inspected_paths = source_scope.get("inspected_paths")
    file_digests = source_scope.get("source_file_digests")
    if not isinstance(inspected_paths, list) or not isinstance(file_digests, list):
        raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
    paths = [path for path in inspected_paths if isinstance(path, str)]
    digest_paths = [
        row.get("path")
        for row in file_digests
        if isinstance(row, Mapping) and isinstance(row.get("path"), str)
    ]
    if (
        len(paths) != len(inspected_paths)
        or len(digest_paths) != len(file_digests)
        or not paths
        or paths != sorted(set(paths))
        or digest_paths != paths
        or any(
            not isinstance(row, Mapping)
            or re.fullmatch(r"[a-f0-9]{64}", str(row.get("sha256"))) is None
            for row in file_digests
        )
    ):
        raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")

    diagnostics = evidence.get("diagnostics")
    edges = diagnostics.get("edges") if isinstance(diagnostics, Mapping) else None
    if isinstance(edges, list) and edges:
        subjects: list[str] = []
        normalized_edges: list[dict[str, Any]] = []
        for edge in edges:
            if (
                not isinstance(edge, Mapping)
                or not isinstance(edge.get("from"), str)
                or not isinstance(edge.get("to"), str)
                or not isinstance(edge.get("references"), list)
                or not edge["references"]
            ):
                raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
            for reference in edge["references"]:
                if not isinstance(reference, Mapping) or reference.get("source_path") not in paths:
                    raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
            subject = f"{edge['from']}->{edge['to']}"
            if subject in subjects:
                raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
            subjects.append(subject)
            normalized_edges.append(dict(edge))
        if subjects != sorted(subjects):
            raise ContractValidationError("PSI_EVALUATOR_INSPECTION_SCOPE_UNRESOLVED")
        return "dependency_edge", subjects, len(subjects), len(subjects), normalized_edges
    return "file", paths, len(paths), None, None


def _undetermined_scoped_proof(
    subject: Mapping[str, Any],
    scope: str,
    architecture_shas: tuple[str, ...],
    verifier_id: str,
) -> dict[str, Any]:
    return {
        "status": "UNDETERMINED",
        "subject_sha256": sha256_bytes(canonical_json_bytes(dict(subject))),
        "scope": scope,
        "architecture_source_shas": list(architecture_shas),
        "verifier_id": verifier_id,
        "source_bindings": [],
        "evidence_refs": [],
    }


def _module_names_from_paths(paths: list[str]) -> list[str]:
    if paths != sorted(set(paths)):
        raise ContractValidationError("PSI_SOURCE_INVENTORY_FILE_LIST_INVALID")
    modules: set[str] = set()
    for path in paths:
        parts = Path(path).parts
        if not parts or parts[0] != "app" or not path.endswith(".py"):
            raise ContractValidationError("PSI_SOURCE_INVENTORY_PATH_INVALID")
        module_parts = list(parts[1:-1]) + [Path(path).stem]
        if module_parts[-1] == "__init__":
            module_parts.pop()
        modules.add("app" if not module_parts else f"app.{'.'.join(module_parts)}")
    return sorted(modules)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_text(repository: Path, *arguments: str) -> str:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("PSI_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # nosec B603 # noqa: S603 - fixed Git worktree commands
        [git_binary, *arguments],  # nosec B603 - fixed Git subcommands and repository paths
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


__all__ = [
    "EVALUATOR_CONFIGS",
    "EVALUATOR_IDS",
    "SOURCE_INVENTORY_VERIFIER_ID",
    "TEST_ONLY_VERIFIER_ID",
    "TestOnlyEvidenceTrustContext",
    "adapt_evaluator_evidence",
    "build_legacy_inspection_scope_artifact",
    "build_inspection_scope_artifact",
    "build_source_inventory_fact_ledger",
    "create_test_only_sidecar",
    "evaluator_source_artifacts",
    "pair_proof_subject",
    "run_fresh_evaluator",
]
