"""Read-only validation of the proposed MONO-E1 A0.3 CI configuration."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess  # nosec B404 - fixed local Git readback, no shell
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, cast
from zipfile import BadZipFile, ZipFile

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path("fitness/configs/mono-e1-b0-dev-a03-v1.yaml")
SCHEMA_PATH = Path("fitness/configs/mono-e1-b0-dev-a03-v1.schema.json")
A03_SHA = "26a9bb667da7d0938e38aca15d2bf29fd1de4829"
A04_SHA = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
A04_APP_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
EXPECTED_VALIDATION_ARCHIVES = {
    "EVAL-01": "experiments/pilots/EVAL01_RAW_EVIDENCE_V1.zip",
    "EVAL-02": "experiments/pilots/EVAL02_RAW_EVIDENCE_V1.zip",
}
GIT_EXECUTABLE = shutil.which("git")


class FitnessConfigurationValidationError(ValueError):
    """Raised when a DEVELOPMENT configuration or its evidence is inconsistent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FitnessConfigurationValidationError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_repository_path(root: Path, value: str) -> Path:
    relative = PurePosixPath(value)
    _require(
        not relative.is_absolute() and ".." not in relative.parts and "\\" not in value,
        f"Unsafe repository artifact path: {value}",
    )
    resolved_root = root.resolve()
    resolved_path = (resolved_root / Path(*relative.parts)).resolve()
    _require(
        resolved_path == resolved_root or resolved_root in resolved_path.parents,
        f"Artifact path escapes repository root: {value}",
    )
    return resolved_path


def _read_artifact(root: Path, record: Mapping[str, Any]) -> bytes:
    path = _safe_repository_path(root, str(record["path"]))
    _require(path.is_file(), f"Missing evidence artifact: {record['path']}")
    payload = path.read_bytes()
    _require(
        _sha256(payload) == record["sha256"],
        f"Evidence digest mismatch: {record['path']}",
    )
    return payload


def _git_bytes(root: Path, revision: str, path: str) -> bytes:
    _require(GIT_EXECUTABLE is not None, "Git is required for canonical source readback")
    _require(
        not PurePosixPath(path).is_absolute() and ".." not in PurePosixPath(path).parts,
        f"Unsafe Git source path: {path}",
    )
    completed = subprocess.run(  # noqa: S603  # nosec B603 - fixed Git argv, no shell
        [cast(str, GIT_EXECUTABLE), "show", f"{revision}:{path}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    _require(
        completed.returncode == 0,
        f"Git source readback failed for {revision}:{path}",
    )
    return completed.stdout


def _git_text(root: Path, *arguments: str) -> str:
    _require(GIT_EXECUTABLE is not None, "Git is required for canonical source readback")
    completed = subprocess.run(  # noqa: S603  # nosec B603 - fixed Git argv, no shell
        [cast(str, GIT_EXECUTABLE), *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    _require(completed.returncode == 0, f"Git identity readback failed: {' '.join(arguments)}")
    return completed.stdout.strip()


def validate_document(config: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    """Validate schema and cross-row identities without reading repository evidence."""
    Draft202012Validator.check_schema(dict(schema))
    errors = sorted(
        Draft202012Validator(dict(schema)).iter_errors(config),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise FitnessConfigurationValidationError(
            f"Configuration schema error at {location}: {first.message}"
        )

    _validate_development_validation_records(config)

    representations = cast(Sequence[Mapping[str, Any]], config["representations"])
    representation_ids = [str(row["id"]) for row in representations]
    evaluator_ids = [str(row["evaluator"]["id"]) for row in representations]
    obligation_ids = [str(row["id"]) for row in config["obligations"]]
    mapping_ids = [str(row["obligation_id"]) for row in representations]
    _require(
        len(representation_ids) == len(set(representation_ids)),
        "Representation identities must be unique",
    )
    _require(len(evaluator_ids) == len(set(evaluator_ids)), "Evaluator identities must be unique")
    _require(
        not set(representation_ids).intersection(evaluator_ids),
        "Evaluator identities must remain distinct from representation identities",
    )
    _require(
        len(obligation_ids) == len(set(obligation_ids)),
        "Architectural obligation identities must be unique",
    )
    _require(
        sorted(mapping_ids) == sorted(obligation_ids),
        "Each candidate representation must map to exactly one listed obligation",
    )
    expected_mappings = {
        "REP_MONO_E1_DEV_A03_PUBLIC_API_CI_V1": "AC_PUBLIC_API",
        "REP_MONO_E1_DEV_A03_MODULE_GRAPH_CI_V1": "AC_MODULE_GRAPH",
    }
    _require(
        {str(row["id"]): str(row["obligation_id"]) for row in representations} == expected_mappings,
        "Representation-to-obligation bindings contradict the DEVELOPMENT contract",
    )


def _validate_development_validation_records(config: Mapping[str, Any]) -> None:
    records = cast(Sequence[Mapping[str, Any]], config["development_validation_evidence"])
    experiment_ids = [str(record["experiment_id"]) for record in records]
    expected_ids = set(EXPECTED_VALIDATION_ARCHIVES)
    _require(
        len(experiment_ids) == len(set(experiment_ids)),
        "Development validation evidence contains duplicate experiment IDs",
    )
    _require(
        set(experiment_ids) == expected_ids,
        "Development validation evidence must contain exactly one EVAL-01 and one EVAL-02 record",
    )
    for record in records:
        experiment_id = str(record["experiment_id"])
        archive = cast(Mapping[str, Any], record["archive"])
        _require(
            archive["path"] == EXPECTED_VALIDATION_ARCHIVES[experiment_id],
            f"{experiment_id} is bound to the wrong evidence archive",
        )


def _load_checkpoint(root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    checkpoint_bytes = _read_artifact(root, cast(Mapping[str, Any], state["checkpoint"]))
    checkpoint = cast(dict[str, Any], json.loads(checkpoint_bytes))
    source = cast(dict[str, Any], checkpoint.get("source", checkpoint))
    expected_source = {
        "source_sha": state["source_sha"],
        "repository_tree_sha": state["repository_tree_sha"],
        "application_tree_sha": state["application_tree_sha"],
    }
    actual_source = {
        "source_sha": source.get("source_sha"),
        "repository_tree_sha": source.get("repository_tree_sha"),
        "application_tree_sha": source.get("application_tree_sha"),
    }
    _require(actual_source == expected_source, "Canonical checkpoint source identity mismatch")
    _require(
        checkpoint.get("readback_status") == "PASS", "Canonical checkpoint readback did not pass"
    )
    _require(
        _git_text(root, "rev-parse", f"{state['source_sha']}^{{tree}}")
        == state["repository_tree_sha"],
        f"Git repository tree does not match {state['architecture_state']}",
    )
    _require(
        _git_text(root, "rev-parse", f"{state['source_sha']}:app") == state["application_tree_sha"],
        f"Git application tree does not match {state['architecture_state']}",
    )
    state_manifest = cast(Mapping[str, Any], state["state_manifest"])
    source_manifest = cast(Mapping[str, Any], state["source_manifest"])
    _require(
        _sha256(_git_bytes(root, str(state["source_sha"]), str(state_manifest["path"])))
        == state_manifest["sha256"],
        f"Pinned state manifest bytes changed for {state['architecture_state']}",
    )
    _read_artifact(root, source_manifest)
    return checkpoint


def _verify_historical_a0_b0(root: Path, config: Mapping[str, Any]) -> None:
    historical = cast(Mapping[str, Any], config["provenance"]["historical_a0_b0"])
    source_revision = str(historical["source_revision"])
    _require(
        _git_text(root, "rev-parse", f"{historical['source_tag']}^{{commit}}") == source_revision,
        "Frozen A0 B0 source tag identity changed",
    )
    configuration = cast(Mapping[str, Any], historical["configuration"])
    configuration_path = str(configuration["path"])
    configuration_digest = str(configuration["sha256"])
    _require(
        _sha256(_git_bytes(root, source_revision, configuration_path)) == configuration_digest,
        "Frozen A0 B0 configuration bytes changed at the frozen source revision",
    )
    _require(
        _sha256(_git_bytes(root, A03_SHA, configuration_path)) == configuration_digest,
        "Frozen A0 B0 configuration bytes changed in the canonical A0.3 tree",
    )
    _require(
        _sha256(_safe_repository_path(root, configuration_path).read_bytes())
        == configuration_digest,
        "Working-tree frozen A0 B0 configuration bytes changed",
    )

    supporting_revision = str(historical["supporting_artifacts_source_revision"])
    for key in ("representation_catalog", "traceability", "frozen_evaluator"):
        artifact = cast(Mapping[str, Any], historical[key])
        path = str(artifact["path"])
        expected = str(artifact["sha256"])
        _require(
            _sha256(_git_bytes(root, supporting_revision, path)) == expected,
            f"Frozen A0 B0 supporting artifact bytes changed at the recorded A0.3 readback: {path}",
        )
        _require(
            _sha256(_safe_repository_path(root, path).read_bytes()) == expected,
            f"Working-tree frozen A0 B0 supporting artifact bytes changed: {path}",
        )


def _verify_source_artifacts(
    root: Path, config: Mapping[str, Any], states: Sequence[Mapping[str, Any]]
) -> None:
    artifacts = cast(
        Sequence[Mapping[str, Any]],
        config["provenance"]["evaluator_implementation"]["source_artifacts"],
    )
    aggregate_digest = str(config["provenance"]["evaluator_implementation"]["aggregate_sha256"])
    for artifact in artifacts:
        expected = str(artifact["sha256"])
        for state in states:
            actual = _sha256(_git_bytes(root, str(state["source_sha"]), str(artifact["path"])))
            _require(
                actual == expected,
                f"Evaluator source digest mismatch at {state['architecture_state']}: "
                f"{artifact['path']}",
            )

    obligation_catalog = cast(Mapping[str, Any], config["provenance"]["obligation_catalog"])
    _require(
        _sha256(_git_bytes(root, A03_SHA, str(obligation_catalog["path"])))
        == obligation_catalog["sha256"],
        "Pinned A0.3 obligation catalog bytes changed",
    )

    representations = cast(Sequence[Mapping[str, Any]], config["representations"])
    for representation in representations:
        evaluator = cast(Mapping[str, Any], representation["evaluator"])
        artifact = cast(Mapping[str, Any], evaluator["configuration_artifact"])
        expected_digest = str(artifact["sha256"])
        for state in states:
            source_config = _git_bytes(root, str(state["source_sha"]), str(artifact["path"]))
            _require(
                _sha256(source_config) == expected_digest,
                f"Evaluator configuration digest mismatch for {evaluator['id']}",
            )
            evaluator_config = cast(dict[str, Any], yaml.safe_load(source_config.decode("utf-8")))
            identity = cast(Mapping[str, Any], evaluator_config["evaluator"])
            _require(
                identity.get("id") == evaluator["id"]
                and identity.get("obligation_id") == representation["obligation_id"]
                and identity.get("version") == evaluator["version"],
                f"Evaluator/configuration/obligation binding mismatch for {evaluator['id']}",
            )

    for state in states:
        checkpoint = _load_checkpoint(root, state)
        checkpoint_evaluators = cast(Mapping[str, Any], checkpoint["evaluators"])
        for representation in representations:
            evaluator = cast(Mapping[str, Any], representation["evaluator"])
            evaluator_id = str(evaluator["id"])
            record = cast(Mapping[str, Any], checkpoint_evaluators[evaluator_id])
            source_digest = record.get("evaluator_sha256")
            _require(
                source_digest == aggregate_digest == evaluator["source_digest_sha256"],
                f"Evaluator implementation digest mismatch for {evaluator_id}",
            )
            evidence = next(
                item
                for item in cast(Sequence[Mapping[str, Any]], representation["evidence_by_state"])
                if item["architecture_state"] == state["architecture_state"]
            )
            _require(
                evidence["checkpoint_sha256"] == state["checkpoint"]["sha256"],
                f"Evidence references the wrong checkpoint for {evaluator_id}",
            )
            _require(
                record.get("configuration_sha256") == evaluator["configuration_artifact"]["sha256"]
                and record.get("evidence_file_sha256") == evidence["observation"]["sha256"]
                and record.get("execution_status") == evidence["execution_status"]
                and record.get("compliance") == evidence["compliance"]
                and record.get("source_scope_complete") is evidence["source_scope"]["complete"]
                and record.get("inspected_files")
                == evidence["source_scope"]["inspected_python_files"]
                and record.get("inspected_imports")
                == evidence["source_scope"]["inspected_import_nodes"],
                f"Checkpoint record contradicts configuration evidence for {evaluator_id}",
            )
            raw_digest = record.get("raw_diagnostics_sha256", record.get("raw_output_file_sha256"))
            _require(
                raw_digest == evidence["raw_diagnostics"]["sha256"],
                f"Raw diagnostics digest mismatch for {evaluator_id}",
            )
            _read_artifact(root, cast(Mapping[str, Any], evidence["observation"]))
            _read_artifact(root, cast(Mapping[str, Any], evidence["raw_diagnostics"]))


def _verify_archive_integrity(
    root: Path, record: Mapping[str, Any], experiment_id: str
) -> dict[str, Any]:
    _require(
        record["path"] == EXPECTED_VALIDATION_ARCHIVES[experiment_id],
        f"{experiment_id} is bound to the wrong evidence archive",
    )
    archive_path = _safe_repository_path(root, str(record["path"]))
    sidecar_path = _safe_repository_path(root, f"{record['path']}.sha256")
    _require(
        archive_path.is_file() and sidecar_path.is_file(),
        "Evaluator evidence archive or sidecar is missing",
    )
    actual_digest = _sha256(archive_path.read_bytes())
    sidecar_fields = sidecar_path.read_text(encoding="utf-8").split()
    _require(
        sidecar_fields and sidecar_fields[0] == record["sha256"] == actual_digest,
        f"Evaluator evidence archive digest mismatch: {record['path']}",
    )

    try:
        with ZipFile(archive_path) as archive:
            members = archive.namelist()
            _require(len(members) == len(set(members)), "Evidence archive contains duplicate paths")
            _require(archive.testzip() is None, "Evidence archive has a ZIP CRC error")
            _require("SHA256SUMS" in members, "Evidence archive has no internal checksum inventory")
            checksum_rows: dict[str, str] = {}
            for line_number, line in enumerate(
                archive.read("SHA256SUMS").decode("utf-8").splitlines(), 1
            ):
                fields = line.split(maxsplit=1)
                _require(len(fields) == 2, f"Malformed SHA256SUMS row {line_number}")
                digest, relative_path = fields
                relative = PurePosixPath(relative_path.strip().lstrip("*"))
                _require(
                    not relative.is_absolute() and ".." not in relative.parts,
                    f"Unsafe archive checksum path: {relative_path}",
                )
                checksum_rows[relative.as_posix()] = digest
            _require(
                set(checksum_rows) == set(members) - {"SHA256SUMS"},
                "Archive member inventory differs from SHA256SUMS",
            )
            for name, digest in checksum_rows.items():
                _require(
                    _sha256(archive.read(name)) == digest,
                    f"Archive member checksum mismatch: {name}",
                )
            manifest = cast(dict[str, Any], json.loads(archive.read("run-manifest.json")))
            analysis_name = f"{experiment_id.replace('-', '')}_ANALYSIS_V1.json"
            analysis = cast(dict[str, Any], json.loads(archive.read(analysis_name)))
            runs = [
                json.loads(line)
                for line in archive.read("execution.jsonl").decode("utf-8").splitlines()
                if line.strip()
            ]
    except (BadZipFile, KeyError, json.JSONDecodeError) as error:
        raise FitnessConfigurationValidationError(
            f"Invalid evaluator evidence archive: {record['path']}"
        ) from error

    return {
        "manifest": manifest,
        "analysis": analysis,
        "run_count": len(runs),
        "internal_checksums_verified": len(checksum_rows),
    }


def _verify_validation_evidence(root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    _validate_development_validation_records(config)
    states = cast(Sequence[Mapping[str, Any]], config["provenance"]["canonical_states"])
    a04 = next(state for state in states if state["architecture_state"] == "A0_4_REPORT_QUERY_PORT")
    summaries: dict[str, Any] = {}
    for validation in cast(Sequence[Mapping[str, Any]], config["development_validation_evidence"]):
        experiment_id = str(validation["experiment_id"])
        archive_data = _verify_archive_integrity(
            root, cast(Mapping[str, Any], validation["archive"]), experiment_id
        )
        manifest = cast(Mapping[str, Any], archive_data["manifest"])
        analysis = cast(Mapping[str, Any], archive_data["analysis"])
        _require(
            manifest.get("experiment_id") == experiment_id,
            f"{experiment_id} record does not match the archive's experiment ID",
        )
        _require(
            manifest["source_baseline"]["commit_sha"] == validation["source_sha"] == A04_SHA
            and manifest["source_baseline"]["application_tree_sha"] == a04["application_tree_sha"],
            f"{experiment_id} is bound to the wrong source",
        )
        _require(
            manifest["evaluator_source_digest"] == validation["evaluator_source_digest_sha256"],
            f"{experiment_id} evaluator source digest mismatch",
        )
        _require(
            manifest["execution_environment"]["planned_evaluator_calls"]
            == validation["calls_completed"]
            == archive_data["run_count"],
            f"{experiment_id} call inventory mismatch",
        )
        _require(
            len(manifest["failures"]) == validation["diagnostic_mismatches"]
            and len(manifest["failures"]) == 0 + int(validation["diagnostic_mismatches"]),
            f"{experiment_id} failure inventory mismatch",
        )
        _require(
            manifest["analysis_raw_inventory_verification"] == "PASS"
            and analysis["raw_inventory_verification"] == "PASS",
            f"{experiment_id} raw analysis inventory did not pass",
        )
        expected_archive_sources = [
            {
                "path": PurePosixPath(str(row["path"])).name,
                "sha256": row["sha256"],
            }
            for row in config["provenance"]["evaluator_implementation"]["source_artifacts"]
        ]
        _require(
            manifest["evaluator_source_artifacts"] == expected_archive_sources,
            f"{experiment_id} evaluator source files differ from configuration",
        )
        expected_configs = {
            str(row["evaluator"]["id"]): {
                "path": row["evaluator"]["configuration_artifact"]["path"],
                "sha256": row["evaluator"]["configuration_artifact"]["sha256"],
            }
            for row in cast(Sequence[Mapping[str, Any]], config["representations"])
        }
        _require(
            manifest["configurations"] == expected_configs,
            f"{experiment_id} evaluator configuration bindings differ",
        )
        _require(
            analysis["evaluator_metrics"]
            and set(analysis["evaluator_metrics"]) == {"AC_PUBLIC_API", "AC_MODULE_GRAPH"},
            f"{experiment_id} does not contain both evaluator results",
        )
        expected_matrices = cast(Mapping[str, Any], validation["confusion_matrices"])
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH"):
            matrix = cast(
                Mapping[str, Any],
                analysis["evaluator_metrics"][evaluator_id]["confusion_matrix"],
            )
            _require(
                matrix == expected_matrices[evaluator_id],
                f"{experiment_id} binary outcomes differ for {evaluator_id}",
            )
            _require(
                matrix["tp"] > 0 and matrix["tn"] > 0 and matrix["fp"] == 0 and matrix["fn"] == 0,
                f"{experiment_id} lacks both positive and negative controls for {evaluator_id}",
            )
        summaries[str(validation["experiment_id"])] = {
            "archive_sha256": validation["archive"]["sha256"],
            "calls_completed": archive_data["run_count"],
            "diagnostic_mismatches": len(manifest["failures"]),
            "internal_checksums_verified": archive_data["internal_checksums_verified"],
            "confusion_matrices": dict(expected_matrices),
        }

    eval02 = next(
        row
        for row in config["development_validation_evidence"]
        if row["experiment_id"] == "EVAL-02"
    )
    eval02_path = _safe_repository_path(root, str(eval02["archive"]["path"]))
    from experiments.pilots.validate_eval02_postrun import validate_eval02_archive

    eval02_result = validate_eval02_archive(eval02_path)
    _require(
        eval02_result["execution_status"]["diagnostic_expectation_mismatches"] == 3,
        "EVAL-02 post-run validator did not preserve the three diagnostic mismatches",
    )
    return summaries


def validate_evidence_bindings(root: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    """Verify canonical source, frozen A0 bytes, and archived evaluator controls."""
    _validate_development_validation_records(config)
    states = cast(Sequence[Mapping[str, Any]], config["provenance"]["canonical_states"])
    _require(
        {str(state["architecture_state"]) for state in states}
        == {"A0_3_GOVERNED_MODULE_GRAPH", "A0_4_REPORT_QUERY_PORT"},
        "Canonical source pair is incomplete or contradictory",
    )
    _verify_historical_a0_b0(root, config)
    _verify_source_artifacts(root, config, states)
    return _verify_validation_evidence(root, config)


def _verify_existing_gates(root: Path) -> dict[str, str]:
    profile_path = _safe_repository_path(root, "docs/mono_e1_ci_fitness_profile_v1.json")
    preflight_path = _safe_repository_path(
        root, "experiments/execution/MONO_E1_COMPARABILITY_PREFLIGHT_V1.json"
    )
    profile = cast(dict[str, Any], json.loads(profile_path.read_text(encoding="utf-8")))
    preflight = cast(dict[str, Any], json.loads(preflight_path.read_text(encoding="utf-8")))
    from experiments.execution.tooling.p_interface import P_ALGORITHM_STATUS

    status = {
        "P_ALGORITHM_STATUS": str(P_ALGORITHM_STATUS),
        "G1": str(profile["readiness"]["G1"]),
        "G4": str(profile["readiness"]["G4"]),
        "MONO_E1": str(profile["experimental_go"]),
    }
    _require(
        status
        == {
            "P_ALGORITHM_STATUS": "NOT_READY",
            "G1": "INCOMPLETE",
            "G4": "NOT_AUTHORIZED",
            "MONO_E1": "NO_GO",
        },
        "Existing P/G1/G4/MONO-E1 gate status was changed",
    )
    _require(
        preflight["preparation_status"] == "INCOMPLETE"
        and preflight["experimental_go"] == "NO_GO"
        and preflight["authority"]["G1"] == "INCOMPLETE"
        and preflight["authority"]["G4"] == "NOT_AUTHORIZED",
        "Existing MONO-E1 comparability preflight was promoted",
    )
    return status


def _load_configuration(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved_config_path = config_path if config_path.is_absolute() else root / config_path
    try:
        config = cast(
            dict[str, Any], yaml.safe_load(resolved_config_path.read_text(encoding="utf-8"))
        )
        schema_path = root / SCHEMA_PATH
        schema = cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, json.JSONDecodeError) as error:
        raise FitnessConfigurationValidationError(
            "Unable to load DEVELOPMENT configuration or schema"
        ) from error
    return config, schema


def validate_project(root: Path = ROOT, config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Validate configuration, exact source/evaluator provenance, and existing controls."""
    root = root.resolve()
    resolved_config_path = config_path if config_path.is_absolute() else root / config_path
    config, schema = _load_configuration(root, config_path)
    validate_document(config, schema)

    digest_path = _safe_repository_path(
        root, str(config["fitness_configuration_digest"]["sidecar_path"])
    )
    actual_configuration_digest = _sha256(resolved_config_path.read_bytes())
    digest_fields = digest_path.read_text(encoding="utf-8").split()
    _require(
        digest_fields and digest_fields[0] == actual_configuration_digest,
        "Fitness configuration SHA-256 sidecar mismatch",
    )

    validation_summaries = validate_evidence_bindings(root, config)
    gate_status = _verify_existing_gates(root)

    return {
        "configuration_id": config["configuration_id"],
        "configuration_version": config["configuration_version"],
        "configuration_sha256": actual_configuration_digest,
        "schema_status": "PASS",
        "historical_a0_b0_bytes": "PRESERVED",
        "canonical_source_and_checkpoint_provenance": "PASS",
        "evaluator_control_evidence": validation_summaries,
        "semantic_fitness_validity": "UNKNOWN",
        "method_input_component_status": "PROPOSED_COMPONENT_ONLY",
        "complete_method_input_bundle": False,
        "official_mono_e1_baseline_authorized": False,
        **gate_status,
        "method_p_execution_authorized": False,
    }


def main() -> int:
    """Run the read-only configuration/evidence validator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    try:
        result = validate_project(args.root, args.config)
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "INVALID",
                    "error": f"{type(error).__name__}: {error}",
                    "method_p_execution_authorized": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
