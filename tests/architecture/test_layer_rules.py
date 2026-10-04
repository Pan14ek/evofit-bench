"""Deterministic AST checks for A0 horizontal dependency rules."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "app"


def imported_modules(path: Path) -> set[str]:
    """Read direct app imports from one source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def modules_under(layer: str) -> set[str]:
    """Collect imports from Python files in a layer."""
    return {module for path in (ROOT / layer).rglob("*.py") for module in imported_modules(path)}


def test_api_does_not_import_repositories() -> None:
    """HTTP handlers depend on services/schemas, not persistence details."""
    assert not any(module.startswith("app.repositories") for module in modules_under("api"))


def test_repositories_do_not_import_api() -> None:
    """Persistence functions do not depend on HTTP handlers."""
    assert not any(module.startswith("app.api") for module in modules_under("repositories"))


def test_models_do_not_import_api_or_services() -> None:
    """Persistence models remain independent of upper layers."""
    modules = modules_under("models")
    assert not any(module.startswith(("app.api", "app.services")) for module in modules)
