"""Check that every Git-tracked source directory has local agent context."""

from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_context_files_cover_all_tracked_directories_except_docs() -> None:
    """Documentation instructions must be present along the tracked source tree."""
    git_root = ROOT / ".git"
    if not git_root.exists():
        pytest.skip("Git metadata unavailable; cannot audit tracked-directory coverage")

    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    paths = {
        path.decode("utf-8")
        for path in result.stdout.split(b"\x00")
        if path
    }
    expected = {"CONTEXT.md"}
    for name in paths:
        for parent in Path(name).parents:
            directory = parent.as_posix()
            if directory == ".":
                continue
            if directory == "docs" or directory.startswith("docs/"):
                continue
            expected.add(f"{directory}/CONTEXT.md")
    missing = sorted(expected - paths)
    assert not missing, f"Missing local agent contexts: {missing}"
