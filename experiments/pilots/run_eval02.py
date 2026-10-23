"""Execute and analyze the preregistered EVAL-02 source mutation study."""

# ruff: noqa: E501 -- generated report prose and case tables are intentionally unwrapped.

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _git_executable() -> str:
    """Find Git once so every subprocess uses an argv-only invocation."""
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("Git executable is required for EVAL-02")
    return executable


GIT = _git_executable()
SCRIPT_PATH = Path(__file__).resolve()
REPOSITORY_ROOT = SCRIPT_PATH.parents[2]
CATALOG_PATH = REPOSITORY_ROOT / "experiments/pilots/EVAL02_MUTATION_CATALOG_V1.json"
PROTOCOL_PATH = REPOSITORY_ROOT / "experiments/pilots/EVAL02_PROTOCOL_V1.md"
BASELINE_COMMIT = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
BASELINE_APP_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
MAIN_BASE = "cd134063e8c1eae37eb3bafe01ce228f02f49493"
STATE_NAME = "A0_4_REPORT_QUERY_PORT"
STATE_MANIFEST = "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
EVALUATOR_IDS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH")
RETURN_CODES = {
    "COMPLIANT": 0,
    "NON_COMPLIANT": 1,
    "NOT_EVALUABLE": 2,
    "UNKNOWN": 2,
    "NOT_APPLICABLE": 3,
}
COMMIT_DATE = "2026-10-23T00:00:00+00:00"
COMMIT_ENV = {
    "GIT_AUTHOR_NAME": "EVAL-02 Experimental Harness",
    "GIT_AUTHOR_EMAIL": "eval02@invalid.example",
    "GIT_COMMITTER_NAME": "EVAL-02 Experimental Harness",
    "GIT_COMMITTER_EMAIL": "eval02@invalid.example",
    "GIT_AUTHOR_DATE": COMMIT_DATE,
    "GIT_COMMITTER_DATE": COMMIT_DATE,
}
GENERATED_NAMES = {
    "EVAL02_ANALYSIS_V1.json",
    "EVAL02_CASE_RESULTS_V1.csv",
    "EVAL02_REPORT_V1.md",
    "EVAL02_MANUSCRIPT_UA.md",
    "SHA256SUMS",
    "run-manifest.json",
}


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest for bytes."""
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash one file without changing it."""
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    """Serialize JSON deterministically for evaluator source inventory checks."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def read_json(path: Path) -> Any:
    """Read a UTF-8 JSON document."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    """Write stable, human-readable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def git(repo_root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run Git with a fixed executable, an argument vector, and no shell."""
    result = subprocess.run(  # noqa: S603 - argv-only Git command; no shell
        [GIT, "-C", str(repo_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result


def git_with_env(repo_root: Path, env: dict[str, str], *arguments: str) -> None:
    """Run a deterministic Git commit command."""
    result = subprocess.run(  # noqa: S603 - argv-only Git command; no shell
        [GIT, "-C", str(repo_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode:
        raise RuntimeError(f"git {' '.join(arguments)} failed: {result.stderr.strip()}")


def current_commit(repo_root: Path) -> str:
    """Return the full checked-out Git commit SHA."""
    return git(repo_root, "rev-parse", "HEAD").stdout.strip()


def complete_status(repo_root: Path) -> str:
    """Return the full status, including untracked files."""
    return git(repo_root, "status", "--porcelain", "--untracked-files=all").stdout


def _replace_once(path: Path, old: str, new: str) -> None:
    """Apply one exact source replacement or stop before producing a case."""
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise ValueError(f"Mutation anchor was not unique in {path}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def _append_once(path: Path, text: str) -> None:
    """Append a source declaration without changing line endings or encoding."""
    source = path.read_text(encoding="utf-8")
    path.write_text(source.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def apply_mutation(repo_root: Path, operation: str) -> list[str]:
    """Apply one preregistered source-only A0.4 mutation and return changed paths."""
    reporting = repo_root / "app/modules/reporting/service.py"
    tasks_public = repo_root / "app/modules/tasks/public.py"
    changed: list[str] = []
    if operation == "rewrite_reporting_tasks_imports_as_relative_public_imports":
        _replace_once(
            reporting,
            "from app.modules.tasks.public import TaskSummary\n"
            "from app.modules.tasks.public import get_task_summary as _get_task_summary\n",
            "from ..tasks.public import TaskSummary\n"
            "from ..tasks.public import get_task_summary as _get_task_summary\n",
        )
        changed.append("app/modules/reporting/service.py")
    elif operation == "move_reporting_tasks_public_query_import_into_function":
        _replace_once(
            reporting,
            "from app.modules.tasks.public import get_task_summary as _get_task_summary\n",
            "",
        )
        _replace_once(
            reporting,
            "def get_task_summary(session: Session) -> TaskSummary:\n"
            '    """Return the task summary report."""\n'
            "    return _get_task_summary(session)",
            "def get_task_summary(session: Session) -> TaskSummary:\n"
            '    """Return the task summary report."""\n'
            "    from app.modules.tasks.public import get_task_summary as _get_task_summary\n\n"
            "    return _get_task_summary(session)",
        )
        changed.append("app/modules/reporting/service.py")
    elif operation == "remove_tasks_public_get_task_summary":
        _replace_once(
            tasks_public,
            "def get_task_summary(session: Session) -> TaskSummary:\n"
            '    """Return aggregate task counts through the public Tasks contract."""\n'
            "    return cast(TaskSummary, _task_summary(session))\n",
            "",
        )
        changed.append("app/modules/tasks/public.py")
    elif operation == "remove_task_summary_count_by_status_field":
        _replace_once(tasks_public, "    count_by_status: dict[str, int]\n", "")
        changed.append("app/modules/tasks/public.py")
    elif operation == "add_tasks_public_debug_summary_export":
        _append_once(
            tasks_public,
            'def debug_summary() -> str:\n    """Return a diagnostic summary."""\n    return "debug"',
        )
        changed.append("app/modules/tasks/public.py")
    elif operation == "add_aliased_notifications_service_module_import":
        _replace_once(
            reporting,
            "from app.modules.tasks.public import get_task_summary as _get_task_summary\n",
            "from app.modules.tasks.public import get_task_summary as _get_task_summary\n"
            "import app.modules.notifications.service as _notifications_service\n",
        )
        changed.append("app/modules/reporting/service.py")
    elif operation == "add_function_local_relative_notifications_public_import":
        _replace_once(
            reporting,
            "    return _get_task_summary(session)",
            "    from ..notifications.public import create_notification as _create_notification\n\n"
            "    return _get_task_summary(session)",
        )
        changed.append("app/modules/reporting/service.py")
    elif operation == "add_dynamic_notifications_service_import":
        _replace_once(
            reporting,
            "from sqlalchemy.orm import Session\n",
            "import importlib\n\nfrom sqlalchemy.orm import Session\n",
        )
        _replace_once(
            reporting,
            "    return _get_task_summary(session)",
            '    importlib.import_module("app.modules.notifications.service")\n'
            "    return _get_task_summary(session)",
        )
        changed.append("app/modules/reporting/service.py")
    elif operation == "make_task_summary_session_keyword_only":
        _replace_once(
            tasks_public,
            "def get_task_summary(session: Session) -> TaskSummary:",
            "def get_task_summary(*, session: Session) -> TaskSummary:",
        )
        changed.append("app/modules/tasks/public.py")
    elif operation == "none":
        return []
    else:
        raise ValueError(f"Unknown EVAL-02 mutation operation: {operation}")

    for relative in changed:
        path = repo_root / relative
        ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    return changed


def evaluator_artifacts(repo_root: Path) -> tuple[list[dict[str, str]], str]:
    """Compute evaluator source inventory and its canonical aggregate digest."""
    evaluator_root = repo_root / "architecture/acceptance/a1"
    artifacts = [
        {"path": path.name, "sha256": sha256_file(path)}
        for path in sorted(evaluator_root.glob("*.py"))
    ]
    return artifacts, sha256_bytes(canonical_json(artifacts))


def validate_preregistration(repo_root: Path, catalog: dict[str, Any]) -> tuple[str, str, str]:
    """Require a clean descendant of the direct-child preregistration commit."""
    if complete_status(repo_root).strip():
        raise RuntimeError("Experiment checkout must be completely clean")
    head = current_commit(repo_root)
    catalog_relative = CATALOG_PATH.relative_to(repo_root).as_posix()
    preregistration = git(
        repo_root, "log", "-1", "--format=%H", "--", catalog_relative
    ).stdout.strip()
    if not preregistration:
        raise RuntimeError("Committed preregistration revision is unavailable")
    parent = git(repo_root, "rev-parse", f"{preregistration}^1").stdout.strip()
    if parent != catalog["experiment_base_main_sha"] or parent != MAIN_BASE:
        raise RuntimeError("Preregistration must be a direct child of verified PR #38 main")
    for ancestor in (preregistration, BASELINE_COMMIT):
        if git(repo_root, "merge-base", "--is-ancestor", ancestor, head, check=False).returncode:
            raise RuntimeError(f"Required source revision is not an ancestor: {ancestor}")
    if git(repo_root, "rev-parse", f"{BASELINE_COMMIT}:app").stdout.strip() != BASELINE_APP_TREE:
        raise RuntimeError("Canonical A0.4 application tree SHA mismatch")
    if git(repo_root, "rev-parse", f"{MAIN_BASE}^{{commit}}", check=False).returncode:
        raise RuntimeError("Verified main commit object is unavailable")
    for relative, expected_sha in catalog["canonical_identity_only_references"].items():
        if sha256_file(repo_root / relative) != expected_sha:
            raise RuntimeError(f"Canonical identity reference changed: {relative}")
        main_bytes = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
            [GIT, "-C", str(repo_root), "show", f"{MAIN_BASE}:{relative}"],
            check=False,
            capture_output=True,
        )
        if main_bytes.returncode or sha256_bytes(main_bytes.stdout) != expected_sha:
            raise RuntimeError(f"Identity-only source missing from verified main: {relative}")
    for relative, expected_sha in catalog["eval01_immutable_readback_references"].items():
        if sha256_file(repo_root / relative) != expected_sha:
            raise RuntimeError(f"Frozen EVAL-01 artifact changed: {relative}")
    for evaluator_id in EVALUATOR_IDS:
        evaluator = catalog["evaluators"][evaluator_id]
        config_path = repo_root / evaluator["configuration"]
        if sha256_file(config_path) != evaluator["configuration_sha256"]:
            raise RuntimeError(f"{evaluator_id} configuration digest mismatch")
    return head, preregistration, sha256_file(CATALOG_PATH)


def _commit_mutation(case_root: Path, case_id: str) -> None:
    """Create one deterministic mutation commit containing only app/ changes."""
    env = os.environ.copy()
    env.update(COMMIT_ENV)
    git_with_env(
        case_root,
        env,
        "-c",
        "user.name=EVAL-02 Experimental Harness",
        "-c",
        "user.email=eval02@invalid.example",
        "add",
        "--",
        "app",
    )
    git_with_env(
        case_root,
        env,
        "-c",
        "user.name=EVAL-02 Experimental Harness",
        "-c",
        "user.email=eval02@invalid.example",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        f"EVAL-02 {case_id} mutation v1.0.0",
    )


def _clone_baseline(repo_root: Path, destination: Path) -> None:
    """Create a disposable clean checkout at the exact A0.4 commit."""
    result = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
        [GIT, "clone", "--shared", "--no-checkout", str(repo_root), str(destination)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Git clone failed: {result.stderr.strip()}")
    git(destination, "checkout", "--detach", BASELINE_COMMIT)
    if git(destination, "rev-parse", "HEAD:app").stdout.strip() != BASELINE_APP_TREE:
        raise RuntimeError("Materialized case does not match the canonical A0.4 app tree")
    if complete_status(destination).strip():
        raise RuntimeError("Canonical A0.4 checkout is not clean")


def _case_bundle(
    case_root: Path, case_id: str, is_mutation: bool, evidence_root: Path
) -> dict[str, Any]:
    """Preserve the exact diff and a verifiable Git bundle for one case."""
    patch = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
        [
            GIT,
            "-C",
            str(case_root),
            "diff",
            "--binary",
            "--no-ext-diff",
            "--no-renames",
            BASELINE_COMMIT,
            "HEAD",
            "--",
            "app",
        ],
        check=False,
        capture_output=True,
    )
    if patch.returncode:
        raise RuntimeError("Could not create mutation patch")
    case_evidence = evidence_root / "cases" / case_id
    case_evidence.mkdir(parents=True, exist_ok=True)
    patch_path = case_evidence / "mutation.patch"
    patch_path.write_bytes(patch.stdout)
    bundle_path: Path | None = None
    if is_mutation:
        bundle_path = case_evidence / "mutation.bundle"
        bundle = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
            [
                GIT,
                "-C",
                str(case_root),
                "bundle",
                "create",
                str(bundle_path),
                "HEAD",
                f"^{BASELINE_COMMIT}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if bundle.returncode:
            raise RuntimeError(f"Git bundle creation failed: {bundle.stderr.strip()}")
        verify = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
            [GIT, "bundle", "verify", str(bundle_path)],
            check=False,
            capture_output=True,
            text=True,
            cwd=case_root,
        )
        if verify.returncode:
            raise RuntimeError(f"Git bundle verification failed: {verify.stderr.strip()}")
    head = current_commit(case_root)
    parents = git(case_root, "rev-list", "--parents", "-n", "1", head).stdout.split()[1:]
    if (is_mutation and parents != [BASELINE_COMMIT]) or (
        not is_mutation and head != BASELINE_COMMIT
    ):
        raise RuntimeError(f"Case {case_id} has unexpected Git parentage")
    if complete_status(case_root).strip():
        raise RuntimeError(f"Case {case_id} checkout is not clean after source revision creation")
    return {
        "case_id": case_id,
        "source_commit_sha": head,
        "source_parent_shas": parents,
        "repository_tree_sha": git(case_root, "rev-parse", "HEAD^{tree}").stdout.strip(),
        "application_tree_sha": git(case_root, "rev-parse", "HEAD:app").stdout.strip(),
        "mutation_patch_path": patch_path.relative_to(evidence_root).as_posix(),
        "mutation_patch_sha256": sha256_file(patch_path),
        "mutation_bundle_path": bundle_path.relative_to(evidence_root).as_posix()
        if bundle_path
        else None,
        "mutation_bundle_sha256": sha256_file(bundle_path) if bundle_path else None,
        "complete_git_status_before_evaluation": "clean",
        "case_checkout_path": str(case_root),
    }


def _copy_frozen_inputs(case_root: Path, repo_root: Path, evidence_root: Path) -> dict[str, Any]:
    """Archive exact evaluator inputs from A0.4 plus identity-only main references."""
    source_paths = [
        "architecture/acceptance/a1/__init__.py",
        "architecture/acceptance/a1/analyzers.py",
        "architecture/acceptance/a1/cli.py",
        "architecture/acceptance/a1/engine.py",
        "architecture/acceptance/a1/public_api_v1.yaml",
        "architecture/acceptance/a1/module_graph_v1.yaml",
        STATE_MANIFEST,
    ]
    copied: dict[str, str] = {}
    revisions: dict[str, str] = {}
    for relative in source_paths:
        source = case_root / relative
        target = evidence_root / "frozen_inputs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied[relative] = sha256_file(target)
        revisions[relative] = BASELINE_COMMIT
    for relative in read_json(CATALOG_PATH)["canonical_identity_only_references"]:
        source = repo_root / relative
        target = evidence_root / "frozen_inputs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied[relative] = sha256_file(target)
        revisions[relative] = MAIN_BASE
    return {"sha256": copied, "source_commit_by_path": revisions}


def _materialize_case(
    repo_root: Path,
    case: dict[str, Any],
    destination: Path,
    evidence_root: Path,
) -> dict[str, Any]:
    """Create and record one independent clean child of the canonical A0.4 commit."""
    _clone_baseline(repo_root, destination)
    changed = apply_mutation(destination, case["mutation"])
    is_mutation = case["mutation"] != "none"
    if is_mutation:
        if not changed:
            raise RuntimeError(f"Mutation {case['mutation']} produced no source changes")
        _commit_mutation(destination, case["case_id"])
    elif changed:
        raise RuntimeError("The clean control unexpectedly changed source files")
    provenance = _case_bundle(destination, case["case_id"], is_mutation, evidence_root)
    provenance["mutation"] = case["mutation"]
    provenance["changed_source_paths"] = changed
    return provenance


def _validate_case_observation(
    evidence: dict[str, Any],
    case: dict[str, Any],
    evaluator_id: str,
    source_sha: str,
    checkout_status_after: str,
    catalog: dict[str, Any],
) -> list[str]:
    """Compare one output to preregistered evaluator behavior and source provenance."""
    failures: list[str] = []
    expected = case["expected_by_evaluator"][evaluator_id]
    evaluator = catalog["evaluators"][evaluator_id]
    observed_evaluator = evidence.get("evaluator", {})
    if observed_evaluator.get("version") != evaluator["version"]:
        failures.append("EVALUATOR_VERSION_MISMATCH")
    if observed_evaluator.get("configuration_digest") != evaluator["configuration_sha256"]:
        failures.append("CONFIGURATION_DIGEST_MISMATCH")
    if observed_evaluator.get("source_digest") != evaluator["expected_source_artifact_digest"]:
        failures.append("EVALUATOR_SOURCE_DIGEST_MISMATCH")
    architecture = evidence.get("architecture", {})
    if architecture.get("target_source_sha") != source_sha:
        failures.append("TARGET_SOURCE_SHA_MISMATCH")
    if architecture.get("expected_source_sha") != source_sha:
        failures.append("EXPECTED_SOURCE_SHA_MISMATCH")
    if architecture.get("source_sha_status") != "MATCHED":
        failures.append("SOURCE_IDENTITY_NOT_MATCHED")
    if architecture.get("subject_source_dirty") is not False:
        failures.append("SUBJECT_SOURCE_NOT_CLEAN")
    if checkout_status_after.strip():
        failures.append("CHECKOUT_DIRTY_AFTER_EVALUATION")
    if architecture.get("state") != STATE_NAME:
        failures.append("ARCHITECTURE_STATE_MISMATCH")
    result = evidence.get("result", {})
    if result.get("execution_status") != "COMPLETED":
        failures.append("EVALUATOR_EXECUTION_NOT_COMPLETED")
    if result.get("compliance") != expected["compliance"]:
        failures.append("COMPLIANCE_OUTCOME_MISMATCH")
    observed_codes = sorted(
        {
            str(item.get("code"))
            for item in evidence.get("diagnostics", {}).get("observed_policy_findings", [])
            if isinstance(item, dict) and item.get("code")
        }
    )
    if observed_codes != sorted(expected["finding_codes"]):
        failures.append("FINDING_CLASS_MISMATCH")
    scope = evidence.get("source_scope", {})
    if scope.get("complete") is not case["expected_scope_complete"]:
        failures.append("SOURCE_SCOPE_COMPLETENESS_MISMATCH")
    if evaluator_id == "AC_MODULE_GRAPH":
        diagnostics = evidence.get("diagnostics", {})
        if len(diagnostics.get("cycles", [])) != case["expected_cycle_count"]:
            failures.append("CYCLE_COUNT_MISMATCH")
        unresolved_count = len(diagnostics.get("unresolved_capability_imports", [])) + len(
            diagnostics.get("unresolved_local_imports", [])
        )
        if unresolved_count != case["expected_unresolved_import_count"]:
            failures.append("UNRESOLVED_IMPORT_COUNT_MISMATCH")
        observed_edges = sorted(
            (str(edge["from"]), str(edge["to"])) for edge in diagnostics.get("edges", [])
        )
        expected_edges = sorted(tuple(edge) for edge in case["expected_edge_pairs"])
        if observed_edges != expected_edges:
            failures.append("EDGE_SET_MISMATCH")
    return failures


def _append_event(path: Path, event: dict[str, Any]) -> None:
    """Append one JSON object per executed call."""
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")


def preflight(repo_root: Path) -> int:
    """Check mutation anchors and Git provenance without invoking evaluators."""
    catalog = read_json(CATALOG_PATH)
    head, preregistration, catalog_sha = validate_preregistration(repo_root, catalog)
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="eval02-preflight-") as temporary:
        root = Path(temporary)
        for index, case in enumerate(catalog["cases"]):
            destination = root / f"case-{index:02d}"
            _clone_baseline(repo_root, destination)
            changed = apply_mutation(destination, case["mutation"])
            is_mutation = case["mutation"] != "none"
            if is_mutation:
                if not changed:
                    raise RuntimeError(
                        f"Preflight mutation did not change source: {case['case_id']}"
                    )
                _commit_mutation(destination, case["case_id"])
            elif changed:
                raise RuntimeError("Preflight clean control changed source")
            current = current_commit(destination)
            parent = git(destination, "rev-list", "--parents", "-n", "1", current).stdout.split()[
                1:
            ]
            if (is_mutation and parent != [BASELINE_COMMIT]) or (
                not is_mutation and current != BASELINE_COMMIT
            ):
                raise RuntimeError(f"Preflight parentage mismatch: {case['case_id']}")
            if complete_status(destination).strip():
                raise RuntimeError(f"Preflight checkout is dirty: {case['case_id']}")
            cases.append(
                {
                    "case_id": case["case_id"],
                    "source_commit_sha": current,
                    "application_tree_sha": git(
                        destination, "rev-parse", "HEAD:app"
                    ).stdout.strip(),
                    "changed_source_paths": changed,
                    "mutation_commit_parent": parent,
                }
            )
    artifacts, digest = evaluator_artifacts(repo_root)
    if digest != catalog["evaluators"]["AC_MODULE_GRAPH"]["expected_source_artifact_digest"]:
        raise RuntimeError("Pinned evaluator implementation digest mismatch")
    print(
        json.dumps(
            {
                "preflight": "PASS",
                "evaluator_invocations": 0,
                "experiment_checkout_head": head,
                "preregistration_commit_sha": preregistration,
                "preregistration_catalog_sha256": catalog_sha,
                "evaluator_source_artifacts": artifacts,
                "evaluator_source_digest": digest,
                "cases": cases,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def execute_experiment(repo_root: Path, output_dir: Path) -> int:
    """Materialize the frozen catalog, run 60 calls, and preserve their raw evidence."""
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError(f"Output directory already exists: {output_dir}")
    catalog = read_json(CATALOG_PATH)
    head, preregistration, catalog_sha = validate_preregistration(repo_root, catalog)
    artifacts, evaluator_digest = evaluator_artifacts(repo_root)
    for evaluator_id in EVALUATOR_IDS:
        if (
            evaluator_digest
            != catalog["evaluators"][evaluator_id]["expected_source_artifact_digest"]
        ):
            raise RuntimeError(f"{evaluator_id} evaluator source digest mismatch")
    for relative, expected_sha in catalog["eval01_immutable_readback_references"].items():
        if sha256_file(repo_root / relative) != expected_sha:
            raise RuntimeError(f"Frozen EVAL-01 file changed before execution: {relative}")

    output_dir.mkdir(parents=True)
    (output_dir / "preregistration").mkdir()
    shutil.copyfile(CATALOG_PATH, output_dir / "preregistration/mutation_catalog.json")
    shutil.copyfile(PROTOCOL_PATH, output_dir / "preregistration/protocol.md")
    shutil.copyfile(SCRIPT_PATH, output_dir / "preregistration/run_eval02.py")
    write_json(output_dir / "preregistration/evaluator_artifacts.json", artifacts)

    try:
        import yaml

        yaml_version = str(yaml.__version__)
        yaml_path = str(getattr(yaml, "__file__", "unavailable"))
    except ImportError:
        yaml_version = "unavailable"
        yaml_path = "unavailable"

    schedule = [
        {"case_id": case["case_id"], "evaluator_id": evaluator_id, "repeat": repeat}
        for case in catalog["cases"]
        for evaluator_id in EVALUATOR_IDS
        for repeat in range(
            1, catalog["execution_protocol"]["measured_repeats_per_case_evaluator"] + 1
        )
    ]
    random.Random(catalog["execution_protocol"]["schedule_seed"]).shuffle(schedule)  # noqa: S311 - deterministic schedule, not security use
    write_json(output_dir / "schedule.json", schedule)

    provenance: dict[str, dict[str, Any]] = {}
    case_paths: dict[str, Path | None] = {}
    failures: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    start_utc = datetime.now(UTC).isoformat()
    with tempfile.TemporaryDirectory(prefix="eval02-cases-") as temporary:
        temporary_root = Path(temporary)
        for index, case in enumerate(catalog["cases"]):
            try:
                case_path = temporary_root / f"case-{index:02d}-{case['case_id']}"
                provenance[case["case_id"]] = _materialize_case(
                    repo_root, case, case_path, output_dir
                )
                case_paths[case["case_id"]] = case_path
                if case["case_id"] == "clean_scope_control":
                    provenance[case["case_id"]]["frozen_input_digests"] = _copy_frozen_inputs(
                        case_path, repo_root, output_dir
                    )
            except Exception as exc:
                case_paths[case["case_id"]] = None
                provenance[case["case_id"]] = {
                    "case_id": case["case_id"],
                    "materialization_failure": f"{type(exc).__name__}: {exc}",
                }
                failures.append(
                    {
                        "case_id": case["case_id"],
                        "stage": "case_materialization",
                        "detail": provenance[case["case_id"]]["materialization_failure"],
                    }
                )

        event_log = output_dir / "execution.jsonl"
        for index, scheduled in enumerate(schedule, start=1):
            case = next(
                item for item in catalog["cases"] if item["case_id"] == scheduled["case_id"]
            )
            evaluator_id = scheduled["evaluator_id"]
            case_path = case_paths[case["case_id"]]
            source_sha = provenance[case["case_id"]].get("source_commit_sha")
            run_dir = (
                output_dir
                / "runs"
                / case["case_id"]
                / evaluator_id
                / f"repeat-{scheduled['repeat']}"
            )
            run_dir.mkdir(parents=True, exist_ok=True)
            stdout_path = run_dir / "stdout.json"
            stderr_path = run_dir / "stderr.log"
            command = [
                sys.executable,
                "-m",
                "architecture.acceptance.a1.cli",
                evaluator_id,
                "--repo-root",
                str(case_path) if case_path else "__MATERIALIZATION_FAILED__",
                "--state-manifest",
                STATE_MANIFEST,
                "--architecture-state",
                STATE_NAME,
                "--expected-source-sha",
                str(source_sha or "__SOURCE_SHA_UNAVAILABLE__"),
            ]
            started_at = datetime.now(UTC).isoformat()
            started_ns = time.perf_counter_ns()
            output = b""
            error = b""
            return_code: int | None = None
            launch_error: str | None = None
            parse_error: str | None = None
            observation: dict[str, Any] | None = None
            checkout_after = "not_run"
            if case_path is None:
                launch_error = "CASE_MATERIALIZATION_FAILED"
                error = str(
                    provenance[case["case_id"]].get("materialization_failure", "unknown")
                ).encode()
            else:
                try:
                    if current_commit(case_path) != source_sha:
                        raise RuntimeError("Case HEAD changed after materialization")
                    if complete_status(case_path).strip():
                        raise RuntimeError("Case checkout is dirty before evaluator invocation")
                    process = subprocess.run(  # noqa: S603 - pinned evaluator module argv; no shell
                        command,
                        cwd=case_path,
                        check=False,
                        capture_output=True,
                        timeout=120,
                    )
                    output, error, return_code = process.stdout, process.stderr, process.returncode
                    checkout_after = complete_status(case_path)
                    if output:
                        try:
                            observation = json.loads(output.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                            parse_error = f"{type(exc).__name__}: {exc}"
                except subprocess.TimeoutExpired as exc:
                    output = exc.stdout if isinstance(exc.stdout, bytes) else b""
                    error = exc.stderr if isinstance(exc.stderr, bytes) else b""
                    launch_error = "EVALUATOR_TIMEOUT_120_SECONDS"
                except Exception as exc:  # preserve each failed call as an observation
                    launch_error = f"{type(exc).__name__}: {exc}"
                    error = str(exc).encode("utf-8")
            elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
            ended_at = datetime.now(UTC).isoformat()
            stdout_path.write_bytes(output)
            stderr_path.write_bytes(error)
            record: dict[str, Any] = {
                **scheduled,
                "schedule_index": index,
                "source_commit_sha": source_sha,
                "command": command,
                "working_directory": str(case_path) if case_path else None,
                "started_at_utc": started_at,
                "ended_at_utc": ended_at,
                "wall_time_ms": round(elapsed_ms, 6),
                "return_code": return_code,
                "launch_error": launch_error,
                "parse_error": parse_error,
                "stdout_path": stdout_path.relative_to(output_dir).as_posix(),
                "stdout_sha256": sha256_file(stdout_path),
                "stderr_path": stderr_path.relative_to(output_dir).as_posix(),
                "stderr_sha256": sha256_file(stderr_path),
                "checkout_status_after": checkout_after.strip() or "clean",
            }
            if observation is not None:
                result = observation.get("result", {})
                architecture = observation.get("architecture", {})
                observed_codes = sorted(
                    {
                        str(item.get("code"))
                        for item in observation.get("diagnostics", {}).get(
                            "observed_policy_findings", []
                        )
                        if isinstance(item, dict) and item.get("code")
                    }
                )
                scope = observation.get("source_scope", {})
                record.update(
                    {
                        "observed_compliance": result.get("compliance"),
                        "execution_status": result.get("execution_status"),
                        "finding_codes": observed_codes,
                        "target_source_sha": architecture.get("target_source_sha"),
                        "expected_source_sha": architecture.get("expected_source_sha"),
                        "source_sha_status": architecture.get("source_sha_status"),
                        "subject_source_dirty": architecture.get("subject_source_dirty"),
                        "source_scope_complete": scope.get("complete"),
                        "inspected_file_count": len(scope.get("inspected_paths", [])),
                        "evaluator_version": observation.get("evaluator", {}).get("version"),
                        "evaluator_source_digest": observation.get("evaluator", {}).get(
                            "source_digest"
                        ),
                        "configuration_digest": observation.get("evaluator", {}).get(
                            "configuration_digest"
                        ),
                        "raw_diagnostics_digest": observation.get("raw_output", {}).get("sha256"),
                    }
                )
                outcome_failures = _validate_case_observation(
                    observation, case, evaluator_id, str(source_sha), checkout_after, catalog
                )
                expected_return = RETURN_CODES.get(result.get("compliance"))
                if return_code != expected_return:
                    outcome_failures.append("RETURN_CODE_MISMATCH")
                for failure in outcome_failures:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "evaluator_id": evaluator_id,
                            "repeat": scheduled["repeat"],
                            "stage": "observation_validation",
                            "detail": failure,
                        }
                    )
            else:
                failures.append(
                    {
                        "case_id": case["case_id"],
                        "evaluator_id": evaluator_id,
                        "repeat": scheduled["repeat"],
                        "stage": "evaluator_execution",
                        "detail": launch_error or parse_error or "NO_JSON_OBSERVATION",
                    }
                )
            runs.append(record)
            _append_event(event_log, record)

    raw_artifacts = {
        path.relative_to(output_dir).as_posix(): sha256_file(path)
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name != "run-manifest.json"
    }
    manifest = {
        "schema_version": 1,
        "experiment_id": catalog["experiment_id"],
        "protocol_version": "1.0.0",
        "catalog_version": catalog["catalog_version"],
        "registered_at_utc": git(
            repo_root, "show", "-s", "--format=%cI", preregistration
        ).stdout.strip(),
        "preregistration_commit_sha": preregistration,
        "preregistration_catalog_sha256": catalog_sha,
        "preregistration_protocol_sha256": sha256_file(PROTOCOL_PATH),
        "preregistration_runner_sha256": sha256_file(SCRIPT_PATH),
        "execution_branch_head_sha": head,
        "experiment_base_main_sha": catalog["experiment_base_main_sha"],
        "source_baseline": catalog["source_baseline"],
        "evaluator_source_artifacts": artifacts,
        "evaluator_source_digest": evaluator_digest,
        "configurations": {
            evaluator_id: {
                "path": catalog["evaluators"][evaluator_id]["configuration"],
                "sha256": catalog["evaluators"][evaluator_id]["configuration_sha256"],
            }
            for evaluator_id in EVALUATOR_IDS
        },
        "execution_environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "pythonpath": os.environ.get("PYTHONPATH", ""),
            "yaml_version": yaml_version,
            "yaml_module_path": yaml_path,
            "platform": platform.platform(),
            "schedule_seed": catalog["execution_protocol"]["schedule_seed"],
            "repeat_count": catalog["execution_protocol"]["measured_repeats_per_case_evaluator"],
            "planned_evaluator_calls": len(schedule),
            "measured_schedule": "schedule.json",
        },
        "cases": provenance,
        "runs": runs,
        "failures": failures,
        "raw_artifacts_sha256": raw_artifacts,
        "started_at_utc": start_utc,
        "completed_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(output_dir / "run-manifest.json", manifest)
    print(
        json.dumps(
            {"run_dir": str(output_dir), "run_count": len(runs), "failure_count": len(failures)},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not failures and len(runs) == len(schedule) else 1


def analyze_case(
    case: dict[str, Any],
    evaluator_id: str,
    run_records: list[dict[str, Any]],
    repeat_count: int,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    """Collapse timing repeats to one source-condition result and eligibility decision."""
    expected = case["expected_by_evaluator"][evaluator_id]
    selected = sorted(
        [
            item
            for item in run_records
            if item.get("case_id") == case["case_id"] and item.get("evaluator_id") == evaluator_id
        ],
        key=lambda item: int(item.get("repeat", 0)),
    )
    statuses = [item.get("observed_compliance") for item in selected]
    findings = [item.get("finding_codes", []) for item in selected]
    evaluator = catalog["evaluators"][evaluator_id]
    provenance_valid = len(selected) == repeat_count and all(
        not item.get("launch_error")
        and not item.get("parse_error")
        and item.get("execution_status") == "COMPLETED"
        and item.get("target_source_sha") == item.get("source_commit_sha")
        and item.get("expected_source_sha") == item.get("source_commit_sha")
        and item.get("source_sha_status") == "MATCHED"
        and item.get("subject_source_dirty") is False
        and item.get("checkout_status_after") == "clean"
        and item.get("evaluator_version") == evaluator["version"]
        and item.get("evaluator_source_digest") == evaluator["expected_source_artifact_digest"]
        and item.get("configuration_digest") == evaluator["configuration_sha256"]
        and item.get("return_code") == RETURN_CODES.get(item.get("observed_compliance"))
        for item in selected
    )
    status_stable = bool(statuses) and len(set(statuses)) == 1
    findings_stable = bool(findings) and len({tuple(value) for value in findings}) == 1
    observed = statuses[0] if status_stable else "UNKNOWN"
    architectural_status = expected["architectural_status"]
    metric_eligible = (
        expected["metric_eligible"]
        and expected["applicability"] == "APPLICABLE"
        and architectural_status in {"COMPLIANT", "NON_COMPLIANT"}
    )
    valid_for_matrix = (
        metric_eligible
        and provenance_valid
        and status_stable
        and findings_stable
        and observed in {"COMPLIANT", "NON_COMPLIANT"}
    )
    exclusions: list[str] = []
    if not metric_eligible:
        exclusions.append(case.get("exclusion_reason", expected["applicability"]))
    if not provenance_valid:
        exclusions.append("REPEATED_RUN_PROVENANCE_OR_EXECUTION_INCOMPLETE")
    if not status_stable:
        exclusions.append("REPEATED_COMPLIANCE_OUTCOMES_NOT_STABLE")
    if not findings_stable:
        exclusions.append("REPEATED_FINDING_CLASSES_NOT_STABLE")
    if metric_eligible and status_stable and observed not in {"COMPLIANT", "NON_COMPLIANT"}:
        exclusions.append("OBSERVED_UNKNOWN_OR_NOT_EVALUABLE")
    return {
        "case_id": case["case_id"],
        "evaluator_id": evaluator_id,
        "evaluator_applicability": expected["applicability"],
        "architectural_status": architectural_status,
        "expected_compliance": expected["compliance"],
        "expected_finding_codes": sorted(expected["finding_codes"]),
        "observed_compliance_by_repeat": statuses,
        "observed_compliance_case_level": observed,
        "observed_finding_codes_by_repeat": findings,
        "observed_finding_classes_stable": findings_stable,
        "preregistered_expected_outcome_matched": (
            len(selected) == repeat_count
            and all(
                item.get("observed_compliance") == expected["compliance"]
                and item.get("finding_codes", []) == sorted(expected["finding_codes"])
                for item in selected
            )
        ),
        "planned_repeat_count": repeat_count,
        "completed_repeat_count": len(selected),
        "provenance_valid": provenance_valid,
        "metric_eligible_by_catalog": metric_eligible,
        "valid_for_confusion_matrix": valid_for_matrix,
        "exclusion_reasons": exclusions,
        "source_commit_sha": selected[0].get("source_commit_sha") if selected else None,
        "application_tree_sha": None,
        "case_wall_time_ms": [item.get("wall_time_ms") for item in selected],
        "case_median_wall_time_ms": statistics.median(
            [
                float(item["wall_time_ms"])
                for item in selected
                if isinstance(item.get("wall_time_ms"), (int, float))
            ]
        )
        if any(isinstance(item.get("wall_time_ms"), (int, float)) for item in selected)
        else None,
    }


def confusion_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute finite case-level metrics from independent architecture labels."""
    included = [item for item in rows if item["valid_for_confusion_matrix"]]
    counts: Counter[str] = Counter()
    for item in included:
        positive = item["architectural_status"] == "NON_COMPLIANT"
        detected = item["observed_compliance_case_level"] == "NON_COMPLIANT"
        if positive and detected:
            counts["tp"] += 1
        elif positive:
            counts["fn"] += 1
        elif detected:
            counts["fp"] += 1
        else:
            counts["tn"] += 1
    tp, fp, tn, fn = (counts[name] for name in ("tp", "fp", "tn", "fn"))
    eligible = sum(bool(item["metric_eligible_by_catalog"]) for item in rows)
    applicability_counts = Counter(item["evaluator_applicability"] for item in rows)
    architecture_counts = Counter(item["architectural_status"] for item in rows)
    return {
        "unit": "one evaluator-by-source-condition case",
        "eligible_binary_applicable_cases": eligible,
        "evaluable_binary_applicable_cases": len(included),
        "unknown_or_invalid_cases": eligible - len(included),
        "excluded_from_matrix_cases": len(rows) - eligible,
        "evaluator_applicability_counts": dict(sorted(applicability_counts.items())),
        "architectural_status_counts": dict(sorted(architecture_counts.items())),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall_sensitivity": tp / (tp + fn) if tp + fn else None,
        "specificity": tn / (tn + fp) if tn + fp else None,
        "accuracy": (tp + tn) / len(included) if included else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
    }


def _validate_raw_inventory(run_dir: Path, manifest: dict[str, Any]) -> list[str]:
    """Verify raw artifact names and digests before deriving result tables."""
    expected = manifest.get("raw_artifacts_sha256", {})
    observed_files = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name not in GENERATED_NAMES
    }
    errors: list[str] = []
    if observed_files != set(expected):
        errors.append("RAW_ARTIFACT_INVENTORY_MISMATCH")
    for relative, digest in expected.items():
        path = run_dir / relative
        if not path.is_file() or sha256_file(path) != digest:
            errors.append(f"RAW_ARTIFACT_DIGEST_MISMATCH:{relative}")
    catalog_path = run_dir / "preregistration/mutation_catalog.json"
    if not catalog_path.is_file() or sha256_file(catalog_path) != manifest.get(
        "preregistration_catalog_sha256"
    ):
        errors.append("PREREGISTRATION_CATALOG_DIGEST_MISMATCH")
    return errors


def _rederive_records(
    run_dir: Path, run_records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Re-derive evaluator fields from raw stdout rather than trusting the run index."""
    derived: list[dict[str, Any]] = []
    errors: list[str] = []
    fields = {
        "observed_compliance": lambda data: data.get("result", {}).get("compliance"),
        "execution_status": lambda data: data.get("result", {}).get("execution_status"),
        "target_source_sha": lambda data: data.get("architecture", {}).get("target_source_sha"),
        "expected_source_sha": lambda data: data.get("architecture", {}).get("expected_source_sha"),
        "source_sha_status": lambda data: data.get("architecture", {}).get("source_sha_status"),
        "subject_source_dirty": lambda data: data.get("architecture", {}).get(
            "subject_source_dirty"
        ),
        "evaluator_version": lambda data: data.get("evaluator", {}).get("version"),
        "evaluator_source_digest": lambda data: data.get("evaluator", {}).get("source_digest"),
        "configuration_digest": lambda data: data.get("evaluator", {}).get("configuration_digest"),
    }
    for record in run_records:
        copied = dict(record)
        stdout_path = run_dir / str(record.get("stdout_path", ""))
        stderr_path = run_dir / str(record.get("stderr_path", ""))
        if not stdout_path.is_file() or sha256_file(stdout_path) != record.get("stdout_sha256"):
            errors.append(
                f"STDOUT_MISSING_OR_DIGEST_MISMATCH:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}"
            )
            derived.append(copied)
            continue
        if not stderr_path.is_file() or sha256_file(stderr_path) != record.get("stderr_sha256"):
            errors.append(
                f"STDERR_MISSING_OR_DIGEST_MISMATCH:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}"
            )
        try:
            observation = json.loads(stdout_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            derived.append(copied)
            continue
        for field, getter in fields.items():
            value = getter(observation)
            if value != record.get(field):
                errors.append(
                    f"RUN_INDEX_DERIVATION_MISMATCH:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}:{field}"
                )
            copied[field] = value
        codes = sorted(
            {
                str(item.get("code"))
                for item in observation.get("diagnostics", {}).get("observed_policy_findings", [])
                if isinstance(item, dict) and item.get("code")
            }
        )
        if codes != record.get("finding_codes"):
            errors.append(
                f"RUN_INDEX_DERIVATION_MISMATCH:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}:finding_codes"
            )
        copied["finding_codes"] = codes
        derived.append(copied)
    return derived, errors


def _metric_table(metrics: dict[str, Any]) -> str:
    """Render case-level confusion counts with undefined metrics left blank."""
    rows = [
        "| Evaluator | TP | FP | TN | FN | Labeled/evaluable | Unknown/invalid | Excluded | Precision | Recall | Specificity | Accuracy | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for evaluator_id in EVALUATOR_IDS:
        item = metrics[evaluator_id]
        cm = item["confusion_matrix"]
        values = [
            item[name]
            for name in ("precision", "recall_sensitivity", "specificity", "accuracy", "f1")
        ]
        formatted = ["NOT_DEFINED" if value is None else f"{value:.3f}" for value in values]
        rows.append(
            f"| `{evaluator_id}` | {cm['tp']} | {cm['fp']} | {cm['tn']} | {cm['fn']} | "
            f"{item['evaluable_binary_applicable_cases']}/{item['eligible_binary_applicable_cases']} | "
            f"{item['unknown_or_invalid_cases']} | {item['excluded_from_matrix_cases']} | "
            + " | ".join(formatted)
            + " |"
        )
    return "\n".join(rows)


def _generate_report(
    catalog: dict[str, Any],
    manifest: dict[str, Any],
    results: dict[str, list[dict[str, Any]]],
    metrics: dict[str, Any],
    timing: dict[str, dict[str, Any]],
    integrity_errors: list[str],
) -> str:
    """Build the report from the preregistration and raw-observation-derived analysis."""
    table = [
        "| Case | Evaluator | Architecture | Applicability | Expected output | Observed repeats | Expected findings | Observed findings | Matrix |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in catalog["cases"]:
        for evaluator_id in EVALUATOR_IDS:
            row = next(item for item in results[evaluator_id] if item["case_id"] == case["case_id"])
            repeats = ", ".join(row["observed_compliance_by_repeat"]) or "NO_OBSERVATIONS"
            expected_codes = ", ".join(row["expected_finding_codes"]) or "none"
            observed_codes = (
                "; ".join(
                    ", ".join(codes) if codes else "none"
                    for codes in row["observed_finding_codes_by_repeat"]
                )
                or "none"
            )
            matrix = (
                "included"
                if row["valid_for_confusion_matrix"]
                else "excluded: " + "; ".join(row["exclusion_reasons"])
            )
            table.append(
                f"| `{case['case_id']}` | `{evaluator_id}` | `{row['architectural_status']}` | "
                f"`{row['evaluator_applicability']}` | `{row['expected_compliance']}` | {repeats} | "
                f"{expected_codes} | {observed_codes} | {matrix} |"
            )
    timing_lines = [
        "| Evaluator | Valid completed calls | Median ms | Minimum ms | Maximum ms |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for evaluator_id in EVALUATOR_IDS:
        row = timing[evaluator_id]
        timing_lines.append(
            f"| `{evaluator_id}` | {row['n_completed']} | {row['median_ms']} | {row['minimum_ms']} | {row['maximum_ms']} |"
        )
    failures = manifest.get("failures", [])
    failure_table = (
        "\n".join(
            f"- `{item.get('case_id')}` / `{item.get('evaluator_id', 'n/a')}` / "
            f"repeat {item.get('repeat', 'n/a')}: {item.get('stage')}: {item.get('detail')}"
            for item in failures
        )
        if failures
        else "- None."
    )
    integrity_text = (
        "\n".join(f"- `{item}`" for item in integrity_errors)
        if integrity_errors
        else "- PASS; no inventory or raw stream digest errors."
    )
    not_evaluable_lines = "\n".join(
        f"- `{evaluator_id}`: "
        + (
            ", ".join(
                f"`{row['case_id']}`"
                for row in results[evaluator_id]
                if row["observed_compliance_case_level"] == "NOT_EVALUABLE"
            )
            or "none"
        )
        for evaluator_id in EVALUATOR_IDS
    )
    return f"""# EVAL-02 results — expanded controlled evaluator validation

- **Protocol/catalog:** 1.0.0; preregistration commit `{
        manifest["preregistration_commit_sha"]
    }`; catalog SHA-256 `{manifest["preregistration_catalog_sha256"]}`.
- **Verified main base:** `{manifest["experiment_base_main_sha"]}`; PR #38 merge commit.
- **Canonical A0.4 source:** `{manifest["source_baseline"]["commit_sha"]}`; application tree `{
        manifest["source_baseline"]["application_tree_sha"]
    }`.
- **Run window:** {manifest.get("started_at_utc")} — {manifest.get("completed_at_utc")}.
- **Environment:** Python {manifest["execution_environment"]["python_version"].split()[0]}, PyYAML {
        manifest["execution_environment"]["yaml_version"]
    }, {manifest["execution_environment"]["platform"]}.

## Design and interpretation

Ten source conditions were registered before evaluator execution. Each mutation was independently created as a clean Git child of canonical A0.4. Both evaluators were called three times per condition; the repeats are collapsed to one case result and are not independent samples. Architectural labels, per-evaluator applicability and expected evaluator outputs were preregistered separately. Out-of-scope and indeterminate cases remain visible but are not included in binary metrics.

## Case-level metrics

{_metric_table(metrics)}

The unit is one evaluator-by-source-condition case. These finite counts do not estimate population-level accuracy, and no confidence intervals or significance tests are reported.

Applicability and architecture-label counts are shown separately:

| Evaluator | Architectural status counts | Applicability counts |
| --- | --- | --- |
{
        chr(10).join(
            f"| `{evaluator_id}` | "
            + ", ".join(
                f"{label}: {count}"
                for label, count in metrics[evaluator_id]["architectural_status_counts"].items()
            )
            + " | "
            + ", ".join(
                f"{label}: {count}"
                for label, count in metrics[evaluator_id]["evaluator_applicability_counts"].items()
            )
            + " |"
            for evaluator_id in EVALUATOR_IDS
        )
    }

## Case results

{chr(10).join(table)}

## Descriptive evaluator time

{chr(10).join(timing_lines)}

Times are fresh subprocess wall durations, not application runtime, CI latency, adaptation cost, CPU or memory use. Timing repetitions are technical repeats on the same source revisions.

## Execution failures, unavailable outcomes and integrity

Runner-recorded failures: {len(failures)}.

{failure_table}

Case-level `NOT_EVALUABLE` outcomes:

{not_evaluable_lines}

Raw archive/inventory integrity: {integrity_text}

Expected CLI exit codes for `NON_COMPLIANT` and `NOT_EVALUABLE` are outcomes, not launch failures. `NOT_EVALUABLE`, unknown, unstable, missing or provenance-invalid rows are reported separately and never converted into detections.

## Threats to validity

**Internal:** all cases use one frozen A0.4 baseline; the local OS, Python runtime, filesystem and cache state may affect timing. Repeats measure invocation stability only.

**Construct:** cases are finite and author-selected. Labels follow the frozen API/edge inventory and language/source semantics; there was no external reviewer or independent human oracle. The signature case is indeterminate under the frozen contract. The dynamic-import boundary is an architecture violation outside both evaluators' direct-import scope. A static source result does not establish runtime behavior or full architecture conformance.

**External:** results apply only to the named evaluator/configuration versions, patterns and A0.4 baseline. They do not support population-level accuracy or generalization to other architectures, repositories, languages or runtime mechanisms.

## Recommendation before MONO-E1

The evaluators can be used as narrowly scoped source evidence when their exact source/configuration bindings and applicability are recorded. EVAL-02 does not justify treating them as complete architecture oracles: the dynamic-import boundary demonstrates a concrete blind spot. Further validation is necessary before using these evaluators as the sole basis for an architecture-validity claim in MONO-E1. MONO-E1 may use them as one bounded input only if the report preserves this limitation and the run has separate checks for unsupported mechanisms; this result does not change any MONO-E1 gate or authorize Method P.

## Reproduction and evidence

See [`EVAL02_PROTOCOL_V1.md`](EVAL02_PROTOCOL_V1.md). The raw archive contains exact commands and streams, case SHAs/trees, mutation patches and Git bundles, preregistration snapshots, frozen evaluator inputs, derived tables, and internal checksums. Verify the external ZIP sidecar before extraction, then run `sha256sum -c SHA256SUMS` from the extraction root.
"""


def _generate_manuscript_ua(
    catalog: dict[str, Any],
    metrics: dict[str, Any],
    timing: dict[str, dict[str, Any]],
    results: dict[str, list[dict[str, Any]]],
    manifest: dict[str, Any],
) -> str:
    """Render a concise Ukrainian manuscript subsection from observed rows."""
    rows: list[str] = []
    for evaluator_id in EVALUATOR_IDS:
        metric = metrics[evaluator_id]
        cm = metric["confusion_matrix"]
        scores = [
            "не визначено" if metric[name] is None else f"{metric[name]:.3f}"
            for name in ("precision", "recall_sensitivity", "specificity", "accuracy", "f1")
        ]
        rows.append(
            f"| {evaluator_id} | {cm['tp']} | {cm['fp']} | {cm['tn']} | {cm['fn']} | "
            f"{metric['evaluable_binary_applicable_cases']}/{metric['eligible_binary_applicable_cases']} | "
            f"{metric['unknown_or_invalid_cases']} | " + " | ".join(scores) + " |"
        )
    case_observations = []
    for case in catalog["cases"]:
        for evaluator_id in EVALUATOR_IDS:
            result = next(
                item for item in results[evaluator_id] if item["case_id"] == case["case_id"]
            )
            observed = ", ".join(result["observed_compliance_by_repeat"]) or "немає спостережень"
            case_observations.append(
                f"| `{case['case_id']}` | `{evaluator_id}` | `{result['architectural_status']}` | "
                f"`{result['evaluator_applicability']}` | {observed} | "
                f"{'так' if result['valid_for_confusion_matrix'] else 'ні'} |"
            )
    not_evaluable_cases = {
        evaluator_id: [
            row["case_id"]
            for row in results[evaluator_id]
            if row["observed_compliance_case_level"] == "NOT_EVALUABLE"
        ]
        for evaluator_id in EVALUATOR_IDS
    }
    return f"""# Підрозділ для рукопису: розширена валідація архітектурних evaluator-ів

Для перевірки меж застосовності `AC_PUBLIC_API` та `AC_MODULE_GRAPH` було проведено EVAL-02 на канонічному вихідному стані A0.4 (`{manifest["source_baseline"]["commit_sha"]}`, дерево `app/` `{manifest["source_baseline"]["application_tree_sha"]}`). Протокол і каталог із очікуваннями зафіксовано до запуску evaluator-ів у коміті `{manifest["preregistration_commit_sha"]}`, що безпосередньо базується на перевіреному `main` `{manifest["experiment_base_main_sha"]}`. Каталог включав {len(catalog["cases"])} умов, зокрема чистий контроль, позитивні форми відносного та локального імпорту, порушення опису публічного контракту, два нові форми залежностей, а також межі динамічного імпорту й неповної специфікації сигнатури. Кожну зміну створено як окремий чистий Git-коміт із канонічним A0.4 як єдиним батьком. Кожен evaluator виконувався тричі для кожної умови; повтори є технічними вимірами одного випадку.

Архітектурний статус, застосовність evaluator-а та очікуваний вихід визначалися окремо. Бінарні метрики включали лише випадки з попередньо визначеним статусом `COMPLIANT`/`NON_COMPLIANT`, де evaluator був застосовним, а всі повтори мали стабільні результати та перевірене походження.

| Evaluator | TP | FP | TN | FN | Застосовних / придатних випадків | Невідомі/некоректні | Precision | Recall | Specificity | Accuracy | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

| Випадок | Evaluator | Архітектурний статус | Застосовність | Спостереження за повтореннями | У матриці |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(case_observations)}

Медіанний час підпроцесу становив {timing["AC_PUBLIC_API"]["median_ms"]} мс для `AC_PUBLIC_API` та {timing["AC_MODULE_GRAPH"]["median_ms"]} мс для `AC_MODULE_GRAPH` (відповідно {timing["AC_PUBLIC_API"]["n_completed"]} і {timing["AC_MODULE_GRAPH"]["n_completed"]} валідних завершених викликів). Час є описовим виміром запуску evaluator-а і не відображає часу виконання застосунку чи повного CI.

Результати `NOT_EVALUABLE`: `AC_PUBLIC_API` — {", ".join(f"`{item}`" for item in not_evaluable_cases["AC_PUBLIC_API"]) or "немає"}; `AC_MODULE_GRAPH` — {", ".join(f"`{item}`" for item in not_evaluable_cases["AC_MODULE_GRAPH"]) or "немає"}.

Динамічний імпорт приватного модуля є архітектурно неприпустимим за зареєстрованими API та графовою вимогами, однак обидва evaluator-и повернули вихід, передбачений для межі їхнього статичного аналізу, і не класифікували цей дефект. Ці спостереження виключено з бінарних метрик через `OUT_OF_SCOPE_DYNAMIC_IMPORT`. Зміна сигнатури на keyword-only порушує позиційний виклик у Reporting, але сигнатура не зафіксована у чинній конфігурації `AC_PUBLIC_API`; її архітектурну оцінку позначено як `INDETERMINATE`, а не як успіх чи помилку evaluator-а.

Отже, EVAL-02 розширює емпіричні спостереження для окремих статичних вихідних шаблонів, але не оцінює точність evaluator-ів у популяції архітектур. До використання цих evaluator-ів як єдиної підстави для твердження про архітектурну валідність у MONO-E1 потрібні додаткові перевірки механізмів поза межами прямого AST-імпорту; їхні поточні результати можуть застосовуватися лише як обмежене, прив'язане до джерела свідчення.
"""


def analyze_experiment(run_dir: Path, summary_dir: Path | None, package: Path | None) -> int:
    """Verify raw evidence, derive tables, and package the checksummed archive."""
    run_dir = run_dir.resolve()
    manifest_path = run_dir / "run-manifest.json"
    manifest = read_json(manifest_path)
    catalog = read_json(run_dir / "preregistration/mutation_catalog.json")
    integrity_errors = _validate_raw_inventory(run_dir, manifest)
    derived_runs, derivation_errors = _rederive_records(run_dir, manifest.get("runs", []))
    integrity_errors.extend(derivation_errors)
    case_results: dict[str, list[dict[str, Any]]] = {
        evaluator_id: [] for evaluator_id in EVALUATOR_IDS
    }
    repeat_count = int(catalog["execution_protocol"]["measured_repeats_per_case_evaluator"])
    for case in catalog["cases"]:
        for evaluator_id in EVALUATOR_IDS:
            row = analyze_case(case, evaluator_id, derived_runs, repeat_count, catalog)
            row["application_tree_sha"] = (
                manifest.get("cases", {}).get(case["case_id"], {}).get("application_tree_sha")
            )
            case_results[evaluator_id].append(row)
    metrics = {
        evaluator_id: confusion_metrics(case_results[evaluator_id])
        for evaluator_id in EVALUATOR_IDS
    }

    timing: dict[str, dict[str, Any]] = {}
    for evaluator_id in EVALUATOR_IDS:
        values = [
            float(item["wall_time_ms"])
            for item in derived_runs
            if item.get("evaluator_id") == evaluator_id
            and item.get("execution_status") == "COMPLETED"
            and item.get("target_source_sha") == item.get("source_commit_sha")
            and item.get("source_sha_status") == "MATCHED"
            and item.get("subject_source_dirty") is False
            and item.get("checkout_status_after") == "clean"
            and not item.get("launch_error")
            and not item.get("parse_error")
            and isinstance(item.get("wall_time_ms"), (int, float))
        ]
        timing[evaluator_id] = {
            "n_completed": len(values),
            "median_ms": round(statistics.median(values), 3) if values else None,
            "minimum_ms": round(min(values), 3) if values else None,
            "maximum_ms": round(max(values), 3) if values else None,
            "timing_unit": catalog["execution_protocol"]["timing_unit"],
        }

    analysis = {
        "schema_version": 1,
        "experiment_id": catalog["experiment_id"],
        "run_manifest_sha256_before_analysis": sha256_file(manifest_path),
        "raw_inventory_verification": "PASS" if not integrity_errors else "FAIL",
        "raw_inventory_errors": integrity_errors,
        "evaluator_case_results": case_results,
        "evaluator_metrics": metrics,
        "not_evaluable_case_ids_by_evaluator": {
            evaluator_id: [
                row["case_id"]
                for row in case_results[evaluator_id]
                if row["observed_compliance_case_level"] == "NOT_EVALUABLE"
            ]
            for evaluator_id in EVALUATOR_IDS
        },
        "descriptive_wall_time": timing,
        "repeats_are_independent_cases": False,
        "architectural_labels_source": "preregistered architecture_status_by_evaluator and evaluator applicability, independent of observed outputs",
    }
    analysis_path = run_dir / "EVAL02_ANALYSIS_V1.json"
    csv_path = run_dir / "EVAL02_CASE_RESULTS_V1.csv"
    report_path = run_dir / "EVAL02_REPORT_V1.md"
    manuscript_path = run_dir / "EVAL02_MANUSCRIPT_UA.md"
    write_json(analysis_path, analysis)
    csv_fields = [
        "case_id",
        "evaluator_id",
        "source_commit_sha",
        "application_tree_sha",
        "architectural_status",
        "evaluator_applicability",
        "expected_compliance",
        "observed_compliance_case_level",
        "observed_compliance_by_repeat",
        "expected_finding_codes",
        "observed_finding_codes_by_repeat",
        "planned_repeat_count",
        "completed_repeat_count",
        "provenance_valid",
        "preregistered_expected_outcome_matched",
        "metric_eligible_by_catalog",
        "valid_for_confusion_matrix",
        "exclusion_reasons",
        "case_median_wall_time_ms",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for evaluator_id in EVALUATOR_IDS:
            for row in case_results[evaluator_id]:
                writer.writerow(
                    {
                        **row,
                        "observed_compliance_by_repeat": json.dumps(
                            row["observed_compliance_by_repeat"]
                        ),
                        "expected_finding_codes": json.dumps(row["expected_finding_codes"]),
                        "observed_finding_codes_by_repeat": json.dumps(
                            row["observed_finding_codes_by_repeat"]
                        ),
                        "exclusion_reasons": json.dumps(row["exclusion_reasons"]),
                    }
                )
    report_path.write_text(
        _generate_report(catalog, manifest, case_results, metrics, timing, integrity_errors),
        encoding="utf-8",
    )
    manuscript_path.write_text(
        _generate_manuscript_ua(catalog, metrics, timing, case_results, manifest),
        encoding="utf-8",
    )
    output_paths = [analysis_path, csv_path, report_path, manuscript_path]
    manifest["analysis_artifacts_sha256"] = {path.name: sha256_file(path) for path in output_paths}
    manifest["analysis_raw_inventory_verification"] = analysis["raw_inventory_verification"]
    manifest["analysis_raw_inventory_errors"] = integrity_errors
    write_json(manifest_path, manifest)

    if summary_dir:
        summary_dir = summary_dir.resolve()
        summary_dir.mkdir(parents=True, exist_ok=True)
        for path in output_paths:
            shutil.copyfile(path, summary_dir / path.name)
    if package:
        package = package.resolve()
        package.parent.mkdir(parents=True, exist_ok=True)
        checksum_lines = [
            f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}"
            for path in sorted(run_dir.rglob("*"))
            if path.is_file() and path.name != "SHA256SUMS"
        ]
        (run_dir / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(run_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(run_dir).as_posix())
        package.with_suffix(package.suffix + ".sha256").write_text(
            f"{sha256_file(package)}  {package.name}\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "raw_inventory_verification": analysis["raw_inventory_verification"],
                "raw_inventory_errors": integrity_errors,
                "metrics": metrics,
                "failures": manifest.get("failures", []),
                "package": str(package.resolve()) if package else None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not integrity_errors else 1


def _parser() -> argparse.ArgumentParser:
    """Build the focused EVAL-02 command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preflight_parser = commands.add_parser(
        "preflight", help="validate mutations without evaluator calls"
    )
    preflight_parser.add_argument("--repo-root", type=Path, default=REPOSITORY_ROOT)
    execute_parser = commands.add_parser(
        "execute", help="run preregistered case/evaluator repetitions"
    )
    execute_parser.add_argument("--repo-root", type=Path, default=REPOSITORY_ROOT)
    execute_parser.add_argument("--output-dir", type=Path, required=True)
    analyze_parser = commands.add_parser(
        "analyze", help="verify, analyze, and package captured observations"
    )
    analyze_parser.add_argument("--run-dir", type=Path, required=True)
    analyze_parser.add_argument("--summary-dir", type=Path)
    analyze_parser.add_argument("--package", type=Path)
    return parser


def main() -> int:
    """Run the requested preflight, execution, or analysis stage."""
    args = _parser().parse_args()
    try:
        if args.command == "preflight":
            return preflight(args.repo_root.resolve())
        if args.command == "execute":
            return execute_experiment(args.repo_root, args.output_dir)
        return analyze_experiment(args.run_dir, args.summary_dir, args.package)
    except Exception as exc:
        print(f"EVAL-02 {args.command} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
