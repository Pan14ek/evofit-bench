"""Finalize a narrowly recognized post-arm B0/P aggregation failure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.execution.tooling.b0p_execution import (
    create_evidence_archive,
    finalize_post_execution_failure,
)

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    """Persist an execution manifest from existing arm outputs without rerunning methods."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--uv", required=True)
    parser.add_argument("--attempt-id", default="a01")
    args = parser.parse_args(argv)

    manifest: dict[str, Any] = finalize_post_execution_failure(
        args.run_directory,
        repository=args.repository,
        docker_executable=args.docker,
        uv_executable=args.uv,
        attempt_id=args.attempt_id,
    )
    archive, archive_sha256 = create_evidence_archive(args.run_directory)
    print(
        json.dumps(
            {
                "execution_manifest": manifest,
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
