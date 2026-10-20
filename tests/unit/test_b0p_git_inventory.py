"""Source-inventory verification against synthetic committed architecture revisions."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.verify_b0p_git_inventory import (
    SourceInventoryError,
    actual_inventory,
    assess_observations,
    committed_modules,
)


def _git(repository: Path, *args: str) -> str:
    executable = shutil.which("git")
    assert executable is not None
    result = subprocess.run(  # noqa: S603 - controlled synthetic test repository
        [executable, "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _commit(repository: Path, label: str) -> str:
    _git(repository, "add", "-A")
    _git(repository, "commit", "-m", label)
    return _git(repository, "rev-parse", "HEAD")


def _write(repository: Path, path: str, data: str) -> None:
    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data, encoding="utf-8")


@pytest.fixture
def revision_pair(tmp_path: Path) -> tuple[Path, str, str]:
    repository = tmp_path / "source"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Fixture")
    _git(repository, "config", "user.email", "fixture@example.invalid")

    _write(repository, "app/__init__.py", "")
    _write(repository, "app/api.py", "def api(): pass\n")
    _write(repository, "app/services/service.py", "def run(): pass\n")
    first = _commit(repository, "before")

    (repository / "app/api.py").unlink()
    _write(repository, "app/modules/__init__.py", "")
    _write(repository, "app/modules/tasks/service.py", "def run(): pass\n")
    second = _commit(repository, "after")
    return repository, first, second


def test_pinned_git_inventory_recomputes_all_four_fields(
    revision_pair: tuple[Path, str, str],
) -> None:
    repository, before, after = revision_pair
    expected = actual_inventory(repository, before, after)
    assert expected["before_module_names"] == [
        "app",
        "app.api",
        "app.services.service",
    ]
    assert expected["after_module_names"] == [
        "app",
        "app.modules",
        "app.modules.tasks.service",
        "app.services.service",
    ]
    assert expected["added_module_names"] == ["app.modules", "app.modules.tasks.service"]
    assert expected["removed_module_names"] == ["app.api"]
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
    result = assess_observations(repository, before, after, expected, digest)
    assert result["source_fact_verified"] is True
    assert result["assessment"] == "VERIFIED_GIT_INVENTORY"
    assert result["policy_authority_verified"] is False
    assert result["semantic_pair_verified"] is False


@pytest.mark.parametrize("field", [
    "before_module_names",
    "after_module_names",
    "added_module_names",
    "removed_module_names",
])
def test_a_tampered_observation_is_not_admitted(
    revision_pair: tuple[Path, str, str], field: str,
) -> None:
    repository, before, after = revision_pair
    observations = actual_inventory(repository, before, after)
    observations[field] = ["app.invented"]
    digest = hashlib.sha256(json.dumps(observations).encode()).hexdigest()
    result = assess_observations(repository, before, after, observations, digest)
    assert result["source_fact_verified"] is False
    assert result["field_results"][field]["matches"] is False


def test_cannot_substitute_branch_name_for_pinned_revision(
    revision_pair: tuple[Path, str, str],
) -> None:
    repository, _, _ = revision_pair
    with pytest.raises(SourceInventoryError, match="complete lowercase"):
        committed_modules(repository, "HEAD")


def test_observations_must_be_canonical_unique_sorted(
    revision_pair: tuple[Path, str, str],
) -> None:
    repository, before, after = revision_pair
    observations = actual_inventory(repository, before, after)
    observations["added_module_names"] = list(reversed(observations["added_module_names"]))
    result = assess_observations(repository, before, after, observations, "a" * 64)
    assert result["assessment"] == "MISMATCH"


def test_symlink_in_git_source_fails_closed(
    revision_pair: tuple[Path, str, str],
) -> None:
    repository, _, _ = revision_pair
    link = repository / "app" / "external.py"
    link.symlink_to(repository.parent / "outside.py"
    commit = _commit(repository, "symlink")
    with pytest.raises(SourceInventoryError, match="symlink"):
        committed_modules(repository, commit)


def test_mutating_the_worktree_does_not_change_pinned_git_fact(
    revision_pair: tuple[Path, str, str],
) -> None:
    repository, before, after = revision_pair
    original = actual_inventory(repository, before, after)
    _write(repository, "app/uncommitted_extra.py", "pass\n")
    assert actual_inventory(repository, before, after) == original


def test_invalid_observation_digest_is_rejected(
    revision_pair: tuple[Path, str, str],
) -> None:
    repository, before, after = revision_pair
    with pytest.raises(SourceInventoryError, match="SHA-256"):
        assess_observations(repository, before, after, {}, "bad")
