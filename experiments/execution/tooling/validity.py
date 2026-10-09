"""Independent semantic-validity checks for evaluator evidence and candidates."""

from __future__ import annotations

import tomllib
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import sha256_file

SemanticStatus = Literal[
    "VALID_APPLICABLE",
    "SEMANTIC_MISMATCH",
    "STALE_ARCHITECTURE_SCOPE",
    "MISSING_ARCHITECTURE_TARGET",
    "VACUOUS_SUCCESS",
    "MISSING_EVIDENCE",
    "EXECUTION_FAILURE",
    "INFRASTRUCTURE_FAILURE",
    "STAGE_OR_CONTEXT_MISMATCH",
    "OBLIGATION_MAPPING_MISMATCH",
    "INACTIVE",
]


def assess_representation(
    representation: dict[str, Any],
    evidence: dict[str, Any],
    required_architecture_sha: str,
) -> dict[str, Any]:
    """Evaluate validity predicates without treating process success as coverage."""
    validate_payload("evaluator_evidence.schema.json", evidence)
    representation_id = str(representation["id"])
    if evidence["representation_id"] != representation_id:
        raise ProtocolError("Evaluator evidence representation_id does not match its candidate")

    active = bool(representation.get("active", False))
    mapping_resolved = bool(evidence["mapping_resolved"])
    stage_applicable = bool(evidence["stage_applicable"])
    semantic_compatible = evidence["semantic_compatible"]
    evidence_artifacts = cast(list[dict[str, str]], evidence["evidence_artifacts"])
    evidence_present = bool(evidence_artifacts) or evidence.get("stdout_sha256") is not None
    configured_targets = cast(list[str], evidence["configured_targets"])
    resolved_targets = cast(list[str], evidence["resolved_targets"])
    inspected_subjects = cast(list[str], evidence["inspected_subjects"])
    missing_targets = cast(list[str], evidence["missing_targets"])
    status: SemanticStatus
    reason_codes: list[str] = []

    if evidence["architecture_source_sha"] != required_architecture_sha:
        status = "STALE_ARCHITECTURE_SCOPE"
        reason_codes.append("ARCHITECTURE_SOURCE_MISMATCH")
    elif evidence["infrastructure_status"] == "infrastructure_failure":
        status = "INFRASTRUCTURE_FAILURE"
        reason_codes.append("RUNNER_INFRASTRUCTURE_FAILURE")
    elif not active:
        status = "INACTIVE"
        reason_codes.append("REPRESENTATION_INACTIVE")
    elif evidence["infrastructure_status"] != "completed" or evidence["process_exit_code"] is None:
        status = "MISSING_EVIDENCE"
        reason_codes.append("EVALUATOR_NOT_RUN")
    elif evidence["process_exit_code"] != 0:
        status = "EXECUTION_FAILURE"
        reason_codes.append("EVALUATOR_EXIT_NONZERO")
    elif missing_targets:
        status = "MISSING_ARCHITECTURE_TARGET"
        reason_codes.append("CONFIGURED_TARGET_NOT_RESOLVED")
    elif not mapping_resolved:
        status = "OBLIGATION_MAPPING_MISMATCH"
        reason_codes.append("OBLIGATION_MAPPING_UNRESOLVED")
    elif not stage_applicable:
        status = "STAGE_OR_CONTEXT_MISMATCH"
        reason_codes.append("STAGE_NOT_APPLICABLE")
    elif semantic_compatible is False:
        status = "SEMANTIC_MISMATCH"
        reason_codes.append("INTENDED_SEMANTIC_NOT_PRESERVED")
    elif semantic_compatible is None:
        status = "MISSING_EVIDENCE"
        reason_codes.append("SEMANTIC_COMPATIBILITY_NOT_ASSESSED")
    elif not configured_targets or not resolved_targets or not inspected_subjects:
        status = "VACUOUS_SUCCESS"
        reason_codes.append("NO_APPLICABLE_SUBJECTS_INSPECTED")
    elif evidence["evaluator_id"] in {"import_linter", "architecture_checker"} and (
        evidence["inspected_edge_count"] == 0
    ):
        status = "VACUOUS_SUCCESS"
        reason_codes.append("NO_RELEVANT_IMPORT_EDGES_INSPECTED")
    elif not evidence["evidence_contract_satisfied"] or not evidence_present:
        status = "MISSING_EVIDENCE"
        reason_codes.append("EVIDENCE_CONTRACT_NOT_SATISFIED")
    elif not evidence["adequacy_proven"]:
        status = "MISSING_EVIDENCE"
        reason_codes.append("EVALUATOR_ADEQUACY_NOT_PROVEN")
    elif evidence.get("clean_probe") == "fail" or evidence.get("fault_probe") == "missed":
        status = "SEMANTIC_MISMATCH"
        reason_codes.append("CONTROLLED_PROBE_RESULT_INVALID")
    else:
        status = "VALID_APPLICABLE"

    verdict = {
        "schema_version": 1,
        "representation_id": representation_id,
        "architecture_source_sha": required_architecture_sha,
        "status": status,
        "reason_codes": reason_codes,
        "active": active,
        "mapping_resolved": mapping_resolved,
        "stage_applicable": stage_applicable,
        "semantic_compatible": semantic_compatible,
        "executable_nonvacuous": status == "VALID_APPLICABLE",
        "evidence_contract_satisfied": bool(
            evidence["evidence_contract_satisfied"] and evidence_present
        ),
        "evidence_refs": [str(item["path"]) for item in evidence_artifacts]
        or [f"stdout_sha256:{evidence['stdout_sha256']}"]
        if evidence_present
        else [],
    }
    validate_payload("semantic_verdict.schema.json", verdict)
    return verdict


def valid_cover(
    verdict: dict[str, Any],
    representation: dict[str, Any],
    obligation_id: str,
    architecture_source_sha: str,
) -> bool:
    """Return whether an independently assessed active representation covers one obligation."""
    return (
        verdict.get("status") == "VALID_APPLICABLE"
        and verdict.get("representation_id") == representation.get("id")
        and verdict.get("architecture_source_sha") == architecture_source_sha
        and verdict.get("active") is True
        and bool(representation.get("active"))
        and obligation_id in representation.get("covers", [])
        and verdict.get("mapping_resolved") is True
        and verdict.get("stage_applicable") is True
        and verdict.get("semantic_compatible") is True
        and verdict.get("executable_nonvacuous") is True
        and verdict.get("evidence_contract_satisfied") is True
        and bool(verdict.get("evidence_refs"))
    )


def inspect_import_linter_scope(
    configuration: bytes,
    available_modules: set[str],
) -> dict[str, Any]:
    """Resolve every frozen Import Linter selector against a source module set."""
    try:
        parsed = tomllib.loads(configuration.decode("utf-8"))
        contracts = parsed["tool"]["importlinter"]["contracts"]
    except (UnicodeDecodeError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ProtocolError("Import Linter configuration cannot be parsed") from error

    selectors: list[str] = []
    for contract in contracts:
        for key in ("source_modules", "forbidden_modules", "layers"):
            values = contract.get(key, [])
            if isinstance(values, list):
                selectors.extend(str(value) for value in values)
    unique_selectors = list(dict.fromkeys(selectors))
    resolved = [
        selector
        for selector in unique_selectors
        if _module_selector_resolves(selector, available_modules)
    ]
    missing = [selector for selector in unique_selectors if selector not in resolved]
    applicable_modules = {
        module
        for module in available_modules
        if any(_module_is_within(module, selector) for selector in unique_selectors)
    }
    return {
        "configured_contract_count": len(contracts),
        "configured_selector_count": len(unique_selectors),
        "resolved_selectors": resolved,
        "missing_targets": missing,
        "inspected_module_count": len(applicable_modules),
        "vacuous": not applicable_modules,
        "stale": bool(missing),
    }


def validate_layer_edges(
    layer_order: list[str],
    import_edges: list[tuple[str, str]],
) -> dict[str, Any]:
    """Check synthetic or observed import edges against a declared top-down layer order."""
    if len(layer_order) < 2 or len(layer_order) != len(set(layer_order)):
        raise ProtocolError("A layer policy requires at least two unique ordered layers")
    violations: list[dict[str, str]] = []
    inspected_edges: list[dict[str, str]] = []
    for source, target in import_edges:
        source_layer = _matching_layer(source, layer_order)
        target_layer = _matching_layer(target, layer_order)
        if source_layer is None or target_layer is None:
            continue
        inspected_edges.append({"source": source, "target": target})
        if layer_order.index(source_layer) > layer_order.index(target_layer):
            violations.append({"source": source, "target": target})
    return {
        "inspected_edge_count": len(inspected_edges),
        "inspected_edges": inspected_edges,
        "violations": violations,
        "compliant": not violations,
    }


def validate_module_structure(root: Path, module_manifest: dict[str, Any]) -> dict[str, Any]:
    """Check declared package files in a disposable architecture source tree."""
    root_path = root.resolve(strict=True)
    modules = module_manifest.get("modules")
    if not isinstance(modules, dict) or not modules:
        raise ProtocolError("Structural manifest must declare at least one module")
    inspected: list[str] = []
    missing: list[str] = []
    for module_name, module in sorted(modules.items()):
        if not isinstance(module, dict):
            raise ProtocolError(f"Invalid module manifest entry: {module_name}")
        package = str(module.get("package", ""))
        required_files = module.get("required_files", [])
        package_parts = PurePosixPath(package.replace(".", "/"))
        if not package or package_parts.is_absolute() or ".." in package_parts.parts:
            raise ProtocolError(f"Unsafe module package path: {package}")
        if not isinstance(required_files, list) or not required_files:
            raise ProtocolError(f"Module {module_name} must declare required_files")
        package_root = (root_path / Path(*package_parts.parts)).resolve()
        if not package_root.is_relative_to(root_path):
            raise ProtocolError(f"Module path escapes the source root: {package}")
        inspected.append(package)
        for filename in required_files:
            file_part = PurePosixPath(str(filename))
            if (
                file_part.is_absolute()
                or len(file_part.parts) != 1
                or file_part.name in {".", ".."}
            ):
                raise ProtocolError(f"Unsafe required module filename: {filename}")
            candidate = package_root / file_part.name
            if candidate.is_symlink() or not candidate.is_file():
                missing.append(f"{package}.{file_part.name}")
    return {
        "inspected_module_count": len(inspected),
        "inspected_modules": inspected,
        "missing_targets": missing,
        "compliant": not missing,
        "vacuous": not inspected,
    }


def verify_evidence_artifacts(evidence_root: Path, evidence: dict[str, Any]) -> list[str]:
    """Verify evidence artifact paths and hashes remain inside the evidence root."""
    root = evidence_root.resolve(strict=True)
    verified: list[str] = []
    for artifact in evidence.get("evidence_artifacts", []):
        relative = PurePosixPath(str(artifact["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ProtocolError(f"Unsafe evidence path: {relative.as_posix()}")
        path = root.joinpath(*relative.parts)
        parents = [
            root.joinpath(*relative.parts[:index]) for index in range(1, len(relative.parts))
        ]
        if (
            any(parent.is_symlink() for parent in parents)
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root)
        ):
            raise ProtocolError(
                f"Evidence artifact is missing or outside its root: {relative.as_posix()}"
            )
        if sha256_file(path) != artifact["sha256"]:
            raise ProtocolError(f"Evidence artifact hash mismatch: {relative.as_posix()}")
        verified.append(relative.as_posix())
    return verified


def _module_selector_resolves(selector: str, modules: set[str]) -> bool:
    return any(_module_is_within(module, selector) for module in modules)


def _module_is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


def _matching_layer(module: str, layers: list[str]) -> str | None:
    matching = [layer for layer in layers if _module_is_within(module, layer)]
    if not matching:
        return None
    return max(matching, key=len)


__all__ = [
    "SemanticStatus",
    "assess_representation",
    "inspect_import_linter_scope",
    "valid_cover",
    "validate_layer_edges",
    "validate_module_structure",
    "verify_evidence_artifacts",
]
