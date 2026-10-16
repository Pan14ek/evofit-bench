"""Check that every Git-tracked source directory has local agent context."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STRICT_POLICY_SOURCE = "experiments/execution/policy-pilot/v1/source"


def test_context_files_cover_all_tracked_directories_except_docs() -> None:
    """Documentation instructions must be present along the tracked source tree."""
    git_root = ROOT / ".git"
    if not git_root.exists():
        pytest.skip("Git metadata unavailable; cannot audit tracked-directory coverage")

    # Fixed, argument-vector command; never takes untrusted shell input.
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(ROOT), "ls-files", "-z"],  # noqa: S607
        capture_output=True,
        check=True,
    )
    paths = {path.decode("utf-8") for path in result.stdout.split(b"\x00") if path}
    expected = {"CONTEXT.md"}
    for name in paths:
        for parent in Path(name).parents:
            directory = parent.as_posix()
            if directory == ".":
                continue
            if directory == "docs" or directory.startswith("docs/"):
                continue
            if directory == STRICT_POLICY_SOURCE:
                continue
            if directory.startswith(f"{STRICT_POLICY_SOURCE}/"):
                continue
            expected.add(f"{directory}/CONTEXT.md")
    missing = sorted(expected - paths)
    assert not missing, f"Missing local agent contexts: {missing}"
