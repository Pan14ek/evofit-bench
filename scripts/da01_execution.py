"""Preparation-only CLI for the DA01 experimental execution infrastructure."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, cast

from experiments.execution.tooling.contracts import validate_prediction
from experiments.execution.tooling.inputs import (
    MethodId,
    export_method_inputs,
    verify_method_bundle,
)
from experiments.execution.tooling.sealing import load_verified_prediction, seal_prediction
from experiments.execution.tooling.validity import inspect_import_linter_scope

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("da01_execution")


def main() -> None:
    """Run a preparation command; no command starts measured B0/B1/P execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    export_parser = commands.add_parser("export-inputs", help="create an allowlisted method bundle")
    export_parser.add_argument("--method", choices=("B0", "B1", "P"), required=True)
    export_parser.add_argument("--before-sha", required=True)
    export_parser.add_argument("--architecture-sha", required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    export_parser.add_argument("--repository", type=Path, default=ROOT)

    verify_parser = commands.add_parser(
        "verify-bundle", help="verify manifest, hashes, and allowlist"
    )
    verify_parser.add_argument("--bundle", type=Path, required=True)
    verify_parser.add_argument("--method", choices=("B0", "B1", "P"))

    seal_parser = commands.add_parser(
        "seal-prediction", help="write a deterministic prediction once"
    )
    seal_parser.add_argument("--prediction", type=Path, required=True)
    seal_parser.add_argument("--output-directory", type=Path, required=True)

    verify_seal_parser = commands.add_parser(
        "verify-seal", help="verify immutable prediction bytes"
    )
    verify_seal_parser.add_argument("--output-directory", type=Path, required=True)

    scope_parser = commands.add_parser(
        "inspect-importlinter-scope",
        help="assess frozen Import Linter selectors against an architecture source tree",
    )
    scope_parser.add_argument("--configuration", type=Path, required=True)
    scope_parser.add_argument("--source-root", type=Path, required=True)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    result: dict[str, Any]
    if args.command == "export-inputs":
        result = export_method_inputs(
            args.repository,
            args.output,
            cast(MethodId, args.method),
            args.before_sha,
            args.architecture_sha,
        )
        LOGGER.info(
            "method_input_bundle_created method_id=%s bundle_sha256=%s file_count=%d",
            result["method_id"],
            result["bundle_sha256"],
            len(result["files"]),
        )
    elif args.command == "verify-bundle":
        result = verify_method_bundle(args.bundle, cast(MethodId | None, args.method))
        LOGGER.info("method_input_bundle_verified method_id=%s", result["method_id"])
    elif args.command == "seal-prediction":
        payload = cast(dict[str, Any], json.loads(args.prediction.read_text(encoding="utf-8")))
        validate_prediction(payload)
        sealed = seal_prediction(payload, args.output_directory)
        result = {
            "path": str(sealed.path),
            "sha256": sealed.sha256,
            "sealed_at_utc": sealed.sealed_at_utc,
        }
        LOGGER.info("prediction_sealed method_id=%s sha256=%s", payload["method_id"], sealed.sha256)
    elif args.command == "verify-seal":
        sealed = load_verified_prediction(args.output_directory)
        result = {"path": str(sealed.path), "sha256": sealed.sha256, "verified": True}
        LOGGER.info("prediction_seal_verified sha256=%s", sealed.sha256)
    else:
        source_root = args.source_root.resolve(strict=True)
        modules = {
            _module_name(path, source_root)
            for path in source_root.rglob("*.py")
            if path.is_file() and not path.is_symlink()
        }
        result = inspect_import_linter_scope(args.configuration.read_bytes(), modules)
        LOGGER.info(
            "evaluator_scope_inspected missing_target_count=%d inspected_module_count=%d",
            len(result["missing_targets"]),
            result["inspected_module_count"],
        )
    print(json.dumps(result, indent=2, sort_keys=True))


def _module_name(path: Path, source_root: Path) -> str:
    relative = path.relative_to(source_root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


if __name__ == "__main__":
    main()
