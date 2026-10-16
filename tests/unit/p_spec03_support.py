"""Independent generic TEST_ONLY fixtures and builders for SPEC 03 tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_applicability import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    EvidenceProof,
    ObligationResult,
    ProofStatus,
)
from experiments.execution.tooling.p_impact import (
    ImpactAssessment,
    ImpactRecord,
    ImpactStatus,
    analyze_impact,
    parse_trace_graph,
)
from experiments.execution.tooling.p_semantic import (
    CoverageAssessment,
    PairAssessment,
    PairStatus,
    assess_mandatory_coverage,
    assess_pair,
    pair_proof_subject,
)

FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures/p_method/generic_architecture_evolution_v1.json"
)
ARCH_BEFORE = "1111111111111111111111111111111111111111"
ARCH_AFTER = "2222222222222222222222222222222222222222"
SYN_SOURCE_SHA = "6666666666666666666666666666666666666666666666666666666666666666"
SYN_ARTIFACT = b"# TEST_ONLY generic checker artifact\nprint('synthetic check')\n"
SYN_EVIDENCE = b"TEST_ONLY evidence bytes\n"


def load_synthetic_fixture() -> dict[str, Any]:
    """Read the independently authored, non-DA01 scenario fixture."""
    return cast(dict[str, Any], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


def sha256_fixture() -> str:
    return sha256_bytes(FIXTURE_PATH.read_bytes())


def make_representation(**changes: Any) -> dict[str, Any]:
    fixture = load_synthetic_fixture()
    row = dict(fixture["representation"])
    row.update(changes)
    row["evaluator_artifact"] = dict(row["evaluator_artifact"])
    row["evaluator_artifact"]["sha256"] = sha256_bytes(SYN_ARTIFACT)
    return row


def make_obligation(**changes: Any) -> dict[str, Any]:
    row = dict(load_synthetic_fixture()["obligations"][0])
    row.update(changes)
    return row


def make_evaluator_evidence(
    representation: dict[str, Any] | None = None,
    *,
    obligation_id: str = "SYN_OBL_TRACE",
    architecture_source_sha: str = ARCH_AFTER,
    process_exit_code: int | None = 0,
    configured_targets: list[str] | None = None,
    resolved_targets: list[str] | None = None,
    inspected_subjects: list[str] | None = None,
    evidence_artifact_bytes: bytes = SYN_EVIDENCE,
    **changes: Any,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    rep = representation or make_representation()
    path = "evidence/synthetic-trace.json"
    evidence = {
        "schema_version": 1,
        "representation_id": rep["id"],
        "architecture_source_sha": architecture_source_sha,
        "evaluator_id": rep["evaluator"],
        "infrastructure_status": "completed"
        if process_exit_code is not None
        else "infrastructure_failure",
        "process_exit_code": process_exit_code,
        "configured_targets": configured_targets
        if configured_targets is not None
        else [obligation_id],
        "resolved_targets": resolved_targets if resolved_targets is not None else [obligation_id],
        "inspected_subjects": inspected_subjects
        if inspected_subjects is not None
        else ["synthetic_component_alpha"],
        "missing_targets": [],
        "inspected_edge_count": 1,
        "stage_applicable": True,
        "semantic_compatible": True,
        "mapping_resolved": True,
        "evidence_contract_satisfied": True,
        "adequacy_proven": True,
        "evidence_artifacts": [{"path": path, "sha256": sha256_bytes(evidence_artifact_bytes)}],
        "stdout_sha256": sha256_bytes(b"synthetic stdout"),
        "stderr_sha256": sha256_bytes(b""),
        "failure_reason_code": None,
    }
    evidence.update(changes)
    return evidence, {
        rep["evaluator_artifact"]["path"]: SYN_ARTIFACT,
        path: evidence_artifact_bytes,
    }


def make_valid_pair(
    *,
    representation: dict[str, Any] | None = None,
    obligation: dict[str, Any] | None = None,
    architecture_source_sha: str = ARCH_AFTER,
    process_exit_code: int | None = 0,
    evidence_changes: dict[str, Any] | None = None,
    proof_status: ProofStatus = ProofStatus.VALID,
    source_digests: dict[str, str] | None = None,
) -> tuple[PairAssessment, dict[str, Any], dict[str, Any], dict[str, bytes], EvidenceProof]:
    rep = representation or make_representation()
    q = obligation or make_obligation()
    evidence_options: dict[str, Any] = {
        "architecture_source_sha": architecture_source_sha,
        "process_exit_code": process_exit_code,
        **(evidence_changes or {}),
    }
    evidence, artifacts = make_evaluator_evidence(
        rep, obligation_id=str(q["id"]), **evidence_options
    )
    source_map = source_digests or {"SYN_SOURCE_FACT": SYN_SOURCE_SHA}
    bindings = tuple(sorted(source_map.items()))
    proof = EvidenceProof(
        proof_status,
        sha256_bytes(
            canonical_json_bytes(pair_proof_subject(rep, q, architecture_source_sha, evidence))
        ),
        bindings,
        "synthetic_pair_semantics_v1",
        ("SYN_PAIR_PROOF",),
        () if proof_status is ProofStatus.VALID else ("PAIR_SEMANTIC_PROOF_UNRESOLVED",),
    )
    assessment = assess_pair(
        representation=rep,
        obligation=q,
        architecture_source_sha=architecture_source_sha,
        evaluator_evidence=evidence,
        semantic_proof=proof,
        artifact_bytes=artifacts,
        source_digests=source_map,
    )
    return assessment, rep, q, artifacts, proof


def make_applicability(
    statuses: dict[str, ApplicabilityStatus] | None = None,
    *,
    architecture_source_sha: str = ARCH_AFTER,
) -> ApplicabilityAssessment:
    chosen = statuses or {"SYN_OBL_TRACE": ApplicabilityStatus.ACTIVE}
    results = tuple(
        ObligationResult(
            obligation_id,
            status,
            ("SYNTHETIC_TEST_STATUS",),
            (),
            (),
            ("SYN_POLICY_SOURCE",),
            (),
        )
        for obligation_id, status in sorted(chosen.items())
    )
    return ApplicabilityAssessment(
        "SYN_RULESET_V1",
        "FV_CORE_V1",
        "SYN_REGISTRY_V1",
        "SYN_POLICY_REV_1",
        "2026-01-01T00:00:00Z",
        architecture_source_sha,
        "after",
        "8" * 64,
        "5" * 64,
        "4" * 64,
        {
            "schema_status": "VALID",
            "integrity_status": "VALID",
            "authority_status": "VALID",
            "fact_status": "VALID",
            "completeness_status": "VALID",
            "reason_codes": [],
        },
        results,
    )


def make_coverage(
    obligations: list[dict[str, Any]] | None = None,
    *,
    statuses: dict[str, ApplicabilityStatus] | None = None,
    pairs: list[PairAssessment] | None = None,
) -> CoverageAssessment:
    rows = obligations or [make_obligation()]
    applicability = make_applicability(
        statuses or {str(row["id"]): ApplicabilityStatus.ACTIVE for row in rows}
    )
    return assess_mandatory_coverage(
        applicability=applicability,
        obligations=rows,
        pair_assessments=pairs or [],
    )


def make_impact_assessment(
    representations: list[dict[str, Any]],
    obligations: list[dict[str, Any]],
    applicability: dict[str, str] | None = None,
) -> ImpactAssessment:
    """Build an independently declared, complete synthetic no-change analysis."""
    fixture = load_synthetic_fixture()
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for obligation in obligations:
        obligation_id, criterion_id = str(obligation["id"]), str(obligation["criterion"])
        nodes[obligation_id] = {
            "id": obligation_id,
            "kind": "obligation",
            "scope": "service:synth",
            "version": "catalog:1",
            "source_refs": ["SYN_SOURCE_CATALOG"],
        }
        nodes.setdefault(
            criterion_id,
            {
                "id": criterion_id,
                "kind": "criterion",
                "scope": "service:synth",
                "version": "criterion:1",
                "source_refs": ["SYN_SOURCE_CATALOG"],
            },
        )
        edges.append(
            {
                "source_id": obligation_id,
                "target_id": criterion_id,
                "kind": "obligation_to_criterion",
                "source_refs": ["SYN_SOURCE_CATALOG"],
                "scope": "service:synth",
                "source_version": "catalog:1",
                "target_version": "criterion:1",
            }
        )
    for representation in representations:
        representation_id = str(representation["id"])
        criterion_id = str(representation["criterion"])
        evaluator_id = "SYN_EVALUATOR_" + representation_id
        nodes[representation_id] = {
            "id": representation_id,
            "kind": "representation",
            "scope": "service:synth",
            "version": "configuration:1",
            "source_refs": ["SYN_SOURCE_CONFIG"],
        }
        nodes[evaluator_id] = {
            "id": evaluator_id,
            "kind": "evaluator",
            "scope": "service:synth",
            "version": "artifact:1",
            "source_refs": ["SYN_SOURCE_ARTIFACT"],
        }
        edges.append(
            {
                "source_id": criterion_id,
                "target_id": representation_id,
                "kind": "criterion_to_representation",
                "source_refs": ["SYN_SOURCE_CATALOG", "SYN_SOURCE_CONFIG"],
                "scope": "service:synth",
                "source_version": "criterion:1",
                "target_version": "configuration:1",
            }
        )
        edges.append(
            {
                "source_id": representation_id,
                "target_id": evaluator_id,
                "kind": "representation_to_evaluator",
                "source_refs": ["SYN_SOURCE_CONFIG", "SYN_SOURCE_ARTIFACT"],
                "scope": "service:synth",
                "source_version": "configuration:1",
                "target_version": "artifact:1",
            }
        )
    graph = parse_trace_graph(
        {
            "schema_version": 1,
            "inventory_complete": True,
            "nodes": list(nodes.values()),
            "edges": edges,
        }
    )
    graph = replace(graph, inventory_complete_verified=True)
    statuses = applicability or {str(row["id"]): "ACTIVE" for row in obligations}
    mandatory = [str(row["id"]) for row in obligations if row.get("mandatory") is True]
    return analyze_impact(
        architecture_before_sha=fixture["architecture_before_sha"],
        architecture_after_sha=fixture["architecture_after_sha"],
        policy_source_revision=fixture["policy_source_revision"],
        policy_bundle_sha256=fixture["policy_bundle_sha256"],
        ruleset_sha256=fixture["ruleset_sha256"],
        snapshot_sha256=fixture["snapshot_sha256"],
        changes=(),
        graph=graph,
        source_digests={
            source_id: fixture["source_sha256"]
            for source_id in (
                "SYN_SOURCE_CATALOG",
                "SYN_SOURCE_CONFIG",
                "SYN_SOURCE_ARTIFACT",
            )
        },
        expected_scope="service:synth",
        representation_ids=[str(row["id"]) for row in representations],
        applicability_after=statuses,
        mandatory_obligations=mandatory,
        covered_obligations=mandatory,
        change_inventory_verified=True,
    )


def impact_with_status(assessment: ImpactAssessment, status: ImpactStatus) -> ImpactAssessment:
    """Return a digest-consistent synthetic impact outcome for planner tests."""
    records = tuple(
        ImpactRecord(
            record.representation_id,
            status,
            ((record.representation_id,),) if status is ImpactStatus.PROVEN_AFFECTED else (),
            ("SYNTHETIC_TEST_IMPACT",),
            ("SYN_SOURCE_FACT",) if status is ImpactStatus.PROVEN_AFFECTED else (),
        )
        for record in assessment.representations
    )
    updated = replace(assessment, representations=records, assessment_sha256="")
    content = updated.to_dict()
    content.pop("assessment_sha256")
    return replace(
        updated,
        assessment_sha256=sha256_bytes(canonical_json_bytes(content)),
    )


def pair_with_status(pair: PairAssessment, status: PairStatus) -> PairAssessment:
    """Build a digest-consistent synthetic pair assessment with a chosen status."""
    reasons = set(pair.reason_codes)
    if status is PairStatus.INVALID:
        reasons.add("SYNTHETIC_PAIR_INVALID")
    payload = pair.to_dict()
    payload["status"] = status.value
    payload["reason_codes"] = sorted(reasons)
    if status is PairStatus.INVALID:
        payload["semantic_proof_status"] = "INVALID"
    payload.pop("assessment_sha256")
    return replace(
        pair,
        status=status,
        semantic_proof_status=(
            "INVALID" if status is PairStatus.INVALID else pair.semantic_proof_status
        ),
        reason_codes=tuple(sorted(reasons)),
        assessment_sha256=sha256_bytes(canonical_json_bytes(payload)),
    )
