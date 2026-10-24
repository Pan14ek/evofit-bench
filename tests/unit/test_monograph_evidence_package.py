"""Integrity, replay, and derived-artifact checks for the CI-only monograph package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from experiments.pilots import verify_monograph_evidence as evidence
from research_dashboard.figures import export_publication_figures

ROOT = Path(__file__).resolve().parents[2]


def _source_evidence_paths() -> tuple[Path, ...]:
    run_dir = ROOT / "experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1"
    canonical_dir = ROOT / "architecture/acceptance/a1"
    pilot_dir = ROOT / "experiments/pilots"
    fixed_paths = (
        run_dir / "SHA256SUMS",
        run_dir / "execution_manifest.json",
        run_dir / "raw_records_manifest.json",
        run_dir / "score_manifest.json",
        run_dir / "results_v1.json",
        run_dir / "report_v1.md",
        pilot_dir / "mono_e1_dev_p_decisions_v1/reference_v1.json",
        pilot_dir / "mono_e1_dev_p_decisions_v1/scenarios_v1.json",
        canonical_dir / "a0_3_canonical_checkpoint.json",
        canonical_dir / "a0_3_canonical_public_api_observation.json",
        canonical_dir / "a0_3_canonical_module_graph_observation.json",
        canonical_dir / "a0_4_canonical_checkpoint.json",
        canonical_dir / "a0_4_canonical_public_api_observation.json",
        canonical_dir / "a0_4_canonical_module_graph_observation.json",
        pilot_dir / "EVAL01_RAW_EVIDENCE_V1.zip",
        pilot_dir / "EVAL01_ANALYSIS_V1.json",
        pilot_dir / "EVAL01_CASE_RESULTS_V1.csv",
        pilot_dir / "EVAL01_REPORT_V1.md",
        pilot_dir / "EVAL02_RAW_EVIDENCE_V1.zip",
        pilot_dir / "EVAL02_ANALYSIS_V1.json",
        pilot_dir / "EVAL02_CASE_RESULTS_V1.csv",
        pilot_dir / "EVAL02_REPORT_V1.md",
        pilot_dir / "EVAL02_POST_EXPERIMENT_ERRATUM_V1.md",
    )
    checksum_paths = tuple(
        run_dir / line.split("  ", maxsplit=1)[1].lstrip("* ")
        for line in (run_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    )
    return tuple(dict.fromkeys((*fixed_paths, *checksum_paths)))


def _digests(paths: tuple[Path, ...]) -> dict[Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_package_replays_read_only_and_keeps_claim_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protected_paths = (
        *_source_evidence_paths(),
        *(
            evidence.PACKAGE_DIR / filename
            for filenames in evidence.FIGURE_FILES.values()
            for filename in filenames
        ),
    )
    before = _digests(protected_paths)
    export_figures = export_publication_figures

    def export_with_platform_render_metadata(
        dataset: Any,
        output_dir: str | Path,
        force: bool = False,
    ) -> tuple[Path, ...]:
        from PIL import Image, PngImagePlugin

        paths = export_figures(dataset, output_dir, force=force)
        for path in paths:
            if path.suffix == ".svg":
                svg = path.read_bytes()
                path.write_bytes(svg.replace(b"</svg>", b"<!-- host-specific -->\n</svg>"))
            else:
                with Image.open(path) as image:
                    image.load()
                    pnginfo = PngImagePlugin.PngInfo()
                    pnginfo.add_text("Host", "linux")
                    image.save(path, format="PNG", pnginfo=pnginfo)
        return paths

    monkeypatch.setattr(
        evidence, "export_publication_figures", export_with_platform_render_metadata
    )

    result = evidence.verify_package()

    assert _digests(protected_paths) == before
    assert result["status"] == "PASS"
    assert result["verified_derived_files"] == 17
    assert result["p_raw_files_verified"] == 51
    assert result["p_input_bundle_archives_verified"] == 8
    assert result["p_raw_checksum_files_verified"] == 57
    assert (result["eval01_calls"], result["eval02_calls"]) == (42, 60)
    assert result["eval02_diagnostic_mismatches"] == 3
    assert (result["p_scenario_count"], result["p_technical_repetition_count"]) == (8, 24)
    assert result["p_actual_post_adaptation_coverage"] == "NOT_MEASURED"
    assert result["official_mono_e1_b0p_experiment"] is False

    package = json.loads((evidence.PACKAGE_DIR / "evidence_tables_v1.json").read_text())
    p_metrics = package["verification"]["method_p_raw_replay"]
    assert p_metrics["operation_matches"] == "24/24"
    assert p_metrics["combined_correct_incorrect_not_evaluable"] == [21, 3, 0]
    assert p_metrics["actual_post_adaptation_coverage"] == {"NOT_MEASURED": 24}
    assert p_metrics["b0_synth_is_independent_arm"] is False
    assert package["verification"]["evaluator_control_validation"]["EVAL-02"][
        "diagnostic_mismatch_repeats"
    ] == [1, 2, 3]

    figures = package["figure_to_claim"]
    assert len(figures) == 3
    assert any("NOT_MEASURED" in caption for caption in figures[0]["caption_and_footnotes"])
    assert "Author-declared" in figures[1]["x_axis_or_columns"][0][-1]
    for row in figures:
        assert row["figure_files"]
        for filename, expected_digest in row["figure_files"].items():
            assert expected_digest == evidence._sha256_file(evidence.PACKAGE_DIR / filename)


def test_binary_metrics_exclude_unavailable_cases() -> None:
    rows = [
        {
            "case_id": "positive",
            "valid_for_confusion_matrix": True,
            "expected_compliance": "NON_COMPLIANT",
            "observed_compliance_case_level": "NON_COMPLIANT",
        },
        {
            "case_id": "negative",
            "valid_for_confusion_matrix": True,
            "expected_compliance": "COMPLIANT",
            "observed_compliance_case_level": "COMPLIANT",
        },
        {
            "case_id": "out_of_scope",
            "valid_for_confusion_matrix": False,
            "expected_compliance": "COMPLIANT",
            "observed_compliance_case_level": "NOT_EVALUABLE",
        },
    ]

    metrics = evidence._metric_from_case_rows(rows)

    assert metrics["confusion_matrix"] == {"tp": 1, "fp": 0, "tn": 1, "fn": 0}
    assert metrics["evaluable_cases"] == 2
    assert metrics["excluded_cases"] == 1
    assert metrics["f1"] == 1.0


def test_eval02_report_rejects_undocumented_changes_to_archived_evidence() -> None:
    archive_path = ROOT / "experiments/pilots/EVAL02_RAW_EVIDENCE_V1.zip"
    with ZipFile(archive_path) as archive:
        archived_report = archive.read("EVAL02_REPORT_V1.md")
    published_report = (ROOT / "experiments/pilots/EVAL02_REPORT_V1.md").read_bytes()
    tampered_report = published_report.replace(b"all 60 calls completed", b"all 59 calls completed")
    assert tampered_report != published_report

    with pytest.raises(evidence.EvidencePackageError, match="clarification"):
        evidence._assert_eval02_report_preserves_archive(archived_report, tampered_report, ROOT)


def test_evaluator_report_rejects_drift_in_published_confusion_metrics() -> None:
    analysis_path = ROOT / "experiments/pilots/EVAL02_ANALYSIS_V1.json"
    report_path = ROOT / "experiments/pilots/EVAL02_REPORT_V1.md"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    analysis["evaluator_metrics"]["AC_PUBLIC_API"]["confusion_matrix"]["tp"] += 1

    with pytest.raises(evidence.EvidencePackageError, match="report TP differs"):
        evidence._assert_eval_report_aggregates(
            "EVAL-02",
            analysis,
            report_path.read_text(encoding="utf-8"),
        )
