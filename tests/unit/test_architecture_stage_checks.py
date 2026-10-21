"""Adversarial controls for historical/current architecture-stage separation."""

from pathlib import Path

import pytest

from scripts import check_architecture_stages as stage


def _fake_modules(root: Path, public: tuple[str, ...] = ()) -> None:
    for name in stage.MODULES:
        folder = root / "app/modules" / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "__init__.py").write_text("", encoding="utf-8")
        if name in public:
            (folder / "public.py").write_text("", encoding="utf-8")


def test_detects_exact_baseline_when_no_public_apis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)
    monkeypatch.setattr(stage, "_git", lambda *_args: "")
    assert stage.detect_stage(tmp_path) == stage.A01


def _fake_w4_preparation_files(root: Path) -> None:
    for path in stage.W4_REQUIRED_APP_PATHS:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# W4 preparation fixture\n", encoding="utf-8")


def test_detects_allowlisted_w4_preparation_overlay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)
    _fake_w4_preparation_files(tmp_path)
    monkeypatch.setattr(stage, "_git", lambda *_args: "\n".join(stage.W4_ALLOWED_APP_PATHS))

    assert stage.detect_stage(tmp_path) == stage.W4_PREPARATION


def test_w4_preparation_requires_event_implementation_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)
    monkeypatch.setattr(stage, "_git", lambda *_args: "\n".join(stage.W4_ALLOWED_APP_PATHS))

    with pytest.raises(stage.StageCheckError, match="required W4 files missing"):
        stage.detect_stage(tmp_path)


def test_w4_preparation_overlay_rejects_task_service_or_app_main_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)
    monkeypatch.setattr(
        stage,
        "_git",
        lambda *_args: "app/main.py\napp/modules/tasks/service.py",
    )

    with pytest.raises(stage.StageCheckError, match="outside the W4 preparation allowlist"):
        stage.detect_stage(tmp_path)


def test_rejects_partial_public_interface_inventory(tmp_path: Path) -> None:
    _fake_modules(tmp_path, ("users", "tasks"))
    with pytest.raises(stage.StageCheckError, match="Partial public API"):
        stage.detect_stage(tmp_path)


def test_rejects_vacuous_absent_capability_tree(tmp_path: Path) -> None:
    with pytest.raises(stage.StageCheckError, match="Missing capability"):
        stage.detect_stage(tmp_path)


def test_requires_concrete_w1_contract_tests_for_complete_stage(tmp_path: Path) -> None:
    _fake_modules(tmp_path, stage.MODULES)
    with pytest.raises(stage.StageCheckError, match="mandatory contract tests"):
        stage.detect_stage(tmp_path)
    test_file = tmp_path / "tests/unit/test_module_public_apis.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_example(): pass\n", encoding="utf-8")
    assert stage.detect_stage(tmp_path) == stage.A02


def test_historical_pin_rejects_unknown_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def wrong_commit(_root: Path, *_args: str) -> str:
        return "0" * 40

    monkeypatch.setattr(stage, "_git", wrong_commit)
    with pytest.raises(stage.StageCheckError, match="Historical A0.1 Git commit"):
        stage.verify_historical_pin(tmp_path)


def test_historical_pin_rejects_stale_app_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def changed_tree(_root: Path, *args: str) -> str:
        return stage.HISTORICAL_A01_SHA if "^{commit}" in args[-1] else "0" * 40

    monkeypatch.setattr(stage, "_git", changed_tree)
    with pytest.raises(stage.StageCheckError, match="app tree changed"):
        stage.verify_historical_pin(tmp_path)


def test_mismatched_declared_and_actual_stage_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)
    monkeypatch.setattr(stage, "_git", lambda *_args: "")
    with pytest.raises(stage.StageCheckError, match="Requested architecture stage"):
        stage.current_stage_acceptance(tmp_path, requested_stage=stage.A02)


def test_claimed_baseline_cannot_pass_with_altered_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)

    def wrong_tree(_root: Path, *args: str) -> str:
        if args == ("status", "--porcelain", "--", "app", "architecture", "tests"):
            return ""
        if args and args[0] == "diff":
            return ""
        return "not-the-expected-tree"

    monkeypatch.setattr(stage, "_git", wrong_tree)
    with pytest.raises(stage.StageCheckError, match="nonhistorical app tree"):
        stage.current_stage_acceptance(tmp_path, requested_stage="auto")


def test_dirty_application_source_cannot_pass_as_sha_bound(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)

    def dirty_git(_root: Path, *args: str) -> str:
        return "" if args and args[0] == "diff" else " M app/modules/tasks/service.py"

    monkeypatch.setattr(stage, "_git", dirty_git)
    with pytest.raises(stage.StageCheckError, match="dirty"):
        stage.current_stage_acceptance(tmp_path, requested_stage="auto")


def test_new_stage_executes_focused_checks_without_old_exact_inventory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path, stage.MODULES)
    test_file = tmp_path / "tests/unit/test_module_public_apis.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_contract(): pass\n", encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(stage, "_git", lambda *_args: "")
    monkeypatch.setattr(
        stage,
        "_run_pytest",
        lambda _root, paths, *, historical: calls.append(paths),
    )
    assert stage.current_stage_acceptance(tmp_path, requested_stage=stage.A02) == stage.A02
    assert calls == [
        ["tests/architecture/test_layer_rules.py", "tests/unit/test_module_public_apis.py"]
    ]


def test_w4_preparation_runs_layer_and_event_contract_checks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)
    _fake_w4_preparation_files(tmp_path)
    calls: list[list[str]] = []

    def git(_root: Path, *args: str) -> str:
        if args and args[0] == "diff":
            return "\n".join(stage.W4_ALLOWED_APP_PATHS)
        if args and args[0] == "rev-parse":
            return "source-sha"
        return ""

    monkeypatch.setattr(stage, "_git", git)
    monkeypatch.setattr(
        stage,
        "_run_pytest",
        lambda _root, paths, *, historical: calls.append(paths),
    )

    assert stage.current_stage_acceptance(tmp_path, requested_stage=stage.W4_PREPARATION) == (
        stage.W4_PREPARATION
    )
    assert calls == [["tests/architecture/test_layer_rules.py", "tests/unit/test_domain_events.py"]]


def test_w2_evaluator_tests_appear_only_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path, stage.MODULES)
    for path in (
        "tests/unit/test_module_public_apis.py",
        "tests/architecture/a1/test_evaluators.py",
    ):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def test_contract(): pass\n", encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(stage, "_git", lambda *_args: "")
    monkeypatch.setattr(
        stage,
        "_run_pytest",
        lambda _root, paths, *, historical: calls.append(paths),
    )
    stage.current_stage_acceptance(tmp_path, requested_stage=stage.A02)
    assert "tests/architecture/a1/test_evaluators.py" in calls[0]
