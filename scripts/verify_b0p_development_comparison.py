"""Independently read back a prepared B0/P DEVELOPMENT comparison package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.execution.tooling.b0p_development import verify_study_manifest

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    """Verify source pins, bundles, source facts and every declared run artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    result: dict[str, Any] = verify_study_manifest(args.run_directory, args.repository)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
