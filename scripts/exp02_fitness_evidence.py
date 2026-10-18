"""Bind EXP-01 DEVELOPMENT evaluator records to an A0.1 fitness configuration."""

import argparse
import json
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from scripts.exp01_evidence_contract import (
    ROOT,
    _safe_relative_path,
    sha256_bytes,
    validate_bundle,
)

FITNESS_CONFIGURATION_PATH = "fitness/configs/a0_1-capability-modules.dev.yaml"
FITNESS_CONFIGURATION_SCHEMA_PATH = ROOT / "fitness/configs/a0_1-capability-modules.dev.schema.json"
REPRESENTATION_EVIDENCE_SCHEMA_PATH = (
    ROOT / "experiments/schemas/fitness_representation_evidence_v1.schema.json"
)
REPRESENTATION_EVIDENCE_FILENAME = "representation_evidence.json"
EXPECTED_ARCHITECTURE_STATE = "A0_1_CAPABILITY_MODULES"


def _validate_json_schema(
    document: Any,
    schema_path: Path,
    label: str,
    schema_bytes: bytes | None = None,
) -> None:
    """Validate one JSON-compatible document against a checked-in schema."""
    schema_content = schema_bytes if schema_bytes is not None else schema_path.read_bytes()
    try:
        schema = json.loads(schema_content)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} schema is not valid JSON") from error
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValueError(f"{label} schema violation at {location}: {first.message}")


def load_fitness_configuration(
    configuration_bytes: bytes,
    obligation_catalog_bytes: bytes | None = None,
    schema_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Parse and validate an A0.1 configuration without inferring its authority."""
    try:
        parsed = yaml.safe_load(configuration_bytes)
    except yaml.YAMLError as error:
        raise ValueError("fitness configuration is not valid YAML") from error
    if not isinstance(parsed, dict):
        raise ValueError("fitness configuration must be a YAML object")
    _validate_json_schema(
        parsed,
        FITNESS_CONFIGURATION_SCHEMA_PATH,
        "fitness configuration",
        schema_bytes,
    )
    if parsed["architecture_state"] != EXPECTED_ARCHITECTURE_STATE:
        raise ValueError("fitness configuration architecture state does not match A0.1")

    if obligation_catalog_bytes is None:
        obligation_catalog_bytes = (
            ROOT / "fitness/catalog/architectural-obligations.yaml"
        ).read_bytes()
    obligation_registry = yaml.safe_load(obligation_catalog_bytes)
    known_obligations = {item["id"] for item in obligation_registry["obligations"]}
    declared_obligations = {
        obligation
        for representation in parsed["representations"]
        for obligation in representation["declared_obligations"]
    }
    unknown_obligations = declared_obligations - known_obligations
    if unknown_obligations:
        raise ValueError(
            "fitness configuration references unknown obligation IDs: "
            + ", ".join(sorted(unknown_obligations))
        )

    criterion_ids = [item["id"] for item in parsed["criteria"]]
    representation_ids = [item["id"] for item in parsed["representations"]]
    if len(criterion_ids) != len(set(criterion_ids)):
        raise ValueError("fitness configuration contains duplicate criterion identities")
    if len(representation_ids) != len(set(representation_ids)):
        raise ValueError("fitness configuration contains duplicate representation identities")
    unknown_criteria = {item["criterion_id"] for item in parsed["representations"]} - set(
        criterion_ids
    )
    if unknown_criteria:
        raise ValueError(
            "fitness representation references an unknown criterion: "
            + ", ".join(sorted(unknown_criteria))
        )
    return parsed


def _verify_artifact(run_dir: Path, reference: dict[str, Any]) -> bytes:
    """Read one safe artifact and confirm the exact bytes match its reference."""
    relative = _safe_relative_path(reference["path"])
    root = run_dir.resolve()
    target = root.joinpath(*relative.parts)
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"evidence artifact is missing or is a symlink: {reference['path']}")
    try:
        target.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"evidence artifact resolves outside the run: {reference['path']}"
        ) from error
    content = target.read_bytes()
    if len(content) != reference["size_bytes"]:
        raise ValueError(f"evidence artifact size mismatch: {reference['path']}")
    if sha256_bytes(content) != reference["sha256"]:
        raise ValueError(f"evidence artifact digest mismatch: {reference['path']}")
    return content


def _input_artifact_index(
    run_dir: Path, references: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Index digest-verified copied inputs by their repository source path."""
    by_source: dict[str, dict[str, Any]] = {}
    paths: dict[str, dict[str, Any]] = {}
    for reference in references:
        _verify_artifact(run_dir, reference)
        source_path = reference["source_path"]
        if source_path is None:
            continue
        previous = by_source.get(source_path)
        if previous is not None and previous != reference:
            raise ValueError(f"copied input identity conflicts for {source_path}")
        previous_path = paths.get(reference["path"])
        if previous_path is not None and previous_path != reference:
            raise ValueError(f"artifact identity conflicts for {reference['path']}")
        by_source[source_path] = reference
        paths[reference["path"]] = reference
    return by_source


def _record_index(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Check run and source identity, then index evaluator records by stable ID."""
    expected_run_id = bundle["run_id"]
    expected_revision = bundle["source_revision"]["commit_sha"]
    records: dict[str, dict[str, Any]] = {}
    for record in bundle["records"]:
        if record["run_id"] != expected_run_id:
            raise ValueError("evaluator record run identity conflicts with the bundle")
        if record["source_revision"] != expected_revision:
            raise ValueError("evaluator record source revision conflicts with the bundle")
        record_id = record["record_id"]
        if record_id in records:
            raise ValueError(f"duplicate evaluator record identity: {record_id}")
        records[record_id] = record
    return records


def _resolve_path(document: dict[str, Any], evidence_path: str) -> tuple[Any, str | None]:
    """Resolve a configured dotted path and retain a nearby status field when present."""
    parts = evidence_path.split(".")
    value: Any = document
    parent: Any = None
    for part in parts:
        parent = value
        if not isinstance(value, dict) or part not in value:
            return None, None
        value = value[part]
    status = parent.get("status") if isinstance(parent, dict) else None
    return value, status


def _metric_observation(
    record: dict[str, Any], metric: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Read an evaluator metric while keeping missing and invalid states explicit."""
    value, source_status = _resolve_path(record, metric["evidence_path"])
    record_status = record["status"]
    limitations: list[str] = []
    if record_status == "invalid" or source_status == "invalid":
        status = "invalid"
    elif record_status != "available" or source_status == "missing" or value is None or value == []:
        status = "missing"
    else:
        status = "available"
    if isinstance(value, dict):
        raw_limitations = value.get("limitations", [])
        if isinstance(raw_limitations, list):
            limitations.extend(str(item) for item in raw_limitations)
        if value.get("status") in {"missing", "invalid"}:
            status = value["status"]
    observation = {
        "name": metric["name"],
        "unit": metric["unit"],
        "status": status,
        "source_metric_names": metric["source_metric_names"],
        "value": value if status == "available" else None,
        "limitations": sorted(set(limitations)),
    }
    return observation, status != "available"


def build_representation_evidence(
    bundle: dict[str, Any],
    run_dir: Path,
    configuration_bytes: bytes,
) -> dict[str, Any]:
    """Bind configured representations to exact EXP-01 evaluator outputs."""
    if bundle.get("schema_version") != "1.2.0":
        raise ValueError("representation binding requires an EXP-01 schema 1.2.0 bundle")
    if bundle.get("architecture", {}).get("state") != EXPECTED_ARCHITECTURE_STATE:
        raise ValueError("evidence bundle architecture does not match the A0.1 configuration")
    input_by_source = _input_artifact_index(run_dir, bundle["input_artifacts"])
    obligation_catalog_path = "fitness/catalog/architectural-obligations.yaml"
    obligation_catalog_ref = input_by_source.get(obligation_catalog_path)
    if obligation_catalog_ref is None:
        raise ValueError("obligation catalog is not a digest-bound input artifact")
    configuration_schema_ref = input_by_source.get(
        "fitness/configs/a0_1-capability-modules.dev.schema.json"
    )
    if configuration_schema_ref is None:
        raise ValueError("fitness configuration schema is not a digest-bound input artifact")
    configuration = load_fitness_configuration(
        configuration_bytes,
        _verify_artifact(run_dir, obligation_catalog_ref),
        _verify_artifact(run_dir, configuration_schema_ref),
    )
    configuration_hash = sha256_bytes(configuration_bytes)
    selected = bundle.get("fitness_configuration", {})
    if selected.get("declared_architecture_state") != configuration["architecture_state"]:
        raise ValueError(
            "selected fitness configuration and bundle architecture identities conflict"
        )
    if selected.get("configuration_version") != configuration["configuration_version"]:
        raise ValueError("selected fitness configuration version conflicts with its exact bytes")
    if selected.get("configuration_sha256") != configuration_hash:
        raise ValueError("selected fitness configuration digest conflicts with its exact bytes")
    config_reference = selected.get("configuration_artifact")
    if not isinstance(config_reference, dict):
        raise ValueError("selected fitness configuration artifact reference is missing")
    copied_config = _verify_artifact(run_dir, config_reference)
    if copied_config != configuration_bytes:
        raise ValueError("selected fitness configuration artifact does not match the loaded bytes")

    expected_sources = {
        configuration["provenance"]["source_configuration"],
        configuration["provenance"]["source_architecture_state"],
        configuration["provenance"]["source_obligation_catalog"],
        FITNESS_CONFIGURATION_PATH,
    }
    for representation in configuration["representations"]:
        expected_sources.update(representation["evaluator"]["source_artifacts"])
    missing_sources = expected_sources - set(input_by_source)
    if missing_sources:
        raise ValueError(
            "configuration/evaluator source artifacts are not digest-bound in the bundle: "
            + ", ".join(sorted(missing_sources))
        )
    manifest_reference = bundle["architecture"]["manifest_artifact"]
    if (
        manifest_reference
        != input_by_source[configuration["provenance"]["source_architecture_state"]]
    ):
        raise ValueError("architecture manifest artifact identity conflicts with copied input")

    record_by_id = _record_index(bundle)
    source_revision = bundle["source_revision"]["commit_sha"]
    representations: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    global_limitations = [
        (
            "This adapter binds engineering evaluator execution; it does not assess normative "
            "applicability or independently validate semantics."
        ),
        "Coverage_P is not assessed and independent Coverage_ref is not established.",
        "The manually established A0.1 configuration is not a P or B1 adaptation result.",
    ]

    for configured in configuration["representations"]:
        evaluator = configured["evaluator"]
        record = record_by_id.get(evaluator["record_id"])
        evidence_references: list[dict[str, Any]] = []
        record_status = "missing"
        execution_verdict = "not_run"
        record_revision: str | None = None
        runtime_binding_status = "not_applicable"
        scope_status = "unknown"
        compliance_status = "unknown"
        compliance_basis = "No matching evaluator record is available."
        record_limitations: list[str] = []
        metrics: list[dict[str, Any]] = []
        unresolved_status: str | None = None

        if record is None:
            unresolved_status = "missing_evaluator"
            record_limitations.append("Configured evaluator record is missing from this run.")
        else:
            if record["evaluator_name"] != evaluator["name"]:
                raise ValueError(
                    f"evaluator identity conflicts for {configured['id']}: "
                    f"expected {evaluator['name']}, got {record['evaluator_name']}"
                )
            if record["lifecycle_stage"] != configured["stage"]:
                raise ValueError(f"evaluator lifecycle stage conflicts for {configured['id']}")
            if record["run_id"] != bundle["run_id"]:
                raise ValueError(f"evaluator run identity conflicts for {configured['id']}")
            if record["source_revision"] != source_revision:
                raise ValueError(f"evaluator source revision conflicts for {configured['id']}")
            if record.get("scope_id") != evaluator["scope_id"]:
                raise ValueError(f"evaluator architecture scope conflicts for {configured['id']}")
            configured_artifact_source = evaluator["configuration_artifact_source"]
            expected_configuration_artifact = (
                input_by_source.get(configured_artifact_source)
                if configured_artifact_source is not None
                else None
            )
            if record.get("configuration_artifact") != expected_configuration_artifact:
                raise ValueError(
                    f"evaluator configuration artifact conflicts for {configured['id']}"
                )
            scope_status = "matched"
            record_status = record["status"]
            execution_verdict = record["execution_verdict"]
            record_revision = record["source_revision"]
            record_limitations.extend(record["limitations"])
            raw_references = record["raw_output_artifacts"]
            if record_status == "available" and not raw_references:
                raise ValueError(
                    f"available evaluator has no raw output artifacts: {configured['id']}"
                )
            for reference in raw_references:
                _verify_artifact(run_dir, reference)
                evidence_references.append(reference)
            source_binding = record.get("source_binding")
            if configured["stage"] == "runtime":
                runtime_binding_status = (
                    source_binding.get("status", "not_observed")
                    if isinstance(source_binding, dict)
                    else "not_observed"
                )
                if runtime_binding_status != "verified":
                    record_limitations.append(
                        "Runtime observations are not verified against the application source "
                        "revision."
                    )
                    unresolved_status = "unverified_source_identity"

            if evaluator["compliance_mapping"] == "execution_verdict":
                if execution_verdict == "passed" and record_status == "available":
                    compliance_status = "conforming"
                    compliance_basis = (
                        "The configured evaluator completed and reported no violations."
                    )
                elif execution_verdict == "violations_detected" and record_status == "available":
                    compliance_status = "nonconforming"
                    compliance_basis = "The configured evaluator completed and reported violations."
                else:
                    compliance_status = "unknown"
                    compliance_basis = (
                        "Evaluator execution did not establish a compliance observation."
                    )
            elif record_status == "available":
                compliance_status = "not_assessed"
                compliance_basis = (
                    "The representation records observations and has no configured threshold rule."
                )

            for metric in evaluator["metrics"]:
                observation, unresolved_metric = _metric_observation(record, metric)
                metrics.append(observation)
                if unresolved_metric and unresolved_status is None:
                    unresolved_status = (
                        "invalid_evidence"
                        if observation["status"] == "invalid"
                        else "missing_metric"
                    )
                if (
                    metric["name"] == "http_request_duration_seconds_histogram"
                    and observation["status"] == "available"
                ):
                    value = observation["value"]
                    if isinstance(value, dict) and value.get("quantiles") is not None:
                        raise ValueError("runtime histogram quantiles were unexpectedly asserted")

        if unresolved_status is not None:
            reason = (
                "Runtime endpoint identity is unverified; observations cannot be promoted "
                "to revision-bound evidence."
                if unresolved_status == "unverified_source_identity"
                else "; ".join(record_limitations)
                or f"Configured evaluator evidence is unresolved: {unresolved_status}."
            )
            unresolved.append(
                {
                    "representation_id": configured["id"],
                    "status": unresolved_status,
                    "reason": reason,
                }
            )
        representations.append(
            {
                "representation_id": configured["id"],
                "criterion_id": configured["criterion_id"],
                "declared_obligations": configured["declared_obligations"],
                "lifecycle_stage": configured["stage"],
                "evaluator_id": evaluator["id"],
                "evaluator_execution": {
                    "status": _execution_status(record_status),
                    "record_id": evaluator["record_id"],
                    "evaluator_name": evaluator["name"],
                    "execution_verdict": execution_verdict,
                    "source_revision": record_revision,
                    "runtime_source_binding_status": runtime_binding_status,
                },
                "compliance_observation": {
                    "status": compliance_status,
                    "basis": compliance_basis,
                },
                "scope_binding_status": scope_status,
                "applicability_status": "not_independently_assessed",
                "semantic_fitness_validity": "not_independently_validated",
                "independent_coverage": "not_established",
                "metrics": metrics,
                "evidence_references": evidence_references,
                "limitations": sorted(set(configured["limitations"] + record_limitations)),
            }
        )

    return {
        "schema_version": "1.0.0",
        "evidence_type": "development_representation_execution",
        "run_id": bundle["run_id"],
        "exp01_bundle_schema_version": bundle["schema_version"],
        "source_revision": source_revision,
        "architecture_state": bundle["architecture"]["state"],
        "fitness_configuration": {
            "configuration_id": configuration["configuration_id"],
            "configuration_version": configuration["configuration_version"],
            "configuration_sha256": configuration_hash,
            "configuration_artifact": config_reference,
            "provenance_status": "manual_development_reference",
        },
        "supported_stages": configuration["supported_stages"],
        "representations": representations,
        "unresolved_mappings": unresolved,
        "coverage_claims": {
            "Coverage_P": "not_assessed",
            "Coverage_ref": "not_established",
            "semantic_validity": "not_independently_validated",
        },
        "limitations": global_limitations,
    }


def _execution_status(record_status: str) -> str:
    """Normalize evidence availability without converting it to compliance."""
    return {
        "available": "available",
        "missing": "missing",
        "invalid": "invalid",
        "skipped": "unsupported",
        "inconclusive": "inconclusive",
    }.get(record_status, "inconclusive")


def validate_representation_evidence(run_dir: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    """Validate the packaged representation evidence and its bundle identities."""
    if bundle.get("schema_version") != "1.2.0":
        raise ValueError("representation evidence is only required for EXP-01 schema 1.2.0")
    reference = bundle.get("fitness_representation_evidence")
    if not isinstance(reference, dict):
        raise ValueError("bundle is missing the representation evidence artifact reference")
    content = _verify_artifact(run_dir, reference)
    try:
        parsed_evidence = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("representation evidence artifact is not valid JSON") from error
    if not isinstance(parsed_evidence, dict):
        raise ValueError("representation evidence artifact must contain a JSON object")
    evidence = cast(dict[str, Any], parsed_evidence)
    input_by_source = _input_artifact_index(run_dir, bundle["input_artifacts"])
    representation_schema_ref = input_by_source.get(
        "experiments/schemas/fitness_representation_evidence_v1.schema.json"
    )
    if representation_schema_ref is None:
        raise ValueError("representation evidence schema is not a digest-bound input artifact")
    _validate_json_schema(
        evidence,
        REPRESENTATION_EVIDENCE_SCHEMA_PATH,
        "representation evidence",
        _verify_artifact(run_dir, representation_schema_ref),
    )
    if evidence["run_id"] != bundle["run_id"]:
        raise ValueError("representation evidence run identity conflicts with the bundle")
    if evidence["source_revision"] != bundle["source_revision"]["commit_sha"]:
        raise ValueError("representation evidence source revision conflicts with the bundle")
    if evidence["architecture_state"] != bundle["architecture"]["state"]:
        raise ValueError("representation evidence architecture conflicts with the bundle")
    selected = bundle["fitness_configuration"]
    if selected["configuration_artifact"].get("source_path") != FITNESS_CONFIGURATION_PATH:
        raise ValueError("bundle selected fitness configuration artifact path conflicts")
    evidence_config = evidence["fitness_configuration"]
    if evidence_config["configuration_artifact"] != selected["configuration_artifact"]:
        raise ValueError("representation evidence configuration artifact conflicts with the bundle")
    if evidence_config["configuration_sha256"] != selected["configuration_sha256"]:
        raise ValueError("representation evidence configuration digest conflicts with the bundle")
    if evidence["exp01_bundle_schema_version"] != bundle["schema_version"]:
        raise ValueError("representation evidence bundle schema version conflicts")
    configuration_bytes = _verify_artifact(run_dir, selected["configuration_artifact"])
    obligation_ref = input_by_source.get("fitness/catalog/architectural-obligations.yaml")
    config_schema_ref = input_by_source.get(
        "fitness/configs/a0_1-capability-modules.dev.schema.json"
    )
    if obligation_ref is None or config_schema_ref is None:
        raise ValueError("configuration validation inputs are missing from the bundle")
    configuration = load_fitness_configuration(
        configuration_bytes,
        _verify_artifact(run_dir, obligation_ref),
        _verify_artifact(run_dir, config_schema_ref),
    )
    expected_sources = {
        configuration["provenance"]["source_configuration"],
        configuration["provenance"]["source_architecture_state"],
        configuration["provenance"]["source_obligation_catalog"],
        FITNESS_CONFIGURATION_PATH,
    }
    for configured in configuration["representations"]:
        expected_sources.update(configured["evaluator"]["source_artifacts"])
    if expected_sources - set(input_by_source):
        raise ValueError("selected configuration refers to source artifacts absent from the bundle")
    if configuration["configuration_id"] != evidence_config["configuration_id"]:
        raise ValueError(
            "representation evidence configuration identity conflicts with exact bytes"
        )
    if configuration["configuration_version"] != evidence_config["configuration_version"]:
        raise ValueError("representation evidence configuration version conflicts with exact bytes")
    configured_by_id = {item["id"]: item for item in configuration["representations"]}
    evidence_by_id = {item["representation_id"]: item for item in evidence["representations"]}
    if len(evidence_by_id) != len(evidence["representations"]) or set(evidence_by_id) != set(
        configured_by_id
    ):
        raise ValueError("representation identities conflict with the selected configuration")
    record_by_id = _record_index(bundle)
    for representation_id, configured in configured_by_id.items():
        item = evidence_by_id[representation_id]
        evaluator = configured["evaluator"]
        if (
            item["criterion_id"] != configured["criterion_id"]
            or item["declared_obligations"] != configured["declared_obligations"]
            or item["lifecycle_stage"] != configured["stage"]
            or item["evaluator_id"] != evaluator["id"]
            or item["evaluator_execution"]["record_id"] != evaluator["record_id"]
            or item["evaluator_execution"]["evaluator_name"] != evaluator["name"]
        ):
            raise ValueError(
                f"representation identity conflicts with its configuration: {representation_id}"
            )
        record = record_by_id.get(evaluator["record_id"])
        expected_references = record["raw_output_artifacts"] if record is not None else []
        if item["evidence_references"] != expected_references:
            raise ValueError(f"representation raw evidence links conflict: {representation_id}")
        if record is not None and (
            record["evaluator_name"] != evaluator["name"]
            or record["lifecycle_stage"] != configured["stage"]
            or record.get("scope_id") != evaluator["scope_id"]
        ):
            raise ValueError(f"representation evaluator identity conflicts: {representation_id}")
        expected_configuration_artifact = (
            input_by_source.get(evaluator["configuration_artifact_source"])
            if evaluator["configuration_artifact_source"] is not None
            else None
        )
        if (
            record is not None
            and record.get("configuration_artifact") != expected_configuration_artifact
        ):
            raise ValueError(f"representation evaluator artifact conflicts: {representation_id}")
    expected_evidence = build_representation_evidence(bundle, run_dir, configuration_bytes)
    if evidence != expected_evidence:
        raise ValueError(
            "representation evidence does not match its selected "
            "configuration and evaluator records"
        )
    return evidence


def main(argv: list[str] | None = None) -> int:
    """Validate an existing EXP-02 DEVELOPMENT run and print a compact summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = validate_bundle(args.run_dir)
        evidence = validate_representation_evidence(args.run_dir, bundle)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}, sort_keys=True))
        return 1
    summary = {
        "status": "valid",
        "run_id": evidence["run_id"],
        "representation_count": len(evidence["representations"]),
        "unresolved_mapping_count": len(evidence["unresolved_mappings"]),
        "Coverage_P": evidence["coverage_claims"]["Coverage_P"],
        "Coverage_ref": evidence["coverage_claims"]["Coverage_ref"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
