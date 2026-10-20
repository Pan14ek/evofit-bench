"""Source-bound Method P input profile checks for the PILOT-02 DEVELOPMENT case."""

from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import sha256_bytes
from experiments.execution.tooling.p_adaptation import (
    PILOT02_PROFILE_DEFINITION_PATH,
    PILOT02_PROFILE_DEFINITION_SHA256,
    PILOT02_PROFILE_V2_DEFINITION_PATH,
    PILOT02_PROFILE_V2_DEFINITION_SHA256,
    _normalize_representation,
    _validate_pilot02_method_input_profile,
)
from experiments.pilots.run_pilot02_inherited_evaluators import (
    _representation_result,
    _verified_source_reference,
    _verify_run_artifact_digest,
)

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / PILOT02_PROFILE_DEFINITION_PATH


def _profile_input() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Build the exact source profile plus its digest-bound embedded file set."""
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["profile_definition_artifact"] = {
        "path": PILOT02_PROFILE_DEFINITION_PATH,
        "sha256": PILOT02_PROFILE_DEFINITION_SHA256,
    }
    references = [profile["profile_definition_artifact"]]
    references.extend(
        [profile["fitness_configuration_artifact"], profile["obligation_catalog_artifact"]]
    )
    for mapping in profile["mappings"]:
        references.extend(
            [
                mapping["configuration_artifact"],
                *mapping["evaluator_source_artifacts"],
                mapping["candidate_template"]["representation"]["evaluator_artifact"],
            ]
        )
    by_path = {row["path"]: row for row in references}
    profile["embedded_evaluator_artifacts"] = []
    for relative, reference in sorted(by_path.items()):
        content = (ROOT / relative).read_bytes()
        assert sha256_bytes(content) == reference["sha256"]
        profile["embedded_evaluator_artifacts"].append(
            {
                "path": relative,
                "size_bytes": len(content),
                "sha256": reference["sha256"],
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        )
    capabilities = {
        "generic_candidate_templates": [
            mapping["candidate_template"] for mapping in profile["mappings"]
        ]
    }
    catalog = yaml.safe_load((ROOT / "fitness/catalog/architectural-obligations.yaml").read_text())
    obligations = catalog["obligations"]
    manifest = {
        "architecture_source_sha": profile["architecture_source_sha"],
        "after_tree_sha": profile["a0_1_app_tree_sha"],
    }
    snapshot = {
        "architecture": {
            "before_commit": profile["architecture_before_sha"],
            "after_commit": profile["architecture_source_sha"],
        }
    }
    return profile, capabilities, {"manifest": manifest, "snapshot": snapshot}, obligations


def test_profile_verifies_exact_source_configuration_and_evaluator_bytes() -> None:
    profile, capabilities, bindings, obligations = _profile_input()

    artifacts = _validate_pilot02_method_input_profile(
        profile,
        capabilities=capabilities,
        manifest=bindings["manifest"],
        snapshot=bindings["snapshot"],
        obligations=obligations,
    )

    assert set(artifacts) == {row["path"] for row in profile["embedded_evaluator_artifacts"]}
    assert len(profile["mappings"]) == 2


def test_profile_rejects_a_resealed_mapping_outside_its_pinned_definition() -> None:
    profile, capabilities, bindings, obligations = _profile_input()
    profile = copy.deepcopy(profile)
    profile["mappings"][0]["source_scope_id"] = "architecture.unreviewed_scope"
    capabilities["generic_candidate_templates"] = [
        mapping["candidate_template"] for mapping in profile["mappings"]
    ]

    with pytest.raises(
        ProtocolError,
        match="P03_PILOT02_(CANONICAL_BINDING|PROFILE_DEFINITION)_MISMATCH",
    ):
        _validate_pilot02_method_input_profile(
            profile,
            capabilities=capabilities,
            manifest=bindings["manifest"],
            snapshot=bindings["snapshot"],
            obligations=obligations,
        )


def test_profile_rejects_missing_digest_bound_evaluator_bytes() -> None:
    profile, capabilities, bindings, obligations = _profile_input()
    profile["embedded_evaluator_artifacts"].pop()

    with pytest.raises(ProtocolError, match="P03_PILOT02_EMBEDDED_ARTIFACT_INVENTORY_MISMATCH"):
        _validate_pilot02_method_input_profile(
            profile,
            capabilities=capabilities,
            manifest=bindings["manifest"],
            snapshot=bindings["snapshot"],
            obligations=obligations,
        )


def _profile_v2_input() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    str,
]:
    """Build V2's exact pinned profile, parent rows, and embedded source artifact bytes."""
    profile = json.loads(
        (ROOT / "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json").read_text(
            encoding="utf-8"
        )
    )
    profile["profile_definition_artifact"] = {
        "path": PILOT02_PROFILE_V2_DEFINITION_PATH,
        "sha256": PILOT02_PROFILE_V2_DEFINITION_SHA256,
    }
    references = {
        PILOT02_PROFILE_V2_DEFINITION_PATH: PILOT02_PROFILE_V2_DEFINITION_SHA256,
        profile["fitness_configuration_artifact"]["path"]: profile[
            "fitness_configuration_artifact"
        ]["sha256"],
        profile["obligation_catalog_artifact"]["path"]: profile["obligation_catalog_artifact"][
            "sha256"
        ],
        profile["parent_representation_catalog_artifact"]["path"]: profile[
            "parent_representation_catalog_artifact"
        ]["sha256"],
    }
    for mapping in profile["mappings"]:
        for reference in [
            mapping["configuration_artifact"],
            *mapping["evaluator_source_artifacts"],
            mapping["candidate_template"]["representation"]["evaluator_artifact"],
        ]:
            references[reference["path"]] = reference["sha256"]
    for binding in profile["parent_evaluator_bindings"]:
        for reference in [
            binding["evaluator_artifact"],
            *binding["evaluator_source_artifacts"],
        ]:
            references[reference["path"]] = reference["sha256"]
    profile["embedded_evaluator_artifacts"] = []
    for path, digest in sorted(references.items()):
        content = (ROOT / path).read_bytes()
        assert sha256_bytes(content) == digest
        profile["embedded_evaluator_artifacts"].append(
            {
                "path": path,
                "size_bytes": len(content),
                "sha256": digest,
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        )
    capabilities = {
        "generic_candidate_templates": [
            mapping["candidate_template"] for mapping in profile["mappings"]
        ]
    }
    obligations = yaml.safe_load(
        (ROOT / "fitness/catalog/architectural-obligations.yaml").read_text(encoding="utf-8")
    )["obligations"]
    parent_catalog = yaml.safe_load(
        (ROOT / profile["parent_representation_catalog_artifact"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    parent_representations = [
        _normalize_representation(row) for row in parent_catalog["representations"]
    ]
    bindings = {
        "manifest": {
            "architecture_source_sha": profile["architecture_source_sha"],
            "after_tree_sha": profile["a0_1_app_tree_sha"],
        },
        "snapshot": {
            "architecture": {
                "before_commit": profile["architecture_before_sha"],
                "after_commit": profile["architecture_source_sha"],
            }
        },
    }
    return (
        profile,
        capabilities,
        bindings["manifest"],
        bindings["snapshot"],
        obligations,
        parent_representations,
        profile["parent_representation_catalog_sha256"],
    )


def test_profile_v2_verifies_all_parent_evaluator_artifacts() -> None:
    (
        profile,
        capabilities,
        manifest,
        snapshot,
        obligations,
        parent_representations,
        parent_digest,
    ) = _profile_v2_input()

    artifacts = _validate_pilot02_method_input_profile(
        profile,
        capabilities=capabilities,
        manifest=manifest,
        snapshot=snapshot,
        obligations=obligations,
        parent_representations=parent_representations,
        parent_configuration_sha256=parent_digest,
    )

    assert {row["representation_id"] for row in profile["parent_evaluator_bindings"]} == {
        "REP_A0_PERF_TEST_HTTP_P95",
        "REP_A0_PERF_RUNTIME_HTTP_DURATION",
        "REP_A0_REL_TEST_INTEGRATION",
        "REP_A0_REL_RUNTIME_FAILURES",
    }
    assert set(artifacts) == {row["path"] for row in profile["embedded_evaluator_artifacts"]}


def test_profile_v2_rejects_parent_binding_for_unknown_row() -> None:
    profile, capabilities, manifest, snapshot, obligations, parent_rows, digest = (
        _profile_v2_input()
    )
    profile["parent_evaluator_bindings"][0]["representation_id"] = "REP_NOT_IN_PARENT"

    with pytest.raises(ProtocolError, match="P03_PILOT02_PARENT_BINDING_IDENTITY_MISMATCH"):
        _validate_pilot02_method_input_profile(
            profile,
            capabilities=capabilities,
            manifest=manifest,
            snapshot=snapshot,
            obligations=obligations,
            parent_representations=parent_rows,
            parent_configuration_sha256=digest,
        )


def test_profile_v2_rejects_different_parent_catalog_digest() -> None:
    profile, capabilities, manifest, snapshot, obligations, parent_rows, digest = (
        _profile_v2_input()
    )

    with pytest.raises(ProtocolError, match="P03_PILOT02_PARENT_BINDING_BASELINE_MISMATCH"):
        _validate_pilot02_method_input_profile(
            profile,
            capabilities=capabilities,
            manifest=manifest,
            snapshot=snapshot,
            obligations=obligations,
            parent_representations=parent_rows,
            parent_configuration_sha256="0" * 64 if digest != "0" * 64 else "1" * 64,
        )


def test_inherited_evaluator_result_binds_source_config_and_raw_streams() -> None:
    profile = json.loads(
        (ROOT / "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json").read_text(
            encoding="utf-8"
        )
    )
    command_record = {
        "started_at_utc": "2026-10-20T10:00:00Z",
        "ended_at_utc": "2026-10-20T10:00:01Z",
        "duration_ns": 1_000_000_000,
        "exit_status": 0,
        "stdout": {"path": "raw/locust.stdout.bin", "sha256": "a" * 64},
        "stderr": {"path": "raw/locust.stderr.bin", "sha256": "b" * 64},
    }

    result = _representation_result(
        run_id="pilot02-inherited-unit",
        representation_id="REP_A0_PERF_TEST_HTTP_P95",
        source_revision="c" * 40,
        architecture_source_sha=profile["a0_1_source_basis_sha"],
        command_record=command_record,
        command=["python", "-m", "locust"],
        evaluator_version="2.46.6",
        configuration_artifact={"path": "raw/locust.json", "sha256": "d" * 64},
        metric_value=12.5,
        metric_unit="ms",
        metric_details={"request_count": 10},
        evaluation_status="NOT_EVALUATED",
        execution_status="measured",
        source_provenance_status="container_identity_unverified",
        raw_output_artifacts=[],
    )

    binding = next(
        row
        for row in profile["parent_evaluator_bindings"]
        if row["representation_id"] == "REP_A0_PERF_TEST_HTTP_P95"
    )
    assert result["source_artifact_path"] == binding["evaluator_artifact"]["path"]
    assert result["source_artifact_sha256"] == binding["evaluator_artifact"]["sha256"]
    assert result["configuration_artifact_sha256"] == "d" * 64
    assert result["raw_stdout_sha256"] == "a" * 64
    assert result["raw_stderr_sha256"] == "b" * 64
    assert result["metric_value"] == 12.5
    assert result["evaluation_status"] == "NOT_EVALUATED"


def test_inherited_evaluator_source_reference_rejects_digest_and_path_mismatch() -> None:
    profile = json.loads(
        (ROOT / "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json").read_text(
            encoding="utf-8"
        )
    )
    reference = profile["parent_evaluator_bindings"][0]["evaluator_artifact"]

    assert _verified_source_reference(reference)["sha256"] == reference["sha256"]
    with pytest.raises(ValueError, match="source artifact digest mismatch"):
        _verified_source_reference({**reference, "sha256": "0" * 64})
    with pytest.raises(ValueError, match="path escapes the checkout"):
        _verified_source_reference({"path": "../../outside", "sha256": "0" * 64})


def test_inherited_evaluator_readback_rejects_tampered_raw_output(tmp_path: Path) -> None:
    raw_output = tmp_path / "raw/stdout.bin"
    raw_output.parent.mkdir()
    raw_output.write_bytes(b"original evaluator output")
    reference = {
        "path": "raw/stdout.bin",
        "sha256": sha256_bytes(raw_output.read_bytes()),
    }

    assert _verify_run_artifact_digest(tmp_path, reference) == raw_output
    raw_output.write_bytes(b"tampered evaluator output")
    with pytest.raises(ValueError, match="run artifact digest mismatch"):
        _verify_run_artifact_digest(tmp_path, reference)
