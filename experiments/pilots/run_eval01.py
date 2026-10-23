"""Run and analyze the preregistered EVAL-01 evaluator mutation experiment."""

# ruff: noqa: E501 -- embedded Markdown report prose stays unwrapped in this runner.

from __future__ import annotations

import argparse
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

GIT_EXECUTABLE = shutil.which("git")
if GIT_EXECUTABLE is None:
    raise RuntimeError("Git executable is required for EVAL-01")

SCRIPT_PATH = Path(__file__).resolve()
REPOSITORY_ROOT = SCRIPT_PATH.parents[2]
CATALOG_PATH = REPOSITORY_ROOT / "experiments/pilots/EVAL01_MUTATION_CATALOG_V1.json"
PROTOCOL_PATH = REPOSITORY_ROOT / "experiments/pilots/EVAL01_PROTOCOL_V1.md"
BASELINE_COMMIT = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
BASELINE_APP_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
STATE_NAME = "A0_4_REPORT_QUERY_PORT"
STATE_MANIFEST = "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
EVALUATOR_IDS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH")
EXPECTED_RETURN_CODES = {
    "COMPLIANT": 0,
    "NON_COMPLIANT": 1,
    "NOT_EVALUABLE": 2,
    "UNKNOWN": 2,
    "NOT_APPLICABLE": 3,
}
MUTATION_COMMIT_DATE = "2026-10-23T00:00:00+00:00"
AUTHOR_ENV = {
    "GIT_AUTHOR_NAME": "EVAL-01 Experimental Harness",
    "GIT_AUTHOR_EMAIL": "eval01@invalid.example",
    "GIT_COMMITTER_NAME": "EVAL-01 Experimental Harness",
    "GIT_COMMITTER_EMAIL": "eval01@invalid.example",
    "GIT_AUTHOR_DATE": MUTATION_COMMIT_DATE,
    "GIT_COMMITTER_DATE": MUTATION_COMMIT_DATE,
}


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 digest for bytes."""
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash one file without changing it."""
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    """Serialize JSON with the canonical form used by the evaluator engine."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def read_json(path: Path) -> Any:
    """Read a UTF-8 JSON document."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    """Write a stable, human-readable JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def run_git(repo_root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a Git command and return its text output."""
    result = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
        [
            GIT_EXECUTABLE,
            "-C",
            str(repo_root),
            *arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(arguments)} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result


def current_commit(repo_root: Path) -> str:
    """Return the checked-out Git commit."""
    return run_git(repo_root, "rev-parse", "HEAD").stdout.strip()


def complete_git_status(repo_root: Path) -> str:
    """Return the complete porcelain status, including untracked files."""
    return run_git(repo_root, "status", "--porcelain", "--untracked-files=all").stdout


def _replace_once(path: Path, old: str, new: str) -> None:
    """Replace exactly one declared source fragment or stop materialization."""
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise ValueError(f"Expected one mutation anchor in {path.relative_to(path.parents[2])}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def _append_type_checking_import(path: Path, import_statement: str) -> None:
    """Append one conditional source import that the AST evaluators still inspect."""
    source = path.read_text(encoding="utf-8")
    if "from typing import TYPE_CHECKING" in source:
        raise ValueError(f"Unexpected TYPE_CHECKING import already present in {path}")
    addition = (
        "\n\nfrom typing import TYPE_CHECKING\n\n"
        "if TYPE_CHECKING:\n"
        f"    {import_statement}\n"
    )
    path.write_text(source.rstrip() + addition, encoding="utf-8")


def apply_mutation(repo_root: Path, operation: str) -> None:
    """Apply one catalogued source-only mutation to a clean A0.4 checkout."""
    reporting_service = repo_root / "app/modules/reporting/service.py"
    tasks_service = repo_root / "app/modules/tasks/service.py"
    if operation == "replace_reporting_imports_with_public_module_alias":
        _replace_once(
            reporting_service,
            "from app.modules.tasks.public import TaskSummary\n"
            "from app.modules.tasks.public import get_task_summary as _get_task_summary\n",
            "from app.modules.tasks import public as tasks_public\n",
        )
        _replace_once(
            reporting_service,
            "def get_task_summary(session: Session) -> TaskSummary:",
            "def get_task_summary(session: Session) -> tasks_public.TaskSummary:",
        )
        _replace_once(
            reporting_service,
            "return _get_task_summary(session)",
            "return tasks_public.get_task_summary(session)",
        )
    elif operation == "replace_reporting_public_query_with_private_service_query":
        _replace_once(
            reporting_service,
            "from app.modules.tasks.public import get_task_summary as _get_task_summary",
            "from app.modules.tasks.service import task_summary as _get_task_summary",
        )
    elif operation == "add_type_only_undeclared_public_dependency":
        _append_type_checking_import(
            reporting_service,
            "from app.modules.users.public import user_exists as _validation_only_user_exists",
        )
    elif operation == "add_type_only_cycle_to_reporting":
        _append_type_checking_import(
            tasks_service,
            "from app.modules.reporting.public import get_task_summary as _reporting_summary",
        )
    elif operation == "add_type_only_unresolved_local_import":
        _append_type_checking_import(
            tasks_service,
            "from app.modules.tasks.unavailable import missing_symbol",
        )
    elif operation == "remove_expected_capability_audit":
        audit_path = repo_root / "app/modules/audit"
        if not audit_path.is_dir():
            raise ValueError("Expected Audit capability package is absent before mutation")
        run_git(repo_root, "rm", "-r", "--", "app/modules/audit")
    else:
        raise ValueError(f"Unknown EVAL-01 mutation operation: {operation}")


def evaluator_artifacts(repo_root: Path) -> tuple[list[dict[str, str]], str]:
    """Compute the exact aggregate evaluator source digest from a checkout."""
    evaluator_root = repo_root / "architecture/acceptance/a1"
    artifacts = [
        {"path": path.name, "sha256": sha256_file(path)}
        for path in sorted(evaluator_root.glob("*.py"))
    ]
    return artifacts, sha256_bytes(canonical_json(artifacts))


def validate_preregistration(repo_root: Path, catalog: dict[str, Any]) -> tuple[str, str, str]:
    """Require a clean descendant checkout and an unchanged preregistration commit."""
    if complete_git_status(repo_root).strip():
        raise RuntimeError("Subject repository must be completely clean before execution")
    head = current_commit(repo_root)
    catalog_relative = CATALOG_PATH.relative_to(repo_root).as_posix()
    preregistration = run_git(
        repo_root,
        "log",
        "-1",
        "--format=%H",
        "--",
        catalog_relative,
    ).stdout.strip()
    if not preregistration:
        raise RuntimeError("Committed preregistration revision is unavailable")
    parent = run_git(repo_root, "rev-parse", f"{preregistration}^").stdout.strip()
    if parent != catalog["experiment_base_main_sha"]:
        raise RuntimeError("Preregistration must be a direct child of the verified main commit")
    if run_git(repo_root, "merge-base", "--is-ancestor", preregistration, head, check=False).returncode != 0:
        raise RuntimeError("Current experiment revision must descend from preregistration")
    if run_git(repo_root, "merge-base", "--is-ancestor", BASELINE_COMMIT, head, check=False).returncode != 0:
        raise RuntimeError("Canonical A0.4 baseline is not an ancestor of the experiment branch")
    if run_git(repo_root, "rev-parse", f"{BASELINE_COMMIT}:app").stdout.strip() != BASELINE_APP_TREE:
        raise RuntimeError("Canonical A0.4 application tree SHA mismatch")
    if run_git(repo_root, "cat-file", "-e", f"{BASELINE_COMMIT}^{{commit}}", check=False).returncode != 0:
        raise RuntimeError("Canonical A0.4 commit object is unavailable")
    return head, preregistration, sha256_file(CATALOG_PATH)


def materialize_case(
    repo_root: Path,
    case: dict[str, Any],
    case_root: Path,
    evidence_case_root: Path,
    expected_evaluator_digest: str,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    """Create a case-specific disposable Git revision and preserve its provenance."""
    case_root.parent.mkdir(parents=True, exist_ok=True)
    evidence_case_root.mkdir(parents=True, exist_ok=True)
    clone = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
        [
            GIT_EXECUTABLE,
            "clone",
            "--shared",
            "--no-checkout",
            str(repo_root),
            str(case_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if clone.returncode != 0:
        raise RuntimeError(f"clone failed: {clone.stderr.strip()}")
    run_git(case_root, "checkout", "--detach", BASELINE_COMMIT)
    if run_git(case_root, "rev-parse", "HEAD:app").stdout.strip() != BASELINE_APP_TREE:
        raise RuntimeError("Materialized base application tree SHA mismatch")
    if complete_git_status(case_root).strip():
        raise RuntimeError("Baseline checkout is not clean")

    if case["mutation"] != "none":
        apply_mutation(case_root, case["mutation"])
        staged = run_git(case_root, "status", "--porcelain", "--untracked-files=all").stdout
        if not staged.strip():
            raise RuntimeError("Mutation did not change the source checkout")
        git_env = os.environ.copy()
        git_env.update(AUTHOR_ENV)
        commit = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
            [
                GIT_EXECUTABLE,
                "-C",
                str(case_root),
                "-c",
                "user.name=EVAL-01 Experimental Harness",
                "-c",
                "user.email=eval01@invalid.example",
                "add",
                "--",
                "app",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=git_env,
        )
        if commit.returncode != 0:
            raise RuntimeError(f"git add failed: {commit.stderr.strip()}")
        commit = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
            [
                GIT_EXECUTABLE,
                "-C",
                str(case_root),
                "-c",
                "user.name=EVAL-01 Experimental Harness",
                "-c",
                "user.email=eval01@invalid.example",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                f"EVAL-01 {case['case_id']} mutation v1.0.0",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=git_env,
        )
        if commit.returncode != 0:
            raise RuntimeError(f"git commit failed: {commit.stderr.strip()}")

    source_sha = current_commit(case_root)
    parent_line = run_git(case_root, "rev-list", "--parents", "-n", "1", source_sha).stdout.split()
    is_mutation = case["mutation"] != "none"
    if is_mutation and parent_line != [source_sha, BASELINE_COMMIT]:
        raise RuntimeError("Mutation commit is not a direct child of canonical A0.4")
    if not is_mutation and source_sha != BASELINE_COMMIT:
        raise RuntimeError("Clean control does not use the exact canonical A0.4 revision")
    if complete_git_status(case_root).strip():
        raise RuntimeError("Provenance-bound case checkout is not clean after commit")

    app_tree = run_git(case_root, "rev-parse", "HEAD:app").stdout.strip()
    repository_tree = run_git(case_root, "rev-parse", "HEAD^{tree}").stdout.strip()
    patch_result = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
        [
            GIT_EXECUTABLE,
            "-C",
            str(case_root),
            "diff",
            "--binary",
            "--no-ext-diff",
            "--no-renames",
            BASELINE_COMMIT,
            source_sha,
            "--",
            "app",
        ],
        check=False,
        capture_output=True,
    )
    if patch_result.returncode != 0:
        raise RuntimeError("Could not preserve the source mutation patch")
    patch_path = evidence_case_root / "mutation.patch"
    patch_path.write_bytes(patch_result.stdout)
    bundle_path: Path | None = None
    if is_mutation:
        bundle_path = evidence_case_root / "mutation.bundle"
        bundle = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
            [
                GIT_EXECUTABLE,
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
        if bundle.returncode != 0:
            raise RuntimeError(f"git bundle failed: {bundle.stderr.strip()}")
        verify_bundle = subprocess.run(  # noqa: S603 - fixed Git argv; no shell
            [
                GIT_EXECUTABLE,
                "bundle",
                "verify",
                str(bundle_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=case_root,
        )
        if verify_bundle.returncode != 0:
            raise RuntimeError(f"mutation bundle verification failed: {verify_bundle.stderr.strip()}")

    frozen_input_digests: dict[str, str] | None = None
    if case["case_id"] == "clean_unchanged_dependencies":
        frozen_input_digests = copy_frozen_inputs(
            case_root, evidence_case_root.parent.parent, repo_root, catalog["experiment_base_main_sha"], catalog
        )
        artifacts, observed_digest = evaluator_artifacts(case_root)
        if observed_digest != expected_evaluator_digest:
            raise RuntimeError("A0.4 evaluator source digest differs from preregistered digest")
        for evaluator in EVALUATOR_IDS:
            config = case_root / catalog_config_path(evaluator)
            expected_config_digest = catalog_config_digest(evaluator)
            if sha256_file(config) != expected_config_digest:
                raise RuntimeError(f"{evaluator} configuration digest differs from preregistration")
        if not artifacts:
            raise RuntimeError("No evaluator source artifacts found in baseline checkout")

    return {
        "case_id": case["case_id"],
        "mutation": case["mutation"],
        "source_commit_sha": source_sha,
        "source_parent_shas": parent_line[1:],
        "repository_tree_sha": repository_tree,
        "application_tree_sha": app_tree,
        "is_mutation_revision": is_mutation,
        "complete_git_status_before_evaluation": "clean",
        "mutation_patch_path": patch_path.relative_to(evidence_case_root.parent.parent).as_posix(),
        "mutation_patch_sha256": sha256_file(patch_path),
        "mutation_bundle_path": bundle_path.relative_to(evidence_case_root.parent.parent).as_posix()
        if bundle_path
        else None,
        "mutation_bundle_sha256": sha256_file(bundle_path) if bundle_path else None,
        "frozen_input_digests": frozen_input_digests,
    }


def catalog_config_path(evaluator_id: str) -> str:
    """Return the catalogued relative configuration path."""
    return read_json(CATALOG_PATH)["evaluators"][evaluator_id]["configuration"]


def catalog_config_digest(evaluator_id: str) -> str:
    """Return the preregistered configuration digest."""
    return read_json(CATALOG_PATH)["evaluators"][evaluator_id]["configuration_sha256"]


def copy_frozen_inputs(
    base_checkout: Path, evidence_root: Path, experiment_root: Path, main_sha: str, catalog: dict[str, Any]
) -> dict[str, Any]:
    """Copy evaluator inputs from A0.4 and identity-only checkpoint evidence from main."""
    relative_paths = [
        "architecture/acceptance/a1/__init__.py",
        "architecture/acceptance/a1/analyzers.py",
        "architecture/acceptance/a1/cli.py",
        "architecture/acceptance/a1/engine.py",
        "architecture/acceptance/a1/public_api_v1.yaml",
        "architecture/acceptance/a1/module_graph_v1.yaml",
        "architecture/acceptance/a1/a0_4_canonical_checkpoint.json",
        "architecture/acceptance/a1/a0_4_canonical_source_manifest.yaml",
        STATE_MANIFEST,
    ]
    frozen_root = evidence_root / "frozen_inputs"
    digests: dict[str, str] = {}
    source_revisions: dict[str, str] = {}
    identity_only = {
        catalog["canonical_a04_checkpoint_reference"]["path"]: catalog["canonical_a04_checkpoint_reference"]["sha256"],
        catalog["canonical_a04_source_manifest_reference"]["path"]: catalog["canonical_a04_source_manifest_reference"]["sha256"],
    }
    for relative in relative_paths:
        is_identity_only = relative in identity_only
        source_root = experiment_root if is_identity_only else base_checkout
        source = source_root / relative
        if not source.is_file():
            raise RuntimeError(f"Frozen input missing at declared source revision: {relative}")
        if is_identity_only:
            if sha256_file(source) != identity_only[relative]:
                raise RuntimeError(f"Canonical checkpoint evidence digest mismatch: {relative}")
            main_blob = run_git(experiment_root, "rev-parse", f"{main_sha}:{relative}").stdout.strip()
            head_blob = run_git(experiment_root, "rev-parse", f"HEAD:{relative}").stdout.strip()
            if not main_blob or main_blob != head_blob:
                raise RuntimeError(f"Canonical identity evidence differs from verified main: {relative}")
            source_revisions[relative] = main_sha
        else:
            source_revisions[relative] = BASELINE_COMMIT
        target = frozen_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        digests[relative] = sha256_file(target)
    return {"sha256": digests, "source_commit_by_path": source_revisions}


def check_observation(
    evidence: dict[str, Any],
    case: dict[str, Any],
    evaluator_id: str,
    expected_source_sha: str,
    source_status_after: str,
    catalog: dict[str, Any],
) -> list[str]:
    """Compare one observation to provenance and preregistered expectations."""
    failures: list[str] = []
    evaluator_expected = catalog["evaluators"][evaluator_id]
    expected = case["expected_by_evaluator"][evaluator_id]
    if evidence.get("evaluator", {}).get("version") != evaluator_expected["version"]:
        failures.append("EVALUATOR_VERSION_MISMATCH")
    if evidence.get("evaluator", {}).get("configuration_digest") != evaluator_expected[
        "configuration_sha256"
    ]:
        failures.append("CONFIGURATION_DIGEST_MISMATCH")
    if evidence.get("evaluator", {}).get("source_digest") != evaluator_expected[
        "expected_source_artifact_digest"
    ]:
        failures.append("EVALUATOR_SOURCE_DIGEST_MISMATCH")
    architecture = evidence.get("architecture", {})
    if architecture.get("target_source_sha") != expected_source_sha:
        failures.append("TARGET_SOURCE_SHA_MISMATCH")
    if architecture.get("expected_source_sha") != expected_source_sha:
        failures.append("EXPECTED_SOURCE_SHA_MISMATCH")
    if architecture.get("source_sha_status") != "MATCHED":
        failures.append("SOURCE_IDENTITY_NOT_MATCHED")
    if architecture.get("subject_source_dirty") is not False:
        failures.append("SUBJECT_SOURCE_NOT_CLEAN")
    if source_status_after:
        failures.append("CHECKOUT_DIRTY_AFTER_EVALUATION")
    if evidence.get("architecture", {}).get("state") != STATE_NAME:
        failures.append("ARCHITECTURE_STATE_MISMATCH")
    if evidence.get("result", {}).get("execution_status") != "COMPLETED":
        failures.append("EVALUATOR_EXECUTION_NOT_COMPLETED")
    if evidence.get("result", {}).get("compliance") != expected["compliance"]:
        failures.append("COMPLIANCE_OUTCOME_MISMATCH")

    diagnostics = evidence.get("diagnostics", {})
    observed_codes = sorted(
        {
            str(item.get("code"))
            for item in diagnostics.get("observed_policy_findings", [])
            if isinstance(item, dict) and item.get("code")
        }
    )
    if observed_codes != sorted(expected["finding_codes"]):
        failures.append("FINDING_CLASS_MISMATCH")
    scope = evidence.get("source_scope", {})
    if scope.get("complete") is not case.get("expected_scope_complete"):
        failures.append("SOURCE_SCOPE_COMPLETENESS_MISMATCH")
    missing_uncertainties = set(case.get("expected_scope_uncertainties", [])) - set(
        scope.get("uncertainties", [])
    )
    if missing_uncertainties:
        failures.append("EXPECTED_SCOPE_UNCERTAINTY_MISSING")
    if evaluator_id == "AC_MODULE_GRAPH":
        if len(diagnostics.get("cycles", [])) != case.get("expected_cycle_count", 0):
            failures.append("CYCLE_COUNT_MISMATCH")
        unresolved_count = len(diagnostics.get("unresolved_capability_imports", [])) + len(
            diagnostics.get("unresolved_local_imports", [])
        )
        if unresolved_count != case.get("expected_unresolved_import_count", unresolved_count):
            failures.append("UNRESOLVED_IMPORT_COUNT_MISMATCH")
        if "expected_declared_edges" in case:
            edge_pairs = sorted(
                [str(edge["from"]), str(edge["to"])] for edge in diagnostics.get("edges", [])
            )
            if edge_pairs != sorted(case["expected_declared_edges"]):
                failures.append("DECLARED_EDGE_SET_MISMATCH")
    return failures


def append_event(path: Path, event: dict[str, Any]) -> None:
    """Append one JSON object to the human-readable execution log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")


def execute_experiment(args: argparse.Namespace) -> int:
    """Materialize all preregistered cases, run 42 evaluator calls, and save evidence."""
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError(f"Output directory already exists: {output_dir}")
    catalog = read_json(CATALOG_PATH)
    head, preregistration_commit, catalog_sha = validate_preregistration(repo_root, catalog)
    artifacts, evaluator_digest = evaluator_artifacts(repo_root)
    if not artifacts:
        raise RuntimeError("No evaluator artifacts are available")
    for evaluator_id in EVALUATOR_IDS:
        config_path = repo_root / catalog["evaluators"][evaluator_id]["configuration"]
        if sha256_file(config_path) != catalog["evaluators"][evaluator_id]["configuration_sha256"]:
            raise RuntimeError(f"{evaluator_id} configuration changed after preregistration")
        if evaluator_digest != catalog["evaluators"][evaluator_id]["expected_source_artifact_digest"]:
            raise RuntimeError(f"{evaluator_id} evaluator source changed after preregistration")

    output_dir.mkdir(parents=True)
    (output_dir / "preregistration").mkdir()
    shutil.copyfile(CATALOG_PATH, output_dir / "preregistration/mutation_catalog.json")
    shutil.copyfile(PROTOCOL_PATH, output_dir / "preregistration/protocol.md")
    shutil.copyfile(SCRIPT_PATH, output_dir / "preregistration/run_eval01.py")
    write_json(output_dir / "preregistration/evaluator_artifacts.json", artifacts)

    python_yaml_version = "unavailable"
    try:
        import yaml

        python_yaml_version = str(yaml.__version__)
    except ImportError:
        pass

    cases = catalog["cases"]
    repeat_count = int(catalog["execution_protocol"]["measured_repeats_per_case_evaluator"])
    schedule: list[dict[str, Any]] = [
        {"case_id": case["case_id"], "evaluator_id": evaluator, "repeat": repeat}
        for case in cases
        for evaluator in EVALUATOR_IDS
        for repeat in range(1, repeat_count + 1)
    ]
    random.Random(  # noqa: S311 - preregistered deterministic execution order, no security use
        int(catalog["execution_protocol"]["schedule_seed"])
    ).shuffle(schedule)
    write_json(output_dir / "schedule.json", schedule)

    failures: list[dict[str, Any]] = []
    case_provenance: dict[str, dict[str, Any]] = {}
    run_records: list[dict[str, Any]] = []
    event_log = output_dir / "execution.jsonl"
    with tempfile.TemporaryDirectory(prefix="eval01-mutations-") as temporary_root:
        temporary_path = Path(temporary_root)
        case_paths: dict[str, Path] = {}
        for case in cases:
            case_checkout = temporary_path / case["case_id"]
            evidence_case_root = output_dir / "cases" / case["case_id"]
            try:
                provenance = materialize_case(
                    repo_root,
                    case,
                    case_checkout,
                    evidence_case_root,
                    evaluator_digest,
                    catalog,
                )
                case_provenance[case["case_id"]] = provenance
                case_paths[case["case_id"]] = case_checkout
            except Exception as exc:  # retain a failed case instead of silently dropping it
                failure = {
                    "case_id": case["case_id"],
                    "stage": "materialization",
                    "detail": f"{type(exc).__name__}: {exc}",
                }
                failures.append(failure)
                case_provenance[case["case_id"]] = {"materialization_failure": failure["detail"]}

        for index, scheduled in enumerate(schedule, start=1):
            case = next(item for item in cases if item["case_id"] == scheduled["case_id"])
            evaluator_id = scheduled["evaluator_id"]
            case_path = case_paths.get(case["case_id"])
            source_sha = case_provenance[case["case_id"]].get("source_commit_sha")
            expected = case["expected_by_evaluator"][evaluator_id]
            run_dir = output_dir / "runs" / case["case_id"] / evaluator_id / f"repeat-{scheduled['repeat']}"
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
            start_utc = datetime.now(UTC).isoformat()
            started_ns = time.perf_counter_ns()
            return_code: int | None = None
            launch_error: str | None = None
            stdout = b""
            stderr = b""
            checkout_dirty_after = "not_run"
            observation: dict[str, Any] | None = None
            parse_error: str | None = None
            if case_path is None:
                launch_error = "CASE_MATERIALIZATION_FAILED"
                stderr = case_provenance[case["case_id"]]["materialization_failure"].encode()
            else:
                try:
                    if current_commit(case_path) != source_sha:
                        raise RuntimeError("HEAD changed after case materialization")
                    dirty_before = complete_git_status(case_path)
                    if dirty_before.strip():
                        raise RuntimeError("case checkout is dirty before evaluator invocation")
                    process = subprocess.run(  # noqa: S603 - fixed interpreter/evaluator argv
                        command,
                        cwd=case_path,
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    stdout = process.stdout
                    stderr = process.stderr
                    return_code = process.returncode
                    checkout_dirty_after = complete_git_status(case_path)
                    if stdout:
                        try:
                            observation = json.loads(stdout.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                            parse_error = f"{type(exc).__name__}: {exc}"
                except subprocess.TimeoutExpired as exc:
                    stdout = exc.stdout if isinstance(exc.stdout, bytes) else b""
                    stderr = exc.stderr if isinstance(exc.stderr, bytes) else b""
                    launch_error = "EVALUATOR_TIMEOUT_120_SECONDS"
                except Exception as exc:  # preserve the failed call as an explicit observation
                    launch_error = f"{type(exc).__name__}: {exc}"
                    stderr = str(exc).encode("utf-8")
            elapsed_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
            end_utc = datetime.now(UTC).isoformat()
            stdout_path.write_bytes(stdout)
            stderr_path.write_bytes(stderr)
            run_record = {
                **scheduled,
                "schedule_index": index,
                "source_commit_sha": source_sha,
                "command": command,
                "working_directory": str(case_path) if case_path else None,
                "started_at_utc": start_utc,
                "ended_at_utc": end_utc,
                "wall_time_ms": round(elapsed_ms, 6),
                "return_code": return_code,
                "launch_error": launch_error,
                "parse_error": parse_error,
                "stdout_path": stdout_path.relative_to(output_dir).as_posix(),
                "stdout_sha256": sha256_file(stdout_path),
                "stderr_path": stderr_path.relative_to(output_dir).as_posix(),
                "stderr_sha256": sha256_file(stderr_path),
                "checkout_status_after": checkout_dirty_after.strip() or "clean",
            }
            if observation is not None:
                finding_codes = sorted(
                    {
                        str(item.get("code"))
                        for item in observation.get("diagnostics", {}).get(
                            "observed_policy_findings", []
                        )
                        if isinstance(item, dict) and item.get("code")
                    }
                )
                run_record.update(
                    {
                        "observed_compliance": observation.get("result", {}).get("compliance"),
                        "execution_status": observation.get("result", {}).get("execution_status"),
                        "finding_codes": finding_codes,
                        "target_source_sha": observation.get("architecture", {}).get(
                            "target_source_sha"
                        ),
                        "expected_source_sha": observation.get("architecture", {}).get(
                            "expected_source_sha"
                        ),
                        "source_sha_status": observation.get("architecture", {}).get(
                            "source_sha_status"
                        ),
                        "subject_source_dirty": observation.get("architecture", {}).get(
                            "subject_source_dirty"
                        ),
                        "source_scope_complete": observation.get("source_scope", {}).get(
                            "complete"
                        ),
                        "inspected_file_count": len(
                            observation.get("source_scope", {}).get("inspected_paths", [])
                        ),
                        "evaluator_version": observation.get("evaluator", {}).get("version"),
                        "evaluator_source_digest": observation.get("evaluator", {}).get(
                            "source_digest"
                        ),
                        "configuration_digest": observation.get("evaluator", {}).get(
                            "configuration_digest"
                        ),
                        "raw_diagnostics_digest": observation.get("raw_output", {}).get(
                            "sha256"
                        ),
                    }
                )
                validation_failures = check_observation(
                    observation,
                    case,
                    evaluator_id,
                    str(source_sha),
                    checkout_dirty_after.strip(),
                    catalog,
                )
                expected_return = EXPECTED_RETURN_CODES[expected["compliance"]]
                if return_code != expected_return:
                    validation_failures.append("RETURN_CODE_MISMATCH")
                for failure_code in validation_failures:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "evaluator_id": evaluator_id,
                            "repeat": scheduled["repeat"],
                            "stage": "observation_validation",
                            "detail": failure_code,
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
            run_records.append(run_record)
            append_event(event_log, run_record)

    raw_artifacts = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "run-manifest.json":
            raw_artifacts[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    manifest = {
        "schema_version": 1,
        "experiment_id": catalog["experiment_id"],
        "protocol_version": "1.0.0",
        "catalog_version": catalog["catalog_version"],
        "registered_at_utc": run_git(repo_root, "show", "-s", "--format=%cI", preregistration_commit).stdout.strip(),
        "preregistration_commit_sha": preregistration_commit,
        "preregistration_catalog_sha256": catalog_sha,
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
            "yaml_version": python_yaml_version,
            "yaml_module_path": str(getattr(sys.modules.get("yaml"), "__file__", "unavailable")),
            "platform": platform.platform(),
            "schedule_seed": catalog["execution_protocol"]["schedule_seed"],
            "repeat_count": repeat_count,
            "planned_evaluator_calls": len(schedule),
            "measured_schedule": "schedule.json",
        },
        "cases": case_provenance,
        "runs": run_records,
        "failures": failures,
        "raw_artifacts_sha256": raw_artifacts,
        "started_at_utc": min(
            (item["started_at_utc"] for item in run_records), default=None
        ),
        "completed_at_utc": max(
            (item["ended_at_utc"] for item in run_records), default=None
        ),
    }
    write_json(output_dir / "run-manifest.json", manifest)
    print(json.dumps({"run_dir": str(output_dir), "run_count": len(run_records), "failure_count": len(failures)}, indent=2))
    return 0 if not failures and len(run_records) == len(schedule) else 1


def _percentage(numerator: int, denominator: int) -> float | None:
    """Return a ratio or None when its denominator is empty."""
    return numerator / denominator if denominator else None


def _metric_string(value: float | None) -> str:
    """Format a derived metric without inventing a value for undefined ratios."""
    return "NOT_DEFINED" if value is None else f"{value:.3f}"


def _validate_raw_inventory(run_dir: Path, manifest: dict[str, Any]) -> list[str]:
    """Verify every captured raw artifact against its run-manifest digest."""
    errors: list[str] = []
    expected = manifest.get("raw_artifacts_sha256", {})
    post_analysis_names = {
        "EVAL01_ANALYSIS_V1.json",
        "EVAL01_CASE_RESULTS_V1.csv",
        "EVAL01_REPORT_V1.md",
        "SHA256SUMS",
    }
    observed_files = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name not in post_analysis_names | {"run-manifest.json"}
    }
    if observed_files != set(expected):
        errors.append("RAW_ARTIFACT_INVENTORY_MISMATCH")
    for relative, digest in expected.items():
        path = run_dir / relative
        if not path.is_file() or sha256_file(path) != digest:
            errors.append(f"RAW_ARTIFACT_DIGEST_MISMATCH:{relative}")
    return errors


def _rederive_run_records_from_stdout(
    run_dir: Path, run_records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Recompute observation fields from preserved stdout instead of trusting the run index."""
    derived_records: list[dict[str, Any]] = []
    errors: list[str] = []
    fields = {
        "observed_compliance": lambda value: value.get("result", {}).get("compliance"),
        "execution_status": lambda value: value.get("result", {}).get("execution_status"),
        "target_source_sha": lambda value: value.get("architecture", {}).get("target_source_sha"),
        "expected_source_sha": lambda value: value.get("architecture", {}).get("expected_source_sha"),
        "source_sha_status": lambda value: value.get("architecture", {}).get("source_sha_status"),
        "subject_source_dirty": lambda value: value.get("architecture", {}).get("subject_source_dirty"),
        "source_scope_complete": lambda value: value.get("source_scope", {}).get("complete"),
        "evaluator_version": lambda value: value.get("evaluator", {}).get("version"),
        "evaluator_source_digest": lambda value: value.get("evaluator", {}).get("source_digest"),
        "configuration_digest": lambda value: value.get("evaluator", {}).get("configuration_digest"),
        "raw_diagnostics_digest": lambda value: value.get("raw_output", {}).get("sha256"),
    }
    for record in run_records:
        copied = dict(record)
        stdout_path = run_dir / str(record.get("stdout_path", ""))
        if not stdout_path.is_file():
            errors.append(f"RAW_STDOUT_MISSING:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}")
            derived_records.append(copied)
            continue
        if sha256_file(stdout_path) != record.get("stdout_sha256"):
            errors.append(f"STDOUT_DIGEST_INDEX_MISMATCH:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}")
        stderr_path = run_dir / str(record.get("stderr_path", ""))
        if not stderr_path.is_file() or sha256_file(stderr_path) != record.get("stderr_sha256"):
            errors.append(f"STDERR_DIGEST_INDEX_MISMATCH:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}")
        try:
            observed = json.loads(stdout_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            derived_records.append(copied)
            continue
        for field, getter in fields.items():
            value = getter(observed)
            if value != record.get(field):
                errors.append(
                    f"RUN_INDEX_DERIVATION_MISMATCH:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}:{field}"
                )
            copied[field] = value
        derived_codes = sorted(
            {
                str(item.get("code"))
                for item in observed.get("diagnostics", {}).get("observed_policy_findings", [])
                if isinstance(item, dict) and item.get("code")
            }
        )
        if derived_codes != record.get("finding_codes"):
            errors.append(
                f"RUN_INDEX_DERIVATION_MISMATCH:{record.get('case_id')}:{record.get('evaluator_id')}:{record.get('repeat')}:finding_codes"
            )
        copied["finding_codes"] = derived_codes
        copied["inspected_file_count"] = len(observed.get("source_scope", {}).get("inspected_paths", []))
        derived_records.append(copied)
    return derived_records, errors


def analyze_case(
    case: dict[str, Any],
    evaluator_id: str,
    run_records: list[dict[str, Any]],
    repeat_count: int,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    """Collapse repeated timings to one source-case outcome without pooling repeats."""
    expected = case["expected_by_evaluator"][evaluator_id]
    selected = sorted(
        [
            item
            for item in run_records
            if item.get("case_id") == case["case_id"]
            and item.get("evaluator_id") == evaluator_id
        ],
        key=lambda item: int(item.get("repeat", 0)),
    )
    statuses = [item.get("observed_compliance") for item in selected]
    codes = [item.get("finding_codes", []) for item in selected]
    provenance_valid = len(selected) == repeat_count and all(
        not item.get("launch_error")
        and not item.get("parse_error")
        and item.get("execution_status") == "COMPLETED"
        and item.get("target_source_sha") == item.get("source_commit_sha")
        and item.get("expected_source_sha") == item.get("source_commit_sha")
        and item.get("source_sha_status") == "MATCHED"
        and item.get("subject_source_dirty") is False
        and item.get("checkout_status_after") == "clean"
        and item.get("evaluator_version") == catalog["evaluators"][evaluator_id]["version"]
        and item.get("evaluator_source_digest")
        == catalog["evaluators"][evaluator_id]["expected_source_artifact_digest"]
        and item.get("configuration_digest")
        == catalog["evaluators"][evaluator_id]["configuration_sha256"]
        and item.get("return_code") == EXPECTED_RETURN_CODES.get(item.get("observed_compliance"))
        for item in selected
    )
    repeat_status_stable = bool(statuses) and len(set(statuses)) == 1
    repeat_findings_stable = bool(codes) and len({tuple(value) for value in codes}) == 1
    eligible = bool(case.get("metric_eligible")) and expected.get("architectural_label") in {0, 1}
    observed = statuses[0] if repeat_status_stable else None
    metric_included = (
        eligible
        and provenance_valid
        and repeat_status_stable
        and observed in {"COMPLIANT", "NON_COMPLIANT"}
    )
    exclusion_reasons: list[str] = []
    if not eligible:
        exclusion_reasons.append(case.get("exclusion_reason", "PREREGISTERED_NON_BINARY_CASE"))
    if not provenance_valid:
        exclusion_reasons.append("REPEATED_RUN_PROVENANCE_OR_EXECUTION_INCOMPLETE")
    if not repeat_status_stable:
        exclusion_reasons.append("REPEATED_COMPLIANCE_OUTCOMES_NOT_STABLE")
    if eligible and repeat_status_stable and observed not in {"COMPLIANT", "NON_COMPLIANT"}:
        exclusion_reasons.append("OBSERVED_UNKNOWN_OR_NOT_EVALUABLE")
    return {
        "case_id": case["case_id"],
        "evaluator_id": evaluator_id,
        "expected_compliance": expected["compliance"],
        "expected_architectural_label": expected.get("architectural_label"),
        "expected_finding_codes": sorted(expected.get("finding_codes", [])),
        "observed_compliance_by_repeat": statuses,
        "observed_finding_codes_by_repeat": codes,
        "observed_compliance_case_level": observed if repeat_status_stable else "UNKNOWN",
        "observed_finding_classes_stable": repeat_findings_stable,
        "preregistered_expected_outcome_matched": (
            len(selected) == repeat_count
            and all(
                item.get("observed_compliance") == expected["compliance"]
                and item.get("finding_codes", []) == sorted(expected.get("finding_codes", []))
                for item in selected
            )
        ),
        "planned_repeat_count": repeat_count,
        "completed_repeat_count": len(selected),
        "metric_eligible_by_catalog": eligible,
        "valid_for_confusion_matrix": metric_included,
        "exclusion_reasons": exclusion_reasons,
        "source_commit_sha": selected[0].get("source_commit_sha") if selected else None,
        "application_tree_sha": None,
        "case_wall_time_ms": [item.get("wall_time_ms") for item in selected],
        "case_median_wall_time_ms": statistics.median(
            [float(item["wall_time_ms"]) for item in selected if isinstance(item.get("wall_time_ms"), (int, float))]
        )
        if any(isinstance(item.get("wall_time_ms"), (int, float)) for item in selected)
        else None,
    }


def confusion_metrics(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute finite case-level detection counts from valid labeled conditions."""
    included = [item for item in case_rows if item["valid_for_confusion_matrix"]]
    counts = Counter()
    for item in included:
        actual_positive = item["expected_architectural_label"] == 1
        detected_positive = item["observed_compliance_case_level"] == "NON_COMPLIANT"
        if actual_positive and detected_positive:
            counts["tp"] += 1
        elif actual_positive:
            counts["fn"] += 1
        elif detected_positive:
            counts["fp"] += 1
        else:
            counts["tn"] += 1
    tp, fp, tn, fn = (counts[name] for name in ("tp", "fp", "tn", "fn"))
    precision = _percentage(tp, tp + fp)
    recall = _percentage(tp, tp + fn)
    specificity = _percentage(tn, tn + fp)
    accuracy = _percentage(tp + tn, len(included))
    f1 = _percentage(2 * tp, 2 * tp + fp + fn)
    eligible_count = sum(1 for item in case_rows if item["metric_eligible_by_catalog"])
    return {
        "unit": "one independently specified evaluator-by-source-case condition",
        "eligible_labeled_cases": eligible_count,
        "evaluable_labeled_cases": len(included),
        "unknown_or_invalid_labeled_cases": eligible_count - len(included),
        "not_evaluable_catalog_cases": sum(1 for item in case_rows if not item["metric_eligible_by_catalog"]),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": precision,
        "recall_sensitivity": recall,
        "specificity": specificity,
        "accuracy": accuracy,
        "f1": f1,
    }


def _format_confusion_table(metrics_by_evaluator: dict[str, Any]) -> str:
    """Render confusion counts and finite case-level metrics as Markdown."""
    lines = [
        "| Evaluator | TP | FP | TN | FN | Labeled/evaluable | Unknown or invalid | Precision | Recall | Specificity | Accuracy | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for evaluator_id in EVALUATOR_IDS:
        metrics = metrics_by_evaluator[evaluator_id]
        counts = metrics["confusion_matrix"]
        lines.append(
            "| {evaluator} | {tp} | {fp} | {tn} | {fn} | {evaluated}/{eligible} | {unknown} | "
            "{precision} | {recall} | {specificity} | {accuracy} | {f1} |".format(
                evaluator=evaluator_id,
                tp=counts["tp"],
                fp=counts["fp"],
                tn=counts["tn"],
                fn=counts["fn"],
                evaluated=metrics["evaluable_labeled_cases"],
                eligible=metrics["eligible_labeled_cases"],
                unknown=metrics["unknown_or_invalid_labeled_cases"],
                precision=_metric_string(metrics["precision"]),
                recall=_metric_string(metrics["recall_sensitivity"]),
                specificity=_metric_string(metrics["specificity"]),
                accuracy=_metric_string(metrics["accuracy"]),
                f1=_metric_string(metrics["f1"]),
            )
        )
    return "\n".join(lines)


def _generate_report(
    catalog: dict[str, Any],
    manifest: dict[str, Any],
    case_results: dict[str, list[dict[str, Any]]],
    metrics_by_evaluator: dict[str, Any],
    timing_by_evaluator: dict[str, dict[str, Any]],
    raw_errors: list[str],
) -> str:
    """Render the scientific report only from preregistered inputs and captured output."""
    cases_table = [
        "| Case | Evaluator | Expected | Observed by repeat | Finding classes | Metric status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in catalog["cases"]:
        for evaluator_id in EVALUATOR_IDS:
            row = next(item for item in case_results[evaluator_id] if item["case_id"] == case["case_id"])
            repeats = ", ".join(str(item) for item in row["observed_compliance_by_repeat"]) or "NO_OBSERVATIONS"
            findings = "; ".join(
                ", ".join(codes) if codes else "none"
                for codes in row["observed_finding_codes_by_repeat"]
            ) or "none"
            metric = "included" if row["valid_for_confusion_matrix"] else "excluded: " + "; ".join(row["exclusion_reasons"])
            cases_table.append(
                f"| `{case['case_id']}` | `{evaluator_id}` | `{row['expected_compliance']}` | {repeats} | {findings} | {metric} |"
            )
    timing_lines = [
        "| Evaluator | Valid completed calls | Median ms | Minimum ms | Maximum ms |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for evaluator_id in EVALUATOR_IDS:
        item = timing_by_evaluator[evaluator_id]
        timing_lines.append(
            f"| `{evaluator_id}` | {item['n_completed']} | {item['median_ms']} | {item['minimum_ms']} | {item['maximum_ms']} |"
        )
    failure_lines = (
        "\n".join(f"- `{failure}`" for failure in raw_errors)
        if raw_errors
        else "- No provenance, execution, outcome, or artifact-integrity failures were recorded."
    )
    failures = manifest.get("failures", [])
    run_failures = (
        "\n".join(
            f"- `{item.get('case_id', 'unknown')}` / `{item.get('evaluator_id', 'n/a')}` / "
            f"repeat {item.get('repeat', 'n/a')}: {item.get('stage')}: {item.get('detail')}"
            for item in failures
        )
        if failures
        else "- None."
    )
    return f"""# EVAL-01 results — controlled evaluator validation

- **Protocol/catalog:** version 1.0.0; preregistration commit `{manifest['preregistration_commit_sha']}`; catalog SHA-256 `{manifest['preregistration_catalog_sha256']}`.
- **Main base:** `{manifest['experiment_base_main_sha']}`.
- **Canonical A0.4:** `{manifest['source_baseline']['commit_sha']}`; app tree `{manifest['source_baseline']['application_tree_sha']}`.
- **Run window:** {manifest.get('started_at_utc')} — {manifest.get('completed_at_utc')}.
- **Execution environment:** Python {manifest['execution_environment']['python_version'].split()[0]}, PyYAML {manifest['execution_environment']['yaml_version']}, {manifest['execution_environment']['platform']}.

## Research question and preregistered hypotheses

**RQ:** On clean, source-pinned A0.4 checkouts, do `AC_PUBLIC_API` and `AC_MODULE_GRAPH` produce the outcomes catalogued for the controlled mutations, and what subprocess wall time is observed?

- **H1:** allowed public module imports remain compliant; the private Reporting → Tasks service import is rejected by `AC_PUBLIC_API`.
- **H2:** `AC_MODULE_GRAPH` rejects the injected undeclared edge, cycle, and unresolved local import while accepting the five declared edges.
- **H3:** deleting the expected Audit package yields explicit `NOT_EVALUABLE` scope results, not a detection true positive.

## Intervention and execution

The experiment materialized {len(catalog['cases'])} source conditions from canonical commit `{manifest['source_baseline']['commit_sha']}`. Every mutation has a distinct Git commit with canonical A0.4 as its sole parent; the archive retains the exact mutation patch and Git bundle. Before each of {len(manifest['runs'])} evaluator calls the runner required clean checkout state and passed the case HEAD as `--expected-source-sha`. Both evaluators ran {manifest['execution_environment']['repeat_count']} times on every condition in seed-randomized order. The untouched baseline checks all five expected edges, zero cycles, and zero unresolved imports. The public-import pair contrasts the same Reporting/Tasks boundary. Type-checking-only cases test static source rules without claiming runtime execution.

These are controlled W2 engineering evaluator observations, not MONO-E1/E2, B0, Method P, scorer, production, or fitness-representation coverage evidence.

## Results

### Case-level detection metrics

{_format_confusion_table(metrics_by_evaluator)}

The unit is one labeled evaluator-by-source-case condition. The 42 evaluator calls are **not** 42 independent cases; the three calls for each condition are collapsed before confusion metrics. Counts include only preregistered binary labels with stable, source/configuration-bound `COMPLIANT` or `NON_COMPLIANT` outcomes. The missing-package condition is `NOT_EVALUABLE` and is excluded by the catalog. Undefined metric denominators are shown as `NOT_DEFINED`. No confidence intervals or population inference are computed.

### Per-case observations

{chr(10).join(cases_table)}

### Subprocess wall time

{chr(10).join(timing_lines)}

Wall duration includes interpreter startup, source inventory, AST analysis, and JSON output. It is a descriptive evaluator-call measurement, not application runtime, full CI latency, adaptation overhead, CPU, or memory cost. Repeated calls are timing repeats of the same source revisions.

### Failures and unavailable outcomes

Runner-recorded failures: {len(failures)}.

{run_failures}

Analysis/artifact-integrity issues:

{failure_lines}

Unexpected nonzero evaluator exits are retained. Expected CLI exit 1 for `NON_COMPLIANT` and exit 2 for `NOT_EVALUABLE` are outcomes, not execution failures. A source SHA mismatch, dirty source, evaluator/configuration drift, launch/parse error, or absent observation is never counted as a true positive.

## Limitations and threats to validity

The finite cases were selected by the experiment author from the versioned A0.4 policy, and their labels follow the explicit interventions. Results therefore test these exact conditions and evaluator versions; they do not establish broad external validity or independent semantic review. Mutations are static Python source changes and do not verify runtime behavior.

`AC_PUBLIC_API` checks configured top-level API names and `TaskSummary` fields, not call signatures, runtime re-exports, or behavior. `AC_MODULE_GRAPH` derives dependency edges from direct Python imports and configured shared roots; it does not inspect dynamic imports, reflection, runtime dependency injection, raw SQL contents, database permissions, or deployable topology. Conditional imports count as dependencies regardless of reachability. Missing expected module scope is deliberately unresolved and has no binary label.

The measured duration covers only a fresh evaluator subprocess. This study has one canonical architecture baseline, no runtime workload, no independently designed architecture transitions, no inferential statistics, and no B0/Method P or scorer comparison.

## Supported conclusions

The conclusions are limited to whether each preregistered case produced its expected source-bound evaluator outcome and to the observed subprocess durations. Any confirmed detection supports only the named rule, source pattern, evaluator/configuration version, and A0.4 baseline in this catalog. `NOT_EVALUABLE`, execution failures, and unknown observations remain separate. No conclusion about MONO-E1/E2, Method P effectiveness, production authorization, G1/G4, or population-level evaluator accuracy follows from EVAL-01.

## Reproduction and evidence

Follow [`EVAL01_PROTOCOL_V1.md`](EVAL01_PROTOCOL_V1.md). The archive contains raw stdout JSON and stderr for every scheduled call, exact commands and timings, source and application tree SHAs, evaluator/configuration digests, mutation patches, mutation Git bundles, generated analysis, and `SHA256SUMS`. Verify the external archive sidecar before extraction. See the case-level CSV for machine-readable rows.
"""


def analyze_experiment(args: argparse.Namespace) -> int:
    """Validate raw run evidence, collapse repeats, derive metrics, and package artifacts."""
    run_dir = args.run_dir.resolve()
    manifest_path = run_dir / "run-manifest.json"
    manifest = read_json(manifest_path)
    catalog = read_json(run_dir / "preregistration/mutation_catalog.json")
    raw_errors = _validate_raw_inventory(run_dir, manifest)
    if sha256_file(run_dir / "preregistration/mutation_catalog.json") != manifest.get(
        "preregistration_catalog_sha256"
    ):
        raw_errors.append("PREREGISTRATION_CATALOG_DIGEST_MISMATCH")
    if manifest.get("source_baseline", {}).get("application_tree_sha") != BASELINE_APP_TREE:
        raw_errors.append("CANONICAL_APPLICATION_TREE_BINDING_MISMATCH")
    derived_runs, derivation_errors = _rederive_run_records_from_stdout(
        run_dir, manifest.get("runs", [])
    )
    raw_errors.extend(derivation_errors)
    manifest_for_analysis = {**manifest, "runs": derived_runs}

    case_results: dict[str, list[dict[str, Any]]] = {item: [] for item in EVALUATOR_IDS}
    repeat_count = int(catalog["execution_protocol"]["measured_repeats_per_case_evaluator"])
    for case in catalog["cases"]:
        for evaluator_id in EVALUATOR_IDS:
            case_results[evaluator_id].append(
                analyze_case(case, evaluator_id, derived_runs, repeat_count, catalog)
            )
    metrics_by_evaluator = {
        evaluator_id: confusion_metrics(case_results[evaluator_id])
        for evaluator_id in EVALUATOR_IDS
    }
    timing_by_evaluator: dict[str, dict[str, Any]] = {}
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
        timing_by_evaluator[evaluator_id] = {
            "n_completed": len(values),
            "median_ms": round(statistics.median(values), 3) if values else None,
            "minimum_ms": round(min(values), 3) if values else None,
            "maximum_ms": round(max(values), 3) if values else None,
            "timing_unit": catalog["execution_protocol"]["timing_unit"],
        }

    rows = [item for evaluator_id in EVALUATOR_IDS for item in case_results[evaluator_id]]
    by_case = {item["case_id"]: item for item in catalog["cases"]}
    for row in rows:
        row["application_tree_sha"] = manifest.get("cases", {}).get(row["case_id"], {}).get(
            "application_tree_sha"
        )
        row["expected_compliance"] = by_case[row["case_id"]]["expected_by_evaluator"][
            row["evaluator_id"]
        ]["compliance"]

    analysis = {
        "schema_version": 1,
        "experiment_id": catalog["experiment_id"],
        "run_manifest_sha256_before_analysis": sha256_file(manifest_path),
        "raw_inventory_verification": "PASS" if not raw_errors else "FAIL",
        "raw_inventory_errors": raw_errors,
        "evaluator_case_results": case_results,
        "evaluator_metrics": metrics_by_evaluator,
        "descriptive_wall_time": timing_by_evaluator,
        "repeated_runs_are_independent_cases": False,
        "missing_expected_capability_metric_treatment": "NOT_EVALUABLE; excluded from confusion matrices",
    }
    write_json(run_dir / "EVAL01_ANALYSIS_V1.json", analysis)

    csv_path = run_dir / "EVAL01_CASE_RESULTS_V1.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            extrasaction="ignore",
            fieldnames=[
                "case_id",
                "evaluator_id",
                "source_commit_sha",
                "application_tree_sha",
                "expected_compliance",
                "expected_architectural_label",
                "observed_compliance_case_level",
                "observed_compliance_by_repeat",
                "expected_finding_codes",
                "observed_finding_codes_by_repeat",
                "planned_repeat_count",
                "completed_repeat_count",
                "preregistered_expected_outcome_matched",
                "metric_eligible_by_catalog",
                "valid_for_confusion_matrix",
                "exclusion_reasons",
                "case_median_wall_time_ms",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "observed_compliance_by_repeat": json.dumps(row["observed_compliance_by_repeat"]),
                    "expected_finding_codes": json.dumps(row["expected_finding_codes"]),
                    "observed_finding_codes_by_repeat": json.dumps(
                        row["observed_finding_codes_by_repeat"]
                    ),
                    "exclusion_reasons": json.dumps(row["exclusion_reasons"]),
                }
            )

    report = _generate_report(
        catalog,
        manifest_for_analysis,
        case_results,
        metrics_by_evaluator,
        timing_by_evaluator,
        raw_errors,
    )
    (run_dir / "EVAL01_REPORT_V1.md").write_text(report, encoding="utf-8")

    analysis_paths = [
        run_dir / "EVAL01_ANALYSIS_V1.json",
        csv_path,
        run_dir / "EVAL01_REPORT_V1.md",
    ]
    manifest["analysis_artifacts_sha256"] = {
        path.relative_to(run_dir).as_posix(): sha256_file(path) for path in analysis_paths
    }
    manifest["analysis_raw_inventory_verification"] = analysis["raw_inventory_verification"]
    manifest["analysis_raw_inventory_errors"] = raw_errors
    write_json(manifest_path, manifest)

    if args.summary_dir:
        summary_dir = args.summary_dir.resolve()
        summary_dir.mkdir(parents=True, exist_ok=True)
        for path in analysis_paths:
            shutil.copyfile(path, summary_dir / path.name)
    if args.package:
        package_path = args.package.resolve()
        package_path.parent.mkdir(parents=True, exist_ok=True)
        checksum_lines = []
        for path in sorted(run_dir.rglob("*")):
            if path.is_file() and path.name not in {"SHA256SUMS"}:
                checksum_lines.append(
                    f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}"
                )
        (run_dir / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(run_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(run_dir).as_posix())
        sidecar = package_path.with_suffix(package_path.suffix + ".sha256")
        sidecar.write_text(f"{sha256_file(package_path)}  {package_path.name}\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "raw_inventory_verification": analysis["raw_inventory_verification"],
                "raw_inventory_errors": raw_errors,
                "metrics": metrics_by_evaluator,
                "failures": manifest.get("failures", []),
                "package": str(args.package.resolve()) if args.package else None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not raw_errors else 1


def _parser() -> argparse.ArgumentParser:
    """Build the EVAL-01 command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    execute_parser = subparsers.add_parser("execute", help="materialize and run preregistered cases")
    execute_parser.add_argument("--repo-root", type=Path, default=REPOSITORY_ROOT)
    execute_parser.add_argument("--output-dir", type=Path, required=True)
    execute_parser.set_defaults(handler=execute_experiment)

    analyze_parser = subparsers.add_parser("analyze", help="derive metrics and package raw evidence")
    analyze_parser.add_argument("--run-dir", type=Path, required=True)
    analyze_parser.add_argument("--summary-dir", type=Path)
    analyze_parser.add_argument("--package", type=Path)
    analyze_parser.set_defaults(handler=analyze_experiment)
    return parser


def main() -> int:
    """Dispatch an EVAL-01 command."""
    args = _parser().parse_args()
    try:
        return int(args.handler(args))
    except Exception as exc:
        print(f"EVAL-01 {args.command} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
