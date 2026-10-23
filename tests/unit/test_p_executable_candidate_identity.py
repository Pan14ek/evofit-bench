"""Byte-level identity checks for the review-only Method P candidate."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from itertools import chain
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_PATH = Path("experiments/execution/P_EXECUTABLE_CANDIDATE_V1.json")
SCHEMA_PATH = Path("experiments/execution/schemas/p_executable_candidate_identity_v1.schema.json")
GIT_EXECUTABLE = shutil.which("git")


def _canonical_digest(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _identity_digest(payload: dict[str, Any]) -> str:
    content = {key: value for key, value in payload.items() if key != "identity_sha256"}
    return _canonical_digest(content)


def test_identity_manifest_matches_schema_and_pinned_git_bytes() -> None:
    manifest = json.loads((REPOSITORY_ROOT / IDENTITY_PATH).read_text(encoding="utf-8"))
    schema = json.loads((REPOSITORY_ROOT / SCHEMA_PATH).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)

    assert manifest["identity_sha256"] == _identity_digest(manifest)
    assert manifest["source_identity_sha256"] == _canonical_digest(
        {
            "source_revision": manifest["source_revision"],
            "implementation_files": manifest["implementation_files"],
        }
    )
    assert manifest["configuration_sha256"] == _canonical_digest(manifest["configuration_files"])
    revision = manifest["source_revision"]
    assert re.fullmatch(r"[a-f0-9]{40}", revision["commit"])

    groups = (
        manifest["implementation_files"],
        manifest["configuration_files"],
        manifest["review_basis_files"],
    )
    all_paths: list[str] = []
    entries = list(chain.from_iterable(groups))
    for group in groups:
        paths = [entry["path"] for entry in group]
        assert paths == sorted(paths)
        assert len(paths) == len(set(paths))
        all_paths.extend(paths)

    assert len(all_paths) == len(set(all_paths))
    for entry in entries:
        path = PurePosixPath(entry["path"])
        assert not path.is_absolute()
        assert ".." not in path.parts
        assert not {".git", "oracle", "scorer", "ground_truth.yaml"}.intersection(
            part.lower() for part in path.parts
        )

    assert GIT_EXECUTABLE is not None
    # Git receives only a schema-checked full object ID and safe repository paths; shell=False.
    actual_tree = subprocess.run(  # noqa: S603
        [GIT_EXECUTABLE, "rev-parse", f"{revision['commit']}^{{tree}}"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert actual_tree == revision["tree"]

    for entry in entries:
        # Paths are repository-relative and traversal-free; shell=False prevents shell expansion.
        git_bytes = subprocess.run(  # noqa: S603
            [GIT_EXECUTABLE, "show", f"{revision['commit']}:{entry['path']}"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
        ).stdout
        checkout_bytes = (REPOSITORY_ROOT / entry["path"]).read_bytes()
        expected_sha256 = entry["sha256"]
        assert hashlib.sha256(git_bytes).hexdigest() == expected_sha256
        assert hashlib.sha256(checkout_bytes).hexdigest() == expected_sha256


def test_identity_manifest_digest_detects_tampering() -> None:
    manifest = json.loads((REPOSITORY_ROOT / IDENTITY_PATH).read_text(encoding="utf-8"))
    manifest["implementation_files"][0]["sha256"] = "0" * 64
    assert manifest["identity_sha256"] != _identity_digest(manifest)
