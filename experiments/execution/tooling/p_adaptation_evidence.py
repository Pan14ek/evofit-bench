"""Versioned, signed evidence sidecars for SPEC 03 method-side inputs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal, Protocol, cast

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes


class AdaptationEvidenceVerifier(Protocol):
    """Externally configured trust anchor for method-side evidence signatures."""

    @property
    def trust_scope(self) -> Literal["PRODUCTION", "TEST_ONLY"]: ...

    def verify(self, verifier_id: str, content_sha256: str, signature: str) -> bool | None: ...


@dataclass(frozen=True)
class AdaptationEvidenceVerifierRegistry:
    """Verifier identities configured at the verified-input trust boundary."""

    verifiers: Mapping[str, AdaptationEvidenceVerifier]

    def __post_init__(self) -> None:
        configured = dict(self.verifiers)
        if any(
            not isinstance(verifier_id, str)
            or not verifier_id
            or getattr(verifier, "trust_scope", None) not in {"PRODUCTION", "TEST_ONLY"}
            or not callable(getattr(verifier, "verify", None))
            for verifier_id, verifier in configured.items()
        ):
            raise ContractValidationError("P03_EVIDENCE_VERIFIER_REGISTRY_INVALID")
        object.__setattr__(self, "verifiers", MappingProxyType(configured))

    def resolve(self, verifier_id: str) -> AdaptationEvidenceVerifier | None:
        """Resolve only an explicitly configured verifier identity."""
        verifier = self.verifiers.get(verifier_id)
        if verifier is None or verifier_id not in self.verifiers:
            return None
        return verifier


@dataclass(frozen=True)
class VerifiedAdaptationEvidence:
    """Immutable projection of one verified sidecar's exact bound evidence."""

    trust_scope: Literal["PRODUCTION", "TEST_ONLY"]
    verifier_id: str
    sidecar_sha256: str
    source_bindings: tuple[tuple[str, str], ...]
    payload: Mapping[str, Any]
    schema_version: int = 1


def verify_adaptation_evidence(
    sidecar: Mapping[str, Any],
    *,
    expected_bindings: Mapping[str, Any],
    expected_source_digests: Mapping[str, str],
    verifier_registry: AdaptationEvidenceVerifierRegistry | None,
    allow_test_only: bool,
    expected_trust_scope: Literal["PRODUCTION", "TEST_ONLY"],
) -> VerifiedAdaptationEvidence | None:
    """Verify schema, content digest, exact input context, sources and signature.

    Missing verifier authority returns ``None`` so callers can produce HOLD.
    A verifier explicitly rejecting a signed sidecar is an invalid input.
    """
    if verifier_registry is None:
        return None
    try:
        snapshot_bytes = canonical_json_bytes(dict(sidecar))
        snapshot = json.loads(snapshot_bytes)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ContractValidationError("P03_EVIDENCE_CONTEXT_NOT_JSON") from error
    if not isinstance(snapshot, dict):
        raise ContractValidationError("P03_EVIDENCE_CONTEXT_INVALID")
    schema_version_value = snapshot.get("schema_version")
    if type(schema_version_value) is not int:
        raise ContractValidationError("P03_EVIDENCE_SCHEMA_VERSION_UNSUPPORTED")
    schema_version = schema_version_value
    schema_name = {
        1: "p_adaptation_evidence_v1.schema.json",
        2: "p_adaptation_evidence_v2.schema.json",
    }.get(schema_version)
    if schema_name is None:
        raise ContractValidationError("P03_EVIDENCE_SCHEMA_VERSION_UNSUPPORTED")
    validate_payload(schema_name, snapshot)
    verifier_id = snapshot.get("verifier_id")
    if not isinstance(verifier_id, str):
        raise ContractValidationError("P03_EVIDENCE_VERIFIER_ID_INVALID")
    verifier = verifier_registry.resolve(verifier_id)
    if verifier is None:
        return None
    expected_scope = verifier.trust_scope
    if expected_scope != expected_trust_scope:
        return None
    if expected_scope == "TEST_ONLY" and not allow_test_only:
        return None
    for field, expected in expected_bindings.items():
        if snapshot.get(field) != expected:
            raise ContractValidationError("P03_EVIDENCE_CONTEXT_BINDING_MISMATCH:" + field)
    raw_sources = snapshot.get("source_bindings")
    if not isinstance(raw_sources, list):
        raise ContractValidationError("P03_EVIDENCE_SOURCE_BINDINGS_INVALID")
    source_bindings: list[tuple[str, str]] = []
    for item in raw_sources:
        if not isinstance(item, Mapping):
            raise ContractValidationError("P03_EVIDENCE_SOURCE_BINDINGS_INVALID")
        source_id, digest = item.get("source_id"), item.get("sha256")
        if not isinstance(source_id, str) or not isinstance(digest, str):
            raise ContractValidationError("P03_EVIDENCE_SOURCE_BINDINGS_INVALID")
        if expected_source_digests.get(source_id) != digest:
            raise ContractValidationError("P03_EVIDENCE_SOURCE_BINDING_MISMATCH")
        source_bindings.append((source_id, digest))
    if not source_bindings or tuple(sorted(set(source_bindings))) != tuple(source_bindings):
        raise ContractValidationError("P03_EVIDENCE_SOURCE_BINDINGS_INVALID")

    unsigned = {
        key: value for key, value in snapshot.items() if key not in {"signature", "sidecar_sha256"}
    }
    content_sha256 = sha256_bytes(canonical_json_bytes(unsigned))
    if snapshot.get("sidecar_sha256") != content_sha256:
        raise ContractValidationError("P03_EVIDENCE_SIDECAR_DIGEST_MISMATCH")
    verifier_result = verifier.verify(verifier_id, content_sha256, str(snapshot.get("signature")))
    if verifier_result is None:
        return None
    if verifier_result is not True:
        raise ContractValidationError("P03_EVIDENCE_SIDECAR_SIGNATURE_INVALID")
    payload = snapshot.get("payload")
    if not isinstance(payload, Mapping):
        raise ContractValidationError("P03_EVIDENCE_SIDECAR_PAYLOAD_INVALID")
    return VerifiedAdaptationEvidence(
        trust_scope=expected_scope,
        verifier_id=verifier_id,
        sidecar_sha256=content_sha256,
        source_bindings=tuple(source_bindings),
        payload=_freeze(payload),
        schema_version=schema_version,
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                str(key): _freeze(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        )
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def thaw_verified_payload(evidence: VerifiedAdaptationEvidence) -> dict[str, Any]:
    """Return a detached copy for validators and downstream pure functions."""
    return cast(dict[str, Any], _thaw(evidence.payload))


__all__ = [
    "AdaptationEvidenceVerifier",
    "AdaptationEvidenceVerifierRegistry",
    "VerifiedAdaptationEvidence",
    "thaw_verified_payload",
    "verify_adaptation_evidence",
]
