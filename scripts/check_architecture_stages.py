"""Stage-aware architecture checks without rewriting the frozen DA01 acceptance.

Historical A0.1 acceptance is executed from exactly pinned Git archive bytes,
never against the evolving application worktree. Current-source checks have
an explicitly limited stage scope; their PASS is not Method P or A1 approval.
"""

from __future__ import annotations

import argparse
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

HISTORICAL_A01_SHA = "3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306"
HISTORICAL_APP_TREE = "cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08"
MODULES = ("users", "tasks", "notifications", "reporting", "audit")
A01 = "A0_1_CAPABILITY_MODULES"
A02 = "A0_2_PUBLIC_MODULE_APIS"
ALLOWED_STAGES = ("auto", A01, A02)


class StageCheckError(RuntimeError):
    """Fail-closed architecture-stage/checkpoint error."""


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise StageCheckError(
            f"Git {arguments[0]} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def detect_stage(root: Path) -> str:
    """Infer only the two supported *development* stages; refuse partial APIs."""
    modules = root / "app" / "modules"
    missing_modules = [name for name in MODULES if not (modules / name / "__init__.py").is_file()]
    if missing_modules:
        raise StageCheckError(f"Missing capability modules: {missing_modules}")
    present = [name for name in MODULES if (modules / name / "public.py").is_file()]
    if not present:
        return A01
    if len(present) != len(MODULES):
        raise StageCheckError(f"Partial public API modules: {present}; expected all {MODULES}")
    contract_test = root / "tests/unit/test_module_public_apis.py"
    if not contract_test.is_file():
        raise StageCheckError(f"New public interfaces lack mandatory contract tests: {contract_test}")
    return A02


def verify_historical_pin(root: Path) -> None:
    """Require exactly the published A0.1 commit and application tree."""
    if _git(root, "rev-parse", f"{HISTORICAL_A01_SHA}^{{commit}}") != HISTORICAL_A01_SHA:
        raise StageCheckError("Historical A0.1 Git commit is absent or incorrect")
    actual_tree = _git(root, "rev-parse", f"{HISTORICAL_A01_SHA}:app")
    if actual_tree != HISTORICAL_APP_TREE:
        raise StageCheckError(
            f"Historical A0.1 app tree changed: {actual_tree}, expected {HISTORICAL_APP_TREE}"
        )
    for path in (
        "tests/architecture/test_module_structure.py",
        "tests/architecture/test_layer_rules.py",
        "architecture/states/A0_1_CAPABILITY_MODULES.yaml",
    ):
        _git(root, "cat-file", "-e", f"{HISTORICAL_A01_SHA}:{path}")


def _run_pytest(root: Path, testpaths: list[str], *, historical: bool) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if historical:
        # Do not import any current-worktree Python modules while testing pinned history.
        env["PYTHONPATH"] = str(root)
    command = [
        sys.executable, "-m", "pytest", "-q", "--no-cov", "-p", "no:cacheprovider",
        *testpaths,
    ]
    print(f"[stage-ci] pytest cwd={root} targets={testpaths}", flush=True)
    result = subprocess.run(command, cwd=root, env=env, check=False)
    if result.returncode:
        raise StageCheckError(f"Architecture pytest failed ({result.returncode}) for {testpaths}")


def historical_a01_acceptance(repo: Path) -> None:
    """Execute the original test code and its original source, not today's files."""
    verify_historical_pin(repo)
    print(
        f"[stage-ci] HISTORICAL_A01 source={HISTORICAL_A01_SHA} "
        f"app_tree={HISTORICAL_APP_TREE}",
        flush=True,
    )
    process = subprocess.run(
        [
            "git", "-C", str(repo), "archive", "--format=tar", HISTORICAL_A01_SHA,
            "app", "architecture/states/A0_1_CAPABILITY_MODULES.yaml",
            "tests/architecture", "pyproject.toml",
        ],
        capture_output=True,
        check=False,
    )
    if process.returncode:
        raise StageCheckError(f"Could not materialize pinned archive: {process.stderr!r}")
    with tempfile.TemporaryDirectory(prefix="evofit-pinned-a01-") as temporary:
        checkout = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(process.stdout), mode="r:") as archive:
            # Python 3.12 data filter rejects archive traversal and unsafe links.
            archive.extractall(checkout, filter="data")
        _run_pytest(
            checkout,
            ["tests/architecture/test_module_structure.py", "tests/architecture/test_layer_rules.py"],
            historical=True,
        )
    print("[stage-ci] HISTORICAL_A01 PASS (6 exact historical tests)", flush=True)


def current_stage_acceptance(repo: Path, *, requested_stage: str) -> str:
    """Validate actual checkout with only stage-relevant tests, no historical drift."""
    current = detect_stage(repo)
    if requested_stage != "auto" and requested_stage != current:
        raise StageCheckError(
            f"Requested architecture stage {requested_stage} != observed {current}"
        )
    # Git checkout must be provenance-bound for a gate result.
    changed = _git(repo, "status", "--porcelain", "--", "app", "architecture", "tests")
    if changed:
        raise StageCheckError("Current architecture source/tests are dirty; commit first")
    current_head = _git(repo, "rev-parse", "HEAD")
    print(f"[stage-ci] CURRENT {current} source={current_head}", flush=True)
    if current == A01:
        if _git(repo, "rev-parse", "HEAD:app") != HISTORICAL_APP_TREE:
            raise StageCheckError("Claimed A0.1 stage has a nonhistorical app tree")
        checks = ["tests/architecture/test_module_structure.py", "tests/architecture/test_layer_rules.py"]
    else:
        checks = ["tests/architecture/test_layer_rules.py", "tests/unit/test_module_public_apis.py"]
        new_tests = repo / "tests/architecture/a1/test_evaluators.py"
        if new_tests.exists():
            checks.append("tests/architecture/a1/test_evaluators.py")
            print("[stage-ci] W2 evaluator unit/fixture suite PRESENT", flush=True)
        else:
            print(
                "[stage-ci] W2 AC_PUBLIC_API/AC_MODULE_GRAPH/AC_DATA_OWNERSHIP "
                "source evaluators PENDING; NOT a complete ΔA2/A1 research gate",
                flush=True,
            )
    _run_pytest(repo, checks, historical=False)
    print(f"[stage-ci] CURRENT {current} CHECKS PASS", flush=True)
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stage", choices=ALLOWED_STAGES, default="auto")
    args = parser.parse_args()
    root = args.repo.resolve()
    try:
        historical_a01_acceptance(root)
        current = current_stage_acceptance(root, requested_stage=args.stage)
    except StageCheckError as error:
        print(f"[stage-ci] FAIL: {error}", file=sys.stderr, flush=True)
        return 1
    print(
        f"[stage-ci] PASS historical_source={HISTORICAL_A01_SHA} "
        f"current_stage={current}; final A1 proof and DA01 research gates NOT ASSERTED",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
