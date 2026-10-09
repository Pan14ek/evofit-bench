"""Deterministic AST checks for capability-local dependency layering."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "app/modules"
MODULE_LAYERS = {
    "users": ("api", "service", "repository", "model"),
    "tasks": ("api", "service", "repository", "model"),
    "notifications": ("api", "service", "repository", "model"),
    "reporting": ("api", "service"),
    "audit": ("service", "repository", "model"),
}


def imported_modules(path: Path) -> set[str]:
    """Read direct absolute imports from one Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def layer_violations(module_name: str) -> list[str]:
    """Find same-module imports that point from a lower layer to a higher one."""
    layers = MODULE_LAYERS[module_name]
    layer_index = {layer: index for index, layer in enumerate(layers)}
    package_prefix = f"app.modules.{module_name}."
    violations: list[str] = []
    for source_layer, source_index in layer_index.items():
        source_file = ROOT / module_name / f"{source_layer}.py"
        if not source_file.exists():
            continue
        for imported in imported_modules(source_file):
            if not imported.startswith(package_prefix):
                continue
            target_layer = imported.removeprefix(package_prefix).split(".", 1)[0]
            target_index = layer_index.get(target_layer)
            if target_index is not None and target_index < source_index:
                violations.append(
                    f"{source_file.relative_to(ROOT)} imports higher layer {imported}"
                )
    return sorted(violations)


@pytest.mark.parametrize("module_name", MODULE_LAYERS)
def test_module_dependencies_follow_local_layer_order(module_name: str) -> None:
    """Each capability keeps its own allowed internal dependency direction."""
    assert layer_violations(module_name) == []
