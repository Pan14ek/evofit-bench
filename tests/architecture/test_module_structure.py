"""Exact acceptance checks for the DA01 capability-module manifest."""

from pathlib import Path
from typing import Any, TypedDict

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "architecture/states/A0_1_CAPABILITY_MODULES.yaml"


class ModuleContract(TypedDict):
    package: str
    required_files: list[str]


EXPECTED_MODULES: dict[str, ModuleContract] = {
    "users": {
        "package": "app.modules.users",
        "required_files": [
            "__init__.py",
            "api.py",
            "schemas.py",
            "service.py",
            "repository.py",
            "model.py",
        ],
    },
    "tasks": {
        "package": "app.modules.tasks",
        "required_files": [
            "__init__.py",
            "api.py",
            "schemas.py",
            "service.py",
            "repository.py",
            "model.py",
        ],
    },
    "notifications": {
        "package": "app.modules.notifications",
        "required_files": [
            "__init__.py",
            "api.py",
            "schemas.py",
            "service.py",
            "repository.py",
            "model.py",
        ],
    },
    "reporting": {
        "package": "app.modules.reporting",
        "required_files": ["__init__.py", "api.py", "schemas.py", "service.py"],
    },
    "audit": {
        "package": "app.modules.audit",
        "required_files": ["__init__.py", "service.py", "repository.py", "model.py"],
    },
}
EXPECTED_SHARED_INFRASTRUCTURE = [
    "app.config",
    "app.db",
    "app.experiment",
    "app.observability",
    "app.api.dependencies",
    "app.api.health",
    "app.api.metrics",
    "app.api.experiment",
    "app.models.base",
    "app.services.errors",
]
EXPECTED_DEPENDENCIES = [
    {
        "from": "app.modules.tasks.service",
        "to": "app.modules.users.repository",
        "rationale": "Preserved from A0; public module APIs belong to DA02.",
    },
    {
        "from": "app.modules.tasks.service",
        "to": "app.modules.notifications.service",
        "rationale": "Preserved from A0; communication abstraction changes later.",
    },
    {
        "from": "app.modules.tasks.service",
        "to": "app.modules.audit.service",
        "rationale": "Preserved from A0.",
    },
    {
        "from": "app.modules.users.service",
        "to": "app.modules.audit.service",
        "rationale": "Preserved from A0.",
    },
    {
        "from": "app.modules.reporting.service",
        "to": "app.modules.tasks.service",
        "rationale": "Preserved from A0; Task query port belongs to DA04.",
    },
]
EXPECTED_GOVERNANCE = {
    "cross_module_public_api_enforcement": False,
    "module_dependency_graph_governance": False,
    "module_data_ownership_enforcement": False,
    "domain_event_communication": False,
}
LEGACY_CAPABILITY_FILES = (
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


def load_manifest() -> dict[str, Any]:
    """Load the checked-in architecture-state manifest."""
    parsed = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def shared_infrastructure_path(module_name: str) -> Path:
    """Resolve a dotted Python package or module name to its source path."""
    path = ROOT.joinpath(*module_name.split("."))
    return path if path.is_dir() else path.with_suffix(".py")


def test_manifest_matches_exact_da01_module_contract() -> None:
    """The manifest, source files, shared infrastructure, and declared edges agree."""
    manifest = load_manifest()
    assert manifest["schema_version"] == 1
    assert manifest["architecture_state"] == "A0_1_CAPABILITY_MODULES"
    assert manifest["source_state"] == "A0_MONOLITH"
    assert manifest["scenario_id"] == "DA01"
    assert manifest["deployment"] == {
        "deployment_units": 1,
        "application_processes": 1,
        "database_instances": 1,
        "database_product": "PostgreSQL",
        "internal_communication": "synchronous_python_calls",
        "message_broker": "none",
    }
    assert manifest["modules"] == EXPECTED_MODULES
    assert manifest["shared_infrastructure"] == EXPECTED_SHARED_INFRASTRUCTURE
    assert manifest["preserved_cross_module_dependencies"] == EXPECTED_DEPENDENCIES
    assert manifest["governance"] == EXPECTED_GOVERNANCE

    modules_root = ROOT / "app/modules"
    actual_packages = {
        path.name
        for path in modules_root.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }
    assert actual_packages == set(EXPECTED_MODULES)
    assert {path.name for path in modules_root.glob("*.py")} == {"__init__.py"}

    for module in EXPECTED_MODULES.values():
        package_path = ROOT.joinpath(*module["package"].split("."))
        required_files = set(module["required_files"])
        actual_files = {path.name for path in package_path.glob("*.py")}
        assert actual_files == required_files

    assert all(shared_infrastructure_path(name).exists() for name in EXPECTED_SHARED_INFRASTRUCTURE)
    assert all(not (ROOT / legacy_path).exists() for legacy_path in LEGACY_CAPABILITY_FILES)
    assert not (ROOT / "app/repositories").exists()
    assert not (ROOT / "app/schemas").exists()
