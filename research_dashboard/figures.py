"""Deterministic publication figure exports for the retained Method P run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from research_dashboard.data import (
    DashboardDataError,
    ExperimentDataset,
    default_results_path,
    load_dataset,
    validate_publication_export_readiness,
)
from research_dashboard.metrics import (
    GOVERNANCE_RESULTS,
    OPERATIONS,
    duration_rows,
    scenario_rows,
)

DEFAULT_OUTPUT_RELATIVE_PATH = Path(
    "experiments/results/research_figures/mono_e1_dev_p_decisions_v1"
)
OUTPUT_BASENAMES = (
    "coverage_assessment_transitions",
    "operations_and_governance",
    "execution_duration_by_operation_scenario",
)
STATUS_COLORS = {
    "COMPLETE": "#147D64",
    "INCOMPLETE": "#D58B12",
    "UNKNOWN": "#687386",
}
OPERATION_COLORS = {
    "RETAIN": "#0072B2",
    "ADD": "#009E73",
    "REPLACE": "#E69F00",
    "HOLD": "#687386",
}
GOVERNANCE_COLORS = {
    "ACCEPT": "#009E73",
    "HOLD": "#E69F00",
    "REJECT": "#D55E00",
}
_CELL_KEYS = (
    "COMPLETE",
    "INCOMPLETE",
    "UNKNOWN",
    "RETAIN",
    "ADD",
    "REPLACE",
    "OP_HOLD",
    "ACCEPT",
    "GOV_HOLD",
    "REJECT",
    "MIXED",
    "NO DATA",
    "UNAVAILABLE",
)
_CELL_COLORS = (
    STATUS_COLORS["COMPLETE"],
    STATUS_COLORS["INCOMPLETE"],
    STATUS_COLORS["UNKNOWN"],
    OPERATION_COLORS["RETAIN"],
    OPERATION_COLORS["ADD"],
    OPERATION_COLORS["REPLACE"],
    OPERATION_COLORS["HOLD"],
    GOVERNANCE_COLORS["ACCEPT"],
    GOVERNANCE_COLORS["HOLD"],
    GOVERNANCE_COLORS["REJECT"],
    "#9B59B6",
    "#D9DEE7",
    "#D9DEE7",
)


def _pyplot() -> tuple[Any, Any, Any, Any, Any]:
    import matplotlib

    matplotlib.use("Agg", force=True)
    matplotlib.rcParams["svg.hashsalt"] = "evofitbench-method-p-dashboard-v1"
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
    matplotlib.rcParams["font.size"] = 9
    matplotlib.rcParams["axes.titleweight"] = "bold"
    from matplotlib import pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch, Rectangle

    return plt, BoundaryNorm, ListedColormap, Patch, Rectangle


def _matrix_category(column: str, value: str) -> str:
    if column == "Observed operation" and value == "HOLD":
        return "OP_HOLD"
    if column == "Governance" and value == "HOLD":
        return "GOV_HOLD"
    return value


def coverage_figure(dataset: ExperimentDataset) -> Any:
    plt, BoundaryNorm, ListedColormap, Patch, Rectangle = _pyplot()
    rows = scenario_rows(dataset)
    figure, axis = plt.subplots(figsize=(11.2, max(4.5, 0.48 * len(rows) + 1.6)))
    columns = (
        "Current coverage assessment",
        "Observed operation",
        "Candidate coverage assessment",
        "Governance",
    )
    fields = ("current_coverage", "operation", "candidate_coverage", "governance")
    key_to_index = {key: index for index, key in enumerate(_CELL_KEYS)}
    matrix: list[list[int]] = []
    labels: list[list[str]] = []
    for row in rows:
        values = [str(row.get(field, "NO DATA")).upper() for field in fields]
        labels.append(values)
        matrix.append(
            [
                key_to_index.get(_matrix_category(column, value), key_to_index["UNAVAILABLE"])
                for column, value in zip(columns, values, strict=True)
            ]
        )

    cmap = ListedColormap(_CELL_COLORS)
    norm = BoundaryNorm([index - 0.5 for index in range(len(_CELL_KEYS) + 1)], cmap.N)
    axis.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")
    for row_index, row_labels in enumerate(labels):
        for column_index, label in enumerate(row_labels):
            axis.text(
                column_index,
                row_index,
                label,
                ha="center",
                va="center",
                color="#172033",
                fontsize=8.5,
                fontweight="bold",
            )
    axis.set_xticks(range(len(columns)), columns)
    axis.xaxis.tick_top()
    axis.tick_params(axis="x", labelrotation=0, pad=10, length=0)
    axis.set_yticks(range(len(rows)), [row["scenario_id"] for row in rows])
    axis.tick_params(axis="y", length=0)
    axis.set_xticks([index - 0.5 for index in range(len(columns) + 1)], minor=True)
    axis.set_yticks([index - 0.5 for index in range(len(rows) + 1)], minor=True)
    axis.grid(which="minor", color="white", linewidth=2)
    axis.tick_params(which="minor", bottom=False, left=False)
    for index, row in enumerate(rows):
        if row["candidate_transition_emphasized"]:
            axis.add_patch(
                Rectangle(
                    (-0.48, index - 0.48),
                    len(columns) - 0.04,
                    0.96,
                    fill=False,
                    edgecolor="#5B21B6",
                    linewidth=1.7,
                )
            )
            axis.get_yticklabels()[index].set_fontweight("bold")
    for spine in axis.spines.values():
        spine.set_visible(False)

    figure.suptitle(
        "Method P coverage assessment transitions",
        x=0.03,
        y=0.99,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    axis.set_title(
        "Candidate configuration assessment only; actual post-adaptation coverage: NOT_MEASURED",
        loc="left",
        fontsize=9,
        color="#475569",
        pad=18,
    )
    legend_patches = (
        [
            Patch(
                facecolor=STATUS_COLORS[status],
                edgecolor="#172033",
                label=f"Coverage {status}",
            )
            for status in ("COMPLETE", "INCOMPLETE", "UNKNOWN")
        ]
        + [
            Patch(
                facecolor=OPERATION_COLORS[operation],
                edgecolor="#172033",
                label=f"Operation {operation}",
            )
            for operation in ("RETAIN", "ADD", "REPLACE", "HOLD")
        ]
        + [
            Patch(
                facecolor=GOVERNANCE_COLORS[result],
                edgecolor="#172033",
                label=f"Governance {result}",
            )
            for result in GOVERNANCE_RESULTS
        ]
    )
    figure.legend(
        handles=legend_patches,
        ncol=5,
        loc="lower left",
        bbox_to_anchor=(0.03, 0.02),
        frameon=False,
        fontsize=8,
    )
    figure.text(
        0.03,
        0.005,
        "Purple outlines mark INCOMPLETE → ADD/REPLACE → COMPLETE candidate assessments. "
        "They do not show measured improvement.",
        fontsize=8,
        color="#475569",
    )
    figure.subplots_adjust(left=0.08, right=0.99, top=0.84, bottom=0.23)
    return figure


def operations_governance_figure(dataset: ExperimentDataset) -> Any:
    plt, BoundaryNorm, ListedColormap, Patch, Rectangle = _pyplot()
    rows = scenario_rows(dataset)
    columns = (
        "Expected\noperation",
        "Observed\noperation",
        "Expected\ngovernance",
        "Observed\ngovernance",
        "Author-declared\nreference match",
    )
    matrix_values = (
        "expected_operation",
        "operation",
        "expected_governance",
        "governance",
        "correctness",
    )
    cell_colors: dict[str, str] = {
        **{key: STATUS_COLORS[key] for key in STATUS_COLORS},
        **OPERATION_COLORS,
        **GOVERNANCE_COLORS,
        "MATCH": "#D7F0E5",
        "MISMATCH": "#FCE1DA",
        "MIXED": "#EFE5F5",
        "NO DATA": "#E8ECF2",
        "NOT EVALUABLE": "#E8ECF2",
        "UNAVAILABLE": "#E8ECF2",
    }
    data = [[0 for _ in columns] for _ in rows]
    labels: list[list[str]] = []
    values_for_color: list[list[str]] = []
    color_to_index: dict[str, int] = {}
    all_colors: list[str] = []
    for row in rows:
        labels_for_row: list[str] = []
        colors_for_row: list[str] = []
        for field in matrix_values:
            value = str(row.get(field, "UNAVAILABLE")).upper()
            labels_for_row.append(value)
            color_key = value if value in cell_colors else "UNAVAILABLE"
            colors_for_row.append(color_key)
            if color_key not in color_to_index:
                color_to_index[color_key] = len(color_to_index)
                all_colors.append(cell_colors[color_key])
        labels.append(labels_for_row)
        values_for_color.append(colors_for_row)
    for row_index, colors in enumerate(values_for_color):
        for column_index, color_key in enumerate(colors):
            data[row_index][column_index] = color_to_index[color_key]

    cmap = ListedColormap(all_colors or ["#E8ECF2"])
    norm = BoundaryNorm(
        [index - 0.5 for index in range(len(cmap.colors) + 1)],
        cmap.N,
    )
    figure, axis = plt.subplots(figsize=(12.5, max(4.6, 0.48 * len(rows) + 1.7)))
    axis.imshow(data, cmap=cmap, norm=norm, aspect="auto")
    for row_index, row_labels in enumerate(labels):
        for column_index, label in enumerate(row_labels):
            axis.text(
                column_index,
                row_index,
                label,
                ha="center",
                va="center",
                color="#172033",
                fontsize=8,
                fontweight="bold",
            )
    axis.set_xticks(range(len(columns)), columns)
    axis.xaxis.tick_top()
    axis.tick_params(axis="x", length=0, pad=9)
    axis.set_yticks(range(len(rows)), [row["scenario_id"] for row in rows])
    axis.tick_params(axis="y", length=0)
    axis.set_xticks([index - 0.5 for index in range(len(columns) + 1)], minor=True)
    axis.set_yticks([index - 0.5 for index in range(len(rows) + 1)], minor=True)
    axis.grid(which="minor", color="white", linewidth=2)
    axis.tick_params(which="minor", bottom=False, left=False)
    for index, row in enumerate(rows):
        if row["correctness"] == "MISMATCH":
            axis.add_patch(
                Rectangle(
                    (-0.48, index - 0.48),
                    len(columns) - 0.04,
                    0.96,
                    fill=False,
                    edgecolor="#B42318",
                    linewidth=2.0,
                )
            )
            axis.get_yticklabels()[index].set_fontweight("bold")
            axis.get_yticklabels()[index].set_color("#B42318")
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.suptitle(
        "Method P operations and governance outcomes",
        x=0.03,
        y=0.99,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    figure.text(
        0.03,
        0.94,
        "Expected labels are AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT references.",
        fontsize=8.5,
        color="#475569",
    )
    figure.text(
        0.03,
        0.025,
        "Red outlines mark reference mismatches. D2 records HOLD / REJECT in all three "
        "technical repetitions; the declared HOLD governance reference is preserved.",
        fontsize=8.5,
        color="#7F1D1D",
    )
    figure.subplots_adjust(left=0.08, right=0.99, top=0.84, bottom=0.15)
    return figure


def duration_figure(dataset: ExperimentDataset) -> Any:
    plt, _, _, _, _ = _pyplot()
    all_rows = duration_rows(dataset)
    available = [row for row in all_rows if row["duration_ms"] is not None]
    figure, axes = plt.subplots(
        1,
        4,
        figsize=(14.2, 4.7),
        sharey=True,
        squeeze=False,
    )
    axes_flat = list(axes[0])
    all_scenarios = scenario_rows(dataset)
    operation_scenarios = {
        operation: [
            row["scenario_id"] for row in all_scenarios if row["operation"] == operation.upper()
        ]
        for operation in OPERATIONS
    }
    offsets = {1: -0.12, 2: 0.0, 3: 0.12}
    if available:
        values = [float(row["duration_ms"]) for row in available]
        low = min(values)
        high = max(values)
        padding = max((high - low) * 0.12, 1.5)
        y_limits = (max(0.0, low - padding), high + padding)
    else:
        y_limits = (0.0, 1.0)

    for axis, operation in zip(axes_flat, OPERATIONS, strict=True):
        scenarios = operation_scenarios[operation]
        color = OPERATION_COLORS[operation.upper()]
        for scenario_index, scenario_id in enumerate(scenarios):
            scenario_data = [
                row
                for row in available
                if row["scenario_id"] == scenario_id and row["operation"] == operation
            ]
            for row in scenario_data:
                axis.scatter(
                    scenario_index + offsets.get(row["repetition"], 0.0),
                    row["duration_ms"],
                    s=46,
                    color=color,
                    edgecolor="#172033",
                    linewidth=0.65,
                    zorder=3,
                )
            axis.set_xticks(range(len(scenarios)), scenarios)
        axis.set_title(operation.upper(), color=color, fontweight="bold")
        axis.set_ylim(*y_limits)
        axis.grid(axis="y", color="#D8DEE8", linewidth=0.65)
        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_color("#B9C2D0")
        axis.spines["bottom"].set_color("#B9C2D0")
        axis.tick_params(axis="both", labelsize=8)
        if not available:
            axis.text(
                0.5,
                0.5,
                "No duration measurements",
                transform=axis.transAxes,
                ha="center",
                va="center",
                color="#475569",
                fontsize=8,
            )

    axes_flat[0].set_ylabel("Execution duration (ms)")
    figure.suptitle(
        "Method P execution duration by operation and scenario",
        x=0.03,
        y=0.99,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    figure.text(
        0.03,
        0.01,
        "Each dot is an individual technical repetition. The horizontal offsets only separate "
        "overlapping points; three runs per scenario are not independent cases.",
        fontsize=8.5,
        color="#475569",
    )
    figure.subplots_adjust(left=0.07, right=0.995, top=0.83, bottom=0.2, wspace=0.24)
    return figure


def export_publication_figures(
    dataset: ExperimentDataset,
    output_dir: str | Path,
    force: bool = False,
) -> tuple[Path, ...]:
    """Write the three publication figures as SVG and 300 dpi PNG."""

    validate_publication_export_readiness(dataset)
    selected_output = Path(output_dir).expanduser().resolve()
    targets = [
        selected_output / f"{basename}.{extension}"
        for basename in OUTPUT_BASENAMES
        for extension in ("svg", "png")
    ]
    existing = [path for path in targets if path.exists()]
    if existing and not force:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Figure output already exists: {names}. Choose another --output-dir or pass --force."
        )

    selected_output.mkdir(parents=True, exist_ok=True)
    figures = (
        coverage_figure(dataset),
        operations_governance_figure(dataset),
        duration_figure(dataset),
    )
    created: list[Path] = []
    for basename, figure in zip(OUTPUT_BASENAMES, figures, strict=True):
        for extension in ("svg", "png"):
            output_path = selected_output / f"{basename}.{extension}"
            metadata = (
                {
                    "Creator": "EvoFitBench Method P Research Dashboard",
                    "Date": None,
                    "Title": basename.replace("_", " ").title(),
                }
                if extension == "svg"
                else {
                    "Software": "EvoFitBench Method P Research Dashboard",
                    "Title": basename.replace("_", " ").title(),
                }
            )
            figure.savefig(
                output_path,
                format=extension,
                dpi=300 if extension == "png" else "figure",
                bbox_inches="tight",
                facecolor="white",
                metadata=metadata,
            )
            if extension == "svg":
                lines = output_path.read_text(encoding="utf-8").splitlines()
                output_path.write_text(
                    "\n".join(line.rstrip() for line in lines) + "\n",
                    encoding="utf-8",
                )
            created.append(output_path)
    import matplotlib.pyplot as plt

    for figure in figures:
        plt.close(figure)
    return tuple(created)


def _default_output_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / DEFAULT_OUTPUT_RELATIVE_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export reproducible SVG and high-resolution PNG figures."
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=default_results_path(),
        help="Path to the corrected results_v1.json file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_default_output_path(),
        help="Output folder; defaults to the ignored experiments/results figure directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace figure files with the same deterministic names.",
    )
    args = parser.parse_args(argv)

    try:
        dataset = load_dataset(args.results)
        paths = export_publication_figures(dataset, args.output_dir, force=args.force)
    except (DashboardDataError, FileExistsError, OSError) as exc:
        print(f"research-figures: {exc}", file=sys.stderr)
        return 2
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
