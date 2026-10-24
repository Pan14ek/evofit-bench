"""Integrity and replay checks for the synthetic Method P decision experiment."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.p_adaptation import run_adaptation, verify_v3_p_bundle
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3
from experiments.pilots.mono_e1_dev_p_decisions_v1 import runner
from tests.integration import test_p_applicability_v3 as fixtures


def _scenario(scenario_id: str) -> dict[str, Any]:
    catalog = runner.validate_scenario_catalog()
    return next(row for row in catalog["scenarios"] if row["scenario_id"] == scenario_id)


def _prepare(tmp_path: Path, scenario_id: str) -> tuple[Any, Any, bytes, dict[str, Any] | None]:
    scenario = _scenario(scenario_id)
    bundle, trust_context, evaluator_artifact = fixtures._synthetic_positive_bundle(
        tmp_path,
        **runner._fixture_arguments(scenario),
    )
    sidecar, _ = runner._prepare_sidecar(
        scenario,
        bundle,
        trust_context,
        evaluator_artifact,
        tmp_path / "sidecar-evaluator",
    )
    return bundle, trust_context, evaluator_artifact, sidecar


def _verified(bundle: Any, trust_context: Any, bundle_root: Path | None = None) -> Any:
    return verify_v3_p_bundle(
        bundle_root or bundle.root,
        evidence_ledger=bundle.evidence_ledger,
        trust_context=trust_context,
        fact_verifier=fixtures._synthetic_fact_verifier,
        completeness_verifier=fixtures._synthetic_completeness_verifier,
    )


def test_scenarios_match_strict_schema_and_have_unique_ids() -> None:
    catalog = runner.validate_scenario_catalog()
    assert len(catalog["scenarios"]) == 8
    assert {row["scenario_id"] for row in catalog["scenarios"]} == runner.EXPECTED_SCENARIO_IDS
    assert all("expected_operation" not in row for row in catalog["scenarios"])


def test_author_declared_reference_is_frozen_and_read_back() -> None:
    reference, digest = runner._expected_reference()
    assert digest == runner._sha256(runner.REFERENCE_PATH)
    assert len(reference) == 8
    assert all(case.get("scenario_id") for case in reference.values())
    assert all(case.get("not_justified_if") for case in reference.values())


def test_scorer_reference_is_absent_from_verified_method_inputs(tmp_path: Path) -> None:
    bundle, trust_context, _artifact, sidecar = _prepare(tmp_path, "A1")
    preserved = tmp_path / "preserved-method-input"
    shutil.copytree(bundle.root, preserved)
    manifest = verify_method_bundle_v3(preserved, expected_method_id="P")
    paths = [str(row["path"]) for row in manifest["files"]]
    assert not any("reference_v1" in path.lower() for path in paths)
    contents = b"\n".join(path.read_bytes() for path in preserved.rglob("*") if path.is_file())
    assert runner.REFERENCE_PATH.read_bytes() not in contents
    assert b"expected_operation" not in contents
    assert b"scenario_id" not in contents
    assert sidecar is not None
    sidecar_bytes = json.dumps(sidecar, sort_keys=True).encode()
    assert runner.REFERENCE_PATH.read_bytes() not in sidecar_bytes
    assert b"expected_operation" not in sidecar_bytes
    assert b"scenario_id" not in sidecar_bytes
    assert _verified(bundle, trust_context, preserved).trust_scope == "TEST_ONLY"


def test_archived_input_bundle_round_trips_through_v3_verification(tmp_path: Path) -> None:
    bundle, _trust_context, _artifact, _sidecar = _prepare(tmp_path, "A1")
    source_manifest = verify_method_bundle_v3(bundle.root, expected_method_id="P")
    archive_path = tmp_path / "A1_method_input_v3.zip"
    archive_digest = runner._archive_method_bundle(bundle.root, archive_path)
    extracted = tmp_path / "extracted-method-input"
    extracted.mkdir()
    with ZipFile(archive_path) as archive:
        archive.extractall(extracted)
    extracted_manifest = verify_method_bundle_v3(extracted, expected_method_id="P")
    assert archive_digest == runner._sha256(archive_path)
    assert extracted_manifest["bundle_sha256"] == source_manifest["bundle_sha256"]


def test_verified_replay_is_deterministic_for_fixed_input(tmp_path: Path) -> None:
    bundle, trust_context, _artifact, sidecar = _prepare(tmp_path, "A1")
    verified = _verified(bundle, trust_context)
    first = run_adaptation(verified, evidence_context=sidecar)
    replay = run_adaptation(verified, evidence_context=sidecar)
    assert first.evidence_trust_scope == replay.evidence_trust_scope == "TEST_ONLY"
    assert first.operation_plan.plan_sha256 == replay.operation_plan.plan_sha256
    assert first.candidate_sha256 == replay.candidate_sha256
    assert (
        first.governance.to_dict()["decision_sha256"]
        == replay.governance.to_dict()["decision_sha256"]
    )
    assert first.operation_plan.operations[0].operation.value == "retain"
    assert first.governance.result.value == "ACCEPT"


def test_policy_activation_adds_only_after_state(tmp_path: Path) -> None:
    bundle, trust_context, _artifact, sidecar = _prepare(tmp_path, "B2")
    result = run_adaptation(_verified(bundle, trust_context), evidence_context=sidecar)
    before = {row.obligation_id: row.status.value for row in result.before_applicability.results}
    after = {row.obligation_id: row.status.value for row in result.after_applicability.results}
    assert before["AC_LAYERING"] == "INACTIVE"
    assert after["AC_LAYERING"] == "ACTIVE"
    assert [row.operation.value for row in result.operation_plan.operations] == ["add"]
    assert result.governance.result.value == "ACCEPT"
    assert result.candidate_coverage is not None
    assert result.candidate_coverage.status.value == "COMPLETE"


@pytest.mark.parametrize("scenario_id", ["C1", "C2"])
def test_semantically_invalid_parent_is_replaced_only_with_exact_successor_evidence(
    tmp_path: Path,
    scenario_id: str,
) -> None:
    scenario_root = tmp_path / scenario_id
    scenario_root.mkdir()
    bundle, trust_context, _artifact, sidecar = _prepare(scenario_root, scenario_id)
    result = run_adaptation(_verified(bundle, trust_context), evidence_context=sidecar)
    assert [row.operation.value for row in result.operation_plan.operations] == ["replace"]
    assert result.operation_plan.hold_reasons == ()
    assert result.governance.result.value == "ACCEPT"
    assert result.candidate_coverage is not None
    assert result.candidate_coverage.status.value == "COMPLETE"
    pair = next(
        row for row in result.current_pairs if row.representation_id == "REP_A0_ARCH_CI_LAYERING"
    )
    assert pair.status.value == "INVALID"


def test_missing_semantic_evidence_remains_hold_and_unknown(tmp_path: Path) -> None:
    bundle, trust_context, _artifact, sidecar = _prepare(tmp_path, "D1")
    assert sidecar is None
    result = run_adaptation(_verified(bundle, trust_context), evidence_context=None)
    assert result.governance.result.value == "HOLD"
    assert not result.operation_plan.reject_reasons
    assert result.operation_plan.hold_reasons
    assert any(row.status.value == "UNKNOWN" for row in result.current_pairs)
    assert result.candidate_v1 is None
    assert result.prediction_v1 is None


def test_stale_before_revision_evidence_cannot_retain_or_replace(tmp_path: Path) -> None:
    bundle, trust_context, _artifact, sidecar = _prepare(tmp_path, "D2")
    assert sidecar is not None
    assert (
        sidecar["payload"]["evaluator_evidence"][0]["evidence"]["architecture_source_sha"]
        == (bundle.snapshot["architecture"]["before_commit"])
    )
    result = run_adaptation(_verified(bundle, trust_context), evidence_context=sidecar)
    assert result.governance.result.value == "REJECT"
    assert "INVARIANT_VIOLATION_PROVEN" in result.governance.to_dict()["reason_codes"]
    assert not result.operation_plan.operations
    assert "REPLACEMENT_NOT_MATERIALIZABLE" in result.operation_plan.hold_reasons
    assert any("ARCHITECTURE_REVISION_MISMATCH" in row.reason_codes for row in result.current_pairs)


def test_raw_output_digest_tampering_is_rejected(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    raw_file = output_dir / "raw/A1/method_p_rep_01.json"
    raw_file.parent.mkdir(parents=True)
    raw_file.write_text('{"result":"original"}\n', encoding="utf-8")
    runner._write_raw_manifest(output_dir / "raw")
    raw_file.write_text('{"result":"tampered"}\n', encoding="utf-8")
    with pytest.raises(ProtocolError, match="RAW_DIGEST_MISMATCH"):
        runner._verify_raw_manifest(output_dir)


def test_result_metadata_does_not_promote_scientific_status() -> None:
    assert (
        runner._method_identity(runner.EXPERIMENT_DIR.parents[2])["method_version"]
        == "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1"
    )
    assert runner.SCIENTIFIC_STATUS_EFFECT == "NONE"
    reference, _ = runner._expected_reference()
    assert all(
        runner.REFERENCE_PATH.read_bytes().find(case["expected_operation"].encode()) >= 0
        for case in reference.values()
    )
