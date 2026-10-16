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


def pair_with_status(pair: PairAssessment, status: PairStatus) -> PairAssessment:
    """Change only the synthetic test assessment status, preserving its identity."""
    return replace(pair, status=status)
