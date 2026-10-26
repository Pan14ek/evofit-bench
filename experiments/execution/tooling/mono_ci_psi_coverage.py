"""Independent source inspection and adaptation-necessity diagnostics.

This module is deliberately outside the Method Ψ runtime. It reconstructs the
inspection universe from pinned Git trees, evaluator configuration, and state
manifests, then compares that universe with the evaluator's raw output.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import shutil
import subprocess  # nosec B404 - fixed, read-only Git object queries
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any

import yaml

from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes

_EVALUATOR_IDS = {"AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP"}
_STATE_NAMES = {
    "A0_3_GOVERNED_MODULE_GRAPH",
    "A0_4_REPORT_QUERY_PORT",
    "A0_5_MODULE_DATA_OWNERSHIP",
}
_SHA1 = re.compile(r"^[a-f0-9]{40}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")

_REQUIREMENT_CAPABILITY_MAPPINGS = {
    "architecture.module_graph.allowed_dependency": {
        "capability_type": "evaluator.module_graph.allowed_dependency_policy",
        "mapping_id": "MAP-MODULE-DEPENDENCY-TO-A1-ALLOWED-EDGE-V1",
        "comparison_rule": "EXACT_STRUCTURED_EDGE_MEMBERSHIP",
    },
    "architecture.public_api.reporting_query_port": {
        "capability_type": "evaluator.public_api.reporting_query_port_boundary",
        "mapping_id": "MAP-REPORTING-QUERY-PORT-TO-A1-PUBLIC-API-V1",
        "comparison_rule": "SOURCE_TARGET_EXPORT_AND_FORBIDDEN_IMPORT_CHECK",
    },
    "architecture.public_api.temporary_exception": {
        "capability_type": "evaluator.public_api.temporary_exception_scope",
        "mapping_id": "MAP-TEMPORARY-EXCEPTION-TO-A1-STATE-SCOPE-V1",
        "comparison_rule": "EXACT_EXCEPTION_AND_STATE_MEMBERSHIP",
    },
    "architecture.data_ownership.persistence_ownership": {
        "capability_type": "evaluator.data_ownership.table_and_access_policy",
        "mapping_id": "MAP-PERSISTENCE-OWNERSHIP-TO-A1-DATA-OWNERSHIP-V1",
        "comparison_rule": "EXACT_TABLE_OWNERS_AND_DECLARED_STATIC_ACCESS_RULES",
    },
}

_INDEPENDENT_REQUIREMENT_SOURCE_KINDS = {
    "VERSIONED_ARCHITECTURE_STATE_MANIFEST",
    "APPROVED_ARCHITECTURE_POLICY",
    "APPROVED_GOVERNANCE_REQUIREMENT",
}


def verify_inspection_coverage(
    *,
    repository: Any,
    source_commit_sha: str,
    source_tree_sha: str,
    architecture_state: str,
    evaluator_id: str,
    evaluator_configuration_bytes: bytes,
    state_manifest_bytes: bytes,
    evaluator_output_bytes: bytes,
    evaluator_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Independently verify evaluator inspection against the pinned Git tree.

    The evaluator's ``inspected_paths`` is used only as the observed set. The
    expected set comes from ``git ls-tree`` plus the separately bound evaluator
    configuration. For AC_MODULE_GRAPH, statically identifiable import
    relationships are also reconstructed from the pinned source bytes; allowed
    policy edges are recorded separately and never used as expected imports.
    """
    if (
        evaluator_id not in _EVALUATOR_IDS
        or architecture_state not in _STATE_NAMES
        or _SHA1.fullmatch(source_commit_sha) is None
        or _SHA1.fullmatch(source_tree_sha) is None
        or _SHA256.fullmatch(sha256_bytes(evaluator_configuration_bytes)) is None
        or _SHA256.fullmatch(sha256_bytes(state_manifest_bytes)) is None
    ):
        raise ContractValidationError("PSI_INSPECTION_IDENTITY_INVALID")
    output_sha256 = sha256_bytes(evaluator_output_bytes)
    try:
        parsed_output = json.loads(evaluator_output_bytes)
        config = yaml.safe_load(evaluator_configuration_bytes)
        manifest = yaml.safe_load(state_manifest_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ContractValidationError("PSI_INSPECTION_SOURCE_CONTRACT_INVALID") from error
    if not isinstance(parsed_output, Mapping) or dict(parsed_output) != dict(evaluator_evidence):
        raise ContractValidationError("PSI_INSPECTION_OUTPUT_BINDING_MISMATCH")
    if not isinstance(config, Mapping) or not isinstance(manifest, Mapping):
        raise ContractValidationError("PSI_INSPECTION_SOURCE_CONTRACT_INVALID")

    evaluator = evaluator_evidence.get("evaluator")
    architecture = evaluator_evidence.get("architecture")
    source_scope = evaluator_evidence.get("source_scope")
    if not isinstance(evaluator, Mapping) or not isinstance(architecture, Mapping):
        raise ContractValidationError("PSI_INSPECTION_EVALUATOR_IDENTITY_MISMATCH")
    config_sha256 = sha256_bytes(evaluator_configuration_bytes)
    manifest_sha256 = sha256_bytes(state_manifest_bytes)
    tree_sha = _git_text(repository, "rev-parse", f"{source_commit_sha}^{{tree}}")
    if (
        evaluator.get("id") != evaluator_id
        or evaluator.get("obligation_id") != evaluator_id
        or evaluator.get("configuration_digest") != config_sha256
        or architecture.get("state") != architecture_state
        or architecture.get("expected_source_sha") != source_commit_sha
        or architecture.get("target_source_sha") != source_commit_sha
        or architecture.get("source_sha_status") != "MATCHED"
        or architecture.get("manifest_state_status") != "MATCHED"
        or architecture.get("manifest_digest") != manifest_sha256
        or tree_sha != source_tree_sha
        or manifest.get("architecture_state") != architecture_state
        or not _manifest_requires_evaluator(manifest, evaluator_id)
    ):
        raise ContractValidationError("PSI_INSPECTION_REVISION_CONFIG_OR_MANIFEST_MISMATCH")

    scope = config.get("source_scope")
    configured_state = config.get("states", {}).get(architecture_state)
    if (
        not isinstance(scope, Mapping)
        or not isinstance(configured_state, Mapping)
        or configured_state.get("applicability") != "ACTIVE"
        or config.get("evaluator", {}).get("id") != evaluator_id
        or not isinstance(source_scope, Mapping)
    ):
        raise ContractValidationError("PSI_INSPECTION_DECLARED_SCOPE_INVALID")

    module_root = _safe_relative_path(scope.get("module_root"))
    expected_modules = scope.get("expected_modules")
    if (
        module_root is None
        or not isinstance(expected_modules, list)
        or not expected_modules
        or any(not isinstance(item, str) or not item for item in expected_modules)
        or len(expected_modules) != len(set(expected_modules))
    ):
        raise ContractValidationError("PSI_INSPECTION_DECLARED_SCOPE_INVALID")

    tree_entries = _git_tree_entries(repository, source_commit_sha, module_root)
    tree_paths = set(tree_entries)
    discovered_modules = set()
    for path in tree_paths:
        if not path.startswith(f"{module_root}/") or not path.endswith("/__init__.py"):
            continue
        relative_parts = path[len(module_root) + 1 :].split("/")
        if len(relative_parts) > 1:
            discovered_modules.add(relative_parts[0])
    configured_modules = set(expected_modules)
    eligible_modules = configured_modules | discovered_modules
    expected_files = {
        path
        for path in tree_paths
        if path.endswith(".py")
        and any(path.startswith(f"{module_root}/{name}/") for name in eligible_modules)
    }
    scope_uncertainties: list[str] = []
    if configured_modules - discovered_modules:
        scope_uncertainties.extend(
            f"MISSING_CONFIGURED_MODULE:{name}"
            for name in sorted(configured_modules - discovered_modules)
        )
    if discovered_modules - configured_modules:
        scope_uncertainties.extend(
            f"UNEXPECTED_DISCOVERED_MODULE:{name}"
            for name in sorted(discovered_modules - configured_modules)
        )

    additional_files = scope.get("additional_source_files", [])
    if not isinstance(additional_files, list):
        raise ContractValidationError("PSI_INSPECTION_DECLARED_SCOPE_INVALID")
    for row in additional_files:
        path_value = row.get("path") if isinstance(row, Mapping) else row
        path = _safe_relative_path(path_value)
        if path is None:
            raise ContractValidationError("PSI_INSPECTION_DECLARED_SCOPE_INVALID")
        if path not in tree_paths:
            scope_uncertainties.append(f"MISSING_CONFIGURED_SOURCE:{path}")
        else:
            expected_files.add(path)

    source_rows = [
        {
            "path": path,
            "git_blob_sha1": tree_entries[path]["blob_sha1"],
            "sha256": sha256_bytes(_git_blob(repository, source_commit_sha, path)),
        }
        for path in sorted(expected_files)
    ]
    actual_subjects, digest_rows, source_scope_errors = _observed_file_scope(source_scope)
    scope_uncertainties.extend(source_scope_errors)
    expected_subjects = sorted(expected_files)
    actual_set = set(actual_subjects)
    expected_set = set(expected_subjects)
    missing = sorted(expected_set - actual_set)
    unexpected = sorted(actual_set - expected_set)
    expected_digests = {row["path"]: row["sha256"] for row in source_rows}
    observed_digests = {row["path"]: row["sha256"] for row in digest_rows}
    altered = sorted(
        path
        for path in actual_set & expected_set
        if observed_digests.get(path) != expected_digests.get(path)
    )
    verified_matching = sorted(
        path
        for path in actual_set & expected_set
        if path in observed_digests and observed_digests[path] == expected_digests.get(path)
    )
    module_records = source_scope.get("modules")
    reported_expected = (
        {
            row.get("name")
            for row in module_records
            if isinstance(row, Mapping) and row.get("expected") is True
        }
        if isinstance(module_records, list)
        else set()
    )
    reported_discovered = (
        {
            row.get("name")
            for row in module_records
            if isinstance(row, Mapping) and row.get("discovered") is True
        }
        if isinstance(module_records, list)
        else set()
    )
    declared_scope_matches = (
        source_scope.get("module_root") == module_root
        and reported_expected == configured_modules
        and reported_discovered == discovered_modules
    )
    if not declared_scope_matches:
        scope_uncertainties.append("EVALUATOR_DECLARED_SCOPE_MISMATCH")
    minimum_per_module = scope.get("minimum_source_files_per_module", 1)
    minimum_total = scope.get("minimum_inspected_files", 1)
    if type(minimum_per_module) is not int or type(minimum_total) is not int:
        raise ContractValidationError("PSI_INSPECTION_DECLARED_SCOPE_INVALID")
    for name in sorted(configured_modules):
        file_count = sum(
            path.startswith(f"{module_root}/{name}/") and path.endswith(".py")
            for path in expected_files
        )
        if file_count < minimum_per_module:
            scope_uncertainties.append(f"INSUFFICIENT_MODULE_SOURCE:{name}")
    if len(expected_files) < minimum_total:
        scope_uncertainties.append("INSUFFICIENT_DECLARED_SOURCE_FILE_COUNT")
    source_scope_status = "COMPLETE"
    if (
        missing
        or unexpected
        or altered
        or scope_uncertainties
        or source_scope.get("complete") is not True
    ):
        source_scope_status = "INCOMPLETE"
    counts = {
        "expected_count": len(expected_subjects),
        "inspected_count": len(actual_subjects),
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "altered_count": len(altered),
        "verified_matching_count": len(verified_matching),
    }

    dependency_analysis: dict[str, Any] | None = None
    if evaluator_id == "AC_MODULE_GRAPH":
        static_imports, import_uncertainties = _independent_capability_imports(
            repository,
            source_commit_sha,
            source_rows,
            configured_modules,
            discovered_modules,
        )
        observed_imports, observed_edge_errors = _observed_capability_imports(
            evaluator_evidence.get("diagnostics")
        )
        observed_cycles, cycle_errors = _observed_cycle_paths(evaluator_evidence.get("diagnostics"))
        missing_imports = _counter_difference(static_imports, observed_imports)
        unexpected_imports = _counter_difference(observed_imports, static_imports)
        expected_cycles = _cycle_paths(
            configured_modules | discovered_modules,
            {(item["from"], item["to"]) for item in static_imports},
        )
        cycle_comparison = (
            "MATCHED" if observed_cycles == expected_cycles and not cycle_errors else "MISMATCH"
        )
        allowed_edges = _configured_edges(config, architecture_state)
        dependency_analysis = {
            "basis": "SOURCE_DERIVED_STATIC_IMPORTS; allowed policy edges are separate",
            "expected_static_relationships": static_imports,
            "observed_static_relationships": observed_imports,
            "missing_static_relationships": missing_imports,
            "unexpected_static_relationships": unexpected_imports,
            "expected_edge_subjects": _edge_subjects(static_imports),
            "observed_edge_subjects": _edge_subjects(observed_imports),
            "expected_static_cycles": expected_cycles,
            "observed_cycles": observed_cycles,
            "cycle_comparison": cycle_comparison,
            "allowed_policy_edges": allowed_edges,
            "static_relationship_comparison": (
                "MATCHED"
                if not missing_imports
                and not unexpected_imports
                and not import_uncertainties
                and not observed_edge_errors
                else "MISMATCH"
            ),
            "exact_dependency_edge_completeness": "UNKNOWN",
            "reason_codes": sorted(
                set(import_uncertainties)
                | set(observed_edge_errors)
                | set(cycle_errors)
                | (
                    {"STATIC_CYCLE_COMPARISON_MISMATCH"}
                    if cycle_comparison == "MISMATCH"
                    else set()
                )
                | {"DYNAMIC_IMPORTS_OUTSIDE_DECLARED_STATIC_SCOPE"}
            ),
        }
        if import_uncertainties:
            scope_uncertainties.extend(import_uncertainties)
    inspection_unit = "file"
    overall_status = (
        "COMPLETE_FOR_DECLARED_STATIC_SOURCE_SCOPE"
        if source_scope_status == "COMPLETE"
        else "INCOMPLETE_OR_UNRESOLVED"
    )
    if dependency_analysis is not None:
        if (
            source_scope_status == "COMPLETE"
            and dependency_analysis["static_relationship_comparison"] == "MATCHED"
            and dependency_analysis["cycle_comparison"] == "MATCHED"
        ):
            overall_status = "STATIC_SCOPE_MATCHED_DYNAMIC_EDGE_COMPLETENESS_UNKNOWN"
        else:
            overall_status = "INCOMPLETE_OR_UNRESOLVED"

    return {
        "schema_version": "MONO_CI_PSI_INSPECTION_COVERAGE_V1",
        "architecture_state": architecture_state,
        "evaluator_id": evaluator_id,
        "inspection_unit": inspection_unit,
        "expected_subjects": expected_subjects,
        "inspected_subjects": actual_subjects,
        "missing_subjects": missing,
        "unexpected_subjects": unexpected,
        "altered_subjects": altered,
        "verified_matching_subjects": verified_matching,
        "counts": counts,
        "source_inspection_status": source_scope_status,
        "overall_completeness": overall_status,
        "uncertainties": sorted(set(scope_uncertainties)),
        "source_inventory": source_rows,
        "dependency_analysis": dependency_analysis,
        "evidence_sources": {
            "source_commit_sha": source_commit_sha,
            "source_tree_sha": source_tree_sha,
            "evaluator_configuration_sha256": config_sha256,
            "state_manifest_sha256": manifest_sha256,
            "evaluator_output_sha256": output_sha256,
            "source_scope_sha256": sha256_bytes(canonical_json_bytes(dict(source_scope))),
        },
    }


def assess_adaptation_necessity(case: Mapping[str, Any]) -> dict[str, Any]:
    """Compare independent architecture requirements with typed evaluator capabilities.

    Requirement records must name a source kind that is independent of the
    evaluator configuration. Matching labels are never evidence of semantic
    coverage: only the versioned, structured mappings below can compare a
    requirement to a capability. This DEVELOPMENT diagnostic does not emit or
    alter Method Ψ operations.
    """
    before_sha = case.get("configuration_sha256_before")
    after_sha = case.get("configuration_sha256_after")
    if not isinstance(before_sha, str) or not _SHA256.fullmatch(before_sha):
        raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_CONFIG_IDENTITY_INVALID")
    if not isinstance(after_sha, str) or not _SHA256.fullmatch(after_sha):
        raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_CONFIG_IDENTITY_INVALID")

    requirements = case.get("requirements_after")
    capabilities = case.get("capabilities_after")
    mappings = case.get("requirement_capability_mappings")
    unresolved_requirements = case.get("unresolved_requirements_after")
    if (
        not isinstance(requirements, list)
        or not isinstance(capabilities, list)
        or not isinstance(mappings, list)
        or not isinstance(unresolved_requirements, list)
    ):
        raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_INVENTORY_INVALID")

    comparisons, missing_controls, comparison_reasons = _compare_requirement_capabilities(
        requirements=requirements,
        capabilities=capabilities,
        mappings=mappings,
        state=str(case.get("architecture_state_after", "")),
    )

    mismatches: list[str] = []
    if case.get("evaluator_identity_verified") is not True:
        mismatches.append("EVALUATOR_IDENTITY_MISMATCH")
    if case.get("architecture_identity_verified") is not True:
        mismatches.append("ARCHITECTURE_IDENTITY_MISMATCH")
    if case.get("configuration_identity_verified") is not True:
        mismatches.append("CONFIGURATION_IDENTITY_MISMATCH")

    evidence_ready = (
        case.get("source_inspection_before") == "COMPLETE"
        and case.get("source_inspection_after") == "COMPLETE"
        and case.get("evaluator_compliance_before") == "COMPLIANT"
        and case.get("evaluator_compliance_after") == "COMPLIANT"
        and case.get("rule_scope_match_before") is True
        and case.get("rule_scope_match_after") is True
    )
    inventory_reasons: list[str] = []
    if case.get("requirement_inventory_status_after") != "COMPLETE_FOR_DECLARED_MANIFEST_TYPES":
        inventory_reasons.append("REQUIREMENT_INVENTORY_INCOMPLETE_WITHIN_DECLARED_SCOPE")
    if case.get("requirement_universe_completeness_after") != "COMPLETE_WITHIN_DECLARED_SCOPE":
        inventory_reasons.append("REQUIREMENT_UNIVERSE_COMPLETENESS_UNKNOWN")
    if case.get("capability_inventory_status_after") != "VERIFIED_FOR_DECLARED_STATIC_SCOPE":
        inventory_reasons.append("EVALUATOR_CAPABILITY_INVENTORY_NOT_VERIFIED")
    if unresolved_requirements:
        inventory_reasons.append("INDEPENDENT_REQUIREMENTS_REMAIN_UNRESOLVED")
    if case.get("normative_applicability") != "APPROVED":
        inventory_reasons.append("NORMATIVE_APPLICABILITY_NOT_APPROVED")

    if mismatches:
        status = "MISMATCH_DETECTED"
        reason_codes = mismatches
    elif not evidence_ready:
        status = "NOT_EVALUABLE"
        reason_codes = ["INSUFFICIENT_VERIFIED_SCOPE_OR_COMPLIANCE_EVIDENCE"]
    elif before_sha != after_sha:
        status = "NOT_EVALUABLE"
        reason_codes = ["BEFORE_AFTER_CONFIGURATION_IDENTITY_CHANGED"]
    elif missing_controls and not inventory_reasons and not comparison_reasons:
        status = "ADAPTATION_NEEDED"
        reason_codes = ["REQUIRED_POST_TRANSITION_CONTROLS_UNREPRESENTED"]
    elif comparison_reasons or inventory_reasons:
        status = "NOT_EVALUABLE"
        reason_codes = sorted(set(comparison_reasons + inventory_reasons))
    elif missing_controls:
        status = "NOT_EVALUABLE"
        reason_codes = ["UNREPRESENTED_CONTROL_WITH_UNRESOLVED_EVIDENCE"]
    else:
        status = "RETAIN_CANDIDATE"
        reason_codes = ["EXISTING_CONFIGURATION_COVERS_VERIFIED_POST_TRANSITION_SCOPE"]

    pair_semantic = case.get("pair_semantic_validity")
    missing_proofs = sorted(
        reason
        for condition, reason in (
            (pair_semantic != "VALID", "INDEPENDENT_PAIR_SEMANTIC_VALIDITY_NOT_ESTABLISHED"),
            (
                case.get("normative_applicability") != "APPROVED",
                "NORMATIVE_APPLICABILITY_NOT_APPROVED",
            ),
            (case.get("baseline_identity") != "HISTORICAL", "BASELINE_NOT_HISTORICALLY_IDENTIFIED"),
            (case.get("independent_review") is not True, "INDEPENDENT_REVIEW_NOT_PERFORMED"),
            *[(reason in inventory_reasons, reason) for reason in inventory_reasons],
            *[(reason in comparison_reasons, reason) for reason in comparison_reasons],
        )
        if condition
    )
    operation_justification = {
        "ADD": "UNSUPPORTED",
        "REPLACE": "UNSUPPORTED",
        "RETAIN": "TECHNICAL_CANDIDATE_ONLY" if status == "RETAIN_CANDIDATE" else "UNSUPPORTED",
        "HOLD": "REQUIRED_PENDING_FORMAL_AUTHORITY_OR_MISSING_PROOFS"
        if missing_proofs or status in {"NOT_EVALUABLE", "MISMATCH_DETECTED"}
        else "REVIEW_REQUIRED",
    }
    return {
        "assessment_status": status,
        "reason_codes": sorted(set(reason_codes)),
        "missing_post_transition_controls": missing_controls,
        "requirement_capability_comparison": comparisons,
        "missing_proofs": missing_proofs,
        "operation_justification": operation_justification,
    }


def _compare_requirement_capabilities(
    *,
    requirements: list[Any],
    capabilities: list[Any],
    mappings: list[Any],
    state: str,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    requirement_ids: set[str] = set()
    capability_by_type: dict[str, Mapping[str, Any]] = {}
    mapping_by_type: dict[str, Mapping[str, Any]] = {}
    for capability in capabilities:
        if not isinstance(capability, Mapping):
            raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_CAPABILITY_INVALID")
        capability_type = capability.get("capability_type")
        if not isinstance(capability_type, str) or capability_type in capability_by_type:
            raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_CAPABILITY_INVALID")
        capability_by_type[capability_type] = capability
    for mapping in mappings:
        if not isinstance(mapping, Mapping):
            raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_MAPPING_INVALID")
        requirement_type = mapping.get("requirement_type")
        if not isinstance(requirement_type, str) or requirement_type in mapping_by_type:
            raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_MAPPING_INVALID")
        mapping_by_type[requirement_type] = mapping

    comparisons: list[dict[str, Any]] = []
    missing_controls: list[str] = []
    unresolved_reasons: set[str] = set()
    for requirement in requirements:
        if not isinstance(requirement, Mapping):
            raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_REQUIREMENT_INVALID")
        control_id = requirement.get("control_id")
        requirement_type = requirement.get("requirement_type")
        if (
            not isinstance(control_id, str)
            or not control_id
            or control_id in requirement_ids
            or not isinstance(requirement_type, str)
        ):
            raise ContractValidationError("PSI_ADAPTATION_ASSESSMENT_REQUIREMENT_INVALID")
        requirement_ids.add(control_id)
        source_ref = requirement.get("source_ref")
        independent_source = (
            requirement.get("source_kind") in _INDEPENDENT_REQUIREMENT_SOURCE_KINDS
            and isinstance(source_ref, Mapping)
            and isinstance(source_ref.get("path"), str)
            and bool(source_ref.get("path"))
            and isinstance(source_ref.get("sha256"), str)
            and _SHA256.fullmatch(source_ref["sha256"]) is not None
        )
        mapping_spec = _REQUIREMENT_CAPABILITY_MAPPINGS.get(requirement_type)
        mapping = mapping_by_type.get(requirement_type)
        capability: Mapping[str, Any] | None = None
        mapping_id: str | None = None
        capability_id: str | None = None
        if mapping_spec is not None and mapping is not None:
            capability = capability_by_type.get(mapping_spec["capability_type"])
            raw_id = mapping.get("mapping_id")
            if isinstance(raw_id, str):
                mapping_id = raw_id
            if capability is not None and isinstance(capability.get("capability_id"), str):
                capability_id = str(capability["capability_id"])

        result = "UNRESOLVED"
        reason: str | None = None
        if not independent_source:
            reason = "REQUIREMENT_SOURCE_NOT_INDEPENDENT_OR_NOT_DIGEST_BOUND"
            unresolved_reasons.add("REQUIREMENT_SOURCE_NOT_INDEPENDENT_OR_NOT_DIGEST_BOUND")
        elif requirement.get("detail_status") != "SPECIFIED":
            reason = "INDEPENDENT_REQUIREMENT_DETAIL_UNRESOLVED"
            unresolved_reasons.add("INDEPENDENT_REQUIREMENT_DETAIL_UNRESOLVED")
        elif mapping_spec is None or mapping is None:
            reason = "REQUIREMENT_CAPABILITY_MAPPING_UNVERIFIED"
            unresolved_reasons.add("REQUIREMENT_CAPABILITY_MAPPING_UNVERIFIED")
        elif (
            mapping.get("mapping_id") != mapping_spec["mapping_id"]
            or mapping.get("status") != "VERIFIED_RULE_IMPLEMENTATION"
            or mapping.get("comparison_rule") != mapping_spec["comparison_rule"]
            or mapping.get("capability_type") != mapping_spec["capability_type"]
        ):
            reason = "REQUIREMENT_CAPABILITY_MAPPING_UNVERIFIED"
            unresolved_reasons.add("REQUIREMENT_CAPABILITY_MAPPING_UNVERIFIED")
        elif capability is None:
            result = "NOT_COVERED"
            reason = "MAPPED_EVALUATOR_CAPABILITY_NOT_DECLARED"
            missing_controls.append(control_id)
        elif capability.get("verification_status") != "VERIFIED_STATIC_SCOPE":
            reason = "EVALUATOR_CAPABILITY_NOT_VERIFIED"
            unresolved_reasons.add("EVALUATOR_CAPABILITY_NOT_VERIFIED")
        else:
            matched = _mapped_requirement_is_covered(
                requirement_type=requirement_type,
                requirement_value=requirement.get("value"),
                capability_value=capability.get("value"),
                state=state,
            )
            if matched is None:
                reason = "REQUIREMENT_CAPABILITY_SEMANTICS_UNRESOLVED"
                unresolved_reasons.add("REQUIREMENT_CAPABILITY_SEMANTICS_UNRESOLVED")
            elif matched:
                result = "COVERED"
            else:
                result = "NOT_COVERED"
                reason = "REQUIRED_CONTROL_NOT_REPRESENTED_BY_VERIFIED_CAPABILITY"
                missing_controls.append(control_id)
        comparisons.append(
            {
                "control_id": control_id,
                "requirement_type": requirement_type,
                "capability_id": capability_id,
                "mapping_id": mapping_id,
                "mapping_status": (
                    "VERIFIED_RULE_IMPLEMENTATION"
                    if mapping_spec is not None
                    and mapping is not None
                    and mapping.get("mapping_id") == mapping_spec["mapping_id"]
                    and mapping.get("status") == "VERIFIED_RULE_IMPLEMENTATION"
                    and mapping.get("comparison_rule") == mapping_spec["comparison_rule"]
                    and mapping.get("capability_type") == mapping_spec["capability_type"]
                    else "UNVERIFIED"
                ),
                "comparison_result": result,
                "reason": reason,
            }
        )
    return (
        sorted(comparisons, key=lambda row: row["control_id"]),
        sorted(set(missing_controls)),
        sorted(unresolved_reasons),
    )


def _mapped_requirement_is_covered(
    *,
    requirement_type: str,
    requirement_value: Any,
    capability_value: Any,
    state: str,
) -> bool | None:
    if not isinstance(requirement_value, Mapping) or not isinstance(capability_value, Mapping):
        return None
    if requirement_type == "architecture.module_graph.allowed_dependency":
        edges = capability_value.get("edges")
        if not isinstance(edges, list):
            return None
        return any(edge == dict(requirement_value) for edge in edges if isinstance(edge, Mapping))
    if requirement_type == "architecture.public_api.reporting_query_port":
        required_fields = (
            "source_module",
            "public_target_module",
            "public_imported_name",
            "forbidden_target_module",
            "forbidden_imported_name",
        )
        if any(not isinstance(requirement_value.get(key), str) for key in required_fields):
            return None
        target_module = str(requirement_value["public_target_module"])
        target_parts = target_module.split(".")
        if len(target_parts) < 4 or target_parts[:2] != ["app", "modules"]:
            return None
        capability_name = target_parts[2]
        public_pattern = capability_value.get("public_module_pattern")
        interfaces = capability_value.get("interfaces_by_capability")
        exports = capability_value.get("exports_by_capability")
        imports = capability_value.get("cross_capability_imports")
        exception = capability_value.get("legacy_exception")
        if (
            not isinstance(public_pattern, str)
            or not isinstance(interfaces, Mapping)
            or not isinstance(exports, Mapping)
            or not isinstance(imports, list)
        ):
            return None
        expected_pattern = public_pattern.replace("{capability}", capability_name)
        public_name = str(requirement_value["public_imported_name"])
        declared = interfaces.get(capability_name)
        exported = exports.get(capability_name)
        observed_public_import = any(
            isinstance(row, Mapping)
            and row.get("source_module") == requirement_value["source_module"]
            and row.get("target_module") == target_module
            and row.get("imported_name") == public_name
            and row.get("classification") == "declared_public_interface"
            for row in imports
        )
        observed_forbidden_import = any(
            isinstance(row, Mapping)
            and row.get("source_module") == requirement_value["source_module"]
            and row.get("target_module") == requirement_value["forbidden_target_module"]
            and row.get("imported_name") == requirement_value["forbidden_imported_name"]
            for row in imports
        )
        exception_active = (
            isinstance(exception, Mapping)
            and state in exception.get("allowed_architecture_states", [])
            and exception.get("source_module") == requirement_value["source_module"]
            and exception.get("target_module") == requirement_value["forbidden_target_module"]
            and requirement_value["forbidden_imported_name"] in exception.get("imported_names", [])
        )
        return (
            expected_pattern == target_module
            and isinstance(declared, Mapping)
            and declared.get(public_name) == "function"
            and isinstance(exported, Mapping)
            and exported.get(public_name) == "function"
            and observed_public_import
            and not observed_forbidden_import
            and not exception_active
        )
    if requirement_type == "architecture.public_api.temporary_exception":
        configured = capability_value.get("legacy_exception")
        if not isinstance(configured, Mapping):
            return False
        return (
            configured.get("id") == requirement_value.get("id")
            and configured.get("source_module") == requirement_value.get("source_module")
            and configured.get("target_module") == requirement_value.get("target_module")
            and set(configured.get("imported_names", []))
            == set(requirement_value.get("imported_names", []))
            and state in configured.get("allowed_architecture_states", [])
            and state in requirement_value.get("allowed_architecture_states", [])
        )
    if requirement_type == "architecture.data_ownership.persistence_ownership":
        table_owners = capability_value.get("table_owners")
        prohibited = capability_value.get("prohibited_access_patterns")
        registry_exception = capability_value.get("model_registry_exception")
        if (
            not isinstance(table_owners, Mapping)
            or not isinstance(prohibited, list)
            or not isinstance(registry_exception, Mapping)
        ):
            return None
        required_ownership = requirement_value.get("table_owners")
        required_patterns = requirement_value.get("prohibited_access_patterns")
        required_exception = requirement_value.get("model_registry_exception")
        if (
            not isinstance(required_ownership, Mapping)
            or not isinstance(required_patterns, list)
            or not isinstance(required_exception, Mapping)
        ):
            return None
        return (
            dict(table_owners) == dict(required_ownership)
            and set(prohibited) >= set(required_patterns)
            and dict(registry_exception) == dict(required_exception)
            and state == "A0_5_MODULE_DATA_OWNERSHIP"
        )
    return None


def _manifest_requires_evaluator(manifest: Mapping[str, Any], evaluator_id: str) -> bool:
    governance = manifest.get("governance_requirements")
    required = governance.get("required_evaluators") if isinstance(governance, Mapping) else None
    return isinstance(required, list) and evaluator_id in required


def _safe_relative_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path.as_posix()


def _git_tree_entries(repository: Any, commit: str, pathspec: str) -> dict[str, dict[str, str]]:
    raw = _git_bytes(repository, "ls-tree", "-r", "-z", "--full-tree", commit, "--", pathspec)
    entries: dict[str, dict[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, separator, path_bytes = record.partition(b"\t")
        parts = metadata.decode("ascii").split()
        if not separator or len(parts) != 3 or parts[1] != "blob":
            raise ContractValidationError("PSI_GIT_SOURCE_INVENTORY_INVALID")
        try:
            path = path_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContractValidationError("PSI_GIT_SOURCE_INVENTORY_INVALID") from error
        entries[path] = {"mode": parts[0], "blob_sha1": parts[2]}
    return entries


def _git_blob(repository: Any, commit: str, path: str) -> bytes:
    if _safe_relative_path(path) != path:
        raise ContractValidationError("PSI_GIT_SOURCE_PATH_INVALID")
    return _git_bytes(repository, "show", f"{commit}:{path}")


def _git_bytes(repository: Any, *args: str) -> bytes:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ContractValidationError("PSI_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # noqa: S603  # nosec B603 - fixed read-only Git subcommands
        [git_binary, *args], cwd=repository, check=False, capture_output=True, timeout=30
    )
    if result.returncode != 0:
        raise ContractValidationError("PSI_GIT_SOURCE_READBACK_FAILED")
    return result.stdout


def _git_text(repository: Any, *args: str) -> str:
    try:
        return _git_bytes(repository, *args).decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise ContractValidationError("PSI_GIT_SOURCE_READBACK_FAILED") from error


def _observed_file_scope(
    source_scope: Mapping[str, Any],
) -> tuple[list[str], list[dict[str, str]], list[str]]:
    paths = source_scope.get("inspected_paths")
    digest_rows = source_scope.get("source_file_digests")
    errors: list[str] = []
    if not isinstance(paths, list) or not isinstance(digest_rows, list):
        return [], [], ["EVALUATOR_INSPECTION_INVENTORY_MISSING"]
    if any(not isinstance(path, str) or _safe_relative_path(path) != path for path in paths):
        errors.append("EVALUATOR_INSPECTION_PATH_INVALID")
        paths = [path for path in paths if isinstance(path, str)]
    if paths != sorted(set(paths)):
        errors.append("EVALUATOR_INSPECTION_PATH_ORDER_OR_DUPLICATE")
    rows: list[dict[str, str]] = []
    for row in digest_rows:
        if (
            not isinstance(row, Mapping)
            or not isinstance(row.get("path"), str)
            or not isinstance(row.get("sha256"), str)
            or _SHA256.fullmatch(str(row.get("sha256"))) is None
        ):
            errors.append("EVALUATOR_SOURCE_DIGEST_RECORD_INVALID")
            continue
        rows.append({"path": str(row["path"]), "sha256": str(row["sha256"])})
    if [row["path"] for row in rows] != paths:
        errors.append("EVALUATOR_SOURCE_DIGEST_SCOPE_MISMATCH")
    return list(paths), rows, errors


def _independent_capability_imports(
    repository: Any,
    commit: str,
    source_rows: list[dict[str, str]],
    configured_modules: set[str],
    discovered_modules: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    paths = {row["path"]: row for row in source_rows}
    known_dotted_modules = {
        _module_name(path)
        for path in _git_tree_entries(repository, commit, "app")
        if path.endswith(".py")
    }
    known_modules = configured_modules | discovered_modules
    edges: list[dict[str, Any]] = []
    uncertainties: list[str] = []
    for path in sorted(paths):
        if not path.startswith("app/modules/") or not path.endswith(".py"):
            continue
        capability = path[len("app/modules/") :].split("/", 1)[0]
        if capability not in known_modules:
            continue
        source_module = _module_name(path)
        source_package = (
            source_module if path.endswith("/__init__.py") else source_module.rpartition(".")[0]
        )
        try:
            tree = ast.parse(_git_blob(repository, commit, path).decode("utf-8"), filename=path)
        except (OSError, UnicodeDecodeError, SyntaxError):
            uncertainties.append(f"SOURCE_IMPORT_PARSE_UNRESOLVED:{path}")
            continue
        for node in sorted(
            (item for item in ast.walk(tree) if isinstance(item, (ast.Import, ast.ImportFrom))),
            key=lambda item: (getattr(item, "lineno", 0), type(item).__name__),
        ):
            imports: list[tuple[str, str | None]] = []
            if isinstance(node, ast.Import):
                imports.extend((alias.name, None) for alias in node.names)
            else:
                for alias in node.names:
                    base = node.module or ""
                    if node.level:
                        try:
                            base = importlib.util.resolve_name(
                                "." * node.level + base, source_package
                            )
                        except (ImportError, ValueError):
                            uncertainties.append(
                                f"RELATIVE_IMPORT_RESOLUTION_UNRESOLVED:{path}:{node.lineno}"
                            )
                            continue
                    target = base
                    if (
                        alias.name != "*"
                        and base
                        and f"{base}.{alias.name}" in known_dotted_modules
                    ):
                        target = f"{base}.{alias.name}"
                    imports.append((target, alias.name))
            for target_module, imported_name in imports:
                target_capability = _capability(target_module, known_modules)
                if target_capability is None or target_capability == capability:
                    continue
                edges.append(
                    {
                        "from": capability,
                        "to": target_capability,
                        "source_path": path,
                        "line": int(getattr(node, "lineno", 0)),
                        "source_module": source_module,
                        "target_module": target_module,
                        "imported_name": imported_name,
                    }
                )
    edges.sort(key=_relationship_key)
    return edges, uncertainties


def _observed_capability_imports(
    diagnostics: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(diagnostics, Mapping) or not isinstance(diagnostics.get("edges"), list):
        return [], ["EVALUATOR_DEPENDENCY_EDGE_INVENTORY_MISSING"]
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for edge in diagnostics["edges"]:
        if (
            not isinstance(edge, Mapping)
            or not isinstance(edge.get("from"), str)
            or not isinstance(edge.get("to"), str)
            or not isinstance(edge.get("references"), list)
        ):
            errors.append("EVALUATOR_DEPENDENCY_EDGE_RECORD_INVALID")
            continue
        for ref in edge["references"]:
            if (
                not isinstance(ref, Mapping)
                or not isinstance(ref.get("source_path"), str)
                or type(ref.get("line")) is not int
                or not isinstance(ref.get("source_module"), str)
                or not isinstance(ref.get("target_module"), str)
                or ref.get("imported_name") is not None
                and not isinstance(ref.get("imported_name"), str)
            ):
                errors.append("EVALUATOR_DEPENDENCY_REFERENCE_INVALID")
                continue
            rows.append(
                {
                    "from": edge["from"],
                    "to": edge["to"],
                    "source_path": ref["source_path"],
                    "line": ref["line"],
                    "source_module": ref["source_module"],
                    "target_module": ref["target_module"],
                    "imported_name": ref.get("imported_name"),
                }
            )
    rows.sort(key=_relationship_key)
    return rows, errors


def _observed_cycle_paths(diagnostics: Any) -> tuple[list[list[str]], list[str]]:
    if not isinstance(diagnostics, Mapping):
        return [], ["EVALUATOR_GRAPH_DIAGNOSTICS_MISSING"]
    cycles = diagnostics.get("cycles")
    if not isinstance(cycles, list):
        return [], ["EVALUATOR_GRAPH_CYCLE_INVENTORY_MISSING"]
    output: list[list[str]] = []
    errors: list[str] = []
    for cycle in cycles:
        if (
            not isinstance(cycle, list)
            or len(cycle) < 2
            or any(not isinstance(item, str) or not item for item in cycle)
            or cycle[0] != cycle[-1]
        ):
            errors.append("EVALUATOR_GRAPH_CYCLE_RECORD_INVALID")
            continue
        output.append(list(cycle))
    if [tuple(item) for item in output] != sorted(set(tuple(item) for item in output)):
        errors.append("EVALUATOR_GRAPH_CYCLE_ORDER_OR_DUPLICATE")
    return output, errors


def _cycle_paths(nodes: set[str], edges: set[tuple[str, str]]) -> list[list[str]]:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for source, target in edges:
        if source in nodes and target in nodes:
            adjacency[source].add(target)
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str], positions: dict[str, int], visited: set[str]) -> None:
        for target in sorted(adjacency[node]):
            if target in positions:
                body = path[positions[target] :]
                rotations = [tuple(body[index:] + body[:index]) for index in range(len(body))]
                canonical = min(rotations)
                cycles.add(canonical + (canonical[0],))
            elif target not in visited:
                visit(target, [*path, target], {**positions, target: len(path)}, visited)
        visited.add(node)

    for start in sorted(nodes):
        visit(start, [start], {start: 0}, set())
    return [list(cycle) for cycle in sorted(cycles)]


def _module_name(path: str) -> str:
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _capability(module: str, known: set[str]) -> str | None:
    prefix = "app.modules."
    if not module.startswith(prefix):
        return None
    capability = module[len(prefix) :].split(".", 1)[0]
    return capability if capability in known else None


def _relationship_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("from"),
        row.get("to"),
        row.get("source_path"),
        row.get("line"),
        row.get("target_module"),
        row.get("imported_name") or "",
    )


def _counter_difference(
    left: Sequence[dict[str, Any]], right: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    left_counter = Counter(canonical_json_bytes(row) for row in left)
    right_counter = Counter(canonical_json_bytes(row) for row in right)
    needed = left_counter - right_counter
    lookup = {canonical_json_bytes(row): row for row in left}
    return [lookup[key] for key in sorted(needed) for _ in range(needed[key])]


def _edge_subjects(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({f"{row['from']}->{row['to']}" for row in rows})


def _configured_edges(config: Mapping[str, Any], architecture_state: str) -> list[dict[str, str]]:
    module_graph = config.get("module_graph")
    by_state = (
        module_graph.get("allowed_dependencies_by_state")
        if isinstance(module_graph, Mapping)
        else None
    )
    rows = by_state.get(architecture_state) if isinstance(by_state, Mapping) else None
    if not isinstance(rows, list):
        return []
    output = [
        {"from": str(row["from"]), "to": str(row["to"])}
        for row in rows
        if isinstance(row, Mapping)
        and isinstance(row.get("from"), str)
        and isinstance(row.get("to"), str)
    ]
    return sorted(output, key=lambda row: (row["from"], row["to"]))


__all__ = ["assess_adaptation_necessity", "verify_inspection_coverage"]
