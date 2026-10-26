"""Adversarial controls for historical/current architecture-stage separation."""

import shutil
from pathlib import Path

import pytest

from scripts import check_architecture_stages as stage

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _fake_modules(root: Path, public: tuple[str, ...] = ()) -> None:
    for name in stage.MODULES:
        folder = root / "app/modules" / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "__init__.py").write_text("", encoding="utf-8")
        if name in public:
            (folder / "public.py").write_text("", encoding="utf-8")


def _install_a03_manifest(root: Path) -> None:
    for relative in (stage.A03_MANIFEST, stage.A03_SCHEMA):
        source = REPOSITORY_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _install_a04_manifest(root: Path) -> None:
    for relative in (stage.A04_MANIFEST, stage.A04_SCHEMA):
        source = REPOSITORY_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _install_a05_manifest(root: Path) -> None:
    for relative in (stage.A05_MANIFEST, stage.A05_SCHEMA):
        source = REPOSITORY_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _install_a05_evaluators(root: Path) -> None:
    evaluator_root = root / "architecture/acceptance/a1"
    evaluator_root.mkdir(parents=True, exist_ok=True)
    for filename in ("public_api_v1.yaml", "module_graph_v1.yaml", "data_ownership_v1.yaml"):
        shutil.copyfile(
            REPOSITORY_ROOT / "architecture/acceptance/a1" / filename,
            evaluator_root / filename,
        )


def _fake_a03_subject(root: Path) -> None:
    _fake_modules(root, stage.MODULES)
    contract_test = root / "tests/unit/test_module_public_apis.py"
    contract_test.parent.mkdir(parents=True)
    contract_test.write_text("def test_contract(): pass\n", encoding="utf-8")
    _install_a03_manifest(root)


def _fake_a04_subject(root: Path) -> None:
    _fake_a03_subject(root)
    _install_a04_manifest(root)


def _fake_a05_subject(root: Path) -> None:
    _fake_a04_subject(root)
    _install_a05_manifest(root)
    _install_a05_evaluators(root)


def test_detects_exact_baseline_when_no_public_apis(tmp_path: Path) -> None:
    _fake_modules(tmp_path)
    assert stage.detect_stage(tmp_path) == stage.A01


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


def test_public_api_modules_alone_do_not_identify_a03(tmp_path: Path) -> None:
    _fake_modules(tmp_path, stage.MODULES)
    contract_test = tmp_path / "tests/unit/test_module_public_apis.py"
    contract_test.parent.mkdir(parents=True)
    contract_test.write_text("def test_contract(): pass\n", encoding="utf-8")
    assert stage.detect_stage(tmp_path) == stage.A02

    _install_a03_manifest(tmp_path)
    assert stage.detect_stage(tmp_path) == stage.A03
    manifest = stage._validate_a03_manifest(tmp_path)
    stage._validate_a03_policy_bindings(REPOSITORY_ROOT, manifest)


def test_a04_manifest_is_latest_state_and_policy_bindings_are_explicit(tmp_path: Path) -> None:
    _fake_a04_subject(tmp_path)

    assert stage.detect_stage(tmp_path) == stage.A04
    manifest = stage._validate_a04_manifest(tmp_path)
    stage._validate_a04_policy_bindings(REPOSITORY_ROOT, manifest)


def test_a05_manifest_is_prospective_successor_and_binds_ownership_policy(tmp_path: Path) -> None:
    _fake_a05_subject(tmp_path)
    assert stage.detect_stage(tmp_path) == stage.A05
    manifest = stage._validate_a05_manifest(tmp_path)
    stage._validate_a05_policy_bindings(tmp_path, manifest)
    assert manifest["source_provenance"]["predecessor_commit"] == stage.HISTORICAL_A04_SHA
    assert manifest["governance_requirements"]["required_evaluators"] == list(
        stage.A05_REQUIRED_EVALUATORS
    )


def test_a05_rejects_ownership_evaluator_or_exception_drift(tmp_path: Path) -> None:
    _fake_a05_subject(tmp_path)
    ownership_path = tmp_path / "architecture/acceptance/a1/data_ownership_v1.yaml"
    original = ownership_path.read_text(encoding="utf-8")
    ownership_path.write_text(
        original.replace("audit_events: audit", "audit_events: tasks"), encoding="utf-8"
    )
    with pytest.raises(stage.StageCheckError, match="A0.5_OWNERSHIP_CONFIG_MANIFEST_MISMATCH"):
        stage._validate_a05_policy_bindings(tmp_path, stage._validate_a05_manifest(tmp_path))

    ownership_path.write_text(original, encoding="utf-8")
    ownership_path.write_text(
        original.replace("path: app/db/model_registry.py", "path: app/db/other_registry.py"),
        encoding="utf-8",
    )
    with pytest.raises(stage.StageCheckError, match="A0.5_MODEL_REGISTRY_EXCEPTION_MISMATCH"):
        stage._validate_a05_policy_bindings(tmp_path, stage._validate_a05_manifest(tmp_path))


def test_committed_a03_manifest_removal_fails_acceptance_and_historical_a02_stays_valid(
    tmp_path: Path,
) -> None:
    """A0.3 cannot regress by deletion; a pre-A0.3 commit still detects as A0.2."""
    _fake_modules(tmp_path, stage.MODULES)
    contract_test = tmp_path / "tests/unit/test_module_public_apis.py"
    contract_test.parent.mkdir(parents=True)
    contract_test.write_text("def test_contract(): pass\n", encoding="utf-8")

    stage._git(tmp_path, "init", "--quiet")
    stage._git(tmp_path, "config", "user.name", "Architecture stage test")
    stage._git(tmp_path, "config", "user.email", "architecture-stage@example.test")
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "valid historical A0.2 source")
    a02_commit = stage._git(tmp_path, "rev-parse", "HEAD")
    assert stage.detect_stage(tmp_path) == stage.A02

    _install_a03_manifest(tmp_path)
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "establish A0.3 state")
    assert stage.detect_stage(tmp_path) == stage.A03

    (tmp_path / stage.A03_MANIFEST).unlink()
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "remove established A0.3 manifest")
    with pytest.raises(stage.StageCheckError, match="A0.3_MANIFEST_REMOVED_AFTER_ESTABLISHMENT"):
        stage.current_stage_acceptance(tmp_path, requested_stage=stage.A03)

    # Detection is based on HEAD ancestry, not the presence of later A0.3
    # commits in the object database or another ref.
    stage._git(tmp_path, "checkout", "--quiet", a02_commit)
    assert stage.detect_stage(tmp_path) == stage.A02


def test_a04_manifest_removal_or_stage_downgrade_fails_and_history_stays_detectable(
    tmp_path: Path,
) -> None:
    _fake_modules(tmp_path, stage.MODULES)
    contract_test = tmp_path / "tests/unit/test_module_public_apis.py"
    contract_test.parent.mkdir(parents=True)
    contract_test.write_text("def test_contract(): pass\n", encoding="utf-8")

    stage._git(tmp_path, "init", "--quiet")
    stage._git(tmp_path, "config", "user.name", "Architecture stage test")
    stage._git(tmp_path, "config", "user.email", "architecture-stage@example.test")
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "valid historical A0.2 source")
    a02_commit = stage._git(tmp_path, "rev-parse", "HEAD")

    _install_a03_manifest(tmp_path)
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "establish A0.3 state")
    a03_commit = stage._git(tmp_path, "rev-parse", "HEAD")
    assert stage.detect_stage(tmp_path) == stage.A03

    _install_a04_manifest(tmp_path)
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "establish A0.4 state")
    assert stage.detect_stage(tmp_path) == stage.A04
    with pytest.raises(stage.StageCheckError, match="Requested architecture stage"):
        stage.current_stage_acceptance(tmp_path, requested_stage=stage.A03)

    (tmp_path / stage.A04_MANIFEST).unlink()
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "remove established A0.4 manifest")
    with pytest.raises(stage.StageCheckError, match="A0.4_MANIFEST_REMOVED_AFTER_ESTABLISHMENT"):
        stage.current_stage_acceptance(tmp_path, requested_stage=stage.A03)

    stage._git(tmp_path, "checkout", "--quiet", a03_commit)
    assert stage.detect_stage(tmp_path) == stage.A03
    stage._git(tmp_path, "checkout", "--quiet", a02_commit)
    assert stage.detect_stage(tmp_path) == stage.A02


def test_a05_manifest_removal_fails_and_historical_a04_remains_detectable(tmp_path: Path) -> None:
    stage._git(tmp_path, "init", "--quiet")
    stage._git(tmp_path, "config", "user.name", "Architecture stage test")
    stage._git(tmp_path, "config", "user.email", "architecture-stage@example.test")
    _fake_a04_subject(tmp_path)
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "establish A0.4 state")
    a04_commit = stage._git(tmp_path, "rev-parse", "HEAD")
    _install_a05_manifest(tmp_path)
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "establish A0.5 state")
    assert stage.detect_stage(tmp_path) == stage.A05
    (tmp_path / stage.A05_MANIFEST).unlink()
    stage._git(tmp_path, "add", "-A")
    stage._git(tmp_path, "commit", "--quiet", "-m", "remove established A0.5 manifest")
    with pytest.raises(stage.StageCheckError, match="A0.5_MANIFEST_REMOVED_AFTER_ESTABLISHMENT"):
        stage.detect_stage(tmp_path)
    stage._git(tmp_path, "checkout", "--quiet", a04_commit)
    assert stage.detect_stage(tmp_path) == stage.A04


def test_a04_manifest_requires_valid_preserved_a03_record_and_schema(tmp_path: Path) -> None:
    _fake_a04_subject(tmp_path)
    (tmp_path / stage.A04_SCHEMA).unlink()
    with pytest.raises(stage.StageCheckError, match="A0.4_MANIFEST_SCHEMA_INVALID"):
        stage.detect_stage(tmp_path)

    (tmp_path / stage.A04_SCHEMA).write_bytes((REPOSITORY_ROOT / stage.A04_SCHEMA).read_bytes())
    (tmp_path / stage.A03_MANIFEST).unlink()
    with pytest.raises(stage.StageCheckError, match="A0.3_MANIFEST_INVALID"):
        stage.detect_stage(tmp_path)


def test_a04_policy_rejects_data_ownership_activation(tmp_path: Path) -> None:
    _fake_a04_subject(tmp_path)
    evaluator_root = tmp_path / "architecture/acceptance/a1"
    evaluator_root.mkdir(parents=True, exist_ok=True)
    for name in ("public_api_v1.yaml", "module_graph_v1.yaml", "data_ownership_v1.yaml"):
        source = REPOSITORY_ROOT / "architecture/acceptance/a1" / name
        shutil.copyfile(source, evaluator_root / name)
    ownership_path = evaluator_root / "data_ownership_v1.yaml"
    ownership = ownership_path.read_text(encoding="utf-8").replace(
        "A0_4_REPORT_QUERY_PORT: {applicability: NOT_APPLICABLE}",
        "A0_4_REPORT_QUERY_PORT: {applicability: ACTIVE}",
    )
    ownership_path.write_text(ownership, encoding="utf-8")
    manifest = stage._validate_a04_manifest(tmp_path)
    with pytest.raises(stage.StageCheckError, match="A0.4_OWNERSHIP_NOT_NOT_APPLICABLE"):
        stage._validate_a04_policy_bindings(tmp_path, manifest)


def test_a03_manifest_cannot_fall_back_to_a01_without_public_apis(tmp_path: Path) -> None:
    _fake_modules(tmp_path)
    _install_a03_manifest(tmp_path)
    with pytest.raises(stage.StageCheckError, match="A0.3 state lacks complete public APIs"):
        stage.detect_stage(tmp_path)


def test_a03_manifest_rejects_changed_dependency_graph(tmp_path: Path) -> None:
    _install_a03_manifest(tmp_path)
    manifest_path = tmp_path / stage.A03_MANIFEST
    contents = manifest_path.read_text(encoding="utf-8").replace(
        "{from: reporting, to: tasks}", "{from: reporting, to: notifications}"
    )
    manifest_path.write_text(contents, encoding="utf-8")
    with pytest.raises(stage.StageCheckError, match="A0.3_MANIFEST_GRAPH_MISMATCH"):
        stage._validate_a03_manifest(tmp_path)


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
    with pytest.raises(stage.StageCheckError, match="Requested architecture stage"):
        stage.current_stage_acceptance(tmp_path, requested_stage=stage.A02)


def test_claimed_baseline_cannot_pass_with_altered_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)

    def wrong_tree(_root: Path, *args: str) -> str:
        if args == ("status", "--porcelain", "--", "app", "architecture", "tests"):
            return ""
        return "not-the-expected-tree"

    monkeypatch.setattr(stage, "_git", wrong_tree)
    with pytest.raises(stage.StageCheckError, match="nonhistorical app tree"):
        stage.current_stage_acceptance(tmp_path, requested_stage="auto")


def test_dirty_application_source_cannot_pass_as_sha_bound(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_modules(tmp_path)
    monkeypatch.setattr(stage, "_git", lambda *_args: " M app/modules/tasks/service.py")
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


def test_a03_acceptance_requires_both_live_evaluators_and_adversarial_suite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_a03_subject(tmp_path)
    calls: list[tuple[str, object]] = []
    pytest_targets: list[list[str]] = []

    def git_result(_root: Path, *args: str) -> str:
        if args == ("status", "--porcelain", "--", "app", "architecture", "tests"):
            return ""
        return "a" * 40

    monkeypatch.setattr(stage, "_git", git_result)
    monkeypatch.setattr(
        stage,
        "_run_a03_evaluators",
        lambda _root, source_sha: calls.append(("evaluators", source_sha)),
    )
    monkeypatch.setattr(
        stage,
        "_run_pytest",
        lambda _root, paths, *, historical: pytest_targets.append(paths),
    )

    assert stage.current_stage_acceptance(tmp_path, requested_stage=stage.A03) == stage.A03
    assert calls == [("evaluators", "a" * 40)]
    assert pytest_targets == [
        [
            "tests/architecture/test_layer_rules.py",
            "tests/unit/test_module_public_apis.py",
            "tests/architecture/a1/test_evaluators.py",
        ]
    ]


def test_a03_evaluator_failure_blocks_architecture_tests(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_a03_subject(tmp_path)
    pytest_called = False

    def reject_graph(_root: Path, _source_sha: str) -> None:
        raise stage.StageCheckError("AC_MODULE_GRAPH evidence rejected: EVALUATOR_NOT_COMPLIANT")

    def unexpected_pytest(*_args: object, **_kwargs: object) -> None:
        nonlocal pytest_called
        pytest_called = True

    monkeypatch.setattr(
        stage,
        "_git",
        lambda _root, *args: (
            "a" * 40
            if args != ("status", "--porcelain", "--", "app", "architecture", "tests")
            else ""
        ),
    )
    monkeypatch.setattr(stage, "_run_a03_evaluators", reject_graph)
    monkeypatch.setattr(stage, "_run_pytest", unexpected_pytest)

    with pytest.raises(stage.StageCheckError, match="AC_MODULE_GRAPH evidence rejected"):
        stage.current_stage_acceptance(tmp_path, requested_stage=stage.A03)
    assert not pytest_called


def test_a04_acceptance_requires_both_evaluators_and_adversarial_suite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_a04_subject(tmp_path)
    calls: list[tuple[str, object]] = []
    pytest_targets: list[list[str]] = []

    def git_result(_root: Path, *args: str) -> str:
        if args == ("status", "--porcelain", "--", "app", "architecture", "tests"):
            return ""
        return "a" * 40

    monkeypatch.setattr(stage, "_git", git_result)
    monkeypatch.setattr(
        stage,
        "_run_a04_evaluators",
        lambda _root, source_sha: calls.append(("evaluators", source_sha)),
    )
    monkeypatch.setattr(
        stage,
        "_run_pytest",
        lambda _root, paths, *, historical: pytest_targets.append(paths),
    )

    assert stage.current_stage_acceptance(tmp_path, requested_stage=stage.A04) == stage.A04
    assert calls == [("evaluators", "a" * 40)]
    assert pytest_targets == [
        [
            "tests/architecture/test_layer_rules.py",
            "tests/unit/test_module_public_apis.py",
            "tests/architecture/a1/test_evaluators.py",
        ]
    ]


def test_a05_acceptance_requires_three_evaluators_and_ownership_suite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_a05_subject(tmp_path)
    calls: list[tuple[str, object]] = []
    pytest_targets: list[list[str]] = []
    monkeypatch.setattr(
        stage,
        "_git",
        lambda _root, *args: (
            ""
            if args == ("status", "--porcelain", "--", "app", "architecture", "tests")
            else "a" * 40
        ),
    )
    monkeypatch.setattr(
        stage, "_run_a05_evaluators", lambda _root, sha: calls.append(("evaluators", sha))
    )
    monkeypatch.setattr(
        stage, "_run_pytest", lambda _root, paths, *, historical: pytest_targets.append(paths)
    )
    assert stage.current_stage_acceptance(tmp_path, requested_stage=stage.A05) == stage.A05
    assert calls == [("evaluators", "a" * 40)]
    assert "tests/unit/test_a05_data_ownership.py" in pytest_targets[0]


def test_a04_evaluator_failure_blocks_architecture_tests(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_a04_subject(tmp_path)
    pytest_called = False

    def reject_public_api(_root: Path, _source_sha: str) -> None:
        raise stage.StageCheckError("AC_PUBLIC_API evidence rejected: EVALUATOR_NOT_COMPLIANT")

    def unexpected_pytest(*_args: object, **_kwargs: object) -> None:
        nonlocal pytest_called
        pytest_called = True

    monkeypatch.setattr(
        stage,
        "_git",
        lambda _root, *args: (
            "a" * 40
            if args != ("status", "--porcelain", "--", "app", "architecture", "tests")
            else ""
        ),
    )
    monkeypatch.setattr(stage, "_run_a04_evaluators", reject_public_api)
    monkeypatch.setattr(stage, "_run_pytest", unexpected_pytest)

    with pytest.raises(stage.StageCheckError, match="AC_PUBLIC_API evidence rejected"):
        stage.current_stage_acceptance(tmp_path, requested_stage=stage.A04)
    assert not pytest_called


def test_development_ci_pins_a05_architecture_stage() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "ARCHITECTURE_STAGE: A0_5_MODULE_DATA_OWNERSHIP" in workflow
