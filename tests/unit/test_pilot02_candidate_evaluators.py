"""TEST_ONLY safeguards for PILOT-02 candidate evaluator attribution."""

from __future__ import annotations

import base64
import copy
import importlib.metadata
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.hashing import sha256_bytes
from experiments.execution.tooling.p_adaptation import (
    PILOT02_PROFILE_DEFINITION_PATH,
    PILOT02_PROFILE_DEFINITION_SHA256,
)
from experiments.pilots import run_pilot02_method_p as runner

ROOT = Path(__file__).resolve().parents[2]
SOURCE_REVISION = "test-source-revision"
AFTER_TREE_SHA = "test-after-tree-sha"
INPUT_BUNDLE_SHA256 = "test-input-bundle-sha256"


def _profile_and_candidate() -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a source-byte-bound profile and candidate with two exact template rows."""
    profile = json.loads((ROOT / PILOT02_PROFILE_DEFINITION_PATH).read_text(encoding="utf-8"))
    profile["architecture_source_sha"] = SOURCE_REVISION
    profile["a0_1_app_tree_sha"] = AFTER_TREE_SHA
    profile["profile_definition_artifact"] = {
        "path": PILOT02_PROFILE_DEFINITION_PATH,
        "sha256": PILOT02_PROFILE_DEFINITION_SHA256,
    }
    references: dict[str, str] = {
        PILOT02_PROFILE_DEFINITION_PATH: PILOT02_PROFILE_DEFINITION_SHA256
    }
    for mapping in profile["mappings"]:
        for reference in [
            mapping["configuration_artifact"],
            *mapping["evaluator_source_artifacts"],
            mapping["candidate_template"]["representation"]["evaluator_artifact"],
        ]:
            references[str(reference["path"])] = str(reference["sha256"])
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
    candidate = {
        "architecture_source_sha": SOURCE_REVISION,
        "input_bundle_sha256": INPUT_BUNDLE_SHA256,
        "candidate_validation": {"status": "failed", "reason_codes": ["inherited rows"]},
        "representations": [
            copy.deepcopy(mapping["candidate_template"]["representation"])
            for mapping in profile["mappings"]
        ],
    }
    return profile, candidate


@pytest.mark.parametrize(
    ("mismatch", "expected_reason"),
    [
        ("candidate_row_missing", "candidate_row_missing_or_duplicated"),
        ("candidate_row_duplicate", "candidate_row_missing_or_duplicated"),
        ("evaluator_id", "candidate_row_field_mismatch:evaluator"),
        ("artifact_path", "candidate_row_field_mismatch:evaluator_artifact"),
        ("artifact_digest", "candidate_row_field_mismatch:evaluator_artifact"),
        ("configuration_digest", "candidate_row_field_mismatch:evidence_contract"),
        ("configuration_artifact_digest", "profile_configuration_digest_mismatch"),
        ("source_revision", "candidate_source_revision_mismatch"),
        ("profile_source_revision", "profile_source_revision_mismatch"),
        ("source_tree", "profile_source_tree_mismatch"),
        ("scope_id", "candidate_row_field_mismatch:applicability_scope"),
        ("stage", "candidate_row_field_mismatch:stage"),
        ("covered_obligation", "candidate_row_field_mismatch:covers"),
        ("evidence_contract", "candidate_row_field_mismatch:evidence_contract"),
        ("contract_stage", "candidate_row_field_mismatch:evidence_contract"),
        ("mapping_scope", "profile_scope_or_obligation_binding_mismatch"),
        ("embedded_artifact_digest", "profile_artifact_digest_mismatch:"),
        ("embedded_artifact_bytes", "profile_artifact_source_unavailable:"),
        ("input_bundle", "candidate_input_bundle_mismatch"),
        ("profile_definition_digest", "profile_definition_digest_mismatch"),
    ],
)
def test_profile_binding_mismatch_prevents_candidate_evaluator_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
    expected_reason: str,
) -> None:
    """Do not execute or attribute output to a candidate row with any binding mismatch."""
    profile, candidate = _profile_and_candidate()
    profile["mappings"] = [profile["mappings"][0]]
    mapping = profile["mappings"][0]
    row = candidate["representations"][0]
    if mismatch == "candidate_row_missing":
        row["id"] = "REP_UNBOUND"
    elif mismatch == "candidate_row_duplicate":
        candidate["representations"].append(copy.deepcopy(row))
    elif mismatch == "evaluator_id":
        row["evaluator"] = "EV_UNBOUND"
    elif mismatch == "artifact_path":
        row["evaluator_artifact"]["path"] = "unbound.toml"
    elif mismatch == "artifact_digest":
        row["evaluator_artifact"]["sha256"] = "0" * 64
    elif mismatch == "configuration_digest":
        row["evidence_contract"]["configuration_artifact_sha256"] = "0" * 64
    elif mismatch == "configuration_artifact_digest":
        mapping["configuration_artifact"]["sha256"] = "0" * 64
    elif mismatch == "source_revision":
        candidate["architecture_source_sha"] = "other-revision"
    elif mismatch == "profile_source_revision":
        profile["architecture_source_sha"] = "other-revision"
    elif mismatch == "source_tree":
        profile["a0_1_app_tree_sha"] = "other-tree"
    elif mismatch == "scope_id":
        row["applicability_scope"]["scope_id"] = "unbound.scope"
    elif mismatch == "stage":
        row["stage"] = "runtime"
    elif mismatch == "covered_obligation":
        row["covers"] = ["AC_UNBOUND"]
    elif mismatch == "evidence_contract":
        row["evidence_contract"]["record_id"] = "unbound-record"
    elif mismatch == "contract_stage":
        row["evidence_contract"]["method_stage"] = "runtime"
    elif mismatch == "mapping_scope":
        mapping["source_scope_id"] = "unbound.scope"
    elif mismatch == "embedded_artifact_digest":
        profile["embedded_evaluator_artifacts"][0]["sha256"] = "0" * 64
    elif mismatch == "embedded_artifact_bytes":
        profile["embedded_evaluator_artifacts"][0]["content_base64"] = "%%%"
    elif mismatch == "input_bundle":
        candidate["input_bundle_sha256"] = "other-bundle"
    elif mismatch == "profile_definition_digest":
        profile["profile_definition_artifact"]["sha256"] = "0" * 64

    monkeypatch.setattr(
        runner,
        "_source_blob",
        lambda revision, path: (ROOT / path).read_bytes(),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("candidate evaluator ran after a binding mismatch"),
    )

    result = runner._run_profile_candidate_evaluators(
        tmp_path,
        profile,
        candidate,
        source_revision=SOURCE_REVISION,
        after_tree_sha=AFTER_TREE_SHA,
        input_bundle_sha256=INPUT_BUNDLE_SHA256,
    )

    record = result["representations"][0]
    assert record["status"] == "not_measured"
    assert record["reason_code"] == "CANDIDATE_PROFILE_BINDING_MISMATCH"
    assert expected_reason in record["candidate_profile_binding"]["reason_codes"] or any(
        reason.startswith(expected_reason)
        for reason in record["candidate_profile_binding"]["reason_codes"]
    )
    assert result["execution_count"] == 0
    assert result["status"] == "not_measured"
    assert candidate["candidate_validation"]["status"] == "failed"


def test_matched_profile_rows_run_even_when_full_candidate_validation_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scoped architecture measurements do not rewrite full candidate validation."""
    profile, candidate = _profile_and_candidate()
    calls: list[list[str]] = []

    monkeypatch.setattr(
        runner,
        "_source_blob",
        lambda revision, path: (ROOT / path).read_bytes(),
    )

    def fake_run(command: list[str], **kwargs: Any) -> Any:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"pass\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(importlib.metadata, "version", lambda package: "test-version")

    result = runner._run_profile_candidate_evaluators(
        tmp_path,
        profile,
        candidate,
        source_revision=SOURCE_REVISION,
        after_tree_sha=AFTER_TREE_SHA,
        input_bundle_sha256=INPUT_BUNDLE_SHA256,
    )

    assert len(calls) == result["execution_count"] == result["expected_evaluator_count"] == 2
    assert result["status"] == "measured"
    assert all(
        row["candidate_profile_binding"]["status"] == "matched" for row in result["representations"]
    )
    assert candidate["candidate_validation"]["status"] == "failed"
