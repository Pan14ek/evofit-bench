"""Prepare a pinned B0/P DEVELOPMENT comparison without opening the oracle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.execution.tooling.b0p_development import prepare_development_study

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    """Export write-once B0/P method inputs and independently verified source facts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--before-sha", required=True)
    parser.add_argument("--after-sha", required=True)
    parser.add_argument("--b0-source-sha", required=True)
    parser.add_argument("--p-source-sha", required=True)
    parser.add_argument("--policy-source-sha", required=True)
    parser.add_argument(
        "--exposure-class",
        choices=("CALIBRATION_EXPOSED", "PROSPECTIVE_HELD_OUT"),
        default="CALIBRATION_EXPOSED",
    )
    parser.add_argument("--repository", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    result: dict[str, Any] = prepare_development_study(
        args.repository,
        run_id=args.run_id,
        architecture_before_sha=args.before_sha,
        architecture_after_sha=args.after_sha,
        b0_source_sha=args.b0_source_sha,
        p_source_sha=args.p_source_sha,
        policy_source_sha=args.policy_source_sha,
        exposure_class=args.exposure_class,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
