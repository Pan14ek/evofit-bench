"""Independently verify a B0/P DEVELOPMENT execution package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.execution.tooling.b0p_execution import verify_development_execution

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    """Check sealed predictions, exact input bindings, and complete artifact hashes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=None)
    args = parser.parse_args(argv)
    result: dict[str, Any] = verify_development_execution(
        args.run_directory,
        repository=args.repository or ROOT,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
