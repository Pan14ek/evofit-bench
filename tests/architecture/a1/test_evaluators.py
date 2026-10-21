"""Adversarial source fixtures for the proposed A1 architecture evaluators."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import yaml

from architecture.acceptance.a1.analyzers import ANALYZERS
from architecture.acceptance.a1.engine import run_evaluator, verify_evidence

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
            _write(
                package / "public.py",
                f'def {capability}_port() -> None:\n    """Public contract fixture."""\n',
            )
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
    assert evidence["diagnostics"]["cross_capability_imports"] == []


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
    intermediate_root, intermediate_sha = _fixture_repo(
        tmp_path / "intermediate", source, state="A0_2_PUBLIC_MODULE_APIS"
    )
    intermediate, _ = _run(
        intermediate_root, intermediate_sha, "AC_PUBLIC_API", state="A0_2_PUBLIC_MODULE_APIS"
    )
    assert intermediate["result"]["compliance"] == "COMPLIANT"
    assert (
        intermediate["diagnostics"]["cross_capability_imports"][0]["classification"]
        == "legacy_exception"
    )
    final_root, final_sha = _fixture_repo(tmp_path / "final", source, state=FINAL_STATE)
    final, _ = _run(final_root, final_sha, "AC_PUBLIC_API", state=FINAL_STATE)
    assert any(
        item["classification"] == "private_or_undeclared_contract"
        for item in final["diagnostics"]["cross_capability_imports"]
    )
    assert final["result"]["compliance"] == "NON_COMPLIANT"


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


def test_evaluator_runs_against_current_a01_sources_only_as_not_applicable() -> None:
    base_sha = _git(ROOT, "rev-parse", "HEAD", capture_output=True).stdout.strip()
    manifest = ROOT / "architecture/states/A0_1_CAPABILITY_MODULES.yaml"
    outputs = {}
    for evaluator_id, config_name in (
        ("AC_PUBLIC_API", "public_api_v1.yaml"),
        ("AC_MODULE_GRAPH", "module_graph_v1.yaml"),
        ("AC_DATA_OWNERSHIP", "data_ownership_v1.yaml"),
    ):
        evidence = run_evaluator(
            evaluator_id,
            ROOT,
            EVALUATOR_ROOT / config_name,
            manifest,
            "A0_1_CAPABILITY_MODULES",
            base_sha,
            ANALYZERS[evaluator_id],
        )
        assert evidence["result"]["execution_status"] == "COMPLETED"
        assert evidence["result"]["compliance"] == "NOT_APPLICABLE"
        assert evidence["source_scope"]["complete"] is True
        assert evidence["architecture"]["target_source_sha"] == base_sha
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
        for item in outputs["AC_DATA_OWNERSHIP"]["diagnostics"]["observed_policy_findings"]
    )
    assert ownership["model_registry_exception"]["observed_allowed_imports"]
