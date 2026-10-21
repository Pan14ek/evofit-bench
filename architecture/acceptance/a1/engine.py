"""Shared source inventory and evidence utilities for the A1 evaluators."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from shutil import which
from typing import Any

import yaml

JSONValue = dict[str, Any] | list[Any] | str | int | float | bool | None
Analyzer = Callable[
    [dict[str, Any], "SourceInventory", str], tuple[dict[str, Any], list[dict[str, Any]], list[str]]
]


@dataclass(frozen=True)
class SourceInventory:
    repo_root: Path
    modules: list[dict[str, Any]]
    source_files: list[str]
    file_digests: list[dict[str, str]]
    imports: list[dict[str, Any]]
    trees: dict[str, ast.Module]
    uncertainties: list[str]

    @property
    def complete(self) -> bool:
        return not self.uncertainties


def canonical_json(value: JSONValue) -> bytes:
    """Serialize JSON evidence deterministically for digesting."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    """Hash one file without interpreting its contents."""
    return sha256_bytes(path.read_bytes())


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _module_exists(root: Path, dotted_name: str) -> bool:
    if not dotted_name:
        return False
    candidate = root.joinpath(*dotted_name.split("."))
    return candidate.with_suffix(".py").is_file() or (candidate / "__init__.py").is_file()


def _source_module(root: Path, path: Path, capability: str | None) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    if capability is not None:
        return ".".join(["app", "modules", capability, *parts[3:]])
    return ".".join(parts)


def _capability_for_module(module_name: str, capabilities: set[str]) -> str | None:
    prefix = "app.modules."
    if not module_name.startswith(prefix):
        return None
    remainder = module_name[len(prefix) :]
    capability = remainder.split(".", 1)[0]
    return capability if capability in capabilities else None


def _resolve_import_from(
    root: Path, source_package: str, node: ast.ImportFrom, alias_name: str
) -> str:
    if node.level:
        relative_name = "." * node.level + (node.module or "")
        try:
            base = importlib.util.resolve_name(relative_name, source_package)
        except (ImportError, ValueError):
            return node.module or ""
    else:
        base = node.module or ""
    if alias_name != "*" and base:
        child = f"{base}.{alias_name}"
        if _module_exists(root, child):
            return child
    return base


def _import_records(
    root: Path, path: Path, capability: str | None, tree: ast.Module, known: set[str]
) -> list[dict[str, Any]]:
    source_module = _source_module(root, path, capability)
    is_package = path.name == "__init__.py"
    source_package = source_module if is_package else source_module.rpartition(".")[0]
    records: list[dict[str, Any]] = []
    nodes = sorted(
        (node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))),
        key=lambda node: (getattr(node, "lineno", 0), type(node).__name__),
    )
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                records.append(
                    {
                        "source_path": _relative(path, root),
                        "source_module": source_module,
                        "source_capability": capability,
                        "line": node.lineno,
                        "kind": "import",
                        "imported_module": alias.name,
                        "imported_name": None,
                        "binding": alias.asname or alias.name.split(".", 1)[0],
                        "target_module": target,
                        "target_capability": _capability_for_module(target, known),
                    }
                )
        else:
            for alias in node.names:
                target = _resolve_import_from(root, source_package, node, alias.name)
                records.append(
                    {
                        "source_path": _relative(path, root),
                        "source_module": source_module,
                        "source_capability": capability,
                        "line": node.lineno,
                        "kind": "from",
                        "imported_module": node.module,
                        "imported_name": alias.name,
                        "binding": alias.asname or alias.name,
                        "target_module": target,
                        "target_capability": _capability_for_module(target, known),
                    }
                )
    return records


def inspect_source_scope(repo_root: Path, config: dict[str, Any]) -> SourceInventory:
    """Discover configured capability packages and parse every in-scope Python file."""
    root = repo_root.resolve()
    scope = config["source_scope"]
    module_root = (root / scope["module_root"]).resolve()
    expected = set(scope["expected_modules"])
    uncertainties: list[str] = []
    discovered: set[str] = set()
    if not module_root.is_dir():
        uncertainties.append(f"MODULE_ROOT_MISSING:{scope['module_root']}")
    else:
        for path in sorted(module_root.iterdir()):
            if path.is_dir() and not path.name.startswith("__"):
                if (path / "__init__.py").is_file():
                    discovered.add(path.name)
                elif path.name in expected:
                    uncertainties.append(
                        f"MISSING_PACKAGE_INIT:{path.relative_to(root).as_posix()}/__init__.py"
                    )
    for name in sorted(expected - discovered):
        uncertainties.append(f"MISSING_EXPECTED_MODULE:{name}")
    for name in sorted(discovered - expected):
        uncertainties.append(f"UNEXPECTED_DISCOVERED_MODULE:{name}")

    capabilities = sorted(expected | discovered)
    module_records: list[dict[str, Any]] = []
    python_paths: set[Path] = set()
    for name in capabilities:
        package = module_root / name
        package_files = sorted(package.rglob("*.py")) if package.is_dir() else []
        safe_files: list[Path] = []
        for path in package_files:
            try:
                path.resolve().relative_to(root)
            except ValueError:
                uncertainties.append(f"SOURCE_PATH_ESCAPES_ROOT:{path}")
                continue
            safe_files.append(path)
            python_paths.add(path)
        if name in expected and len(safe_files) < int(
            scope.get("minimum_source_files_per_module", 1)
        ):
            uncertainties.append(f"INSUFFICIENT_MODULE_SOURCE:{name}")
        module_records.append(
            {
                "name": name,
                "package": f"app.modules.{name}",
                "path": _relative(package, root)
                if package.exists()
                else f"{scope['module_root']}/{name}",
                "discovered": name in discovered,
                "expected": name in expected,
                "inspected_file_count": len(safe_files),
            }
        )

    for entry in scope.get("additional_source_files", []):
        path = (root / entry["path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            uncertainties.append(f"ADDITIONAL_SOURCE_ESCAPES_ROOT:{entry['path']}")
            continue
        if not path.is_file():
            uncertainties.append(f"MISSING_REQUIRED_SOURCE:{entry['path']}")
        else:
            python_paths.add(path)

    if not python_paths:
        uncertainties.append("EMPTY_SOURCE_INSPECTION")
    minimum = int(scope.get("minimum_inspected_files", 1))
    if len(python_paths) < minimum:
        uncertainties.append(f"INSUFFICIENT_INSPECTED_FILES:{len(python_paths)}<{minimum}")

    trees: dict[str, ast.Module] = {}
    imports: list[dict[str, Any]] = []
    file_digests: list[dict[str, str]] = []
    source_files: list[str] = []
    for path in sorted(python_paths):
        relative = _relative(path, root)
        source_files.append(relative)
        file_digests.append({"path": relative, "sha256": file_sha256(path)})
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            uncertainties.append(f"SOURCE_PARSE_ERROR:{relative}:{type(exc).__name__}")
            continue
        capability: str | None = None
        if path.is_relative_to(module_root):
            rel = path.relative_to(module_root)
            capability = rel.parts[0] if rel.parts else None
        trees[relative] = tree
        imports.extend(_import_records(root, path, capability, tree, set(capabilities)))

    imports.sort(
        key=lambda item: (
            item["source_path"],
            item["line"],
            item["target_module"],
            item["imported_name"] or "",
        )
    )
    return SourceInventory(
        repo_root=root,
        modules=module_records,
        source_files=source_files,
        file_digests=file_digests,
        imports=imports,
        trees=trees,
        uncertainties=sorted(set(uncertainties)),
    )


def _git_value(repo_root: Path, *args: str) -> str | None:
    executable = which("git")
    if executable is None:
        return None
    result = subprocess.run(  # noqa: S603 - fixed Git executable, argument list, and no shell
        [executable, "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _source_dirty(repo_root: Path, source_paths: list[str]) -> bool | None:
    if not source_paths:
        return None
    executable = which("git")
    if executable is None:
        return None
    result = subprocess.run(  # noqa: S603 - fixed Git executable, argument list, and no shell
        [
            executable,
            "-C",
            str(repo_root),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *source_paths,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())


def _configuration_digest(config_path: Path) -> str:
    return file_sha256(config_path)


def _evaluator_artifacts() -> list[dict[str, str]]:
    evaluator_root = Path(__file__).resolve().parent
    artifacts = []
    for path in sorted(evaluator_root.glob("*.py")):
        artifacts.append({"path": path.name, "sha256": file_sha256(path)})
    return artifacts


def _load_manifest(
    repo_root: Path, manifest_path: Path
) -> tuple[str | None, str | None, str | None]:
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, UnicodeDecodeError):
        return None, None, "ARCHITECTURE_MANIFEST_UNAVAILABLE"
    if not isinstance(manifest, dict):
        return None, None, "ARCHITECTURE_MANIFEST_INVALID"
    state = manifest.get("architecture_state")
    if not isinstance(state, str):
        return None, None, "ARCHITECTURE_MANIFEST_STATE_MISSING"
    source_sha = manifest.get("source_sha")
    return state, source_sha if isinstance(source_sha, str) else None, None


def load_configuration(config_path: Path) -> dict[str, Any]:
    """Load a versioned YAML evaluator configuration."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("CONFIG_SCHEMA_INVALID")
    if not isinstance(raw.get("evaluator"), dict) or not isinstance(raw.get("source_scope"), dict):
        raise ValueError("CONFIG_REQUIRED_SECTION_MISSING")
    expected = raw["source_scope"].get("expected_modules")
    if not isinstance(expected, list) or not expected or len(set(expected)) != len(expected):
        raise ValueError("EXPECTED_MODULES_INVALID")
    return raw


def _state_assessment(
    config: dict[str, Any],
    state: str,
    manifest_path: Path,
    repo_root: Path,
    source_sha: str | None,
    expected_source_sha: str | None,
) -> tuple[str, str, list[str], str | None]:
    uncertainties: list[str] = []
    state_rules = config.get("states", {})
    rule = state_rules.get(state) if isinstance(state_rules, dict) else None
    if not isinstance(rule, dict):
        uncertainties.append("ARCHITECTURE_STATE_NOT_CONFIGURED")
        applicability = "UNKNOWN"
    else:
        applicability = str(rule.get("applicability", "UNKNOWN"))
    manifest_state, manifest_source_sha, manifest_error = _load_manifest(repo_root, manifest_path)
    if manifest_error:
        uncertainties.append(manifest_error)
        state_status = "UNAVAILABLE"
    elif manifest_state != state:
        uncertainties.append(f"ARCHITECTURE_REVISION_MISMATCH:{manifest_state}!={state}")
        state_status = "MISMATCH"
    else:
        state_status = "MATCHED"
    if manifest_source_sha and source_sha and manifest_source_sha != source_sha:
        uncertainties.append("MANIFEST_SOURCE_SHA_MISMATCH")
        state_status = "MISMATCH"
    if expected_source_sha is None:
        source_status = "UNPINNED"
    elif source_sha is None:
        source_status = "UNAVAILABLE"
        uncertainties.append("TARGET_SOURCE_SHA_UNAVAILABLE")
    elif expected_source_sha != source_sha:
        source_status = "MISMATCH"
        uncertainties.append("TARGET_SOURCE_SHA_MISMATCH")
    else:
        source_status = "MATCHED"
    return applicability, state_status, uncertainties, source_status


def run_evaluator(
    evaluator_id: str,
    repo_root: Path,
    config_path: Path,
    manifest_path: Path,
    architecture_state: str,
    expected_source_sha: str | None,
    analyzer: Analyzer,
) -> dict[str, Any]:
    """Run one evaluator and preserve execution, scope, compliance, and provenance separately."""
    root = repo_root.resolve()
    config_file = config_path.resolve()
    manifest_file = manifest_path.resolve()
    errors: list[str] = []
    try:
        config = load_configuration(config_file)
        configured_id = str(config["evaluator"].get("id", ""))
        if configured_id != evaluator_id:
            raise ValueError("EVALUATOR_ID_MISMATCH")
    except (OSError, yaml.YAMLError, UnicodeDecodeError, ValueError, TypeError) as exc:
        config = {
            "evaluator": {"id": evaluator_id, "version": "unknown"},
            "source_scope": {
                "module_root": "app/modules",
                "expected_modules": ["users", "tasks", "notifications", "reporting", "audit"],
            },
            "states": {},
        }
        errors.append(str(exc) or type(exc).__name__)

    inventory = inspect_source_scope(root, config)
    source_sha = _git_value(root, "rev-parse", "HEAD")
    dirty = _source_dirty(root, inventory.source_files)
    applicability, state_status, state_uncertainties, source_status = _state_assessment(
        config, architecture_state, manifest_file, root, source_sha, expected_source_sha
    )
    errors.extend(state_uncertainties)
    diagnostics: dict[str, Any] = {"imports": inventory.imports}
    findings: list[dict[str, Any]] = []
    analyzer_errors: list[str] = []
    if not any(error.startswith("EVALUATOR_ID_MISMATCH") for error in errors):
        try:
            analyzed_diagnostics, findings, analyzer_errors = analyzer(
                config, inventory, architecture_state
            )
            diagnostics = {
                "imports": inventory.imports,
                **analyzed_diagnostics,
                "observed_policy_findings": findings,
            }
        except (KeyError, TypeError, ValueError) as exc:
            analyzer_errors.append(f"ANALYZER_CONFIGURATION_ERROR:{exc}")
    errors.extend(analyzer_errors)

    scope_uncertainties = sorted(
        set(
            inventory.uncertainties
            + [e for e in errors if e.startswith("SOURCE_SCOPE_") or e.startswith("SOURCE_TABLE_")]
        )
    )
    evaluator_root = Path(__file__).resolve().parent
    evaluator_artifacts = _evaluator_artifacts()
    config_digest = _configuration_digest(config_file) if config_file.is_file() else None
    manifest_digest = file_sha256(manifest_file) if manifest_file.is_file() else None
    hard_revision_problem = state_status != "MATCHED" or source_status == "MISMATCH"
    if errors and any(
        error.startswith(("CONFIG_", "EXPECTED_MODULES_", "EVALUATOR_ID_MISMATCH"))
        for error in errors
    ):
        execution_status = "FAILED"
    else:
        execution_status = "COMPLETED"
    if execution_status == "FAILED" or hard_revision_problem or not inventory.complete or errors:
        compliance = "NOT_EVALUABLE"
    elif source_status == "UNPINNED" or source_status == "UNAVAILABLE" or dirty is None:
        compliance = "UNKNOWN"
    elif dirty:
        scope_uncertainties.append("SUBJECT_SOURCE_FILES_DIRTY")
        compliance = "NOT_EVALUABLE"
    elif applicability == "NOT_APPLICABLE":
        compliance = "NOT_APPLICABLE"
    elif applicability != "ACTIVE":
        compliance = "UNKNOWN"
    elif findings:
        compliance = "NON_COMPLIANT"
    else:
        compliance = "COMPLIANT"

    if compliance in {"NOT_EVALUABLE", "UNKNOWN"}:
        active_violations: list[dict[str, Any]] = []
    elif compliance == "ACTIVE" or compliance == "NON_COMPLIANT":
        active_violations = findings
    else:
        active_violations = []

    raw_digest = sha256_bytes(canonical_json(diagnostics))
    return {
        "schema_version": 1,
        "evaluator": {
            "id": evaluator_id,
            "obligation_id": str(config["evaluator"].get("obligation_id", evaluator_id)),
            "version": str(config["evaluator"].get("version", "unknown")),
            "source_digest": sha256_bytes(canonical_json(evaluator_artifacts)),
            "source_artifact_root": _relative(evaluator_root, root)
            if evaluator_root.is_relative_to(root)
            else "architecture/acceptance/a1",
            "source_artifacts": evaluator_artifacts,
            "configuration_digest": config_digest,
        },
        "architecture": {
            "state": architecture_state,
            "manifest_path": _relative(manifest_file, root)
            if manifest_file.is_relative_to(root)
            else str(manifest_file),
            "manifest_digest": manifest_digest,
            "manifest_state_status": state_status,
            "target_source_sha": source_sha,
            "expected_source_sha": expected_source_sha,
            "source_sha_status": source_status,
            "subject_source_dirty": dirty,
        },
        "source_scope": {
            "module_root": str(config["source_scope"].get("module_root", "app/modules")),
            "complete": inventory.complete and not scope_uncertainties,
            "modules": inventory.modules,
            "inspected_paths": inventory.source_files,
            "inspected_import_count": len(inventory.imports),
            "source_file_digests": inventory.file_digests,
            "uncertainties": sorted(
                set(
                    scope_uncertainties
                    + [
                        e
                        for e in errors
                        if e.startswith("ARCHITECTURE_")
                        or e.startswith("TARGET_SOURCE_")
                        or e.startswith("MANIFEST_")
                    ]
                )
            ),
        },
        "applicability": applicability,
        "result": {
            "execution_status": execution_status,
            "compliance": compliance,
            "violation_count": len(active_violations),
            "violations": active_violations,
            "configuration_errors": sorted(
                set(
                    e
                    for e in errors
                    if e.startswith(
                        (
                            "CONFIG_",
                            "EXPECTED_MODULES_",
                            "EVALUATOR_ID_MISMATCH",
                            "ANALYZER_CONFIGURATION_ERROR",
                        )
                    )
                )
            ),
        },
        "diagnostics": diagnostics,
        "raw_output": {"available": True, "format": "application/json", "sha256": raw_digest},
        "coverage_limits": config.get("coverage_limits", []),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def verify_evidence(
    evidence: dict[str, Any],
    repo_root: Path,
    config_path: Path,
    evaluator_root: Path | None = None,
) -> list[str]:
    """Re-read exact manifest, source, config, and evaluator bytes referenced by evidence."""
    failures: list[str] = []
    manifest_value = evidence.get("architecture", {}).get("manifest_path")
    manifest_digest = evidence.get("architecture", {}).get("manifest_digest")
    if isinstance(manifest_value, str):
        manifest_path = Path(manifest_value)
        if not manifest_path.is_absolute():
            manifest_path = repo_root / manifest_path
        if not manifest_path.is_file():
            failures.append("ARCHITECTURE_MANIFEST_MISSING")
        elif file_sha256(manifest_path) != manifest_digest:
            failures.append("ARCHITECTURE_MANIFEST_DIGEST_MISMATCH")
    else:
        failures.append("ARCHITECTURE_MANIFEST_PATH_MISSING")
    if not config_path.is_file() or file_sha256(config_path) != evidence.get("evaluator", {}).get(
        "configuration_digest"
    ):
        failures.append("CONFIGURATION_DIGEST_MISMATCH")
    artifact_root = evaluator_root or (
        repo_root
        / evidence.get("evaluator", {}).get("source_artifact_root", "architecture/acceptance/a1")
    )
    observed_artifacts: list[dict[str, str]] = []
    for item in evidence.get("evaluator", {}).get("source_artifacts", []):
        path = artifact_root / item["path"]
        if not path.is_file():
            failures.append(f"EVALUATOR_ARTIFACT_MISSING:{item['path']}")
        else:
            digest = file_sha256(path)
            observed_artifacts.append({"path": item["path"], "sha256": digest})
            if digest != item.get("sha256"):
                failures.append(f"EVALUATOR_ARTIFACT_DIGEST_MISMATCH:{item['path']}")
    if observed_artifacts and sha256_bytes(canonical_json(observed_artifacts)) != evidence.get(
        "evaluator", {}
    ).get("source_digest"):
        failures.append("EVALUATOR_SOURCE_DIGEST_MISMATCH")
    for item in evidence.get("source_scope", {}).get("source_file_digests", []):
        path = repo_root / item["path"]
        if not path.is_file() or file_sha256(path) != item.get("sha256"):
            failures.append(f"SUBJECT_SOURCE_DIGEST_MISMATCH:{item['path']}")
    return sorted(set(failures))
