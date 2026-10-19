"""Bounds and verifies the PILOT-02 TEST_ONLY continuation source."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from experiments.execution.tooling.hashing import sha256_bytes
from experiments.execution.tooling.p_input_validation import SourceReference
from experiments.pilots.pilot02_testonly_execution import create_testonly_policy_source

ROOT = Path(__file__).resolve().parents[2]
POLICY_SOURCE = ROOT / "experiments/execution/policy-pilot/v1/source"
TARGET_IDS = ["AC_LAYERING", "AC_MODULE_STRUCTURE"]
BEFORE_SHA = "b78b0967be937634b7762baccf5ac6892b279a73"
AFTER_SHA = "3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306"
CATALOG_SHA = "8c5bd8fffe3bdb2af8fb85f8d0012bc34673f72866e52daed99fab96f9763011"
AS_OF = "2026-10-14T00:00:00Z"


def _create_source(tmp_path: Path) -> tuple[Path, Any]:
    """Build the same isolated source shape used by the prospective run."""
    return create_testonly_policy_source(
        POLICY_SOURCE,
        tmp_path,
        evaluation_as_of=AS_OF,
        before_sha=BEFORE_SHA,
        after_sha=AFTER_SHA,
        obligation_catalog_sha256=CATALOG_SHA,
        target_obligation_ids=TARGET_IDS,
    )


def _reference(source_id: str, path: Path, kind: str) -> SourceReference:
    content = path.read_bytes()
    return SourceReference(
        source_id=source_id,
        kind=kind,
        path=path.relative_to(path.parents[4]).as_posix(),
        sha256=sha256_bytes(content),
        content=content,
    )


def test_source_is_isolated_and_limited_to_declared_obligations(tmp_path: Path) -> None:
    original_registry = (POLICY_SOURCE / "fitness/policy/registry.json").read_bytes()
    original_charter = (POLICY_SOURCE / "fitness/policy/authority-charter.json").read_bytes()

    source, trust = _create_source(tmp_path)

    registry = json.loads((source / "fitness/policy/registry.json").read_bytes())
    policies = registry["policies"]
    claims = json.loads((source / "fitness/policy/completeness-claims.json").read_bytes())
    assert {item["obligation_ids"][0] for item in policies} == set(TARGET_IDS)
    assert all(item["normative_status"] == "APPROVED" for item in policies)
    assert all(item["applies_to_states"] == ["after"] for item in policies)
    assert [item["id"] for item in claims] == sorted(item["id"] for item in claims)
    assert trust.trust_scope == "TEST_ONLY"
    assert (POLICY_SOURCE / "fitness/policy/registry.json").read_bytes() == original_registry
    assert (
        POLICY_SOURCE / "fitness/policy/authority-charter.json"
    ).read_bytes() == original_charter


def test_testonly_signatures_verify_and_tampering_is_unresolved(tmp_path: Path) -> None:
    source, trust = _create_source(tmp_path)
    registry = json.loads((source / "fitness/policy/registry.json").read_bytes())
    policy = registry["policies"][0]
    charter_path = source / "fitness/policy/authority-charter.json"
    approval_path = source / "fitness/policy/approvals" / f"{policy['approval_source_id']}.json"
    charter = json.loads(charter_path.read_bytes())
    charter_source = _reference("CHARTER", charter_path, "AUTHORITY_CHARTER")
    approval_source = _reference(str(policy["approval_source_id"]), approval_path, "APPROVAL")

    assert trust.verify_charter(charter, charter_source, AS_OF) is True
    assert trust.verify_approval(policy, charter, approval_source, AS_OF) is True

    tampered = copy.deepcopy(json.loads(approval_path.read_bytes()))
    tampered["signature"] = "0" * 64
    tampered_source = SourceReference(
        source_id=approval_source.source_id,
        kind=approval_source.kind,
        path=approval_source.path,
        sha256=approval_source.sha256,
        content=json.dumps(tampered).encode("utf-8"),
    )
    assert trust.verify_approval(policy, charter, tampered_source, AS_OF) is None
