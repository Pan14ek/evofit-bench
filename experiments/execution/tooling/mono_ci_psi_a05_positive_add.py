"""TEST_ONLY scoped inputs for the controlled positive ADD experiment.

This module supplies author-declared evidence to the unchanged Method P engine.
It does not alter planning, candidate materialization, or governance semantics.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
)
from experiments.execution.tooling.mono_ci_psi_evidence import (
    TEST_ONLY_VERIFIER_ID,
    TestOnlyEvidenceTrustContext,
    adapt_evaluator_evidence,
    build_inspection_scope_artifact,
    build_source_inventory_fact_ledger,
    create_test_only_sidecar,
    evaluator_source_artifacts,
    run_fresh_evaluator,
)
from experiments.execution.tooling.p_adaptation import verify_v3_p_bundle
from experiments.execution.tooling.p_applicability import EvidenceLedger, EvidenceProof, ProofStatus
from experiments.execution.tooling.p_input_validation import (
    SourceReference,
    load_verified_source_manifest,
)
from experiments.execution.tooling.p_operations import template_descriptor_sha256
from experiments.execution.tooling.p_policy_source_v3 import (
    METHOD_INPUT_SCHEMA,
    package_policy_source_v3,
    verify_method_bundle_v3,
)
from experiments.execution.tooling.p_semantic import pair_proof_subject
from experiments.pilots.pilot02_testonly_execution import (
    Pilot02TestOnlyTrustContext,
    build_testonly_evidence_ledger,
    create_testonly_policy_source,
)

SCOPE_EVIDENCE_ID = "POSITIVE_ADD_SCOPE_DECLARATION"
SCOPE_EVIDENCE_PATH = f"fitness/policy/evidence/{SCOPE_EVIDENCE_ID}.json"
EVALUATOR_ID = "AC_DATA_OWNERSHIP"
OBLIGATION_ID = "AC_DATA_OWNERSHIP"
REPRESENTATION_ID = "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP"
TEMPLATE_ARTIFACT_PATH = (
    "PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP/source-manifest.json"
)
CONFIGURATION_PATH = "architecture/acceptance/a1/data_ownership_v1.yaml"
POLICY_VERIFIER_ID = "pilot02_test_only_policy_verifier_v1"
POLICY_SIGNER_ID = "PILOT02_TEST_ONLY_KEY"
POLICY_HMAC_KEY = b"pilot02-public-test-only-policy-key-v1"
STUDY_ID = "MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_V1"
PROFILE_ID = "MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_PROFILE_V1"
PROFILE_C2_ID = "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_PROFILE_V1"
STUDY_C2_ID = "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_V1"
PROFILE_C2_SCHEMA = "mono_ci_psi_positive_add_c2_profile_v1.schema.json"
RETAIN_OBLIGATION_IDS = ("AC_MODULE_GRAPH", "AC_PUBLIC_API")
MAX_COST_MS = 225
MAX_SEARCH_NODES = 2


@dataclass(frozen=True)
class PositiveAddRuntimeContext:
    """Verified evidence for this study's bounded TEST_ONLY input profile."""

    trust_context: Pilot02TestOnlyTrustContext
    evidence_ledger: EvidenceLedger
    ledger_summary: dict[str, Any]
    fact_verifier: Any
    completeness_verifier: Any


class PositiveAddTrustContext(Pilot02TestOnlyTrustContext):
    """TEST_ONLY policy declarations plus a run-local adaptation-evidence key."""

    def __init__(self, key: bytes) -> None:
        super().__init__()
        self.adaptation_evidence_verifiers = TestOnlyEvidenceTrustContext(
            key
        ).adaptation_evidence_verifiers


def create_policy_source(
    repository: Path,
    working_root: Path,
    output_directory: Path,
    *,
    evaluation_as_of: str,
    before_sha: str,
    after_sha: str,
    obligation_catalog_sha256: str,
    policy_source_revision: str,
) -> dict[str, Any]:
    """Build a versioned, bounded TEST_ONLY policy package in run output."""
    if policy_source_revision == PROFILE_ID:
        selected_ids = (OBLIGATION_ID,)
        applicability = {OBLIGATION_ID: {"before": "INACTIVE", "after": "ACTIVE"}}
    elif policy_source_revision == PROFILE_C2_ID:
        selected_ids = (OBLIGATION_ID, *RETAIN_OBLIGATION_IDS)
        applicability = {
            OBLIGATION_ID: {"before": "INACTIVE", "after": "ACTIVE"},
            **{
                obligation_id: {"before": "ACTIVE", "after": "ACTIVE"}
                for obligation_id in RETAIN_OBLIGATION_IDS
            },
        }
    else:
        raise ContractValidationError("POSITIVE_ADD_POLICY_PROFILE_VERSION_UNSUPPORTED")
    working_root.mkdir(parents=True, exist_ok=False)
    source, _trust = create_testonly_policy_source(
        repository / "experiments/execution/policy-pilot/v1/source",
        working_root,
        evaluation_as_of=evaluation_as_of,
        before_sha=before_sha,
        after_sha=after_sha,
        obligation_catalog_sha256=obligation_catalog_sha256,
        target_obligation_ids=list(selected_ids),
        applicability_by_obligation=applicability,
    )
    registry_path = source / "fitness/policy/registry.json"
    registry = json.loads(registry_path.read_bytes())
    registry["registry_version"] = policy_source_revision
    registry["as_of"] = evaluation_as_of
    for policy in registry["policies"]:
        policy["proposition"] = (
            "TEST_ONLY author declaration for bounded obligations: "
            + ", ".join(selected_ids)
            + ". The selection and exact-pair semantics are not independent or external "
            "normative authority."
        )
        approval_path = source / f"fitness/policy/approvals/{policy['approval_source_id']}.json"
        approval = json.loads(approval_path.read_bytes())
        policy_sha = sha256_bytes(canonical_json_bytes(policy))
        signed = {
            "action": "APPROVED",
            "policy_sha256": policy_sha,
            "signer_key_id": POLICY_SIGNER_ID,
        }
        import hashlib
        import hmac

        approval.update(
            {
                "policy_registry_version": registry["registry_version"],
                "policy_sha256": policy_sha,
                "signature": hmac.new(
                    POLICY_HMAC_KEY, canonical_json_bytes(signed), hashlib.sha256
                ).hexdigest(),
            }
        )
        approval_path.write_bytes(pretty_json_bytes(approval))
    registry_path.write_bytes(pretty_json_bytes(registry))

    claims_path = source / "fitness/policy/completeness-claims.json"
    claims = json.loads(claims_path.read_bytes())
    if policy_source_revision == PROFILE_C2_ID:
        expanded_claims: list[dict[str, Any]] = []
        for original in claims:
            for obligation_id in selected_ids:
                claim = dict(original)
                claim["id"] = f"{original['id']}_{obligation_id}"
                claim["fact_type"] = f"obligation:{obligation_id}"
                expanded_claims.append(claim)
        claims = expanded_claims
        registry["closure_claim_ids"] = sorted(str(claim["id"]) for claim in claims)
        registry_path.write_bytes(pretty_json_bytes(registry))
    declaration = {
        "schema_version": 1,
        "profile_id": policy_source_revision,
        "classification": "TEST_ONLY_AUTHOR_DECLARED_SCOPED_INPUT",
        "scope": "application",
        "selected_obligation_id": OBLIGATION_ID,
        "selected_obligation_mandatory": True,
        "claims": [],
        "global_denominator_or_coverage_claim": False,
        "external_normative_authority_claimed": False,
        "independent_verification_claimed": False,
    }
    if policy_source_revision == PROFILE_C2_ID:
        declaration["selected_obligation_ids"] = sorted(selected_ids)
    for claim in claims:
        if policy_source_revision != PROFILE_C2_ID:
            claim["fact_type"] = f"obligation:{OBLIGATION_ID}"
        obligation_id = str(claim["fact_type"].removeprefix("obligation:"))
        claim["method_id"] = (
            "mono_ci_a05_positive_add_test_only_scope_v1"
            if policy_source_revision == PROFILE_ID
            else "mono_ci_a05_positive_add_c2_test_only_scope_v1"
        )
        claim["evidence_source_ids"] = [SCOPE_EVIDENCE_ID]
        claim["assumptions"] = [f"bounded_obligation_universe:{obligation_id}"]
        claim["procedure_ref"] = (
            "test-only://mono-ci-a05-positive-add/v1"
            if policy_source_revision == PROFILE_ID
            else "test-only://mono-ci-a05-positive-add-c2/v1"
        )
        claim["policy_registry_version"] = registry["registry_version"]
        claim["as_of"] = evaluation_as_of
        state = str(claim["state"])
        claim_id = str(claim["id"])
        declaration["claims"].append(
            {
                "claim_id": claim_id,
                "kind": claim["kind"],
                "state": state,
                "fact_type": claim["fact_type"],
                "scope": claim["scope"],
                "architecture_revision": claim["architecture_revision"],
                "policy_registry_version": claim["policy_registry_version"],
                "as_of": evaluation_as_of,
            }
        )
    for path in (source / "fitness/policy/evidence").glob(
        "PILOT02_TEST_ONLY_REGISTRY_EVIDENCE_*.json"
    ):
        path.unlink()
    (source / "fitness/policy/evidence" / f"{SCOPE_EVIDENCE_ID}.json").write_bytes(
        pretty_json_bytes(
            {
                "fixture": "pilot02-test-only-closed-registry-v1",
                **declaration,
            }
        )
    )
    claims_path.write_bytes(pretty_json_bytes(claims))
    return package_policy_source_v3(source, output_directory, policy_source_revision)


def prepare_method_inputs(
    repository: Path,
    run_root: Path,
    bundle_root: Path,
    profile_path: Path,
) -> dict[str, Any]:
    """Bind the TEST_ONLY profile and real artifact inside the V3 capability input."""
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    _validate_static_profile(profile)
    source_rows, source_manifest_bytes, source_digest = evaluator_source_artifacts(repository)
    for retain in profile.get("additional_retain_obligations", []):
        if (
            sha256_file(repository / retain["configuration_path"]) != retain["configuration_sha256"]
            or source_digest != retain["evaluator_source_manifest_sha256"]
        ):
            raise ContractValidationError("POSITIVE_ADD_RETAIN_EVIDENCE_SOURCE_BINDING_MISMATCH")
    config_bytes = (repository / CONFIGURATION_PATH).read_bytes()
    config_digest = sha256_bytes(config_bytes)
    implementation_root = run_root / Path(TEMPLATE_ARTIFACT_PATH).parent
    implementation_root.mkdir(parents=True, exist_ok=True)
    _write_identical_or_new(implementation_root / "source-manifest.json", source_manifest_bytes)
    source_dir = implementation_root / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    for row in source_rows:
        content = (repository / "architecture/acceptance/a1" / row["path"]).read_bytes()
        if sha256_bytes(content) != row["sha256"]:
            raise ContractValidationError("POSITIVE_ADD_EVALUATOR_SOURCE_DIGEST_MISMATCH")
        _write_identical_or_new(source_dir / row["path"], content)
    _write_identical_or_new(implementation_root / Path(CONFIGURATION_PATH).name, config_bytes)
    representation = {
        "id": REPRESENTATION_ID,
        "active": True,
        "criterion": "architecture_compliance",
        "stage": "ci_test",
        "evaluator": EVALUATOR_ID,
        "evaluator_artifact": {"path": TEMPLATE_ARTIFACT_PATH, "sha256": source_digest},
        "covers": [OBLIGATION_ID],
        "applicability_scope": {
            "scope_id": "architecture.data_ownership.persistence_ownership",
            "architecture_scope": "app.modules",
            "architecture_state": "A0_5_MODULE_DATA_OWNERSHIP",
        },
        "evidence_contract": {
            "record_id": "mono-ci-a05-positive-add-ac-data-ownership-v1",
            "evaluator_id": EVALUATOR_ID,
            "evaluator_name": EVALUATOR_ID,
            "source_stage": "ci_test",
            "method_stage": "ci",
            "scope_id": "architecture.data_ownership.persistence_ownership",
            "configuration_path": CONFIGURATION_PATH,
            "configuration_sha256": config_digest,
            "evaluator_source_sha256": source_digest,
            "evidence_requirements": [
                "source_manifest_digest_matches_pinned_evaluator_sources",
                "configuration_digest_matches_a1_configuration",
                "raw_stdout_and_stderr_are_digest_bound",
                "exact_architecture_source_and_inspection_scope_are_bound",
            ],
        },
    }
    template = {
        "template_id": "TEMPLATE_POSITIVE_ADD_AC_DATA_OWNERSHIP_V1",
        "representation": representation,
    }
    capabilities_path = bundle_root / "fitness/evaluator-capabilities.json"
    capabilities = json.loads(capabilities_path.read_bytes())
    capabilities["generic_candidate_templates"] = [template]
    cost_model = {
        "model_version": "POSITIVE_ADD_TEST_ONLY_COST_V1",
        "authority_status": "TEST_ONLY_AUTHOR_DECLARED",
        "unit": "elapsed wall-clock milliseconds per added evaluator invocation",
        "max_incremental_cost": MAX_COST_MS,
        "max_search_nodes": MAX_SEARCH_NODES,
        "candidate_costs": {source_digest: MAX_COST_MS},
        "unavailable_or_exceeded_behavior": "HOLD_AND_DO_NOT_SELECT_TEMPLATE",
        "source_binding": "AC_DATA_OWNERSHIP evaluator source-manifest SHA-256",
    }
    capabilities["p_cost_model_v1"] = cost_model
    profile_id = str(profile["profile_id"])
    profile_key = (
        "positive_add_test_only_profile_v2"
        if profile_id == PROFILE_C2_ID
        else "positive_add_test_only_profile_v1"
    )
    profile_binding = {
        "profile_id": profile_id,
        "study_profile_base64": base64.b64encode(profile_bytes).decode("ascii"),
        "study_profile_sha256": sha256_bytes(profile_bytes),
        "classification": "TEST_ONLY_AUTHOR_DECLARED_SCOPED_INPUT",
        "scope": "application",
        "selected_obligation_id": OBLIGATION_ID,
        "selected_obligation_ids": list(_selected_obligation_ids(profile)),
        "stage_contract": profile.get(
            "stage_contract", {"obligations": {OBLIGATION_ID: ["ci_test"]}}
        ),
        "other_catalog_obligations": "UNKNOWN_APPLICABILITY_AND_NOT_MANDATORY_IN_THIS_SCOPE",
        "template_descriptor_sha256": template_descriptor_sha256(template),
        "template": template,
        "evaluator_artifact_path": TEMPLATE_ARTIFACT_PATH,
        "evaluator_artifact_base64": base64.b64encode(source_manifest_bytes).decode("ascii"),
        "configuration_path": CONFIGURATION_PATH,
        "configuration_bytes_base64": base64.b64encode(config_bytes).decode("ascii"),
        "configuration_sha256": config_digest,
        "source_manifest_sha256": source_digest,
        "cost_model": cost_model,
    }
    capabilities[profile_key] = profile_binding
    capabilities_path.write_bytes(pretty_json_bytes(capabilities))
    manifest_path = bundle_root / "method_input_v3.json"
    method_manifest = json.loads(manifest_path.read_bytes())
    files = {row["path"]: row for row in method_manifest["files"]}
    capabilities_record = files.get("fitness/evaluator-capabilities.json")
    if not isinstance(capabilities_record, dict):
        raise ContractValidationError("POSITIVE_ADD_CAPABILITIES_INPUT_MISSING")
    capabilities_record.update(
        {
            "size_bytes": capabilities_path.stat().st_size,
            "sha256": sha256_file(capabilities_path),
        }
    )
    method_manifest["files"] = sorted(files.values(), key=lambda row: row["path"])
    method_manifest["bundle_sha256"] = bundle_sha256(method_manifest["files"])
    validate_payload(METHOD_INPUT_SCHEMA, method_manifest)
    manifest_path.write_bytes(pretty_json_bytes(method_manifest))
    _validate_profile_binding(bundle_root, method_manifest)
    return {
        "profile": profile,
        "profile_sha256": sha256_bytes(profile_bytes),
        "template": template,
        "template_descriptor_sha256": template_descriptor_sha256(template),
        "evaluator_source_manifest_sha256": source_digest,
        "configuration_sha256": config_digest,
    }


def build_runtime_context(bundle_root: Path, key: bytes) -> PositiveAddRuntimeContext:
    """Reconstruct exact source-bound TEST_ONLY claims before calling Method P."""
    manifest = verify_method_bundle_v3(bundle_root, expected_method_id="P")
    _validate_profile_binding(bundle_root, manifest)
    ledger_facts, facts_summary = build_source_inventory_fact_ledger(bundle_root)
    snapshot = json.loads((bundle_root / "architecture-policy-snapshot.json").read_bytes())
    sources, source_report = load_verified_source_manifest(snapshot, manifest, bundle_root)
    if source_report.status.value != "VALID":
        raise ContractValidationError("POSITIVE_ADD_SOURCE_MANIFEST_UNVERIFIED")
    profile_binding = _validate_profile_binding(bundle_root, manifest)
    profile = json.loads(base64.b64decode(profile_binding["study_profile_base64"], validate=True))
    _validate_policy_claim_scope(snapshot, sources, profile)
    policy_context = PositiveAddTrustContext(key)
    policy_ledger = build_testonly_evidence_ledger(
        snapshot,
        sources,
        source_integrity_valid=True,
        trust_context=policy_context,
    )
    completeness_proofs: dict[str, EvidenceProof] = {}
    for claim in snapshot.get("completeness_claims", []):
        if not isinstance(claim, dict) or not _verify_scoped_closure_claim(
            claim,
            {source_id: sources[source_id] for source_id in claim.get("evidence_source_ids", [])},
            snapshot,
            profile,
        ):
            raise ContractValidationError("POSITIVE_ADD_SCOPED_CLOSURE_CLAIM_INVALID")
        claim_source_ids = [str(item) for item in claim["evidence_source_ids"]]
        completeness_proofs[str(claim["id"])] = EvidenceProof(
            ProofStatus.VALID,
            sha256_bytes(canonical_json_bytes(claim)),
            tuple(sorted((source_id, sources[source_id].sha256) for source_id in claim_source_ids)),
            (
                "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_PROFILE_V1"
                if profile.get("profile_id") == PROFILE_C2_ID
                else "MONO_CI_A05_POSITIVE_ADD_PROFILE_V1"
            ),
            tuple(sorted(claim_source_ids)),
        )
    ledger = EvidenceLedger(
        fact_proofs=ledger_facts.fact_proofs,
        policy_proofs=policy_ledger.policy_proofs,
        completeness_proofs=completeness_proofs,
        registry_proof=policy_ledger.registry_proof,
        charter_proof=policy_ledger.charter_proof,
    )
    profile_id = str(profile["profile_id"])
    selected_ids = _selected_obligation_ids(profile)
    summary = {
        "trust_scope": "TEST_ONLY_SOURCE_READBACK_AND_AUTHOR_DECLARATION",
        "verifier_id": (
            profile_id if profile_id == PROFILE_C2_ID else "MONO_CI_A05_POSITIVE_ADD_PROFILE_V1"
        ),
        "verified_fact_ids": sorted(ledger.fact_proofs),
        "verified_policy_ids": sorted(ledger.policy_proofs),
        "verified_completeness_claim_ids": sorted(ledger.completeness_proofs),
        "selected_obligation_id": OBLIGATION_ID,
        "other_catalog_obligations": "UNKNOWN",
        "external_normative_authority": False,
        "independent_verification": False,
        "source_inventory_verifier_id": facts_summary["verifier_id"],
    }
    if profile_id == PROFILE_C2_ID:
        summary["selected_obligation_ids"] = list(selected_ids)

    def fact_verifier(fact: Any, fact_sources: Any, _snapshot: Any) -> bool | None:
        proof = ledger_facts.fact_proofs.get(str(fact.get("id")))
        if proof is None:
            return None
        actual_bindings = tuple(
            sorted((source_id, source.sha256) for source_id, source in fact_sources.items())
        )
        expected_subject = sha256_bytes(canonical_json_bytes(dict(fact)))
        return bool(
            proof.status is ProofStatus.VALID
            and proof.subject_sha256 == expected_subject
            and proof.source_bindings == actual_bindings
        )

    def completeness_verifier(claim: Any, claim_sources: Any, checked_snapshot: Any) -> bool | None:
        return _verify_scoped_closure_claim(claim, claim_sources, checked_snapshot, profile)

    return PositiveAddRuntimeContext(
        trust_context=PositiveAddTrustContext(key),
        evidence_ledger=ledger,
        ledger_summary=summary,
        fact_verifier=fact_verifier,
        completeness_verifier=completeness_verifier,
    )


def build_verified_bundle(bundle_root: Path, key: bytes) -> tuple[Any, PositiveAddRuntimeContext]:
    """Verify V3 inputs and bind TEST_ONLY artifact bytes carried in capabilities."""
    context = build_runtime_context(bundle_root, key)
    bundle = verify_v3_p_bundle(
        bundle_root,
        evidence_ledger=context.evidence_ledger,
        trust_context=context.trust_context,
        fact_verifier=context.fact_verifier,
        completeness_verifier=context.completeness_verifier,
    )
    profile = _validate_profile_binding(bundle_root, dict(bundle.manifest))
    if TEMPLATE_ARTIFACT_PATH in bundle.artifact_bytes:
        raise ContractValidationError("POSITIVE_ADD_EVALUATOR_ARTIFACT_PATH_CONFLICT")
    try:
        evaluator_artifact = base64.b64decode(profile["evaluator_artifact_base64"], validate=True)
    except (KeyError, ValueError, TypeError) as error:
        raise ContractValidationError("POSITIVE_ADD_EVALUATOR_ARTIFACT_ENCODING_INVALID") from error
    from experiments.execution.tooling.p_adaptation import (
        _VERIFIED_V3_BUNDLE_DIGESTS,
        _verified_bundle_content_sha256,
    )

    object.__setattr__(
        bundle,
        "artifact_bytes",
        {**bundle.artifact_bytes, TEMPLATE_ARTIFACT_PATH: evaluator_artifact},
    )
    _VERIFIED_V3_BUNDLE_DIGESTS[bundle] = _verified_bundle_content_sha256(bundle)
    return bundle, context


def create_positive_sidecar(
    *,
    repository: Path,
    run_root: Path,
    bundle: Any,
    evaluator_runs: list[dict[str, Any]],
    evaluator_bindings: dict[str, dict[str, Any]],
    evaluator_artifacts: dict[str, dict[str, bytes]],
    key: bytes,
) -> dict[str, Any]:
    """Create signed, scoped evidence from the actual three evaluator outputs."""
    from experiments.execution.tooling import mono_ci_psi_transition as transition

    profile = _validate_profile_binding(run_root / "PSI/method-input", dict(bundle.manifest))
    representations = {str(row["id"]): row for row in bundle.representations}
    obligations = {str(row["id"]): row for row in bundle.obligations}
    after_runs = {
        run["evaluator_id"]: run
        for run in evaluator_runs
        if run["architecture_state"] == "A0_5_MODULE_DATA_OWNERSHIP"
    }
    pair_evidence: list[dict[str, Any]] = []
    pair_proofs: list[dict[str, Any]] = []
    artifact_bytes: dict[str, bytes] = {}
    for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH"):
        representation_id = evaluator_bindings[evaluator_id]["representation_id"]
        representation = representations[representation_id]
        run = after_runs[evaluator_id]
        coverage_path = transition._coverage_assessment_path(
            "A0_5_MODULE_DATA_OWNERSHIP", evaluator_id
        )
        coverage = json.loads((run_root / coverage_path).read_bytes())
        refs = transition._evaluator_artifact_references(
            run_root,
            run,
            evaluator_bindings[evaluator_id],
            evaluator_artifacts[evaluator_id],
        )
        artifact_bytes.update(
            {relative: (run_root / relative).read_bytes() for relative, _ in refs}
        )
        evidence = adapt_evaluator_evidence(
            representation=representation,
            obligation_id=evaluator_id,
            run=run,
            artifact_refs=[{"path": path, "sha256": digest} for path, digest in refs],
            coverage_verification=coverage,
        )
        evidence["semantic_compatible"] = True
        evidence["adequacy_proven"] = True
        pair_evidence.append(
            {
                "representation_id": representation_id,
                "obligation_id": evaluator_id,
                "evidence": evidence,
            }
        )
        pair_proofs.append(_pair_proof(bundle, representation, obligations[evaluator_id], evidence))

    template = next(
        row
        for row in bundle.templates
        if row.get("template_id") == "TEMPLATE_POSITIVE_ADD_AC_DATA_OWNERSHIP_V1"
    )
    representation = dict(template["representation"])
    positive_run, positive_coverage, positive_refs = _run_positive_input_evaluator(
        repository, run_root, str(bundle.snapshot["architecture"]["after_commit"])
    )
    artifact_bytes.update(
        {relative: (run_root / relative).read_bytes() for relative, _ in positive_refs}
    )
    evidence = adapt_evaluator_evidence(
        representation=representation,
        obligation_id=OBLIGATION_ID,
        run=positive_run,
        artifact_refs=[{"path": path, "sha256": digest} for path, digest in positive_refs],
        coverage_verification=positive_coverage,
    )
    evidence["semantic_compatible"] = True
    evidence["adequacy_proven"] = True
    pair_evidence.append(
        {
            "representation_id": REPRESENTATION_ID,
            "obligation_id": OBLIGATION_ID,
            "evidence": evidence,
        }
    )
    pair_proofs.append(_pair_proof(bundle, representation, obligations[OBLIGATION_ID], evidence))

    sidecar = create_test_only_sidecar(
        bundle=bundle,
        pair_evidence=pair_evidence,
        pair_proofs=pair_proofs,
        artifact_bytes=artifact_bytes,
        key=key,
    )
    source_ids = sorted(bundle.source_digests)
    sidecar["source_bindings"] = [
        {"source_id": source_id, "sha256": bundle.source_digests[source_id]}
        for source_id in source_ids
    ]
    payload = sidecar["payload"]
    policy_rows = [dict(row) for row in bundle.snapshot.get("policies", [])]
    payload["policy_inventories"] = []
    for state in ("before", "after"):
        revision = str(bundle.snapshot["architecture"][f"{state}_commit"])
        inventory_subject = {
            "claim_type": "policy_inventory",
            "state": state,
            "scope": str(bundle.snapshot["policy_registry"]["scope"]),
            "architecture_source_sha": revision,
            "policy_source_revision": bundle.manifest["policy_source_revision"],
            "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
            "rows_sha256": sha256_bytes(canonical_json_bytes(policy_rows)),
        }
        payload["policy_inventories"].append(
            {
                "state": state,
                "scope": str(bundle.snapshot["policy_registry"]["scope"]),
                "architecture_source_sha": revision,
                "rows": policy_rows,
                "proof": _scoped_proof(
                    bundle,
                    inventory_subject,
                    tuple(sorted(_policy_source_ids(bundle, policy_rows))),
                    (state,),
                ),
            }
        )
    selected_ids = set(_selected_obligation_ids(profile))
    rows = [
        {"obligation_id": row["id"], "mandatory": row["id"] in selected_ids}
        for row in bundle.obligations
    ]
    payload["test_only_mandatory_classification"] = {
        "rows": rows,
        "proof": _scoped_proof(
            bundle,
            {
                "claim_type": "test_only_mandatory_classification",
                "rows_sha256": sha256_bytes(canonical_json_bytes(rows)),
                "input_bundle_sha256": bundle.manifest["bundle_sha256"],
                "policy_source_revision": bundle.manifest["policy_source_revision"],
                "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
            },
            tuple(sorted(_policy_source_ids(bundle, rows))),
            ("before", "after"),
        ),
    }
    required_stages = {
        str(obligation_id): list(stages)
        for obligation_id, stages in profile.get("stage_contract", {})
        .get("obligations", {OBLIGATION_ID: ["ci_test"]})
        .items()
    }
    payload["required_stages"] = required_stages
    payload["stage_contract_proof"] = _scoped_proof(
        bundle,
        {
            "claim_type": "required_stages",
            "required_stages_sha256": sha256_bytes(canonical_json_bytes(required_stages)),
            "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        },
        ("P_CAPABILITIES",),
        ("after",),
    )
    payload["trace_inventory_proof"] = _scoped_proof(
        bundle,
        {
            "claim_type": "trace_inventory",
            "trace_graph_sha256": bundle.trace_graph.graph_sha256,
            "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        },
        ("P_TRACEABILITY",),
        ("before", "after"),
    )
    from experiments.execution.tooling.p_adaptation import (
        _change_inventory_source_ids,
    )

    payload["change_inventory_proof"] = _scoped_proof(
        bundle,
        {
            "claim_type": "change_inventory",
            "snapshot_sha256": bundle.snapshot_validation.snapshot_digest,
            "input_bundle_sha256": bundle.manifest["bundle_sha256"],
            "policy_source_revision": bundle.manifest["policy_source_revision"],
            "policy_bundle_sha256": bundle.manifest["policy_bundle_sha256"],
        },
        tuple(sorted(_change_inventory_source_ids(bundle))),
        ("before", "after"),
    )
    payload["authorized_template_descriptor_sha256"] = [template_descriptor_sha256(template)]
    payload["cost_model_proof"] = _scoped_proof(
        bundle,
        {
            "claim_type": "cost_model_authority",
            "cost_model_sha256": sha256_bytes(canonical_json_bytes(bundle.cost_model)),
            "capabilities_sha256": bundle.source_digests["P_CAPABILITIES"],
            "input_bundle_sha256": bundle.manifest["bundle_sha256"],
        },
        ("P_CAPABILITIES",),
        ("after",),
    )
    _resign_sidecar(sidecar, key)
    return sidecar


def _run_positive_input_evaluator(
    repository: Path, run_root: Path, source_commit: str
) -> tuple[dict[str, Any], dict[str, Any], list[tuple[str, str]]]:
    from experiments.execution.tooling.mono_ci_psi_coverage import verify_inspection_coverage

    source_rows, source_manifest_bytes, source_digest = evaluator_source_artifacts(repository)
    config_bytes = (repository / CONFIGURATION_PATH).read_bytes()
    config_sha = sha256_bytes(config_bytes)
    output_directory = run_root / "PSI/evaluator-observations/positive-input/AC_DATA_OWNERSHIP"
    run = run_fresh_evaluator(
        repository=repository,
        source_checkout=repository,
        evaluator_id=EVALUATOR_ID,
        architecture_state="A0_5_MODULE_DATA_OWNERSHIP",
        source_commit_sha=source_commit,
        output_directory=output_directory,
    )
    if run["evaluator_source_sha256"] != source_digest or run["configuration_sha256"] != config_sha:
        raise ContractValidationError("POSITIVE_ADD_EVALUATOR_BINDING_MISMATCH")
    state_manifest = (
        repository / "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml"
    ).read_bytes()
    output_path = run_root / run["output_path"]
    coverage = verify_inspection_coverage(
        repository=repository,
        source_commit_sha=source_commit,
        source_tree_sha=run["source_tree_sha"],
        architecture_state="A0_5_MODULE_DATA_OWNERSHIP",
        evaluator_id=EVALUATOR_ID,
        evaluator_configuration_bytes=config_bytes,
        state_manifest_bytes=state_manifest,
        evaluator_output_bytes=output_path.read_bytes(),
        evaluator_evidence=run["evidence"],
    )
    coverage_path = output_directory / "inspection-coverage.json"
    coverage_path.write_bytes(pretty_json_bytes(coverage))
    scope_path = output_directory / "inspection-scope.json"
    scope_path.write_bytes(
        pretty_json_bytes(
            build_inspection_scope_artifact(run["evidence"], sha256_file(output_path), coverage)
        )
    )
    run["inspection_scope_path"] = scope_path.relative_to(run_root).as_posix()
    run["inspection_scope_sha256"] = sha256_file(scope_path)
    paths = [
        TEMPLATE_ARTIFACT_PATH,
        f"PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP/{Path(CONFIGURATION_PATH).name}",
        *[
            f"PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP/source/{row['path']}"
            for row in source_rows
        ],
        run["output_path"],
        run["stdout_path"],
        run["stderr_path"],
        run["inspection_scope_path"],
    ]
    refs = [(relative, sha256_file(run_root / relative)) for relative in sorted(set(paths))]
    summary = {
        "evaluator_id": EVALUATOR_ID,
        "source_commit_sha": source_commit,
        "source_tree_sha": run["source_tree_sha"],
        "application_tree_sha": run["target_application_tree_sha"],
        "evaluator_source_sha256": source_digest,
        "configuration_path": CONFIGURATION_PATH,
        "configuration_sha256": config_sha,
        "execution_status": run["execution_status"],
        "compliance": run["compliance"],
        "duration_ms": run["duration_ms"],
        "output_path": run["output_path"],
        "output_sha256": sha256_file(output_path),
        "inspection_coverage_path": coverage_path.relative_to(run_root).as_posix(),
        "inspection_coverage_sha256": sha256_file(coverage_path),
        "inspection_scope_path": run["inspection_scope_path"],
        "inspection_scope_sha256": run["inspection_scope_sha256"],
        "classification": "ACTUAL_A1_EVALUATOR_OUTPUT_USED_AS_TEST_ONLY_METHOD_INPUT",
    }
    (run_root / "diagnostics").mkdir(exist_ok=True)
    evaluator_run = {
        name: value for name, value in run.items() if name not in {"raw_stdout", "raw_stderr"}
    }
    (run_root / "diagnostics/positive-add-input-evaluator.json").write_bytes(
        pretty_json_bytes(
            {
                "schema_version": "MONO_CI_A05_POSITIVE_ADD_INPUT_EVALUATOR_V1",
                "classification": summary["classification"],
                # Raw streams are already retained at their digest-bound paths.
                # Keep their in-memory bytes out of this JSON diagnostic.
                "evaluator_run": evaluator_run,
                "inspection_coverage": coverage,
                "summary": summary,
            }
        )
    )
    return run, coverage, refs


def _pair_proof(
    bundle: Any,
    representation: dict[str, Any],
    obligation: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    subject = pair_proof_subject(
        representation,
        obligation,
        str(evidence["architecture_source_sha"]),
        evidence,
    )
    source_ids = ("ARCH_AFTER", "P_CAPABILITIES", "P_TRACEABILITY")
    return {
        "representation_id": representation["id"],
        "obligation_id": obligation["id"],
        "status": "VALID",
        "subject_sha256": sha256_bytes(canonical_json_bytes(subject)),
        "verifier_id": TEST_ONLY_VERIFIER_ID,
        "source_bindings": _binding_rows(bundle, source_ids),
        "evidence_refs": ["POSITIVE_ADD_SCOPE_DECLARATION", "ACTUAL_EVALUATOR_OUTPUT"],
        "reason_codes": [],
    }


def _scoped_proof(
    bundle: Any,
    subject: dict[str, Any],
    source_ids: tuple[str, ...],
    states: tuple[str, ...],
) -> dict[str, Any]:
    architecture = bundle.snapshot["architecture"]
    revisions = tuple(str(architecture[f"{state}_commit"]) for state in states)
    return {
        "status": "VALID",
        "subject_sha256": sha256_bytes(canonical_json_bytes(subject)),
        "scope": str(bundle.snapshot["policy_registry"]["scope"]),
        "architecture_source_shas": list(revisions),
        "verifier_id": TEST_ONLY_VERIFIER_ID,
        "source_bindings": _binding_rows(bundle, source_ids),
        "evidence_refs": sorted(set(source_ids)) or ["POSITIVE_ADD_SCOPE_DECLARATION"],
    }


def _binding_rows(bundle: Any, source_ids: tuple[str, ...]) -> list[dict[str, str]]:
    return [
        {"source_id": source_id, "sha256": bundle.source_digests[source_id]}
        for source_id in sorted(set(source_ids))
    ]


def _change_inventory_source_ids(bundle: Any) -> set[str]:
    from experiments.execution.tooling.p_adaptation import (
        _change_inventory_source_ids as source_ids,
    )

    return source_ids(bundle)


def _validate_profile_binding(bundle_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    records = {row["path"]: row for row in manifest["files"]}
    capabilities_path = bundle_root / "fitness/evaluator-capabilities.json"
    capability_record = records.get("fitness/evaluator-capabilities.json")
    if (
        not isinstance(capability_record, dict)
        or capability_record.get("role") != "evaluator_capabilities"
        or capability_record.get("sha256") != sha256_file(capabilities_path)
        or capability_record.get("size_bytes") != capabilities_path.stat().st_size
    ):
        raise ContractValidationError("POSITIVE_ADD_CAPABILITIES_INPUT_UNPINNED")
    capabilities = json.loads(capabilities_path.read_bytes())
    profile = capabilities.get("positive_add_test_only_profile_v2")
    expected_profile_key = "positive_add_test_only_profile_v2"
    if not isinstance(profile, dict):
        profile = capabilities.get("positive_add_test_only_profile_v1")
        expected_profile_key = "positive_add_test_only_profile_v1"
    expected_profile_id = PROFILE_C2_ID if expected_profile_key.endswith("_v2") else PROFILE_ID
    if not isinstance(profile, dict) or profile.get("profile_id") != expected_profile_id:
        raise ContractValidationError("POSITIVE_ADD_TEST_ONLY_PROFILE_MISSING")
    try:
        study_profile_bytes = base64.b64decode(profile["study_profile_base64"], validate=True)
        evaluator_artifact = base64.b64decode(profile["evaluator_artifact_base64"], validate=True)
        configuration_artifact = base64.b64decode(
            profile["configuration_bytes_base64"], validate=True
        )
        study_profile = json.loads(study_profile_bytes)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise ContractValidationError("POSITIVE_ADD_TEST_ONLY_PROFILE_ENCODING_INVALID") from error
    if not isinstance(study_profile, dict) or sha256_bytes(study_profile_bytes) != profile.get(
        "study_profile_sha256"
    ):
        raise ContractValidationError("POSITIVE_ADD_PROFILE_ARTIFACT_BINDING_MISMATCH")
    _validate_static_profile(study_profile)
    templates = capabilities.get("generic_candidate_templates")
    if not isinstance(templates, list) or len(templates) != 1:
        raise ContractValidationError("POSITIVE_ADD_TEMPLATE_INVENTORY_INVALID")
    template = templates[0]
    if (
        template != profile.get("template")
        or template.get("template_id") != "TEMPLATE_POSITIVE_ADD_AC_DATA_OWNERSHIP_V1"
        or template_descriptor_sha256(template) != profile.get("template_descriptor_sha256")
    ):
        raise ContractValidationError("POSITIVE_ADD_TEMPLATE_PROFILE_BINDING_MISMATCH")
    representation = template.get("representation")
    if not isinstance(representation, dict):
        raise ContractValidationError("POSITIVE_ADD_TEMPLATE_REPRESENTATION_INVALID")
    evidence_contract = representation.get("evidence_contract")
    if (
        representation.get("id") != REPRESENTATION_ID
        or representation.get("active") is not True
        or representation.get("criterion") != "architecture_compliance"
        or representation.get("stage") != "ci_test"
        or representation.get("evaluator") != EVALUATOR_ID
        or representation.get("covers") != [OBLIGATION_ID]
        or representation.get("applicability_scope")
        != {
            "scope_id": "architecture.data_ownership.persistence_ownership",
            "architecture_scope": "app.modules",
            "architecture_state": "A0_5_MODULE_DATA_OWNERSHIP",
        }
        or not isinstance(evidence_contract, dict)
    ):
        raise ContractValidationError("POSITIVE_ADD_TEMPLATE_SCOPE_INVALID")
    artifact_path = profile.get("evaluator_artifact_path")
    configuration_sha256 = profile.get("configuration_sha256")
    artifact_reference = representation.get("evaluator_artifact")
    if (
        artifact_path != TEMPLATE_ARTIFACT_PATH
        or sha256_bytes(evaluator_artifact) != profile.get("source_manifest_sha256")
        or artifact_reference
        != {"path": TEMPLATE_ARTIFACT_PATH, "sha256": profile.get("source_manifest_sha256")}
        or profile.get("configuration_path") != CONFIGURATION_PATH
        or sha256_bytes(configuration_artifact) != configuration_sha256
        or evidence_contract.get("configuration_path") != CONFIGURATION_PATH
        or evidence_contract.get("configuration_sha256") != configuration_sha256
        or evidence_contract.get("evaluator_source_sha256") != profile.get("source_manifest_sha256")
    ):
        raise ContractValidationError("POSITIVE_ADD_EVALUATOR_OR_CONFIGURATION_BINDING_MISMATCH")
    cost = profile.get("cost_model")
    if (
        not isinstance(cost, dict)
        or cost.get("max_incremental_cost") != MAX_COST_MS
        or cost.get("max_search_nodes") != MAX_SEARCH_NODES
        or cost.get("candidate_costs") != {profile.get("source_manifest_sha256"): MAX_COST_MS}
        or capabilities.get("p_cost_model_v1") != cost
        or profile.get("selected_obligation_id") != OBLIGATION_ID
        or profile.get("selected_obligation_ids")
        not in (None, list(_selected_obligation_ids(study_profile)))
    ):
        raise ContractValidationError("POSITIVE_ADD_COST_PROFILE_BINDING_INVALID")
    return profile


def _validate_policy_claim_scope(
    snapshot: dict[str, Any],
    sources: dict[str, SourceReference],
    profile: dict[str, Any],
) -> None:
    registry = snapshot.get("policy_registry", {})
    claims = snapshot.get("completeness_claims", [])
    registry_source_id = registry.get("source_id")
    registry_source = (
        sources.get(registry_source_id) if isinstance(registry_source_id, str) else None
    )
    if registry_source is None or registry_source.content is None:
        raise ContractValidationError("POSITIVE_ADD_POLICY_REGISTRY_SOURCE_MISSING")
    try:
        registry_artifact = json.loads(registry_source.content)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError("POSITIVE_ADD_POLICY_REGISTRY_SOURCE_INVALID") from error
    selected_ids = set(_selected_obligation_ids(profile))
    expected_fact_types = {f"obligation:{obligation_id}" for obligation_id in selected_ids}
    if (
        registry.get("closure") != "CLAIMED_CLOSED"
        or registry.get("registry_version") != profile.get("profile_id")
        or registry_artifact.get("schema_version") != "1.2"
        or registry_artifact.get("registry_version") != profile.get("profile_id")
        or registry_source.kind != "POLICY_REGISTRY"
        or profile.get("canonical_mandatory_projection", {}).get(
            "global_denominator_or_coverage_claim"
        )
        is not False
        or len(claims) != 2 * len(selected_ids)
        or any(
            not isinstance(claim, dict)
            or claim.get("fact_type") not in expected_fact_types
            or claim.get("scope") != "application"
            or claim.get("kind") != "AUTHORITATIVE_POLICY_REGISTRY"
            or claim.get("evidence_source_ids") != [SCOPE_EVIDENCE_ID]
            for claim in claims
        )
    ):
        raise ContractValidationError("POSITIVE_ADD_POLICY_SCOPE_NOT_BOUNDED")
    source = sources.get(SCOPE_EVIDENCE_ID)
    if source is None or source.content is None:
        raise ContractValidationError("POSITIVE_ADD_SCOPE_DECLARATION_MISSING")
    declaration = json.loads(source.content)
    if (
        declaration.get("profile_id") != profile.get("profile_id")
        or declaration.get("selected_obligation_id") != OBLIGATION_ID
        or (
            profile.get("profile_id") == PROFILE_C2_ID
            and declaration.get("selected_obligation_ids") != sorted(selected_ids)
        )
        or declaration.get("global_denominator_or_coverage_claim") is not False
        or {row.get("claim_id") for row in declaration.get("claims", [])}
        != {row.get("id") for row in claims}
    ):
        raise ContractValidationError("POSITIVE_ADD_SCOPE_DECLARATION_BINDING_INVALID")


def _verify_scoped_closure_claim(
    claim: dict[str, Any],
    sources: dict[str, SourceReference],
    snapshot: dict[str, Any],
    _profile: dict[str, Any],
) -> bool | None:
    allowed_fact_types = {
        f"obligation:{obligation_id}" for obligation_id in _selected_obligation_ids(_profile)
    }
    if claim.get("fact_type") not in allowed_fact_types or set(sources) != {SCOPE_EVIDENCE_ID}:
        return None
    source = sources[SCOPE_EVIDENCE_ID]
    if source.content is None or sha256_bytes(source.content) != source.sha256:
        return False
    try:
        evidence = json.loads(source.content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    rows = [row for row in evidence.get("claims", []) if row.get("claim_id") == claim.get("id")]
    architecture = snapshot.get("architecture", {})
    revision = architecture.get(
        "before_commit" if claim.get("state") == "before" else "after_commit"
    )
    return bool(
        evidence.get("profile_id") == _profile.get("profile_id")
        and evidence.get("selected_obligation_id") == OBLIGATION_ID
        and (
            evidence.get("selected_obligation_ids") == sorted(_selected_obligation_ids(_profile))
            if _profile.get("profile_id") == PROFILE_C2_ID
            else evidence.get("selected_obligation_ids") is None
        )
        and evidence.get("global_denominator_or_coverage_claim") is False
        and len(rows) == 1
        and rows[0].get("fact_type") == claim.get("fact_type")
        and rows[0].get("state") == claim.get("state")
        and rows[0].get("architecture_revision") == revision == claim.get("architecture_revision")
        and rows[0].get("scope") == claim.get("scope") == "application"
        and rows[0].get("policy_registry_version") == claim.get("policy_registry_version")
        and rows[0].get("as_of") == claim.get("as_of")
    )


def _resign_sidecar(sidecar: dict[str, Any], key: bytes) -> None:
    import hashlib
    import hmac

    sidecar.pop("sidecar_sha256", None)
    sidecar.pop("signature", None)
    digest = sha256_bytes(canonical_json_bytes(sidecar))
    sidecar["sidecar_sha256"] = digest
    sidecar["signature"] = hmac.new(key, digest.encode("ascii"), hashlib.sha256).hexdigest()


def _write_identical_or_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise ProtocolError("POSITIVE_ADD_ARTIFACT_PREEXISTS_WITH_DIFFERENT_BYTES")
        return
    path.write_bytes(content)


def _validate_static_profile(profile: Any) -> None:
    if isinstance(profile, dict) and profile.get("profile_id") == PROFILE_C2_ID:
        validate_payload(PROFILE_C2_SCHEMA, profile)
        selected_ids = {OBLIGATION_ID, *RETAIN_OBLIGATION_IDS}
        if (
            profile.get("schema_version") != 2
            or profile.get("canonical_mandatory_projection", {}).get(
                "additional_test_only_active_obligations"
            )
            != list(RETAIN_OBLIGATION_IDS)
            or profile.get("canonical_mandatory_projection", {}).get(
                "only_selected_rows_are_mandatory_within_test_scope"
            )
            is not True
            or profile.get("canonical_mandatory_projection", {}).get("other_applicability_status")
            != "UNKNOWN"
            or profile.get("cost_rule", {}).get("fixed_max_incremental_cost_ms") != MAX_COST_MS
            or profile.get("cost_rule", {}).get("fixed_max_search_nodes") != MAX_SEARCH_NODES
            or profile.get("research_boundaries", {}).get("canonical_catalog_modified") is not False
            or profile.get("research_boundaries", {}).get("measured_da01_authorized") is not False
            or set(_selected_obligation_ids(profile)) != selected_ids
        ):
            raise ContractValidationError("POSITIVE_ADD_C2_STATIC_PROFILE_INVALID")
        return
    validate_payload("mono_ci_psi_positive_add_profile_v1.schema.json", profile)
    if (
        not isinstance(profile, dict)
        or profile.get("schema_version") != 1
        or profile.get("profile_id") != "MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_PROFILE_V1"
        or profile.get("selected_obligation", {}).get("id") != OBLIGATION_ID
        or profile.get("selected_obligation", {}).get("mandatory") is not True
        or profile.get("canonical_mandatory_projection", {}).get("selected_obligation_is_true")
        is not True
        or profile.get("canonical_mandatory_projection", {}).get(
            "all_other_catalog_rows_are_false_only_within_this_test_scope"
        )
        is not True
        or profile.get("canonical_mandatory_projection", {}).get("other_applicability_status")
        != "UNKNOWN"
        or profile.get("cost_rule", {}).get("fixed_max_incremental_cost_ms") != MAX_COST_MS
        or profile.get("cost_rule", {}).get("fixed_max_search_nodes") != MAX_SEARCH_NODES
        or profile.get("research_boundaries", {}).get("canonical_catalog_modified") is not False
        or profile.get("research_boundaries", {}).get("measured_da01_authorized") is not False
    ):
        raise ContractValidationError("POSITIVE_ADD_STATIC_PROFILE_INVALID")


def _selected_obligation_ids(profile: dict[str, Any]) -> tuple[str, ...]:
    """Return the fixed, bounded applicability set for a supported TEST_ONLY profile."""
    if profile.get("profile_id") == PROFILE_C2_ID:
        return (OBLIGATION_ID, *RETAIN_OBLIGATION_IDS)
    if profile.get("profile_id") == PROFILE_ID:
        return (OBLIGATION_ID,)
    raise ContractValidationError("POSITIVE_ADD_PROFILE_ID_UNSUPPORTED")


def _policy_source_ids(bundle: Any, rows: list[dict[str, Any]]) -> set[str]:
    from experiments.execution.tooling.p_adaptation import _policy_source_ids as source_ids

    return source_ids(bundle, rows)
