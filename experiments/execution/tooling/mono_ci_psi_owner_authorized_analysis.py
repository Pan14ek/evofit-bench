"""Derive descriptive tables, figure and Ukrainian handoff from owner-authorized raw archives."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_file
from experiments.execution.tooling.mono_ci_b0_psi_archive import verify_psi_transition_archive
from experiments.execution.tooling.mono_ci_psi_owner_authorized import verify_calibration_archive


def nearest_rank(values: list[float], probability: float) -> float | None:
    """Return a nearest-rank empirical quantile without interpolation."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def descriptive_statistics(values: Iterable[float]) -> dict[str, float | int | None]:
    """Compute preregistered descriptive statistics for finite timing observations."""
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if not finite:
        return {
            "n": 0,
            "mean_ms": None,
            "median_ms": None,
            "sample_standard_deviation_ms": None,
            "minimum_ms": None,
            "maximum_ms": None,
            "p90_nearest_rank_ms": None,
        }
    p90 = nearest_rank(finite, 0.9)
    return {
        "n": len(finite),
        "mean_ms": round(statistics.mean(finite), 3),
        "median_ms": round(statistics.median(finite), 3),
        "sample_standard_deviation_ms": (
            round(statistics.stdev(finite), 3) if len(finite) > 1 else None
        ),
        "minimum_ms": round(min(finite), 3),
        "maximum_ms": round(max(finite), 3),
        "p90_nearest_rank_ms": round(p90, 3) if p90 is not None else None,
    }


def resource_statistics(values: Iterable[float | None]) -> dict[str, float | int | None]:
    """Summarize process CPU seconds while retaining unavailable and empty states."""
    finite = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not finite:
        return {
            "n": 0,
            "mean_seconds": None,
            "sample_standard_deviation_seconds": None,
            "minimum_seconds": None,
            "maximum_seconds": None,
        }
    return {
        "n": len(finite),
        "mean_seconds": round(statistics.mean(finite), 6),
        "sample_standard_deviation_seconds": (
            round(statistics.stdev(finite), 6) if len(finite) > 1 else None
        ),
        "minimum_seconds": round(min(finite), 6),
        "maximum_seconds": round(max(finite), 6),
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(pretty_json_bytes(value))


def _write_csv(path: Path, rows: list[Mapping[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _outcome_label(row: Mapping[str, Any]) -> str:
    compliance = row.get("compliance")
    codes = row.get("finding_codes") or []
    if compliance == "NON_COMPLIANT":
        return "NON_COMPLIANT_FINDING_REPORTED"
    if compliance == "COMPLIANT" and not codes:
        return "COMPLIANT_NO_FINDING_REPORTED"
    if compliance in {"NOT_EVALUABLE", "UNKNOWN", "NOT_APPLICABLE"}:
        return str(compliance)
    return "OTHER_OR_MISSING"


def _read_calibration_rows(archive: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(archive, "r") as zipped:
        rows = []
        for line in zipped.read("measurement-records.jsonl").decode("utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ContractValidationError("OWNER_AUTHORIZED_RAW_SAMPLE_SHAPE_INVALID")
                rows.append(value)
        return rows


def _summarize_calibration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["source_condition"], row["evaluator_id"])].append(row)
    summaries = []
    for (condition, evaluator), group in sorted(groups.items()):
        measured = [
            row
            for row in group
            if row.get("sample_status") == "MEASURED" and not row.get("is_warmup")
        ]
        process_times = [
            row["process_duration_ms"]
            for row in measured
            if row.get("process_duration_ms") is not None
        ]
        scope_times = [
            row["scope_verification_duration_ms"]
            for row in measured
            if row.get("scope_verification_duration_ms") is not None
        ]
        summaries.append(
            {
                "source_condition": condition,
                "evaluator_id": evaluator,
                "planned_measured_samples": sum(
                    row.get("source_condition") == condition
                    and row.get("evaluator_id") == evaluator
                    and not row.get("is_warmup")
                    for row in rows
                ),
                "measured_samples": len(measured),
                "failed_samples": sum(
                    row.get("sample_status") == "FAILED" and not row.get("is_warmup")
                    for row in group
                ),
                "not_run_samples": sum(
                    row.get("sample_status") == "NOT_RUN_BUDGET_EXHAUSTED"
                    and not row.get("is_warmup")
                    for row in group
                ),
                "process_duration": descriptive_statistics(process_times),
                "scope_call_duration": descriptive_statistics(scope_times),
                "cpu_user": resource_statistics(row.get("cpu_user_seconds") for row in measured),
                "cpu_system": resource_statistics(
                    row.get("cpu_system_seconds") for row in measured
                ),
                "outcome_counts": dict(
                    sorted(Counter(_outcome_label(row) for row in measured).items())
                ),
                "finding_code_counts": dict(
                    sorted(
                        Counter(
                            code for row in measured for code in row.get("finding_codes", [])
                        ).items()
                    )
                ),
                "inspection_status_counts": dict(
                    sorted(Counter(str(row.get("inspection_status")) for row in measured).items())
                ),
            }
        )
    return {
        "warmup_samples": sum(bool(row.get("is_warmup")) for row in rows),
        "measured_planned_samples": sum(not row.get("is_warmup") for row in rows),
        "measured_successful_samples": sum(
            row.get("sample_status") == "MEASURED" and not row.get("is_warmup") for row in rows
        ),
        "measured_failed_samples": sum(
            row.get("sample_status") == "FAILED" and not row.get("is_warmup") for row in rows
        ),
        "measured_not_run_samples": sum(
            row.get("sample_status") == "NOT_RUN_BUDGET_EXHAUSTED" and not row.get("is_warmup")
            for row in rows
        ),
        "cells": summaries,
    }


def _read_transition_archives(
    bundle: Path,
    repository: Path,
    execution: Mapping[str, Any],
    extract_root: Path,
) -> list[dict[str, Any]]:
    run_summaries = []
    declared = {
        row["run_archive"]: row
        for row in execution.get("transition_runs", [])
        if row.get("run_archive_sha256")
    }
    for archive_name, outer in sorted(declared.items()):
        extract_to = extract_root / archive_name.removesuffix(".zip")
        verified = verify_psi_transition_archive(
            bundle / archive_name, repository=repository, extract_to=extract_to
        )
        if verified["archive_sha256"] != outer["run_archive_sha256"]:
            raise ContractValidationError("OWNER_AUTHORIZED_TRANSITION_ARCHIVE_DIGEST_MISMATCH")
        record = _read_json(extract_to / "development_run.json")
        raw = _read_json(extract_to / record["psi"]["raw_result_path"])
        plan = raw.get("operation_plan", {})
        governance = raw.get("governance", {})
        candidate = raw.get("candidate")
        b0_rows = [
            row
            for row in record.get("evaluator_observations", [])
            if row.get("evaluator_id") in {"AC_PUBLIC_API", "AC_MODULE_GRAPH"}
        ]
        extension = _read_json(extract_to / record["a05_extension"]["path"])
        clean = extension["positive_condition"]["evaluator"]
        summary = {
            "archive": archive_name,
            "archive_sha256": verified["archive_sha256"],
            "archive_verification": verified["verification_status"],
            "execution_id": record["execution_id"],
            "source_revision_sha": record["source_revision_sha"],
            "study_readiness": record["study_readiness"],
            "measurement_status": record["measurement_status"],
            "p_algorithm_status": record["p_algorithm_status"],
            "g1": record["g1"],
            "g4": record["g4"],
            "reference_gate": record["reference_gate"],
            "psi": {
                "decision": governance.get("result"),
                "reason_codes": governance.get("reason_codes", []),
                "operation_plan": plan.get("operations", []),
                "operation_hold_reasons": plan.get("hold_reasons", []),
                "candidate_state": "NOT_MATERIALIZED"
                if candidate is None
                else "MATERIALIZED_UNAPPLIED",
                "candidate_sha256": raw.get("candidate_sha256"),
                "candidate_changes": candidate.get("changes", [])
                if isinstance(candidate, dict)
                else [],
                "prediction_emitted": record["psi"].get("prediction_emitted"),
                "method_duration_ms": record["psi"].get("execution_duration_ms"),
                "method_result_sha256": record["psi"].get("raw_result_sha256"),
                "scoring": record["psi"].get("scoring"),
            },
            "B0": [
                {
                    "architecture_state": row["architecture_state"],
                    "evaluator_id": row["evaluator_id"],
                    "duration_ms": row["duration_ms"],
                    "exit_code": row["process_exit_code"],
                    "execution_status": row["execution_status"],
                    "compliance": row["compliance"],
                    "source_commit_sha": row["source_commit_sha"],
                    "output_sha256": row["output_sha256"],
                }
                for row in b0_rows
            ],
            "A0_5_clean_ownership": {
                "compliance": clean["compliance"],
                "duration_ms": clean["duration_ms"],
                "finding_codes": clean["finding_codes"],
                "inspection_status": clean["inspection_status"],
                "output_sha256": clean["output_sha256"],
            },
            "existing_negative_probe": [
                {
                    "evaluator_id": row["evaluator_id"],
                    "compliance": row["compliance"],
                    "duration_ms": row["duration_ms"],
                    "finding_codes": row["finding_codes"],
                    "inspection_status": row["inspection_status"],
                    "output_sha256": row["output_sha256"],
                }
                for row in extension["negative_condition"]["evaluators"]
            ],
        }
        outer_outcome = outer.get("outcome")
        if outer_outcome is not None and (
            outer.get("execution_id") != summary["execution_id"]
            or outer_outcome.get("Psi", {}).get("method_result_sha256")
            != summary["psi"]["method_result_sha256"]
        ):
            raise ContractValidationError("OWNER_AUTHORIZED_OUTER_RUN_SUMMARY_MISMATCH")
        run_summaries.append(summary)
    return run_summaries


def _svg_figure(calibration: list[dict[str, Any]], destination: Path) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    matplotlib.rcParams["svg.hashsalt"] = "evofitbench-owner-authorized-a05-v1"
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    matplotlib.rcParams["font.size"] = 9
    from matplotlib import pyplot as plt

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in calibration:
        if row.get("sample_status") == "MEASURED" and not row.get("is_warmup"):
            groups[(row["source_condition"], row["evaluator_id"])].append(row)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(groups)
    figure, axis = plt.subplots(figsize=(11.5, max(4.5, 0.62 * len(ordered) + 1.7)))
    values_by_cell = [
        [
            float(row["process_duration_ms"])
            for row in groups[key]
            if row.get("process_duration_ms") is not None
        ]
        for key in ordered
    ]
    positions = list(range(1, len(ordered) + 1))
    nonempty_positions = [
        position for position, values in zip(positions, values_by_cell, strict=True) if values
    ]
    nonempty_values = [values for values in values_by_cell if values]
    if nonempty_values:
        artists = axis.boxplot(
            nonempty_values,
            positions=nonempty_positions,
            vert=False,
            patch_artist=True,
            showfliers=False,
            widths=0.55,
        )
        for box in artists["boxes"]:
            box.set(facecolor="#b7d7ea", edgecolor="#27678d")
        for median in artists["medians"]:
            median.set(color="#a33", linewidth=1.8)
        for position, values in zip(positions, values_by_cell, strict=True):
            if values:
                axis.scatter(
                    values, [position] * len(values), s=17, color="#174a6e", alpha=0.75, zorder=3
                )
    axis.set_yticks(positions, [f"{condition} · {evaluator}" for condition, evaluator in ordered])
    axis.set_xlabel("Evaluator process elapsed time (ms)")
    axis.set_title(
        "Evaluator timing by source condition\n"
        "Measured technical repetitions; warmups excluded; one architecture-level transition",
        loc="left",
        fontweight="bold",
    )
    axis.grid(axis="x", color="#e4e8ed", linewidth=0.8)
    for spine in ("top", "right", "left"):
        axis.spines[spine].set_visible(False)
    axis.tick_params(axis="y", length=0)
    figure.tight_layout()
    figure.savefig(
        destination,
        format="svg",
        metadata={"Date": None, "Creator": "EvoFitBench owner-authorized analysis"},
    )
    plt.close(figure)


def _budget_sensitivity(calibration: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [
        float(row["scope_verification_duration_ms"])
        for row in calibration
        if row.get("sample_status") == "MEASURED"
        and not row.get("is_warmup")
        and row.get("scope_verification_duration_ms") is not None
    ]
    p90 = nearest_rank(durations, 0.9)
    reserve_seconds = 900
    scenarios = []
    for total_seconds in (1800, 2700, 3600):
        available_seconds = max(0, total_seconds - reserve_seconds)
        scenarios.append(
            {
                "total_budget_seconds": total_seconds,
                "setup_archive_reserve_seconds": reserve_seconds,
                "measured_execution_seconds": available_seconds,
                "estimated_evaluator_calls_at_p90": (
                    int(available_seconds * 1000 // p90) if p90 and p90 > 0 else None
                ),
            }
        )
    return {
        "scope_call_duration_p90_ms": round(p90, 3) if p90 is not None else None,
        "sample_count": len(durations),
        "scenarios": scenarios,
        "interpretation": (
            "Evaluator-call planning proxy only; does not estimate Ψ candidate cost "
            "or authorize a budget."
        ),
    }


def _render_handoff(
    summary: Mapping[str, Any],
    execution: Mapping[str, Any],
    transition_runs: list[dict[str, Any]],
    calibration_archive_sha: str,
) -> str:
    def fmt(value: Any) -> str:
        return "—" if value is None else str(value)

    calibration_rows = []
    for cell in summary["calibration"]["cells"]:
        times = cell["process_duration"]
        calibration_rows.append(
            (
                "| {evaluator} | {condition} | {n} | {fail} | {mean} | {median} | "
                "{sd} | {min}–{max} | {p90} |"
            ).format(
                evaluator=cell["evaluator_id"],
                condition=cell["source_condition"],
                n=times["n"],
                fail=cell["failed_samples"] + cell["not_run_samples"],
                mean=fmt(times["mean_ms"]),
                median=fmt(times["median_ms"]),
                sd=fmt(times["sample_standard_deviation_ms"]),
                min=fmt(times["minimum_ms"]),
                max=fmt(times["maximum_ms"]),
                p90=fmt(times["p90_nearest_rank_ms"]),
            )
        )
    psi_rows = []
    for run in transition_runs:
        psi = run["psi"]
        plan_row = next(
            item
            for item in execution["transition_runs"]
            if item.get("execution_id") == run["execution_id"]
        )
        measured = "так" if plan_row.get("measured") else "ні, warmup"
        psi_rows.append(
            f"| {run['execution_id']} | {measured} | {psi['decision']} | "
            f"{len(psi['operation_plan'])} | {psi['candidate_state']} | "
            f"{psi['method_duration_ms']} | {psi['method_result_sha256']} |"
        )
    measured_runs = [
        run
        for run in transition_runs
        if any(
            item.get("execution_id") == run["execution_id"] and item.get("measured")
            for item in execution["transition_runs"]
        )
    ]
    decisions = Counter(run["psi"]["decision"] for run in measured_runs)
    operation_counts = [len(run["psi"]["operation_plan"]) for run in measured_runs]
    transition_stats = descriptive_statistics(
        float(run["psi"]["method_duration_ms"])
        for run in measured_runs
        if run["psi"]["method_duration_ms"] is not None
    )
    calibration_table = "\n".join(calibration_rows)
    psi_table = "\n".join(psi_rows)
    archive_digests_text = "\n".join(
        f"- {run['archive']}: SHA-256 {run['archive_sha256']} — {run['archive_verification']}."
        for run in transition_runs
    )
    plan_by_id = {item["execution_id"]: item for item in execution.get("transition_runs", [])}
    b0_psi_rows = []
    probe_rows = []
    for run in transition_runs:
        plan = plan_by_id.get(run["execution_id"], {})
        by_state: dict[str, list[str]] = defaultdict(list)
        for observation in run["B0"]:
            by_state[observation["architecture_state"]].append(
                f"{observation['evaluator_id']}={observation['compliance']}"
            )
        b0_04 = "; ".join(sorted(by_state.get("A0_4_REPORT_QUERY_PORT", []))) or "—"
        b0_05 = "; ".join(sorted(by_state.get("A0_5_MODULE_DATA_OWNERSHIP", []))) or "—"
        b0_psi_rows.append(
            f"| {run['execution_id']} | {'так' if plan.get('measured') else 'ні, warmup'} | "
            f"{b0_04} | {b0_05} | {run['psi']['decision']} | "
            f"{len(run['psi']['operation_plan'])} | {run['psi']['candidate_state']} | "
            f"{fmt(plan.get('full_transition_duration_ms'))} |"
        )
        clean = run["A0_5_clean_ownership"]
        finding_codes = ", ".join(clean["finding_codes"]) or "—"
        probe_rows.append(
            f"| {run['execution_id']} | чистий A0.5 | AC_DATA_OWNERSHIP | "
            f"{clean['compliance']} | {finding_codes} | {clean['inspection_status']} |"
        )
        for observation in run["existing_negative_probe"]:
            finding_codes = ", ".join(observation["finding_codes"]) or "—"
            probe_rows.append(
                f"| {run['execution_id']} | відома негативна проба | "
                f"{observation['evaluator_id']} | "
                f"{observation['compliance']} | {finding_codes} | "
                f"{observation['inspection_status']} |"
            )
    failure_rows = [
        row for row in execution.get("transition_runs", []) if row.get("run_status") != "COMPLETED"
    ]
    failure_table = (
        "\n".join(
            f"| {row['execution_id']} | {row.get('run_status')} | "
            f"{json.dumps(row.get('error'), ensure_ascii=False)} |"
            for row in failure_rows
        )
        or "| — | немає | — |"
    )
    b0_psi_table = "\n".join(b0_psi_rows) or "| — | — | — | — | — | — | — |"
    probe_table = "\n".join(probe_rows) or "| — | — | — | — | — | — |"
    budget_sensitivity = summary["budget_sensitivity"]
    budget_rows = "\n".join(
        f"| {row['total_budget_seconds'] // 60} | {row['setup_archive_reserve_seconds'] // 60} | "
        f"{row['measured_execution_seconds'] // 60} | "
        f"{fmt(row['estimated_evaluator_calls_at_p90'])} |"
        for row in budget_sensitivity["scenarios"]
    )
    resource_rows = [
        (
            f"| evaluator · {cell['source_condition']} · {cell['evaluator_id']} | "
            f"{cell['cpu_user']['n']} | {fmt(cell['cpu_user']['mean_seconds'])} | "
            f"{fmt(cell['cpu_system']['mean_seconds'])} |"
        )
        for cell in summary["calibration"]["cells"]
    ]
    transition_cpu = summary["transition_resources"]
    resource_rows.append(
        f"| full B0/Ψ transition | {transition_cpu['cpu_user']['n']} | "
        f"{fmt(transition_cpu['cpu_user']['mean_seconds'])} | "
        f"{fmt(transition_cpu['cpu_system']['mean_seconds'])} |"
    )
    resource_table = "\n".join(resource_rows)
    full_transition_stats = transition_cpu["full_transition_duration"]
    return f"""# Результати власницьки авторизованого DEVELOPMENT-дослідження ΔA5

**Дослідження:** {execution["study_id"]}<br>
**Класифікація:** DEVELOPMENT_CALIBRATION та EXPLORATORY_DEVELOPMENT.<br>
**Авторизація:** пряма інструкція користувача від 2026-10-27;
особу поза розмовою не перевірено, підпис або незалежне підтвердження відсутні.<br>
**Протокол:** SHA-256 {execution["protocol_sha256"]}<br>
**Фіксація до виконання:** commit {execution["freeze_commit"]},
SHA-256 запису фіксації {execution["freeze_record_sha256"]}.

## Методика та межі

Порівнювались незмінний B0 як проспективно реконструйована конфігурація
з двох контролів AC_PUBLIC_API і AC_MODULE_GRAPH та фактичне рішення
ізольованої DEVELOPMENT-реалізації Ψ на переході A0.4→A0.5.
Точні вихідні commit-и: A0.4 {execution["source_identities"]["a04_commit"]}
і A0.5 {execution["source_identities"]["a05_commit"]}; дерева застосунку однакові.
B0 не є історичною або схваленою конфігурацією.

Калібрування охопило три наявні статичні оцінювачі на чистому A0.5
та на повторно відтвореній історичній негативній пробі PR #56.
Проба не є новим holdout і не передавалась Ψ. План передбачав один прогрів
та десять вимірюваних технічних повторів на кожну комбінацію оцінювач×умова.
Повний запуск B0/Ψ повторено тричі після одного прогріву. Це чотири технічні
виконання одного переходу, тобто один архітектурний експериментальний об'єкт.

Вимір часу оцінювача — монотонний інтервал процесу CLI; час scope-перевірки
наведено окремо. Час Ψ взято з наявного ізольованого раннера; подетапні
тривалості Ψ не надаються контрактом і не оцінюються. CPU містить ресурси
процесу раннера та дочірніх процесів, включно з Git і перевіркою scope;
окремий RSS процесу недоступний. Бюджет виконання — 45 хвилин: межа CI workflow
60 хвилин мінус авторський резерв 15 хвилин на підготовку й перевірку архіву.
Розподіл 15/30 хвилин між калібруванням і повними запусками є авторським
операційним припущенням, а не незалежною моделлю вартості.

## Результати калібрування

Часи подано в мілісекундах. Статистика використовує лише успішні вимірювані
повтори; прогріви зберігаються у вихідних даних, але виключені з підсумку.
p90 — найближчий ранг.

| Оцінювач | Умова | n | помилки/пропуски | середнє | медіана | SD | мін–макс | p90 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{calibration_table}

![Розподіл часу виконання оцінювачів](evaluator-time-distributions.svg)

Значення compliance і коди finding для кожного повтору наведено у файлі
evaluator-samples.csv; вихідний JSON оцінювача, stdout/stderr та inspection
coverage зберігаються у калібрувальному архіві. Результати показують поведінку
реалізації на цих конкретних джерелах; без незалежної семантичної перевірки
вони не встановлюють валідність представлення чи загальну точність.

## Фактичні результати B0 та Ψ

Таблиця зіставляє незмінну конфігурацію B0 на двох станах та окреме рішення Ψ.
Це описове порівняння виходів одного пайплайна, без оцінки coverage
або правильності операцій.

| Run | Вимір | B0 A0.4 | B0 A0.5 | Ψ | Операцій | Кандидат | Увесь запуск, мс |
|---|---|---|---|---|---:|---|---:|
{b0_psi_table}

### Результати контрольованих вихідних умов

| Виконання | Джерело | Оцінювач | Compliance | Finding codes | Перевірка інспекції |
|---|---|---|---|---|---|
{probe_table}

| Виконання | Підсумок | Рішення Ψ | Операції | Кандидат | Ψ, мс | Digest результату |
|---|---|---|---:|---|---:|---|
{psi_table}

Для вимірюваних запусків рішення: {json.dumps(dict(decisions), ensure_ascii=False)};
кількість операцій: {json.dumps(operation_counts)}. Описова статистика часу
ізольованого процесу Ψ: n={transition_stats["n"]}, середнє={fmt(transition_stats["mean_ms"])} мс,
медіана={fmt(transition_stats["median_ms"])} мс,
SD={fmt(transition_stats["sample_standard_deviation_ms"])} мс,
min–max={fmt(transition_stats["minimum_ms"])}–{fmt(transition_stats["maximum_ms"])} мс.
Час повного запуску B0/Ψ: n={full_transition_stats["n"]},
середнє={fmt(full_transition_stats["mean_ms"])} мс,
медіана={fmt(full_transition_stats["median_ms"])} мс,
min–max={fmt(full_transition_stats["minimum_ms"])}–{fmt(full_transition_stats["maximum_ms"])} мс.
Результати B0, Ψ та післяметодної проби збережені у transition-samples.csv.

Кандидат, якщо він матеріалізований, є діагностичним і не застосовувався
до архітектури. Рішення Ψ, план операцій, прапорець prediction та хеш кандидата
читаються з сирого результату; HOLD не трактується як успішна адаптація.
B0 та Ψ виконувались в одному наявному DEVELOPMENT-пайплайні, однак незалежного
score або вимірювання фактичного покриття після застосування кандидата немає.

## Покриття та невизначеність

Перевірене mandatory-coverage: **UNKNOWN; відсоток не обчислювався**.
Усі 18 applicability рядків залишаються невідомими, дев'ять пар у PR #57
не пройшли незалежну семантичну оцінку, реконструйований B0 не схвалений,
а незалежний scorer/reference відсутній. Отже, ці спостереження не відповідають
на питання про кращу відповідність адаптації і не підтверджують причинне
відновлення покриття.

## Бюджетна чутливість

Для планування evaluator-калібрування використано p90 виміряного зовнішнього
часу «оцінювач + перевірка scope» з цієї вибірки. Сценарії резервують 15 хвилин
загального ліміту на setup/readback/archive; число викликів є арифметичною
межею за цим емпіричним p90, без черги, варіацій runner або Ψ compute cost.
Це чутливість операційного ліміту, а не затверджена модель вартості
чи схвалення бюджету.

| Загальний ліміт, хв | Резерв, хв | Вимірювання, хв | Орієнтовні evaluator calls за p90 |
|---:|---:|---:|---:|
{budget_rows}

## Ресурси процесора

CPU часу виміряно для окремого evaluator call і для повного transition runner.
Дочірній CPU включає evaluator/Git/scope-процеси; CPU самого ізольованого
процесу Ψ окремо контрактом не надається. Peak RSS процесу недоступний.

| Межа | n | CPU user, середнє (с) | CPU system, середнє (с) |
|---|---:|---:|---:|
{resource_table}

## Авторитет, доказовість і наступні рішення

Технічна відтворюваність підтримується зафіксованими source/config SHA-256,
readback-перевіркою архівів і повторним відтворенням проби. Це дослідження
авторизоване власником у розмові, але не пройшло незалежної валідації.
Офіційний стан залишається: P_ALGORITHM_STATUS=NOT_READY, G1 INCOMPLETE,
G4 NOT_AUTHORIZED, незалежний reference NOT_READY; офіційний ΔA5 протокол
зберігає NO_GO.

Калібрувальний архів SHA-256: {calibration_archive_sha}. Повні архіви:

{archive_digests_text}

## Помилки та пропуски

Калібрувальні помилки й невиконані виклики наведені по комірках вище
та у `evaluator-samples.csv`; незавершені повні запуски:

| Виконання | Статус | Причина |
|---|---|---|
{failure_table}

Наступна найменша дія для офіційного порівняння — відповідальна людина має
ухвалити й задокументувати рішення з аркуша REVIEW_DECISIONS.md, зокрема щодо
меж applicability/stage, семантики пар, B0, методу, бюджету, незалежного
reference, G1 і окремої G4 авторизації. Цей звіт не заповнює жодного рішення.

**Висновок:** нові вимірювання характеризують час і фактичні виходи трьох
статичних оцінювачів та DEVELOPMENT-реалізації Ψ на одній конкретній
архітектурній парі й одній вже відомій пробі. Вони дозволяють описати технічну
поведінку саме цих запусків; вони не доводять наукову перевагу Ψ, валідність
coverage, статистичну значущість або загальну ефективність методу.
"""


def analyze_bundle(bundle_root: Path, repository: Path, output_root: Path) -> dict[str, Any]:
    """Verify raw archives, derive descriptive outputs and write a Ukrainian handoff."""
    bundle = bundle_root.resolve(strict=True)
    repo = repository.resolve(strict=True)
    output = output_root.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ContractValidationError("OWNER_AUTHORIZED_ANALYSIS_OUTPUT_MUST_BE_NEW")
    output.mkdir(parents=True)
    execution = _read_json(bundle / "study-execution.json")
    calibration_verified = verify_calibration_archive(bundle / "calibration.zip")
    calibration = _read_calibration_rows(bundle / "calibration.zip")
    with tempfile.TemporaryDirectory(prefix="owner-authorized-a05-analysis-") as temporary:
        transition_runs = _read_transition_archives(bundle, repo, execution, Path(temporary))
    calibration_summary = _summarize_calibration(calibration)
    budget_sensitivity = _budget_sensitivity(calibration)
    planned_by_id = {row["execution_id"]: row for row in execution.get("transition_runs", [])}
    measured_runs = [
        run for run in transition_runs if planned_by_id.get(run["execution_id"], {}).get("measured")
    ]
    measured_execution_rows = [
        row
        for row in execution.get("transition_runs", [])
        if row.get("measured") and row.get("run_status") == "COMPLETED"
    ]
    transition_resources = {
        "full_transition_duration": descriptive_statistics(
            float(row["full_transition_duration_ms"])
            for row in measured_execution_rows
            if row.get("full_transition_duration_ms") is not None
        ),
        "cpu_user": resource_statistics(
            row.get("cpu_user_seconds") for row in measured_execution_rows
        ),
        "cpu_system": resource_statistics(
            row.get("cpu_system_seconds") for row in measured_execution_rows
        ),
        "method_process_cpu": "NOT_AVAILABLE_SEPARATELY",
    }
    outcome_summary = {
        "planned_transition_runs": len(execution.get("transition_runs", [])),
        "archived_transition_runs": len(transition_runs),
        "measured_archived_runs": len(measured_runs),
        "method_decisions": dict(
            sorted(Counter(run["psi"]["decision"] for run in transition_runs).items())
        ),
        "measured_method_decisions": dict(
            sorted(Counter(run["psi"]["decision"] for run in measured_runs).items())
        ),
        "measured_operation_counts": [len(run["psi"]["operation_plan"]) for run in measured_runs],
        "B0_outcome_counts": dict(
            sorted(
                Counter(
                    f"{row['architecture_state']}|{row['evaluator_id']}|{row['compliance']}"
                    for run in measured_runs
                    for row in run["B0"]
                ).items()
            )
        ),
    }
    summary = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_ANALYSIS_V1",
        "study_id": execution["study_id"],
        "classification": execution["classification"],
        "calibration_archive": calibration_verified,
        "calibration": calibration_summary,
        "transition_runs": transition_runs,
        "transition_summary": outcome_summary,
        "transition_resources": transition_resources,
        "budget_sensitivity": budget_sensitivity,
        "transition_failures": [
            row
            for row in execution.get("transition_runs", [])
            if row.get("run_status") != "COMPLETED"
        ],
        "gates": execution["gates"],
        "statistical_interpretation": {
            "architecture_level_units": 1,
            "technical_repetitions": len(measured_runs),
            "significance_tests": "NOT_PERFORMED",
            "coverage_percentage": "NOT_COMPUTED",
        },
    }
    csv_rows = []
    for row in calibration:
        csv_rows.append(
            {
                "execution_id": row.get("execution_id"),
                "classification": row.get("classification"),
                "source_condition": row.get("source_condition"),
                "evaluator_id": row.get("evaluator_id"),
                "repetition_index": row.get("repetition_index"),
                "is_warmup": row.get("is_warmup"),
                "attempt_index": row.get("attempt_index"),
                "source_commit_sha": row.get("source_commit_sha"),
                "source_tree_sha": row.get("source_tree_sha"),
                "application_tree_sha": row.get("application_tree_sha"),
                "evaluator_version": row.get("evaluator_version"),
                "configuration_sha256": row.get("configuration_sha256"),
                "evaluator_source_sha256": row.get("evaluator_source_sha256"),
                "process_duration_ms": row.get("process_duration_ms"),
                "scope_verification_duration_ms": row.get("scope_verification_duration_ms"),
                "cpu_user_seconds": row.get("cpu_user_seconds"),
                "cpu_system_seconds": row.get("cpu_system_seconds"),
                "peak_rss_bytes": row.get("peak_rss_bytes"),
                "process_exit_code": row.get("process_exit_code"),
                "execution_status": row.get("execution_status"),
                "compliance": row.get("compliance"),
                "inspection_status": row.get("inspection_status"),
                "finding_codes": json.dumps(row.get("finding_codes", []), separators=(",", ":")),
                "raw_output_path": row.get("raw_output_path"),
                "raw_output_sha256": row.get("raw_output_sha256"),
                "raw_stdout_sha256": row.get("raw_stdout_sha256"),
                "raw_stderr_sha256": row.get("raw_stderr_sha256"),
                "sample_status": row.get("sample_status"),
                "error": json.dumps(row.get("error"), separators=(",", ":"))
                if row.get("error")
                else "",
            }
        )
    _write_csv(
        output / "evaluator-samples.csv",
        csv_rows,
        [
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
            "evaluator_version",
            "configuration_sha256",
            "evaluator_source_sha256",
            "process_duration_ms",
            "scope_verification_duration_ms",
            "cpu_user_seconds",
            "cpu_system_seconds",
            "peak_rss_bytes",
            "process_exit_code",
            "execution_status",
            "compliance",
            "inspection_status",
            "finding_codes",
            "raw_output_path",
            "raw_output_sha256",
            "raw_stdout_sha256",
            "raw_stderr_sha256",
            "sample_status",
            "error",
        ],
    )
    transition_rows = []
    for run in transition_runs:
        plan_row = planned_by_id[run["execution_id"]]
        for row in run["B0"]:
            transition_rows.append(
                {
                    "execution_id": run["execution_id"],
                    "run_role": plan_row["role"],
                    "measured": plan_row["measured"],
                    "arm": "B0_UNCHANGED_RECONSTRUCTION",
                    "architecture_state": row["architecture_state"],
                    "evaluator_id": row["evaluator_id"],
                    "duration_ms": row["duration_ms"],
                    "cpu_user_seconds": plan_row.get("cpu_user_seconds"),
                    "cpu_system_seconds": plan_row.get("cpu_system_seconds"),
                    "exit_code": row["exit_code"],
                    "compliance": row["compliance"],
                    "source_commit_sha": row["source_commit_sha"],
                    "output_sha256": row["output_sha256"],
                    "method_decision": "",
                    "method_operations": "",
                    "candidate_state": "",
                    "method_duration_ms": "",
                    "method_result_sha256": "",
                }
            )
        transition_rows.append(
            {
                "execution_id": run["execution_id"],
                "run_role": plan_row["role"],
                "measured": plan_row["measured"],
                "arm": "PSI_METHOD_DECISION",
                "architecture_state": "A0_4_TO_A0_5",
                "evaluator_id": "",
                "duration_ms": plan_row.get("full_transition_duration_ms"),
                "cpu_user_seconds": plan_row.get("cpu_user_seconds"),
                "cpu_system_seconds": plan_row.get("cpu_system_seconds"),
                "exit_code": "",
                "compliance": "",
                "source_commit_sha": run["source_revision_sha"],
                "output_sha256": run["psi"]["method_result_sha256"],
                "method_decision": run["psi"]["decision"],
                "method_operations": len(run["psi"]["operation_plan"]),
                "candidate_state": run["psi"]["candidate_state"],
                "method_duration_ms": run["psi"]["method_duration_ms"],
                "method_result_sha256": run["psi"]["method_result_sha256"],
            }
        )
    _write_csv(
        output / "transition-samples.csv",
        transition_rows,
        [
            "execution_id",
            "run_role",
            "measured",
            "arm",
            "architecture_state",
            "evaluator_id",
            "duration_ms",
            "cpu_user_seconds",
            "cpu_system_seconds",
            "exit_code",
            "compliance",
            "source_commit_sha",
            "output_sha256",
            "method_decision",
            "method_operations",
            "candidate_state",
            "method_duration_ms",
            "method_result_sha256",
        ],
    )
    _write_json(output / "analysis-summary.json", summary)
    _svg_figure(calibration, output / "evaluator-time-distributions.svg")
    (output / "OWNER_AUTHORIZED_RESULTS_UK_V1.md").write_text(
        _render_handoff(
            summary, execution, transition_runs, calibration_verified["archive_sha256"]
        ),
        encoding="utf-8",
    )
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
    except (ContractValidationError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
