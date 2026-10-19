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
    _validate_pilot02_method_input_profile,
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
