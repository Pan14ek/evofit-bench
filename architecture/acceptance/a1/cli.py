"""CLI for independently running one A1 architecture evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from architecture.acceptance.a1.analyzers import ANALYZERS
from architecture.acceptance.a1.engine import run_evaluator

CONFIGS = {
    "AC_PUBLIC_API": "public_api_v1.yaml",
    "AC_MODULE_GRAPH": "module_graph_v1.yaml",
    "AC_DATA_OWNERSHIP": "data_ownership_v1.yaml",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a source-grounded A1 architecture fitness evaluator."
    )
    parser.add_argument("evaluator", choices=sorted(CONFIGS))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--evidence-root",
        type=Path,
        help="separate root for portable external evidence manifests",
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--state-manifest", type=Path, required=True)
    parser.add_argument("--architecture-state", required=True)
    parser.add_argument("--expected-source-sha")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    config_path = (args.config or Path(__file__).with_name(CONFIGS[args.evaluator])).resolve()
    manifest_path = args.state_manifest
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    evidence = run_evaluator(
        args.evaluator,
        repo_root,
        config_path,
        manifest_path,
        args.architecture_state,
        args.expected_source_sha,
        ANALYZERS[args.evaluator],
        evidence_root=args.evidence_root.resolve() if args.evidence_root else None,
    )
    payload = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if args.output:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    result = evidence["result"]
    if result["execution_status"] == "FAILED" or result["compliance"] in {
        "NOT_EVALUABLE",
        "UNKNOWN",
    }:
        return 2
    if result["compliance"] == "NON_COMPLIANT":
        return 1
    if result["compliance"] == "NOT_APPLICABLE":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
