"""A0.5 ownership policy and evaluator discrimination checks."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import jsonschema  # type: ignore[import-untyped]
import yaml

from architecture.acceptance.a1.analyzers import ANALYZERS
from architecture.acceptance.a1.engine import inspect_source_scope
from scripts.check_architecture_stages import A05, A05_MANIFEST, A05_SCHEMA

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EVALUATOR_ROOT = REPOSITORY_ROOT / "architecture/acceptance/a1"


def _config(evaluator_id: str) -> dict[str, Any]:
    filename = {
        "AC_PUBLIC_API": "public_api_v1.yaml",
        "AC_MODULE_GRAPH": "module_graph_v1.yaml",
        "AC_DATA_OWNERSHIP": "data_ownership_v1.yaml",
    }[evaluator_id]
    return cast(
        dict[str, Any],
        yaml.safe_load((EVALUATOR_ROOT / filename).read_text(encoding="utf-8")),
    )


def _analyze(
    root: Path, evaluator_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    config = _config(evaluator_id)
    inventory = inspect_source_scope(root, config)
    assert inventory.complete
    return ANALYZERS[evaluator_id](config, inventory, A05)


def _copy_application(destination: Path) -> None:
    shutil.copytree(REPOSITORY_ROOT / "app", destination / "app")


def test_a05_manifest_declares_source_owned_persistence_and_preserves_a04() -> None:
    manifest = yaml.safe_load((REPOSITORY_ROOT / A05_MANIFEST).read_text(encoding="utf-8"))
    schema = json.loads((REPOSITORY_ROOT / A05_SCHEMA).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(manifest)
    assert manifest["predecessor_state"] == "A0_4_REPORT_QUERY_PORT"
    assert manifest["source_provenance"]["predecessor_commit"] == (
        "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
    )
    assert manifest["persistence_ownership"]["table_owners"] == {
        "users": "users",
        "tasks": "tasks",
        "notifications": "notifications",
        "audit_events": "audit",
    }
    assert (
        manifest["persistence_ownership"]["shared_infrastructure"]["model_registry_exception"][
            "path"
        ]
        == "app/db/model_registry.py"
    )
    assert manifest["governance_requirements"]["required_evaluators"] == [
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
        "AC_DATA_OWNERSHIP",
    ]


def test_compliant_a05_source_passes_all_controls_and_registry_exception() -> None:
    results = {
        evaluator_id: _analyze(REPOSITORY_ROOT, evaluator_id)
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP")
    }
    for _summary, findings, errors in results.values():
        assert findings == []
        assert errors == []
    summary = results["AC_DATA_OWNERSHIP"][0]
    assert summary["model_registry_exception"]["observed_allowed_imports"]


def test_tasks_table_access_probe_is_invisible_to_old_controls_but_caught_by_ownership(
    tmp_path: Path,
) -> None:
    source = tmp_path / "compliant"
    source.mkdir()
    _copy_application(source)
    compliant = {
        evaluator_id: _analyze(source, evaluator_id)
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP")
    }

    probe = tmp_path / "probe"
    probe.mkdir()
    _copy_application(probe)
    repository_file = probe / "app/modules/tasks/repository.py"
    repository_file.write_text(
        repository_file.read_text(encoding="utf-8")
        + "\nfrom sqlalchemy import MetaData, Table, select\n"
        + '_foreign_notifications = Table("notifications", MetaData(), autoload_with=None)\n'
        + "select(_foreign_notifications)\n",
        encoding="utf-8",
    )
    probed = {
        evaluator_id: _analyze(probe, evaluator_id)
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP")
    }

    for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH"):
        assert probed[evaluator_id] == compliant[evaluator_id]
    findings = probed["AC_DATA_OWNERSHIP"][1]
    assert any(finding["code"] == "FOREIGN_TABLE_ACCESS" for finding in findings)
