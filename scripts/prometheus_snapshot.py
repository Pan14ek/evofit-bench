"""Parsing and interval calculations for Prometheus text exposition."""

from collections.abc import Iterable

from prometheus_client.parser import text_string_to_metric_families


def parse_snapshot(text: str) -> dict[str, list[tuple[dict[str, str], float]]]:
    """Parse sample names into label/value rows without losing dimensions."""
    values: dict[str, list[tuple[dict[str, str], float]]] = {}
    for family in text_string_to_metric_families(text):
        for sample in family.samples:
            values.setdefault(sample.name, []).append((dict(sample.labels), float(sample.value)))
    return values


def value(snapshot: dict[str, list[tuple[dict[str, str], float]]], metric: str) -> float | None:
    """Return a metric only when the snapshot has exactly one matching sample."""
    rows = snapshot.get(metric, [])
    return rows[0][1] if len(rows) == 1 else None


def aggregate(
    snapshot: dict[str, list[tuple[dict[str, str], float]]],
    metric: str,
    labels: dict[str, str],
) -> float | None:
    """Sum matching samples, returning None when no sample exists."""
    rows = [
        sample
        for sample_labels, sample in snapshot.get(metric, [])
        if all(sample_labels.get(k) == v for k, v in labels.items())
    ]
    return sum(rows) if rows else None


def delta(after: float | None, before: float | None) -> float | None:
    """Return a non-negative counter delta when both readings exist."""
    if after is None or before is None:
        return None
    return max(0.0, after - before)


def sum_values(values: Iterable[float | None]) -> float | None:
    """Sum values unless all are missing."""
    present = [item for item in values if item is not None]
    return sum(present) if present else None
