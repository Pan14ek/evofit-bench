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
MODULES = ("users", "tasks", "notifications", "reporting", "audit")
A01 = "A0_1_CAPABILITY_MODULES"
A02 = "A0_2_PUBLIC_MODULE_APIS"
A03 = "A0_3_GOVERNED_MODULE_GRAPH"
ALLOWED_STAGES = ("auto", A01, A02, A03)
A03_MANIFEST = "architecture/states/A0_3_GOVERNED_MODULE_GRAPH.yaml"
A03_SCHEMA = "architecture/states/A0_3_GOVERNED_MODULE_GRAPH.schema.json"
A03_REQUIRED_EVALUATORS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH")
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
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, jsonschema.ValidationError) as error:
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


def detect_stage(root: Path) -> str:
    """Recognize A0.1, A0.2, or explicit A0.3; refuse partial or ambiguous APIs."""
    modules = root / "app" / "modules"
    missing_modules = [name for name in MODULES if not (modules / name / "__init__.py").is_file()]
    if missing_modules:
        raise StageCheckError(f"Missing capability modules: {missing_modules}")
    present = [name for name in MODULES if (modules / name / "public.py").is_file()]
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
    if architecture.get("state") != A03 or architecture.get("manifest_state_status") != "MATCHED":
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


def _run_a03_evaluators(repo: Path, expected_source_sha: str) -> None:
    manifest = _validate_a03_manifest(repo)
    _validate_a03_policy_bindings(repo, manifest)
    for evaluator_id in A03_REQUIRED_EVALUATORS:
        _run_one_a03_evaluator(repo, evaluator_id, expected_source_sha)


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


def current_stage_acceptance(repo: Path, *, requested_stage: str) -> str:
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
    else:
        _run_a03_evaluators(repo, current_head)
        checks = [
            "tests/architecture/test_layer_rules.py",
            "tests/unit/test_module_public_apis.py",
            "tests/architecture/a1/test_evaluators.py",
        ]
    _run_pytest(repo, checks, historical=False)
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
