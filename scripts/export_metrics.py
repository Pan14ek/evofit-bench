"""Export the application's current Prometheus snapshot to a run directory."""

import argparse
import json
from pathlib import Path

import httpx


def export(base_url: str, run_id: str) -> Path:
    """Fetch /metrics and save parsed sample names and values."""
    target = Path("experiments/results") / run_id / "metrics.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    response = httpx.get(f"{base_url.rstrip('/')}/metrics", timeout=10)
    response.raise_for_status()
    text = response.text
    samples = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        name, _, value = line.partition(" ")
        samples.append({"sample": name, "value": float(value)})
    target.write_text(json.dumps({"metrics": samples}, indent=2) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(export(args.url, args.run_id))
