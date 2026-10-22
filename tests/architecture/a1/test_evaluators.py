"""Adversarial source fixtures for W0-approved A1 architecture evaluator policies."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import yaml

from architecture.acceptance.a1.analyzers import ANALYZERS
from architecture.acceptance.a1.engine import canonical_json, run_evaluator, verify_evidence
from scripts import check_architecture_stages as stage_checks

ROOT = Path(__file__).resolve().parents[3]
EVALUATOR_ROOT = ROOT / "architecture/acceptance/a1"
CAPABILITIES = ("users", "tasks", "notifications", "reporting", "audit")
FINAL_STATE = "A1_MODULAR_MONOLITH"
CONFIG_FILES = {
    "AC_PUBLIC_API": "public_api_v1.yaml",
    "AC_MODULE_GRAPH": "module_graph_v1.yaml",
    "AC_DATA_OWNERSHIP": "data_ownership_v1.yaml",
}
TABLES = {
    "users": ("User", "users"),
    "tasks": ("Task", "tasks"),
    "notifications": ("Notification", "notifications"),
    "audit": ("AuditEvent", "audit_events"),
}


def _git(
    repo_root: Path, *arguments: str, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("Git is required for source-pinned fixture tests")
    return subprocess.run(  # noqa: S603 - fixed Git executable, argument list, and no shell
        [executable, *arguments],
        cwd=repo_root,
        check=True,
        capture_output=capture_output,
        text=True,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _public_module_fixture(capability: str) -> str:
    definitions = {
        "users": [
            "def user_exists(session: object, user_id: object) -> bool:",
            "    return True",
        ],
        "audit": [
            "def record_event(",
            "    session: object,",
            "    entity_type: str,",
            "    entity_id: object,",
            "    action: str,",
            "    actor_id: object | None,",
            "    details: dict[str, object] | None = None,",
            ") -> None:",
            "    return None",
        ],
        "notifications": [
            "def create_notification(",
            "    session: object, user_id: object, kind: str, message: str",
            ") -> None:",
            "    return None",
        ],
        "tasks": [
            "class TaskSummary(TypedDict):",
            "    total_task_count: int",
            "    count_by_status: dict[str, int]",
            "    assigned_task_count: int",
            "    unassigned_task_count: int",
            "",
            "def get_task_summary(session: object) -> TaskSummary:",
            "    return {}",
        ],
        "reporting": [
            "def get_task_summary(session: object) -> dict[str, object]:",
            "    return {}",
        ],
    }
    lines = definitions[capability]
    if capability == "tasks":
        lines = ["from typing import TypedDict", "", *lines]
    return "\n".join(lines) + "\n"


def _fixture_repo(
    tmp_path: Path,
    source_overrides: dict[str, str] | None = None,
    *,
    state: str = FINAL_STATE,
    omit_modules: set[str] | None = None,
    empty: bool = False,
) -> tuple[Path, str]:
    root = tmp_path / "subject"
    root.mkdir(parents=True)
    omitted = omit_modules or set()
    if not empty:
        for capability in CAPABILITIES:
            if capability in omitted:
                continue
            package = root / "app/modules" / capability
            _write(package / "__init__.py", f'"""{capability} capability."""\n')
            _write(package / "public.py", _public_module_fixture(capability))
            _write(package / "service.py", f'"""{capability} source fixture."""\n')
            if capability in TABLES:
                model, table = TABLES[capability]
                _write(package / "model.py", f'class {model}:\n    __tablename__ = "{table}"\n')
        _write(
            root / "app/db/model_registry.py",
            "from app.modules.users.model import User\n"
            "from app.modules.tasks.model import Task\n"
            "from app.modules.notifications.model import Notification\n"
            "from app.modules.audit.model import AuditEvent\n",
        )
        _write(root / "app/db/session.py", '"""Shared-session fixture."""\n')
    for relative, source in (source_overrides or {}).items():
        _write(root / relative, source)
    _write(
        root / "architecture/states/state.yaml", f"schema_version: 1\narchitecture_state: {state}\n"
    )
    for _evaluator_id, filename in (
        ("AC_PUBLIC_API", "public_api_v1.yaml"),
        ("AC_MODULE_GRAPH", "module_graph_v1.yaml"),
        ("AC_DATA_OWNERSHIP", "data_ownership_v1.yaml"),
    ):
        source_config = yaml.safe_load((EVALUATOR_ROOT / filename).read_text(encoding="utf-8"))
        _write(root / f".fixtures/{filename}", yaml.safe_dump(source_config, sort_keys=False))
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "A1 fixture")
    _git(root, "config", "user.email", "a1-fixture@example.invalid")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixed A1 evaluator fixture")
    sha = _git(root, "rev-parse", "HEAD", capture_output=True).stdout.strip()
    return root, sha


def _run(
    root: Path,
    sha: str,
    evaluator_id: str,
    *,
    state: str | None = None,
    expected_sha: str | None = None,
) -> tuple[dict[str, Any], Path]:
    config_path = root / ".fixtures" / CONFIG_FILES[evaluator_id]
    manifest_path = root / "architecture/states/state.yaml"
    result = run_evaluator(
        evaluator_id,
        root,
        config_path,
        manifest_path,
        state or FINAL_STATE,
        sha if expected_sha is None else expected_sha,
        ANALYZERS[evaluator_id],
    )
    return result, config_path


def _codes(evidence: dict[str, Any]) -> set[str]:
    return {finding["code"] for finding in evidence["result"]["violations"]}


def test_w0_approved_state_applicability_graph_and_ownership_policy() -> None:
    configs = {
        evaluator_id: yaml.safe_load((EVALUATOR_ROOT / filename).read_text(encoding="utf-8"))
        for evaluator_id, filename in CONFIG_FILES.items()
    }
    expected_states = {
        "A0_1_CAPABILITY_MODULES",
        "A0_2_PUBLIC_MODULE_APIS",
        "A0_3_GOVERNED_MODULE_GRAPH",
        "A0_4_REPORT_QUERY_PORT",
        "A0_5_MODULE_DATA_OWNERSHIP",
        FINAL_STATE,
    }

    public_states = configs["AC_PUBLIC_API"]["states"]
    assert set(public_states) == expected_states
    assert public_states["A0_1_CAPABILITY_MODULES"]["applicability"] == "NOT_APPLICABLE"
    assert all(
        public_states[state]["applicability"] == "ACTIVE"
        for state in expected_states - {"A0_1_CAPABILITY_MODULES"}
    )
    legacy_exception = configs["AC_PUBLIC_API"]["public_api"]["legacy_exception"]
    assert legacy_exception["allowed_architecture_states"] == [
        "A0_2_PUBLIC_MODULE_APIS",
        "A0_3_GOVERNED_MODULE_GRAPH",
    ]

    graph = configs["AC_MODULE_GRAPH"]
    assert set(graph["states"]) == expected_states
    assert all(
        graph["states"][state]["applicability"] == "NOT_APPLICABLE"
        for state in ("A0_1_CAPABILITY_MODULES", "A0_2_PUBLIC_MODULE_APIS")
    )
    assert all(
        graph["states"][state]["applicability"] == "ACTIVE"
        for state in (
            "A0_3_GOVERNED_MODULE_GRAPH",
            "A0_4_REPORT_QUERY_PORT",
            "A0_5_MODULE_DATA_OWNERSHIP",
            FINAL_STATE,
        )
    )
    baseline_edges = {
        ("tasks", "users"),
        ("tasks", "notifications"),
        ("tasks", "audit"),
        ("users", "audit"),
        ("reporting", "tasks"),
    }
    allowed = graph["module_graph"]["allowed_dependencies_by_state"]
    for state in (
        "A0_3_GOVERNED_MODULE_GRAPH",
        "A0_4_REPORT_QUERY_PORT",
        "A0_5_MODULE_DATA_OWNERSHIP",
    ):
        assert {(edge["from"], edge["to"]) for edge in allowed[state]} == baseline_edges
    assert {(edge["from"], edge["to"]) for edge in allowed[FINAL_STATE]} == {
        ("tasks", "users"),
        ("tasks", "audit"),
        ("users", "audit"),
        ("reporting", "tasks"),
    }
    assert graph["module_graph"]["forbidden_dependencies_by_state"][FINAL_STATE] == [
        {"from": "tasks", "to": "notifications"}
    ]
    assert "app.events" in graph["module_graph"]["shared_infrastructure_roots"]

    ownership = configs["AC_DATA_OWNERSHIP"]
    assert set(ownership["states"]) == expected_states
    assert all(
        ownership["states"][state]["applicability"] == "NOT_APPLICABLE"
        for state in expected_states - {"A0_5_MODULE_DATA_OWNERSHIP", FINAL_STATE}
    )
    assert ownership["states"]["A0_5_MODULE_DATA_OWNERSHIP"]["applicability"] == "ACTIVE"
    assert ownership["states"][FINAL_STATE]["applicability"] == "ACTIVE"
    assert ownership["data_ownership"]["table_owners"] == {
        "users": "users",
        "tasks": "tasks",
        "notifications": "notifications",
        "audit_events": "audit",
    }
    assert ownership["data_ownership"]["model_registry_exception"] == {
        "path": "app/db/model_registry.py",
        "module": "app.db.model_registry",
        "allowed_target_suffix": ".model",
        "required_import_kind": "from",
        "require_declared_model_symbol": True,
    }


def test_clean_source_fixture_is_non_vacuous_and_emits_schema_valid_evidence(
    tmp_path: Path,
) -> None:
    root, sha = _fixture_repo(tmp_path)
    schema = json.loads((EVALUATOR_ROOT / "evidence.schema.json").read_text(encoding="utf-8"))
    for evaluator_id in ANALYZERS:
        evidence, _ = _run(root, sha, evaluator_id)
        assert evidence["result"]["execution_status"] == "COMPLETED"
        assert evidence["source_scope"]["complete"] is True
        assert len(evidence["source_scope"]["modules"]) == len(CAPABILITIES)
        assert len(evidence["source_scope"]["inspected_paths"]) >= 11
        assert evidence["raw_output"]["available"] is True
        assert evidence["architecture"]["target_source_sha"] == sha
        assert evidence["architecture"]["source_sha_status"] == "MATCHED"
        assert evidence["result"]["compliance"] == "COMPLIANT"
        jsonschema.Draft202012Validator(schema).validate(evidence)
        assert (
            verify_evidence(
                evidence, root, root / ".fixtures" / CONFIG_FILES[evaluator_id], EVALUATOR_ROOT
            )
            == []
        )


def test_private_foreign_repository_import_is_inspected_and_rejected(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {"app/modules/tasks/service.py": "from ..users.repository import get_user\n"},
    )
    evidence, _ = _run(root, sha, "AC_PUBLIC_API")
    assert evidence["result"]["compliance"] == "NON_COMPLIANT"
    assert "CROSS_MODULE_IMPORT_NOT_PUBLIC" in _codes(evidence)
    item = next(
        imported
        for imported in evidence["diagnostics"]["imports"]
        if imported["target_module"] == "app.modules.users.repository"
    )
    assert item["source_path"] == "app/modules/tasks/service.py"
    assert item["imported_name"] == "get_user"
    data_evidence, _ = _run(root, sha, "AC_DATA_OWNERSHIP")
    assert "FOREIGN_REPOSITORY_IMPORT" in _codes(data_evidence)


def test_declared_public_module_import_is_accepted(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {"app/modules/tasks/service.py": "from app.modules.users.public import user_exists\n"},
    )
    evidence, _ = _run(root, sha, "AC_PUBLIC_API")
    assert evidence["result"]["compliance"] == "COMPLIANT"
    assert evidence["diagnostics"]["imports"]
    assert evidence["diagnostics"]["cross_capability_imports"][0]["classification"] == (
        "declared_public_interface"
    )


def test_unapproved_public_symbol_is_rejected(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {"app/modules/tasks/service.py": "from app.modules.users.public import repository\n"},
    )
    evidence, _ = _run(root, sha, "AC_PUBLIC_API")
    assert evidence["result"]["compliance"] == "NON_COMPLIANT"
    assert "UNDECLARED_PUBLIC_INTERFACE" in _codes(evidence)
    observed = evidence["diagnostics"]["cross_capability_imports"][0]
    assert observed["imported_name"] == "repository"
    assert observed["classification"] == "undeclared_public_interface"


def test_missing_frozen_public_export_and_typed_dict_field_are_rejected(
    tmp_path: Path,
) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/users/public.py": textwrap.dedent(
                """\
                def user_lookup(session: object, user_id: object) -> bool:
                    return True
                """
            ),
            "app/modules/tasks/public.py": (
                "from typing import TypedDict\n\n"
                "class TaskSummary(TypedDict):\n"
                "    total_task_count: int\n"
                "    count_by_status: dict[str, int]\n"
                "    assigned_task_count: int\n"
                "    unexpected_count: int\n\n"
                "def get_task_summary(session: object) -> TaskSummary:\n"
                "    return {}\n"
            ),
        },
    )
    evidence, _ = _run(root, sha, "AC_PUBLIC_API")
    assert evidence["result"]["compliance"] == "NON_COMPLIANT"
    assert {
        "PUBLIC_INTERFACE_MISSING",
        "UNDECLARED_PUBLIC_EXPORT",
        "PUBLIC_TYPED_DICT_FIELDS_MISMATCH",
    } <= _codes(evidence)


def test_public_evaluator_fails_closed_if_frozen_interface_config_is_incomplete(
    tmp_path: Path,
) -> None:
    root, sha = _fixture_repo(tmp_path)
    evidence, config_path = _run(root, sha, "AC_PUBLIC_API")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["public_api"]["interfaces_by_capability"].pop("users")
    _write(config_path, yaml.safe_dump(config, sort_keys=False))
    evidence = run_evaluator(
        "AC_PUBLIC_API",
        root,
        config_path,
        root / "architecture/states/state.yaml",
        FINAL_STATE,
        sha,
        ANALYZERS["AC_PUBLIC_API"],
    )
    assert evidence["result"]["execution_status"] == "FAILED"
    assert evidence["result"]["compliance"] == "NOT_EVALUABLE"
    assert (
        "CONFIG_PUBLIC_INTERFACES_COVERAGE_MISMATCH" in evidence["result"]["configuration_errors"]
    )


def test_strict_graph_rejects_unresolved_local_imports(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {"app/modules/tasks/service.py": "from app.api.missing_dependency import check\n"},
    )
    evidence, _ = _run(root, sha, "AC_MODULE_GRAPH")
    assert evidence["result"]["compliance"] == "NON_COMPLIANT"
    assert "UNRESOLVED_LOCAL_IMPORT" in _codes(evidence)
    assert (
        evidence["diagnostics"]["unresolved_local_imports"][0]["target_module"]
        == "app.api.missing_dependency"
    )


def test_undeclared_dependency_edge_is_derived_from_imports(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/reporting/service.py": (
                "from app.modules.notifications.public import notify\n"
            )
        },
    )
    evidence, _ = _run(root, sha, "AC_MODULE_GRAPH")
    assert evidence["result"]["compliance"] == "NON_COMPLIANT"
    assert "UNDECLARED_DEPENDENCY" in _codes(evidence)
    edge = next(edge for edge in evidence["diagnostics"]["edges"] if edge["from"] == "reporting")
    assert (edge["from"], edge["to"]) == ("reporting", "notifications")
    assert edge["references"][0]["target_module"] == "app.modules.notifications.public"


def test_actual_import_cycle_is_detected(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/tasks/service.py": "from app.modules.users.public import users_port\n",
            "app/modules/users/service.py": "from app.modules.tasks.public import tasks_port\n",
        },
    )
    evidence, _ = _run(root, sha, "AC_MODULE_GRAPH")
    assert evidence["result"]["compliance"] == "NON_COMPLIANT"
    assert ["tasks", "users", "tasks"] in evidence["diagnostics"]["cycles"]
    assert "DEPENDENCY_CYCLE" in _codes(evidence)


def test_shared_infrastructure_import_is_recorded_outside_capability_graph(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {"app/modules/tasks/service.py": "from app.db.session import Session\n"},
    )
    evidence, _ = _run(root, sha, "AC_MODULE_GRAPH")
    assert evidence["result"]["compliance"] == "COMPLIANT"
    assert evidence["diagnostics"]["shared_infrastructure_imports"] == [
        {
            "source_path": "app/modules/tasks/service.py",
            "line": 1,
            "source_module": "app.modules.tasks.service",
            "target_module": "app.db.session",
            "imported_name": "Session",
        }
    ]


def test_app_events_import_is_shared_infrastructure(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/tasks/service.py": "from app.events import publish\n",
            "app/events/__init__.py": '"""Shared in-process event contract."""\n',
        },
    )
    evidence, _ = _run(root, sha, "AC_MODULE_GRAPH")
    assert evidence["result"]["compliance"] == "COMPLIANT"
    assert evidence["diagnostics"]["shared_infrastructure_imports"][0]["target_module"] == (
        "app.events"
    )


def test_task_to_notification_import_is_forbidden_in_final_a1(tmp_path: Path) -> None:
    imports = (
        "from app.modules.notifications.service import create_notification\n",
        "from app.modules.notifications.public import create_notification\n",
    )
    for index, import_statement in enumerate(imports):
        root, sha = _fixture_repo(
            tmp_path / str(index),
            {"app/modules/tasks/service.py": import_statement},
            state=FINAL_STATE,
        )
        evidence, _ = _run(root, sha, "AC_MODULE_GRAPH", state=FINAL_STATE)
        assert evidence["result"]["compliance"] == "NON_COMPLIANT"
        assert "FORBIDDEN_DEPENDENCY" in _codes(evidence)


def test_graph_configuration_is_state_specific_and_final_edge_is_forbidden(
    tmp_path: Path,
) -> None:
    source = {
        "app/modules/tasks/service.py": (
            "from app.modules.notifications.public import notifications_port\n"
        )
    }
    intermediate_root, intermediate_sha = _fixture_repo(
        tmp_path / "intermediate", source, state="A0_3_GOVERNED_MODULE_GRAPH"
    )
    intermediate, _ = _run(
        intermediate_root, intermediate_sha, "AC_MODULE_GRAPH", state="A0_3_GOVERNED_MODULE_GRAPH"
    )
    assert intermediate["result"]["compliance"] == "COMPLIANT"
    final_root, final_sha = _fixture_repo(tmp_path / "final", source, state=FINAL_STATE)
    final, _ = _run(final_root, final_sha, "AC_MODULE_GRAPH", state=FINAL_STATE)
    assert final["result"]["compliance"] == "NON_COMPLIANT"
    assert "FORBIDDEN_DEPENDENCY" in _codes(final)


def test_legacy_reporting_edge_is_allowed_only_in_intermediate_state(tmp_path: Path) -> None:
    source = {
        "app/modules/reporting/service.py": "from app.modules.tasks.service import task_summary\n"
    }
    for state in ("A0_2_PUBLIC_MODULE_APIS", "A0_3_GOVERNED_MODULE_GRAPH"):
        intermediate_root, intermediate_sha = _fixture_repo(tmp_path / state, source, state=state)
        intermediate, _ = _run(intermediate_root, intermediate_sha, "AC_PUBLIC_API", state=state)
        assert intermediate["result"]["compliance"] == "COMPLIANT"
        assert (
            intermediate["diagnostics"]["cross_capability_imports"][0]["classification"]
            == "legacy_exception"
        )

    for state in ("A0_4_REPORT_QUERY_PORT", FINAL_STATE):
        later_root, later_sha = _fixture_repo(tmp_path / state, source, state=state)
        later, _ = _run(later_root, later_sha, "AC_PUBLIC_API", state=state)
        assert any(
            item["classification"] == "private_or_undeclared_contract"
            for item in later["diagnostics"]["cross_capability_imports"]
        )
        assert later["result"]["compliance"] == "NON_COMPLIANT"


def test_legacy_exception_configuration_cannot_include_final_a1(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/reporting/service.py": (
                "from app.modules.tasks.service import task_summary\n"
            )
        },
    )
    evidence, config_path = _run(root, sha, "AC_PUBLIC_API")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["public_api"]["legacy_exception"]["allowed_architecture_states"].append(FINAL_STATE)
    _write(config_path, yaml.safe_dump(config, sort_keys=False))
    evidence = run_evaluator(
        "AC_PUBLIC_API",
        root,
        config_path,
        root / "architecture/states/state.yaml",
        FINAL_STATE,
        sha,
        ANALYZERS["AC_PUBLIC_API"],
    )
    assert evidence["result"]["execution_status"] == "FAILED"
    assert evidence["result"]["compliance"] == "NOT_EVALUABLE"
    assert (
        "CONFIG_LEGACY_EXCEPTION_INCLUDES_FINAL_STATE" in evidence["result"]["configuration_errors"]
    )


def test_legacy_exception_configuration_cannot_include_a04(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/reporting/service.py": (
                "from app.modules.tasks.service import task_summary\n"
            )
        },
        state="A0_4_REPORT_QUERY_PORT",
    )
    _, config_path = _run(root, sha, "AC_PUBLIC_API", state="A0_4_REPORT_QUERY_PORT")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["public_api"]["legacy_exception"]["allowed_architecture_states"].append(
        "A0_4_REPORT_QUERY_PORT"
    )
    _write(config_path, yaml.safe_dump(config, sort_keys=False))
    evidence = run_evaluator(
        "AC_PUBLIC_API",
        root,
        config_path,
        root / "architecture/states/state.yaml",
        "A0_4_REPORT_QUERY_PORT",
        sha,
        ANALYZERS["AC_PUBLIC_API"],
    )
    assert evidence["result"]["execution_status"] == "FAILED"
    assert evidence["result"]["compliance"] == "NOT_EVALUABLE"
    assert (
        "CONFIG_LEGACY_EXCEPTION_STATE_SET_MISMATCH" in evidence["result"]["configuration_errors"]
    )


def test_missing_expected_module_makes_scope_incomplete_and_not_evaluable(tmp_path: Path) -> None:
    root, sha = _fixture_repo(tmp_path, omit_modules={"audit"})
    evidence, _ = _run(root, sha, "AC_MODULE_GRAPH")
    assert evidence["source_scope"]["complete"] is False
    assert "MISSING_EXPECTED_MODULE:audit" in evidence["source_scope"]["uncertainties"]
    assert evidence["result"]["compliance"] == "NOT_EVALUABLE"
    schema = json.loads((EVALUATOR_ROOT / "evidence.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(evidence)


def test_empty_vacuous_scope_never_passes(tmp_path: Path) -> None:
    root, sha = _fixture_repo(tmp_path, empty=True)
    evidence, _ = _run(root, sha, "AC_MODULE_GRAPH")
    assert evidence["source_scope"]["complete"] is False
    assert "EMPTY_SOURCE_INSPECTION" in evidence["source_scope"]["uncertainties"]
    assert evidence["result"]["compliance"] == "NOT_EVALUABLE"
    schema = json.loads((EVALUATOR_ROOT / "evidence.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(evidence)


def test_incorrect_architecture_manifest_revision_and_source_sha_are_not_evaluable(
    tmp_path: Path,
) -> None:
    root, sha = _fixture_repo(tmp_path, state="A0_3_GOVERNED_MODULE_GRAPH")
    state_mismatch, _ = _run(root, sha, "AC_MODULE_GRAPH", state=FINAL_STATE)
    assert state_mismatch["architecture"]["manifest_state_status"] == "MISMATCH"
    assert state_mismatch["result"]["compliance"] == "NOT_EVALUABLE"
    source_mismatch, _ = _run(
        root, sha, "AC_MODULE_GRAPH", state="A0_3_GOVERNED_MODULE_GRAPH", expected_sha="0" * 40
    )
    assert source_mismatch["architecture"]["source_sha_status"] == "MISMATCH"
    assert source_mismatch["result"]["compliance"] == "NOT_EVALUABLE"


def test_foreign_model_and_known_foreign_table_access_are_detected(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/tasks/service.py": textwrap.dedent(
                """\
                from app.modules.notifications.public import Notification
                from sqlalchemy import Table
                from sqlalchemy import select
                select(Notification)
                Table("notifications", None)
                """
            ),
        },
    )
    evidence, _ = _run(root, sha, "AC_DATA_OWNERSHIP")
    assert evidence["result"]["compliance"] == "NON_COMPLIANT"
    assert {"FOREIGN_MODEL_IMPORT", "FOREIGN_MODEL_ACCESS", "FOREIGN_TABLE_ACCESS"} <= _codes(
        evidence
    )
    assert any(
        path["target_module"] == "app.modules.tasks.model"
        for path in evidence["diagnostics"]["model_registry_exception"]["observed_allowed_imports"]
    )


def test_model_registry_exception_requires_declared_model_imports(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/db/model_registry.py": (
                "from app.modules.users.model import User\n"
                "from app.modules.tasks.model import UnknownModel\n"
                "from app.modules.notifications.service import create_notification\n"
            )
        },
    )
    evidence, _ = _run(root, sha, "AC_DATA_OWNERSHIP")
    assert evidence["result"]["compliance"] == "NON_COMPLIANT"
    assert "UNJUSTIFIED_INFRASTRUCTURE_EXCEPTION" in _codes(evidence)
    allowed = evidence["diagnostics"]["model_registry_exception"]["observed_allowed_imports"]
    assert [(item["target_module"], item["imported_name"]) for item in allowed] == [
        ("app.modules.users.model", "User")
    ]


def test_metadata_table_index_and_disallowed_engine_creation_are_detected(tmp_path: Path) -> None:
    root, sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/tasks/service.py": textwrap.dedent(
                """\
                from app.models.base import Base
                from sqlalchemy import create_engine
                Base.metadata.tables["users"]
                create_engine("sqlite:///local.db")
                """
            ),
        },
    )
    evidence, _ = _run(root, sha, "AC_DATA_OWNERSHIP")
    assert {"FOREIGN_TABLE_ACCESS", "DISALLOWED_PERSISTENCE_DEPENDENCY"} <= _codes(evidence)


def test_evidence_re_readback_rejects_changed_config_evaluator_and_subject_bytes(
    tmp_path: Path,
) -> None:
    root, sha = _fixture_repo(tmp_path)
    evidence, config_path = _run(root, sha, "AC_MODULE_GRAPH")
    assert verify_evidence(evidence, root, config_path, EVALUATOR_ROOT) == []

    changed_config = (
        config_path.read_text(encoding="utf-8") + "\n# changed after evidence capture\n"
    )
    _write(config_path, changed_config)
    assert "CONFIGURATION_DIGEST_MISMATCH" in verify_evidence(
        evidence, root, config_path, EVALUATOR_ROOT
    )
    _write(config_path, changed_config.removesuffix("\n# changed after evidence capture\n"))

    manifest_path = root / "architecture/states/state.yaml"
    original_manifest = manifest_path.read_text(encoding="utf-8")
    _write(manifest_path, original_manifest + "source_sha: changed\n")
    assert "ARCHITECTURE_MANIFEST_DIGEST_MISMATCH" in verify_evidence(
        evidence, root, config_path, EVALUATOR_ROOT
    )
    _write(manifest_path, original_manifest)

    evaluator_copy = tmp_path / "evaluator-copy"
    evaluator_copy.mkdir()
    for artifact in evidence["evaluator"]["source_artifacts"]:
        shutil.copy2(EVALUATOR_ROOT / artifact["path"], evaluator_copy / artifact["path"])
    tampered = evaluator_copy / "engine.py"
    tampered.write_text(
        tampered.read_text(encoding="utf-8") + "\n# changed evaluator bytes\n", encoding="utf-8"
    )
    assert any(
        item.startswith("EVALUATOR_ARTIFACT_DIGEST_MISMATCH")
        for item in verify_evidence(evidence, root, config_path, evaluator_copy)
    )

    changed_subject = root / "app/modules/tasks/service.py"
    changed_subject.write_text('"""changed source"""\n', encoding="utf-8")
    assert any(
        item.startswith("SUBJECT_SOURCE_DIGEST_MISMATCH")
        for item in verify_evidence(evidence, root, config_path, EVALUATOR_ROOT)
    )


def test_a03_stage_readback_rejects_tampered_raw_diagnostics(tmp_path: Path) -> None:
    root, sha = _fixture_repo(tmp_path, state="A0_3_GOVERNED_MODULE_GRAPH")
    evidence, _ = _run(root, sha, "AC_MODULE_GRAPH", state="A0_3_GOVERNED_MODULE_GRAPH")
    stage_checks._validate_a03_evidence(
        evidence,
        evaluator_id="AC_MODULE_GRAPH",
        expected_source_sha=sha,
        schema_path=EVALUATOR_ROOT / "evidence.schema.json",
    )

    tampered = json.loads(json.dumps(evidence))
    tampered["diagnostics"]["cycles"] = [["tasks", "users", "tasks"]]
    try:
        stage_checks._validate_a03_evidence(
            tampered,
            evaluator_id="AC_MODULE_GRAPH",
            expected_source_sha=sha,
            schema_path=EVALUATOR_ROOT / "evidence.schema.json",
        )
    except stage_checks.StageCheckError as error:
        assert "RAW_OUTPUT_DIGEST_MISMATCH" in str(error)
    else:
        raise AssertionError("A0.3 stage readback accepted tampered raw diagnostics")


def test_checked_in_a03_evidence_is_byte_bound_and_reads_back() -> None:
    readback = json.loads(
        (EVALUATOR_ROOT / "a0_3_evidence_readback.json").read_text(encoding="utf-8")
    )
    source_sha = readback["source_sha"]
    assert readback["readback_status"] == "PASS"
    assert (
        _git(ROOT, "rev-parse", f"{source_sha}:app", capture_output=True).stdout.strip()
        == readback["application_tree_sha"]
    )
    for evaluator_id, record in readback["evaluators"].items():
        relative_path = Path(record["evidence_path"])
        assert not relative_path.is_absolute() and ".." not in relative_path.parts
        evidence_path = EVALUATOR_ROOT / relative_path
        evidence_bytes = evidence_path.read_bytes()
        assert hashlib.sha256(evidence_bytes).hexdigest() == record["evidence_file_sha256"]
        evidence = json.loads(evidence_bytes)
        assert evidence["architecture"]["target_source_sha"] == source_sha
        assert evidence["evaluator"]["configuration_digest"] == record["configuration_sha256"]
        assert evidence["evaluator"]["source_digest"] == record["evaluator_sha256"]
        assert evidence["raw_output"]["sha256"] == record["raw_diagnostics_sha256"]
        stage_checks._validate_a03_evidence(
            evidence,
            evaluator_id=evaluator_id,
            expected_source_sha=source_sha,
            schema_path=EVALUATOR_ROOT / "evidence.schema.json",
        )
        config_path = EVALUATOR_ROOT / CONFIG_FILES[evaluator_id]
        assert verify_evidence(evidence, ROOT, config_path, EVALUATOR_ROOT) == []


def test_checked_in_canonical_a03_checkpoint_is_byte_bound_and_reads_back() -> None:
    checkpoint_path = EVALUATOR_ROOT / "a0_3_canonical_checkpoint.json"
    checkpoint_bytes = checkpoint_path.read_bytes()
    checkpoint = json.loads(checkpoint_bytes)
    source_sha = "26a9bb667da7d0938e38aca15d2bf29fd1de4829"

    assert checkpoint["checkpoint"] == "canonical_post_merge_A0_3_GOVERNED_MODULE_GRAPH"
    assert checkpoint["readback_status"] == "PASS"
    assert checkpoint["source_sha"] == source_sha
    assert (
        _git(ROOT, "rev-parse", f"{source_sha}^{{tree}}", capture_output=True).stdout.strip()
        == checkpoint["repository_tree_sha"]
    )
    assert (
        _git(ROOT, "rev-parse", f"{source_sha}:app", capture_output=True).stdout.strip()
        == checkpoint["application_tree_sha"]
    )

    manifest_relative = Path(checkpoint["source_manifest_path"])
    assert not manifest_relative.is_absolute() and ".." not in manifest_relative.parts
    manifest_bytes = (EVALUATOR_ROOT / manifest_relative).read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == checkpoint["source_manifest_sha256"]
    assert manifest_bytes == (ROOT / stage_checks.A03_MANIFEST).read_bytes()

    for evaluator_id, config_name in CONFIG_FILES.items():
        if evaluator_id not in {"AC_PUBLIC_API", "AC_MODULE_GRAPH"}:
            continue
        record = checkpoint["evaluators"][evaluator_id]
        assert record["execution_status"] == "COMPLETED"
        assert record["compliance"] == "COMPLIANT"
        assert record["source_scope_complete"] is True
        assert record["inspected_files"] == record["source_file_digest_count"] == 31
        assert record["inspected_imports"] == 185
        assert record["violations"] == []
        assert record["source_scope_uncertainties"] == []
        assert record["readback_failures"] == []

        evidence_relative = Path(record["evidence_path"])
        raw_relative = Path(record["raw_output_path"])
        for relative in (evidence_relative, raw_relative):
            assert not relative.is_absolute() and ".." not in relative.parts
        evidence_bytes = (EVALUATOR_ROOT / evidence_relative).read_bytes()
        assert hashlib.sha256(evidence_bytes).hexdigest() == record["evidence_file_sha256"]
        evidence = json.loads(evidence_bytes)
        assert evidence["architecture"]["target_source_sha"] == source_sha
        assert evidence["source_scope"]["uncertainties"] == []
        assert evidence["evaluator"]["source_digest"] == record["evaluator_sha256"]
        assert (
            evidence["evaluator"]["configuration_digest"]
            == record["configuration_sha256"]
        )
        assert evidence["raw_output"]["sha256"] == record["raw_diagnostics_sha256"]
        raw_bytes = (EVALUATOR_ROOT / raw_relative).read_bytes()
        assert hashlib.sha256(raw_bytes).hexdigest() == record["raw_output_file_sha256"]
        assert raw_bytes == canonical_json(evidence["diagnostics"])

        stage_checks._validate_a03_evidence(
            evidence,
            evaluator_id=evaluator_id,
            expected_source_sha=source_sha,
            schema_path=EVALUATOR_ROOT / "evidence.schema.json",
        )
        assert verify_evidence(
            evidence,
            ROOT,
            EVALUATOR_ROOT / config_name,
            EVALUATOR_ROOT,
            evidence_root=EVALUATOR_ROOT,
        ) == []


def test_checked_in_delta_a2_evidence_survives_subject_and_bundle_relocation(
    tmp_path: Path,
) -> None:
    evidence = json.loads(
        (EVALUATOR_ROOT / "a0_2_public_api_observation.json").read_text(encoding="utf-8")
    )
    source_sha = evidence["architecture"]["target_source_sha"]
    assert source_sha == "934f5e045af473acdb197604c761597ba39b026c"
    assert evidence["architecture"]["manifest_root"] == "evidence"
    assert not Path(evidence["architecture"]["manifest_path"]).is_absolute()

    original_subject = tmp_path / "original-subject-checkout"
    _git(ROOT, "clone", "--shared", "--quiet", "--no-checkout", str(ROOT), str(original_subject))
    _git(original_subject, "checkout", "--quiet", "--detach", source_sha)
    assert (
        _git(original_subject, "rev-parse", "HEAD", capture_output=True).stdout.strip()
        == source_sha
    )

    original_bundle = tmp_path / "original-evidence-bundle"
    original_bundle.mkdir()
    original_evaluator_root = original_bundle / "evaluator"
    original_evaluator_root.mkdir()
    manifest_relative = Path(evidence["architecture"]["manifest_path"])
    manifest_path = original_bundle / manifest_relative
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EVALUATOR_ROOT / manifest_relative, manifest_path)
    config_path = original_bundle / CONFIG_FILES[evidence["evaluator"]["id"]]
    shutil.copy2(EVALUATOR_ROOT / config_path.name, config_path)
    for artifact in evidence["evaluator"]["source_artifacts"]:
        shutil.copy2(EVALUATOR_ROOT / artifact["path"], original_evaluator_root / artifact["path"])

    relocated_subject = tmp_path / "relocated-subject-checkout"
    relocated_bundle = tmp_path / "relocated-evidence-bundle"
    shutil.copytree(original_subject, relocated_subject)
    shutil.copytree(original_bundle, relocated_bundle)
    relocated_evaluator_root = relocated_bundle / "evaluator"
    relocated_config_path = relocated_bundle / config_path.name
    assert (
        verify_evidence(
            evidence,
            relocated_subject,
            relocated_config_path,
            relocated_evaluator_root,
            evidence_root=relocated_bundle,
        )
        == []
    )

    absolute_manifest = {
        **evidence,
        "architecture": {
            **evidence["architecture"],
            "manifest_path": str(manifest_path.resolve()),
        },
    }
    assert "ARCHITECTURE_MANIFEST_PATH_NOT_PORTABLE" in verify_evidence(
        absolute_manifest,
        relocated_subject,
        relocated_config_path,
        relocated_evaluator_root,
        evidence_root=relocated_bundle,
    )

    escaping_manifest = {
        **evidence,
        "architecture": {
            **evidence["architecture"],
            "manifest_path": "../outside/state.yaml",
        },
    }
    assert "ARCHITECTURE_MANIFEST_PATH_ESCAPES_ROOT" in verify_evidence(
        escaping_manifest,
        relocated_subject,
        relocated_config_path,
        relocated_evaluator_root,
        evidence_root=relocated_bundle,
    )


def test_non_applicable_state_keeps_diagnostics_without_compliance_claim(
    tmp_path: Path,
) -> None:
    root, source_sha = _fixture_repo(
        tmp_path,
        {
            "app/modules/tasks/service.py": (
                "from app.modules.users.repository import get_user\n"
                "from app.modules.notifications.service import create_notification\n"
                "from app.modules.audit.service import record_event\n"
            ),
            "app/modules/users/repository.py": '"""User repository fixture."""\n',
            "app/modules/users/service.py": "from app.modules.audit.service import record_event\n",
            "app/modules/reporting/service.py": (
                "from app.modules.tasks.service import task_summary\n"
            ),
        },
        state="A0_1_CAPABILITY_MODULES",
    )
    manifest = root / "architecture/states/state.yaml"
    outputs = {}
    for evaluator_id, config_name in (
        ("AC_PUBLIC_API", "public_api_v1.yaml"),
        ("AC_MODULE_GRAPH", "module_graph_v1.yaml"),
        ("AC_DATA_OWNERSHIP", "data_ownership_v1.yaml"),
    ):
        evidence = run_evaluator(
            evaluator_id,
            root,
            EVALUATOR_ROOT / config_name,
            manifest,
            "A0_1_CAPABILITY_MODULES",
            source_sha,
            ANALYZERS[evaluator_id],
        )
        assert evidence["result"]["execution_status"] == "COMPLETED"
        assert evidence["result"]["compliance"] == "NOT_APPLICABLE"
        assert evidence["source_scope"]["complete"] is True
        assert evidence["architecture"]["target_source_sha"] == source_sha
        assert evidence["architecture"]["source_sha_status"] == "MATCHED"
        assert evidence["result"]["violation_count"] == 0
        outputs[evaluator_id] = evidence
    graph = outputs["AC_MODULE_GRAPH"]["diagnostics"]
    assert {tuple((edge["from"], edge["to"])) for edge in graph["edges"]} == {
        ("tasks", "users"),
        ("tasks", "notifications"),
        ("tasks", "audit"),
        ("users", "audit"),
        ("reporting", "tasks"),
    }
    ownership = outputs["AC_DATA_OWNERSHIP"]["diagnostics"]
    assert any(
        item["code"] == "FOREIGN_REPOSITORY_IMPORT"
        for item in ownership["observed_policy_findings"]
    )
    assert ownership["model_registry_exception"]["observed_allowed_imports"]
