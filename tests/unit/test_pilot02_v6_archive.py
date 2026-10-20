"""Tests for byte-preserving PILOT-02 archive path correction."""

from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from experiments.pilots.correct_pilot02_v6_archive import _parse_old_inventory, correct_archive


def _write_legacy_archive(path: Path) -> dict[str, bytes]:
    root = "fixture"
    artifacts = {
        f"{root}/primary/ordinary.txt": b"ordinary evidence\n",
        f"{root}/{root}/source_files/pinned.py": b"pinned source bytes\n",
    }
    rows = []
    for archive_path, content in artifacts.items():
        relative_path = archive_path.removeprefix(f"{root}/")
        rows.append(f"{hashlib.sha256(content).hexdigest()}  {len(content)}  {relative_path}\n")
    with ZipFile(path, "w") as archive:
        for archive_path, content in artifacts.items():
            archive.writestr(archive_path, content)
        archive.writestr(f"{root}/SHA256SUMS", "".join(rows))
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(f"{path}.sha256").write_text(f"{source_sha}  {path.name}\n", encoding="utf-8")
    return artifacts


def test_correct_archive_normalizes_root_and_keeps_payload_bytes(tmp_path: Path) -> None:
    source = tmp_path / "fixture.zip"
    output = tmp_path / "fixture-corrected.zip"
    original_members = _write_legacy_archive(source)

    result = correct_archive(
        source,
        output,
        expected_duplicated_prefix_count=1,
        root_name="fixture",
    )

    with ZipFile(output) as archive:
        assert set(archive.namelist()) == {
            "fixture/primary/ordinary.txt",
            "fixture/source_files/pinned.py",
            "fixture/SHA256SUMS",
        }
        manifest = archive.read("fixture/SHA256SUMS").decode()
        for line in manifest.splitlines():
            digest, separator, relative_path = line.partition("  ")
            assert len(digest) == 64
            assert separator == "  "
            assert relative_path and not relative_path.startswith("fixture/")
        assert "fixture/source_files" not in manifest
        assert len(manifest.splitlines()) == 2
        assert (
            archive.read("fixture/primary/ordinary.txt")
            == original_members["fixture/primary/ordinary.txt"]
        )
        assert (
            archive.read("fixture/source_files/pinned.py")
            == original_members["fixture/fixture/source_files/pinned.py"]
        )
    assert result["artifact_count"] == 2
    assert result["changed_path_count"] == 1
    assert Path(f"{output}.sha256").exists()


def test_old_inventory_rejects_path_traversal() -> None:
    row = f"{'0' * 64}  1  ../outside.txt\n".encode()
    with pytest.raises(ValueError, match="unsafe archive path"):
        _parse_old_inventory(row, "fixture")
