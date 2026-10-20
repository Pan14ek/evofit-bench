"""Execute the bounded PILOT-02 A0.1 profile and existing Method P pipeline."""

from __future__ import annotations

import argparse
import base64
import binascii
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess  # nosec B404 - fixed Git/evaluator argv, no shell
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.p_adaptation import (
    PILOT02_PROFILE_PINS,
    run_adaptation,
    verify_v3_p_bundle,
)
from experiments.execution.tooling.p_applicability import (
    EvidenceLedger,
    load_and_validate_ruleset,
)
from experiments.execution.tooling.p_input_validation import (
    ValidationStatus,
    load_fact_vocabulary,
    load_verified_source_manifest,
)
from experiments.execution.tooling.p_policy_source_v3 import (
    export_method_inputs_v3,
    package_policy_source_v3,
    verify_method_bundle_v3,
)
from experiments.execution.tooling.p_semantic import assess_pair
from experiments.pilots.pilot02_testonly_execution import (
    Pilot02TestOnlyTrustContext,
    build_adaptation_sidecar,
    build_testonly_evidence_ledger,
    create_testonly_policy_source,
    testonly_completeness_verifier,
)
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
PILOT02_ASSUMPTIONS_PATH = ROOT / "experiments/pilots/PILOT_02_DEVELOPMENT_ASSUMPTIONS_V1.json"


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


def _exp02_execution_evidence_admission(
    *, sidecar_supplied: bool, trust_scope: str | None
) -> tuple[str, bool]:
    """Report verified TEST_ONLY execution admission separately from pair proof."""
    admitted = sidecar_supplied and trust_scope == "TEST_ONLY"
    status = "admitted_execution_evidence" if admitted else "not_admitted"
    return status, admitted


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
    version = profile.get("schema_version")
    pin = PILOT02_PROFILE_PINS.get(version) if isinstance(version, int) else None
    if pin is None:
        raise ProtocolError("PILOT02_PROFILE_VERSION_UNSUPPORTED")
    definition_path, definition_sha256, _ = pin
    references: dict[str, str] = {
        definition_path: definition_sha256,
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
    for binding in profile.get("parent_evaluator_bindings", []):
        for item in [
            binding["evaluator_artifact"],
            *binding["evaluator_source_artifacts"],
        ]:
            path, digest = str(item["path"]), str(item["sha256"])
            previous = references.get(path)
            if previous is not None and previous != digest:
                raise ProtocolError("PILOT02_PROFILE_ARTIFACT_CONFLICT")
            references[path] = digest
    parent_catalog = profile.get("parent_representation_catalog_artifact")
    if isinstance(parent_catalog, dict):
        path, digest = str(parent_catalog["path"]), str(parent_catalog["sha256"])
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
        "path": definition_path,
        "sha256": definition_sha256,
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
    return cast(dict[str, Any], manifest)


def _install_testonly_cost_model(
    bundle_dir: Path,
    profile: dict[str, Any],
    assumptions: dict[str, Any],
) -> dict[str, Any]:
    """Pin only the addendum's bounded TEST_ONLY planning cost assumptions."""
    manifest_path = bundle_dir / "method_input_v3.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    capabilities_path = bundle_dir / "fitness/evaluator-capabilities.json"
    capabilities = json.loads(capabilities_path.read_text(encoding="utf-8"))
    target_ids = {
        str(item["representation"]["evaluator_artifact"]["sha256"])
        for mapping in profile["mappings"]
        for item in [mapping["candidate_template"]]
    }
    cost = assumptions["candidate_cost_model"]
    capabilities["p_cost_model_v1"] = {
        "schema_version": 1,
        "model_version": str(cost["model_id"]),
        "authority_status": "TEST_ONLY",
        "unit": str(cost["unit"]),
        "max_incremental_cost": cost["maximum_incremental_cost"],
        "max_search_nodes": cost["maximum_search_nodes"],
        "candidate_costs": {
            digest: cost["cost_per_profile_template"] for digest in sorted(target_ids)
        },
    }
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
    return cast(dict[str, Any], manifest)


def _configured_import_targets(configuration_bytes: bytes) -> set[str]:
    """Read the module targets actually named by one pinned Import Linter file."""
    document = tomllib.loads(configuration_bytes.decode("utf-8"))
    section = document.get("tool", {}).get("importlinter", {})
    targets: set[str] = set()
    contracts = section.get("contracts", []) if isinstance(section, dict) else []
    for contract in contracts:
        if not isinstance(contract, dict):
            continue
        for key in ("source_modules", "forbidden_modules"):
            targets.update(item for item in contract.get(key, []) if isinstance(item, str))
        layers = contract.get("layers", [])
        for layer in layers:
            if isinstance(layer, str):
                targets.add(layer)
            elif isinstance(layer, list):
                targets.update(item for item in layer if isinstance(item, str))
    return targets


def _after_module_names(bundle_root: Path) -> set[str]:
    """Derive module identities from the exact after-source files in the P bundle."""
    source_root = bundle_root / "architecture/after"
    modules: set[str] = set()
    for path in source_root.rglob("*.py"):
        relative = path.relative_to(source_root)
        parts = list(relative.parts[:-1]) + [path.stem]
        if parts[-1] == "__init__":
            parts.pop()
        modules.add("app" if not parts else "app." + ".".join(parts))
    return modules


def _b0_pair_evidence(
    *,
    bundle: Any,
    output_dir: Path,
    evaluation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Bind the actual B0 process and assess only its exact current pair scope."""
    representation = next(
        row for row in bundle.representations if row.get("id") == "REP_A0_ARCH_CI_LAYERING"
    )
    config_path = "fitness/a0-importlinter.toml"
    config_records = [
        row
        for row in bundle.manifest.get("files", [])
        if isinstance(row, dict) and row.get("path") == config_path
    ]
    if len(config_records) != 1 or config_records[0].get("sha256") != FROZEN_B0_EVALUATOR_SHA256:
        raise ValueError("Pinned B0 evaluator configuration bytes are unavailable")
    config_bytes = (bundle.root / config_path).read_bytes()
    if sha256_bytes(config_bytes) != FROZEN_B0_EVALUATOR_SHA256:
        raise ProtocolError("PILOT02_FROZEN_B0_BUNDLE_CONFIGURATION_MISMATCH")
    configured = sorted(_configured_import_targets(config_bytes))
    resolved_set = _after_module_names(bundle.root)
    resolved = sorted(set(configured) & resolved_set)
    missing = sorted(set(configured) - resolved_set)

    artifact_bytes: dict[str, bytes] = {}
    references: list[dict[str, str]] = []
    for key in ("stdout", "stderr"):
        reference = evaluation[key]
        relative = str(reference["path"])
        content = (output_dir / relative).read_bytes()
        digest = sha256_bytes(content)
        artifact_bytes[relative] = content
        references.append({"path": relative, "sha256": digest})
    stdout = artifact_bytes[str(evaluation["stdout"]["path"])]
    stderr = artifact_bytes[str(evaluation["stderr"]["path"])]
    process_completed = isinstance(evaluation.get("exit_status"), int)
    output_text = (stdout + b"\n" + stderr).decode("utf-8", errors="replace").lower()
    output_confirmed_missing = (
        [target for target in missing if target.lower() in output_text]
        if process_completed and evaluation.get("exit_status") != 0
        else []
    )
    unresolved_missing = sorted(set(missing) - set(output_confirmed_missing))
    evaluation["scope_diagnostics"] = {
        "configured_targets": configured,
        "source_resolved_targets": resolved,
        "source_missing_targets": missing,
        "output_confirmed_missing_targets": output_confirmed_missing,
        "unresolved_missing_targets": unresolved_missing,
        "interpretation": "TEST_ONLY evaluator-scope compatibility only",
    }
    evidence = {
        "schema_version": 1,
        "representation_id": str(representation["id"]),
        "architecture_source_sha": str(bundle.snapshot["architecture"]["after_commit"]),
        "evaluator_id": str(representation["evaluator"]),
        "infrastructure_status": "completed" if process_completed else "infrastructure_failure",
        "process_exit_code": evaluation.get("exit_status"),
        "configured_targets": configured,
        "resolved_targets": resolved,
        "inspected_subjects": resolved,
        "missing_targets": output_confirmed_missing,
        "inspected_edge_count": None,
        "stage_applicable": True,
        "semantic_compatible": False if output_confirmed_missing else None,
        "mapping_resolved": not bool(output_confirmed_missing),
        "evidence_contract_satisfied": not bool(output_confirmed_missing),
        "adequacy_proven": False,
        "evidence_artifacts": references,
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
    }
    return evidence, artifact_bytes


def _profile_artifact_binding_errors(
    profile: dict[str, Any],
    mapping: dict[str, Any],
    source_revision: str,
) -> list[str]:
    """Verify profile configuration and evaluator artifacts against the pinned source."""
    representation = mapping.get("candidate_template", {}).get("representation", {})
    references = [
        mapping.get("configuration_artifact"),
        *mapping.get("evaluator_source_artifacts", []),
        representation.get("evaluator_artifact"),
    ]
    embedded = profile.get("embedded_evaluator_artifacts", [])
    errors: list[str] = []
    for reference in references:
        if not isinstance(reference, dict):
            errors.append("profile_artifact_reference_invalid")
            continue
        path = str(reference.get("path", ""))
        digest = str(reference.get("sha256", ""))
        matches = [row for row in embedded if isinstance(row, dict) and row.get("path") == path]
        if len(matches) != 1:
            errors.append(f"profile_artifact_inventory_mismatch:{path}")
            continue
        record = matches[0]
        try:
            content = base64.b64decode(str(record.get("content_base64", "")), validate=True)
            source_content = _source_blob(source_revision, path)
        except (ValueError, binascii.Error, OSError, subprocess.CalledProcessError):
            errors.append(f"profile_artifact_source_unavailable:{path}")
            continue
        if (
            record.get("sha256") != digest
            or record.get("size_bytes") != len(content)
            or sha256_bytes(content) != digest
            or sha256_bytes(source_content) != digest
        ):
            errors.append(f"profile_artifact_digest_mismatch:{path}")
    for binding in profile.get("parent_evaluator_bindings", []):
        if not isinstance(binding, dict):
            errors.append("profile_parent_binding_invalid")
            continue
        for reference in [
            binding.get("evaluator_artifact"),
            *binding.get("evaluator_source_artifacts", []),
        ]:
            if not isinstance(reference, dict):
                errors.append("profile_parent_artifact_reference_invalid")
                continue
            path = str(reference.get("path", ""))
            digest = str(reference.get("sha256", ""))
            matches = [row for row in embedded if isinstance(row, dict) and row.get("path") == path]
            if len(matches) != 1:
                errors.append(f"profile_artifact_inventory_mismatch:{path}")
                continue
            record = matches[0]
            try:
                content = base64.b64decode(str(record.get("content_base64", "")), validate=True)
                source_content = _source_blob(source_revision, path)
            except (ValueError, binascii.Error, OSError, subprocess.CalledProcessError):
                errors.append(f"profile_artifact_source_unavailable:{path}")
                continue
            if (
                record.get("sha256") != digest
                or sha256_bytes(content) != digest
                or sha256_bytes(source_content) != digest
            ):
                errors.append(f"profile_artifact_digest_mismatch:{path}")
    return sorted(set(errors))


def _candidate_profile_binding_errors(
    *,
    profile: dict[str, Any],
    candidate: dict[str, Any],
    mapping: dict[str, Any],
    candidate_rows: list[Any],
    source_revision: str,
    after_tree_sha: str,
    input_bundle_sha256: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Require the materialized candidate row to match its exact source profile."""
    template = mapping["candidate_template"]["representation"]
    representation_id = str(template["id"])
    errors: list[str] = []
    matching_rows = [
        row
        for row in candidate_rows
        if isinstance(row, dict) and row.get("id") == representation_id
    ]
    if len(matching_rows) != 1:
        errors.append("candidate_row_missing_or_duplicated")
        candidate_row = None
    else:
        candidate_row = matching_rows[0]

    if candidate.get("architecture_source_sha") != source_revision:
        errors.append("candidate_source_revision_mismatch")
    if profile.get("architecture_source_sha") != source_revision:
        errors.append("profile_source_revision_mismatch")
    if profile.get("a0_1_app_tree_sha") != after_tree_sha:
        errors.append("profile_source_tree_mismatch")
    if candidate.get("input_bundle_sha256") != input_bundle_sha256:
        errors.append("candidate_input_bundle_mismatch")

    if candidate_row is not None:
        fields = (
            "id",
            "active",
            "criterion",
            "stage",
            "evaluator",
            "evaluator_artifact",
            "covers",
            "applicability_scope",
            "evidence_contract",
        )
        for field in fields:
            if candidate_row.get(field) != template.get(field):
                errors.append(f"candidate_row_field_mismatch:{field}")
        if candidate_row != template:
            errors.append("candidate_row_template_mismatch")

    config_reference = mapping.get("configuration_artifact", {})
    contract = template.get("evidence_contract", {})
    if not isinstance(config_reference, dict) or not isinstance(contract, dict):
        errors.append("profile_configuration_binding_invalid")
    else:
        expected_config_digest = config_reference.get("sha256")
        if contract.get("configuration_artifact_sha256") != expected_config_digest:
            errors.append("profile_configuration_digest_mismatch")
        if candidate_row is not None:
            candidate_contract = candidate_row.get("evidence_contract")
            if (
                not isinstance(candidate_contract, dict)
                or candidate_contract.get("configuration_artifact_sha256") != expected_config_digest
            ):
                errors.append("candidate_configuration_digest_mismatch")

    scope = template.get("applicability_scope", {})
    if (
        mapping.get("source_scope_id") != scope.get("scope_id")
        or mapping.get("architecture_scope") != scope.get("architecture_scope")
        or mapping.get("obligation_id") not in template.get("covers", [])
    ):
        errors.append("profile_scope_or_obligation_binding_mismatch")

    profile_definition = profile.get("profile_definition_artifact")
    version = profile.get("schema_version")
    pin = PILOT02_PROFILE_PINS.get(version) if isinstance(version, int) else None
    if (
        pin is None
        or not isinstance(profile_definition, dict)
        or profile_definition.get("path") != pin[0]
        or profile_definition.get("sha256") != pin[1]
    ):
        errors.append("profile_definition_digest_mismatch")
    errors.extend(_profile_artifact_binding_errors(profile, mapping, source_revision))
    return candidate_row, sorted(set(errors))


def _run_profile_candidate_evaluators(
    output_dir: Path,
    profile: dict[str, Any],
    candidate: Any,
    *,
    source_revision: str,
    after_tree_sha: str,
    input_bundle_sha256: str,
) -> dict[str, Any]:
    """Run only candidate rows whose full source-profile binding verifies."""
    if not isinstance(candidate, dict):
        return {"status": "not_measured", "reason": "P did not materialize a candidate"}
    candidate_rows = candidate.get("representations", [])
    if not isinstance(candidate_rows, list):
        candidate_rows = []
    records: list[dict[str, Any]] = []
    raw_dir = output_dir / "raw/p-candidate"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for mapping in profile["mappings"]:
        template = mapping["candidate_template"]["representation"]
        representation_id = str(template["id"])
        evaluator_id = str(template["evaluator"])
        candidate_row, binding_errors = _candidate_profile_binding_errors(
            profile=profile,
            candidate=candidate,
            mapping=mapping,
            candidate_rows=candidate_rows,
            source_revision=source_revision,
            after_tree_sha=after_tree_sha,
            input_bundle_sha256=input_bundle_sha256,
        )
        binding = {
            "status": "matched" if not binding_errors else "mismatch",
            "reason_codes": binding_errors,
            "candidate_row_sha256": (
                sha256_bytes(canonical_json_bytes(candidate_row))
                if candidate_row is not None
                else None
            ),
            "template_sha256": sha256_bytes(canonical_json_bytes(template)),
            "candidate_source_revision": candidate.get("architecture_source_sha"),
            "profile_source_revision": profile.get("architecture_source_sha"),
            "expected_source_revision": source_revision,
            "profile_after_tree_sha": profile.get("a0_1_app_tree_sha"),
            "expected_after_tree_sha": after_tree_sha,
            "candidate_input_bundle_sha256": candidate.get("input_bundle_sha256"),
            "expected_input_bundle_sha256": input_bundle_sha256,
            "candidate_applicability_scope": (
                candidate_row.get("applicability_scope") if candidate_row is not None else None
            ),
            "source_scope_id": mapping.get("source_scope_id"),
            "stage": template.get("stage"),
            "covers": template.get("covers"),
            "evaluator_id": evaluator_id,
            "configuration_artifact_sha256": mapping.get("configuration_artifact", {}).get(
                "sha256"
            ),
            "evaluator_artifact_sha256": template.get("evaluator_artifact", {}).get("sha256"),
            "evidence_contract_sha256": sha256_bytes(
                canonical_json_bytes(template.get("evidence_contract", {}))
            ),
        }
        if binding_errors:
            records.append(
                {
                    "representation_id": representation_id,
                    "evaluator_id": evaluator_id,
                    "status": "not_measured",
                    "reason_code": "CANDIDATE_PROFILE_BINDING_MISMATCH",
                    "candidate_profile_binding": binding,
                }
            )
            continue
        if evaluator_id == "EV_A01_IMPORT_LINTER":
            config_path = str(mapping["configuration_artifact"]["path"])
            command = [
                sys.executable,
                "-c",
                IMPORT_LINTER_ENTRYPOINT,
                "--config",
                config_path,
                "--no-cache",
                "--no-logo",
            ]
        elif evaluator_id == "EV_A01_MODULE_STRUCTURE_PYTEST":
            command = [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/architecture/test_module_structure.py",
            ]
        else:
            records.append(
                {
                    "representation_id": representation_id,
                    "status": "not_measured",
                    "reason": "unsupported evaluator",
                    "candidate_profile_binding": binding,
                }
            )
            continue
        started_ns = time.perf_counter_ns()
        completed = subprocess.run(  # noqa: S603 - fixed project evaluator argv; no shell
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            timeout=120,
        )
        duration_ns = time.perf_counter_ns() - started_ns
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", representation_id)
        stdout_path = raw_dir / f"{stem}.stdout.txt"
        stderr_path = raw_dir / f"{stem}.stderr.txt"
        stdout_path.write_bytes(completed.stdout)
        stderr_path.write_bytes(completed.stderr)
        records.append(
            {
                "representation_id": representation_id,
                "evaluator_id": evaluator_id,
                "evaluator_version": (
                    importlib.metadata.version("import-linter")
                    if evaluator_id == "EV_A01_IMPORT_LINTER"
                    else importlib.metadata.version("pytest")
                ),
                "argv": command,
                "exit_status": completed.returncode,
                "duration_ns": duration_ns,
                "duration_seconds": duration_ns / 1_000_000_000,
                "stdout": {
                    "path": stdout_path.relative_to(output_dir).as_posix(),
                    "sha256": sha256_bytes(completed.stdout),
                },
                "stderr": {
                    "path": stderr_path.relative_to(output_dir).as_posix(),
                    "sha256": sha256_bytes(completed.stderr),
                },
                "status": "execution_completed",
                "process_verdict": "PASS" if completed.returncode == 0 else "FAIL",
                "candidate_profile_binding": binding,
            }
        )
    durations = [
        int(row["duration_ns"]) for row in records if isinstance(row.get("duration_ns"), int)
    ]
    expected_count = len(profile["mappings"])
    status = (
        "measured"
        if len(durations) == expected_count
        else "partial"
        if durations
        else "not_measured"
    )
    return {
        "status": status,
        "execution_count": len(durations),
        "expected_evaluator_count": expected_count,
        "total_duration_ns": sum(durations) if durations else None,
        "representations": records,
        "validation_scope": (
            "TEST_ONLY execution of rows matching the exact candidate profile; this scoped run "
            "does not clear full-candidate validation or provide independent pair semantic proof"
        ),
    }


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
                "evaluator_evidence": pair_evidence,
                "source_representation_id": source_id,
                "source_evaluator_record_id": record_id,
                "source_lifecycle_stage": observation["lifecycle_stage"],
                "method_lifecycle_stage": mapping["candidate_template"]["representation"]["stage"],
                "source_scope_id": mapping["source_scope_id"],
                "metric": mapping["metric"],
                "observed_execution_verdict": record["execution_verdict"],
                "observed_exit_status": record["exit_status"],
                "observed_metric": observation["metrics"],
                "assessment_role": (
                    "pair assessment is diagnostic only; no semantic proof is supplied"
                ),
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


def run_pilot(
    exp02_run_dir: Path,
    output_dir: Path,
    *,
    test_only_continuation: bool = False,
    test_only_assumptions_path: Path | None = None,
    profile_version: int = 2,
) -> dict[str, Any]:
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
    if test_only_assumptions_path is not None and not test_only_continuation:
        raise ValueError("TEST_ONLY assumptions require --test-only-continuation")
    profile_pin = PILOT02_PROFILE_PINS.get(profile_version)
    if profile_pin is None:
        raise ValueError("unsupported PILOT-02 profile version")
    profile_path, profile_sha256, _ = profile_pin

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
    b0_evaluation = _run_b0_evaluator(destination)
    assumptions: dict[str, Any] | None = None
    assumptions_bytes: bytes | None = None
    assumptions_digest: str | None = None
    selected_assumptions_path: Path | None = None
    if test_only_continuation:
        selected_assumptions_path = (
            test_only_assumptions_path or PILOT02_ASSUMPTIONS_PATH
        ).resolve(strict=True)
        if not selected_assumptions_path.is_relative_to(root):
            raise ValueError("TEST_ONLY assumptions must be tracked inside the source checkout")
        assumptions_bytes = selected_assumptions_path.read_bytes()
        assumptions_digest = sha256_bytes(assumptions_bytes)
        assumptions = json.loads(assumptions_bytes)
        if assumptions.get("status") != "TEST_ONLY_NOT_AUTHORITY":
            raise ValueError("PILOT-02 TEST_ONLY assumptions are not explicitly non-authoritative")
        if assumptions.get("transition", {}).get("before_commit") != FROZEN_A0_SHA:
            raise ValueError("PILOT-02 TEST_ONLY assumptions do not bind frozen A0")
        transition_assumptions = assumptions.get("transition", {})
        if transition_assumptions.get("after_source_basis") != PILOT02_SOURCE_BASE_SHA:
            raise ValueError("PILOT-02 TEST_ONLY assumptions do not bind the current main base")
        expected_app_tree = transition_assumptions.get("after_app_tree_sha256")
        actual_app_tree = _git("rev-parse", f"{source_revision}:app")
        if expected_app_tree is not None and expected_app_tree != actual_app_tree:
            raise ValueError("PILOT-02 TEST_ONLY assumptions do not bind the A0.1 app tree")
        shutil.copyfile(selected_assumptions_path, destination / "development_assumptions.json")
    with tempfile.TemporaryDirectory(prefix="pilot02-method-input-") as temporary:
        temporary_root = Path(temporary)
        p_input_dir = temporary_root / "method-input-p"
        registry = json.loads(
            (POLICY_SOURCE / "fitness/policy/registry.json").read_text(encoding="utf-8")
        )
        trust_context: Pilot02TestOnlyTrustContext | None = None
        if test_only_continuation:
            profile_bytes = _source_blob(source_revision, profile_path)
            profile = json.loads(profile_bytes)
            ruleset = load_and_validate_ruleset(
                POLICY_SOURCE / "policy/applicability_ruleset_v1.json",
                load_fact_vocabulary(),
                ROOT / "fitness/catalog/architectural-obligations.yaml",
            )
            if assumptions is None:
                raise RuntimeError("PILOT-02 assumptions were not loaded")
            policy_source, trust_context = create_testonly_policy_source(
                POLICY_SOURCE,
                temporary_root,
                evaluation_as_of=str(registry["as_of"]),
                before_sha=FROZEN_A0_SHA,
                after_sha=source_revision,
                obligation_catalog_sha256=str(profile["obligation_catalog_sha256"]),
                target_obligation_ids=list(assumptions["transition"]["target_obligation_ids"]),
                applicability_by_obligation=assumptions["transition"].get(
                    "applicability_by_obligation"
                ),
            )
            obligation_ids = {item.obligation_id for item in ruleset.obligations}
            if not set(assumptions["transition"]["target_obligation_ids"]).issubset(obligation_ids):
                raise ValueError("PILOT-02 assumption names an obligation outside the catalog")
            policy_revision = f"PILOT02_TEST_ONLY_{source_revision[:12]}"
            policy_bundle = temporary_root / "policy-source-v3"
            policy_manifest = package_policy_source_v3(
                policy_source, policy_bundle, policy_revision
            )
        else:
            policy_source = POLICY_SOURCE
            policy_revision = f"PILOT02_DRAFT_OPEN_{source_revision[:12]}"
            policy_bundle = temporary_root / "policy-source-v3"
            policy_manifest = package_policy_source_v3(
                policy_source, policy_bundle, policy_revision
            )
        v3_manifest = export_method_inputs_v3(
            root,
            policy_bundle,
            p_input_dir,
            "P",
            FROZEN_A0_SHA,
            source_revision,
            str(registry["as_of"]),
        )
        profile = json.loads(_source_blob(source_revision, profile_path))
        if sha256_bytes(_source_blob(source_revision, profile_path)) != profile_sha256:
            raise ProtocolError("PILOT02_PROFILE_DEFINITION_SOURCE_MISMATCH")
        profile["architecture_source_sha"] = source_revision
        profile["a0_1_app_tree_sha"] = v3_manifest["after_tree_sha"]
        _embedded_artifacts(profile, source_revision)
        _install_profile(p_input_dir, profile)
        if test_only_continuation:
            if assumptions is None:
                raise RuntimeError("PILOT-02 assumptions were not loaded")
            _install_testonly_cost_model(p_input_dir, profile, assumptions)
            method_manifest = verify_method_bundle_v3(p_input_dir, expected_method_id="P")
            snapshot = json.loads((p_input_dir / "architecture-policy-snapshot.json").read_bytes())
            sources, source_report = load_verified_source_manifest(
                snapshot, method_manifest, p_input_dir
            )
            if trust_context is None:
                raise RuntimeError("TEST_ONLY trust context was not created")
            evidence_ledger = build_testonly_evidence_ledger(
                snapshot,
                sources,
                source_integrity_valid=source_report.status is ValidationStatus.VALID,
                trust_context=trust_context,
            )
            p_bundle = verify_v3_p_bundle(
                p_input_dir,
                evidence_ledger=evidence_ledger,
                trust_context=trust_context,
                completeness_verifier=testonly_completeness_verifier,
            )
        else:
            p_bundle = verify_v3_p_bundle(
                p_input_dir,
                evidence_ledger=EvidenceLedger({}, {}, {}),
            )

        pair_assessments = _assess_profile_pairs(
            profile=profile,
            exp02_run_dir=exp02_path,
            exp02_bundle=exp02_bundle,
            exp02_evidence=exp02_evidence,
            p_bundle=p_bundle,
            output_dir=destination,
        )
        adaptation_sidecar: dict[str, Any] | None = None
        execution_evidence_rows: list[dict[str, Any]] = []
        if test_only_continuation:
            if assumptions is None or trust_context is None:
                raise RuntimeError("TEST_ONLY continuation inputs were not initialized")
            extra_artifacts: dict[str, bytes] = {}
            for item in pair_assessments:
                evidence = item["evaluator_evidence"]
                execution_evidence_rows.append(
                    {
                        "representation_id": item["source_representation_id"],
                        "obligation_id": item["assessment"]["obligation_id"],
                        "evidence": evidence,
                    }
                )
                for reference in evidence["evidence_artifacts"]:
                    path = str(reference["path"])
                    extra_artifacts[path] = (destination / path).read_bytes()
            b0_representation = next(
                row
                for row in p_bundle.representations
                if row.get("id") == "REP_A0_ARCH_CI_LAYERING"
            )
            b0_evidence, b0_artifacts = _b0_pair_evidence(
                bundle=p_bundle,
                output_dir=destination,
                evaluation=b0_evaluation,
            )
            extra_artifacts.update(b0_artifacts)
            adaptation_sidecar = build_adaptation_sidecar(
                p_bundle,
                assumptions=assumptions,
                evaluator_evidence=execution_evidence_rows,
                b0_representation=b0_representation,
                b0_evaluator_evidence=b0_evidence,
                extra_artifacts=extra_artifacts,
            )
            (destination / "adaptation_evidence_test_only.json").write_bytes(
                pretty_json_bytes(adaptation_sidecar)
            )

        started_ns = time.perf_counter_ns()
        result = run_adaptation(p_bundle, evidence_context=adaptation_sidecar)
        adaptation_duration_ns = time.perf_counter_ns() - started_ns
        trace = _adaptation_trace(p_bundle, result)
        execution_admission_status, execution_evidence_admitted = (
            _exp02_execution_evidence_admission(
                sidecar_supplied=adaptation_sidecar is not None,
                trust_scope=result.evidence_trust_scope,
            )
        )
        trace["pilot02_profile_pair_assessments"] = pair_assessments
        trace["pilot02_profile_pair_assessments_role"] = (
            "TEST_ONLY evaluator execution records were admitted; pair diagnostics supplied "
            "no positive semantic proof"
            if test_only_continuation
            else "diagnostic only; not used for adaptation"
        )
        trace["pilot02_test_only_continuation"] = test_only_continuation
        trace["pilot02_test_only_assumptions_sha256"] = (
            assumptions_digest if test_only_continuation else None
        )
        trace["exp02_evidence_admission_status"] = execution_admission_status
        trace["exp02_evidence_admitted_to_p_calculations"] = execution_evidence_admitted
        trace["exp02_observations_used_as_semantic_pair_evidence"] = False
        trace["adaptation_evidence_sidecar_supplied"] = adaptation_sidecar is not None
        trace["adaptation_evidence_trust_scope"] = result.evidence_trust_scope
        trace["pilot02_exp02_consumption"] = {
            "sidecar_passed_to_run_adaptation": adaptation_sidecar is not None,
            "sidecar_sha256": (
                adaptation_sidecar.get("sidecar_sha256") if adaptation_sidecar is not None else None
            ),
            "exp02_run_id": exp02_bundle["run_id"],
            "exp02_bundle_sha256": sha256_bytes((exp02_path / BUNDLE_FILENAME).read_bytes()),
            "exp02_representation_evidence_sha256": exp02_bundle["fitness_representation_evidence"][
                "sha256"
            ],
            "exp02_execution_record_count": len(execution_evidence_rows),
            "exp02_representation_ids": [
                row["representation_id"] for row in execution_evidence_rows
            ],
            "exp02_evaluator_record_ids": [
                row["source_evaluator_record_id"] for row in pair_assessments
            ],
            "raw_artifacts_in_sidecar": (
                [
                    {"path": row["path"], "sha256": row["sha256"]}
                    for row in adaptation_sidecar["payload"]["artifact_bytes"]
                ]
                if adaptation_sidecar is not None
                else []
            ),
            "semantic_pair_proof_supplied_for_exp02": False,
            "execution_evidence_admission_status": execution_admission_status,
            "interpretation": (
                "Digest-validated EXP-02 executions were supplied before run_adaptation under "
                "TEST_ONLY; this is not semantic pair proof or coverage admission."
            ),
        }
        trace["method_p_computation_duration_ns"] = adaptation_duration_ns
        trace["method_p_computation_duration_seconds"] = adaptation_duration_ns / 1_000_000_000
        (destination / "method_p_trace.json").write_bytes(pretty_json_bytes(trace))
        shutil.copytree(p_input_dir, destination / "verified_method_input")

    candidate = result.candidate
    candidate_status = (
        candidate.get("candidate_validation", {}).get("status", "materialized_unvalidated")
        if isinstance(candidate, dict)
        else "not_materialized"
    )
    p_evaluation = (
        _run_profile_candidate_evaluators(
            destination,
            profile,
            candidate,
            source_revision=source_revision,
            after_tree_sha=v3_manifest["after_tree_sha"],
            input_bundle_sha256=p_bundle.manifest["bundle_sha256"],
        )
        if test_only_continuation
        else {
            "status": "not_measured",
            "reason": (
                "The existing Method P result did not provide a valid, publishable candidate "
                "with an independently authorized evaluator configuration."
            ),
            "candidate_validation_status": candidate_status,
        }
    )
    p_evaluation["candidate_validation_status"] = candidate_status
    if isinstance(candidate, dict):
        (destination / "candidate_configuration.json").write_bytes(pretty_json_bytes(candidate))

    artifacts = []
    for artifact_path in sorted(destination.rglob("*")):
        if artifact_path.is_file() and artifact_path.name not in {
            "run_manifest.json",
            "run_manifest.sha256",
        }:
            relative = artifact_path.relative_to(destination).as_posix()
            content = artifact_path.read_bytes()
            artifacts.append(
                {"path": relative, "size_bytes": len(content), "sha256": sha256_bytes(content)}
            )
    manifest = {
        "schema_version": 1,
        "pilot_id": "PILOT-02",
        "execution_status": (
            "completed_test_only_development_continuation"
            if test_only_continuation
            else "completed_development_only"
        ),
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
            "profile_definition_sha256": profile_sha256,
            "trust_scope": result.evidence_trust_scope or "none",
            "test_only_assumptions_sha256": (
                assumptions_digest if test_only_continuation else None
            ),
            "test_only_assumptions_path": (
                selected_assumptions_path.relative_to(root).as_posix()
                if selected_assumptions_path is not None
                else None
            ),
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
            "governance_reason_codes": result.governance.to_dict()["reason_codes"],
            "after_applicability": result.after_applicability.to_dict(),
            "current_pairs": [item.to_dict() for item in result.current_pairs],
            "operation_plan": result.operation_plan.to_dict(),
            "candidate_status": candidate_status,
            "candidate_sha256": result.candidate_sha256,
            "candidate_evaluation": p_evaluation,
            "current_coverage": result.current_coverage.to_dict(),
            "candidate_coverage": (
                result.candidate_coverage.to_dict()
                if result.candidate_coverage is not None
                else None
            ),
            "candidate_pairs": [item.to_dict() for item in result.candidate_pairs],
            "test_only_continuation": test_only_continuation,
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
    parser.add_argument(
        "--test-only-continuation",
        action="store_true",
        help="Use the prospective PILOT-02 TEST_ONLY development assumptions.",
    )
    parser.add_argument(
        "--test-only-assumptions",
        type=Path,
        help="Use a tracked PILOT-02 TEST_ONLY assumption set for a prospective continuation.",
    )
    parser.add_argument("--profile-version", type=int, choices=[1, 2], default=2)
    args = parser.parse_args(argv)
    try:
        manifest = run_pilot(
            args.exp02_run_dir,
            args.output_dir,
            test_only_continuation=args.test_only_continuation,
            test_only_assumptions_path=args.test_only_assumptions,
            profile_version=args.profile_version,
        )
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
