"""Derive V2 DEVELOPMENT analysis and a Ukrainian monograph handoff from raw evidence."""

# Generated Markdown tables retain long single-line rows for copy/paste into the monograph.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tempfile
import zipfile
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments.execution.tooling import mono_ci_psi_owner_authorized as owner
from experiments.execution.tooling import mono_ci_psi_owner_authorized_analysis as analysis_v1
from experiments.execution.tooling import mono_ci_psi_owner_authorized_v2 as study_v2
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import (
    pretty_json_bytes,
    sha256_file,
)
from experiments.execution.tooling.mono_ci_b0_psi_archive import verify_psi_transition_archive


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(pretty_json_bytes(value))


def _write_csv(path: Path, rows: list[Mapping[str, Any]], fields: list[str]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _json_field(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _b0_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "NOT_EXECUTED"
    expected = 4
    parsed = sum(row.get("process_observation_status") == "OUTPUT_PARSED" for row in rows)
    if parsed == expected:
        return "ALL_OUTPUTS_PARSED"
    if parsed:
        return f"PARTIAL_{parsed}_OF_{expected}"
    return "NO_OUTPUTS_PARSED"


def _complete_transition(
    bundle: Path, repository: Path, row: Mapping[str, Any], extract_root: Path
) -> dict[str, Any]:
    archive = bundle / str(row["evidence_archive"])
    extracted = extract_root / str(row["execution_id"])
    verified = verify_psi_transition_archive(archive, repository=repository, extract_to=extracted)
    if verified["archive_sha256"] != row.get("evidence_sha256"):
        raise ContractValidationError(
            "OWNER_AUTHORIZED_V2_ANALYSIS_COMPLETE_ARCHIVE_DIGEST_MISMATCH"
        )
    record = _read_json(extracted / "development_run.json")
    outcome = owner._transition_outcome(extracted, record)
    method_process_path = extracted / "PSI/raw/sandbox-execution.json"
    method_process = _read_json(method_process_path) if method_process_path.is_file() else {}
    extension = _read_json(extracted / record["a05_extension"]["path"])
    candidate_verification = extension.get("candidate_verification", {})
    cost = candidate_verification.get("execution_cost", {})
    candidate_evaluators = [
        {
            "representation_id": item.get("representation_id"),
            "candidate_positive": item.get("candidate_positive_outcome"),
            "candidate_negative": item.get("candidate_negative_outcome"),
            "positive_outcome_parity": item.get("positive_outcome_parity"),
            "negative_outcome_parity": item.get("negative_outcome_parity"),
        }
        for item in candidate_verification.get("outcome_comparisons", [])
    ]
    b0 = []
    state_directories = {
        "A0_4_REPORT_QUERY_PORT": "before",
        "A0_5_MODULE_DATA_OWNERSHIP": "after",
    }
    for observed in outcome.get("B0", []):
        base = (
            extracted
            / "PSI/evaluator-observations"
            / state_directories[observed["architecture_state"]]
            / observed["evaluator_id"]
        )
        process_path = base / "process-execution.json"
        process = _read_json(process_path) if process_path.is_file() else {}
        coverage_path = base / "inspection-coverage.json"
        coverage = _read_json(coverage_path) if coverage_path.is_file() else {}
        b0.append(
            {
                **observed,
                "process_observation_status": process.get("status", "NOT_OBSERVED"),
                "stdout_sha256": process.get("stdout_sha256"),
                "stderr_sha256": process.get("stderr_sha256"),
                "inspection_status": coverage.get("source_inspection_status"),
            }
        )
    return {
        "execution_id": row["execution_id"],
        "run_role": row["role"],
        "measured": row["measured"],
        "run_status": row["run_status"],
        "b0_execution_status": _b0_summary(b0),
        "b0_evaluator_outcomes": b0,
        "method_process_status": method_process.get("status", "NOT_OBSERVED"),
        "method_process_exit_code": method_process.get("exit_code"),
        "method_decision": outcome["Psi"]["decision"],
        "governance_reason_codes": outcome["Psi"]["reason_codes"],
        "operation_plan": outcome["Psi"]["operation_plan"],
        "hold_reasons": outcome["Psi"]["operation_hold_reasons"],
        "candidate_state": outcome["Psi"]["candidate_state"],
        "candidate_configuration_sha256": outcome["Psi"]["candidate_sha256"],
        "candidate_evaluators": candidate_evaluators,
        "candidate_verification_status": candidate_verification.get(
            "status",
            candidate_verification.get("method_candidate_validation_status", "NOT_REPORTED"),
        ),
        "candidate_validation_cost_ms": cost.get("candidate_validation_total_ms"),
        "estimated_additional_ci_execution_ms_per_build": cost.get(
            "estimated_additional_ci_execution_ms_per_build"
        ),
        "full_transition_duration_ms": row.get("full_transition_duration_ms"),
        "method_execution_duration_ms": outcome["Psi"]["method_duration_ms"],
        "evidence_digest": row.get("evidence_sha256"),
        "evidence_classification": row.get("evidence_classification"),
        "error_or_hold_reasons": outcome["Psi"]["operation_hold_reasons"],
        "source_revision_sha": record.get("source_revision_sha"),
        "source_identity_status": "PASS",
        "phase_status": {
            "source_identity": "COMPLETED",
            "baseline_identity": "COMPLETED",
            "b0_evaluator_matrix": "COMPLETED",
            "method_input_bundle": "COMPLETED",
            "method_execution": "COMPLETED",
            "candidate_validation": "COMPLETED",
            "complete_transition_verification": "PASS",
        },
        "transition_record_sha256": sha256_file(extracted / "development_run.json"),
        "method_result_sha256": outcome["Psi"]["method_result_sha256"],
    }


def _read_partial_archive_row(bundle: Path, row: Mapping[str, Any]) -> dict[str, Any]:
    if row.get("evidence_archive"):
        archive_path = bundle / str(row["evidence_archive"])
        verified = owner.verify_partial_execution_archive(archive_path)
        if verified["archive_sha256"] != row.get("evidence_sha256"):
            raise ContractValidationError(
                "OWNER_AUTHORIZED_V2_ANALYSIS_PARTIAL_ARCHIVE_DIGEST_MISMATCH"
            )
        with zipfile.ZipFile(archive_path, "r") as zipped:
            names = set(zipped.namelist())

            def read_member(relative: str) -> Any | None:
                name = f"run/{relative}"
                return json.loads(zipped.read(name)) if name in names else None

            def read_member_bytes(relative: str) -> bytes | None:
                name = f"run/{relative}"
                return zipped.read(name) if name in names else None

            archive_manifest = json.loads(zipped.read("PARTIAL_EVIDENCE_MANIFEST.json"))
            partial = read_member("partial-execution.json") or {}
            if not partial:
                partial = {
                    "phase_status": archive_manifest.get("phase_status", {}),
                    "source_identities": archive_manifest.get("source_identities", {}),
                    "error": archive_manifest.get("error"),
                }
            run_prefix = "run/"
            available = {
                name.removeprefix(run_prefix) for name in names if name.startswith(run_prefix)
            }
            method_process = (
                partial.get("method_subprocess") or archive_manifest.get("method_subprocess") or {}
            )
            method_observation = (
                partial.get("method_observation")
                or archive_manifest.get("method_observation")
                or {}
            )
            record = read_member("development_run.json") or {}
            extension = {}
            extension_path = record.get("a05_extension", {}).get("path")
            if isinstance(extension_path, str):
                extension = read_member(extension_path) or {}
            candidate_verification = extension.get("candidate_verification", {})
            return _partial_transition_summary(
                row,
                partial,
                method_process,
                method_observation,
                candidate_verification,
                record,
                read_member,
                read_member_bytes,
                available,
            )
    if row.get("raw_preservation_path"):
        raw = bundle / str(row["raw_preservation_path"])

        def read_member(relative: str) -> Any | None:
            path = raw / relative
            return _read_json(path) if path.is_file() and not path.is_symlink() else None

        def read_member_bytes(relative: str) -> bytes | None:
            path = raw / relative
            return path.read_bytes() if path.is_file() and not path.is_symlink() else None

        partial = read_member("partial-execution.json") or {}
        available = {path.relative_to(raw).as_posix() for path in raw.rglob("*") if path.is_file()}
        record = read_member("development_run.json") or {}
        method_process = partial.get("method_subprocess") or {}
        method_observation = partial.get("method_observation") or {}
        extension = {}
        extension_path = record.get("a05_extension", {}).get("path")
        if isinstance(extension_path, str):
            extension = read_member(extension_path) or {}
        if record and not method_process:
            psi = record.get("psi", {})
            method_process = {
                "status": psi.get("status", "NOT_OBSERVED"),
                "exit_code": 0 if psi.get("status") == "DEVELOPMENT_METHOD_EXECUTED" else None,
                "execution_duration_ms": psi.get("execution_duration_ms"),
            }
            method_result = read_member(psi.get("raw_result_path", "")) or {}
            governance = method_result.get("governance", {})
            plan = method_result.get("operation_plan", {})
            candidate = method_result.get("candidate")
            method_observation = {
                "governance_decision": governance.get("result"),
                "governance_reason_codes": governance.get("reason_codes", []),
                "operations": plan.get("operations", []),
                "operation_hold_reasons": plan.get("hold_reasons", []),
                "candidate_state": "NOT_MATERIALIZED"
                if candidate is None
                else "MATERIALIZED_UNAPPLIED",
                "candidate_sha256": method_result.get("candidate_sha256"),
                "raw_result_sha256": psi.get("raw_result_sha256"),
            }
        return _partial_transition_summary(
            row,
            partial,
            method_process,
            method_observation,
            extension.get("candidate_verification", {}),
            record,
            read_member,
            read_member_bytes,
            available,
        )
    raise ContractValidationError("OWNER_AUTHORIZED_V2_ANALYSIS_PARTIAL_EVIDENCE_MISSING")


def _partial_transition_summary(
    row: Mapping[str, Any],
    partial: Mapping[str, Any],
    method_process: Mapping[str, Any],
    method_observation: Mapping[str, Any],
    candidate_verification: Mapping[str, Any],
    record: Mapping[str, Any],
    read_member: Any,
    read_member_bytes: Any,
    available: set[str],
) -> dict[str, Any]:
    b0_rows = []
    for state_dir, state_name in (
        ("before", "A0_4_REPORT_QUERY_PORT"),
        ("after", "A0_5_MODULE_DATA_OWNERSHIP"),
    ):
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH"):
            base = f"PSI/evaluator-observations/{state_dir}/{evaluator_id}"
            process = read_member(f"{base}/process-execution.json")
            evidence = read_member(f"{base}/evaluator-output.json")
            coverage = read_member(f"{base}/inspection-coverage.json")
            if process is None and evidence is None:
                continue
            result = evidence.get("result", {}) if isinstance(evidence, dict) else {}
            architecture = evidence.get("architecture", {}) if isinstance(evidence, dict) else {}
            b0_rows.append(
                {
                    "architecture_state": state_name,
                    "evaluator_id": evaluator_id,
                    "exit_code": process.get("exit_code") if isinstance(process, dict) else None,
                    "execution_status": result.get("execution_status"),
                    "compliance": result.get("compliance"),
                    "source_commit_sha": architecture.get("target_source_sha"),
                    "output_sha256": _member_sha256(
                        read_member_bytes, f"{base}/evaluator-output.json"
                    ),
                    "process_observation_status": process.get("status", "NOT_OBSERVED")
                    if isinstance(process, dict)
                    else "NOT_OBSERVED",
                    "stdout_sha256": process.get("stdout_sha256")
                    if isinstance(process, dict)
                    else None,
                    "stderr_sha256": process.get("stderr_sha256")
                    if isinstance(process, dict)
                    else None,
                    "inspection_status": coverage.get("source_inspection_status")
                    if isinstance(coverage, dict)
                    else None,
                }
            )
    cost = candidate_verification.get("execution_cost", {})
    candidate_evaluators = [
        {
            "representation_id": item.get("representation_id"),
            "candidate_positive": item.get("candidate_positive_outcome"),
            "candidate_negative": item.get("candidate_negative_outcome"),
            "positive_outcome_parity": item.get("positive_outcome_parity"),
            "negative_outcome_parity": item.get("negative_outcome_parity"),
        }
        for item in candidate_verification.get("outcome_comparisons", [])
    ]
    source_identities = partial.get("source_identities", {})
    source_identity_status = source_identities.get("verification_status")
    if source_identity_status is None and source_identities:
        source_identity_status = "SOURCE_IDENTITIES_PRESERVED"
    return {
        "execution_id": row["execution_id"],
        "run_role": row["role"],
        "measured": row["measured"],
        "run_status": row["run_status"],
        "b0_execution_status": _b0_summary(b0_rows),
        "b0_evaluator_outcomes": b0_rows,
        "method_process_status": method_process.get("status", "NOT_OBSERVED"),
        "method_process_exit_code": method_process.get("exit_code"),
        "method_decision": method_observation.get("governance_decision"),
        "governance_reason_codes": method_observation.get("governance_reason_codes"),
        "operation_plan": method_observation.get("operations"),
        "hold_reasons": method_observation.get("operation_hold_reasons"),
        "candidate_state": method_observation.get("candidate_state", "NOT_OBSERVED"),
        "candidate_configuration_sha256": method_observation.get("candidate_sha256"),
        "candidate_evaluators": candidate_evaluators,
        "candidate_verification_status": candidate_verification.get(
            "method_candidate_validation_status", "NOT_OBSERVED"
        ),
        "candidate_validation_cost_ms": cost.get("candidate_validation_total_ms"),
        "estimated_additional_ci_execution_ms_per_build": cost.get(
            "estimated_additional_ci_execution_ms_per_build"
        ),
        "full_transition_duration_ms": row.get("full_transition_duration_ms"),
        "method_execution_duration_ms": method_process.get("execution_duration_ms"),
        "evidence_digest": row.get("evidence_sha256") or row.get("raw_preservation_digest"),
        "evidence_classification": row.get("evidence_classification"),
        "error_or_hold_reasons": partial.get("error") or row.get("error"),
        "source_identity_status": source_identity_status,
        "phase_status": partial.get("phase_status", {}),
        "raw_method_result_sha256": method_observation.get("raw_result_sha256"),
        "partial_archive_member_count": len(available),
        "source_revision_sha": record.get("source_revision_sha"),
    }


def _member_sha256(read_member_bytes: Any, relative: str) -> str | None:
    try:
        value = read_member_bytes(relative)
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    return hashlib.sha256(value).hexdigest() if value is not None else None


def _transition_summaries(
    bundle: Path, repository: Path, execution: Mapping[str, Any]
) -> list[dict[str, Any]]:
    summaries = []
    with tempfile.TemporaryDirectory(prefix="mono-ci-psi-v2-analysis-") as temporary:
        extract_root = Path(temporary)
        for row in execution.get("transition_runs", []):
            if row.get("run_status") == "NOT_RUN_BUDGET_EXHAUSTED":
                summaries.append(
                    {
                        "execution_id": row["execution_id"],
                        "run_role": row["role"],
                        "measured": row["measured"],
                        "run_status": row["run_status"],
                        "b0_execution_status": "NOT_EXECUTED",
                        "b0_evaluator_outcomes": [],
                        "method_process_status": "NOT_OBSERVED",
                        "method_decision": None,
                        "operation_plan": None,
                        "candidate_state": "NOT_OBSERVED",
                        "evidence_digest": None,
                        "evidence_classification": "NO_ATTEMPT",
                        "error_or_hold_reasons": "BUDGET_EXHAUSTED_BEFORE_ATTEMPT",
                    }
                )
            elif row.get("evidence_classification") == "COMPLETE_TRANSITION_ARCHIVE":
                summaries.append(_complete_transition(bundle, repository, row, extract_root))
            else:
                summaries.append(_read_partial_archive_row(bundle, row))
    return summaries


def _statistics_row(label: str, values: list[float]) -> dict[str, Any]:
    return {"measure": label, **analysis_v1.descriptive_statistics(values)}


def _measured_timing_summaries(
    transitions: list[Mapping[str, Any]], calibration_rows: list[Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Report calibration and transition B0 process times as separate samples."""
    transition_b0_times = [
        item["duration_ms"]
        for row in transitions
        if row.get("measured")
        for item in row.get("b0_evaluator_outcomes", [])
        if item.get("duration_ms") is not None
    ]
    calibration_process_times = [
        row["process_duration_ms"]
        for row in calibration_rows
        if row.get("sample_status") == "MEASURED"
        and not row.get("is_warmup")
        and row.get("process_duration_ms") is not None
    ]
    return {
        "measured_transition_b0_evaluator_process_times": analysis_v1.descriptive_statistics(
            transition_b0_times
        ),
        "measured_calibration_evaluator_process_times": analysis_v1.descriptive_statistics(
            calibration_process_times
        ),
    }


def _calibration_call_summary(summary: Mapping[str, Any], planned_calls: int) -> dict[str, int]:
    """Use sample-row status counts and keep warmup calls outside measured samples."""
    return {
        "planned_calls": planned_calls,
        "measured_successful_calls": int(summary.get("measured_successful_samples", 0)),
        "measured_failed_calls": int(summary.get("measured_failed_samples", 0)),
        "warmup_calls": int(summary.get("warmup_samples", 0)),
        "not_run_measured_calls": int(summary.get("measured_not_run_samples", 0)),
    }


def _strip_trailing_whitespace(path: Path) -> None:
    """Remove renderer-added trailing spaces without changing SVG content."""
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def _normalize_csv_line_endings(path: Path) -> None:
    """Use stable LF line endings so CSV digests survive cross-platform checkout."""
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _scientific_conclusion(transitions: list[Mapping[str, Any]]) -> str:
    decisions = Counter(
        str(row.get("method_decision"))
        for row in transitions
        if row.get("method_decision") is not None
    )
    parsed_b0 = sum(row.get("b0_execution_status") == "ALL_OUTPUTS_PARSED" for row in transitions)
    observed = sum(row.get("method_process_exit_code") == 0 for row in transitions)
    operations = [row.get("operation_plan") for row in transitions if row.get("method_decision")]
    hold_reasons = sorted(
        {
            str(reason)
            for row in transitions
            for reason in [
                *(row.get("governance_reason_codes") or []),
                *(row.get("hold_reasons") or []),
            ]
        }
    )
    candidate_rows = [
        candidate for row in transitions for candidate in row.get("candidate_evaluators", [])
    ]
    parity_count = sum(
        candidate.get("positive_outcome_parity") is True
        and candidate.get("negative_outcome_parity") is True
        for candidate in candidate_rows
    )
    parity_total = len(candidate_rows)
    decision_text = ", ".join(
        f"{decision}: {count}" for decision, count in sorted(decisions.items())
    )
    if decisions and set(decisions) == {"HOLD"} and all(plan == [] for plan in operations):
        adaptation = (
            "Method Ψ фактично сформував кандидат і запустив його валідацію, але рішення HOLD "
            "залишило конфігурацію MATERIALIZED_UNAPPLIED; застосованої адаптації не було."
        )
    elif any(plan for plan in operations if isinstance(plan, list)):
        adaptation = "Окремо звірити фактичний operation plan і стан застосування з raw result кожної спроби."
    else:
        adaptation = "Результат адаптації обмежити фактичним candidate/operation status у таблиці; відсутнє не домислювати."
    if parity_total and parity_count == parity_total:
        candidate_effect = (
            f"У наявних candidate controls parity з реконструйованим B0 становила "
            f"{parity_count}/{parity_total}; у межах цих перевірок поліпшення detection capability "
            "не зафіксовано."
        )
    elif parity_total:
        candidate_effect = (
            f"Candidate evaluator parity зафіксовано у {parity_count}/{parity_total} доступних "
            "порівнянь; висновок про покращення поза цими точковими controls не робити."
        )
    else:
        candidate_effect = (
            "Candidate evaluator outcomes відсутні або неповні; detection effect невідомий."
        )
    reasons = ", ".join(hold_reasons) if hold_reasons else "не зафіксовані"
    return (
        f"У цьому owner-authorized exploratory DEVELOPMENT запуску B0 зберіг "
        f"розібрані виходи у {parsed_b0}/{len(transitions)} переходах; Method Ψ завершився з "
        f"exit code 0 у {observed}/{len(transitions)} спробах і повернув {decision_text or 'NOT_OBSERVED'}. "
        f"Фактичні блокувальні reason codes: {reasons}. {adaptation} {candidate_effect} "
        "Одна пара станів A0.4→A0.5 і три технічні повтори не встановлюють загальної "
        "ефективності методу, verified mandatory coverage, runtime architectural quality, "
        "статистичної переваги або G1/G4; coverage залишається UNKNOWN, G1 INCOMPLETE, "
        "G4 NOT_AUTHORIZED, scoring NOT_EXECUTED."
    )


def _read_preserved_postexecution_readback_failure(bundle: Path) -> dict[str, Any] | None:
    """Verify the prior frozen V2 attempt record without reclassifying its archived run."""
    protocol = bundle / "protocol-snapshot"
    record_path = protocol / study_v2.POSTEXECUTION_READBACK_FAILURE.name
    sidecar_path = protocol / study_v2.POSTEXECUTION_READBACK_FAILURE_SIDECAR.name
    freeze_path = protocol / study_v2.PREVIOUS_FREEZE.name
    freeze_sidecar_path = protocol / study_v2.PREVIOUS_FREEZE_SIDECAR.name
    present = [
        path.is_file() for path in (record_path, sidecar_path, freeze_path, freeze_sidecar_path)
    ]
    if not any(present):
        return None
    if not all(present):
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PRIOR_READBACK_EVIDENCE_INCOMPLETE")
    record_digest = sha256_file(record_path)
    if sidecar_path.read_text(encoding="ascii").strip() != f"{record_digest}  {record_path.name}":
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PRIOR_READBACK_SIDECAR_MISMATCH")
    record = _read_json(record_path)
    validate_payload(study_v2.POSTEXECUTION_FAILURE_SCHEMA, record)
    freeze_digest = sha256_file(freeze_path)
    if (
        freeze_digest != record.get("previous_freeze_sha256")
        or freeze_sidecar_path.read_text(encoding="ascii").strip()
        != f"{freeze_digest}  {freeze_path.name}"
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PRIOR_FREEZE_READBACK_MISMATCH")
    return {**record, "_record_sha256": record_digest}


def _handoff(
    *,
    execution: Mapping[str, Any],
    v1_execution: Mapping[str, Any],
    v1_calibration_rows: list[Mapping[str, Any]],
    v1_calibration_summary: Mapping[str, Any],
    v2_calibration_summary: Mapping[str, Any],
    transitions: list[Mapping[str, Any]],
    calibration_archive_sha256: str,
    v1_calibration_archive_sha256: str,
    v1_readback: Mapping[str, Any],
    premeasurement_failures: list[Mapping[str, Any]],
    postexecution_readback_failures: list[Mapping[str, Any]],
    transition_failures: list[Mapping[str, Any]],
) -> str:
    v1_by = {
        (row["source_condition"], row["evaluator_id"]): row
        for row in v1_calibration_summary["cells"]
    }
    v2_by = {
        (row["source_condition"], row["evaluator_id"]): row
        for row in v2_calibration_summary["cells"]
    }
    compare_rows = []
    for condition in ("A0_5_CLEAN", "EXISTING_NEGATIVE_PROBE"):
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP"):
            old = v1_by.get((condition, evaluator_id), {})
            new = v2_by.get((condition, evaluator_id), {})
            old_time = old.get("process_duration", {})
            new_time = new.get("process_duration", {})
            if not old and not new:
                continue
            compare_rows.append(
                f"| {condition} | {evaluator_id} | {old_time.get('n', 0)} | "
                f"{old.get('failed_samples', 0)} | {old_time.get('mean_ms', '—')} | "
                f"{new_time.get('n', 0)} | {new.get('failed_samples', 0)} | "
                f"{new_time.get('mean_ms', '—')} |"
            )
    transition_rows = []
    for row in transitions:
        b0 = (
            "; ".join(
                f"{item.get('architecture_state')}:{item.get('evaluator_id')}="
                f"{item.get('compliance') or item.get('execution_status') or 'NOT_OBSERVED'} "
                f"(exit={item.get('exit_code')}, scope={item.get('inspection_status') or 'UNKNOWN'})"
                for item in row.get("b0_evaluator_outcomes", [])
            )
            or "NOT_OBSERVED"
        )
        decision = row.get("method_decision") or "NOT_OBSERVED"
        operations = row.get("operation_plan")
        operation_text = _json_field(operations) if operations is not None else "NOT_OBSERVED"
        candidate_text = (
            f"{row.get('candidate_state')} / {row.get('candidate_verification_status')} / "
            f"{row.get('candidate_configuration_sha256') or 'NO_DIGEST'}"
        )
        validation_text = _json_field(row.get("candidate_evaluators", []))
        reasons = {
            "governance": row.get("governance_reason_codes"),
            "operation_hold": row.get("hold_reasons"),
        }
        transition_rows.append(
            f"| {row.get('execution_id')} | {row.get('run_role')} | "
            f"{row.get('b0_execution_status')} | {b0} | "
            f"{row.get('method_process_status')} | {decision} | {operation_text} | "
            f"{_json_field(reasons)} | {candidate_text} | {validation_text} | "
            f"{row.get('candidate_validation_cost_ms') or '—'} | "
            f"{row.get('estimated_additional_ci_execution_ms_per_build') if row.get('estimated_additional_ci_execution_ms_per_build') is not None else '—'} | "
            f"{row.get('full_transition_duration_ms') or '—'} | "
            f"{row.get('method_execution_duration_ms') or '—'} | "
            f"{_json_field(row.get('error_or_hold_reasons'))} | {row.get('evidence_digest') or '—'} |"
        )
    completed = execution.get("transition_summary", {}).get("completed_runs", 0)
    failed = execution.get("transition_summary", {}).get("failed_runs", 0)
    v1_transition = v1_execution.get("transition_summary", {})
    clean_means = [
        row["process_duration"]["mean_ms"]
        for row in v1_calibration_summary["cells"]
        if row["source_condition"] == "A0_5_CLEAN"
        and row["process_duration"]["mean_ms"] is not None
    ]
    v1_clean_rows = [
        row
        for row in v1_calibration_rows
        if row.get("source_condition") == "A0_5_CLEAN"
        and row.get("sample_status") == "MEASURED"
        and not row.get("is_warmup")
    ]
    v1_clean_complete = sum(
        row.get("inspection_status") == "COMPLETE"
        and isinstance(row.get("inspection_counts"), dict)
        and all(
            row["inspection_counts"].get(key) == 0
            for key in ("missing_count", "altered_count", "unexpected_count")
        )
        for row in v1_clean_rows
    )
    stats = (
        f"За даними `{v1_execution['study_id']}`, run 40499692594, сирого `calibration.zip` "
        f"SHA-256 `{v1_calibration_archive_sha256}` та первинної обробки функцією "
        f"`_summarize_calibration` (десять виміряних повторів; прогрів вилучено; p90 — "
        f"nearest-rank), середні CLI-часи трьох оцінювачів на чистому A0.5 становили "
        f"{min(clean_means):.3f}–{max(clean_means):.3f} мс. У межах цих clean-source "
        f"вибірок повну source inspection із нульовими missing, altered і unexpected файлами "
        f"зафіксовано у {v1_clean_complete}/{len(v1_clean_rows)} виміряних запусків."
        if clean_means
        else "V1 clean-source timing data are unavailable."
    )
    v1_negative = (
        f"У V1 тієї самої історичної проби було збережено "
        f"{v1_readback['counts']['archived_evaluator_outputs']} raw-виходи; "
        f"post-run технічний readback пройшов для "
        f"{v1_readback['counts']['post_run_scope_pass']} "
        f"із них. Архів містить 30 failed виміряних sample records і три failed warmup records "
        f"для негативної умови; початкові статуси та process durations не переписувалися. "
        f"Readback SHA-256 `{_sha256_file_from_mapping(v1_readback)}` "
        f"підтверджує лише повторне source/scope зіставлення, а не новий запуск."
    )
    v1_calibration_counts = _calibration_call_summary(
        v1_calibration_summary, int(v1_execution["calibration"].get("planned_calls", 0))
    )
    v2_calibration_counts = _calibration_call_summary(
        v2_calibration_summary, int(execution["calibration"].get("planned_calls", 0))
    )
    v2_conditions = execution["calibration"].get("source_conditions", [])
    v2_timing_rows = []
    for cell in v2_calibration_summary.get("cells", []):
        timing = cell.get("process_duration", {})
        v2_timing_rows.append(
            f"| {cell['source_condition']} | {cell['evaluator_id']} | {timing.get('n', 0)} | "
            f"{cell.get('failed_samples', 0)} | {timing.get('mean_ms') or '—'} | "
            f"{timing.get('median_ms') or '—'} | {timing.get('sample_standard_deviation_ms') or '—'} | "
            f"{timing.get('minimum_ms') or '—'}–{timing.get('maximum_ms') or '—'} | "
            f"{timing.get('p90_nearest_rank_ms') or '—'} |"
        )
    v2_timing_text = "\n".join(v2_timing_rows) or "| — | — | 0 | 0 | — | — | — | — | — |"
    v2_transition_text = (
        "\n".join(transition_rows)
        or "| — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |"
    )
    comparison_text = "\n".join(compare_rows) or "| — | — | 0 | 0 | — | 0 | 0 | — |"
    premeasurement_text = (
        "\n".join(
            f"| {row.get('workflow_run_id')} | {row.get('failure_stage')} | "
            f"{row.get('calibration_calls_started')} | {row.get('transition_attempts_started')} | "
            f"{row.get('method_psi_status')} | {row.get('error_code')} | "
            f"{row.get('archive_sha256')} |"
            for row in premeasurement_failures
        )
        or "| — | — | 0 | 0 | — | — | — |"
    )
    release_run = execution.get("workflow_run_id", "NOT_RECORDED")
    measured_transitions = [row for row in transitions if row.get("measured")]
    b0_times = [
        item["duration_ms"]
        for row in measured_transitions
        for item in row.get("b0_evaluator_outcomes", [])
        if item.get("duration_ms") is not None
    ]
    measured_costs = [
        row["candidate_validation_cost_ms"]
        for row in measured_transitions
        if row.get("candidate_validation_cost_ms") is not None
    ]
    method_times = [
        row["method_execution_duration_ms"]
        for row in measured_transitions
        if row.get("method_execution_duration_ms") is not None
    ]
    transition_times = [
        row["full_transition_duration_ms"]
        for row in measured_transitions
        if row.get("full_transition_duration_ms") is not None
    ]
    timing_rows = []
    for label, values, expected in (
        (
            "B0 evaluator process time (all states/evaluators)",
            b0_times,
            len(measured_transitions) * 4,
        ),
        ("Method Ψ subprocess", method_times, len(measured_transitions)),
        ("Candidate evaluator validation", measured_costs, len(measured_transitions)),
        ("Full transition orchestration", transition_times, len(measured_transitions)),
    ):
        stats_row = analysis_v1.descriptive_statistics(values)
        timing_rows.append(
            f"| {label} | {stats_row['n']} | {expected - stats_row['n']} | "
            f"{stats_row['mean_ms'] if stats_row['mean_ms'] is not None else '—'} | "
            f"{stats_row['median_ms'] if stats_row['median_ms'] is not None else '—'} | "
            f"{stats_row['sample_standard_deviation_ms'] if stats_row['sample_standard_deviation_ms'] is not None else '—'} | "
            f"{stats_row['minimum_ms'] if stats_row['minimum_ms'] is not None else '—'}–"
            f"{stats_row['maximum_ms'] if stats_row['maximum_ms'] is not None else '—'} | "
            f"{stats_row['p90_nearest_rank_ms'] if stats_row['p90_nearest_rank_ms'] is not None else '—'} |"
        )
    timing_text = "\n".join(timing_rows)
    prior_attempt_rows = []
    for prior in postexecution_readback_failures:
        for attempt in prior.get("transition_attempts", []):
            prior_attempt_rows.append(
                f"| {prior.get('workflow_run_id')} | {attempt.get('execution_id')} | "
                f"{attempt.get('wrapper_run_status')} | {attempt.get('method_process_status')} | "
                f"{attempt.get('method_decision')} | {attempt.get('candidate_validation_status')} | "
                f"{attempt.get('wrapper_error')} | {attempt.get('partial_archive_sha256')} |"
            )
    prior_attempt_text = "\n".join(prior_attempt_rows) or "| — | — | — | — | — | — | — | — |"
    technical_failure_rows = []
    for failure in transition_failures:
        technical_failure_rows.append(
            f"| {failure.get('execution_id')} | {failure.get('run_status')} | "
            f"{_json_field(failure.get('error_or_hold_reasons'))} | "
            f"{failure.get('evidence_classification')} | {failure.get('evidence_digest')} |"
        )
    technical_failure_text = "\n".join(technical_failure_rows) or "| — | — | — | — | — |"
    return f"""# Власницьки авторизоване DEVELOPMENT-дослідження ΔA5 — V2

## Класифікація і межі

Study ID: `{execution["study_id"]}`. Класифікація — `RESEARCH_OWNER_AUTHORIZED_EXPLORATORY_DEVELOPMENT`; workflow run: `{release_run}`. Це одна архітектурна одиниця A0.4→A0.5 і чотири технічні спроби (один прогрів і три вимірювані повтори). Результати не є незалежним порівнянням, не завершують G1/G4 і не встановлюють наукову перевагу. P algorithm лишається NOT_READY, G1 INCOMPLETE, G4 NOT_AUTHORIZED, scoring NOT_EXECUTED, coverage UNKNOWN.

## Порівняння повноти V1 та V2

| Набір | Calls planned | Measured successful | Measured failed | Warmups | Measured not run | Transitions: completed / failed | Статус B0/Ψ |
|---|---:|---:|---:|---:|---:|---:|---|
| V1 (`{v1_execution["study_id"]}`; run 40499692594) | {v1_calibration_counts["planned_calls"]} | {v1_calibration_counts["measured_successful_calls"]} | {v1_calibration_counts["measured_failed_calls"]} | {v1_calibration_counts["warmup_calls"]} | {v1_calibration_counts["not_run_measured_calls"]} | {v1_transition.get("completed_runs", 0)} / {v1_transition.get("failed_runs", 0)} | порівняння NOT_EXECUTED; Ψ NOT_OBSERVED |
| V2 (`{execution["study_id"]}`; run {release_run}) | {v2_calibration_counts["planned_calls"]} | {v2_calibration_counts["measured_successful_calls"]} | {v2_calibration_counts["measured_failed_calls"]} | {v2_calibration_counts["warmup_calls"]} | {v2_calibration_counts["not_run_measured_calls"]} | {completed} / {failed} | див. окремі фактичні рядки нижче |

| Умова | Оцінювач | V1 n | V1 failed | V1 mean ms | V2 n | V2 failed | V2 mean ms |
|---|---|---:|---:|---:|---:|---:|---:|
{comparison_text}

Вибірки калібрування V1 та V2 збережені окремо. Протокол V2 вибрав умови `{", ".join(v2_conditions)}` за замороженим правилом порівнянності середовища; часові вибірки не об'єднувалися.

## Калібрування: виміряні результати

{stats}

| Умова | Оцінювач | n | Failed | Mean ms | Median ms | SD ms | Min–max ms | p90 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{v2_timing_text}

V2 числові рядки відтворюються зі study `{execution["study_id"]}`, workflow run `{release_run}`, `calibration.zip` SHA-256 `{calibration_archive_sha256}` та `evaluator-samples.csv`; обробка: `descriptive_statistics`/`_summarize_calibration`, прогрів не входить до часу. На одне architecture-level спостереження статистичну значущість не обчислено.

## Перехід: фактичні B0 та Method Ψ

| Execution ID | Роль | B0 status | B0 outcomes (exit/scope) | Ψ process | Ψ decision | Operations | Ψ reasons | Candidate state/status/digest | Candidate outcomes/parity | Candidate cost ms | Estimated added CI ms/build | Transition ms | Ψ ms | Error | Evidence SHA-256 |
|---|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---|---|
{v2_transition_text}

Повні дані кожної спроби, включно з candidate evaluator checks, додатковою вартістю перевірки кандидата, помилками, B0 raw streams і фазами, наведені в `transition-run-table.csv` та `analysis-summary.json`. Повні архіви перевірено чинним V4 verifier-ом; невдалі спроби перевірено окремою схемою PARTIAL_EXECUTION_EVIDENCE. Кожний рядок прив'язаний до digest окремого архіву або raw partial inventory.

### Часові та обчислювальні витрати трьох виміряних технічних повторів

| Показник | n | Missing | Mean ms | Median ms | Sample SD ms | Min–max ms | p90 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
{timing_text}

Ці повтори належать одній парі архітектурних станів; це описові технічні виміри. Вартість candidate validation — фактично виміряна перевірка кандидатних evaluators. Estimated added CI ms/build із рядків кандидата є окремою оцінкою, а не виміром повного CI.

## Технічні помилки і пропущені дані

V1 зафіксував чотири bubblewrap-помилки `Failed RTM_NEWADDR: Operation not permitted`; результат Ψ, план операцій і кандидат не спостерігалися. Часткові B0 каталоги не були збережені. {v1_negative}

Попередня технічна спроба V2 (run `40569757224`) зупинилася до калібрування через невідповідність ідентичності baseline у коді технічного preflight. Це окремий pre-measurement failure, а не одна з чотирьох transition-спроб і не результат B0/Ψ. Її raw hosted preflight ZIP має readback `{premeasurement_failures[0].get("archive_readback_status") if premeasurement_failures else "NOT_PRESENT"}`; SHA-256 наведено нижче.

| Workflow run | Stage | Calibration calls | Transitions | Ψ status | Error | Raw preflight ZIP SHA-256 |
|---:|---|---:|---:|---|---|---|
{premeasurement_text}

Окремо збережено перший post-measurement V2 запуск (run `40574090499`) та його заморожені partial archives. Усі чотири wrapper rows лишилися `FAILED` через `KeyError: 'evaluator_observations'`, але raw release readback показав завершений B0 та фактичний Ψ `HOLD` у кожній спробі, валідований, materialized-but-unapplied кандидат і parity із реконструйованим B0 на двох наявних candidate controls. Цей запуск не переписано; наступний freeze/run є окремою версіонованою спробою. Попередній release ZIP підтверджено локально за GitHub asset digest (`{postexecution_readback_failures[0].get("release", {}).get("outer_archive_sha256") if postexecution_readback_failures else "NOT_RECORDED"}`), однак його `.sha256` посилався на абсолютний шлях runner temp і не давав portable `sha256sum --check` після завантаження. Новий workflow виправляє sidecar і перевіряє саме downloaded bytes.

| Попередній workflow run | Execution ID | Wrapper status | Raw Ψ process | Actual decision | Candidate validation | Wrapper error | Partial archive SHA-256 |
|---:|---|---|---|---|---|---|---|
{prior_attempt_text}

У V2 невиміряні, не запущені, помилкові та частково збережені фази збережено окремо у `technical-failures.csv`; інфраструктурна помилка не інтерпретується як HOLD. Якщо Method Ψ не видав валідний result, статус — NOT_OBSERVED. Якщо фактичне рішення було HOLD, його reason codes і raw digest збережені без змін.

| Спроба цього freeze | Run status | Помилка / причина | Evidence class | Evidence SHA-256 |
|---|---|---|---|---|
{technical_failure_text}

## Обмеження інтерпретації

Чотири переходи є технічними повторами однієї пари станів, а не незалежними архітектурними одиницями. Три статичні evaluators і відома історична probe не дають оцінки загальної чутливості/специфічності або незалежного holdout. Перевірена source inspection не доводить семантичної адекватності, нормативної applicability, повноти obligation denominator, representation coverage чи runtime architectural quality. Навіть валідований кандидат не є застосованою або незалежно схваленою конфігурацією.

## Запропонований висновок

{_scientific_conclusion(transitions)}

## Трасування доказів

- V1: study `{v1_execution["study_id"]}`, run `40499692594`, release [evidence release](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-a05-owner-authorized-40499692594-1), calibration archive SHA-256 `{v1_calibration_archive_sha256}`, analysis inputs `historical-v1/calibration.zip` і `POST_RUN_PROBE_READBACK.json`.
- Попередня спроба V2: run `40574090499`, release [перша V2 evidence release](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-a05-owner-authorized-v2-40574090499-1), outer archive SHA-256 `{postexecution_readback_failures[0].get("release", {}).get("outer_archive_sha256") if postexecution_readback_failures else "NOT_RECORDED"}`, frozen `study-execution.json` SHA-256 `{postexecution_readback_failures[0].get("study_execution_sha256") if postexecution_readback_failures else "NOT_RECORDED"}`, readback-record SHA-256 `{postexecution_readback_failures[0].get("_record_sha256") if postexecution_readback_failures else "NOT_RECORDED"}`. Оригінальні wrapper failures і raw HOLD/candidate observations лишаються відокремленими від нового запуску.
- V2: study `{execution["study_id"]}`, frozen commit `{execution["freeze_commit"]}`, workflow run `{release_run}`, calibration archive SHA-256 `{calibration_archive_sha256}`; перехідні архіви й partial-evidence digests наведені у `transition-run-table.csv`.
- Обробка: `{study_v2.__name__}` і `analysis-summary.json`; descriptive mean/median/sample SD/min/max/nearest-rank p90; без об'єднання V1/V2, без inferential significance і без coverage percentage.
"""


def _sha256_file_from_mapping(readback: Mapping[str, Any]) -> str:
    return str(readback.get("_record_sha256") or "NOT_RECORDED")


def _read_preserved_premeasurement_failure(bundle: Path) -> dict[str, Any] | None:
    """Verify the retained first V2 technical stop and its raw hosted preflight ZIP."""
    protocol = bundle / "protocol-snapshot"
    record_path = protocol / study_v2.PREMEASUREMENT_FAILURE.name
    archive_path = protocol / study_v2.PREMEASUREMENT_ARTIFACT.name
    sidecar_path = protocol / study_v2.PREMEASUREMENT_ARTIFACT_SIDECAR.name
    present = [path.is_file() for path in (record_path, archive_path, sidecar_path)]
    if not any(present):
        return None
    if not all(present):
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PREMEASUREMENT_EVIDENCE_INCOMPLETE")
    record = _read_json(record_path)
    if (
        record.get("schema_version") != "MONO_CI_PSI_V2_PREMEASUREMENT_FAILURE_V1"
        or record.get("classification") != "PRE_MEASUREMENT_TECHNICAL_PREFLIGHT_FAILURE"
        or record.get("raw_github_artifact_sha256") != sha256_file(archive_path)
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PREMEASUREMENT_RECORD_MISMATCH")
    expected_sidecar = f"{sha256_file(archive_path)}  {archive_path.name}"
    if sidecar_path.read_text(encoding="ascii").strip() != expected_sidecar:
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PREMEASUREMENT_SIDECAR_MISMATCH")
    with zipfile.ZipFile(archive_path, "r") as zipped:
        if zipped.testzip() is not None:
            raise ContractValidationError("OWNER_AUTHORIZED_V2_PREMEASUREMENT_ZIP_CORRUPT")
        names = set(zipped.namelist())
        if not {"sandbox-preflight.json", "sandbox-preflight.json.sha256"} <= names:
            raise ContractValidationError("OWNER_AUTHORIZED_V2_PREMEASUREMENT_PREFLIGHT_MISSING")
        raw_preflight = zipped.read("sandbox-preflight.json")
        preflight = json.loads(raw_preflight)
        try:
            validate_payload(study_v2.PREFLIGHT_SCHEMA, preflight)
        except ContractValidationError as error:
            raise ContractValidationError(
                "OWNER_AUTHORIZED_V2_PREMEASUREMENT_PREFLIGHT_SCHEMA_INVALID"
            ) from error
        preflight_digest = hashlib.sha256(raw_preflight).hexdigest()
        internal_sidecar = zipped.read("sandbox-preflight.json.sha256").decode("ascii").strip()
        if internal_sidecar != f"{preflight_digest}  sandbox-preflight.json":
            raise ContractValidationError(
                "OWNER_AUTHORIZED_V2_PREMEASUREMENT_INTERNAL_DIGEST_MISMATCH"
            )
        if preflight.get("verification_status") != "PASS":
            raise ContractValidationError("OWNER_AUTHORIZED_V2_PREMEASUREMENT_PREFLIGHT_NOT_PASS")
    return {
        **record,
        "archive_readback_status": "PASS",
        "archive_sha256": sha256_file(archive_path),
        "preflight_sha256": preflight_digest,
    }


def analyze_bundle(bundle_root: Path, repository: Path, output_root: Path) -> dict[str, Any]:
    bundle = bundle_root.resolve(strict=True)
    repo = repository.resolve(strict=True)
    output = output_root.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ContractValidationError("OWNER_AUTHORIZED_V2_ANALYSIS_OUTPUT_MUST_BE_NEW")
    output.mkdir(parents=True)
    execution = _read_json(bundle / "study-execution.json")
    frozen_analysis_sha256 = _read_json(bundle / "protocol-snapshot/PRE_RUN_FREEZE.json")[
        "analysis_version"
    ]["sha256"]
    analysis_code_sha256 = sha256_file(Path(__file__))
    post_run_analysis_correction = analysis_code_sha256 != frozen_analysis_sha256
    premeasurement_failure = _read_preserved_premeasurement_failure(bundle)
    premeasurement_failures = [premeasurement_failure] if premeasurement_failure else []
    prior_readback_failure = _read_preserved_postexecution_readback_failure(bundle)
    postexecution_readback_failures = (
        [prior_readback_failure] if prior_readback_failure is not None else []
    )
    v2_calibration_verified = owner.verify_calibration_archive(bundle / "calibration.zip")
    v2_calibration_rows = (
        owner._read_jsonl(bundle / "calibration.zip")
        if hasattr(owner, "_read_jsonl")
        else analysis_v1._read_calibration_rows(bundle / "calibration.zip")
    )
    v2_calibration = analysis_v1._summarize_calibration(v2_calibration_rows)
    transitions = _transition_summaries(bundle, repo, execution)

    v1_execution = _read_json(bundle / "historical-v1/study-execution.json")
    v1_calibration_verified = owner.verify_calibration_archive(
        bundle / "historical-v1/calibration.zip"
    )
    v1_calibration = analysis_v1._read_calibration_rows(bundle / "historical-v1/calibration.zip")
    v1_calibration_summary = analysis_v1._summarize_calibration(v1_calibration)
    v1_readback = _read_json(bundle / "historical-v1/POST_RUN_PROBE_READBACK.json")
    v1_readback["_record_sha256"] = sha256_file(
        bundle / "historical-v1/POST_RUN_PROBE_READBACK.json"
    )

    evaluator_rows = []
    for study_id, rows in (
        (v1_execution["study_id"], v1_calibration),
        (execution["study_id"], v2_calibration_rows),
    ):
        for row in rows:
            evaluator_rows.append(
                {
                    "study_id": study_id,
                    **{
                        key: row.get(key)
                        for key in (
                            "execution_id",
                            "classification",
                            "source_condition",
                            "evaluator_id",
                            "repetition_index",
                            "is_warmup",
                            "attempt_index",
                            "source_commit_sha",
                            "source_tree_sha",
                            "application_tree_sha",
                            "process_duration_ms",
                            "scope_verification_duration_ms",
                            "process_exit_code",
                            "execution_status",
                            "compliance",
                            "inspection_status",
                            "finding_codes",
                            "raw_output_sha256",
                            "sample_status",
                            "error",
                        )
                    },
                }
            )
    _write_csv(
        output / "evaluator-samples.csv",
        evaluator_rows,
        [
            "study_id",
            "execution_id",
            "classification",
            "source_condition",
            "evaluator_id",
            "repetition_index",
            "is_warmup",
            "attempt_index",
            "source_commit_sha",
            "source_tree_sha",
            "application_tree_sha",
            "process_duration_ms",
            "scope_verification_duration_ms",
            "process_exit_code",
            "execution_status",
            "compliance",
            "inspection_status",
            "finding_codes",
            "raw_output_sha256",
            "sample_status",
            "error",
        ],
    )
    transition_csv_rows = []
    for transition_row in transitions:
        for observation in transition_row.get("b0_evaluator_outcomes", []):
            transition_csv_rows.append(
                {
                    "execution_id": transition_row["execution_id"],
                    "run_role": transition_row["run_role"],
                    "measured": transition_row["measured"],
                    "arm": "B0_UNCHANGED_RECONSTRUCTION",
                    **observation,
                    "method_decision": "",
                    "method_operations": "",
                    "candidate_state": "",
                    "method_duration_ms": "",
                    "evidence_sha256": transition_row.get("evidence_digest"),
                }
            )
        transition_csv_rows.append(
            {
                "execution_id": transition_row["execution_id"],
                "run_role": transition_row["run_role"],
                "measured": transition_row["measured"],
                "arm": "PSI_METHOD_DECISION",
                "architecture_state": "A0_4_TO_A0_5",
                "evaluator_id": "",
                "duration_ms": transition_row.get("full_transition_duration_ms"),
                "compliance": "",
                "method_decision": transition_row.get("method_decision"),
                "method_operations": _json_field(transition_row.get("operation_plan")),
                "candidate_state": transition_row.get("candidate_state"),
                "method_duration_ms": transition_row.get("method_execution_duration_ms"),
                "evidence_sha256": transition_row.get("evidence_digest"),
            }
        )
    _write_csv(
        output / "transition-samples.csv",
        transition_csv_rows,
        [
            "execution_id",
            "run_role",
            "measured",
            "arm",
            "architecture_state",
            "evaluator_id",
            "duration_ms",
            "exit_code",
            "execution_status",
            "process_observation_status",
            "stdout_sha256",
            "stderr_sha256",
            "compliance",
            "source_commit_sha",
            "output_sha256",
            "inspection_status",
            "method_decision",
            "method_operations",
            "candidate_state",
            "method_duration_ms",
            "evidence_sha256",
        ],
    )
    _write_csv(
        output / "transition-run-table.csv",
        transitions,
        [
            "execution_id",
            "run_role",
            "measured",
            "run_status",
            "b0_execution_status",
            "b0_evaluator_outcomes",
            "method_process_status",
            "method_process_exit_code",
            "method_decision",
            "governance_reason_codes",
            "operation_plan",
            "hold_reasons",
            "candidate_state",
            "candidate_configuration_sha256",
            "candidate_evaluators",
            "candidate_verification_status",
            "candidate_validation_cost_ms",
            "estimated_additional_ci_execution_ms_per_build",
            "full_transition_duration_ms",
            "method_execution_duration_ms",
            "evidence_digest",
            "evidence_classification",
            "error_or_hold_reasons",
            "source_revision_sha",
            "source_identity_status",
            "phase_status",
            "transition_record_sha256",
            "method_result_sha256",
            "raw_method_result_sha256",
        ],
    )
    failures = [row for row in transitions if row.get("run_status") != "COMPLETED"]
    technical_failures = [
        *failures,
        *[
            {
                "execution_id": row["execution_id"],
                "workflow_run_id": prior["workflow_run_id"],
                "run_role": row["role"],
                "run_status": row["wrapper_run_status"],
                "b0_execution_status": row["b0_execution_status"],
                "method_process_status": row["method_process_status"],
                "method_decision": row["method_decision"],
                "error_or_hold_reasons": row["wrapper_error"],
                "evidence_classification": "PARTIAL_EXECUTION_EVIDENCE",
                "evidence_digest": row["partial_archive_sha256"],
                "failure_stage": "POSTEXECUTION_READBACK",
                "archive_readback_status": "PASS_IN_PRIOR_RELEASE",
                "calibration_calls_started": prior["calibration"]["measured_calls"],
                "transition_attempts_started": 1,
                "candidate_state": row["candidate_state"],
                "candidate_validation_status": row["candidate_validation_status"],
                "candidate_validation_cost_ms": row["candidate_validation_cost_ms"],
                "method_execution_duration_ms": row["method_execution_duration_ms"],
                "method_result_sha256": row["method_result_sha256"],
            }
            for prior in postexecution_readback_failures
            for row in prior["transition_attempts"]
        ],
        *[
            {
                "execution_id": f"workflow-{row['workflow_run_id']}-premeasurement",
                "workflow_run_id": row["workflow_run_id"],
                "run_role": "PRE_MEASUREMENT",
                "run_status": "FAILED_BEFORE_MEASUREMENTS",
                "b0_execution_status": "NOT_EXECUTED",
                "method_process_status": row["method_psi_status"],
                "method_decision": row["method_decision"],
                "error_or_hold_reasons": row["error_code"],
                "evidence_classification": row["classification"],
                "evidence_digest": row["archive_sha256"],
                "failure_stage": row["failure_stage"],
                "archive_readback_status": row["archive_readback_status"],
                "calibration_calls_started": row["calibration_calls_started"],
                "transition_attempts_started": row["transition_attempts_started"],
            }
            for row in premeasurement_failures
        ],
    ]
    _write_csv(
        output / "technical-failures.csv",
        technical_failures,
        [
            "execution_id",
            "workflow_run_id",
            "run_role",
            "run_status",
            "b0_execution_status",
            "method_process_status",
            "method_decision",
            "error_or_hold_reasons",
            "evidence_classification",
            "evidence_digest",
            "failure_stage",
            "archive_readback_status",
            "calibration_calls_started",
            "transition_attempts_started",
            "candidate_state",
            "candidate_validation_status",
            "candidate_validation_cost_ms",
            "method_execution_duration_ms",
            "method_result_sha256",
        ],
    )
    measured_transitions = [row for row in transitions if row.get("measured")]
    measured_timing_summaries = _measured_timing_summaries(transitions, v2_calibration_rows)
    transition_duration_stats = analysis_v1.descriptive_statistics(
        row["full_transition_duration_ms"]
        for row in measured_transitions
        if row.get("full_transition_duration_ms") is not None
    )
    method_duration_stats = analysis_v1.descriptive_statistics(
        row["method_execution_duration_ms"]
        for row in measured_transitions
        if row.get("method_execution_duration_ms") is not None
    )
    candidate_cost_stats = analysis_v1.descriptive_statistics(
        row["candidate_validation_cost_ms"]
        for row in measured_transitions
        if row.get("candidate_validation_cost_ms") is not None
    )
    v1_transition_summary = {
        "planned": len(v1_execution["transition_runs"]),
        "completed": sum(
            row["run_status"] == "COMPLETED" for row in v1_execution["transition_runs"]
        ),
        "failed": sum(row["run_status"] == "FAILED" for row in v1_execution["transition_runs"]),
        "method_decision": "NOT_OBSERVED",
        "method_results": 0,
    }
    comparison = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_V1_V2_COMPARISON_V1",
        "v1": {
            "study_id": v1_execution["study_id"],
            "workflow_run_id": 40499692594,
            "calibration": v1_calibration_summary,
            "transition_summary": v1_transition_summary,
            "probe_readback": {
                "original_negative_rows_failed": 33,
                "raw_outputs_preserved": v1_readback["counts"]["archived_evaluator_outputs"],
                "post_run_scope_pass": v1_readback["counts"]["post_run_scope_pass"],
                "readback_sha256": sha256_file(
                    bundle / "historical-v1/POST_RUN_PROBE_READBACK.json"
                ),
            },
            "calibration_archive_sha256": v1_calibration_verified["archive_sha256"],
        },
        "v2": {
            "study_id": execution["study_id"],
            "workflow_run_id": execution.get("workflow_run_id"),
            "calibration": v2_calibration,
            "transition_summary": execution["transition_summary"],
            "method_decisions": dict(
                sorted(
                    Counter(
                        str(row.get("method_decision"))
                        for row in transitions
                        if row.get("method_decision") is not None
                    ).items()
                )
            ),
            "premeasurement_failures": premeasurement_failures,
            "calibration_archive_sha256": v2_calibration_verified["archive_sha256"],
        },
        "previous_v2_postexecution_readback_attempt": postexecution_readback_failures,
        "v1_v2_samples_pooled": False,
    }
    summary = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_ANALYSIS_V3",
        "study_id": execution["study_id"],
        "classification": execution["classification"],
        "workflow_run_id": execution.get("workflow_run_id"),
        "calibration_archive": v2_calibration_verified,
        "calibration": v2_calibration,
        "transition_runs": transitions,
        "transition_summary": execution["transition_summary"],
        "transition_timing": {
            "measured_full_transition": transition_duration_stats,
            "measured_method_execution": method_duration_stats,
            "candidate_validation_cost": candidate_cost_stats,
            **measured_timing_summaries,
            "candidate_cost_interpretation": "Only actual candidate validation runs; otherwise unavailable.",
            "method_cpu": "NOT_AVAILABLE_PER_METHOD_PROCESS",
            "monetary_cost": "NOT_MEASURED",
        },
        "comparison_v1_v2": comparison,
        "transition_failures": failures,
        "technical_failures": technical_failures,
        "premeasurement_failures": premeasurement_failures,
        "postexecution_readback_failures": postexecution_readback_failures,
        "gates": execution["gates"],
        "statistical_interpretation": {
            "architecture_level_units": 1,
            "technical_transition_repetitions": len(measured_transitions),
            "significance_tests": "NOT_PERFORMED",
            "coverage_percentage": "NOT_COMPUTED",
        },
        "data_processing": {
            "analysis_module": "experiments.execution.tooling.mono_ci_psi_owner_authorized_v2_analysis",
            "descriptive_statistics_module": "experiments.execution.tooling.mono_ci_psi_owner_authorized_analysis",
            "analysis_code_sha256": analysis_code_sha256,
            "frozen_pre_run_analysis_code_sha256": frozen_analysis_sha256,
            "post_run_analysis_correction": post_run_analysis_correction,
            "p90": "nearest_rank",
            "v1_v2_samples_pooled": False,
        },
    }
    _write_json(output / "analysis-summary.json", summary)
    figure_path = output / "evaluator-time-distributions.svg"
    analysis_v1._svg_figure(v2_calibration_rows, figure_path)
    _strip_trailing_whitespace(figure_path)
    handoff = _handoff(
        execution=execution,
        v1_execution=v1_execution,
        v1_calibration_rows=v1_calibration,
        v1_calibration_summary=v1_calibration_summary,
        v2_calibration_summary=v2_calibration,
        transitions=transitions,
        calibration_archive_sha256=v2_calibration_verified["archive_sha256"],
        v1_calibration_archive_sha256=v1_calibration_verified["archive_sha256"],
        v1_readback=v1_readback,
        premeasurement_failures=premeasurement_failures,
        postexecution_readback_failures=postexecution_readback_failures,
        transition_failures=failures,
    )
    if post_run_analysis_correction:
        b0_stats = measured_timing_summaries["measured_transition_b0_evaluator_process_times"]
        calibration_stats = measured_timing_summaries[
            "measured_calibration_evaluator_process_times"
        ]
        v1_counts = _calibration_call_summary(
            v1_calibration_summary, int(v1_execution["calibration"].get("planned_calls", 0))
        )
        v2_counts = _calibration_call_summary(
            v2_calibration, int(execution["calibration"].get("planned_calls", 0))
        )
        correction_note = (
            "\n\n## Пост-run корекція похідного аналізу\n\n"
            f"Цей звіт є post-run корекцією для run `{execution.get('workflow_run_id')}`; "
            "вимірювання та raw archives не змінювалися. Первісний freeze прив'язував код аналізу "
            f"до SHA-256 `{frozen_analysis_sha256}`; код цієї корекції має SHA-256 "
            f"`{analysis_code_sha256}`. У V3 `analysis-summary.json` окремо подає "
            f"{calibration_stats['n']} калібрувальних B0 evaluator-процесів і "
            f"{b0_stats['n']} B0 evaluator-процесів у виміряних transition runs; "
            "попереднє неоднозначне агреговане поле замінене цими двома ключами. "
            "Порівняльна таблиця повноти тепер окремо рахує measured sample rows і warmups "
            f"з архівів: V1 — {v1_counts['measured_successful_calls']} успішних, "
            f"{v1_counts['measured_failed_calls']} failed виміряних samples і "
            f"{v1_counts['warmup_calls']} warmups; V2 — "
            f"{v2_counts['measured_successful_calls']} успішних, "
            f"{v2_counts['measured_failed_calls']} failed виміряних samples і "
            f"{v2_counts['warmup_calls']} warmups. Це відділяє warmup outcomes, які входили "
            "до попередніх aggregate execution counts, від виміряних повторів. "
            "Первинна release залишається byte-preserved; її readback і freeze verification "
            "пройшли до цієї корекції.\n"
        )
        handoff = handoff.replace(
            "\n## Класифікація і межі\n", correction_note + "\n## Класифікація і межі\n", 1
        )
        correction_path = output / "POST_RUN_ANALYSIS_CORRECTION.md"
        correction_path.write_text(correction_note.lstrip(), encoding="utf-8")
    (output / "OWNER_AUTHORIZED_RESULTS_UK_V2.md").write_text(handoff, encoding="utf-8")
    insertion_map = f"""# Монографія: карта вставлення для ΔA5 DEVELOPMENT V1/V2

Цей файл підготовлений для ручного перенесення до наявного Google Doc. Документ напряму не змінювався.

## Методологія експерименту

Вставити опис owner-authorized exploratory DEVELOPMENT V1/V2, точну пару A0.4→A0.5, незмінний B0 та чинну реалізацію Ψ, межі V1/V2, Docker preflight і джерельну прив'язку scope verifier-а. Використовувати перший розділ `OWNER_AUTHORIZED_RESULTS_UK_V2.md` разом із V2 `PROTOCOL_V2.md`. Обов'язково зазначити одну архітектурну одиницю, технічні повтори, TEST_ONLY evidence і незмінні G1/G4 межі.

## Результати дослідження

Вставити V1/V2 таблицю повноти, V2 таблицю фактичних B0/Ψ результатів, таблицю часу й candidate-validation cost, технічні помилки та SVG фігуру з `OWNER_AUTHORIZED_RESULTS_UK_V2.md`, `transition-run-table.csv`, `technical-failures.csv`, `evaluator-samples.csv` і `evaluator-time-distributions.svg`. Окремо зазначити попередній run 40574090499 як wrapper readback failure із збереженими raw HOLD результатами, не об'єднуючи його повтори з новим freeze. У V3 `analysis-summary.json` calibration B0 evaluator process times і transition-level B0 evaluator process times подані окремо; ці дві сукупності не об'єднувати. У таблиці повноти брати planned, measured success/failure, warmups і not-run із sample rows; warmups не зараховувати до measured counts і не підміняти їх legacy aggregate `measured_calls`. Для кожного числового рядка зберегти study `{execution["study_id"]}`, workflow run `{execution.get("workflow_run_id")}`, calibration archive SHA-256 `{v2_calibration_verified["archive_sha256"]}` або відповідний evidence digest і процедуру обробки з `analysis-summary.json`. У V1 частині посилатися на run 40499692594 та archive SHA-256 `{v1_calibration_verified["archive_sha256"]}`.

## Обговорення

Вставити фактичні B0/Ψ outcomes і технічні збої з `technical-failures.csv`. Пояснити, що інфраструктурна помилка не є HOLD; HOLD зазначається лише якщо його повернув Method Ψ. Обмежити висновки конкретними статичними evaluators, відомою probe, неповним authority та evidence scope. Не трактувати чотири технічні повтори як незалежні transitions.

## Висновки

Використовувати лише розділ «Запропонований висновок» у `OWNER_AUTHORIZED_RESULTS_UK_V2.md`, замінюючи формулювання за фактичним результатом запуску. Не робити загальних висновків про наукову перевагу, verified mandatory coverage, runtime quality або G1/G4.
"""
    (output / "MONOGRAPH_INSERTION_MAP_UK.md").write_text(insertion_map, encoding="utf-8")
    for csv_path in output.glob("*.csv"):
        _normalize_csv_line_endings(csv_path)
    checksums = {
        path.name: sha256_file(path) for path in sorted(output.iterdir()) if path.is_file()
    }
    _write_json(output / "ANALYSIS_SHA256SUMS.json", checksums)
    return {
        "output_path": str(output),
        "summary": summary,
        "analysis_checksums": checksums,
        "verification_status": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        result = analyze_bundle(arguments.bundle, arguments.repository, arguments.output)
    except (ContractValidationError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
