"""SPEC01 → SPEC02 → impact → candidate → governance development pipeline."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, cast
from weakref import WeakKeyDictionary

import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.p_adaptation_evidence import (
    AdaptationEvidenceVerifierRegistry,
    VerifiedAdaptationEvidence,
    thaw_verified_payload,
    verify_adaptation_evidence,
)
from experiments.execution.tooling.p_applicability import (
    ApplicabilityAssessment,
    CompiledRuleset,
    EvidenceLedger,
    EvidenceProof,
    ProofStatus,
    evaluate_obligations,
    load_and_validate_ruleset,
)
from experiments.execution.tooling.p_candidate import (
    adapt_candidate_v1,
    adapt_prediction_v1,
    candidate_sha256,
    derive_configuration_version,
    materialize_candidate,
    normalize_parent_representation,
)
from experiments.execution.tooling.p_governance import (
    GovernanceDecision,
    GovernanceResult,
    _decide_governance_authorized,
    _issue_governance_pipeline_authorization,
)
from experiments.execution.tooling.p_impact import (
    ChangeKind,
    ChangeRecord,
    ImpactAssessment,
    TraceGraph,
    analyze_impact,
    diff_snapshot,
    legacy_trace_graph,
    parse_trace_graph,
)
from experiments.execution.tooling.p_input_validation import (
    AuthorityTrustContext,
    CompletenessVerifier,
    FactVerifier,
    SnapshotValidationResult,
    ValidationStatus,
    load_and_validate_snapshot,
    load_fact_vocabulary,
)
from experiments.execution.tooling.p_operations import (
    OperationPlan,
    build_operation_plan,
    template_descriptor_sha256,
    validate_materializable_template,
)
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3
from experiments.execution.tooling.p_semantic import (
    CoverageAssessment,
    PairAssessment,
    assess_mandatory_coverage,
    assess_pair,
)

METHOD_VERSION = "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1"
PILOT02_PROFILE_DEFINITION_PATH = "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V1.json"
PILOT02_PROFILE_DEFINITION_SHA256 = (
    "b9f9ceb7f5947b4de36544dcaccaafeafe5e0c22bf2742d96af3f56226858712"
)
PILOT02_PROFILE_V2_DEFINITION_PATH = "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json"
PILOT02_PROFILE_V2_DEFINITION_SHA256 = (
    "c480b1907d9f69cb7c5d1c4f45cb221551aeb857881ba859529e8c1f1fd5e8c9"
)
PILOT02_PROFILE_PINS = {
    1: (
        PILOT02_PROFILE_DEFINITION_PATH,
        PILOT02_PROFILE_DEFINITION_SHA256,
        "pilot02_method_input_profile_v1.schema.json",
    ),
    2: (
        PILOT02_PROFILE_V2_DEFINITION_PATH,
        PILOT02_PROFILE_V2_DEFINITION_SHA256,
        "pilot02_method_input_profile_v2.schema.json",
    ),
}


@dataclass(frozen=True, eq=False)
class VerifiedPBundle:
    """Version-bound P inputs; only the V3 verifier registers verified objects."""

    root: Path
    manifest: Mapping[str, Any]
    snapshot: Mapping[str, Any]
    snapshot_validation: SnapshotValidationResult
    compiled_ruleset: CompiledRuleset
    evidence_ledger: EvidenceLedger
    obligations: tuple[Mapping[str, Any], ...]
    representations: tuple[Mapping[str, Any], ...]
    trace_graph: TraceGraph
    templates: tuple[Mapping[str, Any], ...]
    artifact_bytes: Mapping[str, bytes]
    source_digests: Mapping[str, str]
    parent_configuration: Mapping[str, Any]
    parent_configuration_bytes: bytes
    parent_configuration_path: str
    parent_configuration_sha256: str
    cost_model: Mapping[str, Any] | None
    bundle_provenance: str = "UNVERIFIED"
    trust_scope: Literal["PRODUCTION", "TEST_ONLY"] = "PRODUCTION"


_VERIFIED_V3_BUNDLE_DIGESTS: WeakKeyDictionary[VerifiedPBundle, str] = WeakKeyDictionary()
_TEST_ONLY_BUNDLE_DIGESTS: WeakKeyDictionary[VerifiedPBundle, str] = WeakKeyDictionary()
_BUNDLE_EVIDENCE_VERIFIER_REGISTRIES: WeakKeyDictionary[
    VerifiedPBundle, AdaptationEvidenceVerifierRegistry
] = WeakKeyDictionary()


@dataclass(frozen=True)
class AdaptationResult:
    """Complete development result; V1 outputs exist only when governance accepts."""

    before_applicability: ApplicabilityAssessment
    after_applicability: ApplicabilityAssessment
    impact: ImpactAssessment
    current_pairs: tuple[PairAssessment, ...]
    candidate_pairs: tuple[PairAssessment, ...]
    current_coverage: CoverageAssessment
    candidate_coverage: CoverageAssessment | None
    operation_plan: OperationPlan
    candidate: Mapping[str, Any] | None
    candidate_sha256: str | None
    governance: GovernanceDecision
    prediction_v1: Mapping[str, Any] | None
    candidate_v1: Mapping[str, Any] | None
    evidence_trust_scope: str | None


def verify_v3_p_bundle(
    bundle_directory: Path,
    *,
    evidence_ledger: EvidenceLedger,
    trust_context: AuthorityTrustContext | None = None,
    fact_verifier: FactVerifier | None = None,
    completeness_verifier: CompletenessVerifier | None = None,
) -> VerifiedPBundle:
    """Verify source, roles, revisions, hashes and SPEC01 snapshot before use.

    P never walks repository history or discovers inputs dynamically. It reads
    only files named by the V3 method-input manifest and approved role paths.
    """
    manifest = verify_method_bundle_v3(bundle_directory, expected_method_id="P")
    root = bundle_directory.resolve(strict=True)
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ProtocolError("P03_INPUT_MANIFEST_INVALID")
    file_records: dict[str, Mapping[str, Any]] = {}
    for row in entries:
        if isinstance(row, Mapping) and isinstance(row.get("path"), str):
            file_records[str(row["path"])] = row

    snapshot_bytes = _read_pinned_file(root, "architecture-policy-snapshot.json", file_records)
    snapshot = _decode_object(snapshot_bytes, "Snapshot")
    ruleset_path = root / "policy/applicability_ruleset_v1.json"
    catalog_path = root / "fitness/obligations.yaml"
    ruleset = load_and_validate_ruleset(ruleset_path, load_fact_vocabulary(), catalog_path)
    validation = load_and_validate_snapshot(
        root,
        manifest,
        trust_context,
        fact_verifier,
        completeness_verifier,
        {item.obligation_id for item in ruleset.obligations},
        set(ruleset.conditions),
    )
    if (
        validation.schema_status is ValidationStatus.INVALID
        or validation.integrity_status is ValidationStatus.INVALID
    ):
        raise ProtocolError("P03_INPUT_REJECTED:" + ",".join(validation.reason_codes))

    catalog_bytes = _read_pinned_file(root, "fitness/obligations.yaml", file_records)
    catalog = _decode_yaml_object(catalog_bytes, "obligation catalog")
    catalog_rows = catalog.get("obligations")
    if catalog.get("schema_version") != 1 or not isinstance(catalog_rows, list):
        raise ProtocolError("P03_OBLIGATION_CATALOG_INVALID")
    obligations = _bind_obligations(catalog_rows, ruleset)

    representation_bytes = _read_pinned_file(root, "fitness/a0-representations.yaml", file_records)
    representation_doc = _decode_yaml_object(representation_bytes, "representation catalog")
    reps_value = representation_doc.get("representations")
    if not isinstance(reps_value, list):
        raise ProtocolError("P03_REPRESENTATION_CATALOG_INVALID")
    representations = tuple(_normalize_representation(row) for row in reps_value)
    config = {
        "schema_version": 1,
        "representations": [dict(item) for item in representations],
    }

    trace_record = next(
        (row for row in entries if isinstance(row, Mapping) and row.get("role") == "traceability"),
        None,
    )
    if not isinstance(trace_record, Mapping) or not isinstance(trace_record.get("path"), str):
        raise ProtocolError("P03_TRACEABILITY_INPUT_MISSING")
    trace_bytes = _read_pinned_file(root, str(trace_record["path"]), file_records)
    trace_doc = _decode_yaml_object(trace_bytes, "traceability")
    graph = (
        parse_trace_graph(trace_doc)
        if isinstance(trace_doc.get("nodes"), list) and isinstance(trace_doc.get("edges"), list)
        else legacy_trace_graph(trace_doc, representations=representations, obligations=obligations)
    )

    source_digests: dict[str, str] = {}
    for source in snapshot.get("sources", []):
        if not isinstance(source, Mapping):
            continue
        record = file_records.get(str(source.get("path")))
        if isinstance(source.get("id"), str) and isinstance(record, Mapping):
            source_digests[str(source["id"])] = str(record.get("sha256", ""))
    source_digests["P_CAPABILITIES"] = str(
        file_records["fitness/evaluator-capabilities.json"].get("sha256", "")
    )
    source_digests["P_TRACEABILITY"] = str(trace_record.get("sha256", ""))

    capabilities_bytes = _read_pinned_file(
        root, "fitness/evaluator-capabilities.json", file_records
    )
    capabilities = _decode_object(capabilities_bytes, "evaluator capabilities")
    template_value = capabilities.get("generic_candidate_templates", [])
    templates = (
        tuple(dict(item) for item in template_value if isinstance(item, Mapping))
        if isinstance(template_value, list)
        else ()
    )
    pilot_profile = capabilities.get("pilot02_method_input_profile")
    cost_model = capabilities.get("p_cost_model_v1")
    if not isinstance(cost_model, Mapping):
        cost_model = None

    # Read only files that the verified manifest declares as evidence artifacts.
    artifact_bytes = {
        path: _read_pinned_file(root, path, file_records)
        for path, row in file_records.items()
        if row.get("role") in {"evaluator_artifact", "evaluator_evidence", "evidence_artifact"}
    }
    if pilot_profile is not None:
        profile_artifacts = _validate_pilot02_method_input_profile(
            pilot_profile,
            capabilities=capabilities,
            manifest=manifest,
            snapshot=snapshot,
            obligations=obligations,
            parent_representations=representations,
            parent_configuration_sha256=sha256_bytes(representation_bytes),
        )
        if set(artifact_bytes) & set(profile_artifacts):
            raise ProtocolError("P03_PILOT02_ARTIFACT_PATH_CONFLICT")
        artifact_bytes.update(profile_artifacts)
    trust_scope_value = getattr(trust_context, "trust_scope", "PRODUCTION")
    if not isinstance(trust_scope_value, str):
        raise ProtocolError("P03_TRUST_SCOPE_INVALID")
    trust_scope = cast(Literal["PRODUCTION", "TEST_ONLY"], trust_scope_value)
    if trust_scope not in {"PRODUCTION", "TEST_ONLY"}:
        raise ProtocolError("P03_TRUST_SCOPE_INVALID")
    bundle = VerifiedPBundle(
        root,
        manifest,
        snapshot,
        validation,
        ruleset,
        evidence_ledger,
        obligations,
        representations,
        graph,
        templates,
        artifact_bytes,
        source_digests,
        config,
        representation_bytes,
        "fitness/a0-representations.yaml",
        sha256_bytes(representation_bytes),
        cost_model,
        "VERIFIED_V3",
        trust_scope,
    )
    _VERIFIED_V3_BUNDLE_DIGESTS[bundle] = _verified_bundle_content_sha256(bundle)
    registry = getattr(trust_context, "adaptation_evidence_verifiers", None)
    if isinstance(registry, AdaptationEvidenceVerifierRegistry):
        _BUNDLE_EVIDENCE_VERIFIER_REGISTRIES[bundle] = registry
    return bundle


def _validate_pilot02_method_input_profile(
    value: Any,
    *,
    capabilities: Mapping[str, Any],
    manifest: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    obligations: Sequence[Mapping[str, Any]],
    parent_representations: Sequence[Mapping[str, Any]] | None = None,
    parent_configuration_sha256: str | None = None,
) -> dict[str, bytes]:
    """Validate the separately versioned A0.1 pilot profile inside P capabilities."""
    if not isinstance(value, dict):
        raise ProtocolError("P03_PILOT02_PROFILE_INVALID")
    version = value.get("schema_version")
    profile_pin = PILOT02_PROFILE_PINS.get(version) if isinstance(version, int) else None
    if profile_pin is None:
        raise ProtocolError("P03_PILOT02_PROFILE_VERSION_INVALID")
    definition_path, definition_sha256, schema_path = profile_pin
    validate_payload(schema_path, value)
    architecture = snapshot.get("architecture")
    if not isinstance(architecture, Mapping) or (
        value.get("architecture_before_sha") != architecture.get("before_commit")
        or value.get("architecture_source_sha") != architecture.get("after_commit")
        or value.get("architecture_source_sha") != manifest.get("architecture_source_sha")
        or value.get("a0_1_app_tree_sha") != manifest.get("after_tree_sha")
    ):
        raise ProtocolError("P03_PILOT02_ARCHITECTURE_BINDING_MISMATCH")

    mappings = value.get("mappings")
    if not isinstance(mappings, list):
        raise ProtocolError("P03_PILOT02_MAPPINGS_INVALID")
    source_ids: set[str] = set()
    obligation_ids: set[str] = set()
    expected_templates: list[Mapping[str, Any]] = []
    referenced_artifacts: dict[str, str] = {}
    for mapping in mappings:
        if not isinstance(mapping, Mapping):
            raise ProtocolError("P03_PILOT02_MAPPING_INVALID")
        source_id = str(mapping.get("source_representation_id", ""))
        obligation_id = str(mapping.get("obligation_id", ""))
        template = mapping.get("candidate_template")
        metric = mapping.get("metric")
        configuration_artifact = mapping.get("configuration_artifact")
        evaluator_artifacts = mapping.get("evaluator_source_artifacts")
        if (
            not source_id
            or source_id in source_ids
            or obligation_id in obligation_ids
            or not isinstance(template, Mapping)
            or not isinstance(template.get("representation"), Mapping)
            or not isinstance(metric, Mapping)
            or not isinstance(configuration_artifact, Mapping)
            or not isinstance(evaluator_artifacts, list)
        ):
            raise ProtocolError("P03_PILOT02_MAPPING_IDENTITY_INVALID")
        source_ids.add(source_id)
        obligation_ids.add(obligation_id)
        representation = template["representation"]
        evidence_contract = representation.get("evidence_contract")
        scope = representation.get("applicability_scope")
        artifact = representation.get("evaluator_artifact")
        if (
            representation.get("id") != source_id
            or representation.get("criterion") != value.get("criterion_id")
            or representation.get("stage") != value["stage_translation"].get("method_stage")
            or representation.get("evaluator") != mapping.get("source_evaluator_id")
            or representation.get("covers") != [obligation_id]
            or not isinstance(scope, Mapping)
            or scope.get("scope_id") != mapping.get("source_scope_id")
            or not isinstance(evidence_contract, Mapping)
            or evidence_contract.get("metric") != metric
            or evidence_contract.get("configuration_artifact_sha256")
            != configuration_artifact.get("sha256")
            or not isinstance(artifact, Mapping)
        ):
            raise ProtocolError("P03_PILOT02_CANONICAL_BINDING_MISMATCH")
        expected_templates.append(template)
        for record in [configuration_artifact, *evaluator_artifacts, artifact]:
            if not isinstance(record, Mapping):
                raise ProtocolError("P03_PILOT02_ARTIFACT_REFERENCE_INVALID")
            path, digest = record.get("path"), record.get("sha256")
            if not isinstance(path, str) or not _is_sha256(str(digest)):
                raise ProtocolError("P03_PILOT02_ARTIFACT_REFERENCE_INVALID")
            previous = referenced_artifacts.get(path)
            if previous is not None and previous != digest:
                raise ProtocolError("P03_PILOT02_ARTIFACT_REFERENCE_CONFLICT")
            referenced_artifacts[path] = str(digest)

    if obligation_ids != {"AC_LAYERING", "AC_MODULE_STRUCTURE"}:
        raise ProtocolError("P03_PILOT02_OBLIGATION_SCOPE_MISMATCH")
    if value.get("fitness_configuration_sha256") != value["fitness_configuration_artifact"].get(
        "sha256"
    ) or value.get("obligation_catalog_sha256") != value["obligation_catalog_artifact"].get(
        "sha256"
    ):
        raise ProtocolError("P03_PILOT02_PROFILE_ARTIFACT_BINDING_MISMATCH")
    if capabilities.get("generic_candidate_templates") != expected_templates:
        raise ProtocolError("P03_PILOT02_TEMPLATE_BINDING_MISMATCH")
    for record in (
        value["profile_definition_artifact"],
        value["fitness_configuration_artifact"],
        value["obligation_catalog_artifact"],
    ):
        path, digest = record["path"], record["sha256"]
        previous = referenced_artifacts.get(path)
        if previous is not None and previous != digest:
            raise ProtocolError("P03_PILOT02_ARTIFACT_REFERENCE_CONFLICT")
        referenced_artifacts[path] = digest

    if version == 2:
        parent_artifact = value.get("parent_representation_catalog_artifact")
        parent_digest = value.get("parent_representation_catalog_sha256")
        parent_bindings = value.get("parent_evaluator_bindings")
        if (
            not isinstance(parent_artifact, Mapping)
            or parent_artifact.get("sha256") != parent_digest
            or parent_digest != parent_configuration_sha256
            or parent_representations is None
            or not isinstance(parent_bindings, list)
            or not parent_bindings
        ):
            raise ProtocolError("P03_PILOT02_PARENT_BINDING_BASELINE_MISMATCH")
        parent_catalog_path = parent_artifact.get("path")
        if not isinstance(parent_catalog_path, str):
            raise ProtocolError("P03_PILOT02_PARENT_BINDING_ARTIFACT_INVALID")
        previous = referenced_artifacts.get(parent_catalog_path)
        if previous is not None and previous != parent_digest:
            raise ProtocolError("P03_PILOT02_ARTIFACT_REFERENCE_CONFLICT")
        referenced_artifacts[parent_catalog_path] = str(parent_digest)
        parent_by_id = {str(row.get("id")): row for row in parent_representations}
        binding_ids: set[str] = set()
        for binding in parent_bindings:
            if not isinstance(binding, Mapping):
                raise ProtocolError("P03_PILOT02_PARENT_BINDING_INVALID")
            representation_id = binding.get("representation_id")
            artifact = binding.get("evaluator_artifact")
            source_artifacts = binding.get("evaluator_source_artifacts")
            parent_row = parent_by_id.get(str(representation_id))
            if (
                not isinstance(representation_id, str)
                or representation_id in binding_ids
                or parent_row is None
                or parent_row.get("evaluator_artifact") is not None
                or not isinstance(artifact, Mapping)
                or not isinstance(source_artifacts, list)
                or binding.get("binding_status") != "A0_1_DEVELOPMENT_ADAPTER"
            ):
                raise ProtocolError("P03_PILOT02_PARENT_BINDING_IDENTITY_MISMATCH")
            binding_ids.add(representation_id)
            if not source_artifacts:
                raise ProtocolError("P03_PILOT02_PARENT_BINDING_SOURCE_MISSING")
            for record in [artifact, *source_artifacts]:
                if not isinstance(record, Mapping):
                    raise ProtocolError("P03_PILOT02_ARTIFACT_REFERENCE_INVALID")
                path, digest = record.get("path"), record.get("sha256")
                if not isinstance(path, str) or not _is_sha256(str(digest)):
                    raise ProtocolError("P03_PILOT02_ARTIFACT_REFERENCE_INVALID")
                previous = referenced_artifacts.get(path)
                if previous is not None and previous != digest:
                    raise ProtocolError("P03_PILOT02_ARTIFACT_REFERENCE_CONFLICT")
                referenced_artifacts[path] = str(digest)

    embedded = value.get("embedded_evaluator_artifacts", [])
    if not isinstance(embedded, list):
        raise ProtocolError("P03_PILOT02_EMBEDDED_ARTIFACTS_INVALID")
    result: dict[str, bytes] = {}
    declared: dict[str, str] = {}
    for row in embedded:
        if not isinstance(row, Mapping):
            raise ProtocolError("P03_PILOT02_EMBEDDED_ARTIFACT_INVALID")
        path, digest, encoded = row.get("path"), row.get("sha256"), row.get("content_base64")
        if (
            not isinstance(path, str)
            or not isinstance(digest, str)
            or not isinstance(encoded, str)
            or path in declared
        ):
            raise ProtocolError("P03_PILOT02_EMBEDDED_ARTIFACT_INVALID")
        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as error:
            raise ProtocolError("P03_PILOT02_EMBEDDED_ARTIFACT_ENCODING_INVALID") from error
        if len(content) != row.get("size_bytes") or sha256_bytes(content) != digest:
            raise ProtocolError("P03_PILOT02_EMBEDDED_ARTIFACT_DIGEST_MISMATCH")
        if referenced_artifacts.get(path) != digest:
            raise ProtocolError("P03_PILOT02_EMBEDDED_ARTIFACT_UNREFERENCED")
        declared[path] = digest
        result[path] = content
    if declared != referenced_artifacts:
        raise ProtocolError("P03_PILOT02_EMBEDDED_ARTIFACT_INVENTORY_MISMATCH")
    definition_ref = value["profile_definition_artifact"]
    if (
        definition_ref.get("path") != definition_path
        or definition_ref.get("sha256") != definition_sha256
    ):
        raise ProtocolError("P03_PILOT02_PROFILE_DEFINITION_PIN_MISMATCH")
    try:
        definition = json.loads(result[definition_path])
        configuration = yaml.safe_load(result[value["fitness_configuration_artifact"]["path"]])
        catalog = yaml.safe_load(result[value["obligation_catalog_artifact"]["path"]])
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError, yaml.YAMLError, TypeError) as error:
        raise ProtocolError("P03_PILOT02_SOURCE_CONFIGURATION_INVALID") from error
    if (
        not isinstance(definition, Mapping)
        or sha256_bytes(result[definition_path]) != definition_sha256
        or not isinstance(configuration, Mapping)
        or not isinstance(catalog, Mapping)
    ):
        raise ProtocolError("P03_PILOT02_SOURCE_CONFIGURATION_INVALID")
    immutable_definition_keys = (
        "schema_version",
        "profile_id",
        "profile_status",
        "architecture_before_sha",
        "a0_1_source_basis_sha",
        "a0_1_app_tree_sha",
        "fitness_configuration_sha256",
        "fitness_configuration_artifact",
        "obligation_catalog_sha256",
        "obligation_catalog_artifact",
        "criterion_id",
        "criterion_intent",
        "stage_translation",
        "mappings",
    )
    if version == 2:
        immutable_definition_keys += (
            "parent_representation_catalog_sha256",
            "parent_representation_catalog_artifact",
            "parent_evaluator_bindings",
        )
    if any(value.get(key) != definition.get(key) for key in immutable_definition_keys):
        raise ProtocolError("P03_PILOT02_PROFILE_DEFINITION_MISMATCH")
    source_criteria = {
        str(row.get("id")): row
        for row in configuration.get("criteria", [])
        if isinstance(row, Mapping)
    }
    source_representations = {
        str(row.get("id")): row
        for row in configuration.get("representations", [])
        if isinstance(row, Mapping)
    }
    source_obligations = {
        str(row.get("id")): row
        for row in catalog.get("obligations", [])
        if isinstance(row, Mapping)
    }
    p_obligations = {str(row.get("id")): row for row in obligations}
    for mapping in mappings:
        source_id = str(mapping["source_representation_id"])
        obligation_id = str(mapping["obligation_id"])
        source = source_representations.get(source_id)
        obligation = source_obligations.get(obligation_id)
        template = mapping["candidate_template"]["representation"]
        criterion = source_criteria.get(str(template.get("criterion", "")))
        if (
            not isinstance(source, Mapping)
            or not isinstance(obligation, Mapping)
            or not isinstance(criterion, Mapping)
        ):
            raise ProtocolError("P03_PILOT02_SOURCE_MAPPING_MISSING")
        evaluator = source.get("evaluator")
        applicability = source.get("applicability")
        metric_rows = evaluator.get("metrics") if isinstance(evaluator, Mapping) else None
        expected_metric = next(
            (
                row
                for row in metric_rows or []
                if isinstance(row, Mapping) and row.get("name") == mapping["metric"].get("name")
            ),
            None,
        )
        scope = template["applicability_scope"]
        evidence_contract = template["evidence_contract"]
        artifact = template["evaluator_artifact"]
        source_paths = (
            [str(path) for path in evaluator.get("source_artifacts", [])]
            if isinstance(evaluator, Mapping)
            and isinstance(evaluator.get("source_artifacts"), list)
            else []
        )
        if any(path not in result for path in source_paths):
            raise ProtocolError("P03_PILOT02_SOURCE_ARTIFACT_MISSING")
        expected_sources = [
            {"path": path, "sha256": sha256_bytes(result[path])} for path in source_paths
        ]
        if (
            source.get("criterion_id") != value.get("criterion_id")
            or source.get("stage") != mapping.get("source_stage")
            or criterion.get("intent") != value.get("criterion_intent")
            or obligation.get("criterion") != value.get("criterion_id")
            or p_obligations.get(obligation_id, {}).get("criterion") != obligation.get("criterion")
            or p_obligations.get(obligation_id, {}).get("intent") != obligation.get("intent")
            or obligation_id not in source.get("declared_obligations", [])
            or not isinstance(evaluator, Mapping)
            or evaluator.get("id") != mapping.get("source_evaluator_id")
            or evaluator.get("name") != mapping.get("source_evaluator_name")
            or evaluator.get("record_id") != evidence_contract.get("record_id")
            or evaluator.get("scope_id") != mapping.get("source_scope_id")
            or not isinstance(applicability, Mapping)
            or mapping.get("architecture_scope") not in applicability.get("scopes", [])
            or evaluator.get("configuration_artifact_source")
            != mapping["configuration_artifact"].get("path")
            or expected_metric is None
            or expected_metric.get("unit") != mapping["metric"].get("unit")
            or expected_metric.get("evidence_path") != mapping["metric"].get("evidence_path")
            or evidence_contract.get("source_stage") != source.get("stage")
            or evidence_contract.get("scope_id") != evaluator.get("scope_id")
            or evidence_contract.get("metric") != mapping.get("metric")
            or evidence_contract.get("configuration_artifact_sha256")
            != mapping["configuration_artifact"].get("sha256")
            or artifact.get("path")
            not in [row.get("path") for row in mapping["evaluator_source_artifacts"]]
            or sorted(mapping["evaluator_source_artifacts"], key=lambda row: row["path"])
            != sorted(expected_sources, key=lambda row: row["path"])
            or scope.get("architecture_state") != configuration.get("architecture_state")
            or scope.get("architecture_scope") != mapping.get("architecture_scope")
        ):
            raise ProtocolError("P03_PILOT02_SOURCE_MAPPING_MISMATCH")
    return result


def run_adaptation(
    bundle: VerifiedPBundle,
    *,
    evidence_context: Mapping[str, Any] | None = None,
) -> AdaptationResult:
    """Run P only with side evidence verified against this exact input context.

    Raw proofs, inventory flags, stage claims and adjustment rules are accepted
    only inside the signed DEVELOPMENT sidecar contract.
    """
    snapshot, validation, ruleset, manifest = (
        bundle.snapshot,
        bundle.snapshot_validation,
        bundle.compiled_ruleset,
        bundle.manifest,
    )
    _validate_verified_bundle_bindings(bundle)
    if validation.snapshot_digest != sha256_bytes(pretty_json_bytes(dict(snapshot))):
        raise ContractValidationError("P03_PREFLIGHT_SNAPSHOT_BINDING_MISMATCH")
    policy_revision = str(manifest.get("policy_source_revision", ""))
    policy_digest = str(manifest.get("policy_bundle_sha256", ""))
    if not policy_revision or not _is_sha256(policy_digest):
        raise ContractValidationError("P03_PREFLIGHT_POLICY_BINDING_INVALID")
    verified_evidence = _verify_adaptation_evidence(
        bundle,
        evidence_context,
        policy_revision=policy_revision,
        policy_digest=policy_digest,
    )
    side_payload = thaw_verified_payload(verified_evidence) if verified_evidence else {}
    registry = snapshot.get("policy_registry")
    expected_scope = str(registry.get("scope", "")) if isinstance(registry, Mapping) else ""
    before_sha = str(snapshot["architecture"]["before_commit"])
    after_sha = str(snapshot["architecture"]["after_commit"])
    side_inputs = _side_evidence_inputs(
        side_payload, bundle, before_sha, after_sha, verified_evidence
    )
    obligations = _effective_obligations(
        bundle.obligations, side_inputs["mandatory_classifications"], verified_evidence
    )
    before = evaluate_obligations(
        snapshot,
        ruleset,
        bundle.evidence_ledger,
        "before",
        validation,
        policy_source_revision=policy_revision,
        policy_bundle_sha256=policy_digest,
    )
    after = evaluate_obligations(
        snapshot,
        ruleset,
        bundle.evidence_ledger,
        "after",
        validation,
        policy_source_revision=policy_revision,
        policy_bundle_sha256=policy_digest,
    )
    changes = list(
        diff_snapshot(
            snapshot,
            fact_absence_proofs=side_inputs["fact_absence_proofs"],
            policy_inventory_complete=side_inputs["policy_inventory_complete"],
            source_digests=bundle.source_digests,
            policy_before_rows=side_inputs["policy_before_rows"],
            policy_after_rows=side_inputs["policy_after_rows"],
        )
    )
    changes.extend(_diff_applicability(before, after))
    applicability_after = {row.obligation_id: row.status.value for row in after.results}
    pair_evidence = side_inputs["evaluator_evidence"]
    proofs = side_inputs["pair_proofs"]
    checked_artifacts = _merge_artifacts(bundle.artifact_bytes, side_inputs["artifact_bytes"])
    parent_evaluator_bindings = _verified_parent_evaluator_bindings(bundle)
    pairs: list[PairAssessment] = []
    obligations_by_id = {str(row["id"]): row for row in obligations}
    for representation in sorted(bundle.representations, key=lambda item: str(item.get("id", ""))):
        if representation.get("active") is False:
            continue
        representation_id = str(representation.get("id", ""))
        for obligation_id in sorted(_string_set(representation.get("covers"))):
            obligation = obligations_by_id.get(obligation_id)
            if obligation is None:
                continue
            pairs.append(
                assess_pair(
                    representation=representation,
                    obligation=obligation,
                    architecture_source_sha=after.architecture_source_sha,
                    evaluator_evidence=pair_evidence.get((representation_id, obligation_id)),
                    semantic_proof=proofs.get((representation_id, obligation_id)),
                    artifact_bytes=checked_artifacts,
                    source_digests=bundle.source_digests,
                )
            )
    coverage = assess_mandatory_coverage(
        applicability=after,
        obligations=obligations,
        pair_assessments=pairs,
        required_stages=side_inputs["required_stages"],
        stage_contract_verified=side_inputs["stage_contract_verified"],
    )
    mandatory = [str(row["id"]) for row in obligations if row.get("mandatory") is True]
    covered = [row.obligation_id for row in coverage.obligations if row.status == "COVERED"]
    impact_graph = replace(
        bundle.trace_graph,
        inventory_complete_verified=side_inputs["trace_inventory_verified"],
    )
    impact = analyze_impact(
        architecture_before_sha=before.architecture_source_sha,
        architecture_after_sha=after.architecture_source_sha,
        policy_source_revision=policy_revision,
        policy_bundle_sha256=policy_digest,
        ruleset_sha256=ruleset.ruleset_source_sha256,
        snapshot_sha256=validation.snapshot_digest or "",
        changes=changes,
        graph=impact_graph,
        source_digests=bundle.source_digests,
        expected_scope=expected_scope,
        representation_ids=[str(row["id"]) for row in bundle.representations],
        applicability_after=applicability_after,
        mandatory_obligations=mandatory,
        covered_obligations=covered,
        change_inventory_verified=side_inputs["change_inventory_verified"],
    )
    plan = build_operation_plan(
        representations=bundle.representations,
        obligations=obligations,
        applicability=applicability_after,
        pair_assessments=pairs,
        coverage=coverage,
        impact=impact,
        templates=bundle.templates,
        artifact_bytes=checked_artifacts,
        authorized_template_descriptor_digests=side_inputs["authorized_template_descriptor_sha256"],
        adjustment_rules=side_inputs["adjustment_rules"],
        cost_model=bundle.cost_model,
        cost_model_authorized=side_inputs["cost_model_authorized"],
        adjustments_authorized=verified_evidence is not None,
    )
    if evidence_context is not None and verified_evidence is None:
        plan = _with_hold(plan, "ADAPTATION_EVIDENCE_AUTHORITY_UNRESOLVED")
    cost_verdict = _cost_verdict(plan, bundle.cost_model, side_inputs["cost_model_authorized"])
    if cost_verdict != "PASS":
        plan = _with_hold(
            plan, "COST_MODEL_UNRESOLVED" if cost_verdict == "UNKNOWN" else "COST_LIMIT_EXCEEDED"
        )

    candidate: Mapping[str, Any] | None = None
    candidate_digest: str | None = None
    candidate_v1: Mapping[str, Any] | None = None
    if not plan.reject_reasons:
        candidate = materialize_candidate(
            parent_configuration=bundle.parent_configuration,
            parent_configuration_bytes=bundle.parent_configuration_bytes,
            parent_path=bundle.parent_configuration_path,
            parent_sha256=bundle.parent_configuration_sha256,
            architecture_source_sha=after.architecture_source_sha,
            policy_source_revision=policy_revision,
            policy_bundle_sha256=policy_digest,
            policy_ruleset_sha256=ruleset.ruleset_source_sha256,
            input_bundle_sha256=str(manifest.get("bundle_sha256", "")),
            impact_assessment_sha256=impact.assessment_sha256,
            method_version=METHOD_VERSION,
            configuration_version=derive_configuration_version(
                parent_configuration_sha256=bundle.parent_configuration_sha256,
                operation_plan_sha256=plan.plan_sha256,
                architecture_source_sha=after.architecture_source_sha,
                policy_source_revision=policy_revision,
                policy_bundle_sha256=policy_digest,
            ),
            operation_plan=plan,
            artifact_bytes=checked_artifacts,
            valid_obligation_ids=tuple(obligations_by_id),
            parent_evaluator_bindings=parent_evaluator_bindings,
        )
        candidate_digest = candidate_sha256(candidate)
    candidate_pairs: list[PairAssessment] = []
    candidate_coverage: CoverageAssessment | None = None
    if candidate is not None:
        for representation in candidate["representations"]:
            if not isinstance(representation, Mapping) or representation.get("active") is False:
                continue
            representation_id = str(representation.get("id", ""))
            for obligation_id in sorted(_string_set(representation.get("covers"))):
                obligation = obligations_by_id.get(obligation_id)
                if obligation is None:
                    continue
                candidate_pairs.append(
                    assess_pair(
                        representation=representation,
                        obligation=obligation,
                        architecture_source_sha=after.architecture_source_sha,
                        evaluator_evidence=pair_evidence.get((representation_id, obligation_id)),
                        semantic_proof=proofs.get((representation_id, obligation_id)),
                        artifact_bytes=checked_artifacts,
                        source_digests=bundle.source_digests,
                    )
                )
        candidate_coverage = assess_mandatory_coverage(
            applicability=after,
            obligations=obligations,
            pair_assessments=candidate_pairs,
            required_stages=side_inputs["required_stages"],
            stage_contract_verified=side_inputs["stage_contract_verified"],
        )
    decision_coverage = candidate_coverage or coverage
    decision_pairs = candidate_pairs if candidate is not None else pairs
    input_status = _input_status(
        validation, bundle.bundle_provenance, bundle.trust_scope, verified_evidence
    )
    mandatory_ids = {str(row["id"]) for row in obligations if row.get("mandatory") is True}
    before_unresolved = any(
        row.obligation_id in mandatory_ids and row.status.value == "UNKNOWN"
        for row in before.results
    )
    invariants = _invariant_verdicts(
        input_status=input_status,
        coverage=decision_coverage,
        plan=plan,
        candidate=candidate,
        candidate_digest=candidate_digest,
        representations=bundle.representations,
        obligations=obligations,
        before_applicability=before,
        after_applicability=after,
        pairs=decision_pairs,
        bundle=bundle,
        impact=impact,
        evidence_context_verified=verified_evidence is not None,
        authorized_template_digests=side_inputs["authorized_template_descriptor_sha256"],
        artifact_bytes=checked_artifacts,
    )
    governance_arguments: dict[str, Any] = {
        "method_version": METHOD_VERSION,
        "architecture_before_sha": before.architecture_source_sha,
        "architecture_after_sha": after.architecture_source_sha,
        "policy_source_revision": policy_revision,
        "policy_ruleset_sha256": ruleset.ruleset_source_sha256,
        "input_bundle_sha256": str(manifest.get("bundle_sha256", "")),
        "parent_configuration_sha256": bundle.parent_configuration_sha256,
        "candidate_configuration_sha256": candidate_digest,
        "impact_assessment_sha256": impact.assessment_sha256,
        "coverage": decision_coverage,
        "operation_plan": plan,
        "invariant_verdicts": invariants,
        "cost_verdict": cost_verdict,
        "input_status": input_status,
        "candidate_validation_status": (
            str(candidate["candidate_validation"]["status"]) if candidate else None
        ),
        "pairs": [item.to_dict() for item in decision_pairs],
        "evidence_refs": validation.evidence_refs,
        "additional_reasons": (("BEFORE_APPLICABILITY_UNRESOLVED",) if before_unresolved else ()),
    }
    pipeline_authorization = _issue_governance_pipeline_authorization(**governance_arguments)
    governance = _decide_governance_authorized(
        **governance_arguments,
        pipeline_authorization=pipeline_authorization,
    )
    prediction_v1: Mapping[str, Any] | None = None
    if governance.result is GovernanceResult.ACCEPT and candidate is not None:
        candidate_v1 = adapt_candidate_v1(candidate, governance=governance)
        prediction_v1 = adapt_prediction_v1(
            architecture_source_sha=after.architecture_source_sha,
            method_version=METHOD_VERSION,
            input_bundle_sha256=str(manifest["bundle_sha256"]),
            plan=plan,
            impact_records=[record.to_dict() for record in impact.representations],
            candidate_configuration_sha256=str(candidate_digest),
            governance=governance,
        )
    return AdaptationResult(
        before,
        after,
        impact,
        tuple(pairs),
        tuple(candidate_pairs),
        coverage,
        candidate_coverage,
        plan,
        candidate,
        candidate_digest,
        governance,
        prediction_v1,
        candidate_v1,
        verified_evidence.trust_scope if verified_evidence is not None else None,
    )


def _verify_adaptation_evidence(
    bundle: VerifiedPBundle,
    sidecar: Mapping[str, Any] | None,
    *,
    policy_revision: str,
    policy_digest: str,
) -> VerifiedAdaptationEvidence | None:
    if sidecar is None:
        return None
    architecture = bundle.snapshot.get("architecture")
    registry = bundle.snapshot.get("policy_registry")
    if not isinstance(architecture, Mapping) or not isinstance(registry, Mapping):
        raise ContractValidationError("P03_EVIDENCE_CONTEXT_SOURCE_INVALID")
    content_digest = _verified_bundle_content_sha256(bundle)
    test_registered = bundle.trust_scope == "TEST_ONLY" and (
        _VERIFIED_V3_BUNDLE_DIGESTS.get(bundle) == content_digest
        or _TEST_ONLY_BUNDLE_DIGESTS.get(bundle) == content_digest
    )
    expected = {
        "input_bundle_sha256": str(bundle.manifest.get("bundle_sha256", "")),
        "architecture_before_sha": str(architecture.get("before_commit", "")),
        "architecture_after_sha": str(architecture.get("after_commit", "")),
        "policy_source_revision": policy_revision,
        "policy_bundle_sha256": policy_digest,
        "evaluation_as_of": str(architecture.get("evaluation_as_of", "")),
        "scope": str(registry.get("scope", "")),
    }
    return verify_adaptation_evidence(
        sidecar,
        expected_bindings=expected,
        expected_source_digests=bundle.source_digests,
        verifier_registry=_BUNDLE_EVIDENCE_VERIFIER_REGISTRIES.get(bundle),
        allow_test_only=test_registered,
        expected_trust_scope=bundle.trust_scope,
    )


def _side_evidence_inputs(
    payload: Mapping[str, Any],
    bundle: VerifiedPBundle,
    before_sha: str,
    after_sha: str,
    verified_evidence: VerifiedAdaptationEvidence | None,
) -> dict[str, Any]:
    if verified_evidence is None:
        return _empty_side_evidence_inputs()
    registry = bundle.snapshot.get("policy_registry")
    scope = str(registry.get("scope", "")) if isinstance(registry, Mapping) else ""
    bundle_digest = str(bundle.manifest.get("bundle_sha256", ""))
    policy_revision = str(bundle.manifest.get("policy_source_revision", ""))
    policy_digest = str(bundle.manifest.get("policy_bundle_sha256", ""))
    outer_bindings = set(verified_evidence.source_bindings)
    evaluator_evidence: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in payload.get("evaluator_evidence", []):
        pair_key = _pair_key(row)
        evidence = row.get("evidence")
        if pair_key in evaluator_evidence or not isinstance(evidence, Mapping):
            raise ContractValidationError("P03_EVIDENCE_PAIR_RECORD_INVALID")
        evaluator_evidence[pair_key] = dict(evidence)

    pair_proofs: dict[tuple[str, str], EvidenceProof] = {}
    for row in payload.get("pair_proofs", []):
        pair_key = _pair_key(row)
        if pair_key in pair_proofs:
            raise ContractValidationError("P03_EVIDENCE_PAIR_PROOF_CONFLICT")
        if row.get("verifier_id") != verified_evidence.verifier_id:
            raise ContractValidationError("P03_EVIDENCE_PAIR_PROOF_VERIFIER_MISMATCH")
        bindings = _proof_source_bindings(
            row, bundle.source_digests, allowed_bindings=outer_bindings
        )
        pair_proofs[pair_key] = EvidenceProof(
            ProofStatus(str(row["status"])),
            str(row["subject_sha256"]),
            bindings,
            str(row["verifier_id"]),
            tuple(sorted(set(_string_tuple(row.get("evidence_refs"))))),
            tuple(sorted(set(_string_tuple(row.get("reason_codes"))))),
        )

    artifact_bytes: dict[str, bytes] = {}
    for row in payload.get("artifact_bytes", []):
        path, digest, encoded = row.get("path"), row.get("sha256"), row.get("content_base64")
        if not isinstance(path, str) or not isinstance(encoded, str) or not isinstance(digest, str):
            raise ContractValidationError("P03_EVIDENCE_ARTIFACT_INVALID")
        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as error:
            raise ContractValidationError("P03_EVIDENCE_ARTIFACT_ENCODING_INVALID") from error
        if sha256_bytes(content) != digest:
            raise ContractValidationError("P03_EVIDENCE_ARTIFACT_DIGEST_MISMATCH")
        if path in artifact_bytes:
            raise ContractValidationError("P03_EVIDENCE_ARTIFACT_DUPLICATE_PATH")
        artifact_bytes[path] = content

    absence: dict[tuple[str, str, str], bool | None] = {}
    expected_revision = {"before": before_sha, "after": after_sha}
    for row in payload.get("fact_absence_proofs", []):
        absence_key = (str(row["state"]), str(row["predicate"]), str(row["scope"]))
        if absence_key in absence:
            raise ContractValidationError("P03_EVIDENCE_ABSENCE_PROOF_CONFLICT")
        if row.get("architecture_source_sha") != expected_revision[absence_key[0]]:
            raise ContractValidationError("P03_EVIDENCE_ABSENCE_REVISION_MISMATCH")
        proof = row["proof"]
        proof_subject = {
            "claim_type": "fact_absence",
            "state": absence_key[0],
            "predicate": absence_key[1],
            "scope": absence_key[2],
            "architecture_source_sha": expected_revision[absence_key[0]],
            "input_bundle_sha256": bundle_digest,
        }
        _verify_scoped_proof(
            proof,
            expected_subject=proof_subject,
            expected_scope=absence_key[2],
            expected_architecture_shas=(expected_revision[absence_key[0]],),
            verified_evidence=verified_evidence,
            source_digests=bundle.source_digests,
            allowed_bindings=outer_bindings,
            allowed_source_ids=_fact_absence_source_ids(
                bundle, absence_key[0], absence_key[1], absence_key[2]
            ),
            required_source_ids=_fact_absence_source_ids(
                bundle, absence_key[0], absence_key[1], absence_key[2]
            ),
        )
        refs = _string_tuple(proof.get("evidence_refs"))
        absence[absence_key] = proof.get("status") == "VALID" and bool(refs)

    inventory_rows: dict[str, Sequence[Mapping[str, Any]]] = {}
    inventory_complete: dict[str, bool | None] = {}
    for row in payload.get("policy_inventories", []):
        state = str(row.get("state"))
        if state in inventory_rows:
            raise ContractValidationError("P03_EVIDENCE_POLICY_INVENTORY_CONFLICT")
        if row.get("architecture_source_sha") != expected_revision.get(state):
            raise ContractValidationError("P03_EVIDENCE_POLICY_REVISION_MISMATCH")
        rows = row.get("rows")
        if not isinstance(rows, list) or any(not isinstance(item, Mapping) for item in rows):
            raise ContractValidationError("P03_EVIDENCE_POLICY_ROWS_INVALID")
        if row.get("scope") != scope:
            raise ContractValidationError("P03_EVIDENCE_POLICY_SCOPE_MISMATCH")
        if any(item.get("scope") != scope for item in rows):
            raise ContractValidationError("P03_EVIDENCE_POLICY_ROW_SCOPE_MISMATCH")
        proof = row["proof"]
        proof_subject = {
            "claim_type": "policy_inventory",
            "state": state,
            "scope": scope,
            "architecture_source_sha": expected_revision[state],
            "policy_source_revision": policy_revision,
            "policy_bundle_sha256": policy_digest,
            "rows_sha256": sha256_bytes(canonical_json_bytes(rows)),
        }
        _verify_scoped_proof(
            proof,
            expected_subject=proof_subject,
            expected_scope=scope,
            expected_architecture_shas=(expected_revision[state],),
            verified_evidence=verified_evidence,
            source_digests=bundle.source_digests,
            allowed_bindings=outer_bindings,
            allowed_source_ids=_policy_source_ids(bundle, rows),
            required_source_ids=_policy_source_ids(bundle, rows),
        )
        inventory_rows[state] = tuple(dict(item) for item in rows)
        inventory_complete[state] = proof.get("status") == "VALID" and bool(
            _string_tuple(proof.get("evidence_refs"))
        )
    both_inventories = set(inventory_rows) == {"before", "after"}

    required_stages_value = payload.get("required_stages", {})
    required_stages = (
        {str(key): tuple(_string_tuple(value)) for key, value in required_stages_value.items()}
        if isinstance(required_stages_value, Mapping)
        else {}
    )
    stage_proof = payload.get("stage_contract_proof", {})
    capability_digest = bundle.source_digests.get("P_CAPABILITIES")
    stage_subject = {
        "claim_type": "required_stages",
        "required_stages_sha256": sha256_bytes(canonical_json_bytes(required_stages)),
        "input_bundle_sha256": bundle_digest,
    }
    _verify_scoped_proof(
        stage_proof,
        expected_subject=stage_subject,
        expected_scope=scope,
        expected_architecture_shas=(after_sha,),
        verified_evidence=verified_evidence,
        source_digests=bundle.source_digests,
        allowed_bindings=outer_bindings,
        allowed_source_ids={"P_CAPABILITIES"},
        required_source_ids={"P_CAPABILITIES"},
    )
    stage_contract_verified = isinstance(stage_proof, Mapping) and (
        stage_proof.get("status") == "VALID"
    )

    # V1 signed artifact hashes are retained for diagnostics only. They never
    # authorize a template descriptor or enable a new ADD/REPLACE.
    authorized_descriptors = frozenset(
        _string_tuple(payload.get("authorized_template_descriptor_sha256"))
        if verified_evidence.schema_version == 2
        else ()
    )
    materialized_descriptor_digests = {
        template_descriptor_sha256(template) for template in bundle.templates
    }
    if not authorized_descriptors.issubset(materialized_descriptor_digests):
        raise ContractValidationError("P03_TEMPLATE_AUTHORITY_NOT_IN_VERIFIED_CAPABILITIES")
    if authorized_descriptors and (
        "P_CAPABILITIES" not in {source_id for source_id, _ in outer_bindings}
    ):
        raise ContractValidationError("P03_TEMPLATE_AUTHORITY_SOURCE_NOT_BOUND")

    mandatory_classifications: dict[str, bool] = {}
    classification_claim = payload.get("test_only_mandatory_classification")
    if classification_claim is not None:
        if verified_evidence.trust_scope != "TEST_ONLY" or verified_evidence.schema_version != 2:
            raise ContractValidationError("P03_TEST_ONLY_CLASSIFICATION_SCOPE_INVALID")
        rows = (
            classification_claim.get("rows") if isinstance(classification_claim, Mapping) else None
        )
        proof = (
            classification_claim.get("proof") if isinstance(classification_claim, Mapping) else None
        )
        if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
            raise ContractValidationError("P03_TEST_ONLY_CLASSIFICATION_ROWS_INVALID")
        row_ids = [str(row.get("obligation_id", "")) for row in rows]
        expected_ids = {str(row.get("id")) for row in bundle.obligations}
        if (
            len(row_ids) != len(set(row_ids))
            or set(row_ids) != expected_ids
            or any(type(row.get("mandatory")) is not bool for row in rows)
        ):
            raise ContractValidationError("P03_TEST_ONLY_CLASSIFICATION_DENOMINATOR_INVALID")
        classification_source_ids = _policy_source_ids(bundle, rows)
        classification_subject = {
            "claim_type": "test_only_mandatory_classification",
            "rows_sha256": sha256_bytes(canonical_json_bytes(rows)),
            "input_bundle_sha256": bundle_digest,
            "policy_source_revision": policy_revision,
            "policy_bundle_sha256": policy_digest,
        }
        _verify_scoped_proof(
            proof,
            expected_subject=classification_subject,
            expected_scope=scope,
            expected_architecture_shas=(before_sha, after_sha),
            verified_evidence=verified_evidence,
            source_digests=bundle.source_digests,
            allowed_bindings=outer_bindings,
            allowed_source_ids=classification_source_ids,
            required_source_ids=classification_source_ids,
        )
        if isinstance(proof, Mapping) and proof.get("status") == "VALID":
            mandatory_classifications = {
                str(row["obligation_id"]): bool(row["mandatory"]) for row in rows
            }
    trace_proof = payload.get("trace_inventory_proof", {})
    trace_subject = {
        "claim_type": "trace_inventory",
        "trace_graph_sha256": bundle.trace_graph.graph_sha256,
        "input_bundle_sha256": bundle_digest,
    }
    trace_bindings = _verify_scoped_proof(
        trace_proof,
        expected_subject=trace_subject,
        expected_scope=scope,
        expected_architecture_shas=(before_sha, after_sha),
        verified_evidence=verified_evidence,
        source_digests=bundle.source_digests,
        allowed_bindings=outer_bindings,
        allowed_source_ids={"P_TRACEABILITY"},
        required_source_ids={"P_TRACEABILITY"},
    )
    change_proof = payload.get("change_inventory_proof", {})
    change_subject = {
        "claim_type": "change_inventory",
        "snapshot_sha256": bundle.snapshot_validation.snapshot_digest,
        "input_bundle_sha256": bundle_digest,
        "policy_source_revision": policy_revision,
        "policy_bundle_sha256": policy_digest,
    }
    change_source_ids = _change_inventory_source_ids(bundle)
    change_bindings = _verify_scoped_proof(
        change_proof,
        expected_subject=change_subject,
        expected_scope=scope,
        expected_architecture_shas=(before_sha, after_sha),
        verified_evidence=verified_evidence,
        source_digests=bundle.source_digests,
        allowed_bindings=outer_bindings,
        allowed_source_ids=change_source_ids,
        required_source_ids=change_source_ids,
    )
    cost_model_proof = payload.get("cost_model_proof", {})
    cost_subject = {
        "claim_type": "cost_model_authority",
        "cost_model_sha256": sha256_bytes(canonical_json_bytes(bundle.cost_model)),
        "capabilities_sha256": capability_digest,
        "input_bundle_sha256": bundle_digest,
    }
    cost_bindings = _verify_scoped_proof(
        cost_model_proof,
        expected_subject=cost_subject,
        expected_scope=scope,
        expected_architecture_shas=(after_sha,),
        verified_evidence=verified_evidence,
        source_digests=bundle.source_digests,
        allowed_bindings=outer_bindings,
        allowed_source_ids={"P_CAPABILITIES"},
        required_source_ids={"P_CAPABILITIES"},
    )
    cost_model_authorized = (
        bundle.cost_model is not None
        and isinstance(cost_model_proof, Mapping)
        and cost_model_proof.get("status") == "VALID"
        and capability_digest is not None
        and ("P_CAPABILITIES", capability_digest) in cost_bindings
    )
    return {
        "evaluator_evidence": evaluator_evidence,
        "pair_proofs": pair_proofs,
        "artifact_bytes": artifact_bytes,
        "fact_absence_proofs": absence,
        "policy_inventory_complete": inventory_complete,
        "policy_before_rows": inventory_rows.get("before") if both_inventories else None,
        "policy_after_rows": inventory_rows.get("after") if both_inventories else None,
        "required_stages": required_stages,
        "stage_contract_verified": stage_contract_verified,
        "trace_inventory_verified": isinstance(trace_proof, Mapping)
        and trace_proof.get("status") == "VALID"
        and ("P_TRACEABILITY", bundle.source_digests.get("P_TRACEABILITY")) in trace_bindings,
        "change_inventory_verified": isinstance(change_proof, Mapping)
        and change_proof.get("status") == "VALID"
        and bool(change_bindings),
        "adjustment_rules": tuple(payload.get("adjustment_rules", [])),
        "authorized_template_descriptor_sha256": authorized_descriptors,
        "mandatory_classifications": mandatory_classifications,
        "cost_model_authorized": cost_model_authorized,
    }


def _effective_obligations(
    obligations: Sequence[Mapping[str, Any]],
    classifications: Mapping[str, bool],
    verified_evidence: VerifiedAdaptationEvidence | None,
) -> tuple[Mapping[str, Any], ...]:
    """Apply only a complete, signed TEST_ONLY classification projection."""
    if not classifications:
        return tuple(obligations)
    expected_ids = {str(row.get("id")) for row in obligations}
    if (
        verified_evidence is None
        or verified_evidence.trust_scope != "TEST_ONLY"
        or set(classifications) != expected_ids
    ):
        raise ContractValidationError("P03_TEST_ONLY_CLASSIFICATION_NOT_VERIFIED")
    return tuple(dict(row) | {"mandatory": classifications[str(row["id"])]} for row in obligations)


def _pair_key(row: Mapping[str, Any]) -> tuple[str, str]:
    representation_id, obligation_id = row.get("representation_id"), row.get("obligation_id")
    if not isinstance(representation_id, str) or not isinstance(obligation_id, str):
        raise ContractValidationError("P03_EVIDENCE_PAIR_KEY_INVALID")
    return representation_id, obligation_id


def _proof_source_bindings(
    proof: Mapping[str, Any],
    source_digests: Mapping[str, str],
    *,
    allowed_bindings: set[tuple[str, str]] | None = None,
    allowed_source_ids: set[str] | None = None,
    require_sources: bool = True,
) -> tuple[tuple[str, str], ...]:
    rows = proof.get("source_bindings")
    if not isinstance(rows, list) or (require_sources and not rows):
        raise ContractValidationError("P03_EVIDENCE_PROOF_SOURCE_MISSING")
    bindings: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ContractValidationError("P03_EVIDENCE_PROOF_SOURCE_INVALID")
        source_id, digest = row.get("source_id"), row.get("sha256")
        if not isinstance(source_id, str) or source_digests.get(source_id) != digest:
            raise ContractValidationError("P03_EVIDENCE_PROOF_SOURCE_MISMATCH")
        if allowed_source_ids is not None and source_id not in allowed_source_ids:
            raise ContractValidationError("P03_EVIDENCE_PROOF_SOURCE_UNRELATED")
        if allowed_bindings is not None and (source_id, str(digest)) not in allowed_bindings:
            raise ContractValidationError("P03_EVIDENCE_PROOF_SOURCE_NOT_BOUND_BY_SIDECAR")
        bindings.append((source_id, str(digest)))
    if tuple(sorted(set(bindings))) != tuple(bindings):
        raise ContractValidationError("P03_EVIDENCE_PROOF_SOURCE_INVALID")
    if require_sources and not _string_tuple(proof.get("evidence_refs")):
        raise ContractValidationError("P03_EVIDENCE_PROOF_REFERENCE_MISSING")
    return tuple(bindings)


def _verify_scoped_proof(
    proof: Any,
    *,
    expected_subject: Mapping[str, Any],
    expected_scope: str,
    expected_architecture_shas: tuple[str, ...],
    verified_evidence: VerifiedAdaptationEvidence,
    source_digests: Mapping[str, str],
    allowed_bindings: set[tuple[str, str]],
    allowed_source_ids: set[str] | None = None,
    required_source_ids: set[str] | None = None,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(proof, Mapping):
        raise ContractValidationError("P03_EVIDENCE_PROOF_INVALID")
    if (
        proof.get("subject_sha256") != sha256_bytes(canonical_json_bytes(dict(expected_subject)))
        or proof.get("scope") != expected_scope
        or tuple(proof.get("architecture_source_shas", ())) != expected_architecture_shas
        or proof.get("verifier_id") != verified_evidence.verifier_id
    ):
        raise ContractValidationError("P03_EVIDENCE_PROOF_CONTEXT_MISMATCH")
    is_valid = proof.get("status") == "VALID"
    bindings = _proof_source_bindings(
        proof,
        source_digests,
        allowed_bindings=allowed_bindings,
        allowed_source_ids=allowed_source_ids,
        require_sources=is_valid,
    )
    if is_valid and required_source_ids is not None:
        if not required_source_ids.issubset({source_id for source_id, _ in bindings}):
            raise ContractValidationError("P03_EVIDENCE_PROOF_REQUIRED_SOURCE_MISSING")
    return bindings if is_valid else ()


def _empty_side_evidence_inputs() -> dict[str, Any]:
    return {
        "evaluator_evidence": {},
        "pair_proofs": {},
        "artifact_bytes": {},
        "fact_absence_proofs": {},
        "policy_inventory_complete": {},
        "policy_before_rows": None,
        "policy_after_rows": None,
        "required_stages": {},
        "stage_contract_verified": False,
        "trace_inventory_verified": False,
        "change_inventory_verified": False,
        "adjustment_rules": (),
        "authorized_template_descriptor_sha256": frozenset(),
        "mandatory_classifications": {},
        "cost_model_authorized": False,
    }


def _policy_source_ids(bundle: VerifiedPBundle, rows: Sequence[Mapping[str, Any]]) -> set[str]:
    registry = bundle.snapshot.get("policy_registry")
    result: set[str] = set()
    if isinstance(registry, Mapping):
        result.update(
            str(registry[key])
            for key in ("source_id", "authority_charter_source_id")
            if isinstance(registry.get(key), str)
        )
    for row in [*bundle.snapshot.get("policies", []), *rows]:
        if isinstance(row, Mapping):
            result.update(
                str(row[key])
                for key in ("source_id", "approval_source_id")
                if isinstance(row.get(key), str)
            )
    return result


def _fact_absence_source_ids(
    bundle: VerifiedPBundle, state: str, predicate: str, scope: str
) -> set[str]:
    claims = bundle.snapshot.get("completeness_claims", [])
    if not isinstance(claims, list):
        return set()
    return {
        str(source_id)
        for claim in claims
        if isinstance(claim, Mapping)
        and claim.get("state") == state
        and claim.get("fact_type") == predicate
        and claim.get("scope") == scope
        for source_id in _string_tuple(claim.get("evidence_source_ids"))
    }


def _change_inventory_source_ids(bundle: VerifiedPBundle) -> set[str]:
    result: set[str] = set()
    snapshot = bundle.snapshot
    for row in snapshot.get("facts", []):
        if isinstance(row, Mapping):
            result.update(_string_tuple(row.get("source_ids")))
    result.update(_policy_source_ids(bundle, ()))
    for claim in snapshot.get("completeness_claims", []):
        if isinstance(claim, Mapping):
            result.update(_string_tuple(claim.get("evidence_source_ids")))
    return result


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return ()
    return tuple(value)


def _merge_artifacts(
    pinned: Mapping[str, bytes], sidecar_artifacts: Mapping[str, bytes]
) -> dict[str, bytes]:
    result = dict(pinned)
    for path, content in sidecar_artifacts.items():
        existing = result.get(path)
        if existing is not None and existing != content:
            raise ContractValidationError("P03_EVIDENCE_ARTIFACT_PATH_COLLISION")
        result[path] = content
    return result


def _diff_applicability(
    before: ApplicabilityAssessment, after: ApplicabilityAssessment
) -> list[ChangeRecord]:
    old = {row.obligation_id: row.status.value for row in before.results}
    new = {row.obligation_id: row.status.value for row in after.results}
    result: list[ChangeRecord] = []
    for obligation_id in sorted(set(old) | set(new)):
        old_status, new_status = old.get(obligation_id), new.get(obligation_id)
        kind = (
            ChangeKind.INDETERMINATE
            if old_status is None or new_status is None
            else (ChangeKind.UNCHANGED if old_status == new_status else ChangeKind.VALUE_CHANGED)
        )
        result.append(
            ChangeRecord(
                "obligation:" + obligation_id,
                "obligation",
                obligation_id,
                kind,
                old_version=old_status,
                new_version=new_status,
                reason_codes=(
                    "APPLICABILITY_STATE_UNCHANGED"
                    if kind is ChangeKind.UNCHANGED
                    else "APPLICABILITY_STATE_CHANGED"
                    if kind is ChangeKind.VALUE_CHANGED
                    else "APPLICABILITY_RESULT_MISSING",
                ),
            )
        )
    return result


def _invariant_verdicts(
    *,
    input_status: str,
    coverage: CoverageAssessment,
    plan: OperationPlan,
    candidate: Mapping[str, Any] | None,
    candidate_digest: str | None,
    representations: Sequence[Mapping[str, Any]],
    obligations: Sequence[Mapping[str, Any]],
    before_applicability: ApplicabilityAssessment,
    after_applicability: ApplicabilityAssessment,
    pairs: Sequence[PairAssessment],
    bundle: VerifiedPBundle,
    impact: ImpactAssessment,
    evidence_context_verified: bool,
    authorized_template_digests: frozenset[str],
    artifact_bytes: Mapping[str, bytes],
) -> dict[str, str]:
    candidate_rows = candidate.get("representations") if candidate is not None else None
    candidate_status = (
        candidate.get("candidate_validation", {}).get("status")
        if isinstance(candidate, Mapping)
        and isinstance(candidate.get("candidate_validation"), Mapping)
        else None
    )
    after_status = {row.obligation_id: row.status.value for row in after_applicability.results}
    before_status = {row.obligation_id: row.status.value for row in before_applicability.results}
    pair_index: dict[tuple[str, str], list[PairAssessment]] = {}
    for pair in pairs:
        pair_index.setdefault((pair.representation_id, pair.obligation_id), []).append(pair)

    plan_body = {
        "operations": [operation.to_dict() for operation in plan.operations],
        "hold_reasons": list(plan.hold_reasons),
        "reject_reasons": list(plan.reject_reasons),
    }
    plan_digest_valid = sha256_bytes(canonical_json_bytes(plan_body)) == plan.plan_sha256 and len(
        {(op.target_type, op.target_id) for op in plan.operations}
    ) == len(plan.operations)
    impact_digest_valid = _semantic_digest_valid(impact.to_dict(), "assessment_sha256")
    coverage_digest_valid = _semantic_digest_valid(coverage.to_dict(), "assessment_sha256")
    candidate_digest_valid = False
    if candidate is not None and candidate_digest is not None:
        try:
            candidate_digest_valid = candidate_sha256(candidate) == candidate_digest
        except ContractValidationError:
            candidate_digest_valid = False

    input_positive = (
        input_status == "VALID"
        and evidence_context_verified
        and _bundle_registration_is_valid(bundle)
    )
    input_verdict = "PASS" if input_positive else "FAIL" if input_status == "INVALID" else "UNKNOWN"

    obligation_ids = [str(row.get("id")) for row in obligations]
    coverage_rows = {row.obligation_id: row for row in coverage.obligations}
    coverage_accounted = (
        len(coverage_rows) == len(coverage.obligations)
        and set(coverage_rows) == set(obligation_ids)
        and coverage.mandatory_total
        == sum(
            1
            for row in obligations
            if row.get("mandatory") is True and after_status.get(str(row.get("id"))) == "ACTIVE"
        )
        and coverage.mandatory_covered
        == sum(row.status == "COVERED" for row in coverage.obligations)
    )
    coverage_verdict = (
        "PASS"
        if coverage.status.value == "COMPLETE" and coverage_accounted and coverage_digest_valid
        else "FAIL"
        if coverage.status.value == "INCOMPLETE" or not coverage_accounted
        else "UNKNOWN"
    )

    representation_by_id = {
        str(row.get("id")): row for row in representations if isinstance(row.get("id"), str)
    }
    deactivation_ops = [op for op in plan.operations if op.operation.value == "deactivate"]
    deactivation_safe = True
    for operation in deactivation_ops:
        representation = representation_by_id.get(operation.target_id)
        covered_ids = _string_set(representation.get("covers")) if representation else set()
        if not representation or not covered_ids:
            deactivation_safe = False
            break
        for obligation_id in covered_ids:
            result = next(
                (
                    item
                    for item in after_applicability.results
                    if item.obligation_id == obligation_id
                ),
                None,
            )
            obligation = next(
                (item for item in obligations if item.get("id") == obligation_id), None
            )
            if (
                result is None
                or result.status.value != "INACTIVE"
                or not result.evidence_refs
                or obligation is None
            ):
                deactivation_safe = False
                break
        if not deactivation_safe:
            break
    has_applicability_evidence = bool(after_applicability.results) and set(after_status) == set(
        obligation_ids
    )
    inactive_verdict = (
        "PASS"
        if deactivation_safe and has_applicability_evidence
        else "FAIL"
        if not deactivation_safe
        else "UNKNOWN"
    )
    active_or_unknown_mandatory = {
        str(row.get("id"))
        for row in obligations
        if row.get("mandatory") is True
        and after_status.get(str(row.get("id"))) in {"ACTIVE", "UNKNOWN"}
    }
    no_required_deactivation = all(
        not (
            _string_set(representation_by_id[operation.target_id].get("covers"))
            & active_or_unknown_mandatory
        )
        for operation in deactivation_ops
        if operation.target_id in representation_by_id
    ) and all(operation.target_id in representation_by_id for operation in deactivation_ops)
    no_active_deactivation = (
        "PASS" if no_required_deactivation and has_applicability_evidence else "FAIL"
    )

    template_ops = [op for op in plan.operations if op.operation.value in {"add", "replace"}]
    template_authority_ok = all(
        _operation_matches_authorized_template(
            operation,
            bundle.templates,
            authorized_template_digests,
            artifact_bytes,
        )
        for operation in template_ops
    )
    artifact_verdict = (
        "PASS"
        if candidate_status == "valid" and candidate is not None and template_authority_ok
        else "FAIL"
        if candidate_status == "invalid" or not template_authority_ok
        else "UNKNOWN"
    )

    pair_verdict = "PASS"
    impact_by_id = {record.representation_id: record for record in impact.representations}
    if pair_verdict != "FAIL" and (
        not impact_digest_valid or set(impact_by_id) != set(representation_by_id)
    ):
        pair_verdict = "UNKNOWN"
    active_mandatory = {
        str(row.get("id"))
        for row in obligations
        if row.get("mandatory") is True and after_status.get(str(row.get("id"))) == "ACTIVE"
    }
    active_candidate_rows = [
        row
        for row in candidate_rows or []
        if isinstance(row, Mapping) and row.get("active") is not False
    ]
    valid_pairs_by_obligation: dict[str, set[str]] = {
        obligation_id: set() for obligation_id in active_mandatory
    }
    for representation in active_candidate_rows:
        representation_id = str(representation.get("id", ""))
        for obligation_id in _string_set(representation.get("covers")) & active_mandatory:
            assessments = pair_index.get((representation_id, obligation_id), [])
            statuses = {pair.status.value for pair in assessments}
            assessment_digests = {pair.assessment_sha256 for pair in assessments}
            if len(statuses) > 1 or len(assessment_digests) > 1 or "INVALID" in statuses:
                pair_verdict = "FAIL"
                continue
            if not assessments or any(
                pair.status.value != "VALID"
                or pair.architecture_source_sha != after_applicability.architecture_source_sha
                or not pair.evidence_refs
                or not _semantic_digest_valid(pair.to_dict(), "assessment_sha256")
                for pair in assessments
            ):
                if pair_verdict != "FAIL":
                    pair_verdict = "UNKNOWN"
                continue
            valid_pairs_by_obligation[obligation_id].add(representation_id)
    if any(not representation_ids for representation_ids in valid_pairs_by_obligation.values()):
        if pair_verdict != "FAIL":
            pair_verdict = "UNKNOWN"

    candidate_ids = (
        [str(row.get("id")) for row in candidate_rows if isinstance(row, Mapping)]
        if isinstance(candidate_rows, list)
        else []
    )
    parent_bound = (
        candidate is not None
        and candidate.get("parent_configuration", {}).get("sha256")
        == bundle.parent_configuration_sha256
        and sha256_bytes(bundle.parent_configuration_bytes) == bundle.parent_configuration_sha256
    )
    version_bound = candidate is not None and candidate.get("configuration_version") == (
        derive_configuration_version(
            parent_configuration_sha256=bundle.parent_configuration_sha256,
            operation_plan_sha256=plan.plan_sha256,
            architecture_source_sha=after_applicability.architecture_source_sha,
            policy_source_revision=str(bundle.manifest.get("policy_source_revision", "")),
            policy_bundle_sha256=str(bundle.manifest.get("policy_bundle_sha256", "")),
        )
    )
    stable_identity = (
        candidate is not None
        and candidate_digest_valid
        and parent_bound
        and version_bound
        and len(candidate_ids) == len(set(candidate_ids))
        and candidate_ids == sorted(candidate_ids)
        and plan_digest_valid
    )
    identity_violation = candidate is not None and (
        not candidate_digest_valid
        or not parent_bound
        or not version_bound
        or len(candidate_ids) != len(set(candidate_ids))
        or candidate_ids != sorted(candidate_ids)
        or not plan_digest_valid
    )
    identity_verdict = "PASS" if stable_identity else "FAIL" if identity_violation else "UNKNOWN"

    planned_changes = [operation.to_dict() for operation in plan.operations]
    candidate_changes = candidate.get("changes") if candidate is not None else None
    operations_match = isinstance(candidate_changes, list) and canonical_json_bytes(
        candidate_changes
    ) == canonical_json_bytes(planned_changes)
    criterion_preserved = candidate is not None and all(
        isinstance(row, Mapping)
        and isinstance(row.get("covers"), list)
        and all(
            next((str(item.get("criterion")) for item in obligations if item.get("id") == q), None)
            == row.get("criterion")
            for q in row["covers"]
        )
        for row in candidate_rows or []
    )
    no_weakening = (
        candidate_status == "valid"
        and criterion_preserved
        and operations_match
        and not plan.reject_reasons
    )
    invariant1 = (
        "PASS"
        if no_weakening
        else "FAIL"
        if not criterion_preserved or not operations_match or plan.reject_reasons
        else "UNKNOWN"
    )
    invariant9 = (
        "UNKNOWN"
        if candidate is None
        else "PASS"
        if operations_match and plan_digest_valid
        else "FAIL"
    )

    before_unknown_mandatory = any(
        row.get("mandatory") is True and before_status.get(str(row.get("id"))) == "UNKNOWN"
        for row in obligations
    )
    governance_ready = (
        coverage.status.value == "COMPLETE"
        and coverage_verdict == "PASS"
        and candidate_status == "valid"
        and not before_unknown_mandatory
        and input_positive
        and not plan.hold_reasons
        and not plan.reject_reasons
    )
    invariant10 = "PASS" if governance_ready else "UNKNOWN"

    deterministic = (
        plan_digest_valid
        and impact_digest_valid
        and coverage_digest_valid
        and candidate_digest_valid
        and candidate_ids == sorted(candidate_ids)
        and [op.target_id for op in plan.operations]
        == [
            op.target_id
            for op in sorted(
                plan.operations,
                key=lambda item: (
                    item.target_type,
                    item.target_id,
                    item.operation.value,
                    str(item.artifact_sha256 or ""),
                ),
            )
        ]
    )
    invariant11 = "PASS" if deterministic else "FAIL"
    isolation = "PASS" if _bundle_isolation_proven(bundle) else "UNKNOWN"
    return {
        "INV-01": invariant1,
        "INV-02": inactive_verdict,
        "INV-03": no_active_deactivation,
        "INV-04": coverage_verdict,
        "INV-05": input_verdict,
        "INV-06": artifact_verdict,
        "INV-07": pair_verdict,
        "INV-08": identity_verdict,
        "INV-09": invariant9,
        "INV-10": invariant10,
        "INV-11": invariant11,
        "INV-12": isolation,
    }


def _all_unknown_invariants() -> dict[str, str]:
    return {f"INV-{index:02d}": "UNKNOWN" for index in range(1, 13)}


def _semantic_digest_valid(payload: Mapping[str, Any], field_name: str) -> bool:
    body = dict(payload)
    claimed = body.pop(field_name, None)
    return isinstance(claimed, str) and claimed == sha256_bytes(canonical_json_bytes(body))


def _operation_matches_authorized_template(
    operation: Any,
    templates: Sequence[Mapping[str, Any]],
    authorized_descriptor_digests: frozenset[str],
    artifact_bytes: Mapping[str, bytes],
) -> bool:
    """Rebind an ADD/REPLACE payload to one exact signed capability descriptor."""
    if not isinstance(operation.payload, Mapping) or not isinstance(operation.artifact_sha256, str):
        return False
    for template in templates:
        normalized, digest, issue = validate_materializable_template(
            template,
            artifact_bytes=artifact_bytes,
            authorized_template_descriptor_digests=authorized_descriptor_digests,
        )
        if issue is not None or normalized is None or digest != operation.artifact_sha256:
            continue
        if canonical_json_bytes(dict(normalized)) == canonical_json_bytes(dict(operation.payload)):
            return True
    return False


def _bundle_registration_is_valid(bundle: VerifiedPBundle) -> bool:
    if bundle.bundle_provenance == "VERIFIED_V3":
        return _VERIFIED_V3_BUNDLE_DIGESTS.get(bundle) == _verified_bundle_content_sha256(bundle)
    if bundle.bundle_provenance == "TEST_ONLY":
        return _TEST_ONLY_BUNDLE_DIGESTS.get(bundle) == _verified_bundle_content_sha256(bundle)
    return False


def _bundle_isolation_proven(bundle: VerifiedPBundle) -> bool:
    if not _bundle_registration_is_valid(bundle):
        return False
    files = bundle.manifest.get("files")
    if not isinstance(files, list):
        return False
    forbidden = ("da01", "ground_truth", "groundtruth", "oracle", "scorer", "expected_operations")
    for row in files:
        if not isinstance(row, Mapping):
            return False
        path = str(row.get("path", "")).lower()
        role = str(row.get("role", "")).lower()
        if any(marker in path or marker in role for marker in forbidden):
            return False
    if bundle.bundle_provenance == "TEST_ONLY":
        return _TEST_ONLY_BUNDLE_DIGESTS.get(bundle) == _verified_bundle_content_sha256(bundle)
    return True


def _cost_verdict(
    plan: OperationPlan, model: Mapping[str, Any] | None, authority_verified: bool
) -> str:
    if model is None or not authority_verified:
        return "UNKNOWN"
    maximum, node_limit, costs = (
        model.get("max_incremental_cost"),
        model.get("max_search_nodes"),
        model.get("candidate_costs"),
    )
    if (
        not isinstance(maximum, int | float)
        or not isinstance(node_limit, int)
        or node_limit < 1
        or not isinstance(costs, Mapping)
    ):
        return "UNKNOWN"
    digests = {
        operation.artifact_sha256
        for operation in plan.operations
        if operation.artifact_sha256 is not None
    }
    if any(digest not in costs for digest in digests):
        return "UNKNOWN"
    try:
        total = sum(float(costs[digest]) for digest in digests)
    except (TypeError, ValueError):
        return "UNKNOWN"
    return "FAIL" if total > maximum else "PASS"


def _with_hold(plan: OperationPlan, reason: str) -> OperationPlan:
    holds = tuple(sorted(set(plan.hold_reasons) | {reason}))
    body = {
        "operations": [item.to_dict() for item in plan.operations],
        "hold_reasons": list(holds),
        "reject_reasons": list(plan.reject_reasons),
    }
    return OperationPlan(
        plan.operations, holds, plan.reject_reasons, sha256_bytes(canonical_json_bytes(body))
    )


def _bind_obligations(
    rows: Sequence[Any], ruleset: CompiledRuleset
) -> tuple[Mapping[str, Any], ...]:
    result: dict[str, Mapping[str, Any]] = {}
    criteria = {row.obligation_id: row.criterion for row in ruleset.obligations}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            raise ProtocolError("P03_OBLIGATION_ROW_INVALID")
        obligation_id = str(row["id"])
        if obligation_id in result or criteria.get(obligation_id) != row.get("criterion"):
            raise ProtocolError("P03_OBLIGATION_RULESET_BINDING_MISMATCH")
        result[obligation_id] = dict(row) | {
            "mandatory": row.get("mandatory") if isinstance(row.get("mandatory"), bool) else None
        }
    if set(result) != set(criteria):
        raise ProtocolError("P03_OBLIGATION_CATALOG_INCOMPLETE")
    return tuple(result[key] for key in sorted(result))


def _normalize_representation(row: Any) -> Mapping[str, Any]:
    try:
        return normalize_parent_representation(row)
    except ContractValidationError as error:
        raise ProtocolError("P03_REPRESENTATION_ROW_INVALID") from error


def _verified_parent_evaluator_bindings(
    bundle: VerifiedPBundle,
) -> tuple[Mapping[str, Any], ...]:
    """Return only parent bindings carried in the verified Pilot-02 profile bytes."""
    profile_bytes = bundle.artifact_bytes.get(PILOT02_PROFILE_V2_DEFINITION_PATH)
    if profile_bytes is None:
        return ()
    try:
        profile = json.loads(profile_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError("P03_PILOT02_PROFILE_DEFINITION_INVALID") from error
    bindings = profile.get("parent_evaluator_bindings") if isinstance(profile, Mapping) else None
    if not isinstance(bindings, list) or not all(isinstance(row, Mapping) for row in bindings):
        raise ContractValidationError("P03_PILOT02_PARENT_BINDINGS_INVALID")
    return tuple(dict(row) for row in bindings)


def _read_pinned_file(root: Path, relative: str, records: Mapping[str, Mapping[str, Any]]) -> bytes:
    if relative not in records or relative.startswith("/") or ".." in Path(relative).parts:
        raise ProtocolError("P03_UNPINNED_INPUT_PATH")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve(strict=True).is_relative_to(root)
    ):
        raise ProtocolError("P03_INPUT_PATH_INVALID")
    content = path.read_bytes()
    if sha256_bytes(content) != records[relative].get("sha256"):
        raise ProtocolError("P03_INPUT_DIGEST_MISMATCH")
    return content


def _decode_object(content: bytes, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError("P03_JSON_INVALID:" + label) from error
    if not isinstance(value, Mapping):
        raise ProtocolError("P03_JSON_OBJECT_REQUIRED:" + label)
    return value


def _decode_yaml_object(content: bytes, label: str) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise ProtocolError("P03_YAML_INVALID:" + label) from error
    if not isinstance(value, Mapping):
        raise ProtocolError("P03_YAML_OBJECT_REQUIRED:" + label)
    return value


def _input_status(
    validation: SnapshotValidationResult,
    provenance: str,
    trust_scope: str,
    evidence: VerifiedAdaptationEvidence | None,
) -> str:
    statuses = (
        validation.schema_status,
        validation.integrity_status,
        validation.authority_status,
        validation.fact_status,
        validation.completeness_status,
    )
    if ValidationStatus.INVALID in statuses or provenance not in {"VERIFIED_V3", "TEST_ONLY"}:
        return "INVALID"
    if ValidationStatus.UNDETERMINED in statuses:
        return "UNDETERMINED"
    if trust_scope == "TEST_ONLY" and (evidence is None or evidence.trust_scope != "TEST_ONLY"):
        return "UNDETERMINED"
    return "VALID"


def _register_test_only_bundle(
    bundle: VerifiedPBundle,
    verifier_registry: AdaptationEvidenceVerifierRegistry | None = None,
) -> VerifiedPBundle:
    """Register an isolated synthetic bundle for tests; never grants real trust."""
    if bundle.bundle_provenance != "TEST_ONLY":
        raise ContractValidationError("P03_TEST_BUNDLE_PROVENANCE_INVALID")
    object.__setattr__(bundle, "trust_scope", "TEST_ONLY")
    _TEST_ONLY_BUNDLE_DIGESTS[bundle] = _verified_bundle_content_sha256(bundle)
    if verifier_registry is not None:
        _BUNDLE_EVIDENCE_VERIFIER_REGISTRIES[bundle] = verifier_registry
    return bundle


def _validate_verified_bundle_bindings(bundle: VerifiedPBundle) -> None:
    if bundle.bundle_provenance == "VERIFIED_V3":
        verified_digest = _VERIFIED_V3_BUNDLE_DIGESTS.get(bundle)
        if verified_digest is None:
            raise ContractValidationError("P03_VERIFIED_BUNDLE_NOT_VERIFIED")
        if verified_digest != _verified_bundle_content_sha256(bundle):
            raise ContractValidationError("P03_VERIFIED_BUNDLE_CONTENT_CHANGED")
    elif bundle.bundle_provenance == "TEST_ONLY":
        registered_digest = _TEST_ONLY_BUNDLE_DIGESTS.get(bundle)
        if registered_digest is None:
            raise ContractValidationError("P03_TEST_BUNDLE_NOT_REGISTERED")
        if registered_digest != _verified_bundle_content_sha256(bundle):
            raise ContractValidationError("P03_TEST_BUNDLE_CONTENT_CHANGED")
    else:
        raise ContractValidationError("P03_BUNDLE_PROVENANCE_INVALID")
    manifest = bundle.manifest
    files_value = manifest.get("files")
    if manifest.get("method_id") != "P" or not isinstance(files_value, list):
        raise ContractValidationError("P03_INPUT_MANIFEST_INVALID")
    if any(not isinstance(row, Mapping) for row in files_value):
        raise ContractValidationError("P03_INPUT_MANIFEST_FILES_INVALID")
    files = [dict(row) for row in files_value]
    if bundle_sha256(files) != manifest.get("bundle_sha256"):
        raise ContractValidationError("P03_INPUT_BUNDLE_DIGEST_MISMATCH")
    policy_roles = {
        "policy_charter",
        "policy_registry",
        "approval_evidence",
        "completeness_evidence",
        "applicability_ruleset",
        "policy_completeness_claims",
    }
    policy_files = [row for row in files if row.get("role") in policy_roles]
    if bundle_sha256(policy_files) != manifest.get("policy_bundle_sha256"):
        raise ContractValidationError("P03_POLICY_BUNDLE_DIGEST_MISMATCH")
    if manifest.get("common_snapshot_sha256") != bundle.snapshot_validation.snapshot_digest:
        raise ContractValidationError("P03_SNAPSHOT_MANIFEST_BINDING_MISMATCH")
    if bundle.compiled_ruleset.ruleset_source_sha256 != manifest.get("policy_ruleset_sha256"):
        raise ContractValidationError("P03_RULESET_MANIFEST_BINDING_MISMATCH")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _verified_bundle_content_sha256(bundle: VerifiedPBundle) -> str:
    content = {
        item.name: _canonicalize_bundle_value(getattr(bundle, item.name)) for item in fields(bundle)
    }
    return sha256_bytes(canonical_json_bytes(content))


def _canonicalize_bundle_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return {"sha256": sha256_bytes(value), "size": len(value)}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _canonicalize_bundle_value(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        entries = [
            [_canonicalize_bundle_value(key), _canonicalize_bundle_value(item)]
            for key, item in value.items()
        ]
        return {
            "mapping_entries": sorted(entries, key=lambda entry: canonical_json_bytes(entry[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize_bundle_value(item) for item in value]
    if isinstance(value, set | frozenset):
        entries = [_canonicalize_bundle_value(item) for item in value]
        return sorted(entries, key=canonical_json_bytes)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise ContractValidationError("P03_VERIFIED_BUNDLE_VALUE_UNSUPPORTED")


def _string_set(value: Any) -> set[str]:
    return (
        {item for item in value if isinstance(item, str)}
        if isinstance(value, list | tuple)
        else set()
    )


__all__ = [
    "AdaptationResult",
    "METHOD_VERSION",
    "VerifiedPBundle",
    "run_adaptation",
    "verify_v3_p_bundle",
]
