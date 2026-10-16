"""Structural checks for the unapproved G1 preparation register."""

from pathlib import Path

REGISTER = Path(__file__).parents[2] / "docs/G1_METHOD_DECISION_REGISTER.md"


def test_g1_register_lists_every_open_decision_and_discrepancy() -> None:
    document = REGISTER.read_text(encoding="utf-8")

    assert "DRAFT — AWAITING INDEPENDENT METHODOLOGICAL REVIEW" in document
    for number in range(1, 11):
        assert f"OPEN-{number:02d}" in document
    for number in range(1, 7):
        assert f"M-{number:02d}" in document


def test_g1_register_preserves_pending_status_and_gate_boundaries() -> None:
    document = REGISTER.read_text(encoding="utf-8")

    assert "PENDING_INDEPENDENT_REVIEW" in document
    assert "PENDING_EXTERNAL_AUTHORITY" in document
    assert "DEFERRED_FUTURE_RESEARCH" in document
    assert "G1 — methodological/protocol freeze | **INCOMPLETE**" in document
    assert "G4 — measured-run authorization | **NOT AUTHORIZED**" in document
    assert "p_interface.py` remains `NOT_READY`" in document
    assert "Candidate primary endpoints, unapproved" in document
    assert "manuscript" in document and "executable DA01 RQ" in document
