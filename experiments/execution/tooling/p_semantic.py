"""Method-side semantic validity and mandatory pair coverage assessments."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_applicability import (
    ApplicabilityAssessment,
    EvidenceProof,
    ProofStatus,
)

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_SAFE_PATH = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9_./-]+$")


class PairStatus(StrEnum):
    """Evidence-aware method-side conclusion for one exact (r,q) pair."""

    VALID = "VALID"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class ComplianceStatus(StrEnum):
    """Observed architecture compliance, separate from monitor adequacy."""

    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNKNOWN = "UNKNOWN"


class CoverageStatus(StrEnum):
    """Whole mandatory-coverage state for an architecture revision."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PairAssessment:
    """Pair-specific validity, observed compliance and bound evidence."""

    representation_id: str
    obligation_id: str
    architecture_source_sha: str
    criterion_id: str
    stage: str | None
    status: PairStatus
    compliance_status: ComplianceStatus
    evaluator_evidence_sha256: str | None
    evaluator_artifact_sha256: str | None
    semantic_proof_status: str
    semantic_verifier_id: str | None
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    evidence_artifacts: tuple[Mapping[str, str], ...]
    assessment_sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Return a strict-schema compatible diagnostic record."""
        return {
            "schema_version": 1,
            "representation_id": self.representation_id,
            "obligation_id": self.obligation_id,
            "architecture_source_sha": self.architecture_source_sha,
            "criterion_id": self.criterion_id,
            "stage": self.stage,
            "status": self.status.value,
            "compliance_status": self.compliance_status.value,
            "evaluator_evidence_sha256": self.evaluator_evidence_sha256,
            "evaluator_artifact_sha256": self.evaluator_artifact_sha256,
            "semantic_proof_status": self.semantic_proof_status,
            "semantic_verifier_id": self.semantic_verifier_id,
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
            "evidence_artifacts": [dict(item) for item in self.evidence_artifacts],
            "assessment_sha256": self.assessment_sha256,
        }


@dataclass(frozen=True)
class ObligationCoverage:
    """One deduplicated mandatory coverage result per obligation."""

    obligation_id: str
    applicability_status: str
    mandatory: bool | None
    status: str
    required_stages: tuple[str, ...]
    covered_stages: tuple[str, ...]
    valid_pair_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "applicability_status": self.applicability_status,
            "mandatory": self.mandatory,
            "status": self.status,
            "required_stages": list(self.required_stages),
            "covered_stages": list(self.covered_stages),
            "valid_pair_ids": list(self.valid_pair_ids),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class CoverageAssessment:
    """Mandatory coverage summary with complete per-obligation accounting."""

    architecture_source_sha: str
    applicability_assessment_sha256: str
    policy_source_revision: str
    policy_bundle_sha256: str | None
    ruleset_sha256: str
    status: CoverageStatus
    mandatory_total: int
    mandatory_covered: int
    obligations: tuple[ObligationCoverage, ...]
    reason_codes: tuple[str, ...]
    assessment_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "architecture_source_sha": self.architecture_source_sha,
            "applicability_assessment_sha256": self.applicability_assessment_sha256,
            "policy_source_revision": self.policy_source_revision,
            "policy_bundle_sha256": self.policy_bundle_sha256,
            "ruleset_sha256": self.ruleset_sha256,
            "status": self.status.value,
            "mandatory_total": self.mandatory_total,
            "mandatory_covered": self.mandatory_covered,
            "obligations": [item.to_dict() for item in self.obligations],
            "reason_codes": list(self.reason_codes),
            "assessment_sha256": self.assessment_sha256,
        }


def pair_proof_subject(
    representation: Mapping[str, Any],
    obligation: Mapping[str, Any],
    architecture_source_sha: str,
    evaluator_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the canonical exact-pair subject external semantic proof must bind."""
    artifact = representation.get("evaluator_artifact")
    artifact_sha = artifact.get("sha256") if isinstance(artifact, Mapping) else None
    scope = representation.get("applicability_scope")
    return {
        "representation_id": representation.get("id"),
        "obligation_id": obligation.get("id"),
        "criterion_id": representation.get("criterion"),
        "obligation_criterion_id": obligation.get("criterion"),
        "architecture_source_sha": architecture_source_sha,
        "stage": representation.get("stage"),
        "scope": dict(scope) if isinstance(scope, Mapping) else None,
        "evaluator_id": representation.get("evaluator"),
        "evaluator_artifact_sha256": artifact_sha,
        "evidence_contract_sha256": _digest_value(representation.get("evidence_contract")),
        "evaluator_evidence_sha256": sha256_bytes(canonical_json_bytes(dict(evaluator_evidence))),
    }


def assess_pair(
    *,
    representation: Mapping[str, Any],
    obligation: Mapping[str, Any],
    architecture_source_sha: str,
    evaluator_evidence: Mapping[str, Any] | None,
    semantic_proof: EvidenceProof | None,
    artifact_bytes: Mapping[str, bytes],
    source_digests: Mapping[str, str],
) -> PairAssessment:
    """Assess one pair; `covers` and evaluator exit success are never sufficient.

    Artifact bytes are supplied from the allowlisted, hash-verified input set.
    A valid pair also needs an exact-pair SPEC 02-style externally verified proof.
    """
    representation_id = _required_id(representation.get("id"), "representation_id")
    obligation_id = _required_id(obligation.get("id"), "obligation_id")
    criterion_id = _required_id(representation.get("criterion"), "criterion_id")
    stage = representation.get("stage") if isinstance(representation.get("stage"), str) else None
    reasons: set[str] = set()
    evidence_refs: set[str] = set()
    artifacts: tuple[Mapping[str, str], ...] = ()
    compliance = ComplianceStatus.UNKNOWN
    evidence_digest: str | None = None
    evaluator_artifact_sha: str | None = None

    if not _is_sha1(architecture_source_sha):
        raise ContractValidationError("P03_PAIR_ARCHITECTURE_SHA_INVALID")
    if evaluator_evidence is None:
        reasons.add("PAIR_EVIDENCE_MISSING")
        return _pair_result(
            representation_id,
            obligation_id,
            architecture_source_sha,
            criterion_id,
            stage,
            PairStatus.UNKNOWN,
            compliance,
            None,
            None,
            semantic_proof,
            reasons,
            evidence_refs,
            artifacts,
        )
    try:
        validate_payload("evaluator_evidence.schema.json", dict(evaluator_evidence))
    except ContractValidationError:
        reasons.add("EVALUATOR_EVIDENCE_SCHEMA_INVALID")
        return _pair_result(
            representation_id,
            obligation_id,
            architecture_source_sha,
            criterion_id,
            stage,
            PairStatus.INVALID,
            compliance,
            None,
            None,
            semantic_proof,
            reasons,
            evidence_refs,
            artifacts,
        )

    evidence_digest = sha256_bytes(canonical_json_bytes(dict(evaluator_evidence)))
    if evaluator_evidence.get("representation_id") != representation_id:
        reasons.add("REPRESENTATION_ID_MISMATCH")
    if evaluator_evidence.get("architecture_source_sha") != architecture_source_sha:
        reasons.add("ARCHITECTURE_REVISION_MISMATCH")
    if evaluator_evidence.get("evaluator_id") != representation.get("evaluator"):
        reasons.add("EVALUATOR_ID_MISMATCH")
    if obligation_id not in _string_set(representation.get("covers", [])):
        reasons.add("OBLIGATION_MAPPING_MISSING")
    if not criterion_id or obligation.get("criterion") != criterion_id:
        reasons.add("CRITERION_INTENT_MAPPING_MISMATCH")

    artifact = representation.get("evaluator_artifact")
    if not isinstance(artifact, Mapping):
        reasons.add("EVALUATOR_ARTIFACT_UNAVAILABLE")
    else:
        artifact_path = artifact.get("path")
        declared_artifact_sha = artifact.get("sha256")
        evaluator_artifact_sha = (
            declared_artifact_sha if _is_sha256(declared_artifact_sha) else None
        )
        if not isinstance(artifact_path, str) or _SAFE_PATH.fullmatch(artifact_path) is None:
            reasons.add("EVALUATOR_ARTIFACT_PATH_INVALID")
        elif not _is_sha256(evaluator_artifact_sha):
            reasons.add("EVALUATOR_ARTIFACT_DIGEST_INVALID")
        else:
            content = artifact_bytes.get(artifact_path)
            if content is None:
                reasons.add("EVALUATOR_ARTIFACT_BYTES_MISSING")
            elif sha256_bytes(content) != evaluator_artifact_sha:
                reasons.add("EVALUATOR_ARTIFACT_DIGEST_MISMATCH")

    evidence_artifacts = evaluator_evidence.get("evidence_artifacts", [])
    checked_artifacts: list[Mapping[str, str]] = []
    if isinstance(evidence_artifacts, list):
        for item in evidence_artifacts:
            if not isinstance(item, Mapping):
                reasons.add("EVIDENCE_ARTIFACT_INVALID")
                continue
            path, digest = item.get("path"), item.get("sha256")
            if (
                not isinstance(path, str)
                or _SAFE_PATH.fullmatch(path) is None
                or not _is_sha256(digest)
            ):
                reasons.add("EVIDENCE_ARTIFACT_REFERENCE_INVALID")
                continue
            content = artifact_bytes.get(path)
            if content is None:
                reasons.add("EVIDENCE_ARTIFACT_BYTES_MISSING")
            elif sha256_bytes(content) != digest:
                reasons.add("EVIDENCE_ARTIFACT_DIGEST_MISMATCH")
            else:
                checked_artifacts.append({"path": path, "sha256": digest})
                evidence_refs.add(path)
    artifacts = tuple(sorted(checked_artifacts, key=lambda item: (item["path"], item["sha256"])))

    infrastructure = evaluator_evidence.get("infrastructure_status")
    configured = _string_set(evaluator_evidence.get("configured_targets", []))
    resolved = _string_set(evaluator_evidence.get("resolved_targets", []))
    inspected = _string_set(evaluator_evidence.get("inspected_subjects", []))
    missing = _string_set(evaluator_evidence.get("missing_targets", []))
    inspection_scope_unknown = _inspection_scope_unresolved(
        evaluator_evidence, artifacts, artifact_bytes
    )
    if inspection_scope_unknown:
        reasons.add("EVALUATOR_INSPECTION_SCOPE_UNKNOWN")
    if (
        infrastructure == "infrastructure_failure"
        or evaluator_evidence.get("process_exit_code") is None
    ):
        reasons.add("EVALUATOR_EXECUTION_UNRESOLVED")
    elif infrastructure != "completed":
        reasons.add("EVALUATOR_NOT_RUN")
    elif not configured or not resolved or not inspected:
        if not inspection_scope_unknown:
            reasons.add("VACUOUS_SUCCESS")
    elif not resolved.issubset(configured) or missing:
        reasons.add("EVALUATOR_TARGET_RESOLUTION_MISMATCH")
    elif evaluator_evidence.get("stage_applicable") is False:
        reasons.add("STAGE_OR_CONTEXT_MISMATCH")
    elif evaluator_evidence.get("mapping_resolved") is False:
        reasons.add("OBLIGATION_MAPPING_MISMATCH")
    elif evaluator_evidence.get("evidence_contract_satisfied") is False:
        reasons.add("EVIDENCE_CONTRACT_INADEQUATE")
    elif evaluator_evidence.get("adequacy_proven") is False:
        reasons.add("EVALUATOR_ADEQUACY_NOT_PROVEN")
    elif evaluator_evidence.get("semantic_compatible") is False:
        reasons.add("SEMANTIC_MISMATCH")
    elif evaluator_evidence.get("semantic_compatible") is None:
        reasons.add("SEMANTIC_COMPATIBILITY_UNKNOWN")
    elif not artifacts:
        reasons.add("EVIDENCE_ARTIFACTS_UNVERIFIED")

    exit_code = evaluator_evidence.get("process_exit_code")
    compliance_blockers = {
        "REPRESENTATION_ID_MISMATCH",
        "ARCHITECTURE_REVISION_MISMATCH",
        "EVALUATOR_ID_MISMATCH",
        "OBLIGATION_MAPPING_MISSING",
        "CRITERION_INTENT_MAPPING_MISMATCH",
        "EVALUATOR_ARTIFACT_UNAVAILABLE",
        "EVALUATOR_ARTIFACT_PATH_INVALID",
        "EVALUATOR_ARTIFACT_DIGEST_INVALID",
        "EVALUATOR_ARTIFACT_BYTES_MISSING",
        "EVALUATOR_ARTIFACT_DIGEST_MISMATCH",
        "EVIDENCE_ARTIFACT_BYTES_MISSING",
        "EVIDENCE_ARTIFACT_DIGEST_MISMATCH",
        "EVIDENCE_ARTIFACT_REFERENCE_INVALID",
        "EVALUATOR_INSPECTION_SCOPE_UNKNOWN",
        "EVALUATOR_EXECUTION_UNRESOLVED",
        "EVALUATOR_NOT_RUN",
        "VACUOUS_SUCCESS",
        "EVALUATOR_TARGET_RESOLUTION_MISMATCH",
        "STAGE_OR_CONTEXT_MISMATCH",
        "OBLIGATION_MAPPING_MISMATCH",
        "EVIDENCE_ARTIFACTS_UNVERIFIED",
    }
    if infrastructure == "completed" and isinstance(exit_code, int):
        if reasons & compliance_blockers:
            reasons.add("COMPLIANCE_RESULT_UNDETERMINED")
        elif exit_code != 0:
            compliance = ComplianceStatus.NON_COMPLIANT
            reasons.add("COMPLIANCE_VIOLATION_OBSERVED")
        else:
            compliance = ComplianceStatus.COMPLIANT

    proof_status = "UNDETERMINED"
    proof = semantic_proof
    if proof is None:
        reasons.add("PAIR_SEMANTIC_PROOF_MISSING")
    else:
        expected_subject = pair_proof_subject(
            representation, obligation, architecture_source_sha, evaluator_evidence
        )
        if proof.subject_sha256 != sha256_bytes(canonical_json_bytes(expected_subject)):
            reasons.add("PAIR_SEMANTIC_PROOF_SUBJECT_MISMATCH")
        expected_sources = tuple(
            sorted(
                (source_id, source_digests[source_id])
                for source_id, _ in proof.source_bindings
                if source_id in source_digests
            )
        )
        if not proof.source_bindings or expected_sources != proof.source_bindings:
            reasons.add("PAIR_SEMANTIC_PROOF_SOURCE_MISMATCH")
        if not proof.evidence_refs:
            reasons.add("PAIR_SEMANTIC_PROOF_EVIDENCE_MISSING")
        proof_status = proof.status.value
        if proof.status is ProofStatus.INVALID:
            reasons.update(
                _normalized_proof_reasons(proof.reason_codes, "PAIR_SEMANTIC_MISMATCH_PROVEN")
            )
        elif proof.status is ProofStatus.UNDETERMINED:
            reasons.update(
                _normalized_proof_reasons(proof.reason_codes, "PAIR_SEMANTIC_PROOF_UNRESOLVED")
            )
        else:
            evidence_refs.update(proof.evidence_refs)

    hard_mismatches = {
        "REPRESENTATION_ID_MISMATCH",
        "ARCHITECTURE_REVISION_MISMATCH",
        "EVALUATOR_ID_MISMATCH",
        "OBLIGATION_MAPPING_MISSING",
        "CRITERION_INTENT_MAPPING_MISMATCH",
        "EVALUATOR_ARTIFACT_DIGEST_MISMATCH",
        "EVALUATOR_ARTIFACT_PATH_INVALID",
        "EVALUATOR_ARTIFACT_DIGEST_INVALID",
        "EVIDENCE_ARTIFACT_DIGEST_MISMATCH",
        "EVIDENCE_ARTIFACT_REFERENCE_INVALID",
        "VACUOUS_SUCCESS",
        "EVALUATOR_TARGET_RESOLUTION_MISMATCH",
        "STAGE_OR_CONTEXT_MISMATCH",
        "OBLIGATION_MAPPING_MISMATCH",
        "EVIDENCE_CONTRACT_INADEQUATE",
        "SEMANTIC_MISMATCH",
        "PAIR_SEMANTIC_PROOF_SUBJECT_MISMATCH",
        "PAIR_SEMANTIC_PROOF_SOURCE_MISMATCH",
    }
    unresolved_compliance_only = reasons <= {"COMPLIANCE_VIOLATION_OBSERVED"}
    if reasons & hard_mismatches or proof is not None and proof.status is ProofStatus.INVALID:
        status = PairStatus.INVALID
    elif (
        (reasons and not unresolved_compliance_only)
        or proof is None
        or proof.status is not ProofStatus.VALID
    ):
        status = PairStatus.UNKNOWN
    else:
        status = PairStatus.VALID
    return _pair_result(
        representation_id,
        obligation_id,
        architecture_source_sha,
        criterion_id,
        stage,
        status,
        compliance,
        evidence_digest,
        evaluator_artifact_sha,
        proof,
        reasons,
        evidence_refs,
        artifacts,
        proof_status=proof_status,
    )


def assess_mandatory_coverage(
    *,
    applicability: ApplicabilityAssessment,
    obligations: Sequence[Mapping[str, Any]],
    pair_assessments: Sequence[PairAssessment],
    required_stages: Mapping[str, Sequence[str]] | None = None,
    stage_contract_verified: bool | None = None,
) -> CoverageAssessment:
    """Assess all mandatory active obligations once, without aggregate scores."""
    applicability_rows = {item.obligation_id: item.status.value for item in applicability.results}
    if len(applicability_rows) != len(applicability.results):
        raise ContractValidationError("P03_APPLICABILITY_DUPLICATE_OBLIGATION")
    pair_index: dict[str, dict[str, list[PairAssessment]]] = defaultdict(lambda: defaultdict(list))
    stale_pair_obligations: set[str] = set()
    invalid_pair_obligations: set[str] = set()
    invalid_pair_representations: dict[str, set[str]] = defaultdict(set)
    for pair in pair_assessments:
        if pair.architecture_source_sha != applicability.architecture_source_sha:
            stale_pair_obligations.add(pair.obligation_id)
            continue
        if not _pair_assessment_digest_is_valid(pair):
            invalid_pair_obligations.add(pair.obligation_id)
            invalid_pair_representations[pair.obligation_id].add(pair.representation_id)
            continue
        pair_index[pair.obligation_id][pair.representation_id].append(pair)
    stage_map = required_stages or {}
    records: list[ObligationCoverage] = []
    reasons: set[str] = set()
    active_mandatory_count = 0
    covered_count = 0
    unknown_any = False
    for obligation in sorted(obligations, key=lambda item: str(item.get("id", ""))):
        obligation_id = _required_id(obligation.get("id"), "obligation_id")
        applicability_status = applicability_rows.get(obligation_id)
        mandatory_value = obligation.get("mandatory")
        mandatory = mandatory_value if isinstance(mandatory_value, bool) else None
        row_reasons: set[str] = set()
        required: tuple[str, ...] = ()
        covered: tuple[str, ...] = ()
        valid_ids: tuple[str, ...] = ()
        if applicability_status is None:
            applicability_status = "UNKNOWN"
            row_reasons.add("APPLICABILITY_RESULT_MISSING")
        if mandatory is None:
            row_reasons.add("MANDATORY_CLASSIFICATION_UNRESOLVED")
        if applicability_status == "UNKNOWN":
            row_reasons.add("APPLICABILITY_UNKNOWN")
        if applicability_status == "UNKNOWN":
            status = "UNKNOWN"
            unknown_any = True
            required = tuple(sorted(set(stage_map.get(obligation_id, ()))))
            covered = ()
            valid_ids = ()
        elif applicability_status == "INACTIVE" and mandatory is not None:
            status = "NOT_REQUIRED"
            required = ()
            covered = ()
            valid_ids = ()
        elif mandatory is False:
            status = "NOT_REQUIRED"
            required = ()
            covered = ()
            valid_ids = ()
        elif applicability_status != "ACTIVE" or mandatory is None:
            status = "UNKNOWN"
            unknown_any = True
            required = tuple(sorted(set(stage_map.get(obligation_id, ()))))
            covered = ()
            valid_ids = ()
        else:
            active_mandatory_count += 1
            required = tuple(sorted(set(stage_map.get(obligation_id, ()))))
            current_pairs: list[PairAssessment] = []
            conflicting_pair = False
            for representation_pairs in pair_index.get(obligation_id, {}).values():
                pair_statuses = {pair.status for pair in representation_pairs}
                assessment_digests = {pair.assessment_sha256 for pair in representation_pairs}
                if (
                    len(pair_statuses) > 1
                    or len(assessment_digests) > 1
                    or representation_pairs[0].representation_id
                    in invalid_pair_representations.get(obligation_id, set())
                ):
                    conflicting_pair = True
                    continue
                current_pairs.extend(representation_pairs)
            stale_pair = obligation_id in stale_pair_obligations
            invalid_pair = obligation_id in invalid_pair_obligations
            if stale_pair:
                row_reasons.add("PAIR_ARCHITECTURE_REVISION_MISMATCH")
            if invalid_pair:
                row_reasons.add("PAIR_ASSESSMENT_DIGEST_MISMATCH")
            if conflicting_pair:
                row_reasons.add("PAIR_ASSESSMENT_CONFLICT")
            unresolved_pair = (
                stale_pair
                or invalid_pair
                or conflicting_pair
                or any(pair.status is PairStatus.UNKNOWN for pair in current_pairs)
            )
            if required and stage_contract_verified is not True:
                status = "UNKNOWN"
                row_reasons.add("STAGE_CONTRACT_UNVERIFIED")
                unknown_any = True
                covered = ()
                valid_ids = ()
            else:
                valid_pairs = [pair for pair in current_pairs if pair.status is PairStatus.VALID]
                valid_stages = {pair.stage for pair in valid_pairs if pair.stage is not None}
                if required:
                    missing_stages = sorted(set(required) - valid_stages)
                    covered = tuple(stage for stage in required if stage in valid_stages)
                    if not missing_stages:
                        status = "COVERED"
                    elif unresolved_pair:
                        status = "UNKNOWN"
                        if not stale_pair and not invalid_pair and not conflicting_pair:
                            row_reasons.add("REQUIRED_STAGE_EVIDENCE_UNKNOWN")
                        unknown_any = True
                    else:
                        status = "NOT_DEMONSTRATED"
                        row_reasons.add("REQUIRED_STAGE_NOT_COVERED")
                else:
                    covered = tuple(sorted(valid_stages))
                    if valid_pairs:
                        status = "COVERED"
                    elif unresolved_pair:
                        status = "UNKNOWN"
                        if not stale_pair and not invalid_pair and not conflicting_pair:
                            row_reasons.add("PAIR_VALIDITY_UNKNOWN")
                        unknown_any = True
                    else:
                        status = "NOT_DEMONSTRATED"
                        row_reasons.add("NO_VALID_PAIR")
                valid_ids = tuple(sorted({pair.representation_id for pair in valid_pairs}))
                if status == "COVERED":
                    covered_count += 1
        reasons.update(row_reasons)
        records.append(
            ObligationCoverage(
                obligation_id,
                applicability_status,
                mandatory,
                status,
                required,
                covered,
                valid_ids,
                tuple(sorted(row_reasons)),
            )
        )
    status = (
        CoverageStatus.UNKNOWN
        if unknown_any
        else CoverageStatus.INCOMPLETE
        if active_mandatory_count != covered_count
        else CoverageStatus.COMPLETE
    )
    if status is CoverageStatus.INCOMPLETE:
        reasons.add("MANDATORY_COVERAGE_INCOMPLETE")
    applicability_digest = _assessment_digest(applicability)
    content = {
        "schema_version": 1,
        "architecture_source_sha": applicability.architecture_source_sha,
        "applicability_assessment_sha256": applicability_digest,
        "policy_source_revision": applicability.policy_source_revision,
        "policy_bundle_sha256": applicability.policy_bundle_sha256,
        "ruleset_sha256": applicability.ruleset_sha256,
        "status": status.value,
        "mandatory_total": active_mandatory_count,
        "mandatory_covered": covered_count,
        "obligations": [record.to_dict() for record in records],
        "reason_codes": sorted(reasons),
    }
    digest = sha256_bytes(canonical_json_bytes(content))
    result = CoverageAssessment(
        applicability.architecture_source_sha,
        applicability_digest,
        applicability.policy_source_revision,
        applicability.policy_bundle_sha256,
        applicability.ruleset_sha256,
        status,
        active_mandatory_count,
        covered_count,
        tuple(records),
        tuple(sorted(reasons)),
        digest,
    )
    validate_payload("p_coverage_assessment_v1.schema.json", result.to_dict())
    return result


def _pair_result(
    representation_id: str,
    obligation_id: str,
    architecture_source_sha: str,
    criterion_id: str,
    stage: str | None,
    status: PairStatus,
    compliance_status: ComplianceStatus,
    evidence_digest: str | None,
    evaluator_artifact_sha: str | None,
    proof: EvidenceProof | None,
    reasons: set[str],
    evidence_refs: set[str],
    artifacts: tuple[Mapping[str, str], ...],
    *,
    proof_status: str | None = None,
) -> PairAssessment:
    semantic_status = proof_status or (proof.status.value if proof else "UNDETERMINED")
    content = {
        "schema_version": 1,
        "representation_id": representation_id,
        "obligation_id": obligation_id,
        "architecture_source_sha": architecture_source_sha,
        "criterion_id": criterion_id,
        "stage": stage,
        "status": status.value,
        "compliance_status": compliance_status.value,
        "evaluator_evidence_sha256": evidence_digest,
        "evaluator_artifact_sha256": evaluator_artifact_sha,
        "semantic_proof_status": semantic_status,
        "semantic_verifier_id": proof.verifier_id if proof else None,
        "reason_codes": sorted(reasons),
        "evidence_refs": sorted(evidence_refs),
        "evidence_artifacts": [dict(item) for item in artifacts],
    }
    assessment = PairAssessment(
        representation_id,
        obligation_id,
        architecture_source_sha,
        criterion_id,
        stage,
        status,
        compliance_status,
        evidence_digest,
        evaluator_artifact_sha,
        semantic_status,
        proof.verifier_id if proof else None,
        tuple(sorted(reasons)),
        tuple(sorted(evidence_refs)),
        artifacts,
        sha256_bytes(canonical_json_bytes(content)),
    )
    validate_payload("p_pair_assessment_v1.schema.json", assessment.to_dict())
    return assessment


def _assessment_digest(assessment: ApplicabilityAssessment) -> str:
    return sha256_bytes(canonical_json_bytes(assessment.to_dict()))


def _pair_assessment_digest_is_valid(pair: PairAssessment) -> bool:
    content = pair.to_dict()
    claimed_digest = content.pop("assessment_sha256")
    return isinstance(claimed_digest, str) and claimed_digest == sha256_bytes(
        canonical_json_bytes(content)
    )


def _digest_value(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _is_sha1(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{40}", value) is not None


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _required_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ContractValidationError(f"P03_ID_INVALID: {label}")
    return value


def _normalized_proof_reasons(reasons: Sequence[str], fallback: str) -> set[str]:
    if not reasons:
        return {fallback}
    normalized = {
        reason
        if re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", reason)
        else "PAIR_PROOF_REASON_UNSTRUCTURED"
        for reason in reasons
    }
    return normalized


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list | tuple):
        return set()
    return {item for item in value if isinstance(item, str)}


def _inspection_scope_unresolved(
    evaluator_evidence: Mapping[str, Any],
    checked_artifacts: Sequence[Mapping[str, str]],
    artifact_bytes: Mapping[str, bytes],
) -> bool:
    """Validate legacy edge counts or an explicit typed inspection inventory."""
    scope = evaluator_evidence.get("inspection_scope")
    if scope is None:
        return evaluator_evidence.get("inspected_edge_count") is None
    if not isinstance(scope, Mapping):
        return True

    unit = scope.get("unit")
    expected = _string_set(scope.get("expected_subjects"))
    inspected = _string_set(evaluator_evidence.get("inspected_subjects"))
    measured_count = scope.get("measured_count")
    artifact = scope.get("evidence_artifact")
    if (
        unit not in {"dependency_edge", "module", "file"}
        or not expected
        or expected != inspected
        or type(measured_count) is not int
        or measured_count < 0
        or not isinstance(artifact, Mapping)
    ):
        return True

    artifact_path = artifact.get("path")
    artifact_digest = artifact.get("sha256")
    if not any(
        checked.get("path") == artifact_path and checked.get("sha256") == artifact_digest
        for checked in checked_artifacts
    ):
        return True
    scope_bytes = artifact_bytes.get(str(artifact_path))
    if scope_bytes is None:
        return True
    try:
        scope_record = json.loads(scope_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return True
    if not isinstance(scope_record, Mapping):
        return True
    if (
        scope_record.get("inspection_unit") != unit
        or _string_set(scope_record.get("expected_subjects")) != expected
        or _string_set(scope_record.get("inspected_subjects")) != inspected
        or type(scope_record.get("measured_count")) is not int
        or scope_record.get("measured_count") != measured_count
    ):
        return True

    inspected_edge_count = evaluator_evidence.get("inspected_edge_count")
    if unit == "dependency_edge":
        return (
            measured_count <= 0
            or type(inspected_edge_count) is not int
            or inspected_edge_count != measured_count
        )
    return inspected_edge_count is not None or measured_count != len(inspected)


__all__ = [
    "ComplianceStatus",
    "CoverageAssessment",
    "CoverageStatus",
    "ObligationCoverage",
    "PairAssessment",
    "PairStatus",
    "assess_mandatory_coverage",
    "assess_pair",
    "pair_proof_subject",
]
