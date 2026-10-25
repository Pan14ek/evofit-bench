"""Independent inspection coverage and adaptation diagnosis contracts."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.mono_ci_psi_coverage import (
    assess_adaptation_necessity,
    verify_inspection_coverage,
)


def _git(root: Path, *args: str) -> str:
    git_binary = shutil.which("git")
    assert git_binary is not None
    result = subprocess.run(  # noqa: S603 - fixed Git executable and fixture-owned arguments
        [git_binary, "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _coverage_fixture(
    tmp_path: Path, evaluator_id: str = "AC_PUBLIC_API", with_cycle: bool = False
) -> dict[str, Any]:
    repo = tmp_path / "source"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "coverage@example.invalid")
    _git(repo, "config", "user.name", "Coverage Fixture")
    _write(repo, "app/modules/__init__.py", "")
    _write(repo, "app/modules/alpha/__init__.py", "")
    _write(repo, "app/modules/alpha/api.py", "from app.modules.beta.public import thing\n")
    _write(repo, "app/modules/beta/__init__.py", "")
    beta_source = (
        "from app.modules.alpha.api import thing\ndef beta_thing():\n    return thing()\n"
        if with_cycle
        else "def thing():\n    return None\n"
    )
    _write(repo, "app/modules/beta/public.py", beta_source)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "fixture")
    commit = _git(repo, "rev-parse", "HEAD")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    config: dict[str, Any] = {
        "schema_version": 1,
        "evaluator": {"id": evaluator_id, "obligation_id": evaluator_id},
        "source_scope": {
            "module_root": "app/modules",
            "expected_modules": ["alpha", "beta"],
            "minimum_source_files_per_module": 1,
            "minimum_inspected_files": 1,
            "additional_source_files": [],
        },
        "states": {"A0_4_REPORT_QUERY_PORT": {"applicability": "ACTIVE"}},
        "public_api": {"interfaces_by_capability": {"alpha": {}, "beta": {}}},
        "module_graph": {
            "allowed_dependencies_by_state": {
                "A0_4_REPORT_QUERY_PORT": [
                    {"from": "alpha", "to": "beta"},
                    {"from": "beta", "to": "alpha"},
                ]
            }
        },
    }
    config_bytes = yaml.safe_dump(config, sort_keys=False).encode("utf-8")
    manifest = {
        "architecture_state": "A0_4_REPORT_QUERY_PORT",
        "governance_requirements": {"required_evaluators": ["AC_PUBLIC_API", "AC_MODULE_GRAPH"]},
    }
    manifest_bytes = yaml.safe_dump(manifest, sort_keys=False).encode("utf-8")
    files = sorted(
        path.relative_to(repo).as_posix()
        for path in (repo / "app/modules").rglob("*.py")
        if len(path.relative_to(repo / "app/modules").parts) > 1
    )
    digests = [
        {"path": path, "sha256": hashlib.sha256((repo / path).read_bytes()).hexdigest()}
        for path in files
    ]
    modules = [{"name": name, "expected": True, "discovered": True} for name in ("alpha", "beta")]
    evidence: dict[str, Any] = {
        "architecture": {
            "expected_source_sha": commit,
            "target_source_sha": commit,
            "source_sha_status": "MATCHED",
            "manifest_state_status": "MATCHED",
            "manifest_digest": sha256_bytes(manifest_bytes),
            "state": "A0_4_REPORT_QUERY_PORT",
        },
        "evaluator": {
            "id": evaluator_id,
            "obligation_id": evaluator_id,
            "configuration_digest": sha256_bytes(config_bytes),
        },
        "source_scope": {
            "module_root": "app/modules",
            "modules": modules,
            "complete": True,
            "inspected_paths": files,
            "source_file_digests": digests,
        },
        "diagnostics": {
            "edges": [
                {
                    "from": "alpha",
                    "to": "beta",
                    "references": [
                        {
                            "source_path": "app/modules/alpha/api.py",
                            "line": 1,
                            "source_module": "app.modules.alpha.api",
                            "target_module": "app.modules.beta.public",
                            "imported_name": "thing",
                        }
                    ],
                },
                *(
                    [
                        {
                            "from": "beta",
                            "to": "alpha",
                            "references": [
                                {
                                    "source_path": "app/modules/beta/public.py",
                                    "line": 1,
                                    "source_module": "app.modules.beta.public",
                                    "target_module": "app.modules.alpha.api",
                                    "imported_name": "thing",
                                }
                            ],
                        }
                    ]
                    if with_cycle
                    else []
                ),
            ],
            "cycles": [["alpha", "beta", "alpha"]] if with_cycle else [],
        },
        "result": {"execution_status": "COMPLETED", "compliance": "COMPLIANT", "violations": []},
    }
    if evaluator_id == "AC_PUBLIC_API":
        evidence["diagnostics"] = {"imports": []}
    return {
        "repository": repo,
        "commit": commit,
        "tree": tree,
        "config_bytes": config_bytes,
        "manifest_bytes": manifest_bytes,
        "evidence": evidence,
        "output_bytes": canonical_json_bytes(evidence),
        "source_files": files,
    }


def _verify(fixture: dict[str, Any], evaluator_id: str = "AC_PUBLIC_API") -> dict[str, Any]:
    result = verify_inspection_coverage(
        repository=fixture["repository"],
        source_commit_sha=fixture["commit"],
        source_tree_sha=fixture["tree"],
        architecture_state="A0_4_REPORT_QUERY_PORT",
        evaluator_id=evaluator_id,
        evaluator_configuration_bytes=fixture["config_bytes"],
        state_manifest_bytes=fixture["manifest_bytes"],
        evaluator_output_bytes=fixture["output_bytes"],
        evaluator_evidence=fixture["evidence"],
    )
    validate_payload("mono_ci_psi_inspection_coverage_v1.schema.json", result)
    return result


def test_expected_subjects_are_derived_independently_from_git_and_config(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    evidence = fixture["evidence"]
    evidence["source_scope"]["inspected_paths"] = fixture["source_files"][:-1]
    evidence["source_scope"]["source_file_digests"] = evidence["source_scope"][
        "source_file_digests"
    ][:-1]
    fixture["output_bytes"] = canonical_json_bytes(evidence)

    result = _verify(fixture)

    assert result["expected_subjects"] == fixture["source_files"]
    assert result["inspected_subjects"] == fixture["source_files"][:-1]
    assert result["missing_subjects"] == [fixture["source_files"][-1]]
    assert result["counts"] == {
        "expected_count": 4,
        "inspected_count": 3,
        "missing_count": 1,
        "unexpected_count": 0,
        "altered_count": 0,
        "verified_matching_count": 3,
    }
    assert result["source_inspection_status"] == "INCOMPLETE"


def test_additional_unconfigured_subject_is_reported_as_unexpected(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    _write(fixture["repository"], "app/main.py", "# outside configured modules\n")
    _git(fixture["repository"], "add", "app/main.py")
    _git(fixture["repository"], "commit", "-qm", "unexpected source")
    fixture["commit"] = _git(fixture["repository"], "rev-parse", "HEAD")
    fixture["tree"] = _git(fixture["repository"], "rev-parse", "HEAD^{tree}")
    evidence = fixture["evidence"]
    path = "app/main.py"
    evidence["architecture"]["expected_source_sha"] = fixture["commit"]
    evidence["architecture"]["target_source_sha"] = fixture["commit"]
    evidence["source_scope"]["inspected_paths"].append(path)
    evidence["source_scope"]["inspected_paths"].sort()
    evidence["source_scope"]["source_file_digests"].append(
        {
            "path": path,
            "sha256": hashlib.sha256((fixture["repository"] / path).read_bytes()).hexdigest(),
        }
    )
    evidence["source_scope"]["source_file_digests"].sort(key=lambda row: row["path"])
    fixture["output_bytes"] = canonical_json_bytes(evidence)

    result = _verify(fixture)

    assert result["unexpected_subjects"] == [path]
    assert result["source_inspection_status"] == "INCOMPLETE"


def test_changed_file_digest_is_detected_against_the_pinned_git_blob(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    fixture["evidence"]["source_scope"]["source_file_digests"][0]["sha256"] = "f" * 64
    fixture["output_bytes"] = canonical_json_bytes(fixture["evidence"])

    result = _verify(fixture)

    assert result["altered_subjects"] == [fixture["source_files"][0]]
    assert result["source_inspection_status"] == "INCOMPLETE"


def test_wrong_architecture_revision_is_rejected(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    fixture["evidence"]["architecture"]["target_source_sha"] = "0" * 40
    fixture["output_bytes"] = canonical_json_bytes(fixture["evidence"])

    with pytest.raises(ContractValidationError, match="REVISION_CONFIG_OR_MANIFEST_MISMATCH"):
        _verify(fixture)


def test_incomplete_inspection_is_not_promoted_by_zero_violations(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path)
    fixture["evidence"]["result"]["violations"] = []
    fixture["evidence"]["source_scope"]["complete"] = False
    fixture["output_bytes"] = canonical_json_bytes(fixture["evidence"])

    result = _verify(fixture)

    assert result["source_inspection_status"] == "INCOMPLETE"
    assert result["counts"]["missing_count"] == 0
    assert result["overall_completeness"] == "INCOMPLETE_OR_UNRESOLVED"


def test_graph_expected_relationships_are_source_derived_not_allowed_edges(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path, evaluator_id="AC_MODULE_GRAPH")

    result = _verify(fixture, "AC_MODULE_GRAPH")

    analysis = result["dependency_analysis"]
    assert analysis["expected_edge_subjects"] == ["alpha->beta"]
    assert analysis["allowed_policy_edges"] == [
        {"from": "alpha", "to": "beta"},
        {"from": "beta", "to": "alpha"},
    ]
    assert "beta->alpha" not in analysis["expected_edge_subjects"]
    assert analysis["static_relationship_comparison"] == "MATCHED"
    assert analysis["expected_static_cycles"] == []
    assert analysis["observed_cycles"] == []
    assert analysis["cycle_comparison"] == "MATCHED"
    assert analysis["exact_dependency_edge_completeness"] == "UNKNOWN"
    assert result["source_inspection_status"] == "COMPLETE"
    assert (
        result["overall_completeness"] == "STATIC_SCOPE_MATCHED_DYNAMIC_EDGE_COMPLETENESS_UNKNOWN"
    )


def test_graph_cycle_scope_is_reconstructed_from_source_imports(tmp_path: Path) -> None:
    fixture = _coverage_fixture(tmp_path, evaluator_id="AC_MODULE_GRAPH", with_cycle=True)

    result = _verify(fixture, "AC_MODULE_GRAPH")

    analysis = result["dependency_analysis"]
    cycle = ["alpha", "beta", "alpha"]
    assert analysis["expected_static_cycles"] == [cycle]
    assert analysis["observed_cycles"] == [cycle]
    assert analysis["cycle_comparison"] == "MATCHED"


def _adaptation_case(**updates: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "configuration_sha256_before": "a" * 64,
        "configuration_sha256_after": "a" * 64,
        "evaluator_identity_verified": True,
        "architecture_identity_verified": True,
        "configuration_identity_verified": True,
        "source_inspection_before": "COMPLETE",
        "source_inspection_after": "COMPLETE",
        "evaluator_compliance_before": "COMPLIANT",
        "evaluator_compliance_after": "COMPLIANT",
        "rule_scope_match_before": True,
        "rule_scope_match_after": True,
        "required_controls_before": ["control:a"],
        "required_controls_after": ["control:a"],
        "represented_controls_before": ["control:a"],
        "represented_controls_after": ["control:a"],
        "pair_semantic_validity": "UNKNOWN",
        "normative_applicability": "UNKNOWN",
        "baseline_identity": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
        "independent_review": False,
    }
    result.update(updates)
    return result


def test_existing_representation_can_be_a_retain_candidate_with_open_authority() -> None:
    assessment = assess_adaptation_necessity(_adaptation_case())

    assert assessment["assessment_status"] == "RETAIN_CANDIDATE"
    assert "INDEPENDENT_PAIR_SEMANTIC_VALIDITY_NOT_ESTABLISHED" in assessment["missing_proofs"]
    assert assessment["operation_justification"]["RETAIN"] == "TECHNICAL_CANDIDATE_ONLY"
    assert assessment["operation_justification"]["HOLD"].startswith("REQUIRED")


def test_demonstrably_stale_representation_is_diagnosed_generically() -> None:
    assessment = assess_adaptation_necessity(
        _adaptation_case(
            required_controls_after=["control:a", "control:b"],
            represented_controls_after=["control:a"],
        )
    )

    assert assessment["assessment_status"] == "ADAPTATION_NEEDED"
    assert assessment["missing_post_transition_controls"] == ["control:b"]


def test_missing_scope_or_semantic_basis_produces_not_evaluable() -> None:
    assessment = assess_adaptation_necessity(
        _adaptation_case(rule_scope_match_after=None, source_inspection_after="INCOMPLETE")
    )

    assert assessment["assessment_status"] == "NOT_EVALUABLE"
    assert assessment["reason_codes"] == ["INSUFFICIENT_VERIFIED_SCOPE_OR_COMPLIANCE_EVIDENCE"]


def test_representation_identity_mismatch_is_distinguished_from_adaptation_need() -> None:
    assessment = assess_adaptation_necessity(_adaptation_case(evaluator_identity_verified=False))

    assert assessment["assessment_status"] == "MISMATCH_DETECTED"
    assert assessment["reason_codes"] == ["EVALUATOR_IDENTITY_MISMATCH"]
    assert assessment["operation_justification"]["ADD"] == "UNSUPPORTED"
    assert assessment["operation_justification"]["REPLACE"] == "UNSUPPORTED"
