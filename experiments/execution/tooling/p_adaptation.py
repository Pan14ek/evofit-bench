"""SPEC01 → SPEC02 → impact → candidate → governance development pipeline."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from weakref import WeakKeyDictionary

import yaml

from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.p_applicability import (
    ApplicabilityAssessment,
    CompiledRuleset,
    EvidenceLedger,
    EvidenceProof,
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
    decide_governance,
)
from experiments.execution.tooling.p_impact import (
    ChangeKind,
    ChangeRecord,
    ImpactAssessment,
    TraceGraph,
    analyze_impact,
    diff_snapshot,
    legacy_trace_graph,
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
)
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3
from experiments.execution.tooling.p_semantic import (
    CoverageAssessment,
    PairAssessment,
    assess_mandatory_coverage,
    assess_pair,
)

METHOD_VERSION = "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1"


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


_VERIFIED_V3_BUNDLE_DIGESTS: WeakKeyDictionary[VerifiedPBundle, str] = WeakKeyDictionary()


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
    graph = legacy_trace_graph(trace_doc, representations=representations, obligations=obligations)

    source_digests: dict[str, str] = {}
    for source in snapshot.get("sources", []):
        if not isinstance(source, Mapping):
            continue
        record = file_records.get(str(source.get("path")))
        if isinstance(source.get("id"), str) and isinstance(record, Mapping):
            source_digests[str(source["id"])] = str(record.get("sha256", ""))

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
    cost_model = capabilities.get("p_cost_model_v1")
    if not isinstance(cost_model, Mapping):
        cost_model = None

    # Read only files that the verified manifest declares as evidence artifacts.
    artifact_bytes = {
        path: _read_pinned_file(root, path, file_records)
        for path, row in file_records.items()
        if row.get("role") in {"evaluator_artifact", "evaluator_evidence", "evidence_artifact"}
    }
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
    )
    _VERIFIED_V3_BUNDLE_DIGESTS[bundle] = _verified_bundle_content_sha256(bundle)
    return bundle


def run_adaptation(
    bundle: VerifiedPBundle,
    *,
    evaluator_evidence: Mapping[tuple[str, str], Mapping[str, Any]] | None = None,
    pair_proofs: Mapping[tuple[str, str], EvidenceProof] | None = None,
    pair_artifact_bytes: Mapping[str, bytes] | None = None,
    fact_absence_proofs: Mapping[tuple[str, str, str], bool | None] | None = None,
    policy_inventory_complete: Mapping[str, bool | None] | None = None,
    policy_before_rows: Sequence[Mapping[str, Any]] | None = None,
    policy_after_rows: Sequence[Mapping[str, Any]] | None = None,
    required_stages: Mapping[str, Sequence[str]] | None = None,
    stage_contract_verified: bool | None = None,
    adjustment_rules: Sequence[Mapping[str, Any]] = (),
) -> AdaptationResult:
    """Run the entire fail-closed development pipeline on verified inputs."""
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
            fact_absence_proofs=fact_absence_proofs,
            policy_inventory_complete=policy_inventory_complete,
            source_digests=bundle.source_digests,
            policy_before_rows=policy_before_rows,
            policy_after_rows=policy_after_rows,
        )
    )
    changes.extend(_diff_applicability(before, after))
    applicability_after = {row.obligation_id: row.status.value for row in after.results}
    pair_evidence = evaluator_evidence or {}
    proofs = pair_proofs or {}
    checked_artifacts = {**bundle.artifact_bytes, **(pair_artifact_bytes or {})}
    pairs: list[PairAssessment] = []
    obligations_by_id = {str(row["id"]): row for row in bundle.obligations}
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
        obligations=bundle.obligations,
        pair_assessments=pairs,
        required_stages=required_stages,
        stage_contract_verified=stage_contract_verified,
    )
    mandatory = [str(row["id"]) for row in bundle.obligations if row.get("mandatory") is True]
    covered = [row.obligation_id for row in coverage.obligations if row.status == "COVERED"]
    impact = analyze_impact(
        architecture_before_sha=before.architecture_source_sha,
        architecture_after_sha=after.architecture_source_sha,
        policy_source_revision=policy_revision,
        policy_bundle_sha256=policy_digest,
        ruleset_sha256=ruleset.ruleset_source_sha256,
        snapshot_sha256=validation.snapshot_digest or "",
        changes=changes,
        graph=bundle.trace_graph,
        representation_ids=[str(row["id"]) for row in bundle.representations],
        applicability_after=applicability_after,
        mandatory_obligations=mandatory,
        covered_obligations=covered,
    )
    plan = build_operation_plan(
        representations=bundle.representations,
        obligations=bundle.obligations,
        applicability=applicability_after,
        pair_assessments=pairs,
        coverage=coverage,
        templates=bundle.templates,
        artifact_bytes=checked_artifacts,
        adjustment_rules=adjustment_rules,
        cost_model=bundle.cost_model,
    )
    cost_verdict = _cost_verdict(plan, bundle.cost_model)
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
        )
        candidate_digest = candidate_sha256(candidate)
        candidate_v1 = adapt_candidate_v1(candidate)
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
            obligations=bundle.obligations,
            pair_assessments=candidate_pairs,
            required_stages=required_stages,
            stage_contract_verified=stage_contract_verified,
        )
    decision_coverage = candidate_coverage or coverage
    decision_pairs = candidate_pairs if candidate is not None else pairs
    input_status = _input_status(validation, bundle.bundle_provenance)
    mandatory_ids = {str(row["id"]) for row in bundle.obligations if row.get("mandatory") is True}
    before_unresolved = any(
        row.obligation_id in mandatory_ids and row.status.value == "UNKNOWN"
        for row in before.results
    )
    invariants = _invariant_verdicts(
        input_status=input_status,
        coverage=decision_coverage,
        plan=plan,
        candidate=candidate,
        representations=bundle.representations,
        obligations=bundle.obligations,
        applicability=applicability_after,
        pairs=decision_pairs,
        bundle_provenance=bundle.bundle_provenance,
    )
    governance = decide_governance(
        method_version=METHOD_VERSION,
        architecture_before_sha=before.architecture_source_sha,
        architecture_after_sha=after.architecture_source_sha,
        policy_source_revision=policy_revision,
        policy_ruleset_sha256=ruleset.ruleset_source_sha256,
        input_bundle_sha256=str(manifest.get("bundle_sha256", "")),
        parent_configuration_sha256=bundle.parent_configuration_sha256,
        candidate_configuration_sha256=candidate_digest,
        impact_assessment_sha256=impact.assessment_sha256,
        coverage=decision_coverage,
        operation_plan=plan,
        invariant_verdicts=invariants,
        cost_verdict=cost_verdict,
        input_status=input_status,
        candidate_validation_status=(
            str(candidate["candidate_validation"]["status"]) if candidate else None
        ),
        pairs=[item.to_dict() for item in decision_pairs],
        evidence_refs=validation.evidence_refs,
        additional_reasons=(("BEFORE_APPLICABILITY_UNRESOLVED",) if before_unresolved else ()),
    )
    prediction_v1: Mapping[str, Any] | None = None
    if governance.result is GovernanceResult.ACCEPT and candidate is not None:
        prediction_v1 = adapt_prediction_v1(
            architecture_source_sha=after.architecture_source_sha,
            method_version=METHOD_VERSION,
            input_bundle_sha256=str(manifest["bundle_sha256"]),
            plan=plan,
            impact_records=[record.to_dict() for record in impact.representations],
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
    )


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
    representations: Sequence[Mapping[str, Any]],
    obligations: Sequence[Mapping[str, Any]],
    applicability: Mapping[str, str],
    pairs: Sequence[PairAssessment],
    bundle_provenance: str,
) -> dict[str, str]:
    pair_index = {(pair.representation_id, pair.obligation_id): pair.status.value for pair in pairs}
    unknown_ids = {
        obligation_id for obligation_id, status in applicability.items() if status == "UNKNOWN"
    }
    deactivations = [op.target_id for op in plan.operations if op.operation.value == "deactivate"]
    active_mandatory = {
        str(row["id"])
        for row in obligations
        if row.get("mandatory") is True and applicability.get(str(row["id"])) == "ACTIVE"
    }
    deactivation_safe = all(
        not (
            (unknown_ids | active_mandatory)
            & _string_set(
                next(
                    (
                        row.get("covers", [])
                        for row in representations
                        if row.get("id") == representation_id
                    ),
                    [],
                )
            )
        )
        for representation_id in deactivations
    )
    candidate_rows = (candidate or {}).get("representations", [])
    unique_ids = len({str(row.get("id")) for row in candidate_rows}) == len(candidate_rows)
    positive_retain = all(
        pair_index.get((op.target_id, obligation_id)) == "VALID"
        for op in plan.operations
        if op.operation.value == "retain"
        for representation in representations
        if representation.get("id") == op.target_id
        for obligation_id in _string_set(representation.get("covers"))
        if applicability.get(obligation_id) == "ACTIVE" and obligation_id in active_mandatory
    )
    coverage_verdict = (
        "PASS"
        if coverage.status.value == "COMPLETE"
        else "UNKNOWN"
        if coverage.status.value == "UNKNOWN"
        else "FAIL"
    )
    candidate_status = str(candidate["candidate_validation"]["status"]) if candidate else None
    input_verdict = (
        "PASS" if input_status == "VALID" else "FAIL" if input_status == "INVALID" else "UNKNOWN"
    )
    artifact_verdict = (
        "PASS"
        if candidate_status == "valid"
        else "FAIL"
        if candidate_status == "invalid"
        else "UNKNOWN"
    )
    pair_verdict = (
        "PASS"
        if positive_retain
        else "UNKNOWN"
        if any(pair.status.value == "UNKNOWN" for pair in pairs)
        else "PASS"
    )
    return {
        "INV-01": "PASS" if not plan.reject_reasons else "FAIL",
        "INV-02": "PASS" if deactivation_safe else "FAIL",
        "INV-03": "PASS" if deactivation_safe else "FAIL",
        "INV-04": coverage_verdict,
        "INV-05": input_verdict,
        "INV-06": artifact_verdict,
        "INV-07": pair_verdict,
        "INV-08": "PASS" if unique_ids and candidate is not None else "UNKNOWN",
        "INV-09": "FAIL" if plan.reject_reasons else "PASS",
        "INV-10": "PASS"
        if coverage.status.value == "COMPLETE" and candidate_status == "valid"
        else "UNKNOWN",
        "INV-11": "PASS",
        "INV-12": "PASS" if bundle_provenance == "VERIFIED_V3" else "UNKNOWN",
    }


def _cost_verdict(plan: OperationPlan, model: Mapping[str, Any] | None) -> str:
    if model is None or model.get("authority_status") not in {"VERIFIED", "TEST_ONLY"}:
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


def _input_status(validation: SnapshotValidationResult, provenance: str) -> str:
    statuses = (
        validation.schema_status,
        validation.integrity_status,
        validation.authority_status,
        validation.fact_status,
        validation.completeness_status,
    )
    if ValidationStatus.INVALID in statuses or provenance not in {"VERIFIED_V3", "TEST_ONLY"}:
        return "INVALID"
    if provenance == "TEST_ONLY" or ValidationStatus.UNDETERMINED in statuses:
        return "UNDETERMINED"
    return "VALID"


def _validate_verified_bundle_bindings(bundle: VerifiedPBundle) -> None:
    if bundle.bundle_provenance == "VERIFIED_V3":
        verified_digest = _VERIFIED_V3_BUNDLE_DIGESTS.get(bundle)
        if verified_digest is None:
            raise ContractValidationError("P03_VERIFIED_BUNDLE_NOT_VERIFIED")
        if verified_digest != _verified_bundle_content_sha256(bundle):
            raise ContractValidationError("P03_VERIFIED_BUNDLE_CONTENT_CHANGED")
    elif bundle.bundle_provenance != "TEST_ONLY":
        raise ContractValidationError("P03_BUNDLE_PROVENANCE_INVALID")
    manifest = bundle.manifest
    files = manifest.get("files")
    if manifest.get("method_id") != "P" or not isinstance(files, list):
        raise ContractValidationError("P03_INPUT_MANIFEST_INVALID")
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
    policy_files = [
        row for row in files if isinstance(row, Mapping) and row.get("role") in policy_roles
    ]
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
