"""Interactive, read-only Streamlit presentation for the retained Method P run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from research_dashboard.charts import (
    confusion_matrix_figure,
    coverage_transition_figure,
    duration_distribution_figure,
    duration_figure,
    governance_distribution_figure,
)
from research_dashboard.data import (
    DashboardDataError,
    ExperimentDataset,
    default_results_path,
    load_dataset,
    repository_relative_path,
)
from research_dashboard.metrics import (
    duration_rows,
    duration_summary,
    evidence_artifact_rows,
    evidence_inventory_rows,
    mismatch_rows,
    repetition_rows,
    scenario_rows,
    summary_metrics,
)

PAGE_NAMES = (
    "Experiment overview",
    "Architectural coverage transitions",
    "Method P decision explorer",
    "Decision correctness and governance",
    "Execution performance",
    "Evidence and reproducibility",
)


@st.cache_data(show_spinner=False)
def _cached_load(results_path: str) -> ExperimentDataset:
    return load_dataset(results_path)


def _status_label(dataset: ExperimentDataset) -> str:
    first_line = dataset.report_text.splitlines()[0] if dataset.report_text else ""
    return "DEVELOPMENT" if "DEVELOPMENT report" in first_line else "UNAVAILABLE"


def _format_ratio(matches: int, total: int) -> str:
    return f"{matches}/{total}" if total else "Not available"


def _dict_table(mapping: dict[str, Any], key_name: str, value_name: str) -> pd.DataFrame:
    return pd.DataFrame([{key_name: key, value_name: value} for key, value in mapping.items()])


def _hash_rows(dataset: ExperimentDataset) -> pd.DataFrame:
    results = dataset.results
    score = dataset.score_manifest or {}
    rows = [
        {
            "Artifact": "Scored results",
            "Path": repository_relative_path(dataset.results_path, dataset.repo_root),
            "SHA-256": score.get("result_sha256"),
        },
        {
            "Artifact": "Execution manifest",
            "Path": repository_relative_path(
                dataset.run_dir / "execution_manifest.json", dataset.repo_root
            ),
            "SHA-256": results.get("execution_manifest_sha256"),
        },
        {
            "Artifact": "Raw-record manifest",
            "Path": repository_relative_path(
                dataset.run_dir / "raw_records_manifest.json", dataset.repo_root
            ),
            "SHA-256": results.get("raw_records_manifest_sha256"),
        },
        {
            "Artifact": "Scorer source",
            "Path": "experiments/pilots/mono_e1_dev_p_decisions_v1/runner.py",
            "SHA-256": score.get("scorer_code_sha256"),
        },
        {
            "Artifact": "Author-declared reference",
            "Path": "experiments/pilots/mono_e1_dev_p_decisions_v1/reference_v1.json",
            "SHA-256": results.get("reference_sha256"),
        },
        {
            "Artifact": "Scored report",
            "Path": repository_relative_path(dataset.run_dir / "report_v1.md", dataset.repo_root),
            "SHA-256": score.get("report_sha256"),
        },
    ]
    return pd.DataFrame(rows)


def _overview(dataset: ExperimentDataset, metrics: dict[str, Any]) -> None:
    st.title("Method P research dashboard")
    st.caption(
        f"{dataset.results['experiment_id']} · read-only analysis of retained structured results"
    )
    method_version = dataset.results.get("method_identity", {}).get("method_version", "Unavailable")
    st.markdown(
        f"**Run status:** {_status_label(dataset)}  ·  "
        f"**Method version:** {method_version}  ·  "
        f"**Source commit:** {dataset.results.get('source_commit_sha', 'Unavailable')}"
    )

    columns = st.columns(4)
    columns[0].metric("Scenarios", metrics["scenario_count"])
    columns[1].metric("Technical repetitions", metrics["technical_repetition_count"])
    columns[2].metric(
        "Operation agreement",
        _format_ratio(metrics["operation_match_count"], metrics["operation_evaluable_count"]),
    )
    columns[3].metric(
        "Combined decision agreement",
        _format_ratio(metrics["combined_correct_count"], metrics["combined_evaluable_count"]),
    )

    actual_distribution = metrics["actual_post_adaptation_coverage_distribution"]
    actual_status = (
        ", ".join(f"{status}: {count}" for status, count in actual_distribution.items())
        if actual_distribution
        else "No actual post-adaptation records"
    )
    columns = st.columns(3)
    columns[0].metric("Execution failures", metrics["execution_failure_count"])
    columns[1].metric("Actual post-adaptation coverage", actual_status)
    columns[2].metric(
        "Checksum inventory",
        f"{dataset.integrity.verified_files}/{dataset.integrity.expected_files} verified",
    )
    st.caption(
        "The 24 records are technical repetitions nested within 8 scenarios; they are not "
        "24 independent experimental cases."
    )

    left, right = st.columns([1.2, 1])
    with left:
        st.plotly_chart(
            governance_distribution_figure(dataset),
            width="stretch",
            key="overview-governance",
        )
    with right:
        st.subheader("Observed governance distribution")
        st.dataframe(
            _dict_table(metrics["governance_distribution"], "Result", "Repetitions"),
            hide_index=True,
            width="stretch",
        )

    b0 = metrics["b0_synth"]
    st.subheader("Synthetic unchanged-configuration assessment")
    st.info(
        f"B0_SYNTH is {b0.get('assessment_type', 'UNAVAILABLE')}. "
        f"Independent baseline arm executed: "
        f"{b0.get('independently_executed_baseline_arm', 'Unavailable')}. "
        "It is a derived assessment from Method P's current-configuration evaluation; "
        "no runtime or statistical comparison is available."
    )

    warning_items = [
        f"Reference scope: {dataset.results.get('reference_status', 'Unavailable')}.",
        "The report identifies this run as synthetic TEST_ONLY development data.",
        "Reference labels are AUTHOR_DECLARED and NON_INDEPENDENT.",
        "Actual post-adaptation coverage is NOT_MEASURED because "
        "the candidate was not applied and re-evaluated.",
        "B0_SYNTH is not an independently executed baseline arm.",
        "This dashboard does not change P_ALGORITHM_STATUS=NOT_READY, G1=INCOMPLETE, "
        "G4=NOT_AUTHORIZED, or MONO-E1=NO_GO.",
    ]
    with st.expander("Interpretation limits", expanded=True):
        for warning in warning_items:
            st.warning(warning)
        if dataset.warnings:
            st.markdown("**Data-source warnings**")
            for warning in dataset.warnings:
                st.warning(warning)


def _coverage_transitions(dataset: ExperimentDataset) -> None:
    st.title("Architectural coverage transitions")
    st.markdown(
        "**Current configuration coverage assessment → observed operation → candidate "
        "configuration coverage assessment → governance.** Candidate assessment is not a "
        "measurement after applying that candidate."
    )
    rows = scenario_rows(dataset)
    scenario_ids = [row["scenario_id"] for row in rows]
    operations = sorted({row["operation"] for row in rows if row["operation"] != "NO DATA"})
    statuses = ("COMPLETE", "INCOMPLETE", "UNKNOWN")
    governance_values = ("ACCEPT", "HOLD", "REJECT")
    filters = st.columns(5)
    selected_scenarios = filters[0].multiselect(
        "Scenario", scenario_ids, default=scenario_ids, key="coverage-scenarios"
    )
    selected_operations = filters[1].multiselect(
        "Operation", operations, default=operations, key="coverage-operations"
    )
    selected_initial = filters[2].multiselect(
        "Initial coverage", statuses, default=list(statuses), key="coverage-initial"
    )
    selected_candidate = filters[3].multiselect(
        "Candidate coverage", statuses, default=list(statuses), key="coverage-candidate"
    )
    selected_governance = filters[4].multiselect(
        "Governance result",
        governance_values,
        default=list(governance_values),
        key="coverage-governance",
    )
    filtered = [
        row
        for row in rows
        if row["scenario_id"] in selected_scenarios
        and row["operation"] in selected_operations
        and row["current_coverage"] in selected_initial
        and row["candidate_coverage"] in selected_candidate
        and row["governance"] in selected_governance
    ]
    st.plotly_chart(
        coverage_transition_figure(filtered),
        width="stretch",
        key="coverage-transition-matrix",
    )
    st.caption(
        "Highlighted rows are derived INCOMPLETE → ADD/REPLACE → COMPLETE candidate "
        "assessments. Actual post-adaptation coverage remains NOT_MEASURED."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Scenario": row["scenario_id"],
                    "Current configuration coverage assessment": row["current_coverage"],
                    "Observed operation": row["operation"],
                    "Candidate configuration coverage assessment": row["candidate_coverage"],
                    "Governance result": row["governance"],
                    "Technical repetitions": row["repetition_count"],
                    "Candidate transition emphasized": row["candidate_transition_emphasized"],
                }
                for row in filtered
            ]
        ),
        hide_index=True,
        width="stretch",
    )


def _pair_rows(record: dict[str, Any], field: str) -> list[dict[str, Any]]:
    inventory = record.get("evidence_record_inventory", {})
    return [
        {
            "Obligation": item.get("obligation_id", "Unavailable"),
            "Representation": item.get("representation_id", "Unavailable"),
            "Assessment": item.get("status", "Unavailable"),
            "Semantic proof": item.get("semantic_proof_status", "Unavailable"),
            "Reason codes": ", ".join(item.get("reason_codes", [])) or "None recorded",
        }
        for item in inventory.get(field, [])
    ]


def _decision_explorer(dataset: ExperimentDataset) -> None:
    st.title("Method P decision explorer")
    scenarios = scenario_rows(dataset)
    scenario_ids = [row["scenario_id"] for row in scenarios]
    if not scenario_ids:
        st.info("No scenario records are available.")
        return
    selected_id = st.selectbox("Scenario", scenario_ids, key="decision-scenario")
    selected_scenario = next(row for row in scenarios if row["scenario_id"] == selected_id)
    records = [row for row in repetition_rows(dataset) if row["scenario_id"] == selected_id]
    if not records:
        st.info("No technical repetition records are available for this scenario.")
        st.json(selected_scenario)
        return
    selected_number = st.selectbox(
        "Technical repetition",
        [row["repetition"] for row in records],
        key="decision-repetition",
    )
    record = next(row for row in records if row["repetition"] == selected_number)
    catalog: dict[str, Any] = next(
        (
            row
            for row in dataset.scenario_catalog.get("scenarios", [])
            if row.get("scenario_id") == selected_id
        ),
        {},
    )
    st.caption(
        "Recorded facts come from the selected repetition; catalog fields are scenario "
        "metadata. Expected labels are declared references, not independent ground truth."
    )

    st.subheader("1 · Initial architecture and obligations")
    st.write(catalog.get("architecture_before", "Architecture description unavailable."))
    obligation_rows = [
        {
            "Obligation": item.get("obligation_id"),
            "Mandatory": item.get("mandatory"),
            "Applicability before": item.get("applicability_before"),
            "Applicability after": item.get("applicability_after"),
        }
        for item in catalog.get("obligations", [])
    ]
    if obligation_rows:
        st.dataframe(pd.DataFrame(obligation_rows), hide_index=True, width="stretch")
    else:
        st.info("No obligation applicability metadata is available.")
    if catalog.get("architecture_after"):
        st.caption(f"Scenario architecture after change: {catalog['architecture_after']}")

    first, second, third = st.columns(3)
    with first:
        st.subheader("2 · Current assessment")
        current = record.get("pre_adaptation_coverage", {})
        st.metric("Pre-adaptation coverage", current.get("status", "Unavailable"))
        st.write(
            f"Mandatory coverage: {current.get('mandatory_covered', 'Unavailable')} / "
            f"{current.get('mandatory_total', 'Unavailable')}"
        )
        st.dataframe(
            pd.DataFrame(_pair_rows(record, "pre_adaptation_pair_assessments")),
            hide_index=True,
            width="stretch",
        )
    with second:
        st.subheader("3 · Proposed operation")
        st.metric("Observed operation", record.get("proposed_operation", "Unavailable").upper())
        st.write("Operation plan SHA-256")
        st.code(record.get("operation_plan_sha256") or "Unavailable")
        st.write("Recorded proposed operations")
        st.json(record.get("proposed_operations", []))
    with third:
        st.subheader("4 · Candidate assessment")
        candidate = record.get("candidate_configuration_coverage", {})
        st.metric("Candidate configuration coverage", candidate.get("status", "Unavailable"))
        st.write(
            f"Candidate validation: {record.get('candidate_validation_status', 'Unavailable')}"
        )
        st.write("Candidate configuration SHA-256")
        st.code(record.get("candidate_configuration_sha256") or "Unavailable")
        st.dataframe(
            pd.DataFrame(_pair_rows(record, "candidate_pair_assessments")),
            hide_index=True,
            width="stretch",
        )

    fourth, fifth = st.columns(2)
    with fourth:
        st.subheader("5 · Governance decision")
        st.metric("Observed governance", record.get("governance_result", "Unavailable"))
        st.write(f"Accepted: {record.get('governance_accepted', 'Unavailable')}")
        reasons = record.get("governance_reason_codes", [])
        st.write("Reason codes: " + (", ".join(reasons) if reasons else "None recorded"))
    with fifth:
        st.subheader("6 · Reference outcome")
        st.write(f"Expected operation: {record.get('expected_operation', 'Unavailable').upper()}")
        st.write(f"Expected governance: {record.get('expected_governance', 'Unavailable')}")
        st.metric("Combined classification", record.get("classification", "Unavailable"))
        if record.get("classification") == "INCORRECT":
            st.error("This repetition is a mismatch against the declared reference labels.")

    actual = record.get("actual_post_adaptation_coverage", {})
    st.info(
        "Actual post-adaptation coverage: "
        f"{actual.get('status', 'Unavailable')}. {actual.get('reason', '')}"
    )
    with st.expander("Semantic evidence and provenance for this repetition"):
        inventory = record.get("evidence_record_inventory", {})
        st.write("Adaptation evidence sidecar")
        st.json(inventory.get("adaptation_evidence_sidecar", {}))
        st.write("Evaluator evidence records")
        st.json(inventory.get("evaluator_evidence_records", []))
        st.write("Evaluator execution records")
        st.json(inventory.get("evaluator_execution_records", {}))
        st.write("Sidecar pair proofs")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Obligation": item.get("obligation_id"),
                        "Representation": item.get("representation_id"),
                        "Status": item.get("status"),
                        "Reason codes": ", ".join(item.get("reason_codes", [])),
                    }
                    for item in inventory.get("sidecar_pair_proofs", [])
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        st.write(
            {
                "Input bundle SHA-256": record.get("input_bundle_sha256"),
                "Raw record SHA-256": record.get("raw_record_sha256"),
                "Candidate configuration SHA-256": record.get("candidate_configuration_sha256"),
            }
        )


def _correctness(dataset: ExperimentDataset, metrics: dict[str, Any]) -> None:
    st.title("Decision correctness and governance")
    st.caption(
        "Expected outcomes are AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT labels. "
        "Agreement is descriptive and does not independently validate the reference."
    )
    columns = st.columns(3)
    columns[0].metric(
        "Operation agreement",
        _format_ratio(metrics["operation_match_count"], metrics["operation_evaluable_count"]),
    )
    columns[1].metric(
        "Governance agreement",
        _format_ratio(metrics["governance_match_count"], metrics["governance_evaluable_count"]),
    )
    columns[2].metric(
        "Combined decision agreement",
        _format_ratio(metrics["combined_correct_count"], metrics["combined_evaluable_count"]),
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            confusion_matrix_figure(dataset, "operation"),
            width="stretch",
            key="operation-confusion",
        )
    with right:
        st.plotly_chart(
            confusion_matrix_figure(dataset, "governance"),
            width="stretch",
            key="governance-confusion",
        )

    st.subheader("Scenario-level outcomes")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Scenario": row["scenario_id"],
                    "Expected operation": row["expected_operation"],
                    "Observed operation": row["operation"],
                    "Expected governance": row["expected_governance"],
                    "Observed governance": row["governance"],
                    "Correct": row["correct_count"],
                    "Incorrect": row["incorrect_count"],
                    "Not evaluable": row["not_evaluable_count"],
                    "Classification": row["correctness"],
                }
                for row in scenario_rows(dataset)
            ]
        ),
        hide_index=True,
        width="stretch",
    )

    mismatches = mismatch_rows(dataset)
    st.subheader("Repetition-level mismatches")
    if mismatches:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Scenario": row["scenario_id"],
                        "Repetition": row["repetition"],
                        "Expected operation": row["expected_operation"].upper(),
                        "Observed operation": row["proposed_operation"].upper(),
                        "Expected governance": row["expected_governance"],
                        "Observed governance": row["governance_result"],
                        "Classification": row["classification"],
                        "Governance reason codes": ", ".join(
                            row.get("governance_reason_codes", [])
                        ),
                    }
                    for row in mismatches
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.success("No classified mismatches are present in the available repetitions.")

    d2_rows = [row for row in repetition_rows(dataset) if row["scenario_id"] == "D2"]
    if d2_rows:
        d2 = d2_rows[0]
        d2_mismatch_count = sum(row["classification"] != "CORRECT" for row in d2_rows)
        st.warning(
            f"D2: expected operation {d2['expected_operation'].upper()} and governance "
            f"{d2['expected_governance']}; observed operation "
            f"{d2['proposed_operation'].upper()} and governance {d2['governance_result']} "
            f"across {len(d2_rows)} technical repetitions. All {d2_mismatch_count} "
            "D2 repetitions remain mismatches. A safety-oriented REJECT may be defensible, "
            "but it does not match the declared HOLD governance reference."
        )


def _performance(dataset: ExperimentDataset) -> None:
    st.title("Execution performance")
    st.caption(
        "Each mark is one observed Method P technical repetition. Three repetitions per "
        "scenario are not independent cases. No significance or superiority claim is made."
    )
    all_rows = duration_rows(dataset)
    operation_values = sorted({row["operation"] for row in all_rows})
    scenario_values = sorted({row["scenario_id"] for row in all_rows})
    controls = st.columns(2)
    selected_operations = controls[0].multiselect(
        "Observed operation", operation_values, default=operation_values, key="duration-operations"
    )
    selected_scenarios = controls[1].multiselect(
        "Scenario", scenario_values, default=scenario_values, key="duration-scenarios"
    )
    selected_rows = duration_rows(
        dataset,
        operations=set(selected_operations),
        scenario_ids=set(selected_scenarios),
    )
    left, right = st.columns([1.5, 1])
    with left:
        st.plotly_chart(
            duration_figure(
                dataset,
                operations=set(selected_operations),
                scenario_ids=set(selected_scenarios),
            ),
            width="stretch",
            key="duration-by-operation-scenario",
        )
    with right:
        st.plotly_chart(
            duration_distribution_figure(selected_rows),
            width="stretch",
            key="duration-distribution",
        )
    summary = duration_summary(selected_rows)
    st.subheader("Descriptive summary")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Measured repetitions": summary["n"],
                    "Missing measurements": summary["missing"],
                    "Minimum (ms)": summary["minimum_ms"],
                    "Median (ms)": summary["median_ms"],
                    "Mean (ms)": summary["mean_ms"],
                    "Maximum (ms)": summary["maximum_ms"],
                    "Sample SD (ms)": summary["sample_stdev_ms"],
                }
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    st.subheader("Individual technical repetitions")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Scenario": row["scenario_id"],
                    "Repetition": row["repetition"],
                    "Operation": row["operation"].upper(),
                    "Duration (ns)": row["duration_ns"],
                    "Duration (ms)": row["duration_ms"],
                }
                for row in selected_rows
            ]
        ),
        hide_index=True,
        width="stretch",
    )


def _evidence(dataset: ExperimentDataset) -> None:
    st.title("Evidence and reproducibility")
    results = dataset.results
    method = results.get("method_identity", {})
    columns = st.columns(3)
    columns[0].metric("Experiment", results.get("experiment_id", "Unavailable"))
    columns[1].metric("Method version", method.get("method_version", "Unavailable"))
    columns[2].metric("Source commit", results.get("source_commit_sha", "Unavailable"))
    st.caption(
        "This is a per-record inventory. Individual evidence availability does not establish "
        "a global evidence-completeness verdict."
    )
    st.subheader("Source artifacts and manifest hashes")
    st.dataframe(_hash_rows(dataset), hide_index=True, width="stretch")
    st.subheader("Verified checksum inventory")
    st.write(
        f"{dataset.integrity.verified_files} of {dataset.integrity.expected_files} listed "
        f"files verified; {dataset.integrity.missing_files} listed files unavailable."
    )
    if dataset.raw_records_manifest:
        raw_rows = [
            {
                "Path": item.get("path"),
                "SHA-256": item.get("sha256"),
                "Bytes": item.get("size_bytes"),
                "Available in this checkout": (
                    dataset.run_dir.joinpath(*Path(item.get("path", "")).parts).is_file()
                ),
            }
            for item in dataset.raw_records_manifest.get("files", [])
        ]
        with st.expander("Raw-record manifest entries"):
            st.dataframe(pd.DataFrame(raw_rows), hide_index=True, width="stretch")
    else:
        st.info("Raw-record manifest is unavailable.")

    inventory = evidence_inventory_rows(dataset)
    st.subheader("Evidence availability by technical repetition")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Scenario": row["scenario_id"],
                    "Repetition": row["repetition"],
                    "Raw record SHA-256": row["raw_record_sha256"],
                    "Input bundle SHA-256": row["input_bundle_sha256"],
                    "Operation plan SHA-256": row["operation_plan_sha256"],
                    "Candidate configuration SHA-256": row["candidate_configuration_sha256"],
                    "Sidecar present": row["sidecar_present"],
                    "Evaluator evidence records": row["evaluator_evidence_count"],
                    "Evaluator execution records present": row[
                        "evaluator_execution_records_present"
                    ],
                    "Sidecar pair proofs": str(row["sidecar_pair_proofs"]),
                    "Current pair assessments": str(row["pre_adaptation_pair_assessments"]),
                    "Candidate pair assessments": str(row["candidate_pair_assessments"]),
                }
                for row in inventory
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    if inventory:
        selected = st.selectbox(
            "Inspect evidence artifacts for repetition",
            [f"{row['scenario_id']} / {row['repetition']}" for row in inventory],
            key="evidence-record",
        )
        scenario_id, repetition_text = selected.split(" / ", maxsplit=1)
        record = next(
            row
            for row in repetition_rows(dataset)
            if row["scenario_id"] == scenario_id and row["repetition"] == int(repetition_text)
        )
        st.dataframe(
            pd.DataFrame(evidence_artifact_rows(record)),
            hide_index=True,
            width="stretch",
        )
    with st.expander("Method and scorer provenance"):
        st.write(
            {
                "Reference status": results.get("reference_status"),
                "Scorer source commit": results.get("scorer_source_commit_sha"),
                "Scorer code SHA-256": results.get("scorer_code_sha256"),
                "Reference SHA-256": results.get("reference_sha256"),
                "Method identity": method,
                "B0_SYNTH": results.get("b0_synth_vs_method_p"),
                "Actual post-adaptation coverage note": results.get(
                    "post_adaptation_coverage_note"
                ),
                "Scientific status effect": results.get("scientific_status_effect"),
            }
        )
    with st.expander("Repository file locations"):
        for path in (
            dataset.results_path,
            dataset.run_dir / "report_v1.md",
            dataset.run_dir / "execution_manifest.json",
            dataset.run_dir / "raw_records_manifest.json",
            dataset.run_dir / "score_manifest.json",
            dataset.run_dir / "SHA256SUMS",
        ):
            st.code(repository_relative_path(path, dataset.repo_root))


def main() -> None:
    st.set_page_config(
        page_title="Method P Research Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.6rem; padding-bottom: 2.4rem; }
        [data-testid="stMetricValue"] { font-size: 1.45rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.title("Research dashboard")
    selected_path = st.sidebar.text_input("Results JSON path", value=str(default_results_path()))
    if st.sidebar.button("Reload source", width="stretch"):
        _cached_load.clear()
    try:
        dataset = _cached_load(str(Path(selected_path).expanduser()))
    except (DashboardDataError, OSError, ValueError) as exc:
        st.error(f"Could not load this results source: {exc}")
        st.stop()

    page = st.sidebar.radio("Page", PAGE_NAMES, index=0)
    st.sidebar.caption("Read-only local files · no database or external API calls")
    if dataset.integrity.expected_files and dataset.integrity.missing_files:
        st.sidebar.warning(
            f"{dataset.integrity.verified_files}/{dataset.integrity.expected_files} "
            "checksum-listed files verified."
        )
    metrics = summary_metrics(dataset)
    pages = {
        PAGE_NAMES[0]: lambda: _overview(dataset, metrics),
        PAGE_NAMES[1]: lambda: _coverage_transitions(dataset),
        PAGE_NAMES[2]: lambda: _decision_explorer(dataset),
        PAGE_NAMES[3]: lambda: _correctness(dataset, metrics),
        PAGE_NAMES[4]: lambda: _performance(dataset),
        PAGE_NAMES[5]: lambda: _evidence(dataset),
    }
    pages[page]()


if __name__ == "__main__":
    main()
