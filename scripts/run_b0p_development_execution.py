"""Continue a verified B0/P preparation package with one isolated DEVELOPMENT run."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from experiments.execution.tooling.b0p_execution import (
    create_evidence_archive,
    perform_development_execution,
)

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    """Execute both arms, collect fresh evaluator outputs and write a run manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation-directory", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--uv", default=shutil.which("uv") or "uv")
    args = parser.parse_args(argv)

    result: dict[str, Any] = perform_development_execution(
        args.preparation_directory,
        run_id=args.run_id,
        repository=args.repository,
        docker_executable=args.docker,
        uv_executable=args.uv,
    )
    archive, archive_sha256 = create_evidence_archive(
        args.repository / "experiments/results" / args.run_id
    )
    print(
        json.dumps(
            {
                "execution_manifest": result,
                "archive_path": str(archive),
                "archive_sha256": archive_sha256,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
