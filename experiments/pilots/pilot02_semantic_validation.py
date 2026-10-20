"""Run and independently verify PILOT-02 TEST_ONLY semantic controls."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess  # nosec B404 - fixed Git/evaluator argv, no shell
import sys
import tarfile
import tempfile
import time
import tomllib
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import grimp
import yaml

from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes

SOURCE_REVISION = "3758e2cd60810b8d4263f8d91443ec829efc8bb5"
APP_TREE_SHA1 = "cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08"
GRIMP_VERSION = "3.17"
IMPORT_LINTER_VERSION = "2.15"
VERIFIER_ID = "pilot02_semantic_scope_verifier_v1"
ADAPTATION_VERIFIER_ID = "pilot02_test_only_adaptation_verifier_v1"
OBLIGATION_CATALOG_SHA256 = "8c5bd8fffe3bdb2af8fb85f8d0012bc34673f72866e52daed99fab96f9763011"
FITNESS_CONFIGURATION_SHA256 = "3f8c952afd00f97f00b84955cc85fdf8dc5cbe32b52e65771773b8aa5a12fbad"
PROFILE_SHA256 = "c480b1907d9f69cb7c5d1c4f45cb221551aeb857881ba859529e8c1f1fd5e8c9"
IMPORT_LINTER_CONFIG_SHA256 = "5e938273faa86b4584886e2ede5700b35b064d5e54fe04b0c3d1e50278c64eb0"
STATE_MANIFEST_SHA256 = "e062c8cd0689116240bddcb4feacd5975dcf28c86a88cc11e29ebf03968d0aeb"
MODULE_TEST_SHA256 = "d1f7ae29a1c8ed5fb5a4e1c37df8c8c22bfe98a31e0fa85c8c32012c0d083f7c"
S1_PATCH_SHA256 = "7f52e0239d27d089aa9e456821f341259982eeaecdaca44a85404eef8a1f56d8"
NOTIFICATIONS_REPOSITORY_SHA256 = "bc154b83d2dd508294293bec02ad33088ea26b4b866794e7f10f0af6e448ec90"
AUDIT_MODEL_SHA256 = "7017f08f13274d7d600aaa3a9c54d8eb99d441fa7addbeb2326553f5cea599b5"

SOURCE_PATHS = (
    "app",
    "architecture/acceptance/importlinter.toml",
    "architecture/states/A0_1_CAPABILITY_MODULES.yaml",
    "tests/architecture/test_module_structure.py",
    "fitness/catalog/architectural-obligations.yaml",
    "fitness/configs/a0_1-capability-modules.dev.yaml",
    "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json",
    "experiments/pilots/PILOT_01_S1_FAULT.patch",
    "uv.lock",
)
SOURCE_FILE_PINS = {
    "architecture/acceptance/importlinter.toml": IMPORT_LINTER_CONFIG_SHA256,
    "architecture/states/A0_1_CAPABILITY_MODULES.yaml": STATE_MANIFEST_SHA256,
    "tests/architecture/test_module_structure.py": MODULE_TEST_SHA256,
    "fitness/catalog/architectural-obligations.yaml": OBLIGATION_CATALOG_SHA256,
    "fitness/configs/a0_1-capability-modules.dev.yaml": FITNESS_CONFIGURATION_SHA256,
    "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json": PROFILE_SHA256,
    "experiments/pilots/PILOT_01_S1_FAULT.patch": S1_PATCH_SHA256,
}
PAIR_SPECS = {
    "REP_A01_ARCH_INTERNAL_LAYERING_CI": {
        "obligation_id": "AC_LAYERING",
        "scope_path": "inspection_scope/REP_A01_ARCH_INTERNAL_LAYERING_CI.json",
        "positive_prefix": "controls/AC_LAYERING_positive",
        "negative_prefix": "controls/AC_LAYERING_negative",
        "mutation_path": "mutations/AC_LAYERING_negative_mutation.json",
    },
    "REP_A01_ARCH_MODULE_STRUCTURE_CI": {
        "obligation_id": "AC_MODULE_STRUCTURE",
        "scope_path": "inspection_scope/REP_A01_ARCH_MODULE_STRUCTURE_CI.json",
        "positive_prefix": "controls/AC_MODULE_STRUCTURE_positive",
        "negative_prefix": "controls/AC_MODULE_STRUCTURE_negative",
        "mutation_path": "mutations/AC_MODULE_STRUCTURE_negative_mutation.json",
    },
}
OBLIGATION_INTENTS = {
    "AC_LAYERING": "Internal dependencies must conform to the allowed layering model.",
    "AC_MODULE_STRUCTURE": "Capability modules must have declared structure and identity.",
}
EXPECTED_LAYER_CONTRACTS = (
    "Users module internal layering",
    "Tasks module internal layering",
    "Notifications module internal layering",
    "Reporting module internal layering",
    "Audit module internal layering",
)
MODULE_ASSERTION_MARKERS = (
    'manifest["schema_version"]',
    'manifest["architecture_state"]',
    'manifest["source_state"]',
    'manifest["scenario_id"]',
    'manifest["deployment"]',
    'manifest["modules"]',
    'manifest["shared_infrastructure"]',
    'manifest["preserved_cross_module_dependencies"]',
    'manifest["governance"]',
    "modules_root.iterdir()",
    'modules_root.glob("*.py")',
    'package_path.glob("*.py")',
    "shared_infrastructure_path(name).exists()",
    "ROOT / legacy_path).exists()",
    'ROOT / "app/repositories").exists()',
    'ROOT / "app/schemas").exists()',
)
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
GIT_EXECUTABLE = shutil.which("git")


class SemanticValidationError(ValueError):
    """PILOT-02 semantic evidence failed a pinned verification condition."""


def _run_git(
    repository_root: Path,
    *arguments: str,
    text: bool = False,
) -> subprocess.CompletedProcess[Any]:
    """Run a fixed Git operation with a resolved executable and no shell."""
    if GIT_EXECUTABLE is None:
        raise SemanticValidationError("git executable unavailable")
    return subprocess.run(  # noqa: S603 - fixed Git operations and validated source revision
        [GIT_EXECUTABLE, *arguments],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=text,
        timeout=180,
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SemanticValidationError(f"expected JSON object: {path}")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    )


def _run(argv: list[str], *, cwd: Path, timeout: int = 180) -> dict[str, Any]:
    started = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    started_ns = time.perf_counter_ns()
    completed = subprocess.run(  # noqa: S603 - argv is selected by the fixed control runner
        argv,
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    duration_ns = time.perf_counter_ns() - started_ns
    ended = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return {
        "command": argv,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "duration_ns": duration_ns,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _store_execution(root: Path, prefix: str, execution: dict[str, Any]) -> dict[str, Any]:
    stdout_path = root / f"{prefix}.stdout.bin"
    stderr_path = root / f"{prefix}.stderr.bin"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(execution.pop("stdout"))
    stderr_path.write_bytes(execution.pop("stderr"))
    execution["stdout_artifact"] = {
        "path": stdout_path.relative_to(root).as_posix(),
        "sha256": _sha(stdout_path),
    }
    execution["stderr_artifact"] = {
        "path": stderr_path.relative_to(root).as_posix(),
        "sha256": _sha(stderr_path),
    }
    _write_json(root / f"{prefix}.json", execution)
    return execution


def _export_pinned_sources(repository_root: Path, destination: Path) -> dict[str, Any]:
    app_tree = _run_git(
        repository_root, "rev-parse", f"{SOURCE_REVISION}:app", text=True
    ).stdout.strip()
    if app_tree != APP_TREE_SHA1:
        raise SemanticValidationError("pinned A0.1 application-tree SHA-1 mismatch")
    for path, expected_digest in SOURCE_FILE_PINS.items():
        content = _run_git(repository_root, "show", f"{SOURCE_REVISION}:{path}").stdout
        if sha256_bytes(content) != expected_digest:
            raise SemanticValidationError(f"pinned source digest mismatch: {path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run_git(
        repository_root,
        "archive",
        "--format=tar",
        f"--output={destination}",
        SOURCE_REVISION,
        "--",
        *SOURCE_PATHS,
    )
    return {
        "commit_sha": SOURCE_REVISION,
        "application_tree_sha1": app_tree,
        "source_snapshot_tar_sha256": _sha(destination),
        "pinned_source_file_sha256": dict(sorted(SOURCE_FILE_PINS.items())),
        "source_snapshot_paths": list(SOURCE_PATHS),
        "oracle_files_included": False,
    }


def _extract_snapshot(snapshot_tar: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(snapshot_tar, "r:") as archive:
        names = archive.getnames()
        if any("ground_truth" in name or "expected_operations" in name for name in names):
            raise SemanticValidationError("oracle-side path found in scoped source snapshot")
        archive.extractall(destination, filter="data")
    return destination


def _module_file_inventory(source_root: Path) -> dict[str, Any]:
    state_path = source_root / "architecture/states/A0_1_CAPABILITY_MODULES.yaml"
    test_path = source_root / "tests/architecture/test_module_structure.py"
    manifest = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    test_text = test_path.read_text(encoding="utf-8")
    test_tree = ast.parse(test_text)
    test_literals: dict[str, Any] = {}
    for node in test_tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            try:
                test_literals[node.target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        test_literals[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        continue

    expected_modules = manifest["modules"]
    test_constants = {
        "EXPECTED_MODULES": test_literals.get("EXPECTED_MODULES"),
        "EXPECTED_SHARED_INFRASTRUCTURE": test_literals.get("EXPECTED_SHARED_INFRASTRUCTURE"),
        "EXPECTED_DEPENDENCIES": test_literals.get("EXPECTED_DEPENDENCIES"),
        "EXPECTED_GOVERNANCE": test_literals.get("EXPECTED_GOVERNANCE"),
        "LEGACY_CAPABILITY_FILES": test_literals.get("LEGACY_CAPABILITY_FILES"),
    }
    modules_root = source_root / "app/modules"
    discovered_packages = sorted(
        path.name
        for path in modules_root.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    )
    expected_package_names = sorted(expected_modules)
    root_python_files = sorted(path.name for path in modules_root.glob("*.py"))
    module_records: list[dict[str, Any]] = []
    for name, contract in sorted(expected_modules.items()):
        package_path = source_root.joinpath(*contract["package"].split("."))
        expected_files = sorted(contract["required_files"])
        discovered_files = (
            sorted(path.name for path in package_path.glob("*.py")) if package_path.is_dir() else []
        )
        module_records.append(
            {
                "module_id": name,
                "package": contract["package"],
                "package_resolved": package_path.is_dir(),
                "expected_files": expected_files,
                "discovered_files": discovered_files,
                "missing_files": sorted(set(expected_files) - set(discovered_files)),
                "unexpected_files": sorted(set(discovered_files) - set(expected_files)),
                "discovered_file_sha256": {
                    filename: _sha(package_path / filename) for filename in discovered_files
                },
            }
        )
    shared = {
        name: (
            source_root.joinpath(*name.split(".")).is_dir()
            or source_root.joinpath(*name.split(".")).with_suffix(".py").is_file()
        )
        for name in manifest["shared_infrastructure"]
    }
    legacy_paths = (
        "app/api/users.py",
        "app/api/tasks.py",
        "app/api/notifications.py",
        "app/api/reports.py",
        "app/schemas/users.py",
        "app/schemas/tasks.py",
        "app/schemas/notifications.py",
        "app/schemas/reports.py",
        "app/services/user_service.py",
        "app/services/task_service.py",
        "app/services/notification_service.py",
        "app/services/report_service.py",
        "app/services/audit_service.py",
        "app/repositories/user_repository.py",
        "app/repositories/task_repository.py",
        "app/repositories/notification_repository.py",
        "app/repositories/audit_repository.py",
        "app/models/user.py",
        "app/models/task.py",
        "app/models/notification.py",
        "app/models/audit_event.py",
    )
    forbidden_legacy = {path: not (source_root / path).exists() for path in legacy_paths}
    assertion_markers = {marker: marker in test_text for marker in MODULE_ASSERTION_MARKERS}
    manifest_properties = {
        "schema_version": manifest.get("schema_version") == 1,
        "architecture_state": manifest.get("architecture_state") == "A0_1_CAPABILITY_MODULES",
        "source_state": manifest.get("source_state") == "A0_MONOLITH",
        "scenario_id": manifest.get("scenario_id") == "DA01",
        "deployment": manifest.get("deployment")
        == {
            "deployment_units": 1,
            "application_processes": 1,
            "database_instances": 1,
            "database_product": "PostgreSQL",
            "internal_communication": "synchronous_python_calls",
            "message_broker": "none",
        },
        "modules_match_test_constants": test_constants["EXPECTED_MODULES"] == expected_modules,
        "shared_infrastructure_match_test_constants": test_constants[
            "EXPECTED_SHARED_INFRASTRUCTURE"
        ]
        == manifest["shared_infrastructure"],
        "dependencies_match_test_constants": test_constants["EXPECTED_DEPENDENCIES"]
        == manifest["preserved_cross_module_dependencies"],
        "governance_match_test_constants": test_constants["EXPECTED_GOVERNANCE"]
        == manifest["governance"],
        "test_assertion_markers_present": all(assertion_markers.values()),
    }
    module_names = sorted(expected_modules)
    inventory = {
        "schema_version": 1,
        "inspection_unit": "module",
        "expected_subjects": module_names,
        "inspected_subjects": module_names if modules_root.is_dir() else [],
        "measured_count": len(module_names) if modules_root.is_dir() else 0,
        "manifest_file": state_path.relative_to(source_root).as_posix(),
        "manifest_sha256": _sha(state_path),
        "evaluator_source_file": test_path.relative_to(source_root).as_posix(),
        "evaluator_source_sha256": _sha(test_path),
        "test_literals": json.loads(json.dumps(test_constants)),
        "manifest_properties": manifest_properties,
        "package_inventory": {
            "expected": expected_package_names,
            "discovered": discovered_packages,
            "matches": expected_package_names == discovered_packages,
        },
        "root_module_python_files": {"expected": ["__init__.py"], "discovered": root_python_files},
        "modules": module_records,
        "shared_infrastructure": shared,
        "legacy_paths_absent": forbidden_legacy,
        "application_root_forbidden_paths_absent": {
            "app/repositories": not (source_root / "app/repositories").exists(),
            "app/schemas": not (source_root / "app/schemas").exists(),
        },
        "assertion_markers": assertion_markers,
        "limitation": (
            "The test checks manifest declarations and Python package/file names and selected "
            "path presence/absence; it does not inspect API behavior, source semantics, or "
            "dependency edges."
        ),
    }
    return inventory


def _layering_scope(source_root: Path, cache_dir: Path) -> dict[str, Any]:
    config_path = source_root / "architecture/acceptance/importlinter.toml"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    contracts = config.get("tool", {}).get("importlinter", {}).get("contracts", [])
    original_sys_path = sys.path.copy()
    previous_directory = Path.cwd()
    previous_app_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "app" or name.startswith("app.")
    }
    try:
        for name in previous_app_modules:
            sys.modules.pop(name, None)
        sys.path.insert(0, str(source_root))
        os.chdir(source_root)
        graph = grimp.build_graph("app", include_external_packages=False, cache_dir=str(cache_dir))
    finally:
        os.chdir(previous_directory)
        sys.path[:] = original_sys_path
        for name in tuple(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)
        sys.modules.update(previous_app_modules)
    modules = set(graph.modules)
    all_edges = sorted(
        (importer, imported)
        for importer in modules
        for imported in graph.find_modules_directly_imported_by(importer)
    )
    adjacency: dict[str, set[str]] = {module: set() for module in modules}
    reverse: dict[str, set[str]] = {module: set() for module in modules}
    for importer, imported in all_edges:
        adjacency[importer].add(imported)
        reverse[imported].add(importer)

    contract_records: list[dict[str, Any]] = []
    target_inventory: list[str] = []
    scope_edge_bindings: dict[tuple[str, str], set[str]] = {}
    grimp_violations: dict[str, list[dict[str, Any]]] = {}
    missing_targets: list[str] = []
    for contract in contracts:
        name = str(contract.get("name", ""))
        layer_targets = [str(item) for item in contract.get("layers", []) if isinstance(item, str)]
        target_inventory.extend(layer_targets)
        layer_subjects: list[list[str]] = []
        target_status: list[dict[str, Any]] = []
        for target in layer_targets:
            exact_resolved = target in modules
            subjects = sorted(
                module for module in modules if module == target or module.startswith(target + ".")
            )
            if not exact_resolved:
                missing_targets.append(target)
            target_status.append(
                {"target": target, "resolved": exact_resolved, "subject_modules": subjects}
            )
            layer_subjects.append(subjects)

        relevant_edges: set[tuple[str, str]] = set()
        dependency_pairs: list[dict[str, Any]] = []
        for start_index, start_subjects in enumerate(layer_subjects):
            for end_index, end_subjects in enumerate(layer_subjects):
                if start_index == end_index:
                    continue
                for start in start_subjects:
                    forward = _reachable(start, adjacency)
                    for end in end_subjects:
                        if end not in forward:
                            continue
                        backward = _reachable(end, reverse)
                        chain_edges = {
                            (node, child)
                            for node in forward & backward
                            for child in adjacency.get(node, set()) & backward
                        }
                        relevant_edges.update(chain_edges)
                        dependency_pairs.append(
                            {
                                "from_layer_index": start_index,
                                "from_subject": start,
                                "to_layer_index": end_index,
                                "to_subject": end,
                                "shortest_path": _shortest_path(start, end, adjacency),
                            }
                        )
        for edge in relevant_edges:
            scope_edge_bindings.setdefault(edge, set()).add(name)

        violations = graph.find_illegal_dependencies_for_layers(layer_targets)
        normalized_violations = [
            {
                "importer": item.importer,
                "imported": item.imported,
                "routes": [
                    {
                        "heads": sorted(route.heads),
                        "middle": list(route.middle),
                        "tails": sorted(route.tails),
                    }
                    for route in sorted(item.routes)
                ],
            }
            for item in sorted(violations)
        ]
        grimp_violations[name] = normalized_violations
        contract_records.append(
            {
                "name": name,
                "type": contract.get("type"),
                "configured_layers": layer_targets,
                "resolved_layers": [row["target"] for row in target_status if row["resolved"]],
                "missing_layers": [row["target"] for row in target_status if not row["resolved"]],
                "layer_subjects": target_status,
                "contract_relevant_direct_edges": [
                    {"importer": importer, "imported": imported}
                    for importer, imported in sorted(relevant_edges)
                ],
                "contract_relevant_edge_count": len(relevant_edges),
                "reachable_cross_layer_subject_pairs": sorted(
                    dependency_pairs,
                    key=lambda row: (
                        row["from_layer_index"],
                        row["from_subject"],
                        row["to_layer_index"],
                        row["to_subject"],
                    ),
                ),
                "grimp_illegal_dependencies": normalized_violations,
            }
        )
    unique_targets = sorted(set(target_inventory))
    resolved_targets = sorted(set(unique_targets) & modules)
    scoped_edges = [
        {
            "importer": importer,
            "imported": imported,
            "contracts": sorted(scope_edge_bindings[(importer, imported)]),
        }
        for importer, imported in sorted(scope_edge_bindings)
    ]
    graph_reference = {
        "schema_version": 1,
        "graph_builder": "grimp",
        "graph_builder_version": importlib_version("grimp"),
        "root_packages": ["app"],
        "include_external_packages": False,
        "module_count": len(modules),
        "dependency_edge_count": graph.count_imports(),
        "modules": sorted(modules),
        "direct_dependency_edges": [
            {"importer": importer, "imported": imported} for importer, imported in all_edges
        ],
        "contracts": contract_records,
        "configured_target_inventory": unique_targets,
        "resolved_target_inventory": resolved_targets,
        "missing_target_inventory": sorted(set(missing_targets)),
        "contract_relevant_direct_edges": scoped_edges,
        "contract_relevant_edge_count": len(scoped_edges),
    }
    graph_digest = sha256_bytes(canonical_json_bytes(graph_reference))
    return {
        "schema_version": 1,
        "inspection_unit": "dependency_edge",
        "configuration_sha256": _sha(config_path),
        "contract_names": [str(contract.get("name", "")) for contract in contracts],
        "expected_subjects": unique_targets,
        "inspected_subjects": resolved_targets,
        "measured_count": len(scoped_edges),
        "graph_reference": graph_reference,
        "graph_reference_sha256": graph_digest,
        "target_count": len(unique_targets),
        "contract_count": len(contracts),
        "resolved_target_count": len(resolved_targets),
        "missing_targets": sorted(set(missing_targets)),
        "full_graph_module_count": len(modules),
        "full_graph_dependency_edge_count": graph.count_imports(),
        "contract_relevant_edge_count": len(scoped_edges),
        "grimp_violations_by_contract": grimp_violations,
    }


def importlib_version(name: str) -> str:
    """Return one installed distribution version without importing app code."""
    from importlib.metadata import version

    return version(name)


def _reachable(start: str, adjacency: dict[str, set[str]]) -> set[str]:
    visited = {start}
    pending = [start]
    while pending:
        current = pending.pop()
        for child in adjacency.get(current, set()):
            if child not in visited:
                visited.add(child)
                pending.append(child)
    return visited


def _shortest_path(start: str, end: str, adjacency: dict[str, set[str]]) -> list[str]:
    queue: deque[list[str]] = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        if path[-1] == end:
            return path
        for child in sorted(adjacency.get(path[-1], set())):
            if child not in visited:
                visited.add(child)
                queue.append([*path, child])
    return []


def _parse_import_linter_output(output: bytes, contract_names: list[str]) -> dict[str, Any]:
    text = _ANSI.sub("", output.decode("utf-8", errors="replace"))
    results: dict[str, str] = {}
    for name in contract_names:
        match = re.search(rf"^{re.escape(name)}\s+(KEPT|BROKEN)(?:\s|$)", text, re.MULTILINE)
        if match:
            results[name] = match.group(1)
    summary = re.search(r"Contracts:\s+(\d+) kept,\s+(\d+) broken\.", text)
    violation_lines = [
        line
        for line in text.splitlines()
        if "app.modules.notifications.repository" in line
        and "app.modules.notifications.api" in line
    ]
    return {
        "contract_results": results,
        "contract_count": len(results),
        "kept_count": int(summary.group(1)) if summary else None,
        "broken_count": int(summary.group(2)) if summary else None,
        "expected_violation_path_observed": (
            "app.modules.notifications.repository" in text
            and "app.modules.notifications.api" in text
        ),
        "expected_violation_edge_observed": any(
            re.search(r"repository.*(?:->|imports?|to).*notifications\.api", line, re.IGNORECASE)
            or re.search(r"notifications\.repository.*notifications\.api", line, re.IGNORECASE)
            for line in violation_lines
        ),
        "text": text,
    }


def _run_import_linter(source_root: Path, output_root: Path, label: str) -> dict[str, Any]:
    executable = shutil.which("lint-imports")
    if executable is None:
        raise SemanticValidationError("lint-imports executable unavailable")
    execution = _run(
        [
            executable,
            "--config",
            "architecture/acceptance/importlinter.toml",
            "--no-cache",
            "--verbose",
        ],
        cwd=source_root,
        timeout=180,
    )
    parsed = _parse_import_linter_output(
        execution["stdout"] + b"\n" + execution["stderr"],
        [
            "Users module internal layering",
            "Tasks module internal layering",
            "Notifications module internal layering",
            "Reporting module internal layering",
            "Audit module internal layering",
        ],
    )
    result = _store_execution(output_root, f"controls/{label}", execution)
    result["parsed_output"] = {key: value for key, value in parsed.items() if key != "text"}
    return result


def _run_module_structure(source_root: Path, output_root: Path, label: str) -> dict[str, Any]:
    execution = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--no-header",
            "tests/architecture/test_module_structure.py",
        ],
        cwd=source_root,
        timeout=180,
    )
    output = execution["stdout"] + b"\n" + execution["stderr"]
    text = output.decode("utf-8", errors="replace")
    result = _store_execution(output_root, f"controls/{label}", execution)
    result["parsed_output"] = {
        "one_passed": re.search(r"\b1 passed\b", text) is not None,
        "one_failed": re.search(r"\b1 failed\b", text) is not None,
        "missing_audit_model_reported": "model.py" in text,
        "expected_file_set_assertion_reported": "actual_files == required_files" in text,
    }
    return result


def _directory_inventory(root: Path, prefix: str) -> dict[str, Any]:
    rows = []
    base = root / prefix
    for path in sorted(base.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha(path),
                }
            )
    return {
        "schema_version": 1,
        "root": prefix,
        "files": rows,
        "files_sha256": sha256_bytes(canonical_json_bytes(rows)),
    }


def _source_copy(source_root: Path, destination: Path) -> None:
    shutil.copytree(source_root, destination)


def _validate_pinned_inputs(source_root: Path) -> dict[str, Any]:
    digests: dict[str, str] = {}
    for path, expected in SOURCE_FILE_PINS.items():
        actual = _sha(source_root / path)
        if actual != expected:
            raise SemanticValidationError(f"extracted source digest mismatch: {path}")
        digests[path] = actual
    catalog = yaml.safe_load(
        (source_root / "fitness/catalog/architectural-obligations.yaml").read_text()
    )
    obligations = {str(row["id"]): row for row in catalog["obligations"]}
    selected_obligations = {
        obligation_id: {
            "id": obligation_id,
            "criterion": obligations[obligation_id]["criterion"],
            "intent": obligations[obligation_id]["intent"],
        }
        for obligation_id in OBLIGATION_INTENTS
    }
    if any(
        selected_obligations[item]["intent"] != intent
        or selected_obligations[item]["criterion"] != "architecture_compliance"
        for item, intent in OBLIGATION_INTENTS.items()
    ):
        raise SemanticValidationError("pinned obligation identity or intent mismatch")
    profile = _read_json(
        source_root / "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json"
    )
    mappings = {str(row["source_representation_id"]): row for row in profile["mappings"]}
    selected_mappings = {}
    for representation_id, spec in PAIR_SPECS.items():
        mapping = mappings.get(representation_id)
        if mapping is None or mapping.get("obligation_id") != spec["obligation_id"]:
            raise SemanticValidationError(f"pinned profile pair mismatch: {representation_id}")
        representation = mapping["candidate_template"]["representation"]
        selected_mappings[representation_id] = {
            "representation": representation,
            "representation_sha256": sha256_bytes(canonical_json_bytes(representation)),
            "evaluator_artifact_sha256": representation["evaluator_artifact"]["sha256"],
            "evidence_contract_sha256": sha256_bytes(
                canonical_json_bytes(representation["evidence_contract"])
            ),
            "configuration_artifact": mapping["configuration_artifact"],
            "source_evaluator_record_id": representation["evidence_contract"]["record_id"],
            "method_stage": representation["stage"],
            "source_stage": representation["evidence_contract"]["source_stage"],
        }
    return {
        "source_revision": SOURCE_REVISION,
        "application_tree_sha1": APP_TREE_SHA1,
        "source_file_sha256": digests,
        "obligations": selected_obligations,
        "profile_sha256": PROFILE_SHA256,
        "fitness_configuration_sha256": FITNESS_CONFIGURATION_SHA256,
        "locked_evaluator_versions": _locked_evaluator_versions(source_root / "uv.lock"),
        "mappings": selected_mappings,
    }


def _locked_evaluator_versions(lock_path: Path) -> dict[str, str]:
    """Read the exact test/evaluator versions declared by the pinned lockfile."""
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    expected = {"grimp": GRIMP_VERSION, "import-linter": IMPORT_LINTER_VERSION}
    packages = {
        str(row.get("name")): str(row.get("version"))
        for row in lock.get("package", [])
        if isinstance(row, dict)
    }
    actual = {name: packages.get(name, "") for name in expected}
    if actual != expected:
        raise SemanticValidationError(f"pinned evaluator dependency versions differ: {actual}")
    return actual


def _validate_runtime_versions(pinned: dict[str, Any]) -> dict[str, str]:
    """Require the control environment to match the evaluator lockfile pins."""
    expected = pinned["locked_evaluator_versions"]
    actual = {
        "grimp": importlib.metadata.version("grimp"),
        "import-linter": importlib.metadata.version("import-linter"),
    }
    if actual != expected:
        raise SemanticValidationError(f"control environment differs from uv.lock: {actual}")
    return actual


def _validate_method_source(repository_root: Path, revision: str) -> dict[str, Any]:
    """Bind the target Method P run revision to the exact pinned A0.1 source."""
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise SemanticValidationError(
            "method architecture source revision is not a full commit SHA"
        )
    if _run_git(repository_root, "rev-parse", "HEAD", text=True).stdout.strip() != revision:
        raise SemanticValidationError("method architecture source revision is not repository HEAD")
    if _run_git(
        repository_root, "status", "--porcelain", "--untracked-files=all", text=True
    ).stdout.strip():
        raise SemanticValidationError("method source checkout must be clean for semantic controls")
    app_tree = _run_git(repository_root, "rev-parse", f"{revision}:app", text=True).stdout.strip()
    if app_tree != APP_TREE_SHA1:
        raise SemanticValidationError(
            "method architecture source has a different A0.1 application tree"
        )
    source_digests: dict[str, str] = {}
    for path, expected in SOURCE_FILE_PINS.items():
        content = _run_git(repository_root, "show", f"{revision}:{path}").stdout
        actual = sha256_bytes(content)
        if actual != expected:
            raise SemanticValidationError(
                f"method revision differs from pinned evaluator input: {path}"
            )
        source_digests[path] = actual
    return {
        "schema_version": 1,
        "architecture_source_sha": revision,
        "application_tree_sha1": app_tree,
        "source_file_sha256": source_digests,
    }


def _runtime_info() -> dict[str, Any]:
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "grimp_version": importlib.metadata.version("grimp"),
        "import_linter_version": importlib.metadata.version("import-linter"),
    }


def _control_expectations(
    output_root: Path,
    scope_by_representation: dict[str, dict[str, Any]],
    controls: dict[str, dict[str, Any]],
    mutations: dict[str, dict[str, Any]],
    pinned: dict[str, Any],
    method_source_binding: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for representation_id, spec in PAIR_SPECS.items():
        if representation_id not in scope_by_representation:
            continue
        obligation_id = spec["obligation_id"]
        positive = controls[f"{obligation_id}_positive"]
        negative = controls[f"{obligation_id}_negative"]
        scope = scope_by_representation[representation_id]
        if obligation_id == "AC_LAYERING":
            clean_result = positive["parsed_output"]
            fault_result = negative["parsed_output"]
            clean_valid = (
                positive["exit_code"] == 0
                and clean_result["contract_count"] == 5
                and clean_result["kept_count"] == 5
                and clean_result["broken_count"] == 0
                and all(value == "KEPT" for value in clean_result["contract_results"].values())
            )
            negative_valid = (
                negative["exit_code"] != 0
                and fault_result["contract_count"] == 5
                and fault_result["kept_count"] == 4
                and fault_result["broken_count"] == 1
                and fault_result["contract_results"].get("Notifications module internal layering")
                == "BROKEN"
                and fault_result["expected_violation_path_observed"]
                and fault_result["expected_violation_edge_observed"]
            )
            mutation = mutations[obligation_id]
            mutated_graph_ref = mutation.get("mutated_graph_artifact", {})
            mutated_graph_path = output_root / str(mutated_graph_ref.get("path", ""))
            mutated_graph_valid = mutated_graph_path.is_file() and _sha(
                mutated_graph_path
            ) == mutated_graph_ref.get("sha256")
            mutated_graph = _read_json(mutated_graph_path) if mutated_graph_valid else {}
            notification_contract = "Notifications module internal layering"
            mutated_violation_rows = mutated_graph.get("grimp_violations_by_contract", {}).get(
                notification_contract, []
            )
            expected_direct_edge = {
                "importer": "app.modules.notifications.repository",
                "imported": "app.modules.notifications.api",
            }
            mutated_relevant_edges = mutated_graph.get("graph_reference", {}).get(
                "contract_relevant_direct_edges", []
            )
            grimp_edge_present = any(
                row.get("importer") == expected_direct_edge["importer"]
                and row.get("imported") == expected_direct_edge["imported"]
                and notification_contract in row.get("contracts", [])
                for row in mutated_relevant_edges
                if isinstance(row, dict)
            )
            grimp_violation_present = any(
                row.get("importer") == expected_direct_edge["importer"]
                and row.get("imported") == expected_direct_edge["imported"]
                for row in mutated_violation_rows
                if isinstance(row, dict)
            )
            before_inventory_ref = mutation.get("app_inventory_before_artifact", {})
            after_inventory_ref = mutation.get("app_inventory_after_artifact", {})
            before_inventory_path = output_root / str(before_inventory_ref.get("path", ""))
            after_inventory_path = output_root / str(after_inventory_ref.get("path", ""))
            inventories_valid = (
                before_inventory_path.is_file()
                and after_inventory_path.is_file()
                and _sha(before_inventory_path) == before_inventory_ref.get("sha256")
                and _sha(after_inventory_path) == after_inventory_ref.get("sha256")
            )
            before_inventory = _read_json(before_inventory_path) if inventories_valid else {}
            after_inventory = _read_json(after_inventory_path) if inventories_valid else {}
            before_target = next(
                (
                    row
                    for row in before_inventory.get("files", [])
                    if row.get("path") == "app/modules/notifications/repository.py"
                ),
                {},
            )
            after_target = next(
                (
                    row
                    for row in after_inventory.get("files", [])
                    if row.get("path") == "app/modules/notifications/repository.py"
                ),
                {},
            )
            clean_violations = scope.get("grimp_violations_by_contract", {})
            clean_grimp_agrees = all(not rows for rows in clean_violations.values())
            negative_grimp_agrees = all(
                bool(mutated_graph.get("grimp_violations_by_contract", {}).get(name, []))
                == (fault_result["contract_results"].get(name) == "BROKEN")
                for name in fault_result["contract_results"]
            )
            scope_valid = (
                scope["contract_count"] == 5
                and tuple(scope.get("contract_names", [])) == EXPECTED_LAYER_CONTRACTS
                and scope["target_count"] == 17
                and scope["resolved_target_count"] == 17
                and not scope["missing_targets"]
                and scope["full_graph_dependency_edge_count"]
                == len(scope["graph_reference"]["direct_dependency_edges"])
                and scope["full_graph_dependency_edge_count"]
                == scope["graph_reference"]["dependency_edge_count"]
                and scope["contract_relevant_edge_count"] == scope["measured_count"]
                and scope["measured_count"] > 0
                and inventories_valid
                and before_inventory.get("files_sha256")
                == mutation.get("app_inventory_before_sha256")
                and after_inventory.get("files_sha256")
                == mutation.get("app_inventory_after_sha256")
                and before_target.get("sha256") == NOTIFICATIONS_REPOSITORY_SHA256
                and after_target.get("sha256") == mutation.get("target_after_sha256")
                and clean_grimp_agrees
                and mutated_graph_valid
                and grimp_edge_present
                and grimp_violation_present
                and negative_grimp_agrees
                and mutation.get("mutation_id") == "PILOT01_S1_REPOSITORY_TO_API_SECONDARY_CONTROL"
                and mutation.get("target_before_sha256") == NOTIFICATIONS_REPOSITORY_SHA256
                and mutation.get("patch_sha256") == S1_PATCH_SHA256
                and mutation.get("source_revision") == SOURCE_REVISION
            )
        else:
            clean_result = positive["parsed_output"]
            fault_result = negative["parsed_output"]
            clean_valid = positive["exit_code"] == 0 and clean_result["one_passed"]
            negative_valid = (
                negative["exit_code"] != 0
                and fault_result["one_failed"]
                and fault_result["missing_audit_model_reported"]
                and fault_result["expected_file_set_assertion_reported"]
            )
            mutation = mutations[obligation_id]
            before_inventory_ref = mutation.get("app_inventory_before_artifact", {})
            after_inventory_ref = mutation.get("app_inventory_after_artifact", {})
            before_inventory_path = output_root / str(before_inventory_ref.get("path", ""))
            after_inventory_path = output_root / str(after_inventory_ref.get("path", ""))
            inventories_valid = (
                before_inventory_path.is_file()
                and after_inventory_path.is_file()
                and _sha(before_inventory_path) == before_inventory_ref.get("sha256")
                and _sha(after_inventory_path) == after_inventory_ref.get("sha256")
            )
            before_inventory = _read_json(before_inventory_path) if inventories_valid else {}
            after_inventory = _read_json(after_inventory_path) if inventories_valid else {}
            before_target = next(
                (
                    row
                    for row in before_inventory.get("files", [])
                    if row.get("path") == "app/modules/audit/model.py"
                ),
                {},
            )
            after_target_paths = {row.get("path") for row in after_inventory.get("files", [])}
            mutated_scope_ref = mutation.get("mutated_scope_artifact", {})
            mutated_scope_path = output_root / str(mutated_scope_ref.get("path", ""))
            mutated_scope_valid = mutated_scope_path.is_file() and _sha(
                mutated_scope_path
            ) == mutated_scope_ref.get("sha256")
            mutated_scope = _read_json(mutated_scope_path) if mutated_scope_valid else {}
            scope_valid = (
                scope["inspection_unit"] == "module"
                and len(scope["expected_subjects"]) == 5
                and scope["expected_subjects"] == scope["inspected_subjects"]
                and scope["measured_count"] == 5
                and all(scope["manifest_properties"].values())
                and scope["package_inventory"]["matches"]
                and scope["root_module_python_files"]["expected"]
                == scope["root_module_python_files"]["discovered"]
                and all(
                    not row["missing_files"] and not row["unexpected_files"]
                    for row in scope["modules"]
                )
                and all(scope["shared_infrastructure"].values())
                and all(scope["legacy_paths_absent"].values())
                and all(scope["application_root_forbidden_paths_absent"].values())
                and inventories_valid
                and before_inventory.get("files_sha256")
                == mutation.get("app_inventory_before_sha256")
                and after_inventory.get("files_sha256")
                == mutation.get("app_inventory_after_sha256")
                and before_target.get("sha256") == AUDIT_MODEL_SHA256
                and "app/modules/audit/model.py" not in after_target_paths
                and mutated_scope_valid
                and any(
                    row.get("module_id") == "audit" and "model.py" in row.get("missing_files", [])
                    for row in mutated_scope.get("modules", [])
                )
                and mutated_scope.get("inspected_subjects") == scope["expected_subjects"]
                and mutated_scope.get("modules", []) != scope.get("modules", [])
                and mutation.get("mutation_id") == "PILOT02_MODULE_STRUCTURE_MISSING_AUDIT_MODEL_V1"
                and mutation.get("mutation_action") == "delete"
                and mutation.get("target_path") == "app/modules/audit/model.py"
                and mutation.get("target_before_sha256") == AUDIT_MODEL_SHA256
                and mutation.get("source_revision") == SOURCE_REVISION
            )
        mapping = pinned["mappings"][representation_id]
        results[representation_id] = {
            "positive_behavior_observed": bool(clean_valid),
            "negative_behavior_observed": bool(negative_valid),
            "inspection_scope_resolved": bool(scope_valid),
            "obligation_identity_verified": pinned["obligations"][obligation_id]["criterion"]
            == mapping["representation"]["criterion"],
            "template_identity_verified": mapping["representation"].get("id") == representation_id
            and obligation_id in mapping["representation"].get("covers", []),
            "source_revision_verified": pinned["source_revision"] == SOURCE_REVISION
            and pinned["application_tree_sha1"] == APP_TREE_SHA1,
            "method_source_binding_verified": bool(
                re.fullmatch(
                    r"[a-f0-9]{40}",
                    str(method_source_binding.get("architecture_source_sha", "")),
                )
            )
            and method_source_binding.get("application_tree_sha1") == APP_TREE_SHA1
            and method_source_binding.get("source_file_sha256") == SOURCE_FILE_PINS,
            "evaluator_artifact_verified": mapping["evaluator_artifact_sha256"]
            == mapping["representation"]["evaluator_artifact"]["sha256"],
            "evidence_contract_verified": mapping["evidence_contract_sha256"]
            == sha256_bytes(canonical_json_bytes(mapping["representation"]["evidence_contract"])),
            "limitations": (
                [
                    "The module-structure evaluator validates declared names and selected path "
                    "presence/absence; it does not prove module implementation semantics or "
                    "import behavior."
                ]
                if obligation_id == "AC_MODULE_STRUCTURE"
                else [
                    "Negative control covers the predeclared PILOT-01 repository-to-API "
                    "dependency; it does not prove detection of every possible layering defect."
                ]
            ),
        }
    return results


def _build_report(
    representation_id: str,
    scope: dict[str, Any],
    controls: dict[str, dict[str, Any]],
    mutations: dict[str, dict[str, Any]],
    pinned: dict[str, Any],
    control_checks: dict[str, Any],
    root: Path,
    method_source_binding: dict[str, Any],
) -> dict[str, Any]:
    spec = PAIR_SPECS[representation_id]
    obligation_id = str(spec["obligation_id"])
    outcome = control_checks[representation_id]
    is_valid = all(
        outcome[key]
        for key in (
            "positive_behavior_observed",
            "negative_behavior_observed",
            "inspection_scope_resolved",
            "obligation_identity_verified",
            "template_identity_verified",
            "source_revision_verified",
            "method_source_binding_verified",
            "evaluator_artifact_verified",
            "evidence_contract_verified",
        )
    )
    inspection_path = spec["scope_path"]
    inspection_digest = _sha(root / inspection_path)
    support_paths = [
        "inputs/pinned_a01_scope_source.tar",
        "inputs/method_source_binding.json",
        inspection_path,
        spec["positive_prefix"] + ".json",
        spec["positive_prefix"] + ".stdout.bin",
        spec["positive_prefix"] + ".stderr.bin",
        spec["negative_prefix"] + ".json",
        spec["negative_prefix"] + ".stdout.bin",
        spec["negative_prefix"] + ".stderr.bin",
        spec["mutation_path"],
    ]
    mutation = mutations[obligation_id]
    for key in (
        "mutated_graph_artifact",
        "mutated_scope_artifact",
        "app_inventory_before_artifact",
        "app_inventory_after_artifact",
    ):
        reference = mutation.get(key)
        if isinstance(reference, dict) and isinstance(reference.get("path"), str):
            support_paths.append(str(reference["path"]))
    support = []
    for relative in sorted(set(support_paths)):
        support.append({"path": relative, "sha256": _sha(root / relative)})
    support.append({"path": f"semantic_verification/{representation_id}.json", "sha256": None})
    return {
        "schema_version": 1,
        "report_id": f"PILOT02_SEMANTIC_{obligation_id}_V1",
        "verification_component_id": VERIFIER_ID,
        "trust_scope": "TEST_ONLY",
        "independent_human_assessment": False,
        "representation_id": representation_id,
        "obligation": pinned["obligations"][obligation_id],
        "architecture_source_sha": method_source_binding["architecture_source_sha"],
        "scope_source_revision": SOURCE_REVISION,
        "application_tree_sha1": APP_TREE_SHA1,
        "method_source_binding": method_source_binding,
        "runtime": _runtime_info(),
        "profile_sha256": pinned["profile_sha256"],
        "fitness_configuration_sha256": pinned["fitness_configuration_sha256"],
        "evaluator_artifact_sha256": pinned["mappings"][representation_id][
            "evaluator_artifact_sha256"
        ],
        "evidence_contract_sha256": pinned["mappings"][representation_id][
            "evidence_contract_sha256"
        ],
        "inspection_scope": {
            "unit": scope["inspection_unit"],
            "expected_subjects": scope["expected_subjects"],
            "inspected_subjects": scope["inspected_subjects"],
            "measured_count": scope["measured_count"],
            "evidence_artifact": {"path": inspection_path, "sha256": inspection_digest},
            "scope_record_sha256": inspection_digest,
        },
        "positive_control": controls[f"{obligation_id}_positive"],
        "negative_control": controls[f"{obligation_id}_negative"],
        "mutation_manifest": mutation,
        "control_checks": outcome,
        "semantic_compatible": True if is_valid else None,
        "adequacy_proven": is_valid,
        "status": "VALID" if is_valid else "UNKNOWN",
        "unresolved_conditions": []
        if is_valid
        else [key for key, value in outcome.items() if isinstance(value, bool) and not value],
        "limitations": outcome["limitations"],
        "supporting_artifacts": support,
    }


def _prepare_layer_negative(
    source_root: Path,
    repository_root: Path,
    output_root: Path,
    temp_root: Path,
) -> tuple[Path, dict[str, Any]]:
    negative_root = temp_root / "layering-negative"
    _source_copy(source_root, negative_root)
    patch_path = repository_root / "experiments/pilots/PILOT_01_S1_FAULT.patch"
    if _sha(patch_path) != S1_PATCH_SHA256:
        raise SemanticValidationError("PILOT-01 S1 patch digest mismatch")
    target = negative_root / "app/modules/notifications/repository.py"
    if _sha(target) != NOTIFICATIONS_REPOSITORY_SHA256:
        raise SemanticValidationError("S1 mutation target differs from predeclared clean bytes")
    _run_git(negative_root, "apply", "--check", str(patch_path))
    before_inventory = _directory_inventory(negative_root, "app")
    _run_git(negative_root, "apply", str(patch_path))
    after_inventory = _directory_inventory(negative_root, "app")
    before_inventory_path = output_root / "mutations/AC_LAYERING_negative_app_inventory_before.json"
    after_inventory_path = output_root / "mutations/AC_LAYERING_negative_app_inventory_after.json"
    _write_json(before_inventory_path, before_inventory)
    _write_json(after_inventory_path, after_inventory)
    manifest = {
        "schema_version": 1,
        "mutation_id": "PILOT01_S1_REPOSITORY_TO_API_SECONDARY_CONTROL",
        "control_role": "evaluator_sensitivity_secondary_control_same_transition",
        "source_revision": SOURCE_REVISION,
        "patch_path": "experiments/pilots/PILOT_01_S1_FAULT.patch",
        "patch_sha256": _sha(patch_path),
        "target_path": "app/modules/notifications/repository.py",
        "target_before_sha256": NOTIFICATIONS_REPOSITORY_SHA256,
        "target_after_sha256": _sha(target),
        "app_inventory_before_sha256": before_inventory["files_sha256"],
        "app_inventory_after_sha256": after_inventory["files_sha256"],
        "app_inventory_before_artifact": {
            "path": before_inventory_path.relative_to(output_root).as_posix(),
            "sha256": _sha(before_inventory_path),
        },
        "app_inventory_after_artifact": {
            "path": after_inventory_path.relative_to(output_root).as_posix(),
            "sha256": _sha(after_inventory_path),
        },
        "app_inventory_after": after_inventory,
    }
    manifest_path = output_root / PAIR_SPECS["REP_A01_ARCH_INTERNAL_LAYERING_CI"]["mutation_path"]
    _write_json(manifest_path, manifest)
    return negative_root, manifest


def _prepare_module_negative(
    source_root: Path,
    output_root: Path,
    temp_root: Path,
) -> tuple[Path, dict[str, Any]]:
    negative_root = temp_root / "module-structure-negative"
    _source_copy(source_root, negative_root)
    target = negative_root / "app/modules/audit/model.py"
    if _sha(target) != AUDIT_MODEL_SHA256:
        raise SemanticValidationError(
            "module-structure mutation target differs from predeclared clean bytes"
        )
    before_inventory = _directory_inventory(negative_root, "app")
    target.unlink()
    after_inventory = _directory_inventory(negative_root, "app")
    before_inventory_path = (
        output_root / "mutations/AC_MODULE_STRUCTURE_negative_app_inventory_before.json"
    )
    after_inventory_path = (
        output_root / "mutations/AC_MODULE_STRUCTURE_negative_app_inventory_after.json"
    )
    _write_json(before_inventory_path, before_inventory)
    _write_json(after_inventory_path, after_inventory)
    manifest = {
        "schema_version": 1,
        "mutation_id": "PILOT02_MODULE_STRUCTURE_MISSING_AUDIT_MODEL_V1",
        "source_revision": SOURCE_REVISION,
        "mutation_action": "delete",
        "target_path": "app/modules/audit/model.py",
        "target_before_sha256": AUDIT_MODEL_SHA256,
        "target_after_sha256": None,
        "app_inventory_before_sha256": before_inventory["files_sha256"],
        "app_inventory_after_sha256": after_inventory["files_sha256"],
        "app_inventory_before_artifact": {
            "path": before_inventory_path.relative_to(output_root).as_posix(),
            "sha256": _sha(before_inventory_path),
        },
        "app_inventory_after_artifact": {
            "path": after_inventory_path.relative_to(output_root).as_posix(),
            "sha256": _sha(after_inventory_path),
        },
    }
    manifest_path = output_root / PAIR_SPECS["REP_A01_ARCH_MODULE_STRUCTURE_CI"]["mutation_path"]
    _write_json(manifest_path, manifest)
    return negative_root, manifest


def _verify_mutation_evidence(
    *,
    obligation_id: str,
    source_root: Path,
    output_root: Path,
    mutation: dict[str, Any],
) -> None:
    """Recreate the pinned source mutation and compare all recorded inventories."""
    with tempfile.TemporaryDirectory(prefix="pilot02-mutation-readback-") as temporary:
        mutated_root = Path(temporary) / "mutated-source"
        _source_copy(source_root, mutated_root)
        if obligation_id == "AC_LAYERING":
            patch = source_root / "experiments/pilots/PILOT_01_S1_FAULT.patch"
            if _sha(patch) != S1_PATCH_SHA256:
                raise SemanticValidationError("readback S1 patch digest mismatch")
            target = mutated_root / "app/modules/notifications/repository.py"
            if _sha(target) != NOTIFICATIONS_REPOSITORY_SHA256:
                raise SemanticValidationError("readback S1 source target digest mismatch")
            _run_git(mutated_root, "apply", "--check", str(patch))
            before = _directory_inventory(mutated_root, "app")
            _run_git(mutated_root, "apply", str(patch))
            after = _directory_inventory(mutated_root, "app")
            graph = _layering_scope(mutated_root, Path(temporary) / "grimp-cache")
            graph_reference = mutation.get("mutated_graph_artifact", {})
            if not isinstance(graph_reference, dict):
                raise SemanticValidationError("readback mutated Grimp graph reference missing")
            if _read_json(output_root / str(graph_reference.get("path", ""))) != graph:
                raise SemanticValidationError("readback mutated Grimp graph did not reproduce")
        elif obligation_id == "AC_MODULE_STRUCTURE":
            target = mutated_root / "app/modules/audit/model.py"
            if _sha(target) != AUDIT_MODEL_SHA256:
                raise SemanticValidationError("readback module mutation target digest mismatch")
            before = _directory_inventory(mutated_root, "app")
            target.unlink()
            after = _directory_inventory(mutated_root, "app")
            mutated_scope = _module_file_inventory(mutated_root)
            scope_reference = mutation.get("mutated_scope_artifact", {})
            if not isinstance(scope_reference, dict):
                raise SemanticValidationError("readback mutated module scope reference missing")
            if _read_json(output_root / str(scope_reference.get("path", ""))) != mutated_scope:
                raise SemanticValidationError("readback mutated module scope did not reproduce")
        else:
            raise SemanticValidationError(
                f"unrecognized semantic mutation obligation: {obligation_id}"
            )

        for key, expected in (
            ("app_inventory_before_artifact", before),
            ("app_inventory_after_artifact", after),
        ):
            reference = mutation.get(key)
            if not isinstance(reference, dict):
                raise SemanticValidationError(f"readback mutation inventory missing: {key}")
            artifact = output_root / str(reference.get("path", ""))
            if _read_json(artifact) != expected:
                raise SemanticValidationError(
                    f"readback mutation inventory did not reproduce: {key}"
                )
        if mutation.get("app_inventory_before_sha256") != before["files_sha256"]:
            raise SemanticValidationError("readback clean mutation inventory digest mismatch")
        if mutation.get("app_inventory_after_sha256") != after["files_sha256"]:
            raise SemanticValidationError("readback changed mutation inventory digest mismatch")
        if obligation_id == "AC_LAYERING":
            if mutation.get("target_after_sha256") != _sha(
                mutated_root / "app/modules/notifications/repository.py"
            ):
                raise SemanticValidationError("readback S1 mutated target digest mismatch")
        elif mutation.get("target_after_sha256") is not None:
            raise SemanticValidationError(
                "readback deleted-file mutation must have no after digest"
            )


def run_semantic_controls(
    repository_root: Path,
    output_root: Path,
    architecture_source_sha: str,
) -> dict[str, Any]:
    """Run the preregistered clean and fault controls outside Method P."""
    output_root = output_root.resolve()
    if output_root.is_relative_to(repository_root.resolve()):
        raise SemanticValidationError(
            "semantic evidence output must be outside the source checkout"
        )
    if output_root.exists() and any(output_root.iterdir()):
        raise SemanticValidationError(f"refusing to overwrite evidence directory: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    method_source_binding = _validate_method_source(repository_root, architecture_source_sha)
    method_binding_path = output_root / "inputs/method_source_binding.json"
    _write_json(method_binding_path, method_source_binding)
    snapshot_path = output_root / "inputs/pinned_a01_scope_source.tar"
    source_info = _export_pinned_sources(repository_root, snapshot_path)
    pinned_sources = _extract_snapshot(snapshot_path, output_root / "inputs/source_extract")
    pinned = _validate_pinned_inputs(pinned_sources)
    pinned["runtime_evaluator_versions"] = _validate_runtime_versions(pinned)
    source_info["method_source_binding"] = method_source_binding
    source_info["runtime"] = _runtime_info()
    scope_by_representation: dict[str, dict[str, Any]] = {}
    controls: dict[str, dict[str, Any]] = {}
    mutations: dict[str, dict[str, Any]] = {}

    with tempfile.TemporaryDirectory(prefix="pilot02-semantic-controls-") as temp_directory:
        temp_root = Path(temp_directory)
        clean_root = _extract_snapshot(snapshot_path, temp_root / "clean")
        layering = _layering_scope(clean_root, temp_root / "grimp-cache-clean")
        layering_path = output_root / PAIR_SPECS["REP_A01_ARCH_INTERNAL_LAYERING_CI"]["scope_path"]
        _write_json(layering_path, layering)
        scope_by_representation["REP_A01_ARCH_INTERNAL_LAYERING_CI"] = layering

        structure = _module_file_inventory(clean_root)
        structure_path = output_root / PAIR_SPECS["REP_A01_ARCH_MODULE_STRUCTURE_CI"]["scope_path"]
        _write_json(structure_path, structure)
        scope_by_representation["REP_A01_ARCH_MODULE_STRUCTURE_CI"] = structure

        controls["AC_LAYERING_positive"] = _run_import_linter(
            clean_root, output_root, "AC_LAYERING_positive"
        )
        controls["AC_MODULE_STRUCTURE_positive"] = _run_module_structure(
            clean_root, output_root, "AC_MODULE_STRUCTURE_positive"
        )

        layer_negative_root, mutations["AC_LAYERING"] = _prepare_layer_negative(
            clean_root, repository_root, output_root, temp_root
        )
        mutated_layering = _layering_scope(layer_negative_root, temp_root / "grimp-cache-negative")
        negative_scope_path = output_root / "mutations/AC_LAYERING_negative_graph.json"
        _write_json(negative_scope_path, mutated_layering)
        mutations["AC_LAYERING"]["mutated_graph_artifact"] = {
            "path": negative_scope_path.relative_to(output_root).as_posix(),
            "sha256": _sha(negative_scope_path),
        }
        _write_json(
            output_root / PAIR_SPECS["REP_A01_ARCH_INTERNAL_LAYERING_CI"]["mutation_path"],
            mutations["AC_LAYERING"],
        )
        mutations["AC_LAYERING"] = _read_json(
            output_root / PAIR_SPECS["REP_A01_ARCH_INTERNAL_LAYERING_CI"]["mutation_path"]
        )
        controls["AC_LAYERING_negative"] = _run_import_linter(
            layer_negative_root, output_root, "AC_LAYERING_negative"
        )

        module_negative_root, mutations["AC_MODULE_STRUCTURE"] = _prepare_module_negative(
            clean_root, output_root, temp_root
        )
        mutated_structure = _module_file_inventory(module_negative_root)
        negative_structure_path = output_root / "mutations/AC_MODULE_STRUCTURE_negative_scope.json"
        _write_json(negative_structure_path, mutated_structure)
        mutations["AC_MODULE_STRUCTURE"]["mutated_scope_artifact"] = {
            "path": negative_structure_path.relative_to(output_root).as_posix(),
            "sha256": _sha(negative_structure_path),
        }
        _write_json(
            output_root / PAIR_SPECS["REP_A01_ARCH_MODULE_STRUCTURE_CI"]["mutation_path"],
            mutations["AC_MODULE_STRUCTURE"],
        )
        mutations["AC_MODULE_STRUCTURE"] = _read_json(
            output_root / PAIR_SPECS["REP_A01_ARCH_MODULE_STRUCTURE_CI"]["mutation_path"]
        )
        controls["AC_MODULE_STRUCTURE_negative"] = _run_module_structure(
            module_negative_root, output_root, "AC_MODULE_STRUCTURE_negative"
        )

    checks = _control_expectations(
        output_root, scope_by_representation, controls, mutations, pinned, method_source_binding
    )
    for representation_id in PAIR_SPECS:
        report = _build_report(
            representation_id,
            scope_by_representation[representation_id],
            controls,
            mutations,
            pinned,
            checks,
            output_root,
            method_source_binding,
        )
        report_path = output_root / f"semantic_verification/{representation_id}.json"
        _write_json(report_path, report)

    manifest = _inventory_outputs(output_root)
    _write_json(output_root / "sha256_inventory.json", manifest)
    verified = verify_semantic_evidence_directory(
        output_root,
        repository_root=repository_root,
        expected_architecture_source_sha=architecture_source_sha,
    )
    return {
        "status": "validated"
        if all(item["status"] == "VALID" for item in verified.values())
        else "incomplete",
        "source": source_info,
        "reports": {
            representation_id: {
                "status": row["status"],
                "semantic_compatible": row["semantic_compatible"],
                "adequacy_proven": row["adequacy_proven"],
            }
            for representation_id, row in verified.items()
        },
        "output_dir": str(output_root),
        "inventory_sha256": _sha(output_root / "sha256_inventory.json"),
    }


def _inventory_outputs(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "sha256_inventory.json":
            rows.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha(path),
                }
            )
    return {"schema_version": 1, "artifacts": rows}


def _validate_inventory(root: Path) -> dict[str, Any]:
    inventory_path = root / "sha256_inventory.json"
    inventory = _read_json(inventory_path)
    expected = {str(row["path"]): row for row in inventory.get("artifacts", [])}
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != inventory_path
    }
    if actual_paths != set(expected):
        raise SemanticValidationError("semantic evidence inventory path set mismatch")
    for relative, row in expected.items():
        path = root / relative
        if path.stat().st_size != row.get("size_bytes") or _sha(path) != row.get("sha256"):
            raise SemanticValidationError(f"semantic evidence artifact digest mismatch: {relative}")
    return inventory


def verify_semantic_evidence_directory(
    root: Path,
    *,
    repository_root: Path,
    expected_architecture_source_sha: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Recheck source, report, inspection evidence, and both raw controls."""
    root = root.resolve()
    _validate_inventory(root)
    method_source_binding = _read_json(root / "inputs/method_source_binding.json")
    target_revision = str(method_source_binding.get("architecture_source_sha", ""))
    recomputed_binding = _validate_method_source(repository_root, target_revision)
    if (
        method_source_binding != recomputed_binding
        or expected_architecture_source_sha is not None
        and target_revision != expected_architecture_source_sha
    ):
        raise SemanticValidationError("method architecture-source binding did not reproduce")
    snapshot_path = root / "inputs/pinned_a01_scope_source.tar"
    if not snapshot_path.is_file():
        raise SemanticValidationError("pinned source snapshot missing")
    with tempfile.TemporaryDirectory(prefix="pilot02-semantic-readback-") as temp_directory:
        source_root = _extract_snapshot(snapshot_path, Path(temp_directory) / "source")
        pinned = _validate_pinned_inputs(source_root)
        pinned["runtime_evaluator_versions"] = _validate_runtime_versions(pinned)
        layering_actual = _layering_scope(source_root, Path(temp_directory) / "grimp-cache")
        structure_actual = _module_file_inventory(source_root)
        expected_scopes = {
            "REP_A01_ARCH_INTERNAL_LAYERING_CI": layering_actual,
            "REP_A01_ARCH_MODULE_STRUCTURE_CI": structure_actual,
        }
        verified: dict[str, dict[str, Any]] = {}
        for representation_id, spec in PAIR_SPECS.items():
            scope_path = root / spec["scope_path"]
            scope = _read_json(scope_path)
            if canonical_json_bytes(scope) != canonical_json_bytes(
                expected_scopes[representation_id]
            ):
                raise SemanticValidationError(
                    f"recomputed inspection scope mismatch: {representation_id}"
                )
            mutation = _read_json(root / spec["mutation_path"])
            _verify_mutation_evidence(
                obligation_id=spec["obligation_id"],
                source_root=source_root,
                output_root=root,
                mutation=mutation,
            )
            positive = _read_execution(root, spec["positive_prefix"])
            negative = _read_execution(root, spec["negative_prefix"])
            controls = {
                f"{spec['obligation_id']}_positive": positive,
                f"{spec['obligation_id']}_negative": negative,
            }
            mutations = {spec["obligation_id"]: mutation}
            checks = _control_expectations(
                root, {representation_id: scope}, controls, mutations, pinned, method_source_binding
            )
            report_path = root / f"semantic_verification/{representation_id}.json"
            report = _read_json(report_path)
            expected_report = _build_report(
                representation_id,
                scope,
                controls,
                mutations,
                pinned,
                checks,
                root,
                method_source_binding,
            )
            if canonical_json_bytes(report) != canonical_json_bytes(expected_report):
                raise SemanticValidationError(
                    f"semantic report did not reproduce: {representation_id}"
                )
            verified[representation_id] = report
        return verified


def _read_execution(root: Path, prefix: str) -> dict[str, Any]:
    metadata_path = root / f"{prefix}.json"
    if not metadata_path.is_file():
        raise SemanticValidationError(f"control metadata missing: {metadata_path}")
    metadata = _read_json(metadata_path)
    output = (root / metadata["stdout_artifact"]["path"]).read_bytes()
    error = (root / metadata["stderr_artifact"]["path"]).read_bytes()
    if (
        sha256_bytes(output) != metadata["stdout_artifact"]["sha256"]
        or sha256_bytes(error) != metadata["stderr_artifact"]["sha256"]
    ):
        raise SemanticValidationError(f"control stream digest mismatch: {prefix}")
    result = dict(metadata)
    combined = output + b"\n" + error
    if prefix.startswith("controls/AC_LAYERING"):
        parsed = _parse_import_linter_output(
            combined,
            [
                "Users module internal layering",
                "Tasks module internal layering",
                "Notifications module internal layering",
                "Reporting module internal layering",
                "Audit module internal layering",
            ],
        )
        result["parsed_output"] = {key: value for key, value in parsed.items() if key != "text"}
    else:
        text = combined.decode("utf-8", errors="replace")
        result["parsed_output"] = {
            "one_passed": re.search(r"\b1 passed\b", text) is not None,
            "one_failed": re.search(r"\b1 failed\b", text) is not None,
            "missing_audit_model_reported": "model.py" in text,
            "expected_file_set_assertion_reported": "actual_files == required_files" in text,
        }
    return result


def load_verified_pair_inputs(
    root: Path,
    *,
    repository_root: Path,
    expected_architecture_source_sha: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Return report evidence only after an independent raw-artifact readback."""
    reports = verify_semantic_evidence_directory(
        root,
        repository_root=repository_root,
        expected_architecture_source_sha=expected_architecture_source_sha,
    )
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for representation_id, report in reports.items():
        obligation_id = PAIR_SPECS[representation_id]["obligation_id"]
        artifacts: dict[str, bytes] = {}
        artifact_refs: list[dict[str, str]] = []
        selected = [str(row["path"]) for row in report["supporting_artifacts"] if row.get("sha256")]
        selected.extend(
            [
                f"controls/{obligation_id}_positive.json",
                f"controls/{obligation_id}_negative.json",
                "sha256_inventory.json",
                f"semantic_verification/{representation_id}.json",
            ]
        )
        selected = sorted(set(selected))
        for relative in selected:
            path = root / relative
            if not path.is_file():
                raise SemanticValidationError(f"pair proof artifact missing: {relative}")
            sidecar_path = f"semantic/{relative}"
            content = path.read_bytes()
            artifacts[sidecar_path] = content
            artifact_refs.append({"path": sidecar_path, "sha256": sha256_bytes(content)})
        scope_record = report["inspection_scope"]
        scope = {
            "unit": scope_record["unit"],
            "expected_subjects": list(scope_record["expected_subjects"]),
            "measured_count": scope_record["measured_count"],
            "evidence_artifact": {
                "path": f"semantic/{scope_record['evidence_artifact']['path']}",
                "sha256": scope_record["evidence_artifact"]["sha256"],
            },
        }
        result[(representation_id, obligation_id)] = {
            "report": report,
            "inspection_scope": scope,
            "artifact_bytes": artifacts,
            "evidence_artifacts": artifact_refs,
            "evidence_refs": [
                f"PILOT02_SEMANTIC_REPORT_{obligation_id}",
                f"PILOT02_SEMANTIC_SCOPE_{obligation_id}",
                f"PILOT02_POSITIVE_CONTROL_{obligation_id}",
                f"PILOT02_NEGATIVE_CONTROL_{obligation_id}",
            ],
            "verifier_id": ADAPTATION_VERIFIER_ID,
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--architecture-source-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_semantic_controls(
            args.repository_root.resolve(), args.output_dir, args.architecture_source_sha
        )
    except (OSError, KeyError, ValueError, subprocess.SubprocessError, tarfile.TarError) as error:
        print(json.dumps({"status": "rejected", "reason": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
