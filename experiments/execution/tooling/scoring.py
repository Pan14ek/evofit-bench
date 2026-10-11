"""Read-only, oracle-side RQ1 and RQ2 scoring for sealed artifacts."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed Git executable and validated argv, never a shell
from collections import Counter
from collections.abc import Mapping, Sequence, Set
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import validate_payload, validate_prediction
from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_file
from experiments.execution.tooling.sealing import load_verified_prediction
from experiments.execution.tooling.validity import valid_cover

TargetType = Literal["representation", "obligation"]
TargetKey = tuple[TargetType, str]
EMITTED_OPERATIONS = {"retain", "replace", "add", "deactivate", "adjust"}


def score_rq1(
    prediction: dict[str, Any],
    ground_truth: Mapping[str, Any],
    known_targets: Set[TargetKey] | None = None,
) -> dict[str, Any]:
    """Score sealed prediction decisions against a separate oracle mapping.

    Inputs are read only. The complete target universe is reconstructed from the
    oracle, and omitted targets receive the protocol's implicit-retain or
    missing-add normalization.
    """
    validate_prediction(prediction)
    universe, expected = _oracle_universe(ground_truth)
    if known_targets is None:
        raise ProtocolError("RQ1 requires a trusted known-target registry")
    known = _validated_known_targets(known_targets)
    if not set(universe).issubset(known):
        raise ProtocolError(
            "Trusted target registries do not cover the oracle classification universe"
        )
    predicted_affected = cast(list[dict[str, Any]], prediction["predicted_affected"])
    proposed_operations = cast(list[dict[str, Any]], prediction["proposed_operations"])
    positive_predictions: set[TargetKey] = set()
    emitted: dict[TargetKey, str] = {}
    diagnostics: list[dict[str, Any]] = []
    extra_decisions: list[dict[str, Any]] = []

    for item in predicted_affected:
        target = _target_key(item)
        operation = str(item["predicted_operation"])
        if target not in universe:
            extra_decisions.append(_extra_decision(target, operation, known))
            diagnostics.append(_diagnostic("EXTRA_PREDICTED_TARGET", target, operation))
            if target not in known:
                diagnostics.append(_diagnostic("UNKNOWN_TARGET", target, operation))
            positive_predictions.add(target)
        else:
            positive_predictions.add(target)

    for item in proposed_operations:
        target = _target_key(item)
        operation = str(item["operation"])
        if operation not in EMITTED_OPERATIONS:
            diagnostics.append(_diagnostic("UNDECLARED_OPERATION", target, operation))
            continue
        emitted[target] = operation
        if target not in universe:
            extra_decisions.append(_extra_decision(target, operation, known))
            diagnostics.append(_diagnostic("EXTRA_OPERATION_TARGET", target, operation))
            if target not in known:
                diagnostics.append(_diagnostic("UNKNOWN_TARGET", target, operation))

    true_positive_targets = {target for target in universe if expected[target] != "retain"}
    false_negative_targets = true_positive_targets - positive_predictions
    false_positive_in_targets = (positive_predictions & set(universe)) - true_positive_targets
    extra_positive_targets = positive_predictions - set(universe)
    true_negative_targets = {
        target
        for target in universe
        if expected[target] == "retain" and target not in positive_predictions
    }

    tp = len(true_positive_targets & positive_predictions)
    fp_in = len(false_positive_in_targets)
    fp_extra = len(extra_positive_targets)
    fp_total = fp_in + fp_extra
    fn = len(false_negative_targets)
    tn = len(true_negative_targets)
    precision, recall, f1, empty_detection = _impact_metrics(
        tp,
        fp_total,
        fn,
        len(true_positive_targets),
        len(positive_predictions),
    )

    normalized: list[dict[str, str]] = []
    operation_confusion: Counter[tuple[str, str]] = Counter()
    implicit_retain_count = 0
    explicit_retain_count = 0
    correct_operations = 0
    for target in universe:
        normalized_operation = emitted.get(target)
        if normalized_operation is None:
            if target[0] == "representation":
                normalized_operation = "retain"
                normalization = "implicit_retain"
                implicit_retain_count += 1
            else:
                normalized_operation = "missing_add"
                normalization = "missing_add"
        else:
            normalization = "explicit"
            if normalized_operation == "retain":
                explicit_retain_count += 1
        expected_operation = expected[target]
        operation_confusion[(expected_operation, normalized_operation)] += 1
        correct_operations += int(normalized_operation == expected_operation)
        normalized.append(
            {
                "target_type": target[0],
                "target_id": target[1],
                "expected_operation": expected_operation,
                "normalized_operation": normalized_operation,
                "normalization": normalization,
            }
        )

    matrix: dict[str, dict[str, int]] = {}
    for (expected_operation, predicted_operation), count in sorted(operation_confusion.items()):
        matrix.setdefault(expected_operation, {})[predicted_operation] = count
    operation_accuracy = correct_operations / len(universe) if universe else None
    return {
        "tp": tp,
        "fp_in": fp_in,
        "fp_extra": fp_extra,
        "fp_total": fp_total,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "operation_accuracy": operation_accuracy,
        "universe_size": len(universe),
        "implicit_retain_count": implicit_retain_count,
        "explicit_retain_count": explicit_retain_count,
        "correct_empty_set_detection": empty_detection,
        "operation_confusion": matrix,
        "normalized_operations": normalized,
        "extra_predicted_targets": _unique_decisions(extra_decisions),
        "diagnostics": _unique_diagnostics(diagnostics),
    }


def score_rq2(
    ground_truth: Mapping[str, Any],
    architecture_source_sha: str,
    configuration_before: Sequence[dict[str, Any]],
    verdicts_before: Mapping[str, dict[str, Any]],
    configuration_after: Sequence[dict[str, Any]],
    verdicts_after: Mapping[str, dict[str, Any]],
    obligation_verdicts_before: Sequence[dict[str, Any]] = (),
    obligation_verdicts_after: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Score the complete oracle obligation set before and after on one target."""
    oracle_obligations = ground_truth.get("required_obligations_after")
    if not isinstance(oracle_obligations, list) or not all(
        isinstance(item, str) and item for item in oracle_obligations
    ):
        raise ProtocolError("Ground truth lacks its complete required_obligations_after set")
    required = list(oracle_obligations)
    if not required or len(required) != len(set(required)):
        raise ProtocolError("RQ2 requires a non-empty, unique complete obligation set")
    before = _coverage_assessment(
        required,
        architecture_source_sha,
        configuration_before,
        verdicts_before,
        obligation_verdicts_before,
    )
    after = _coverage_assessment(
        required,
        architecture_source_sha,
        configuration_after,
        verdicts_after,
        obligation_verdicts_after,
    )
    return {
        "coverage_before": before["coverage"],
        "coverage_after": after["coverage"],
        "coverage_delta": after["coverage"] - before["coverage"],
        "required_obligations": required,
        "coverage_before_assessment": before,
        "coverage_after_assessment": after,
        "uncovered_obligations": after["uncovered_obligations"],
        "stale_representations": after["stale_representations"],
        "invalid_representations": after["invalid_representations"],
        "semantic_violation_counts": after["violation_counts"],
        "semantic_violation_denominator": after["violation_denominator"],
        "semantic_violation_rate": after["violation_rate"],
    }


def build_scored_result(
    prediction: dict[str, Any],
    prediction_sha256: str,
    rq1: dict[str, Any],
    rq2: dict[str, Any],
    diagnostics: Sequence[Mapping[str, Any]] = (),
    failure_statuses: Sequence[str] = (),
) -> dict[str, Any]:
    """Assemble a versioned scorer envelope without changing prediction bytes."""
    statuses = set(failure_statuses)
    if any(
        item.get("code") == "UNKNOWN_TARGET"
        for source in (rq1.get("diagnostics", ()), diagnostics)
        for item in source
    ):
        statuses.add("PROTOCOL_VIOLATION")
    result = {
        "schema_version": 1,
        "method_id": prediction["method_id"],
        "architecture_source_sha": prediction["architecture_source_sha"],
        "prediction_sha256": prediction_sha256,
        "rq1": rq1,
        "rq2": rq2,
        "diagnostics": [dict(item) for item in diagnostics],
        "failure_statuses": sorted(statuses),
    }
    validate_payload("scored_result.schema.json", result)
    return result


def score_sealed_prediction(
    prediction_directory: Path,
    ground_truth_path: Path,
    architecture_source_sha: str,
    configuration_before: Sequence[dict[str, Any]],
    verdicts_before: Mapping[str, dict[str, Any]],
    configuration_after: Sequence[dict[str, Any]],
    verdicts_after: Mapping[str, dict[str, Any]],
    diagnostics: Sequence[Mapping[str, Any]] = (),
    failure_statuses: Sequence[str] = (),
    obligation_verdicts_before: Sequence[dict[str, Any]] = (),
    obligation_verdicts_after: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Verify a sealed prediction, load the private oracle, and return a scorer envelope."""
    sealed = load_verified_prediction(prediction_directory)
    if sealed.payload["architecture_source_sha"] != architecture_source_sha:
        raise ProtocolError("Sealed prediction architecture SHA does not match the scorer run")
    ground_truth = load_private_ground_truth(str(ground_truth_path))
    known_targets = load_trusted_known_targets(architecture_source_sha)
    rq1 = score_rq1(sealed.payload, ground_truth, known_targets)
    rq2 = score_rq2(
        ground_truth,
        architecture_source_sha,
        configuration_before,
        verdicts_before,
        configuration_after,
        verdicts_after,
        obligation_verdicts_before,
        obligation_verdicts_after,
    )
    return build_scored_result(
        sealed.payload,
        sealed.sha256,
        rq1,
        rq2,
        diagnostics,
        failure_statuses,
    )


def load_trusted_known_targets(
    architecture_source_sha: str,
    repository: Path | None = None,
) -> set[TargetKey]:
    """Load general representation and obligation IDs from the pinned Git revision."""
    if re.fullmatch(r"[a-f0-9]{40}", architecture_source_sha) is None:
        raise ProtocolError("Known-target registry revision must be a full lowercase Git SHA")
    root = (repository or Path(__file__).resolve().parents[3]).resolve(strict=True)
    git = shutil.which("git")
    if git is None:
        raise ProtocolError("Git is required to load the trusted known-target registries")
    try:
        top_level = subprocess.run(  # noqa: S603  # nosec B603 - fixed Git argv
            [git, "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    except subprocess.CalledProcessError as error:
        raise ProtocolError("Could not resolve the trusted registry Git repository") from error
    if Path(top_level).resolve() != root:
        raise ProtocolError("Trusted target registries must be loaded from the Git root")

    representation_catalog = _load_pinned_yaml(
        git,
        root,
        architecture_source_sha,
        "fitness/catalog/a0-fitness-elements.yaml",
    )
    obligation_registry = _load_pinned_yaml(
        git,
        root,
        architecture_source_sha,
        "fitness/catalog/architectural-obligations.yaml",
    )
    representations = representation_catalog.get("representations")
    obligations = obligation_registry.get("obligations")
    if representation_catalog.get("schema_version") != 1 or not isinstance(representations, list):
        raise ProtocolError("Pinned representation catalog has an unsupported or malformed schema")
    if obligation_registry.get("schema_version") != 1 or not isinstance(obligations, list):
        raise ProtocolError("Pinned obligation registry has an unsupported or malformed schema")

    targets: set[TargetKey] = set()
    for target_type, entries in (("representation", representations), ("obligation", obligations)):
        if not entries:
            raise ProtocolError(f"Pinned {target_type} registry must be non-empty")
        identifiers: set[str] = set()
        for entry in entries:
            key = "id"
            identifier = entry.get(key) if isinstance(entry, Mapping) else None
            if (
                not isinstance(identifier, str)
                or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", identifier) is None
            ):
                raise ProtocolError(f"Pinned {target_type} registry contains an invalid identifier")
            if identifier in identifiers:
                raise ProtocolError(f"Pinned {target_type} registry contains duplicate IDs")
            identifiers.add(identifier)
            targets.add((cast(TargetType, target_type), identifier))
    return targets


def _load_pinned_yaml(
    git: str,
    repository: Path,
    revision: str,
    relative_path: str,
) -> dict[str, Any]:
    try:
        entry = subprocess.run(  # noqa: S603  # nosec B603 - validated revision/path Git argv
            [git, "-C", str(repository), "ls-tree", revision, "--", relative_path],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        if not entry.startswith(("100644 blob ", "100755 blob ")):
            raise ProtocolError(
                f"Pinned trusted registry is missing or not a regular file: {relative_path}"
            )
        content = subprocess.run(  # noqa: S603  # nosec B603 - validated revision/path Git argv
            [git, "-C", str(repository), "show", f"{revision}:{relative_path}"],
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise ProtocolError(f"Could not read pinned trusted registry: {relative_path}") from error
    try:
        payload = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise ProtocolError(
            f"Pinned trusted registry is not valid YAML: {relative_path}"
        ) from error
    if not isinstance(payload, dict):
        raise ProtocolError(f"Pinned trusted registry must contain a YAML mapping: {relative_path}")
    return cast(dict[str, Any], payload)


def _validated_known_targets(known_targets: Set[TargetKey]) -> set[TargetKey]:
    result: set[TargetKey] = set()
    for target in known_targets:
        if (
            not isinstance(target, tuple)
            or len(target) != 2
            or target[0] not in {"representation", "obligation"}
            or not isinstance(target[1], str)
            or not target[1]
        ):
            raise ProtocolError("Trusted known-target set contains a malformed typed identity")
        result.add(target)
    if not result:
        raise ProtocolError("Trusted known-target set must be non-empty")
    return result


def load_private_ground_truth(path: str) -> dict[str, Any]:
    """Load a private YAML oracle for the scorer process only."""
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProtocolError("Private ground truth must contain a YAML mapping")
    result = cast(dict[str, Any], payload)
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "ground_truth.schema.json"
    schema = cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = list(validator.iter_errors(result))
    if errors:
        raise ProtocolError("Private ground truth does not match its frozen schema")
    return result


def record_private_ground_truth_hash(
    ground_truth_path: Path,
    scorer_directory: Path,
    recorded_at_utc: str,
) -> dict[str, Any]:
    """Write a scorer-only hash record without copying any oracle content."""
    if ground_truth_path.name != "ground_truth.yaml" or not ground_truth_path.is_file():
        raise ProtocolError("Ground-truth hash input must be the frozen ground_truth.yaml file")
    output = scorer_directory / "ground_truth_hash.json"
    if output.exists():
        raise ProtocolError("Ground-truth hash record is write-once")
    record = {
        "schema_version": 1,
        "artifact_name": "ground_truth.yaml",
        "sha256": sha256_file(ground_truth_path),
        "recorded_at_utc": recorded_at_utc,
        "scope": "scorer_only",
    }
    validate_payload("ground_truth_hash.schema.json", record)
    scorer_directory.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    except FileExistsError as error:
        raise ProtocolError("Ground-truth hash record is write-once") from error
    with os.fdopen(descriptor, "wb") as file_handle:
        file_handle.write(pretty_json_bytes(record))
        file_handle.flush()
        os.fsync(file_handle.fileno())
    output.chmod(0o444)
    return record


def _oracle_universe(
    ground_truth: Mapping[str, Any],
) -> tuple[list[TargetKey], dict[TargetKey, str]]:
    classification = ground_truth.get("classification_universe")
    expected_operations = ground_truth.get("expected_operations")
    if not isinstance(classification, Mapping) or not isinstance(expected_operations, Mapping):
        raise ProtocolError("Ground truth lacks the classification universe or total operation map")
    representations = classification.get("existing_representations")
    obligations = classification.get("new_obligations")
    if not isinstance(representations, list) or not isinstance(obligations, list):
        raise ProtocolError("Ground-truth target lists are malformed")
    universe: list[TargetKey] = [
        *(("representation", str(item)) for item in representations),
        *(("obligation", str(item)) for item in obligations),
    ]
    identifiers = [target_id for _, target_id in universe]
    if not universe or len(universe) != len(set(identifiers)):
        raise ProtocolError("Ground-truth target IDs must form a non-empty unique universe")
    if set(expected_operations) != set(identifiers):
        raise ProtocolError(
            "Ground-truth operation map must cover exactly the complete target universe"
        )
    expected: dict[TargetKey, str] = {}
    for target_type, target_id in universe:
        operation = str(expected_operations[target_id])
        if operation not in EMITTED_OPERATIONS:
            raise ProtocolError(f"Ground-truth operation is unsupported for target {target_id}")
        if target_type == "obligation" and operation != "add":
            raise ProtocolError(f"Obligation target {target_id} must have the add operation")
        if target_type == "representation" and operation == "add":
            raise ProtocolError(f"Representation target {target_id} cannot have the add operation")
        expected[(target_type, target_id)] = operation
    return universe, expected


def _target_key(item: Mapping[str, Any]) -> TargetKey:
    target_type = str(item["target_type"])
    if target_type not in {"representation", "obligation"}:
        raise ProtocolError(f"Unsupported target type: {target_type}")
    return cast(TargetType, target_type), str(item["target_id"])


def _impact_metrics(
    tp: int,
    fp_total: int,
    fn: int,
    oracle_positive_count: int,
    predicted_positive_count: int,
) -> tuple[float | None, float | None, float | None, bool | None]:
    if oracle_positive_count == 0 and predicted_positive_count == 0:
        return None, None, None, True
    precision = tp / (tp + fp_total) if tp + fp_total else 0.0
    recall = tp / (tp + fn) if tp + fn else None
    f1_denominator = 2 * tp + fp_total + fn
    f1 = 2 * tp / f1_denominator if f1_denominator else None
    return precision, recall, f1, False if oracle_positive_count == 0 else None


def _coverage_assessment(
    required: list[str],
    architecture_source_sha: str,
    representations: Sequence[dict[str, Any]],
    verdicts: Mapping[str, dict[str, Any]],
    obligation_verdicts: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    ids = [str(item["id"]) for item in representations]
    if len(ids) != len(set(ids)):
        raise ProtocolError("Coverage configuration contains duplicate representation IDs")
    representation_by_id = {str(item["id"]): item for item in representations}
    unexpected_verdicts = set(verdicts) - set(ids)
    if unexpected_verdicts:
        raise ProtocolError(
            f"Representation verdicts reference unknown candidates: {sorted(unexpected_verdicts)}"
        )
    for representation_verdict in verdicts.values():
        validate_payload("semantic_verdict.schema.json", representation_verdict)

    pair_verdicts: dict[tuple[str, str], dict[str, Any]] = {}
    for pair_verdict in obligation_verdicts:
        validate_payload("obligation_verdict.schema.json", pair_verdict)
        pair_key = (pair_verdict["representation_id"], pair_verdict["obligation_id"])
        representation = representation_by_id.get(pair_key[0])
        if representation is None:
            raise ProtocolError("Obligation verdict references an unknown representation")
        covers = representation.get("covers", [])
        if not isinstance(covers, list) or pair_key[1] not in covers:
            raise ProtocolError("Obligation verdict pair is not declared by its representation")
        previous = pair_verdicts.get(pair_key)
        if previous is not None and previous != pair_verdict:
            raise ProtocolError(
                "Conflicting duplicate verdicts for one representation-obligation pair"
            )
        pair_verdicts[pair_key] = pair_verdict

    covered: list[str] = []
    uncovered: list[str] = []
    invalid: set[str] = set()
    stale: set[str] = set()
    violations: Counter[str] = Counter()
    assessed_count = 0
    execution_statuses: dict[str, str] = {}
    for representation in representations:
        representation_id = str(representation["id"])
        if not representation.get("active", False):
            continue
        assessed_count += 1
        verdict = verdicts.get(representation_id)
        if verdict is None:
            execution_statuses[representation_id] = "MISSING_EVIDENCE"
            invalid.add(representation_id)
            violations["MISSING_EVIDENCE"] += 1
            continue
        status = str(verdict.get("status", "MISSING_EVIDENCE"))
        if verdict.get("architecture_source_sha") != architecture_source_sha:
            status = "STALE_ARCHITECTURE_SCOPE"
        if verdict.get("representation_id") != representation_id:
            status = "PROTOCOL_VIOLATION"
        if status == "VALID_APPLICABLE" and (
            verdict.get("active") is not True
            or verdict.get("mapping_resolved") is not True
            or verdict.get("stage_applicable") is not True
            or verdict.get("semantic_compatible") is not True
            or verdict.get("executable_nonvacuous") is not True
            or verdict.get("evidence_contract_satisfied") is not True
            or not verdict.get("evidence_refs")
        ):
            status = "PROTOCOL_VIOLATION"
        if status != "VALID_APPLICABLE":
            invalid.add(representation_id)
            violations[status] += 1
        if status == "STALE_ARCHITECTURE_SCOPE":
            stale.add(representation_id)
        execution_statuses[representation_id] = status
        for reason in verdict.get("reason_codes", []):
            if reason:
                violations[str(reason)] += 1

    pair_assessments: list[dict[str, Any]] = []
    valid_cover_pairs: list[dict[str, Any]] = []
    valid_obligations: set[str] = set()
    for obligation in required:
        for representation in representations:
            representation_id = str(representation["id"])
            if not representation.get("active", False):
                continue
            covers = representation.get("covers", [])
            if not isinstance(covers, list):
                raise ProtocolError(f"Representation {representation_id} has malformed covers")
            if not all(isinstance(item, str) and item for item in covers):
                raise ProtocolError(f"Representation {representation_id} has malformed covers")
            if obligation not in covers:
                continue

            execution_status = execution_statuses.get(representation_id, "MISSING_EVIDENCE")
            selected_pair_verdict = pair_verdicts.get((representation_id, obligation))
            pair_status: str
            reason_codes: list[str]
            evidence_refs: list[str]
            if execution_status != "VALID_APPLICABLE":
                pair_status = execution_status
                reason_codes = ["REPRESENTATION_EXECUTION_INVALID"]
                if selected_pair_verdict is not None:
                    reason_codes.extend(selected_pair_verdict["reason_codes"])
            elif selected_pair_verdict is None:
                pair_status = "MISSING_EVIDENCE"
                reason_codes = ["OBLIGATION_VERDICT_MISSING"]
            elif selected_pair_verdict["architecture_source_sha"] != architecture_source_sha:
                pair_status = "STALE_ARCHITECTURE_SCOPE"
                reason_codes = ["ARCHITECTURE_SOURCE_MISMATCH"]
                reason_codes.extend(selected_pair_verdict["reason_codes"])
            else:
                pair_status = str(selected_pair_verdict["status"])
                reason_codes = list(selected_pair_verdict["reason_codes"])
            evidence_refs = (
                list(selected_pair_verdict["evidence_refs"]) if selected_pair_verdict else []
            )
            pair_assessment = {
                "representation_id": representation_id,
                "obligation_id": obligation,
                "architecture_source_sha": (
                    selected_pair_verdict["architecture_source_sha"]
                    if selected_pair_verdict
                    else architecture_source_sha
                ),
                "status": pair_status,
                "reason_codes": sorted(set(reason_codes)),
                "evidence_refs": evidence_refs,
            }
            pair_assessments.append(pair_assessment)
            representation_verdict = verdicts.get(representation_id, {})
            if selected_pair_verdict is not None and valid_cover(
                representation_verdict,
                selected_pair_verdict,
                representation,
                obligation,
                architecture_source_sha,
            ):
                valid_obligations.add(obligation)
                valid_cover_pairs.append(
                    {
                        "representation_id": representation_id,
                        "obligation_id": obligation,
                        "architecture_source_sha": architecture_source_sha,
                        "evidence_refs": evidence_refs,
                    }
                )
        if obligation in valid_obligations:
            covered.append(obligation)
        else:
            uncovered.append(obligation)

    coverage = len(covered) / len(required)
    result = {
        "schema_version": 2,
        "architecture_source_sha": architecture_source_sha,
        "required_obligations": required,
        "denominator": len(required),
        "covered_count": len(covered),
        "coverage": coverage,
        "covered_obligations": covered,
        "uncovered_obligations": uncovered,
        "stale_representations": sorted(stale),
        "invalid_representations": sorted(invalid),
        "violation_counts": dict(sorted(violations.items())),
        "violation_denominator": assessed_count,
        "violation_rate": len(invalid) / assessed_count if assessed_count else 0.0,
        "pair_assessments": pair_assessments,
        "valid_cover_pairs": valid_cover_pairs,
    }
    validate_payload("coverage_assessment.schema.json", result)
    return result


def _diagnostic(code: str, target: TargetKey, operation: str) -> dict[str, str]:
    return {
        "code": code,
        "target_type": target[0],
        "target_id": target[1],
        "operation": operation,
    }


def _extra_decision(target: TargetKey, operation: str, known: set[TargetKey]) -> dict[str, Any]:
    return {
        "target_type": target[0],
        "target_id": target[1],
        "operation": operation,
        "known_target": target in known,
    }


def _unique_decisions(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in decisions:
        key = (item["target_type"], item["target_id"], item["operation"])
        unique[key] = item
    return [unique[key] for key in sorted(unique)]


def _unique_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in diagnostics:
        key = (item["code"], item["target_type"], item["target_id"], item["operation"])
        unique[key] = item
    return [unique[key] for key in sorted(unique)]


__all__ = [
    "TargetKey",
    "TargetType",
    "build_scored_result",
    "load_trusted_known_targets",
    "load_private_ground_truth",
    "record_private_ground_truth_hash",
    "score_rq1",
    "score_rq2",
    "score_sealed_prediction",
]
