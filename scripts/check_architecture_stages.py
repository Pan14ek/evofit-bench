"""Stage-aware architecture checks without rewriting the frozen DA01 acceptance.

Historical A0.1 acceptance is executed from exactly pinned Git archive bytes,
never against the evolving application worktree. Current-source checks have
an explicitly limited stage scope; their PASS is not Method P or A1 approval.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess  # nosec B404 - fixed local Git and interpreter commands only
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import yaml

from architecture.acceptance.a1.analyzers import ANALYZERS
from architecture.acceptance.a1.engine import (
    canonical_json,
    run_evaluator,
    verify_evidence,
)

HISTORICAL_A01_SHA = "3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306"
HISTORICAL_APP_TREE = "cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08"
HISTORICAL_A03_SHA = "26a9bb667da7d0938e38aca15d2bf29fd1de4829"
HISTORICAL_A03_TREE = "7b951421395f532ca403dab09d76902ff08a807d"
HISTORICAL_A03_APP_TREE = "b147b8961ea9e76c966663d4832e4c303581151a"
MODULES = ("users", "tasks", "notifications", "reporting", "audit")
A01 = "A0_1_CAPABILITY_MODULES"
A02 = "A0_2_PUBLIC_MODULE_APIS"
A03 = "A0_3_GOVERNED_MODULE_GRAPH"
A04 = "A0_4_REPORT_QUERY_PORT"
ALLOWED_STAGES = ("auto", A01, A02, A03, A04)
A03_MANIFEST = "architecture/states/A0_3_GOVERNED_MODULE_GRAPH.yaml"
A03_SCHEMA = "architecture/states/A0_3_GOVERNED_MODULE_GRAPH.schema.json"
A04_MANIFEST = "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
A04_SCHEMA = "architecture/states/A0_4_REPORT_QUERY_PORT.schema.json"
A03_REQUIRED_EVALUATORS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH")
A04_REQUIRED_EVALUATORS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH")
A03_DEPENDENCIES = {
    ("tasks", "users"),
    ("tasks", "notifications"),
    ("tasks", "audit"),
    ("users", "audit"),
    ("reporting", "tasks"),
}
A03_REPORTING_EXCEPTION = {
    "id": "reporting_tasks_query_intermediate_v1",
    "source_module": "app.modules.reporting.service",
    "target_module": "app.modules.tasks.service",
    "imported_names": ["task_summary"],
    "allowed_architecture_states": [A02, A03],
    "expires_at_state": "A0_4_REPORT_QUERY_PORT",
}
A04_DEPENDENCIES = A03_DEPENDENCIES
A04_REPORTING_QUERY_PORT = {
    "source_module": "app.modules.reporting.service",
    "public_target_module": "app.modules.tasks.public",
    "public_imported_name": "get_task_summary",
    "forbidden_target_module": "app.modules.tasks.service",
    "forbidden_imported_name": "task_summary",
}


class StageCheckError(RuntimeError):
    """Fail-closed architecture-stage/checkpoint error."""


def _git(root: Path, *arguments: str) -> str:
    git = shutil.which("git")
    if git is None:
        raise StageCheckError("Git executable unavailable")
    result = subprocess.run(  # noqa: S603  # nosec B603 - fixed Git argv, no shell
        [git, "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise StageCheckError(
            f"Git {arguments[0]} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _read_yaml(path: Path, *, error_code: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise StageCheckError(f"{error_code}: {error}") from error
    if not isinstance(value, dict):
        raise StageCheckError(f"{error_code}: expected a YAML mapping")
    return value


def _edge_set(value: Any, *, error_code: str) -> set[tuple[str, str]]:
    if not isinstance(value, list):
        raise StageCheckError(error_code)
    edges: set[tuple[str, str]] = set()
    for edge in value:
        if (
            not isinstance(edge, dict)
            or not isinstance(edge.get("from"), str)
            or not isinstance(edge.get("to"), str)
        ):
            raise StageCheckError(error_code)
        edges.add((str(edge["from"]), str(edge["to"])))
    if len(edges) != len(value):
        raise StageCheckError(error_code)
    return edges


def _mapping(value: Any, *, error_code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StageCheckError(error_code)
    return value


def _validate_a03_manifest(root: Path) -> dict[str, Any]:
    """Require the explicit, versioned ΔA3 contract; APIs alone identify only ΔA2."""
    manifest_path = root / A03_MANIFEST
    schema_path = root / A03_SCHEMA
    manifest = _read_yaml(manifest_path, error_code="A0.3_MANIFEST_INVALID")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(manifest)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        jsonschema.SchemaError,
        jsonschema.ValidationError,
    ) as error:
        raise StageCheckError(f"A0.3_MANIFEST_SCHEMA_INVALID: {error}") from error

    if manifest.get("architecture_state") != A03 or manifest.get("predecessor_state") != A02:
        raise StageCheckError("A0.3_MANIFEST_STATE_OR_PREDECESSOR_MISMATCH")
    if _edge_set(manifest.get("allowed_dependencies"), error_code="A0.3_GRAPH_INVALID") != (
        A03_DEPENDENCIES
    ):
        raise StageCheckError("A0.3_MANIFEST_GRAPH_MISMATCH")
    governance = manifest.get("governance_requirements")
    if not isinstance(governance, dict) or governance.get("required_evaluators") != list(
        A03_REQUIRED_EVALUATORS
    ):
        raise StageCheckError("A0.3_REQUIRED_EVALUATORS_MISMATCH")
    exception = manifest.get("temporary_exceptions")
    if exception != [A03_REPORTING_EXCEPTION]:
        raise StageCheckError("A0.3_REPORTING_EXCEPTION_MISMATCH")
    provenance = manifest.get("source_provenance")
    if (
        not isinstance(provenance, dict)
        or provenance.get("predecessor_commit") != ("b003144ae78238707af555aee68a16ffa14e800b")
        or provenance.get("predecessor_tree") != "894f676d82a8264878ce4fb64a6c28d98a1c5fed"
    ):
        raise StageCheckError("A0.3_PREDECESSOR_PROVENANCE_MISMATCH")
    return manifest


def _validate_a04_manifest(root: Path) -> dict[str, Any]:
    """Require the versioned ΔA4 contract and retain the historical ΔA3 record."""
    # A0.3 remains a readable, unchanged predecessor record at A0.4.
    _validate_a03_manifest(root)
    manifest_path = root / A04_MANIFEST
    schema_path = root / A04_SCHEMA
    manifest = _read_yaml(manifest_path, error_code="A0.4_MANIFEST_INVALID")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(manifest)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        jsonschema.SchemaError,
        jsonschema.ValidationError,
    ) as error:
        raise StageCheckError(f"A0.4_MANIFEST_SCHEMA_INVALID: {error}") from error

    if manifest.get("architecture_state") != A04 or manifest.get("predecessor_state") != A03:
        raise StageCheckError("A0.4_MANIFEST_STATE_OR_PREDECESSOR_MISMATCH")
    if _edge_set(manifest.get("allowed_dependencies"), error_code="A0.4_GRAPH_INVALID") != (
        A04_DEPENDENCIES
    ):
        raise StageCheckError("A0.4_MANIFEST_GRAPH_MISMATCH")
    if manifest.get("reporting_query_port") != A04_REPORTING_QUERY_PORT:
        raise StageCheckError("A0.4_REPORTING_QUERY_PORT_MISMATCH")
    if manifest.get("temporary_exceptions") != []:
        raise StageCheckError("A0.4_TEMPORARY_EXCEPTION_PRESENT")
    governance = manifest.get("governance_requirements")
    if not isinstance(governance, dict):
        raise StageCheckError("A0.4_GOVERNANCE_REQUIREMENTS_INVALID")
    if governance.get("required_evaluators") != list(A04_REQUIRED_EVALUATORS):
        raise StageCheckError("A0.4_REQUIRED_EVALUATORS_MISMATCH")
    if governance.get("not_applicable_evaluators") != {"AC_DATA_OWNERSHIP": "NOT_APPLICABLE"}:
        raise StageCheckError("A0.4_DATA_OWNERSHIP_APPLICABILITY_MISMATCH")
    provenance = manifest.get("source_provenance")
    if (
        not isinstance(provenance, dict)
        or provenance.get("predecessor_commit") != HISTORICAL_A03_SHA
        or provenance.get("predecessor_tree") != HISTORICAL_A03_TREE
        or provenance.get("predecessor_application_tree") != HISTORICAL_A03_APP_TREE
    ):
        raise StageCheckError("A0.4_PREDECESSOR_PROVENANCE_MISMATCH")
    return manifest


def _a03_manifest_was_established(root: Path) -> bool:
    """Return whether an A0.3 manifest was added on this checkout's ancestry.

    The revision is deliberately resolved from HEAD history rather than from
    a hardcoded future merge SHA. Historical A0.2 commits therefore remain
    A0.2 even when later A0.3 commits exist elsewhere in the repository.
    """
    if not any((parent / ".git").exists() for parent in (root, *root.parents)):
        # Pure synthetic source fixtures have no lineage. The architecture
        # acceptance entry point separately requires a Git-backed checkout.
        return False
    additions = _git(
        root,
        "log",
        "--format=%H",
        "--diff-filter=A",
        "HEAD",
        "--",
        A03_MANIFEST,
    )
    return bool(additions)


def _a04_manifest_was_established(root: Path) -> bool:
    """Return whether an A0.4 manifest was added on this checkout's ancestry."""
    if not any((parent / ".git").exists() for parent in (root, *root.parents)):
        return False
    additions = _git(
        root,
        "log",
        "--format=%H",
        "--diff-filter=A",
        "HEAD",
        "--",
        A04_MANIFEST,
    )
    return bool(additions)


def _validate_a03_policy_bindings(root: Path, manifest: dict[str, Any]) -> None:
    """Reject drift between the state record and the evaluator configurations."""
    evaluator_root = root / "architecture/acceptance/a1"
    public = _read_yaml(
        evaluator_root / "public_api_v1.yaml", error_code="A0.3_PUBLIC_CONFIG_INVALID"
    )
    graph = _read_yaml(
        evaluator_root / "module_graph_v1.yaml", error_code="A0.3_GRAPH_CONFIG_INVALID"
    )
    public_evaluator = _mapping(public.get("evaluator"), error_code="A0.3_EVALUATOR_CONFIG_INVALID")
    graph_evaluator = _mapping(graph.get("evaluator"), error_code="A0.3_EVALUATOR_CONFIG_INVALID")
    public_states = _mapping(public.get("states"), error_code="A0.3_EVALUATOR_CONFIG_INVALID")
    graph_states = _mapping(graph.get("states"), error_code="A0.3_EVALUATOR_CONFIG_INVALID")
    public_scope = _mapping(public.get("source_scope"), error_code="A0.3_EVALUATOR_CONFIG_INVALID")
    graph_scope = _mapping(graph.get("source_scope"), error_code="A0.3_EVALUATOR_CONFIG_INVALID")
    graph_policy = _mapping(graph.get("module_graph"), error_code="A0.3_EVALUATOR_CONFIG_INVALID")
    public_policy = _mapping(public.get("public_api"), error_code="A0.3_EVALUATOR_CONFIG_INVALID")
    if (
        public_evaluator.get("id") != "AC_PUBLIC_API"
        or graph_evaluator.get("id") != "AC_MODULE_GRAPH"
    ):
        raise StageCheckError("A0.3_EVALUATOR_CONFIG_ID_MISMATCH")
    public_state = _mapping(public_states.get(A03), error_code="A0.3_EVALUATOR_NOT_ACTIVE")
    graph_state = _mapping(graph_states.get(A03), error_code="A0.3_EVALUATOR_NOT_ACTIVE")
    if (
        public_state.get("applicability") != "ACTIVE"
        or graph_state.get("applicability") != "ACTIVE"
    ):
        raise StageCheckError("A0.3_EVALUATOR_NOT_ACTIVE")
    expected_modules = list(MODULES)
    for scope in (public_scope, graph_scope):
        if scope.get("expected_modules") != expected_modules:
            raise StageCheckError("A0.3_EVALUATOR_SCOPE_MISMATCH")
    allowed_by_state = _mapping(
        graph_policy.get("allowed_dependencies_by_state"),
        error_code="A0.3_GRAPH_CONFIG_INVALID",
    )
    configured_edges = _edge_set(
        allowed_by_state.get(A03),
        error_code="A0.3_GRAPH_CONFIG_INVALID",
    )
    manifest_edges = _edge_set(
        manifest.get("allowed_dependencies"), error_code="A0.3_GRAPH_INVALID"
    )
    if configured_edges != manifest_edges:
        raise StageCheckError("A0.3_GRAPH_CONFIG_MANIFEST_MISMATCH")
    exception = public_policy.get("legacy_exception")
    if exception != {
        key: value for key, value in A03_REPORTING_EXCEPTION.items() if key != "expires_at_state"
    }:
        raise StageCheckError("A0.3_PUBLIC_EXCEPTION_CONFIG_MISMATCH")


def _validate_a04_policy_bindings(root: Path, manifest: dict[str, Any]) -> None:
    """Bind A0.4's stage applicability and graph to the existing evaluator configs."""
    a03_manifest = _validate_a03_manifest(root)
    _validate_a03_policy_bindings(root, a03_manifest)
    evaluator_root = root / "architecture/acceptance/a1"
    public = _read_yaml(
        evaluator_root / "public_api_v1.yaml", error_code="A0.4_PUBLIC_CONFIG_INVALID"
    )
    graph = _read_yaml(
        evaluator_root / "module_graph_v1.yaml", error_code="A0.4_GRAPH_CONFIG_INVALID"
    )
    ownership = _read_yaml(
        evaluator_root / "data_ownership_v1.yaml", error_code="A0.4_OWNERSHIP_CONFIG_INVALID"
    )
    public_states = _mapping(public.get("states"), error_code="A0.4_EVALUATOR_CONFIG_INVALID")
    graph_states = _mapping(graph.get("states"), error_code="A0.4_EVALUATOR_CONFIG_INVALID")
    ownership_states = _mapping(ownership.get("states"), error_code="A0.4_EVALUATOR_CONFIG_INVALID")
    public_evaluator = _mapping(public.get("evaluator"), error_code="A0.4_EVALUATOR_CONFIG_INVALID")
    graph_evaluator = _mapping(graph.get("evaluator"), error_code="A0.4_EVALUATOR_CONFIG_INVALID")
    ownership_evaluator = _mapping(
        ownership.get("evaluator"), error_code="A0.4_EVALUATOR_CONFIG_INVALID"
    )
    if (
        _mapping(public_states.get(A04), error_code="A0.4_EVALUATOR_NOT_ACTIVE").get(
            "applicability"
        )
        != "ACTIVE"
        or _mapping(graph_states.get(A04), error_code="A0.4_EVALUATOR_NOT_ACTIVE").get(
            "applicability"
        )
        != "ACTIVE"
    ):
        raise StageCheckError("A0.4_REQUIRED_EVALUATOR_NOT_ACTIVE")
    if (
        _mapping(ownership_states.get(A04), error_code="A0.4_OWNERSHIP_NOT_NOT_APPLICABLE").get(
            "applicability"
        )
        != "NOT_APPLICABLE"
    ):
        raise StageCheckError("A0.4_OWNERSHIP_NOT_NOT_APPLICABLE")

    expected_modules = list(MODULES)
    for config in (public, graph, ownership):
        scope = _mapping(config.get("source_scope"), error_code="A0.4_EVALUATOR_CONFIG_INVALID")
        if scope.get("expected_modules") != expected_modules:
            raise StageCheckError("A0.4_EVALUATOR_SCOPE_MISMATCH")
    graph_policy = _mapping(graph.get("module_graph"), error_code="A0.4_GRAPH_CONFIG_INVALID")
    allowed_by_state = _mapping(
        graph_policy.get("allowed_dependencies_by_state"),
        error_code="A0.4_GRAPH_CONFIG_INVALID",
    )
    configured_edges = _edge_set(allowed_by_state.get(A04), error_code="A0.4_GRAPH_CONFIG_INVALID")
    manifest_edges = _edge_set(
        manifest.get("allowed_dependencies"), error_code="A0.4_GRAPH_INVALID"
    )
    if configured_edges != manifest_edges:
        raise StageCheckError("A0.4_GRAPH_CONFIG_MANIFEST_MISMATCH")
    if public_evaluator.get("id") != "AC_PUBLIC_API":
        raise StageCheckError("A0.4_PUBLIC_EVALUATOR_ID_MISMATCH")
    if graph_evaluator.get("id") != "AC_MODULE_GRAPH":
        raise StageCheckError("A0.4_GRAPH_EVALUATOR_ID_MISMATCH")
    if ownership_evaluator.get("id") != "AC_DATA_OWNERSHIP":
        raise StageCheckError("A0.4_OWNERSHIP_EVALUATOR_ID_MISMATCH")


def detect_stage(root: Path) -> str:
    """Recognize the latest established state; refuse partial or ambiguous APIs."""
    modules = root / "app" / "modules"
    missing_modules = [name for name in MODULES if not (modules / name / "__init__.py").is_file()]
    if missing_modules:
        raise StageCheckError(f"Missing capability modules: {missing_modules}")
    present = [name for name in MODULES if (modules / name / "public.py").is_file()]
    a04_manifest = root / A04_MANIFEST
    if a04_manifest.exists():
        _validate_a04_manifest(root)
        if len(present) != len(MODULES):
            raise StageCheckError(f"A0.4 state lacks complete public APIs: {present}")
        contract_test = root / "tests/unit/test_module_public_apis.py"
        if not contract_test.is_file():
            raise StageCheckError(
                f"A0.4 state lacks mandatory public API contract tests: {contract_test}"
            )
        return A04
    if _a04_manifest_was_established(root):
        raise StageCheckError("A0.4_MANIFEST_REMOVED_AFTER_ESTABLISHMENT")
    a03_manifest = root / A03_MANIFEST
    if a03_manifest.exists():
        _validate_a03_manifest(root)
        if len(present) != len(MODULES):
            raise StageCheckError(f"A0.3 state lacks complete public APIs: {present}")
        contract_test = root / "tests/unit/test_module_public_apis.py"
        if not contract_test.is_file():
            raise StageCheckError(
                f"A0.3 state lacks mandatory public API contract tests: {contract_test}"
            )
        return A03
    if _a03_manifest_was_established(root):
        raise StageCheckError("A0.3_MANIFEST_REMOVED_AFTER_ESTABLISHMENT")
    if not present:
        return A01
    if len(present) != len(MODULES):
        raise StageCheckError(f"Partial public API modules: {present}; expected all {MODULES}")
    contract_test = root / "tests/unit/test_module_public_apis.py"
    if not contract_test.is_file():
        raise StageCheckError(
            f"New public interfaces lack mandatory contract tests: {contract_test}"
        )
    return A02


def _validate_a03_evidence(
    evidence: dict[str, Any],
    *,
    evaluator_id: str,
    expected_source_sha: str,
    schema_path: Path,
    expected_architecture_state: str = A03,
) -> None:
    """Fail closed unless one evaluator produced complete, current, source-bound PASS evidence."""
    try:
        jsonschema.Draft202012Validator(
            json.loads(schema_path.read_text(encoding="utf-8"))
        ).validate(evidence)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, jsonschema.ValidationError) as error:
        raise StageCheckError(f"{evaluator_id} evidence schema failure: {error}") from error

    evaluator: dict[str, Any] = evidence.get("evaluator", {})
    architecture: dict[str, Any] = evidence.get("architecture", {})
    scope: dict[str, Any] = evidence.get("source_scope", {})
    result: dict[str, Any] = evidence.get("result", {})
    diagnostics: dict[str, Any] = evidence.get("diagnostics", {})
    raw_output: dict[str, Any] = evidence.get("raw_output", {})
    failures: list[str] = []
    if evaluator.get("id") != evaluator_id:
        failures.append("EVALUATOR_ID_MISMATCH")
    if (
        architecture.get("state") != expected_architecture_state
        or architecture.get("manifest_state_status") != "MATCHED"
    ):
        failures.append("ARCHITECTURE_MANIFEST_MISMATCH")
    if (
        architecture.get("target_source_sha") != expected_source_sha
        or architecture.get("expected_source_sha") != expected_source_sha
        or architecture.get("source_sha_status") != "MATCHED"
    ):
        failures.append("SOURCE_IDENTITY_MISMATCH")
    if architecture.get("subject_source_dirty") is not False:
        failures.append("SUBJECT_SOURCE_NOT_CLEAN")
    if scope.get("complete") is not True or not scope.get("inspected_paths"):
        failures.append("SOURCE_SCOPE_INCOMPLETE")
    if scope.get("uncertainties"):
        failures.append("SOURCE_SCOPE_UNRESOLVED")
    if result.get("execution_status") != "COMPLETED" or result.get("compliance") != "COMPLIANT":
        failures.append("EVALUATOR_NOT_COMPLIANT")
    for key in ("source_digest", "configuration_digest"):
        digest = evaluator.get(key)
        if not isinstance(digest, str) or len(digest) != 64:
            failures.append(f"{key.upper()}_MISSING")
    if not isinstance(raw_output.get("sha256"), str) or len(raw_output["sha256"]) != 64:
        failures.append("RAW_OUTPUT_DIGEST_MISSING")
    if raw_output.get("sha256") != hashlib.sha256(canonical_json(diagnostics)).hexdigest():
        failures.append("RAW_OUTPUT_DIGEST_MISMATCH")
    if evaluator_id == "AC_MODULE_GRAPH" and any(
        diagnostics.get(key)
        for key in ("unresolved_local_imports", "unresolved_capability_imports", "cycles")
    ):
        failures.append("GRAPH_HAS_UNRESOLVED_IMPORTS_OR_CYCLES")
    if failures:
        raise StageCheckError(f"{evaluator_id} evidence rejected: {', '.join(failures)}")


def _run_one_a03_evaluator(repo: Path, evaluator_id: str, expected_source_sha: str) -> None:
    config_path = (
        repo
        / "architecture/acceptance/a1"
        / {
            "AC_PUBLIC_API": "public_api_v1.yaml",
            "AC_MODULE_GRAPH": "module_graph_v1.yaml",
        }[evaluator_id]
    )
    evidence_path = repo / A03_MANIFEST
    evidence = run_evaluator(
        evaluator_id,
        repo,
        config_path,
        evidence_path,
        A03,
        expected_source_sha,
        ANALYZERS[evaluator_id],
    )
    _validate_a03_evidence(
        evidence,
        evaluator_id=evaluator_id,
        expected_source_sha=expected_source_sha,
        schema_path=repo / "architecture/acceptance/a1/evidence.schema.json",
    )
    failures = verify_evidence(
        evidence,
        repo,
        config_path,
        evaluator_root=repo / "architecture/acceptance/a1",
    )
    if failures:
        raise StageCheckError(f"{evaluator_id} evidence readback failed: {failures}")
    print(
        "[stage-ci] "
        f"{evaluator_id} COMPLIANT source={expected_source_sha} "
        f"files={len(evidence['source_scope']['inspected_paths'])} "
        f"imports={evidence['source_scope']['inspected_import_count']} "
        f"evaluator_sha256={evidence['evaluator']['source_digest']} "
        f"config_sha256={evidence['evaluator']['configuration_digest']} "
        f"raw_sha256={evidence['raw_output']['sha256']}",
        flush=True,
    )


def _run_one_a04_evaluator(repo: Path, evaluator_id: str, expected_source_sha: str) -> None:
    config_path = (
        repo
        / "architecture/acceptance/a1"
        / {
            "AC_PUBLIC_API": "public_api_v1.yaml",
            "AC_MODULE_GRAPH": "module_graph_v1.yaml",
        }[evaluator_id]
    )
    evidence = run_evaluator(
        evaluator_id,
        repo,
        config_path,
        repo / A04_MANIFEST,
        A04,
        expected_source_sha,
        ANALYZERS[evaluator_id],
    )
    _validate_a03_evidence(
        evidence,
        evaluator_id=evaluator_id,
        expected_source_sha=expected_source_sha,
        schema_path=repo / "architecture/acceptance/a1/evidence.schema.json",
        expected_architecture_state=A04,
    )
    failures = verify_evidence(
        evidence,
        repo,
        config_path,
        evaluator_root=repo / "architecture/acceptance/a1",
    )
    if failures:
        raise StageCheckError(f"{evaluator_id} evidence readback failed: {failures}")
    print(
        "[stage-ci] "
        f"{evaluator_id} COMPLIANT source={expected_source_sha} "
        f"files={len(evidence['source_scope']['inspected_paths'])} "
        f"imports={evidence['source_scope']['inspected_import_count']} "
        f"evaluator_sha256={evidence['evaluator']['source_digest']} "
        f"config_sha256={evidence['evaluator']['configuration_digest']} "
        f"raw_sha256={evidence['raw_output']['sha256']}",
        flush=True,
    )


def _run_a03_evaluators(repo: Path, expected_source_sha: str) -> None:
    manifest = _validate_a03_manifest(repo)
    _validate_a03_policy_bindings(repo, manifest)
    for evaluator_id in A03_REQUIRED_EVALUATORS:
        _run_one_a03_evaluator(repo, evaluator_id, expected_source_sha)


def _run_a04_evaluators(repo: Path, expected_source_sha: str) -> None:
    manifest = _validate_a04_manifest(repo)
    _validate_a04_policy_bindings(repo, manifest)
    for evaluator_id in A04_REQUIRED_EVALUATORS:
        _run_one_a04_evaluator(repo, evaluator_id, expected_source_sha)


def verify_historical_pin(root: Path) -> None:
    """Require exactly the published A0.1 commit and application tree."""
    if _git(root, "rev-parse", f"{HISTORICAL_A01_SHA}^{{commit}}") != HISTORICAL_A01_SHA:
        raise StageCheckError("Historical A0.1 Git commit is absent or incorrect")
    actual_tree = _git(root, "rev-parse", f"{HISTORICAL_A01_SHA}:app")
    if actual_tree != HISTORICAL_APP_TREE:
        raise StageCheckError(
            f"Historical A0.1 app tree changed: {actual_tree}, expected {HISTORICAL_APP_TREE}"
        )
    for path in (
        "tests/architecture/test_module_structure.py",
        "tests/architecture/test_layer_rules.py",
        "architecture/states/A0_1_CAPABILITY_MODULES.yaml",
    ):
        _git(root, "cat-file", "-e", f"{HISTORICAL_A01_SHA}:{path}")


def _run_pytest(root: Path, testpaths: list[str], *, historical: bool) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if historical:
        # Do not import any current-worktree Python modules while testing pinned history.
        env["PYTHONPATH"] = str(root)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--no-cov",
        "-p",
        "no:cacheprovider",
        *testpaths,
    ]
    print(f"[stage-ci] pytest cwd={root} targets={testpaths}", flush=True)
    result = subprocess.run(command, cwd=root, env=env, check=False)  # noqa: S603  # nosec B603
    if result.returncode:
        raise StageCheckError(f"Architecture pytest failed ({result.returncode}) for {testpaths}")


def historical_a01_acceptance(repo: Path) -> None:
    """Execute the original test code and its original source, not today's files."""
    verify_historical_pin(repo)
    print(
        f"[stage-ci] HISTORICAL_A01 source={HISTORICAL_A01_SHA} app_tree={HISTORICAL_APP_TREE}",
        flush=True,
    )
    git = shutil.which("git")
    if git is None:
        raise StageCheckError("Git executable unavailable")
    process = subprocess.run(  # noqa: S603  # nosec B603 - fixed Git argv, no shell
        [
            git,
            "-C",
            str(repo),
            "archive",
            "--format=tar",
            HISTORICAL_A01_SHA,
            "app",
            "architecture/states/A0_1_CAPABILITY_MODULES.yaml",
            "tests/architecture",
            "pyproject.toml",
        ],
        capture_output=True,
        check=False,
    )
    if process.returncode:
        raise StageCheckError(f"Could not materialize pinned archive: {process.stderr!r}")
    with tempfile.TemporaryDirectory(prefix="evofit-pinned-a01-") as temporary:
        checkout = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(process.stdout), mode="r:") as archive:
            # Python 3.12 data filter rejects archive traversal and unsafe links.
            archive.extractall(checkout, filter="data")
        _run_pytest(
            checkout,
            [
                "tests/architecture/test_module_structure.py",
                "tests/architecture/test_layer_rules.py",
            ],
            historical=True,
        )
    print("[stage-ci] HISTORICAL_A01 PASS (6 exact historical tests)", flush=True)


def historical_a02_acceptance(repo: Path) -> None:
    """Run A0.2 checks at the exact predecessor declared by the A0.3 state."""
    manifest = _validate_a03_manifest(repo)
    provenance = manifest.get("source_provenance")
    predecessor_sha = provenance.get("predecessor_commit") if isinstance(provenance, dict) else None
    if not isinstance(predecessor_sha, str) or len(predecessor_sha) != 40:
        raise StageCheckError("A0.3 predecessor commit is missing or malformed")
    if _git(repo, "rev-parse", f"{predecessor_sha}^{{commit}}") != predecessor_sha:
        raise StageCheckError("Declared A0.2 predecessor commit is absent or incorrect")

    with tempfile.TemporaryDirectory(prefix="evofit-historical-a02-") as temporary:
        checkout = Path(temporary) / "source"
        _git(repo, "worktree", "add", "--detach", str(checkout), predecessor_sha)
        try:
            observed = current_stage_acceptance(checkout, requested_stage=A02, historical=True)
            if observed != A02:
                raise StageCheckError(
                    f"Declared A0.2 predecessor resolved to unexpected stage {observed}"
                )
        finally:
            _git(repo, "worktree", "remove", "--force", str(checkout))
    print(
        f"[stage-ci] HISTORICAL_A02 PASS source={predecessor_sha}; "
        "checked independently of the current stage",
        flush=True,
    )


def historical_a03_acceptance(repo: Path) -> None:
    """Run A0.3's live gate against its exact canonical source revision."""
    if _git(repo, "rev-parse", f"{HISTORICAL_A03_SHA}^{{commit}}") != HISTORICAL_A03_SHA:
        raise StageCheckError("Canonical A0.3 Git commit is absent or incorrect")
    actual_tree = _git(repo, "rev-parse", f"{HISTORICAL_A03_SHA}^{{tree}}")
    if actual_tree != HISTORICAL_A03_TREE:
        raise StageCheckError(
            f"Canonical A0.3 repository tree changed: {actual_tree}, expected {HISTORICAL_A03_TREE}"
        )
    actual_app_tree = _git(repo, "rev-parse", f"{HISTORICAL_A03_SHA}:app")
    if actual_app_tree != HISTORICAL_A03_APP_TREE:
        raise StageCheckError(
            "Canonical A0.3 app tree changed: "
            f"{actual_app_tree}, expected {HISTORICAL_A03_APP_TREE}"
        )

    with tempfile.TemporaryDirectory(prefix="evofit-historical-a03-") as temporary:
        checkout = Path(temporary) / "source"
        _git(repo, "worktree", "add", "--detach", str(checkout), HISTORICAL_A03_SHA)
        try:
            observed = current_stage_acceptance(checkout, requested_stage=A03, historical=True)
            if observed != A03:
                raise StageCheckError(
                    f"Canonical A0.3 source resolved to unexpected stage {observed}"
                )
        finally:
            _git(repo, "worktree", "remove", "--force", str(checkout))
    print(
        f"[stage-ci] HISTORICAL_A03 PASS source={HISTORICAL_A03_SHA}; "
        "canonical A0.3 application tree and source-based gate verified",
        flush=True,
    )


def current_stage_acceptance(repo: Path, *, requested_stage: str, historical: bool = False) -> str:
    """Validate actual checkout with only stage-relevant tests, no historical drift."""
    current = detect_stage(repo)
    if requested_stage != "auto" and requested_stage != current:
        raise StageCheckError(
            f"Requested architecture stage {requested_stage} != observed {current}"
        )
    # Git checkout must be provenance-bound for a gate result.
    changed = _git(repo, "status", "--porcelain", "--", "app", "architecture", "tests")
    if changed:
        raise StageCheckError("Current architecture source/tests are dirty; commit first")
    current_head = _git(repo, "rev-parse", "HEAD")
    print(f"[stage-ci] CURRENT {current} source={current_head}", flush=True)
    if current == A01:
        if _git(repo, "rev-parse", "HEAD:app") != HISTORICAL_APP_TREE:
            raise StageCheckError("Claimed A0.1 stage has a nonhistorical app tree")
        checks = [
            "tests/architecture/test_module_structure.py",
            "tests/architecture/test_layer_rules.py",
        ]
    elif current == A02:
        checks = ["tests/architecture/test_layer_rules.py", "tests/unit/test_module_public_apis.py"]
        new_tests = repo / "tests/architecture/a1/test_evaluators.py"
        if new_tests.exists():
            checks.append("tests/architecture/a1/test_evaluators.py")
            print("[stage-ci] W2 evaluator unit/fixture suite PRESENT", flush=True)
        else:
            print(
                "[stage-ci] W2 AC_PUBLIC_API/AC_MODULE_GRAPH/AC_DATA_OWNERSHIP "
                "source evaluators PENDING; NOT a complete ΔA2/A1 research gate",
                flush=True,
            )
    elif current == A03:
        _run_a03_evaluators(repo, current_head)
        checks = [
            "tests/architecture/test_layer_rules.py",
            "tests/unit/test_module_public_apis.py",
            "tests/architecture/a1/test_evaluators.py",
        ]
    else:
        _run_a04_evaluators(repo, current_head)
        checks = [
            "tests/architecture/test_layer_rules.py",
            "tests/unit/test_module_public_apis.py",
            "tests/architecture/a1/test_evaluators.py",
        ]
    _run_pytest(repo, checks, historical=historical)
    print(f"[stage-ci] CURRENT {current} CHECKS PASS", flush=True)
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stage", choices=ALLOWED_STAGES, default="auto")
    args = parser.parse_args()
    root = args.repo.resolve()
    try:
        historical_a01_acceptance(root)
        current = current_stage_acceptance(root, requested_stage=args.stage)
        if current in {A03, A04}:
            historical_a02_acceptance(root)
        if current == A04:
            historical_a03_acceptance(root)
    except StageCheckError as error:
        print(f"[stage-ci] FAIL: {error}", file=sys.stderr, flush=True)
        return 1
    print(
        f"[stage-ci] PASS historical_source={HISTORICAL_A01_SHA} "
        f"current_stage={current}; final A1 proof and DA01 research gates NOT ASSERTED",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
