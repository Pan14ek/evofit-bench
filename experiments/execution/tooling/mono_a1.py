"""MONO-E1/E2 fail-closed reference custody and endpoint prerequisites.

This additive DEVELOPMENT tool does not execute frozen B0 or Method P and does
not change the DA01 scorer, historical references, or research authorization.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import subprocess  # nosec B404 - fixed Git argv, no shell
import sys
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast

from experiments.execution.tooling.contracts import validate_payload, validate_prediction
from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import (
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
)
from experiments.execution.tooling.sealing import (
    PREDICTION_NAME,
    SEAL_NAME,
    load_verified_prediction,
)

REFERENCE_SCHEMA = "mono_a1_reference_v1.schema.json"
STUDY_SCHEMA = "mono_a1_study_v1.schema.json"
PAIR_SCHEMA = "mono_a1_exact_pair_evidence_v1.schema.json"
REFERENCE_NAME = "reference.json"
REFERENCE_SEAL_NAME = "reference.seal.json"
INVENTORY_NAME = "evidence_inventory.json"
ARCHIVE_SIDE_CAR_SUFFIX = ".sha256"
OPERATIONS = {"retain", "add", "replace", "deactivate", "adjust"}
SHA1_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
PINNED_IMAGE_RE = re.compile(r"^(?:[^\s@]+@)?sha256:[a-f0-9]{64}$")
SENSITIVE_PATH_PARTS = (
    ".git",
    "ground_truth",
    "expected_operation",
    "scorer",
    "other_arm",
    "private_reference",
)
SENSITIVE_JSON_KEYS = {
    "ground_truth",
    "oracle",
    "expected_operation",
    "expected_operations",
    "expected_disposition",
    "expected_answers",
    "reference_labels",
    "scorer_output",
    "other_arm",
    "other_arm_prediction",
}


class MonoA1Error(ProtocolError):
    """A MONO-A1 evidence record violates the versioned custody contract."""


class ExactPairReadbackVerifier(Protocol):
    """Source-pinned evaluator adapter that independently rechecks one exact-pair report."""

    evaluator_id: str
    version: str
    source_sha: str
    tree_sha: str
    artifact_sha256: str
    configuration_sha256: str

    def verify(self, evidence: Mapping[str, Any], *, artifact_root: Path) -> bool | None:
        """Return True only after independently validating the source-bound raw evidence."""


class W2A1ExactPairReadbackVerifier:
    """Read back a W2 A1 evaluator report from its exact pinned source checkout."""

    def __init__(
        self,
        *,
        evaluator_id: str,
        version: str,
        source_sha: str,
        tree_sha: str,
        artifact_sha256: str,
        configuration_sha256: str,
        evaluator_repository: Path,
        evaluator_package_root: Path,
        configuration_path: Path,
        subject_repository: Path,
    ) -> None:
        self.evaluator_id = evaluator_id
        self.version = version
        self.source_sha = source_sha
        self.tree_sha = tree_sha
        self.artifact_sha256 = artifact_sha256
        self.configuration_sha256 = configuration_sha256
        self.evaluator_repository = evaluator_repository
        self.evaluator_package_root = evaluator_package_root
        self.configuration_path = configuration_path
        self.subject_repository = subject_repository

    def verify(self, evidence: Mapping[str, Any], *, artifact_root: Path) -> bool | None:
        """Validate W2 schema, pair/state bindings, pinned bytes, and its independent readback."""
        payload = dict(evidence)
        evaluator = payload.get("evaluator")
        if not isinstance(evaluator, Mapping) or any(
            evaluator.get(key) != value
            for key, value in (
                ("evaluator_id", self.evaluator_id),
                ("version", self.version),
                ("source_sha", self.source_sha),
                ("tree_sha", self.tree_sha),
                ("artifact_sha256", self.artifact_sha256),
                ("configuration_sha256", self.configuration_sha256),
            )
        ):
            return False
        if not _checkout_matches(self.evaluator_repository, self.source_sha, self.tree_sha):
            return False
        if not _checkout_matches(
            self.subject_repository, str(payload.get("architecture_source_sha", "")), None
        ):
            return False
        try:
            evaluator_root = self.evaluator_package_root.resolve(strict=True)
            evaluator_repository = self.evaluator_repository.resolve(strict=True)
            config_path = self.configuration_path.resolve(strict=True)
            subject_root = self.subject_repository.resolve(strict=True)
            if (
                self.evaluator_package_root.is_symlink()
                or self.evaluator_repository.is_symlink()
                or self.configuration_path.is_symlink()
                or self.subject_repository.is_symlink()
            ):
                return False
            evaluator_root.relative_to(evaluator_repository)
            config_path.relative_to(evaluator_repository)
            if not config_path.is_file() or sha256_file(config_path) != self.configuration_sha256:
                return False
            if not _verify_raw_evidence_artifacts(
                payload.get("raw_evidence_artifacts", []), artifact_root
            ):
                return False
            reports = [
                item
                for item in payload.get("raw_evidence_artifacts", [])
                if item.get("artifact_id") == "W2_A1_EVALUATOR_EVIDENCE"
            ]
            if len(reports) != 1:
                return False
            report_path = (artifact_root / str(reports[0]["path"])).resolve(strict=True)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            schema_path = evaluator_root / "evidence.schema.json"
            engine_path = evaluator_root / "engine.py"
            if schema_path.is_symlink() or engine_path.is_symlink():
                return False
            import jsonschema  # type: ignore[import-untyped]

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(
                schema, format_checker=jsonschema.FormatChecker()
            ).validate(report)
            if not _w2_report_matches_pair(report, payload, self):
                return False
            engine_module = _load_w2_engine(engine_path, self.source_sha)
            verify_evidence = getattr(engine_module, "verify_evidence", None)
            if not callable(verify_evidence):
                return False
            failures = verify_evidence(report, subject_root, config_path, evaluator_root)
            return not failures
        except Exception:
            # The pinned verifier, schema library, or report may fail; none grants evidence.
            return False


def validate_mono_reference(reference: Mapping[str, Any]) -> None:
    """Validate reference structure, complete target identity, and denominator closure."""
    validate_payload(REFERENCE_SCHEMA, dict(reference))
    architecture = reference["architecture"]
    before = architecture["before"]
    after = architecture["after"]
    if before["commit_sha"] == after["commit_sha"]:
        raise MonoA1Error("MONO reference requires distinct before and after source revisions")
    facts_by_id = {str(item["fact_id"]): item for item in reference["architecture_facts"]}
    fact_ids = set(facts_by_id)
    if len(fact_ids) != len(reference["architecture_facts"]):
        raise MonoA1Error("Architecture fact IDs must be unique")
    source_shas = {before["commit_sha"], after["commit_sha"]}
    for fact in reference["architecture_facts"]:
        if fact["architecture_source_sha"] not in source_shas:
            raise MonoA1Error("Architecture fact is pinned to an unlisted source revision")
    targets = reference["target_universe"]
    target_keys = [(item["target_type"], item["target_id"]) for item in targets]
    if len(target_keys) != len(set(target_keys)):
        raise MonoA1Error("Reference target universe contains duplicate identities")
    for target in targets:
        if not set(target["source_fact_ids"]).issubset(fact_ids):
            raise MonoA1Error("Reference target cites an unknown source fact")
        if any(
            facts_by_id[fact_id]["status"] != "VERIFIED" for fact_id in target["source_fact_ids"]
        ):
            raise MonoA1Error("Reference target labels require verified source facts")
        expected_action = target["expected_operation"] != "retain"
        if (target["expected_disposition"] == "AFFECTED") != expected_action:
            raise MonoA1Error("Affected status and expected operation disagree")
        if target["target_type"] == "obligation" and target["expected_operation"] != "add":
            raise MonoA1Error("New obligation targets must use the add operation")
        if target["target_type"] == "representation" and target["expected_operation"] == "add":
            raise MonoA1Error("Representation targets cannot use the add operation")
    obligation_rows = reference["obligation_universe"]
    obligation_ids = [str(item["obligation_id"]) for item in obligation_rows]
    if len(obligation_ids) != len(set(obligation_ids)):
        raise MonoA1Error("Obligation universe contains duplicate IDs")
    evaluators = {str(item["evaluator_id"]) for item in reference["evaluator_artifacts"]}
    if len(evaluators) != len(reference["evaluator_artifacts"]):
        raise MonoA1Error("Evaluator IDs must be unique in the sealed reference")
    target_obligations = {
        str(item["target_id"]) for item in targets if item["target_type"] == "obligation"
    }
    if target_obligations - set(obligation_ids):
        raise MonoA1Error("Reference target universe names an unlisted obligation")
    for obligation in obligation_rows:
        if not set(obligation["applicability_fact_ids"]).issubset(fact_ids):
            raise MonoA1Error("Obligation applicability cites an unknown source fact")
        if obligation["applicability"] in {"ACTIVE", "INACTIVE"} and (
            not obligation["applicability_fact_ids"]
            or any(
                facts_by_id[fact_id]["status"] != "VERIFIED"
                for fact_id in obligation["applicability_fact_ids"]
            )
        ):
            raise MonoA1Error("Known applicability requires non-empty verified source facts")
        pair_keys: set[tuple[str, str]] = set()
        for pair in obligation["required_exact_pairs"]:
            key = (str(pair["representation_id"]), str(pair["evaluator_id"]))
            if key in pair_keys:
                raise MonoA1Error("Required exact-pair set contains duplicates")
            pair_keys.add(key)
            if key[1] not in evaluators:
                raise MonoA1Error("Required exact pair names an unregistered evaluator")
            if not any(
                t["target_type"] == "representation" and t["target_id"] == key[0] for t in targets
            ):
                raise MonoA1Error(
                    "Required exact pair names a representation outside the target universe"
                )
        if obligation["applicability"] == "ACTIVE" and obligation["mandatory"] and not pair_keys:
            raise MonoA1Error("Active mandatory obligation lacks a declared exact-pair requirement")
    required = {
        str(item["obligation_id"])
        for item in obligation_rows
        if item["mandatory"] and item["applicability"] == "ACTIVE"
    }
    unresolved = {
        str(item["obligation_id"])
        for item in obligation_rows
        if item["mandatory"] and item["applicability"] == "UNKNOWN"
    }
    denominator = reference["obligation_denominator"]
    if set(denominator["required_obligation_ids"]) != required:
        raise MonoA1Error(
            "Reference obligation denominator does not match the full active mandatory set"
        )
    if set(denominator["unresolved_obligation_ids"]) != unresolved:
        raise MonoA1Error(
            "Reference unresolved obligations do not match applicability UNKNOWN rows"
        )
    if denominator["complete"] != (not unresolved):
        raise MonoA1Error(
            "Reference denominator completeness contradicts unresolved mandatory obligations"
        )


def validate_mono_study(study: Mapping[str, Any]) -> None:
    """Validate study schema and cross-field source, denominator, seal, and abstention rules."""
    validate_payload(STUDY_SCHEMA, dict(study))
    architecture = study["architecture"]
    methods = study["methods"]
    reference = study["reference"]
    arms = study["arms"]
    obligations = study["obligations"]
    if study["study_id"] == "MONO-E0" and study["study_status"] != "HISTORICAL":
        raise MonoA1Error("MONO-E0 is a historical pointer and cannot be staged as a new run")
    if study["study_id"] != "MONO-E0" and study["exposure"] != "KNOWN_SCENARIO_AUTHOR_DECLARED":
        raise MonoA1Error("MONO-E1/E2 must retain known-scenario exposure")
    if architecture["before"]["commit_sha"] and architecture["after"]["commit_sha"]:
        if architecture["before"]["commit_sha"] == architecture["after"]["commit_sha"]:
            raise MonoA1Error("Study before and after source SHAs must differ")
    for arm_name, method in methods.items():
        if method["source_sha"] and method["configuration_sha256"] is None:
            raise MonoA1Error(
                f"{arm_name} configuration digest is required when the method is pinned"
            )
    required_ids = {
        str(row["obligation_id"])
        for row in obligations["universe"]
        if row["mandatory"] and row["applicability"] == "ACTIVE"
    }
    unresolved_ids = {
        str(row["obligation_id"])
        for row in obligations["universe"]
        if row["mandatory"] and row["applicability"] == "UNKNOWN"
    }
    if set(obligations["required_obligation_ids"]) != required_ids:
        raise MonoA1Error("Study denominator differs from its declared obligation universe")
    if set(obligations["unresolved_obligation_ids"]) != unresolved_ids:
        raise MonoA1Error("Study unresolved set differs from mandatory UNKNOWN obligations")
    if obligations["denominator_complete"] != (not unresolved_ids):
        raise MonoA1Error("Study denominator completeness is inconsistent")
    for bundle in study["method_input_bundles"]:
        if set(bundle) != {
            "arm",
            "bundle_id",
            "bundle_sha256",
            "allowlist_sha256",
            "reference_excluded",
            "oracle_excluded",
            "other_arm_excluded",
        }:
            raise MonoA1Error("Method input identity contains unrecognized fields")
        if not (
            bundle["reference_excluded"]
            and bundle["oracle_excluded"]
            and bundle["other_arm_excluded"]
        ):
            raise MonoA1Error(
                "Method input bundle must exclude reference, oracle, and other-arm artifacts"
            )
    if reference["status"] == "SEALED":
        if (
            not reference["reference_sha256"]
            or not reference["seal_path"]
            or not reference["frozen_at_utc"]
        ):
            raise MonoA1Error("A sealed reference requires its digest, path, and freeze time")
        if reference["custody_status"] != "AUTHOR_DECLARED":
            raise MonoA1Error(
                "This workflow requires author-declared custody when no independent reviewer exists"
            )
        for side in ("before", "after"):
            if architecture[side]["commit_sha"] is None:
                raise MonoA1Error("Sealed study source revisions must be pinned")
        frozen_at = _parse_timestamp(reference["frozen_at_utc"])
        for arm_name, arm in arms.items():
            if arm["execution_status"] == "COMPLETED":
                if not arm["run_id"] or not arm["execution_started_at_utc"]:
                    raise MonoA1Error(f"{arm_name} completed run requires identity and start time")
                if _parse_timestamp(arm["execution_started_at_utc"]) <= frozen_at:
                    raise MonoA1Error("Reference must be frozen before both method executions")
    for arm_name, arm in arms.items():
        if arm["prediction_status"] == "SEALED" and not arm["prediction_sha256"]:
            raise MonoA1Error(f"{arm_name} sealed prediction is missing its digest")
        if arm["prediction_status"] != "SEALED" and arm["prediction_sha256"] is not None:
            raise MonoA1Error(f"{arm_name} prediction digest exists without a sealed prediction")
    if (
        reference["status"] != "SEALED"
        and study["study_status"] in {"EXECUTED", "SCORED"}
        and study["study_id"] != "MONO-E0"
    ):
        raise MonoA1Error("New MONO execution cannot be recorded before reference seal")
    if set(reference) != {
        "status",
        "custody_status",
        "reference_sha256",
        "seal_path",
        "frozen_at_utc",
    }:
        raise MonoA1Error("Study reference record contains unrecognized fields")
    for evidence in study["exact_pair_evidence"]:
        validate_payload(PAIR_SCHEMA, evidence)
        if (
            architecture["after"]["commit_sha"]
            and evidence["architecture_source_sha"] != architecture["after"]["commit_sha"]
        ):
            raise MonoA1Error(
                "Study exact-pair evidence is pinned to a different target source SHA"
            )
    rq1 = study["endpoints"]["RQ1"]
    if arms["P"]["prediction_status"] == "NOT_EMITTED_GOVERNANCE_HOLD":
        if rq1["status"] != "NOT_EVALUABLE" or rq1["scorer_invoked"]:
            raise MonoA1Error("P HOLD without a sealed prediction must remain RQ1 NOT_EVALUABLE")
    if rq1["status"] == "NOT_EVALUABLE" and rq1["scorer_invoked"]:
        raise MonoA1Error("RQ1 scorer must not be invoked without both sealed predictions")
    if rq1["status"] == "SCORED" and (
        not rq1["scorer_invoked"]
        or any(arms[arm]["prediction_status"] != "SEALED" for arm in ("B0", "P"))
    ):
        raise MonoA1Error("RQ1 SCORED requires both genuine sealed predictions")
    rq2 = study["endpoints"]["RQ2"]
    if set(rq2["denominator_obligation_ids"]) != set(obligations["required_obligation_ids"]):
        raise MonoA1Error("RQ2 denominator differs from the study's complete mandatory denominator")
    rq2_row_ids = [str(row["obligation_id"]) for row in rq2["rows"]]
    if set(rq2_row_ids) != set(rq2["denominator_obligation_ids"]) or len(rq2_row_ids) != len(
        set(rq2_row_ids)
    ):
        raise MonoA1Error("RQ2 rows do not enumerate the exact denominator once")
    if not obligations["denominator_complete"] or not rq2["denominator_complete"]:
        if any(
            rq2[key] is not None
            for key in (
                "B0_coverage_percentage",
                "P_candidate_potential_coverage_percentage",
                "P_governance_accepted_coverage_percentage",
            )
        ):
            raise MonoA1Error("RQ2 percentages cannot be reported for an incomplete denominator")
    if rq2["status"] == "SCORED" and not obligations["denominator_complete"]:
        raise MonoA1Error("RQ2 cannot be scored with unresolved mandatory applicability")
    rq3 = study["endpoints"]["RQ3"]
    if rq3["status"] == "DESCRIPTIVE":
        _verify_rq3_prerequisites(
            rq3["timing_boundary_id"],
            rq3["B0"],
            rq3["P"],
            arms["B0"]["source_image_provenance"],
            arms["P"]["source_image_provenance"],
            architecture["after"]["commit_sha"],
        )
    for control in study["endpoints"]["RQ4"]["controls"]:
        if control["status"] == "PASS" and (
            not control["source_sha"]
            or not control["evaluator_id"]
            or not control["execution_sha256"]
            or not control["raw_evidence_sha256"]
            or not control["inspected_item_count"]
            or control["inspected_item_count"] < 1
        ):
            raise MonoA1Error("RQ4 PASS requires source-pinned, non-vacuous evaluator evidence")


def verify_source_revision(repository: Path, commit_sha: str, tree_sha: str) -> None:
    """Require a Git commit and exact tree object matching the declared revision."""
    if not SHA1_RE.fullmatch(commit_sha) or not SHA1_RE.fullmatch(tree_sha):
        raise MonoA1Error("Source commit and tree identities must be full lowercase Git SHAs")
    try:
        root = repository.resolve(strict=True)
        commit = subprocess.run(  # noqa: S603 - fixed Git argv and validated full SHA
            ["git", "-C", str(root), "rev-parse", "--verify", f"{commit_sha}^{{commit}}"],  # noqa: S607
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        tree = subprocess.run(  # noqa: S603 - fixed Git argv and validated full SHA
            ["git", "-C", str(root), "rev-parse", "--verify", f"{commit_sha}^{{tree}}"],  # noqa: S607
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise MonoA1Error(
            "Pinned source revision is unavailable in the verification repository"
        ) from error
    if commit != commit_sha or tree != tree_sha:
        raise MonoA1Error("Pinned source commit or tree SHA does not match the Git object database")


def _checkout_matches(repository: Path, commit_sha: str, tree_sha: str | None) -> bool:
    """Require a checkout to be at the requested commit and, when supplied, tree."""
    if repository.is_symlink() or not SHA1_RE.fullmatch(commit_sha):
        return False
    try:
        root = repository.resolve(strict=True)
        head = subprocess.run(  # noqa: S603 - fixed Git argv, no shell
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],  # noqa: S607
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        tree = subprocess.run(  # noqa: S603 - fixed Git argv, no shell
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD^{tree}"],  # noqa: S607
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return head == commit_sha and (tree_sha is None or tree == tree_sha)


def _load_w2_engine(engine_path: Path, source_sha: str) -> Any:
    """Load the source-pinned W2 readback module without adding a main-branch dependency."""
    module_name = f"_mono_a1_w2_engine_{source_sha}"
    spec = importlib.util.spec_from_file_location(module_name, engine_path)
    if spec is None or spec.loader is None:
        raise MonoA1Error("Pinned W2 evaluator engine cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _w2_report_matches_pair(
    report: Any, pair: Mapping[str, Any], verifier: W2A1ExactPairReadbackVerifier
) -> bool:
    """Bind one W2 report to the exact W3 representation, obligation, state, and source."""
    if not isinstance(report, Mapping):
        return False
    evaluator = report.get("evaluator")
    architecture = report.get("architecture")
    scope = report.get("source_scope")
    result = report.get("result")
    raw_output = report.get("raw_output")
    if not (
        isinstance(evaluator, Mapping)
        and isinstance(architecture, Mapping)
        and isinstance(scope, Mapping)
        and isinstance(result, Mapping)
        and isinstance(raw_output, Mapping)
    ):
        return False
    if any(
        evaluator.get(key) != value
        for key, value in (
            ("id", verifier.evaluator_id),
            ("obligation_id", pair.get("obligation_id")),
            ("version", verifier.version),
            ("source_digest", verifier.artifact_sha256),
            ("configuration_digest", verifier.configuration_sha256),
        )
    ):
        return False
    target_sha = pair.get("architecture_source_sha")
    if any(
        architecture.get(key) != value
        for key, value in (
            ("state", pair.get("architecture_state")),
            ("target_source_sha", target_sha),
            ("expected_source_sha", target_sha),
            ("source_sha_status", "MATCHED"),
            ("manifest_state_status", "MATCHED"),
            ("subject_source_dirty", False),
        )
    ):
        return False
    inspected_paths = scope.get("inspected_paths")
    source_digests = scope.get("source_file_digests")
    uncertainties = scope.get("uncertainties")
    if (
        scope.get("complete") is not True
        or not isinstance(inspected_paths, list)
        or not inspected_paths
        or len(inspected_paths) != len(set(inspected_paths))
        or not isinstance(source_digests, list)
        or not source_digests
        or {item.get("path") for item in source_digests if isinstance(item, Mapping)}
        != set(inspected_paths)
        or not isinstance(uncertainties, list)
        or uncertainties
    ):
        return False
    if (
        report.get("applicability") != "ACTIVE"
        or result.get("execution_status") != "COMPLETED"
        or result.get("compliance") != "COMPLIANT"
        or result.get("violation_count") != 0
        or result.get("violations") != []
        or result.get("configuration_errors") != []
        or raw_output.get("available") is not True
        or raw_output.get("format") != "application/json"
    ):
        return False
    try:
        diagnostics_digest = sha256_bytes(canonical_json_bytes(report["diagnostics"]))
    except (KeyError, TypeError, ValueError):
        return False
    return bool(raw_output.get("sha256") == diagnostics_digest)


def freeze_reference(
    reference: Mapping[str, Any],
    destination: Path,
    *,
    repository: Path,
    frozen_at_utc: str | None = None,
) -> dict[str, Any]:
    """Write a scorer-only reference and digest seal exactly once after Git readback."""
    validate_mono_reference(reference)
    for side in ("before", "after"):
        revision = reference["architecture"][side]
        verify_source_revision(repository, revision["commit_sha"], revision["tree_sha"])
    for evaluator in reference["evaluator_artifacts"]:
        verify_source_revision(repository, evaluator["source_sha"], evaluator["tree_sha"])
    if destination.exists() or destination.is_symlink():
        raise MonoA1Error("MONO reference destination exists; reference freezing is write-once")
    frozen_at = frozen_at_utc or _utc_now()
    _parse_timestamp(frozen_at)
    destination.mkdir(parents=True, exist_ok=False)
    reference_bytes = canonical_json_bytes(dict(reference)) + b"\n"
    digest = sha256_bytes(reference_bytes)
    seal = {
        "schema_version": 1,
        "reference_id": reference["reference_id"],
        "study_id": reference["study_id"],
        "reference_sha256": digest,
        "architecture_before_sha": reference["architecture"]["before"]["commit_sha"],
        "architecture_after_sha": reference["architecture"]["after"]["commit_sha"],
        "custody_status": "AUTHOR_DECLARED",
        "frozen_at_utc": frozen_at,
    }
    _write_once(destination / REFERENCE_NAME, reference_bytes, readonly=True)
    _write_once(destination / REFERENCE_SEAL_NAME, pretty_json_bytes(seal), readonly=True)
    return seal


def load_verified_reference(
    directory: Path,
    *,
    repository: Path,
    expected_study_id: str | None = None,
    method_execution_started_at_utc: str | None = None,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Verify immutable reference bytes, seal metadata, Git bindings, and freeze ordering."""
    if directory.is_symlink() or not directory.is_dir():
        raise MonoA1Error("MONO reference custody directory is missing or symlinked")
    expected_files = {REFERENCE_NAME, REFERENCE_SEAL_NAME}
    actual_files = {path.name for path in directory.iterdir()}
    if actual_files != expected_files:
        raise MonoA1Error("MONO reference custody directory must contain only payload and seal")
    payload_path = directory / REFERENCE_NAME
    seal_path = directory / REFERENCE_SEAL_NAME
    if any(path.is_symlink() or not path.is_file() for path in (payload_path, seal_path)):
        raise MonoA1Error("MONO reference payload and seal must be regular files")
    try:
        raw = payload_path.read_bytes()
        seal = cast(dict[str, Any], json.loads(seal_path.read_text(encoding="utf-8")))
        payload = cast(dict[str, Any], json.loads(raw))
    except (OSError, json.JSONDecodeError) as error:
        raise MonoA1Error("MONO reference bytes or seal are missing or malformed") from error
    digest = sha256_bytes(raw)
    if digest != seal.get("reference_sha256"):
        raise MonoA1Error("MONO reference bytes differ from the frozen digest seal")
    validate_mono_reference(payload)
    if seal.get("schema_version") != 1 or seal.get("custody_status") != "AUTHOR_DECLARED":
        raise MonoA1Error("MONO reference seal has unsupported custody metadata")
    if (
        seal.get("study_id") != payload["study_id"]
        or seal.get("reference_id") != payload["reference_id"]
    ):
        raise MonoA1Error("MONO reference seal identifies different reference content")
    for side, seal_key in (
        ("before", "architecture_before_sha"),
        ("after", "architecture_after_sha"),
    ):
        revision = payload["architecture"][side]
        if seal.get(seal_key) != revision["commit_sha"]:
            raise MonoA1Error("MONO reference seal source SHA does not match its payload")
        verify_source_revision(repository, revision["commit_sha"], revision["tree_sha"])
    for evaluator in payload["evaluator_artifacts"]:
        verify_source_revision(repository, evaluator["source_sha"], evaluator["tree_sha"])
    freeze_time = _parse_timestamp(str(seal.get("frozen_at_utc", "")))
    if expected_study_id and payload["study_id"] != expected_study_id:
        raise MonoA1Error("MONO reference belongs to another study")
    if method_execution_started_at_utc:
        if _parse_timestamp(method_execution_started_at_utc) <= freeze_time:
            raise MonoA1Error("Reference must be frozen before the first method execution")
    return payload, digest, seal


def verify_method_input_isolation(
    method_input_directory: Path, reference_directory: Path
) -> list[dict[str, Any]]:
    """Reject reference/oracle leakage, symlinks, and sensitive path or JSON-key contamination."""
    if method_input_directory.is_symlink() or reference_directory.is_symlink():
        raise MonoA1Error("Method input and reference custody roots cannot be symlinked")
    try:
        bundle = method_input_directory.resolve(strict=True)
        reference_root = reference_directory.resolve(strict=True)
    except OSError as error:
        raise MonoA1Error("Method input or reference custody directory is unavailable") from error
    if not bundle.is_dir() or not reference_root.is_dir():
        raise MonoA1Error("Method input and reference custody paths must be directories")
    if (
        bundle == reference_root
        or bundle in reference_root.parents
        or reference_root in bundle.parents
    ):
        raise MonoA1Error("Reference custody and method input trees must be disjoint")
    reference_payload = reference_root / REFERENCE_NAME
    if not reference_payload.is_file():
        raise MonoA1Error("Reference payload is missing from scorer-only custody")
    reference_digest = sha256_file(reference_payload)
    records: list[dict[str, Any]] = []
    for path in sorted(bundle.rglob("*")):
        if path.is_symlink():
            raise MonoA1Error("Method input bundle contains a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(bundle).as_posix().lower()
        if any(part in relative for part in SENSITIVE_PATH_PARTS):
            raise MonoA1Error(
                "Method input path contains reference, oracle, scorer, or cross-arm material"
            )
        content = path.read_bytes()
        if sha256_bytes(content) == reference_digest or reference_digest.encode("ascii") in content:
            raise MonoA1Error("Method input contains the frozen reference or its digest")
        if path.suffix.lower() in {".json", ".jsonl"}:
            try:
                decoded = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise MonoA1Error("Method JSON input is malformed") from None
            if _contains_sensitive_key(decoded):
                raise MonoA1Error(
                    "Method input JSON contains an oracle, scorer, or reference-label key"
                )
        records.append(
            {
                "path": path.relative_to(bundle).as_posix(),
                "sha256": sha256_bytes(content),
                "size_bytes": len(content),
            }
        )
    return records


def verify_exact_pair_evidence(
    evidence: Mapping[str, Any],
    *,
    study_id: str,
    run_id: str,
    architecture_state: str,
    architecture_source_sha: str,
    representation_id: str,
    obligation_id: str,
    configuration_role: str,
    configuration_sha256: str,
    expected_evaluator: Mapping[str, Any] | None = None,
    independent_verifier: ExactPairReadbackVerifier | None = None,
    artifact_root: Path | None = None,
    require_production_authority: bool = False,
) -> str:
    """Return VERIFIED, DIAGNOSTIC_ONLY, or UNKNOWN for one exact evidence tuple."""
    payload = dict(evidence)
    validate_payload(PAIR_SCHEMA, payload)
    expected = {
        "study_id": study_id,
        "run_id": run_id,
        "architecture_state": architecture_state,
        "architecture_source_sha": architecture_source_sha,
        "representation_id": representation_id,
        "obligation_id": obligation_id,
        "configuration_role": configuration_role,
        "configuration_sha256": configuration_sha256,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise MonoA1Error(
            "Exact-pair evidence is mapped to a different study, run, source, or pair"
        )
    expected_arm = "B0" if configuration_role == "B0_FROZEN" else "P"
    if payload["arm"] != expected_arm:
        raise MonoA1Error("Exact-pair evidence arm does not match its configuration role")
    evaluator = payload["evaluator"]
    evaluator_matches = bool(
        expected_evaluator
        and evaluator["evaluator_id"] == expected_evaluator.get("evaluator_id")
        and evaluator["version"] == expected_evaluator.get("version")
        and evaluator["source_sha"] == expected_evaluator.get("source_sha")
        and evaluator["tree_sha"] == expected_evaluator.get("tree_sha")
        and evaluator["artifact_sha256"] == expected_evaluator.get("artifact_sha256")
        and evaluator["configuration_sha256"] == expected_evaluator.get("configuration_sha256")
    )
    execution = payload["execution"]
    inspection = payload["inspection"]
    semantic = payload["semantic_suitability"]
    raw_artifacts_verified = _verify_raw_evidence_artifacts(
        payload["raw_evidence_artifacts"], artifact_root
    )
    raw_digests = {str(item["sha256"]) for item in payload["raw_evidence_artifacts"]}
    positive = (
        evaluator_matches
        and execution["status"] == "VERIFIED"
        and execution["execution_sha256"] is not None
        and execution["execution_sha256"] in raw_digests
        and inspection["inspected_item_count"] is not None
        and inspection["inspected_item_count"] > 0
        and inspection["scope_sha256"] in raw_digests
        and semantic["status"] == "SUITABLE"
        and semantic["assessment_sha256"] is not None
        and semantic["assessment_sha256"] in raw_digests
        and payload["compliance"] == "COMPLIANT"
        and raw_artifacts_verified
    )
    if not positive:
        return "UNKNOWN"
    if artifact_root is None:
        return "UNKNOWN"
    if (
        independent_verifier is None
        or expected_evaluator is None
        or independent_verifier.evaluator_id != expected_evaluator.get("evaluator_id")
        or independent_verifier.version != expected_evaluator.get("version")
        or independent_verifier.source_sha != expected_evaluator.get("source_sha")
        or independent_verifier.tree_sha != expected_evaluator.get("tree_sha")
        or independent_verifier.artifact_sha256 != expected_evaluator.get("artifact_sha256")
        or independent_verifier.configuration_sha256
        != expected_evaluator.get("configuration_sha256")
        or independent_verifier.verify(payload, artifact_root=artifact_root) is not True
    ):
        return "UNKNOWN"
    if payload["trust_scope"] == "TEST_ONLY":
        return "DIAGNOSTIC_ONLY"
    if require_production_authority:
        # No production trust-anchor adapter exists in MONO-A1 v1.
        return "DIAGNOSTIC_ONLY"
    return "VERIFIED"


def score_mono_rq1(
    reference_directory: Path,
    b0_prediction_directory: Path,
    p_prediction_directory: Path | None,
    *,
    repository: Path,
    b0_prediction_status: str,
    p_prediction_status: str,
    input_bundle_sha256: Mapping[str, str],
    method_execution_started_at_utc: Mapping[str, str],
) -> dict[str, Any]:
    """Score genuine sealed B0/P predictions only after a verified scorer-only reference."""
    if set(method_execution_started_at_utc) != {"B0", "P"}:
        raise MonoA1Error("RQ1 requires execution start timestamps for both B0 and P")
    execution_starts = {
        arm: _parse_timestamp(value) for arm, value in method_execution_started_at_utc.items()
    }
    reference, _, seal = load_verified_reference(
        reference_directory,
        repository=repository,
        method_execution_started_at_utc=min(execution_starts.values()).isoformat(),
    )
    if p_prediction_status == "NOT_EMITTED_GOVERNANCE_HOLD":
        if p_prediction_directory is not None and (
            p_prediction_directory.exists() or p_prediction_directory.is_symlink()
        ):
            raise MonoA1Error("P HOLD marker conflicts with a P prediction directory")
        return {
            "status": "NOT_EVALUABLE",
            "scorer_invoked": False,
            "reason": "P_HOLD_WITHOUT_SEALED_PREDICTION",
            "B0": None,
            "P": None,
        }
    if b0_prediction_status != "SEALED":
        return {
            "status": "NOT_EVALUABLE",
            "scorer_invoked": False,
            "reason": "B0_PREDICTION_NOT_SEALED",
            "B0": None,
            "P": None,
        }
    if p_prediction_status != "SEALED" or p_prediction_directory is None:
        return {
            "status": "NOT_EVALUABLE",
            "scorer_invoked": False,
            "reason": "P_PREDICTION_NOT_SEALED",
            "B0": None,
            "P": None,
        }
    if b0_prediction_directory.is_symlink() or p_prediction_directory.is_symlink():
        raise MonoA1Error("RQ1 prediction directories cannot be symlinked")
    for directory in (b0_prediction_directory, p_prediction_directory):
        if any(
            path.is_symlink() or not path.is_file()
            for path in (directory / PREDICTION_NAME, directory / SEAL_NAME)
        ):
            raise MonoA1Error("RQ1 sealed prediction and seal must be regular files")
    b0 = load_verified_prediction(b0_prediction_directory)
    p = load_verified_prediction(p_prediction_directory)
    expected_source = reference["architecture"]["after"]["commit_sha"]
    for arm_name, prediction in (("B0", b0), ("P", p)):
        body = prediction.payload
        if body["method_id"] != arm_name:
            raise MonoA1Error(f"{arm_name} prediction has the wrong method identity")
        if body["architecture_source_sha"] != expected_source:
            raise MonoA1Error(f"{arm_name} prediction is bound to a different architecture SHA")
        if body["input_bundle_sha256"] != input_bundle_sha256.get(arm_name):
            raise MonoA1Error(f"{arm_name} prediction is bound to a different input bundle")
        sealed_at = _parse_timestamp(prediction.sealed_at_utc)
        if sealed_at <= _parse_timestamp(seal["frozen_at_utc"]):
            raise MonoA1Error("Prediction was sealed before the reference freeze")
        if sealed_at < execution_starts[arm_name]:
            raise MonoA1Error(f"{arm_name} prediction was sealed before its method run started")
    return {
        "status": "SCORED",
        "scorer_invoked": True,
        "reason": None,
        "B0": _score_prediction(reference, b0.payload),
        "P": _score_prediction(reference, p.payload),
    }


def score_mono_rq2(
    reference_directory: Path,
    evidence_records: Sequence[Mapping[str, Any]],
    *,
    repository: Path,
    method_execution_started_at_utc: Mapping[str, str],
    declared_denominator_ids: Sequence[str],
    run_ids: Mapping[str, str],
    candidate_validation: str,
    candidate_configuration_sha256: str | None,
    governance_status: str,
    accepted_configuration_sha256: str | None = None,
    evidence_root_by_arm: Mapping[str, Path] | None = None,
    independent_verifier: ExactPairReadbackVerifier | None = None,
) -> dict[str, Any]:
    """Assess B0, P candidate, and governance-accepted coverage on one frozen denominator."""
    if set(method_execution_started_at_utc) != {"B0", "P"}:
        raise MonoA1Error("RQ2 requires execution start timestamps for both B0 and P")
    execution_starts = {
        arm: _parse_timestamp(value) for arm, value in method_execution_started_at_utc.items()
    }
    reference, reference_digest, _ = load_verified_reference(
        reference_directory,
        repository=repository,
        method_execution_started_at_utc=min(execution_starts.values()).isoformat(),
    )
    denominator = reference["obligation_denominator"]
    required_ids = list(denominator["required_obligation_ids"])
    if set(declared_denominator_ids) != set(required_ids):
        raise MonoA1Error("RQ2 declared denominator differs from the sealed reference denominator")
    if set(run_ids) != {"B0", "P"} or run_ids["B0"] == run_ids["P"]:
        raise MonoA1Error("RQ2 requires distinct explicit B0 and P run identities")
    if candidate_validation not in {"NOT_RUN", "VALID", "INVALID", "UNKNOWN", "NOT_APPLICABLE"}:
        raise MonoA1Error("RQ2 candidate validation status is not recognized")
    if governance_status not in {"NOT_RUN", "ACCEPT", "REJECT", "HOLD", "UNKNOWN", "HISTORICAL"}:
        raise MonoA1Error("RQ2 governance status is not recognized")
    for label, digest in (
        ("P candidate configuration", candidate_configuration_sha256),
        ("P accepted configuration", accepted_configuration_sha256),
    ):
        if digest is not None and not SHA256_RE.fullmatch(digest):
            raise MonoA1Error(f"{label} identity must be a full lowercase SHA-256")
    evidence_by_key: dict[tuple[str, str, str, str], Mapping[str, Any]] = {}
    for item in evidence_records:
        key = (
            str(item["run_id"]),
            str(item["configuration_role"]),
            str(item["obligation_id"]),
            str(item["representation_id"]),
        )
        if key in evidence_by_key:
            raise MonoA1Error("Duplicate evidence rows share a run, role, and exact pair")
        evidence_by_key[key] = item
    rows: list[dict[str, Any]] = []
    after_sha = reference["architecture"]["after"]["commit_sha"]
    roles = {
        "B0": ("B0_FROZEN", reference["methods"]["B0"]["configuration_sha256"]),
        "P_PROPOSED_CANDIDATE": ("P_PROPOSED_CANDIDATE", candidate_configuration_sha256),
        "P_GOVERNANCE_ACCEPTED": ("P_GOVERNANCE_ACCEPTED", accepted_configuration_sha256),
    }
    after_state = reference["architecture"]["after"]["state_id"]
    for obligation_id in required_ids:
        obligation = next(
            item
            for item in reference["obligation_universe"]
            if item["obligation_id"] == obligation_id
        )
        role_states: dict[str, list[str]] = {key: [] for key in roles}
        for required_pair in obligation["required_exact_pairs"]:
            for output_key, (role, configuration_sha) in roles.items():
                arm = "B0" if output_key == "B0" else "P"
                if configuration_sha is None:
                    role_states[output_key].append("UNKNOWN")
                    continue
                evidence_key = (
                    run_ids[arm],
                    role,
                    obligation_id,
                    required_pair["representation_id"],
                )
                match = evidence_by_key.get(evidence_key)
                if match is None:
                    role_states[output_key].append("UNKNOWN")
                    continue
                evaluator_identity = next(
                    (
                        item
                        for item in reference["evaluator_artifacts"]
                        if item["evaluator_id"] == required_pair["evaluator_id"]
                    ),
                    None,
                )
                role_states[output_key].append(
                    verify_exact_pair_evidence(
                        match,
                        study_id=reference["study_id"],
                        run_id=run_ids[arm],
                        architecture_state=after_state,
                        architecture_source_sha=after_sha,
                        representation_id=required_pair["representation_id"],
                        obligation_id=obligation_id,
                        configuration_role=role,
                        configuration_sha256=configuration_sha,
                        expected_evaluator=evaluator_identity,
                        independent_verifier=independent_verifier,
                        artifact_root=(evidence_root_by_arm or {}).get(arm),
                        require_production_authority=False,
                    )
                )

        def coverage(values: list[str]) -> str:
            if values and all(value == "VERIFIED" for value in values):
                return "COVERED"
            if (
                values
                and all(value in {"VERIFIED", "DIAGNOSTIC_ONLY"} for value in values)
                and "DIAGNOSTIC_ONLY" in values
            ):
                return "DIAGNOSTIC_ONLY"
            return "UNKNOWN"

        b0_state = coverage(role_states["B0"])
        candidate_state = (
            coverage(role_states["P_PROPOSED_CANDIDATE"])
            if candidate_validation == "VALID"
            else "UNKNOWN"
        )
        if governance_status != "ACCEPT" or candidate_validation != "VALID":
            accepted_state = "ABSENT"
        elif not accepted_configuration_sha256:
            accepted_state = "UNKNOWN"
        else:
            accepted_coverage = coverage(role_states["P_GOVERNANCE_ACCEPTED"])
            accepted_state = (
                accepted_coverage
                if accepted_coverage in {"COVERED", "DIAGNOSTIC_ONLY"}
                else "UNKNOWN"
            )
        rows.append(
            {
                "obligation_id": obligation_id,
                "B0": b0_state,
                "P_candidate_potential": candidate_state,
                "P_governance_accepted": accepted_state,
            }
        )
    complete = denominator["complete"]
    pcts: dict[str, float | None] = {}
    keys = {
        "B0_coverage_percentage": "B0",
        "P_candidate_potential_coverage_percentage": "P_candidate_potential",
        "P_governance_accepted_coverage_percentage": "P_governance_accepted",
    }
    for output_key, row_key in keys.items():
        values = [row[row_key] for row in rows]
        allowed = {"COVERED", "ABSENT"} if row_key == "P_governance_accepted" else {"COVERED"}
        if complete and values and all(value in allowed for value in values):
            if row_key == "P_governance_accepted" and all(value == "ABSENT" for value in values):
                pcts[output_key] = None
            else:
                pcts[output_key] = 100.0 * sum(value == "COVERED" for value in values) / len(values)
        else:
            pcts[output_key] = None
    status = (
        "SCORED"
        if complete
        and all(
            value == "COVERED"
            for row in rows
            for value in (row["B0"], row["P_candidate_potential"], row["P_governance_accepted"])
        )
        else "UNKNOWN"
    )
    if not complete:
        pcts = {key: None for key in pcts}
        status = "UNKNOWN"
    return {
        "status": status,
        "reference_sha256": reference_digest,
        "denominator_complete": complete,
        "denominator_obligation_ids": required_ids,
        **pcts,
        "rows": rows,
    }


def assess_mono_rq3(
    *,
    timing_boundary_ids: Mapping[str, str],
    timings_ns: Mapping[str, Mapping[str, int | None]],
    source_image_provenance: Mapping[str, Mapping[str, Any]],
    architecture_source_sha: str | None,
    resources: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return descriptive timing only for complete matched boundaries and verified images."""
    reasons: list[str] = []
    boundary = timing_boundary_ids.get("B0")
    if not boundary or timing_boundary_ids.get("P") != boundary:
        reasons.append("TIMING_BOUNDARIES_NOT_EQUIVALENT")
    required_times = ("adaptation_ns", "evaluator_ns", "verification_ns", "total_ns")
    for arm in ("B0", "P"):
        if arm not in timings_ns:
            reasons.append(f"{arm}_TIMINGS_INCOMPLETE")
        else:
            values = [timings_ns[arm].get(key) for key in required_times]
            if any(value is None for value in values):
                reasons.append(f"{arm}_TIMINGS_INCOMPLETE")
            elif any(type(value) is not int or value < 0 for value in values):
                reasons.append(f"{arm}_TIMINGS_INVALID")
        provenance = source_image_provenance.get(arm, {})
        if (
            provenance.get("status") != "VERIFIED"
            or provenance.get("source_sha") != architecture_source_sha
            or not isinstance(provenance.get("image_digest"), str)
            or not PINNED_IMAGE_RE.fullmatch(provenance.get("image_digest", ""))
            or not isinstance(provenance.get("attestation_sha256"), str)
            or not SHA256_RE.fullmatch(provenance.get("attestation_sha256", ""))
        ):
            reasons.append(f"{arm}_SOURCE_TO_IMAGE_UNVERIFIED")
    null_times = {key: timings_ns.get("B0", {}).get(key) for key in required_times}
    null_times_p = {key: timings_ns.get("P", {}).get(key) for key in required_times}
    if reasons:
        return {
            "status": "UNKNOWN",
            "timing_boundary_id": boundary,
            "B0": null_times,
            "P": null_times_p,
            "resource_measurements": _resource_record(resources),
            "reason_codes": sorted(set(reasons)),
        }
    return {
        "status": "DESCRIPTIVE",
        "timing_boundary_id": boundary,
        "B0": dict(timings_ns["B0"]),
        "P": dict(timings_ns["P"]),
        "resource_measurements": _resource_record(resources),
        "reason_codes": [],
        "inference_limit": "single transition; descriptive only",
    }


def validate_source_image_provenance(
    record: Mapping[str, Any], architecture_source_sha: str
) -> bool:
    """Check an externally verified image attestation's shape and source binding."""
    return bool(
        record.get("status") == "VERIFIED"
        and record.get("source_sha") == architecture_source_sha
        and isinstance(record.get("image_digest"), str)
        and PINNED_IMAGE_RE.fullmatch(record.get("image_digest", ""))
        and isinstance(record.get("attestation_sha256"), str)
        and SHA256_RE.fullmatch(record.get("attestation_sha256", ""))
    )


def write_evidence_inventory(directory: Path) -> dict[str, Any]:
    """Write a deterministic checksum inventory once, excluding its self-referential bytes."""
    if not directory.is_dir() or directory.is_symlink():
        raise MonoA1Error("Evidence inventory root must be a regular directory")
    entries = _inventory_entries(directory, excluded={INVENTORY_NAME})
    payload = {"schema_version": "mono-a1-evidence-inventory-v1", "entries": entries}
    _write_once(directory / INVENTORY_NAME, pretty_json_bytes(payload), readonly=True)
    return payload


def verify_evidence_inventory(directory: Path) -> dict[str, Any]:
    """Reject missing, extra, symlinked, or changed artifacts against the inventory."""
    if directory.is_symlink() or not directory.is_dir():
        raise MonoA1Error("Evidence inventory root must be a regular directory")
    inventory_path = directory / INVENTORY_NAME
    if inventory_path.is_symlink() or not inventory_path.is_file():
        raise MonoA1Error("Evidence checksum inventory must be a regular file")
    try:
        inventory = cast(dict[str, Any], json.loads(inventory_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as error:
        raise MonoA1Error("Evidence checksum inventory is missing or malformed") from error
    if inventory.get("schema_version") != "mono-a1-evidence-inventory-v1":
        raise MonoA1Error("Evidence checksum inventory schema version is unsupported")
    expected = inventory.get("entries")
    if not isinstance(expected, list):
        raise MonoA1Error("Evidence checksum entries are malformed")
    actual = _inventory_entries(directory, excluded={INVENTORY_NAME})
    if actual != expected:
        raise MonoA1Error("Evidence inventory differs from the run directory bytes")
    return inventory


def create_mono_archive(directory: Path, archive_path: Path) -> tuple[str, dict[str, Any]]:
    """Create a digest-sidecar archive, then verify it after clean extraction."""
    if archive_path.exists() or archive_path.is_symlink():
        raise MonoA1Error("MONO evidence archive is write-once")
    inventory = verify_evidence_inventory(directory)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise MonoA1Error("Evidence archive refuses symlinks")
            if path.is_file():
                archive.write(path, path.relative_to(directory).as_posix())
    archive_digest = sha256_file(archive_path)
    sidecar = archive_path.with_name(archive_path.name + ARCHIVE_SIDE_CAR_SUFFIX)
    _write_once(sidecar, f"{archive_digest}  {archive_path.name}\n".encode("ascii"), readonly=True)
    readback = verify_mono_archive(archive_path, expected_sha256=archive_digest)
    return archive_digest, {"inventory": inventory, "readback": readback}


def verify_mono_archive(
    archive_path: Path, *, expected_sha256: str | None = None
) -> dict[str, Any]:
    """Verify archive sidecar, safe member names, ZIP CRCs, and clean-extraction inventory."""
    if not archive_path.is_file() or archive_path.is_symlink():
        raise MonoA1Error("MONO archive is missing or symlinked")
    actual_digest = sha256_file(archive_path)
    sidecar = archive_path.with_name(archive_path.name + ARCHIVE_SIDE_CAR_SUFFIX)
    if sidecar.is_symlink() or not sidecar.is_file():
        raise MonoA1Error("MONO archive checksum sidecar must be a regular file")
    try:
        sidecar_parts = sidecar.read_text(encoding="ascii").split(maxsplit=1)
        sidecar_digest = sidecar_parts[0]
    except (OSError, IndexError, UnicodeDecodeError) as error:
        raise MonoA1Error("MONO archive checksum sidecar is missing or malformed") from error
    sidecar_name = sidecar_parts[1].lstrip("*").strip() if len(sidecar_parts) > 1 else ""
    if not SHA256_RE.fullmatch(sidecar_digest) or sidecar_name != archive_path.name:
        raise MonoA1Error("MONO archive checksum sidecar digest is malformed")
    if expected_sha256 is not None and not SHA256_RE.fullmatch(expected_sha256):
        raise MonoA1Error("Expected MONO archive digest must be a full lowercase SHA-256")
    if actual_digest != sidecar_digest or (expected_sha256 and actual_digest != expected_sha256):
        raise MonoA1Error("MONO archive digest mismatch")
    with tempfile.TemporaryDirectory(prefix="mono-a1-readback-") as temporary:
        extraction_root = Path(temporary)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                names = [item.filename for item in archive.infolist()]
                if len(names) != len(set(names)) or archive.testzip() is not None:
                    raise MonoA1Error("MONO archive contains duplicate or corrupt ZIP entries")
                for item in archive.infolist():
                    _validate_archive_member(item)
                archive.extractall(extraction_root)
        except (OSError, zipfile.BadZipFile) as error:
            raise MonoA1Error("MONO archive could not be safely read back") from error
        inventory = verify_evidence_inventory(extraction_root)
        return {
            "verified": True,
            "archive_sha256": actual_digest,
            "artifact_count": len(inventory["entries"]),
        }


def _verify_raw_evidence_artifacts(
    artifacts: Sequence[Mapping[str, Any]], root: Path | None
) -> bool:
    if root is None or not artifacts:
        return False
    try:
        evidence_root = root.resolve(strict=True)
    except OSError:
        return False
    if not evidence_root.is_dir() or root.is_symlink():
        return False
    seen: set[str] = set()
    for artifact in artifacts:
        relative = PurePosixPath(str(artifact.get("path", "")))
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in str(relative)
            or not relative.parts
        ):
            return False
        current = evidence_root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return False
        try:
            resolved = current.resolve(strict=True)
        except OSError:
            return False
        if evidence_root not in resolved.parents or not resolved.is_file():
            return False
        name = relative.as_posix()
        if name in seen or sha256_file(resolved) != artifact.get("sha256"):
            return False
        seen.add(name)
    return True


def _score_prediction(
    reference: Mapping[str, Any], prediction: Mapping[str, Any]
) -> dict[str, Any]:
    validate_prediction(dict(prediction))
    universe = {
        (str(row["target_type"]), str(row["target_id"])): str(row["expected_operation"])
        for row in reference["target_universe"]
    }
    emitted: dict[tuple[str, str], str] = {}
    for item in prediction["proposed_operations"]:
        key = (str(item["target_type"]), str(item["target_id"]))
        if key in emitted:
            raise MonoA1Error("Prediction contains duplicate target operations")
        emitted[key] = str(item["operation"])
    positive = {
        (str(item["target_type"]), str(item["target_id"]))
        for item in prediction["predicted_affected"]
    }
    operation_confusion = {
        expected: {predicted: 0 for predicted in sorted(OPERATIONS)}
        for expected in sorted(OPERATIONS)
    }
    for target, expected_operation in universe.items():
        predicted_operation = emitted.get(target, "retain")
        operation_confusion[expected_operation][predicted_operation] += 1
    expected_positive = {key for key, operation in universe.items() if operation != "retain"}
    tp = len(expected_positive & positive)
    fp_in = len((positive & set(universe)) - expected_positive)
    fp_extra = len(positive - set(universe))
    fn = len(expected_positive - positive)
    tn = len({key for key, operation in universe.items() if operation == "retain"} - positive)
    precision = tp / (tp + fp_in + fp_extra) if tp + fp_in + fp_extra else None
    recall = tp / (tp + fn) if tp + fn else None
    f1_denom = 2 * tp + fp_in + fp_extra + fn
    f1 = (2 * tp / f1_denom) if f1_denom else None
    correct = sum(emitted.get(key, "retain") == operation for key, operation in universe.items())
    return {
        "TP": tp,
        "FP_in": fp_in,
        "FP_extra": fp_extra,
        "FN": fn,
        "TN": tn,
        "precision": precision,
        "recall": recall,
        "F1": f1,
        "operation_accuracy": correct / len(universe) if universe else None,
        "operation_confusion": operation_confusion,
        "target_count": len(universe),
    }


def _verify_rq3_prerequisites(
    boundary: str | None,
    b0: Mapping[str, Any],
    p: Mapping[str, Any],
    b0_provenance: Mapping[str, Any],
    p_provenance: Mapping[str, Any],
    architecture_sha: str | None,
) -> None:
    if not boundary or any(
        value is None
        for arm in (b0, p)
        for value in (
            arm["adaptation_ns"],
            arm["evaluator_ns"],
            arm["verification_ns"],
            arm["total_ns"],
        )
    ):
        raise MonoA1Error("RQ3 DESCRIPTIVE requires complete matched timer measurements")
    if (
        not architecture_sha
        or not validate_source_image_provenance(b0_provenance, architecture_sha)
        or not validate_source_image_provenance(p_provenance, architecture_sha)
    ):
        raise MonoA1Error(
            "RQ3 DESCRIPTIVE requires verified source-to-image provenance for both arms"
        )


def _resource_record(resources: Mapping[str, Any] | None) -> dict[str, Any]:
    values = resources or {}
    cpu = values.get("cpu_millicores")
    rss = values.get("rss_bytes")
    cpu_status = str(values.get("cpu_status", "UNKNOWN"))
    rss_status = str(values.get("rss_status", "UNKNOWN"))
    if cpu is not None and (type(cpu) not in {int, float} or cpu < 0):
        raise MonoA1Error("CPU resource measurement must be a non-negative number")
    if rss is not None and (type(rss) is not int or rss < 0):
        raise MonoA1Error("RSS resource measurement must be a non-negative integer")
    if cpu is None and cpu_status == "MEASURED":
        raise MonoA1Error("Measured CPU status requires a numeric measurement")
    if rss is None and rss_status == "MEASURED":
        raise MonoA1Error("Measured RSS status requires a byte measurement")
    return {
        "cpu_status": "MEASURED" if cpu is not None else cpu_status,
        "cpu_millicores": cpu,
        "rss_status": "MEASURED" if rss is not None else rss_status,
        "rss_bytes": rss,
    }


def _inventory_entries(directory: Path, *, excluded: set[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise MonoA1Error("Evidence inventory refuses symlinks")
        if path.is_file():
            relative = path.relative_to(directory).as_posix()
            if relative in excluded:
                continue
            entries.append(
                {"path": relative, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
            )
    return entries


def _validate_archive_member(member: zipfile.ZipInfo) -> None:
    path = PurePosixPath(member.filename)
    if path.is_absolute() or ".." in path.parts or "\\" in member.filename or not path.parts:
        raise MonoA1Error("MONO archive contains an unsafe member path")
    mode = member.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise MonoA1Error("MONO archive contains a symlink entry")


def _write_once(path: Path, content: bytes, *, readonly: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o444 if readonly else 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if readonly:
            path.chmod(0o444)
    except OSError:
        path.unlink(missing_ok=True)
        raise


def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key).lower() in SENSITIVE_JSON_KEYS or _contains_sensitive_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise MonoA1Error("Timestamp must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None:
        raise MonoA1Error("Timestamp must include a timezone")
    return parsed.astimezone(UTC)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


__all__ = [
    "MonoA1Error",
    "W2A1ExactPairReadbackVerifier",
    "assess_mono_rq3",
    "create_mono_archive",
    "freeze_reference",
    "load_verified_reference",
    "score_mono_rq1",
    "score_mono_rq2",
    "validate_mono_reference",
    "validate_mono_study",
    "validate_source_image_provenance",
    "verify_evidence_inventory",
    "verify_exact_pair_evidence",
    "verify_method_input_isolation",
    "verify_mono_archive",
    "verify_source_revision",
    "write_evidence_inventory",
]
