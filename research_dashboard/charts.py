"""Interactive Plotly chart builders for the Streamlit presentation."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from research_dashboard.data import ExperimentDataset
from research_dashboard.metrics import (
    GOVERNANCE_RESULTS,
    OPERATIONS,
    confusion_matrix,
    duration_rows,
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

_TRANSITION_COLORS = {
    **STATUS_COLORS,
    **OPERATION_COLORS,
    **GOVERNANCE_COLORS,
    "OP_HOLD": OPERATION_COLORS["HOLD"],
    "GOV_HOLD": GOVERNANCE_COLORS["HOLD"],
    "MIXED": "#9B59B6",
    "NO DATA": "#D9DEE7",
    "UNAVAILABLE": "#D9DEE7",
}
_TRANSITION_COLUMNS = (
    "Current coverage assessment",
    "Observed operation",
    "Candidate coverage assessment",
    "Governance",
)
_TRANSITION_FIELDS = (
    "current_coverage",
    "operation",
    "candidate_coverage",
    "governance",
)
_TRANSITION_CATEGORIES = (
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


def _transition_category(column: str, value: str) -> str:
    if column == "Observed operation" and value == "HOLD":
        return "OP_HOLD"
    if column == "Governance" and value == "HOLD":
        return "GOV_HOLD"
    return value


def _empty_figure(message: str, height: int = 320) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 15, "color": "#475569"},
    )
    figure.update_layout(
        height=height,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return figure


def _discrete_colorscale(colors: list[str]) -> list[list[Any]]:
    stops: list[list[Any]] = []
    count = len(colors)
    for index, color in enumerate(colors):
        stops.append([index / count, color])
        stops.append([(index + 1) / count, color])
    return stops


def coverage_transition_figure(rows: list[dict[str, Any]]) -> go.Figure:
    """Show categorical current assessment → operation → candidate → governance."""

    if not rows:
        return _empty_figure("No scenario records are available.")
    category_indexes = {category: index for index, category in enumerate(_TRANSITION_CATEGORIES)}
    labels: list[list[str]] = []
    numeric: list[list[int]] = []
    for row in rows:
        row_labels = [str(row.get(field, "NO DATA")).upper() for field in _TRANSITION_FIELDS]
        labels.append(row_labels)
        numeric.append(
            [
                category_indexes.get(
                    _transition_category(column, label),
                    category_indexes["UNAVAILABLE"],
                )
                for column, label in zip(_TRANSITION_COLUMNS, row_labels, strict=True)
            ]
        )

    figure = go.Figure(
        data=go.Heatmap(
            x=list(range(len(_TRANSITION_COLUMNS))),
            y=list(range(len(rows))),
            z=numeric,
            text=labels,
            texttemplate="%{text}",
            textfont={"size": 12, "color": "#111827"},
            customdata=[
                [[row["scenario_id"], column] for column in _TRANSITION_COLUMNS] for row in rows
            ],
            colorscale=_discrete_colorscale(
                [_TRANSITION_COLORS[name] for name in _TRANSITION_CATEGORIES]
            ),
            zmin=-0.5,
            zmax=len(_TRANSITION_CATEGORIES) - 0.5,
            showscale=False,
            xgap=3,
            ygap=3,
            hovertemplate="%{customdata[0]}<br>%{customdata[1]}: %{text}<extra></extra>",
        )
    )
    highlighted = [row["scenario_id"] for row in rows if row.get("candidate_transition_emphasized")]
    subtitle = "Candidate assessment only; actual post-adaptation coverage: NOT_MEASURED."
    if highlighted:
        subtitle += f" Outlined scenarios: {', '.join(highlighted)}."
    figure.update_layout(
        template="plotly_white",
        title={"text": (f"Assessed current and candidate configurations<br><sup>{subtitle}</sup>")},
        height=max(390, 48 * len(rows) + 145),
        margin={"l": 55, "r": 24, "t": 85, "b": 75},
        font={"family": "Arial, sans-serif", "size": 12, "color": "#172033"},
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis={
            "side": "top",
            "tickmode": "array",
            "tickvals": list(range(len(_TRANSITION_COLUMNS))),
            "ticktext": list(_TRANSITION_COLUMNS),
            "tickangle": 0,
            "automargin": True,
        },
        yaxis={
            "tickmode": "array",
            "tickvals": list(range(len(rows))),
            "ticktext": [row["scenario_id"] for row in rows],
            "autorange": "reversed",
            "title": None,
            "automargin": True,
        },
        shapes=[
            {
                "type": "rect",
                "xref": "x",
                "yref": "y",
                "x0": -0.48,
                "x1": len(_TRANSITION_COLUMNS) - 0.52,
                "y0": index - 0.46,
                "y1": index + 0.46,
                "line": {"color": "#5B21B6", "width": 2},
                "fillcolor": "rgba(0,0,0,0)",
                "layer": "above",
            }
            for index, row in enumerate(rows)
            if row.get("candidate_transition_emphasized")
        ],
    )
    return figure


def confusion_matrix_figure(dataset: ExperimentDataset, decision: str) -> go.Figure:
    categories, values = confusion_matrix(dataset, decision)
    if not any(any(row) for row in values):
        return _empty_figure(f"No evaluable {decision} decisions are available.")
    labels = [[str(value) for value in row] for row in values]
    figure = go.Figure(
        data=go.Heatmap(
            z=values,
            x=[item.upper() for item in categories],
            y=[item.upper() for item in categories],
            text=labels,
            texttemplate="%{text}",
            textfont={"size": 13, "color": "#172033"},
            colorscale="Blues",
            zmin=0,
            showscale=False,
            xgap=3,
            ygap=3,
            hovertemplate="Expected: %{y}<br>Observed: %{x}<br>Records: %{z}<extra></extra>",
        )
    )
    title = (
        "Expected vs observed operation (author-declared reference)"
        if decision == "operation"
        else "Expected vs observed governance (author-declared reference)"
    )
    figure.update_layout(
        template="plotly_white",
        title=title,
        height=330,
        margin={"l": 90, "r": 15, "t": 55, "b": 75},
        xaxis={"title": "Observed", "side": "bottom"},
        yaxis={"title": "Expected", "autorange": "reversed"},
        font={"family": "Arial, sans-serif", "size": 12},
    )
    return figure


def governance_distribution_figure(dataset: ExperimentDataset) -> go.Figure:
    distribution = {
        outcome: sum(
            row.get("governance_result") == outcome
            for row in dataset.results["technical_repetition_results"]
        )
        for outcome in GOVERNANCE_RESULTS
    }
    categories = list(GOVERNANCE_RESULTS)
    values = [int(distribution.get(category, 0)) for category in categories]
    if not sum(values):
        return _empty_figure("No governance decisions are available.")
    figure = go.Figure(
        data=go.Bar(
            x=categories,
            y=values,
            text=[str(value) for value in values],
            textposition="outside",
            marker={
                "color": [GOVERNANCE_COLORS[category] for category in categories],
                "line": {"color": "#172033", "width": 0.6},
            },
            hovertemplate="%{x}: %{y} technical repetitions<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white",
        title="Observed governance outcomes",
        height=290,
        margin={"l": 20, "r": 20, "t": 55, "b": 35},
        xaxis={"title": None},
        yaxis={"title": "Technical repetitions", "rangemode": "tozero", "dtick": 1},
        font={"family": "Arial, sans-serif", "size": 12},
        showlegend=False,
    )
    return figure


def duration_figure(
    dataset: ExperimentDataset,
    operations: set[str] | None = None,
    scenario_ids: set[str] | None = None,
) -> go.Figure:
    rows = [
        row
        for row in duration_rows(dataset, operations, scenario_ids)
        if row["duration_ms"] is not None
    ]
    if not rows:
        return _empty_figure("No execution-duration measurements are available for these filters.")

    all_scenario_ids = sorted({row["scenario_id"] for row in rows})
    x_indexes = {scenario_id: index for index, scenario_id in enumerate(all_scenario_ids)}
    offsets = {1: -0.12, 2: 0.0, 3: 0.12}
    figure = go.Figure()
    for operation in OPERATIONS:
        selected = [row for row in rows if row["operation"] == operation]
        if not selected:
            continue
        labels = [row["scenario_id"] for row in selected]
        x_values = [
            x_indexes[row["scenario_id"]] + offsets.get(row["repetition"], 0.0) for row in selected
        ]
        customdata = [
            [row["scenario_id"], row["repetition"], row["duration_ns"]] for row in selected
        ]
        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=[row["duration_ms"] for row in selected],
                mode="markers",
                name=operation.upper(),
                text=labels,
                customdata=customdata,
                marker={
                    "size": 12,
                    "color": OPERATION_COLORS[operation.upper()],
                    "line": {"color": "#172033", "width": 0.8},
                    "symbol": "circle",
                },
                hovertemplate=(
                    "Scenario: %{customdata[0]}<br>"
                    "Technical repetition: %{customdata[1]}<br>"
                    "Duration: %{y:.3f} ms (%{customdata[2]} ns)"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )

    figure.update_layout(
        template="plotly_white",
        title={
            "text": (
                "Method P execution duration by scenario"
                "<br><sup>Every point is one technical repetition; no significance "
                "or baseline comparison is implied.</sup>"
            )
        },
        height=430,
        margin={"l": 65, "r": 20, "t": 85, "b": 70},
        xaxis={
            "title": "Scenario",
            "tickmode": "array",
            "tickvals": list(range(len(all_scenario_ids))),
            "ticktext": all_scenario_ids,
            "range": [-0.45, max(0.45, len(all_scenario_ids) - 0.55)],
            "showgrid": False,
        },
        yaxis={"title": "Execution duration (ms)", "rangemode": "tozero"},
        font={"family": "Arial, sans-serif", "size": 12},
        legend={"title": "Observed operation", "orientation": "h", "y": -0.23},
        hovermode="closest",
    )
    return figure


def duration_distribution_figure(rows: list[dict[str, Any]]) -> go.Figure:
    """Show the filtered descriptive duration distribution and its measurement count."""

    values = [
        row["duration_ms"] for row in rows if isinstance(row.get("duration_ms"), (int, float))
    ]
    if not values:
        return _empty_figure("No execution-duration measurements are available for these filters.")
    figure = go.Figure(
        data=go.Histogram(
            x=values,
            nbinsx=min(8, max(3, len(values))),
            marker={"color": "#0072B2", "line": {"color": "#172033", "width": 0.8}},
            hovertemplate="%{x:.3f} ms<br>%{y} technical repetitions<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white",
        title="Observed execution-duration distribution",
        height=330,
        margin={"l": 55, "r": 20, "t": 55, "b": 55},
        xaxis={"title": "Execution duration (ms)"},
        yaxis={"title": "Technical repetitions", "rangemode": "tozero", "dtick": 1},
        font={"family": "Arial, sans-serif", "size": 12},
        showlegend=False,
    )
    return figure
