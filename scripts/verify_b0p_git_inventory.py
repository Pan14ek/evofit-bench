"""Independently recompute Python-module inventory facts from pinned Git trees.

This checks only structural source facts. It does not establish policy authority,
semantic pair validity, accepted adaptation, or scientific superiority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess  # nosec B404 - local pinned Git object inspection, no shell
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

_SHA40 = re.compile(r"[0-9a-f]{40}", re.ASCII)
_FIELDS = (
    "before_module_names",
    "after_module_names",
    "added_module_names",
    "removed_module_names",
)


class SourceInventoryError(ValueError):
    """A source or reported inventory cannot be verified."""


def _git(repository: Path, *args: str) -> bytes:
    executable = shutil.which("git")
    if executable is None:
        raise SourceInventoryError("Git executable is required")
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603 - fixed Git executable and argv only
            [executable, "-C", str(repository), *args],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as error:
        raise SourceInventoryError("Cannot read pinned Git source object") from error
    return result.stdout


def committed_modules(repository: Path, commit_sha: str) -> list[str]:
    """Inspect Git objects, not the checkout or P's exported inventory."""
    if _SHA40.fullmatch(commit_sha) is None:
        raise SourceInventoryError("A complete lowercase 40-hex commit SHA is required")
    if _git(repository, "cat-file", "-t", commit_sha).strip() != b"commit":
        raise SourceInventoryError("Pinned source object must be a Git commit")

    entries = _git(repository, "ls-tree", "-r", "-z", commit_sha, "--", "app")
    modules: set[str] = set()
    saw_python = False
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        try:
            descriptor, raw_path = entry.split(b"\t", 1)
            mode, object_type, _object_sha = descriptor.split(b" ", 2)
            relative_name = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise SourceInventoryError("Malformed Git tree entry") from error

        if mode == b"120000":
            raise SourceInventoryError("Git source tree includes a symlink")
        if object_type != b"blob" or mode not in (b"100644", b"100755"):
            raise SourceInventoryError("Unexpected non-file Git tree entry")
        path = PurePosixPath(relative_name)
        if (
            path.is_absolute()
            or not path.parts
            or path.parts[0] != "app"
            or ".." in path.parts
            or "." in path.parts
        ):
            raise SourceInventoryError("Unsafe source inventory path")
        if path.suffix != ".py":
            continue
        saw_python = True
        parts = list(path.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        name = ".".join(parts)
        if name in modules:
            raise SourceInventoryError("Duplicate Python module identity in Git tree")
        modules.add(name)

    if not saw_python or not modules:
        raise SourceInventoryError("Pinned source has no Python application modules")
    return sorted(modules)


def actual_inventory(repository: Path, before_sha: str, after_sha: str) -> dict[str, list[str]]:
    """Derive the four module-inventory facts from two independent Git trees."""
    before = committed_modules(repository, before_sha)
    after = committed_modules(repository, after_sha)
    return {
        "before_module_names": before,
        "after_module_names": after,
        "added_module_names": sorted(set(after) - set(before)),
        "removed_module_names": sorted(set(before) - set(after)),
    }


def assess_observations(
    repository: Path,
    before_sha: str,
    after_sha: str,
    observations: Mapping[str, Any],
    observations_sha256: str,
) -> dict[str, Any]:
    """Compare exported observations to Git facts without calling Method P."""
    if not re.fullmatch(r"[0-9a-f]{64}", observations_sha256):
        raise SourceInventoryError("Observation file requires a real SHA-256")
    expected = actual_inventory(repository, before_sha, after_sha)
    field_results: dict[str, Any] = {}
    for key in _FIELDS:
        reported = observations.get(key)
        structurally_valid = (
            isinstance(reported, list)
            and all(isinstance(value, str) and value for value in reported)
            and reported == sorted(set(reported))
        )
        matches = structurally_valid and reported == expected[key]
        field_results[key] = {
            "matches": matches,
            "expected": expected[key],
            "reported": reported,
        }

    valid = all(field["matches"] for field in field_results.values())
    return {
        "schema_version": 1,
        "assessment": "VERIFIED_GIT_INVENTORY" if valid else "MISMATCH",
        "verification_scope": "PINNED_GIT_PYTHON_MODULE_INVENTORY_ONLY",
        "before_sha": before_sha,
        "after_sha": after_sha,
        "observations_sha256": observations_sha256,
        "field_results": field_results,
        "source_fact_verified": valid,
        "policy_authority_verified": False,
        "completeness_outside_module_inventory_verified": False,
        "semantic_pair_verified": False,
        "governance_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--before-sha", required=True)
    parser.add_argument("--after-sha", required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        parser.error("Evidence outputs are write-once; output already exists")
    raw = args.observations.read_bytes()
    try:
        observations = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SourceInventoryError("Observations must be JSON") from error
    if not isinstance(observations, dict):
        raise SourceInventoryError("Observations must be a JSON object")

    report = assess_observations(
        args.repository,
        args.before_sha,
        args.after_sha,
        observations,
        hashlib.sha256(raw).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return 0 if report["source_fact_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
