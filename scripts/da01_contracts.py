"""Capture and compare deterministic structural contracts for DA01."""

import argparse
import hashlib
import importlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import DefaultClause

from app.models.base import Base
from scripts.seed_fingerprint import fingerprint

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "experiments/scenarios/DA01/contracts"
WORKLOAD_FILES = (
    "load/profiles/a0-smoke-v1.yaml",
    "load/profiles/a0-baseline-v1.yaml",
    "load/profiles/a0-warmup-v1.yaml",
)
METRIC_SYMBOLS = (
    "http_request_duration_seconds",
    "http_requests_total",
    "http_responses_total",
    "users_created_total",
    "tasks_created_total",
    "tasks_assigned_total",
    "task_status_changes_total",
    "notifications_created_total",
    "business_operation_failures_total",
    "business_rule_rejections_total",
)
CONTRACT_FILES = (
    "openapi.normalized.json",
    "sqlalchemy-schema.json",
    "seed-fingerprint.json",
    "workload-hashes.json",
    "metrics-contract.json",
    "alembic-state.json",
)


def _write_json(path: Path, value: Any) -> None:
    """Write stable, human-readable JSON with a final newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_sort_key(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load_model_registry() -> None:
    """Ensure every mapped model is registered on the shared declarative Base."""
    registry_path = ROOT / "app/db/model_registry.py"
    if registry_path.exists():
        importlib.import_module("app.db.model_registry")
    else:
        importlib.import_module("app.models")


def _column_default(default: DefaultClause | Any | None) -> Any:
    if default is None:
        return None
    value = getattr(default, "arg", None)
    if callable(value):
        return {
            "kind": "callable",
            "name": f"{value.__module__}.{value.__qualname__}",
        }
    sql_text = getattr(value, "text", None)
    if sql_text is not None:
        return {"kind": "sql", "value": str(sql_text)}
    if value is None or isinstance(value, (bool, float, int, str)):
        return {"kind": "scalar", "value": value}
    return {"kind": "value", "value": str(value)}


def sqlalchemy_schema_contract() -> dict[str, Any]:
    """Describe mapped tables, columns, constraints, indexes, and enum values."""
    _load_model_registry()
    dialect_factory = cast(Callable[[], Any], postgresql.dialect)
    dialect = dialect_factory()
    tables: list[dict[str, Any]] = []
    for table_name, table in sorted(Base.metadata.tables.items()):
        columns: list[dict[str, Any]] = []
        for column in table.columns:
            column_type: dict[str, Any] = {
                "name": type(column.type).__name__,
                "postgresql": column.type.compile(dialect=dialect),
            }
            enum_values = getattr(column.type, "enums", None)
            if enum_values is not None:
                column_type["enum_values"] = list(enum_values)
                column_type["enum_name"] = getattr(column.type, "name", None)
                column_type["native_enum"] = getattr(column.type, "native_enum", None)
            columns.append(
                {
                    "name": column.name,
                    "type": column_type,
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "autoincrement": column.autoincrement,
                    "default": _column_default(column.default),
                    "server_default": _column_default(column.server_default),
                }
            )

        constraints: list[dict[str, Any]] = []
        for constraint in table.constraints:
            constraint_columns: Any = getattr(constraint, "columns", ())
            description: dict[str, Any] = {
                "kind": type(constraint).__name__,
                "name": constraint.name,
                "columns": [column.name for column in constraint_columns],
            }
            if isinstance(constraint, CheckConstraint):
                description["sql"] = str(constraint.sqltext)
            if isinstance(constraint, ForeignKeyConstraint):
                description["elements"] = [
                    {
                        "column": element.parent.name,
                        "target": element.target_fullname,
                        "ondelete": element.ondelete,
                        "onupdate": element.onupdate,
                    }
                    for element in constraint.elements
                ]
                description["deferrable"] = constraint.deferrable
                description["initially"] = constraint.initially
            constraints.append(description)

        indexes = [
            {
                "name": index.name,
                "unique": index.unique,
                "columns": [
                    getattr(expression, "name", str(expression)) for expression in index.expressions
                ],
            }
            for index in table.indexes
        ]
        tables.append(
            {
                "name": table_name,
                "columns": columns,
                "constraints": sorted(constraints, key=_json_sort_key),
                "indexes": sorted(indexes, key=_json_sort_key),
            }
        )
    return {"contract_version": 1, "tables": tables}


def metrics_contract() -> dict[str, Any]:
    """Capture metric identities, types, help text, and label names."""
    from app.observability import metrics

    result: list[dict[str, Any]] = []
    for symbol in METRIC_SYMBOLS:
        metric = getattr(metrics, symbol)
        families = metric.collect()
        family = families[0]
        result.append(
            {
                "symbol": symbol,
                "family_name": family.name,
                "type": family.type,
                "help": family.documentation,
                "label_names": sorted(getattr(metric, "_labelnames", ())),
                "exposed_names": sorted({sample.name for sample in family.samples}),
            }
        )
    return {"contract_version": 1, "metrics": result}


def workload_contract() -> dict[str, Any]:
    return {
        "contract_version": 1,
        "sha256": {
            relative_path: hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            for relative_path in WORKLOAD_FILES
        },
    }


def alembic_contract() -> dict[str, Any]:
    config = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    revision_files = sorted((ROOT / "alembic/versions").glob("*.py"))
    return {
        "contract_version": 1,
        "head_revisions": sorted(script.get_heads()),
        "revision_files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in revision_files
        ],
    }


def capture(label: str, output_dir: Path) -> None:
    from app.main import app

    payloads: dict[str, Any] = {
        "openapi.normalized.json": app.openapi(),
        "sqlalchemy-schema.json": sqlalchemy_schema_contract(),
        "seed-fingerprint.json": fingerprint(),
        "workload-hashes.json": workload_contract(),
        "metrics-contract.json": metrics_contract(),
        "alembic-state.json": alembic_contract(),
    }
    for suffix, payload in payloads.items():
        path = output_dir / f"{label}-{suffix}"
        _write_json(path, payload)
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def compare(output_dir: Path) -> int:
    failed = False
    for suffix in CONTRACT_FILES:
        before_path = output_dir / f"a0-{suffix}"
        after_path = output_dir / f"da01-{suffix}"
        before = json.loads(before_path.read_text(encoding="utf-8"))
        after = json.loads(after_path.read_text(encoding="utf-8"))
        status = "PASS" if before == after else "FAIL"
        print(f"{suffix}: {status}")
        failed = failed or status == "FAIL"
    return int(failed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--capture", choices=("a0", "da01"))
    action.add_argument("--compare", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=CONTRACT_DIR)
    args = parser.parse_args()
    if args.compare:
        raise SystemExit(compare(args.output_dir))
    capture(args.capture, args.output_dir)


if __name__ == "__main__":
    main()
