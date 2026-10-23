"""Guard the non-authoritative MONO-E1 A0.3 configuration lineage candidate."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "docs" / "mono_e1_a03_fitness_configuration_candidate_v1.json"
A03_SHA = "26a9bb667da7d0938e38aca15d2bf29fd1de4829"
GIT_EXECUTABLE = shutil.which("git")


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _bytes_at_a03(path: str) -> bytes:
    if GIT_EXECUTABLE is None:
        raise RuntimeError("Git is required to verify the canonical A0.3 source bytes")
    output = subprocess.run(  # noqa: S603 - fixed Git executable, argument list, and no shell
        [GIT_EXECUTABLE, "show", f"{A03_SHA}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return output.stdout


def _load_yaml_at_a03(path: str) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(_bytes_at_a03(path).decode("utf-8")))


def test_candidate_keeps_a0_b0_separate_from_a03_engineering_controls() -> None:
    spec = _load_json(SPEC_PATH)
    baseline = spec["frozen_a0_b0_configuration"]
    parent = spec["historical_fitness_configuration"]
    controls = spec["development_candidate_controls"]

    assert spec["status"] == "DEVELOPMENT_ONLY_CANDIDATE_NOT_HISTORICAL"
    assert parent["a03_configuration_status"] == "NOT_IDENTIFIED"
    assert parent["a03_parent_fitness_configuration_sha256"] is None
    assert parent["a03_parent_representation_ids"] is None
    assert parent["retain_reference_status"].startswith("NOT_EVALUABLE")

    assert baseline["architecture_state"] == "A0_MONOLITH"
    assert baseline["source_revision"] == "b78b0967be937634b7762baccf5ac6892b279a73"
    assert baseline["frozen_evaluator"]["representation_id"] == "REP_A0_ARCH_CI_LAYERING"
    assert baseline["a03_applicability_of_frozen_representation"] == "UNKNOWN"

    manifest = _load_yaml_at_a03("architecture/states/A0_3_GOVERNED_MODULE_GRAPH.yaml")
    assert manifest["governance_requirements"]["required_evaluators"] == [
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
    ]
    assert [row["evaluator_id"] for row in controls] == [
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
    ]
    assert all(row["representation_id"] is None for row in controls)
    assert all(row["stage_binding"] is None for row in controls)
    assert all(row["semantic_pair_status"] == "UNREVIEWED" for row in controls)
    assert spec["method_input_authorized"] is False
    assert spec["scientific_approval"] is False


def test_candidate_controls_match_a03_checkpoint_and_historical_bytes() -> None:
    spec = _load_json(SPEC_PATH)
    source = spec["provenance"]["canonical_a03_source"]
    checkpoint_ref = spec["provenance"]["canonical_a03_evaluator_readback"]
    checkpoint_path = ROOT / checkpoint_ref["checkpoint"]
    checkpoint_bytes = checkpoint_path.read_bytes()
    checkpoint = cast(dict[str, Any], json.loads(checkpoint_bytes))

    assert source["commit"] == A03_SHA
    assert checkpoint_ref["checkpoint_sha256"] == hashlib.sha256(checkpoint_bytes).hexdigest()
    assert checkpoint["source_sha"] == A03_SHA
    assert checkpoint["repository_tree_sha"] == source["repository_tree"]
    assert checkpoint["application_tree_sha"] == source["application_tree"]
    assert checkpoint["readback_status"] == "PASS"

    for artifact in checkpoint_ref["evaluator_source_artifacts"]:
        assert hashlib.sha256(_bytes_at_a03(artifact["path"])).hexdigest() == artifact["sha256"]

    state_manifest = _bytes_at_a03("architecture/states/A0_3_GOVERNED_MODULE_GRAPH.yaml")
    assert hashlib.sha256(state_manifest).hexdigest() == source["state_manifest_sha256"]

    for path, digest in (
        (
            "fitness/configs/a0-monolith.yaml",
            spec["frozen_a0_b0_configuration"]["configuration_sha256"],
        ),
        (
            "fitness/catalog/a0-fitness-elements.yaml",
            spec["frozen_a0_b0_configuration"]["representation_catalog_sha256"],
        ),
        (
            "fitness/traceability/a0-traceability.yaml",
            spec["frozen_a0_b0_configuration"]["traceability_sha256"],
        ),
    ):
        assert hashlib.sha256(_bytes_at_a03(path)).hexdigest() == digest

    for control in spec["development_candidate_controls"]:
        observed = checkpoint["evaluators"][control["evaluator_id"]]
        assert control["configuration_sha256"] == observed["configuration_sha256"]
        assert control["evaluator_source_digest"] == observed["evaluator_sha256"]
        assert control["observation_sha256"] == observed["evidence_file_sha256"]
        assert control["observed_execution_status"] == observed["execution_status"]
        assert control["observed_compliance"] == observed["compliance"]
        assert control["source_scope_complete"] == observed["source_scope_complete"]
        assert control["inspected_python_files"] == observed["inspected_files"]
        assert control["inspected_import_nodes"] == observed["inspected_imports"]
        assert (
            hashlib.sha256(_bytes_at_a03(control["configuration_path"])).hexdigest()
            == (control["configuration_sha256"])
        )
