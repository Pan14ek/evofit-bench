"""Synthetic checks for MONO-E1 comparability preparation only."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.hashing import bundle_sha256
from experiments.execution.tooling.mono_e1_preflight import (
    MANIFEST_PATH,
    SCHEMA_NAME,
    _verify_arm_inputs,
    _verify_capabilities,
    _verify_image_bindings,
    _verify_measurement_contract,
    _verify_method_identities,
    _verify_shared_input_identity,
    _verify_workload_and_fixture,
    build_current_preflight_manifest,
    verify_mono_e1_preflight,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def current_manifest() -> dict[str, Any]:
    return build_current_preflight_manifest(ROOT)


def test_current_preflight_is_validly_incomplete_and_non_authoritative(
    current_manifest: dict[str, Any],
) -> None:
    validate_payload(SCHEMA_NAME, current_manifest)
    report = verify_mono_e1_preflight(MANIFEST_PATH, repository=ROOT)

    assert report["preparation_status"] == "INCOMPLETE"
    assert report["invalid_reasons"] == []
    assert report["experimental_go"] == "NO_GO"
    assert report["measured_run_status"] == "NOT_EXECUTED"
    assert report["scientific_readiness"] == "NOT_ESTABLISHED"
    assert report["non_authoritative"] is True


def test_different_target_source_shas_fail_closed(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    manifest["arms"]["B0"]["target_source_sha"] = "a" * 40
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_shared_input_identity(manifest, invalid, incomplete)

    assert "B0_P_SHARED_INPUT_MISMATCH:target_source_sha" in invalid
    assert "B0_TARGET_SOURCE_NOT_CANONICAL_A04" in invalid


def test_workload_digest_mismatch_is_detected(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    manifest["arms"]["P"]["workload_spec_sha256"] = "0" * 64
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_workload_and_fixture(manifest, ROOT, invalid, incomplete, {})

    assert "P_WORKLOAD_DIGEST_MISMATCH" in invalid


def test_unverified_workload_repeatability_is_incomplete(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_workload_and_fixture(manifest, ROOT, invalid, incomplete, {})

    assert "COMMON_WORKLOAD_REPEATABILITY_NOT_ESTABLISHED" in incomplete


def test_fixture_and_migration_identity_mismatches_are_detected(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    manifest["arms"]["P"]["database_fixture_sha256"] = "f" * 64
    manifest["arms"]["P"]["migration_revision"] = "0002_other_schema"
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_shared_input_identity(manifest, invalid, incomplete)
    _verify_workload_and_fixture(manifest, ROOT, invalid, incomplete, {})

    assert "B0_P_SHARED_INPUT_MISMATCH:database_fixture_sha256" in invalid
    assert "P_FIXTURE_DIGEST_MISMATCH" in invalid
    assert "P_MIGRATION_REVISION_MISMATCH" in invalid


def test_missing_required_evaluator_capability_is_incomplete(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    manifest["common_inputs"]["evaluator_capabilities"]["required_ids"] = [
        "architecture.module_graph"
    ]
    manifest["arms"]["B0"]["evaluator_capability_ids"] = ["architecture.module_graph"]
    manifest["arms"]["P"]["evaluator_capability_ids"] = []
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_capabilities(manifest, incomplete, invalid)

    assert "MISSING_EVALUATOR_CAPABILITIES:architecture.module_graph" in incomplete


def test_missing_allowlist_remains_incomplete(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_arm_inputs(manifest, invalid, incomplete, {}, None)

    assert "B0_ALLOWLIST_MISSING" in incomplete
    assert "P_ALLOWLIST_MISSING" in incomplete


def test_malformed_allowlist_digest_is_invalid(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    inventory = manifest["arms"]["B0"]["input_inventory"]
    inventory["shared_inputs"] = [
        {
            "path": "fitness/config.yaml",
            "role": "configuration",
            "size_bytes": 1,
            "sha256": "a" * 64,
        }
    ]
    inventory["allowlist_sha256"] = "b" * 64
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_arm_inputs(manifest, invalid, incomplete, {}, None)

    assert "B0_ALLOWLIST_DIGEST_MISMATCH" in invalid


@pytest.mark.parametrize(
    "path",
    [
        "private/scorer/reference.json",
        "run/outputs/P/predictions.json",
        "method_p_outputs/predictions.json",
    ],
)
def test_reference_or_cross_arm_path_leakage_is_invalid(
    current_manifest: dict[str, Any], path: str
) -> None:
    manifest = deepcopy(current_manifest)
    inventory = manifest["arms"]["B0"]["input_inventory"]
    entry = {"path": path, "role": "fixture", "size_bytes": 1, "sha256": "a" * 64}
    inventory["shared_inputs"] = [entry]
    inventory["allowlist_sha256"] = bundle_sha256([entry])
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_arm_inputs(manifest, invalid, incomplete, {}, None)

    assert any(reason.startswith("B0_FORBIDDEN_INPUT_PATH:") for reason in invalid)


def test_structural_image_record_without_external_verifier_stays_unverified(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    for arm in ("B0", "P"):
        manifest["arms"][arm]["image_provenance"] = {
            "status": "STRUCTURALLY_VALID",
            "image_digest": "sha256:" + "a" * 64,
            "source_sha": manifest["arms"][arm]["target_source_sha"],
            "attestation_sha256": "b" * 64,
            "external_verifier_id": "synthetic-verifier",
            "verification_evidence_sha256": "c" * 64,
        }
        manifest["runner"]["container_image_digests"][arm] = "sha256:" + "a" * 64
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_image_bindings(manifest, None, invalid, incomplete, {})

    assert invalid == []
    assert "B0_SOURCE_TO_IMAGE_VERIFIER_EVIDENCE_MISSING" in incomplete
    assert "P_SOURCE_TO_IMAGE_VERIFIER_EVIDENCE_MISSING" in incomplete


def test_incompatible_timing_boundary_is_invalid(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    manifest["measurement_contract"]["arm_measurements"]["P"]["timing_boundary_id"] = (
        "OTHER_BOUNDARIES_V1"
    )
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_measurement_contract(manifest, invalid, incomplete, {})

    assert "P_TIMING_BOUNDARY_INCOMPATIBLE" in invalid


def test_uncollected_cpu_and_rss_remain_null(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_measurement_contract(manifest, invalid, incomplete, {})

    for arm in ("B0", "P"):
        metrics = manifest["measurement_contract"]["arm_measurements"][arm]["resource_metrics"]
        assert metrics["cpu_time_ns"] == {"status": "NOT_COLLECTED", "value": None}
        assert metrics["peak_rss_bytes"] == {"status": "NOT_COLLECTED", "value": None}
    assert invalid == []


def test_pending_authority_never_becomes_pass_or_go(
    current_manifest: dict[str, Any],
) -> None:
    report = verify_mono_e1_preflight(MANIFEST_PATH, repository=ROOT)

    assert current_manifest["authority"]["G1"] == "INCOMPLETE"
    assert current_manifest["authority"]["G4"] == "NOT_AUTHORIZED"
    assert report["preparation_status"] != "STRUCTURALLY_VALID"
    assert report["experimental_go"] == "NO_GO"


def test_tampered_b0_source_and_p_configuration_digests_are_invalid(
    current_manifest: dict[str, Any],
) -> None:
    manifest = deepcopy(current_manifest)
    manifest["arms"]["B0"]["method_identity"]["source_inventory"][0]["sha256"] = "0" * 64
    manifest["arms"]["P"]["method_identity"]["candidate_manifest"]["configuration_sha256"] = (
        "1" * 64
    )
    invalid: list[str] = []
    incomplete: list[str] = []

    _verify_method_identities(manifest, ROOT, invalid, incomplete)

    assert any(reason.startswith("B0_SOURCE_DIGEST_MISMATCH:") for reason in invalid)
    assert "P_CANDIDATE_SOURCE_OR_CONFIGURATION_DIGEST_MISMATCH" in invalid
