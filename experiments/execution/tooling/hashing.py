"""Exact-byte and deterministic JSON hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(content: bytes) -> str:
    """Return the SHA-256 hex digest for exact bytes."""
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest for a file without changing it."""
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize JSON with deterministic key order and compact separators."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def pretty_json_bytes(payload: Any) -> bytes:
    """Serialize human-readable JSON with stable ordering and a final newline."""
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def bundle_sha256(entries: list[dict[str, Any]]) -> str:
    """Hash a sorted bundle manifest without self-referential manifest fields."""
    stable_entries = sorted(entries, key=lambda item: str(item["path"]))
    return sha256_bytes(canonical_json_bytes(stable_entries))
