"""EXP-04 admission-boundary and existing V3 verification integration tests."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import (
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.p_policy_source_v3 import (
    export_method_inputs_v3,
    package_policy_source_v3,
)
from experiments.execution.tooling.p_semantic import ComplianceStatus, PairStatus, assess_pair
from scripts import exp01_evidence_contract as exp01
from scripts import exp03_method_bridge as exp03
from scripts import exp04_evidence_admission as exp04
from tests.integration.test_exp03_method_bridge import (
    ALTERNATE_A0_1_REVISION,
    BASE_REVISION,
    FROZEN_A0_REVISION,
    POLICY_AS_OF,
    POLICY_SOURCE,
    _write_exp02_run,
)
from tests.integration.test_p_applicability_v3 import (
    _positive_adaptation_sidecar,
    _synthetic_positive_bundle,
)


def _export_p_input(root: Path, after_revision: str = BASE_REVISION) -> Path:
    policy_bundle = root / "policy-source"
    method_input = root / "method-input"
    package_policy_source_v3(POLICY_SOURCE, policy_bundle, "EXP04_DRAFT_OPEN_TEST")
    export_method_inputs_v3(
        exp01.ROOT,
        policy_bundle,
        method_input,
        "P",
        FROZEN_A0_REVISION,
        after_revision,
        POLICY_AS_OF,
    )
    return method_input


@pytest.fixture
def p_input_dir(tmp_path: Path) -> Path:
    return _export_p_input(tmp_path)


def _row(manifest: dict[str, Any], representation_id: str) -> dict[str, Any]:
    return next(
        item
        for item in manifest["representation_admissions"]
        if item["exp02_representation_id"] == representation_id
    )


def _reseal_manifest_and_trace(
    output_dir: Path,
    mutate: Any,
) -> None:
    manifest_path = output_dir / exp04.MANIFEST_FILENAME
    trace_path = output_dir / exp04.P_TRACE_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    mutate(manifest, trace)
    trace_bytes = pretty_json_bytes(trace)
    trace_path.write_bytes(trace_bytes)
    trace_reference = next(
        item
        for item in manifest["artifact_inventory"]
        if item["role"] == "method_p_execution_trace"
    )
    trace_reference["sha256"] = sha256_bytes(trace_bytes)
    trace_reference["size_bytes"] = len(trace_bytes)
    manifest["method_p"]["trace_reference"] = copy.deepcopy(trace_reference)
    manifest_bytes = pretty_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    (output_dir / exp04.MANIFEST_DIGEST_FILENAME).write_text(
        f"{sha256_bytes(manifest_bytes)}  {exp04.MANIFEST_FILENAME}\n", encoding="ascii"
    )


def test_validated_observation_keeps_provenance_and_separates_compliance(
    tmp_path: Path, p_input_dir: Path
) -> None:
    compliant_dir, noncompliant_dir = tmp_path / "compliant", tmp_path / "noncompliant"
    compliant_dir.mkdir()
    noncompliant_dir.mkdir()
    compliant_run, _ = _write_exp02_run(compliant_dir)
    noncompliant_run, _ = _write_exp02_run(noncompliant_dir, noncompliant_layering=True)

    compliant, _ = exp04.build_admission_artifact(compliant_run, p_input_dir=p_input_dir)
    noncompliant, _ = exp04.build_admission_artifact(noncompliant_run, p_input_dir=p_input_dir)
    passing = _row(compliant, "REP_A01_ARCH_INTERNAL_LAYERING_CI")
    failing = _row(noncompliant, "REP_A01_ARCH_INTERNAL_LAYERING_CI")

    assert passing["observation_status"] == "validated_observation"
    assert failing["observation_status"] == "validated_observation"
    assert passing["admission_status"] == failing["admission_status"] == "mapping_unresolved"
    assert passing["observed_compliance"]["status"] == "conforming"
    assert failing["observed_compliance"]["status"] == "nonconforming"
    assert passing["execution"]["actual_verdict"] == "passed"
    assert failing["execution"]["actual_verdict"] == "violations_detected"
    assert passing["exp02_evaluator"]["configuration_artifact_sha256"]
    assert passing["exp02_evaluator"]["raw_output_artifacts"]
    assert all(
        len(artifact["sha256"]) == 64
        for artifact in passing["exp02_evaluator"]["source_artifact_inventory"]
    )
    assert compliant["method_p"]["evidence_consumption_status"] == "not_consumed"
    assert noncompliant["method_p"]["evidence_consumption_status"] == "not_consumed"
    assert compliant["coverage_claims"]["Coverage_ref"] == "not_established"
    assert compliant["method_p"]["prediction_v1_emitted"] is False
    assert compliant["method_p"]["governance_result"] != "ACCEPT"
    assert compliant["external_evidence"]["verification_status"] == "authority_missing"


def test_architecture_revision_mismatch_stays_unresolved(tmp_path: Path) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    p_input_dir = _export_p_input(tmp_path, ALTERNATE_A0_1_REVISION)

    manifest, _ = exp04.build_admission_artifact(run_dir, p_input_dir=p_input_dir)
    layering = _row(manifest, "REP_A01_ARCH_INTERNAL_LAYERING_CI")

    assert layering["binding_checks"]["architecture_revision"] == "mismatch"
    assert "ARCHITECTURE_REVISION_NOT_EXACT" in layering["reason_codes"]
    assert layering["admission_status"] == "mapping_unresolved"


@pytest.mark.parametrize(
    ("mutation", "check_name", "expected_status"),
    [
        ("evaluator", "evaluator_identity", "mismatch"),
        ("scope", "applicability_scope", "mismatch"),
        ("stage", "lifecycle_stage", "mismatch"),
        ("metric", "metric_identity_and_units", "mismatch"),
        ("criterion_intent", "criterion_intent", "mismatch"),
        ("source_digest", "source_artifact_provenance", "mismatch"),
        ("metric_contract", "metric_observation_contract", "mismatch"),
        ("architecture_revision", "architecture_revision", "mismatch"),
    ],
)
def test_strict_mapping_rejects_individual_identity_mismatches(
    tmp_path: Path, mutation: str, check_name: str, expected_status: str
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    bundle, evidence, configuration, _ = exp03._load_exp02(run_dir)
    observation = next(
        item
        for item in evidence["representations"]
        if item["representation_id"] == "REP_A01_ARCH_INTERNAL_LAYERING_CI"
    )
    configured = next(
        item
        for item in configuration["representations"]
        if item["id"] == observation["representation_id"]
    )
    criterion = next(
        item for item in configuration["criteria"] if item["id"] == observation["criterion_id"]
    )
    record = next(
        item
        for item in bundle["records"]
        if item["record_id"] == observation["evaluator_execution"]["record_id"]
    )
    source_artifacts = exp04._source_artifact_rows(run_dir, bundle, configured["evaluator"], record)
    metric = configured["evaluator"]["metrics"][0]
    representation = {
        "id": observation["representation_id"],
        "criterion": observation["criterion_id"],
        "criterion_intent": criterion["intent"],
        "stage": exp03.STAGE_TRANSLATIONS[observation["lifecycle_stage"]],
        "evaluator": configured["evaluator"]["id"],
        "evaluator_artifact": {"sha256": record["configuration_artifact"]["sha256"]},
        "source_artifacts": [
            {"source_path": item["source_path"], "sha256": item["sha256"]}
            for item in source_artifacts
            if item["source_path"] is not None
        ],
        "metrics": [{"name": metric["name"], "unit": metric["unit"]}],
        "evidence_contract": {
            "metric_observations": [{"name": metric["name"], "unit": metric["unit"]}]
        },
        "applicability_scope": {"scope_id": configured["evaluator"]["scope_id"]},
        "covers": list(observation["declared_obligations"]),
    }
    after_revision = evidence["source_revision"]
    exact_bundle = SimpleNamespace(
        representations=(copy.deepcopy(representation),),
        snapshot={"architecture": {"after_commit": after_revision}},
    )
    exact_result = exp04._strict_representation_mappings(
        run_dir=run_dir,
        exp02_bundle=bundle,
        evidence=evidence,
        configuration=configuration,
        p_bundle=exact_bundle,
    )
    exact_layering = next(
        item
        for item in exact_result
        if item["exp02_representation_id"] == observation["representation_id"]
    )
    assert exact_layering["admission_status"] == "validated_observation"
    assert set(exact_layering["binding_checks"].values()) <= {"exact", "not_applicable"}

    if mutation == "evaluator":
        representation["evaluator"] = "OTHER_EVALUATOR"
    elif mutation == "scope":
        representation["applicability_scope"]["scope_id"] = "other.scope"
    elif mutation == "stage":
        representation["stage"] = "runtime"
    elif mutation == "metric":
        representation["metrics"][0]["unit"] = "other-unit"
    elif mutation == "criterion_intent":
        representation["criterion_intent"] = "different intent"
    elif mutation == "source_digest":
        representation["source_artifacts"][0]["sha256"] = "0" * 64
    elif mutation == "metric_contract":
        representation["evidence_contract"]["metric_observations"][0]["name"] = "other_metric"
    elif mutation == "architecture_revision":
        after_revision = ALTERNATE_A0_1_REVISION

    p_bundle = SimpleNamespace(
        representations=(representation,),
        snapshot={"architecture": {"after_commit": after_revision}},
    )
    result = exp04._strict_representation_mappings(
        run_dir=run_dir,
        exp02_bundle=bundle,
        evidence=evidence,
        configuration=configuration,
        p_bundle=p_bundle,
    )
    layering = next(
        item
        for item in result
        if item["exp02_representation_id"] == observation["representation_id"]
    )

    assert layering["binding_checks"][check_name] == expected_status
    assert layering["admission_status"] == "mapping_unresolved"


def test_runtime_source_identity_must_be_verified(tmp_path: Path) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    bundle, evidence, configuration, _ = exp03._load_exp02(run_dir)
    runtime_observation = next(
        item for item in evidence["representations"] if item["lifecycle_stage"] == "runtime"
    )
    changed_evidence = copy.deepcopy(evidence)
    changed_observation = next(
        item
        for item in changed_evidence["representations"]
        if item["representation_id"] == runtime_observation["representation_id"]
    )
    changed_observation["evaluator_execution"]["runtime_source_binding_status"] = "unverified"
    configured = next(
        item
        for item in configuration["representations"]
        if item["id"] == runtime_observation["representation_id"]
    )
    p_bundle = SimpleNamespace(
        representations=(
            {
                "id": runtime_observation["representation_id"],
                "criterion": runtime_observation["criterion_id"],
                "stage": exp03.STAGE_TRANSLATIONS[runtime_observation["lifecycle_stage"]],
                "evaluator": configured["evaluator"]["id"],
                "covers": list(runtime_observation["declared_obligations"]),
            },
        ),
        snapshot={"architecture": {"after_commit": evidence["source_revision"]}},
    )

    result = exp04._strict_representation_mappings(
        run_dir=run_dir,
        exp02_bundle=bundle,
        evidence=changed_evidence,
        configuration=configuration,
        p_bundle=p_bundle,
    )
    runtime_row = next(
        item
        for item in result
        if item["exp02_representation_id"] == runtime_observation["representation_id"]
    )
    assert runtime_row["binding_checks"]["runtime_source_identity"] == "unrepresented"
    assert "RUNTIME_APPLICATION_SOURCE_IDENTITY_UNVERIFIED" in runtime_row["reason_codes"]


def test_digest_valid_contradictory_admission_manifest_fails_readback(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    output_dir = tmp_path / "exp04-output"
    exp04.write_admission_run(run_dir, output_dir, p_input_dir=p_input_dir)
    manifest_path = output_dir / exp04.MANIFEST_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["representation_admissions"][0]["admission_status"] = "admitted_execution_evidence"
    manifest_bytes = pretty_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    digest = sha256_bytes(manifest_bytes)
    (output_dir / exp04.MANIFEST_DIGEST_FILENAME).write_text(
        f"{digest}  {exp04.MANIFEST_FILENAME}\n", encoding="ascii"
    )

    with pytest.raises(ValueError, match="admission and consumption disagree"):
        exp04.validate_admission_output(output_dir)


@pytest.mark.parametrize(
    ("include_evaluator_evidence", "expected_status", "expected_consumption"),
    [
        pytest.param(
            False,
            "authorized_but_unconsumed_evidence",
            "not_consumed",
            id="authorized-but-unconsumed",
        ),
        pytest.param(
            True,
            "admitted_execution_evidence",
            "consumed",
            id="exact-pair-consumed",
        ),
    ],
)
def test_test_only_sidecar_admission_tracks_actual_pair_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    include_evaluator_evidence: bool,
    expected_status: str,
    expected_consumption: str,
) -> None:
    """An isolated TEST_ONLY sidecar's row status follows existing P pair consumption."""
    run_dir, _ = _write_exp02_run(tmp_path / "exp02")
    synthetic_root = tmp_path / "synthetic-p"
    synthetic_root.mkdir()
    p_bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        synthetic_root, architecture_noop=True
    )
    sidecar = _positive_adaptation_sidecar(
        p_bundle, trust_context, evaluator_artifact, synthetic_root
    )
    sidecar["payload"]["pair_proofs"] = []
    if not include_evaluator_evidence:
        sidecar["payload"]["evaluator_evidence"] = []
        sidecar["payload"]["artifact_bytes"] = []
    unsigned = {
        key: value for key, value in sidecar.items() if key not in {"sidecar_sha256", "signature"}
    }
    sidecar_digest = sha256_bytes(canonical_json_bytes(unsigned))
    sidecar["sidecar_sha256"] = sidecar_digest
    sidecar["signature"] = hmac.new(
        trust_context.adaptation_key, sidecar_digest.encode("ascii"), hashlib.sha256
    ).hexdigest()
    sidecar_path = tmp_path / "test-only-empty-evaluator-evidence.json"
    sidecar_path.write_bytes(pretty_json_bytes(sidecar))

    monkeypatch.setattr(
        exp03,
        "verify_method_p_input",
        lambda _path, **_kwargs: p_bundle,
    )
    original_mapping = exp04._strict_representation_mappings

    def isolated_test_mapping(**kwargs: Any) -> list[dict[str, Any]]:
        rows = original_mapping(**kwargs)
        row = next(
            item
            for item in rows
            if item["exp02_representation_id"] == "REP_A01_ARCH_INTERNAL_LAYERING_CI"
        )
        row["target_p_representation_id"] = "REP_A0_ARCH_CI_LAYERING"
        row["eligibility_status"] = "eligible"
        row["admission_status"] = "validated_observation"
        row["binding_checks"] = {
            key: "not_applicable" if key == "runtime_source_identity" else "exact"
            for key in row["binding_checks"]
        }
        row["reason_codes"] = []
        return rows

    monkeypatch.setattr(exp04, "_strict_representation_mappings", isolated_test_mapping)
    monkeypatch.setattr(
        exp04,
        "_sidecar_observation_match",
        lambda **_kwargs: (True, []),
    )

    manifest, _ = exp04.write_admission_run(
        run_dir,
        tmp_path / "exp04-test-only-empty-evidence",
        p_input_dir=p_bundle.root,
        evidence_sidecar_path=sidecar_path,
        trust_context=trust_context,
    )
    admission = _row(manifest, "REP_A01_ARCH_INTERNAL_LAYERING_CI")
    assert manifest["status"] == "completed_with_blockers"
    assert admission["eligibility_status"] == "eligible"
    assert admission["authorization_status"] == "authorized_test_only"
    assert admission["admission_status"] == expected_status
    assert admission["p_evidence_consumption_status"] == expected_consumption
    assert manifest["method_p"]["evidence_consumption_status"] == expected_consumption
    blocker_codes = {blocker["code"] for blocker in manifest["blockers"]}
    assert ("P_EVALUATOR_EVIDENCE_NOT_CONSUMED" in blocker_codes) is (
        expected_consumption == "not_consumed"
    )
    assert "TEST_ONLY_EVIDENCE_NOT_RESEARCH_AUTHORITY" in {
        blocker["code"] for blocker in manifest["blockers"]
    }
    trace = json.loads(
        (tmp_path / "exp04-test-only-empty-evidence" / exp04.P_TRACE_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert trace["exp02_evidence_admission_status"] == expected_status
    assert trace["exp02_evidence_admitted_to_p_calculations"] is (
        expected_consumption == "consumed"
    )
    assert trace["adaptation_evidence_sidecar_supplied"] is True
    assert trace["adaptation_evidence_trust_scope"] == "TEST_ONLY"


def test_resealed_accept_in_manifest_and_trace_is_rejected(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    output_dir = tmp_path / "exp04-resealed-accept"
    exp04.write_admission_run(run_dir, output_dir, p_input_dir=p_input_dir)

    def authorize_accept(manifest: dict[str, Any], trace: dict[str, Any]) -> None:
        manifest["method_p"]["governance_result"] = "ACCEPT"
        trace["governance"]["result"] = "ACCEPT"

    _reseal_manifest_and_trace(output_dir, authorize_accept)
    with pytest.raises((ValueError, ContractValidationError)):
        exp04.validate_admission_output(output_dir)


def test_resealed_prediction_and_candidate_publication_are_rejected(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    output_dir = tmp_path / "exp04-resealed-publication"
    exp04.write_admission_run(run_dir, output_dir, p_input_dir=p_input_dir)

    def publish_unauthorized_outputs(manifest: dict[str, Any], trace: dict[str, Any]) -> None:
        manifest["method_p"]["prediction_v1_emitted"] = True
        trace["prediction_v1"] = {"prediction_id": "TEST_ONLY_FORBIDDEN"}
        trace["candidate_v1"] = {"candidate_id": "TEST_ONLY_FORBIDDEN"}

    _reseal_manifest_and_trace(output_dir, publish_unauthorized_outputs)
    with pytest.raises((ValueError, ContractValidationError)):
        exp04.validate_admission_output(output_dir)


def test_resealed_completed_status_with_blockers_is_rejected(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    output_dir = tmp_path / "exp04-resealed-completion"
    exp04.write_admission_run(run_dir, output_dir, p_input_dir=p_input_dir)

    def claim_completion(manifest: dict[str, Any], _trace: dict[str, Any]) -> None:
        manifest["status"] = "completed"

    _reseal_manifest_and_trace(output_dir, claim_completion)
    with pytest.raises(ValueError, match="overall completion status contradicts"):
        exp04.validate_admission_output(output_dir)


def test_resealed_evidence_consumption_claim_without_sidecar_is_rejected(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    output_dir = tmp_path / "exp04-resealed-consumption"
    exp04.write_admission_run(run_dir, output_dir, p_input_dir=p_input_dir)

    def claim_unverified_consumption(manifest: dict[str, Any], trace: dict[str, Any]) -> None:
        manifest["method_p"]["evidence_consumption_status"] = "consumed"
        trace["exp02_evidence_admission_status"] = "admitted_execution_evidence"
        trace["exp02_evidence_admitted_to_p_calculations"] = True
        trace["current_pairs"][0]["evaluator_evidence_sha256"] = "f" * 64
        admission = manifest["representation_admissions"][0]
        admission["admission_status"] = "admitted_execution_evidence"
        admission["p_evidence_consumption_status"] = "consumed"

    _reseal_manifest_and_trace(output_dir, claim_unverified_consumption)
    with pytest.raises(ValueError, match="verified authorized sidecar pair"):
        exp04.validate_admission_output(output_dir)


def test_missing_or_invalid_external_verifier_never_consumes_sidecar(
    tmp_path: Path,
) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        tmp_path, architecture_noop=True
    )
    sidecar = _positive_adaptation_sidecar(bundle, trust_context, evaluator_artifact, tmp_path)

    unknown_verifier = copy.deepcopy(sidecar)
    unknown_verifier["verifier_id"] = "unregistered_exp04_test_verifier"
    _, missing_authority = exp03.run_verified_method_p(bundle, evidence_context=unknown_verifier)
    assert missing_authority is None

    invalid_signature = copy.deepcopy(sidecar)
    invalid_signature["signature"] = "invalid-test-signature"
    with pytest.raises(ContractValidationError, match="SIGNATURE_INVALID"):
        exp03.run_verified_method_p(bundle, evidence_context=invalid_signature)


def test_cli_verifier_configuration_is_pinned_and_test_only(tmp_path: Path) -> None:
    key_path = tmp_path / "test-only-key.bin"
    key_bytes = b"test-only-key-material-with-at-least-32-bytes"
    key_path.write_bytes(key_bytes)
    config_path = tmp_path / "verifier.json"
    config = {
        "schema_version": 1,
        "verifier_id": "EXP04_TEST_ONLY_VERIFIER",
        "trust_scope": "TEST_ONLY",
        "algorithm": exp04.HMAC_ALGORITHM,
        "key_file": str(key_path),
        "key_file_sha256": sha256_bytes(key_bytes),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    context, reference = exp04._external_trust_context(config_path)

    assert context.trust_scope == "TEST_ONLY"
    assert reference["trust_scope"] == "TEST_ONLY"
    assert reference["key_reference"]["sha256"] == sha256_bytes(key_bytes)
    assert key_bytes.decode("ascii") not in json.dumps(reference)

    config["trust_scope"] = "PRODUCTION"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ContractValidationError):
        exp04._external_trust_context(config_path)


def test_test_only_verified_evaluator_execution_without_pair_proof_is_not_valid(
    tmp_path: Path,
) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        tmp_path, architecture_noop=True
    )
    sidecar = _positive_adaptation_sidecar(bundle, trust_context, evaluator_artifact, tmp_path)
    sidecar["payload"]["pair_proofs"] = []
    unsigned = {
        key: value for key, value in sidecar.items() if key not in {"sidecar_sha256", "signature"}
    }
    digest = sha256_bytes(canonical_json_bytes(unsigned))
    sidecar["sidecar_sha256"] = digest
    sidecar["signature"] = hmac.new(
        trust_context.adaptation_key, digest.encode("ascii"), hashlib.sha256
    ).hexdigest()

    result, verified = exp03.run_verified_method_p(bundle, evidence_context=sidecar)
    pair = next(
        row
        for row in result.current_pairs
        if row.representation_id == "REP_A0_ARCH_CI_LAYERING" and row.obligation_id == "AC_LAYERING"
    )

    assert verified is not None
    assert verified.trust_scope == "TEST_ONLY"
    assert pair.evaluator_evidence_sha256 is not None
    assert pair.status is PairStatus.UNKNOWN
    assert pair.compliance_status is ComplianceStatus.COMPLIANT
    assert pair.semantic_proof_status == "UNDETERMINED"
    assert result.governance.result.value != "ACCEPT"


def test_noncompliance_and_evaluator_inadequacy_are_independent() -> None:
    evaluator_bytes = b"test-only evaluator bytes"
    observation_bytes = b"test-only evaluator output"
    architecture_sha = "a" * 40
    representation = {
        "id": "REP_A0_ARCH_CI_LAYERING",
        "criterion": "architecture_compliance",
        "stage": "ci",
        "evaluator": "arch_import_linter_v1",
        "evaluator_artifact": {
            "path": "evaluators/import_linter.py",
            "sha256": sha256_bytes(evaluator_bytes),
        },
        "covers": ["AC_LAYERING"],
    }
    evidence = {
        "schema_version": 1,
        "representation_id": representation["id"],
        "architecture_source_sha": architecture_sha,
        "evaluator_id": representation["evaluator"],
        "infrastructure_status": "completed",
        "process_exit_code": 1,
        "configured_targets": ["app.modules"],
        "resolved_targets": ["app.modules"],
        "inspected_subjects": ["app.modules"],
        "missing_targets": [],
        "inspected_edge_count": 1,
        "stage_applicable": True,
        "semantic_compatible": True,
        "mapping_resolved": True,
        "evidence_contract_satisfied": True,
        "adequacy_proven": False,
        "evidence_artifacts": [
            {"path": "outputs/import_linter.txt", "sha256": sha256_bytes(observation_bytes)}
        ],
        "stdout_sha256": sha256_bytes(observation_bytes),
        "stderr_sha256": sha256_bytes(b""),
    }

    pair = assess_pair(
        representation=representation,
        obligation={"id": "AC_LAYERING", "criterion": "architecture_compliance"},
        architecture_source_sha=architecture_sha,
        evaluator_evidence=evidence,
        semantic_proof=None,
        artifact_bytes={
            "evaluators/import_linter.py": evaluator_bytes,
            "outputs/import_linter.txt": observation_bytes,
        },
        source_digests={},
    )

    assert pair.compliance_status is ComplianceStatus.NON_COMPLIANT
    assert pair.status is PairStatus.UNKNOWN
    assert "EVALUATOR_ADEQUACY_NOT_PROVEN" in pair.reason_codes
    assert "PAIR_SEMANTIC_PROOF_MISSING" in pair.reason_codes


def test_existing_test_only_positive_p_path_remains_available(tmp_path: Path) -> None:
    bundle, trust_context, evaluator_artifact = _synthetic_positive_bundle(
        tmp_path, architecture_noop=True
    )
    sidecar = _positive_adaptation_sidecar(bundle, trust_context, evaluator_artifact, tmp_path)

    result, verified = exp03.run_verified_method_p(bundle, evidence_context=sidecar)

    assert verified is not None
    assert verified.trust_scope == "TEST_ONLY"
    assert result.governance.result.value == "ACCEPT"
