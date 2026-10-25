"""Bounded TEST_ONLY evaluator evidence adapter contracts."""

from __future__ import annotations

import hmac
from pathlib import Path

import pytest

from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.mono_ci_psi_evidence import (
    TEST_ONLY_VERIFIER_ID,
    _module_names_from_paths,
    adapt_evaluator_evidence,
    build_inspection_scope_artifact,
    evaluator_source_artifacts,
)
from experiments.execution.tooling.mono_ci_psi_evidence import (
    TestOnlyEvidenceTrustContext as TrustContextUnderTest,
)
from experiments.execution.tooling.mono_ci_psi_evidence import (
    TestOnlyHmacVerifier as HmacVerifierUnderTest,
)

ROOT = Path(__file__).resolve().parents[2]


def test_evaluator_source_manifest_is_canonical_and_digest_bound() -> None:
    artifacts, manifest_bytes, digest = evaluator_source_artifacts(ROOT)

    assert artifacts
    assert len({row["path"] for row in artifacts}) == len(artifacts)
    assert manifest_bytes == canonical_json_bytes(artifacts)
    assert digest == sha256_bytes(manifest_bytes)
    assert all((ROOT / "architecture/acceptance/a1" / row["path"]).is_file() for row in artifacts)


def test_test_only_verifier_checks_hmac_and_rejects_unregistered_authority() -> None:
    key = b"k" * 32
    verifier = HmacVerifierUnderTest(key)
    digest = "a" * 64
    signature = hmac.new(key, digest.encode("ascii"), "sha256").hexdigest()

    assert verifier.trust_scope == "TEST_ONLY"
    assert verifier.verify(TEST_ONLY_VERIFIER_ID, digest, signature) is True
    assert verifier.verify(TEST_ONLY_VERIFIER_ID, digest, "0" * 64) is False
    assert verifier.verify("UNAPPROVED_VERIFIER", digest, signature) is None
    assert TrustContextUnderTest(key).trust_scope == "TEST_ONLY"


def test_test_only_verifier_rejects_short_keys() -> None:
    with pytest.raises(ContractValidationError, match="VERIFIER_KEY_TOO_SHORT"):
        HmacVerifierUnderTest(b"short")


def test_source_inventory_paths_are_sorted_unique_app_modules() -> None:
    assert _module_names_from_paths(["app/__init__.py", "app/tasks/api.py"]) == [
        "app",
        "app.tasks.api",
    ]
    with pytest.raises(ContractValidationError, match="SOURCE_INVENTORY_FILE_LIST_INVALID"):
        _module_names_from_paths(["app/tasks/api.py", "app/tasks/api.py"])


def test_inspection_scope_projection_binds_evaluator_output_and_file_digests() -> None:
    evidence = {
        "source_scope": {
            "complete": True,
            "inspected_paths": ["app/modules/tasks/api.py"],
            "source_file_digests": [{"path": "app/modules/tasks/api.py", "sha256": "a" * 64}],
        }
    }

    scope = build_inspection_scope_artifact(evidence, "b" * 64)

    assert scope["inspection_unit"] == "file"
    assert scope["expected_subjects"] == ["app/modules/tasks/api.py"]
    assert scope["inspected_subjects"] == ["app/modules/tasks/api.py"]
    assert scope["measured_count"] == 1
    assert scope["source_evaluator_output_sha256"] == "b" * 64

    edge_evidence = {
        "source_scope": evidence["source_scope"],
        "diagnostics": {
            "edges": [
                {
                    "from": "tasks",
                    "to": "audit",
                    "references": [{"source_path": "app/modules/tasks/api.py"}],
                },
                {
                    "from": "users",
                    "to": "audit",
                    "references": [{"source_path": "app/modules/tasks/api.py"}],
                },
            ]
        },
    }
    edge_scope = build_inspection_scope_artifact(edge_evidence, "c" * 64)
    assert edge_scope["inspection_unit"] == "dependency_edge"
    assert edge_scope["expected_subjects"] == ["tasks->audit", "users->audit"]
    assert edge_scope["measured_count"] == 2

    with pytest.raises(ContractValidationError, match="INSPECTION_SCOPE_UNRESOLVED"):
        build_inspection_scope_artifact(
            {
                "source_scope": {
                    "complete": True,
                    "inspected_paths": ["app/modules/tasks/api.py"],
                    "source_file_digests": [],
                }
            },
            "b" * 64,
        )


def test_adapter_preserves_semantic_and_adequacy_unknowns() -> None:
    representation = {
        "id": "AC_PUBLIC_API",
        "stage": "ci_test",
        "covers": ["AC_PUBLIC_API"],
    }
    output_path = "PSI/evaluator-observations/after/AC_PUBLIC_API/evaluator-output.json"
    scope_path = "PSI/evaluator-observations/after/AC_PUBLIC_API/inspection-scope.json"
    inspected_paths = ["app/modules/tasks/api.py", "app/modules/tasks/service.py"]
    run = {
        "architecture_state": "A0_4_REPORT_QUERY_PORT",
        "execution_status": "COMPLETED",
        "process_exit_code": 0,
        "stdout_sha256": "b" * 64,
        "stderr_sha256": "c" * 64,
        "started_at_utc": "2026-10-25T10:00:00+00:00",
        "ended_at_utc": "2026-10-25T10:00:01+00:00",
        "evidence": {
            "architecture": {
                "state": "A0_4_REPORT_QUERY_PORT",
                "manifest_state_status": "MATCHED",
                "target_source_sha": "d" * 40,
                "source_sha_status": "MATCHED",
            },
            "applicability": "ACTIVE",
            "source_scope": {
                "complete": True,
                "modules": [
                    {"name": "tasks", "expected": True, "discovered": True},
                    {"name": "reports", "expected": True, "discovered": False},
                ],
                "inspected_paths": inspected_paths,
                "source_file_digests": [
                    {"path": path, "sha256": "f" * 64} for path in inspected_paths
                ],
            },
            "evaluator": {"id": "AC_PUBLIC_API", "obligation_id": "AC_PUBLIC_API"},
            "diagnostics": {"imports": [{"from": "a", "to": "b"}]},
            "result": {"execution_status": "COMPLETED"},
        },
    }

    adapted = adapt_evaluator_evidence(
        representation=representation,
        obligation_id="AC_PUBLIC_API",
        run=run,
        artifact_refs=[
            {"path": output_path, "sha256": "e" * 64},
            {
                "path": "PSI/evaluator-observations/after/AC_PUBLIC_API/stdout.bin",
                "sha256": "1" * 64,
            },
            {
                "path": "PSI/evaluator-observations/after/AC_PUBLIC_API/stderr.bin",
                "sha256": "2" * 64,
            },
            {"path": scope_path, "sha256": "3" * 64},
        ],
    )

    assert adapted["semantic_compatible"] is None
    assert adapted["adequacy_proven"] is False
    assert adapted["mapping_resolved"] is True
    assert adapted["missing_targets"] == ["reports"]
    assert adapted["inspection_scope"]["measured_count"] == 2
    assert adapted["evidence_contract_satisfied"] is True
    assert adapted["inspection_scope"]["evidence_artifact"] == {
        "path": scope_path,
        "sha256": "3" * 64,
    }
