"""Create a checksum-compatible packaging copy of the immutable PILOT-02 V6 archive."""

from __future__ import annotations

import argparse
import copy
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

_ARCHIVE_ROOT = "PILOT_02_RAW_EVIDENCE_CONTINUATION_V6"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_OLD_SUM_ROW = re.compile(r"^([0-9a-f]{64})  ([0-9]+)  (.+)$")
_STANDARD_SUM_ROW = re.compile(r"^([0-9a-f]{64})  (.+)$")
_DEFAULT_SOURCE = Path(__file__).with_name(f"{_ARCHIVE_ROOT}.zip")
_DEFAULT_OUTPUT = Path(__file__).with_name(f"{_ARCHIVE_ROOT}_PACKAGING_CORRECTED.zip")


@dataclass(frozen=True)
class InventoryEntry:
    """One historical V6 checksum row, including its recorded byte size."""

    sha256: str
    size: int
    archived_path: str
    corrected_path: str


def _safe_archive_path(path: str) -> None:
    """Reject absolute, traversal, backslash, and empty archive paths."""
    pure_path = PurePosixPath(path)
    if (
        not path
        or "\\" in path
        or pure_path.is_absolute()
        or any(part in {"", ".", ".."} for part in pure_path.parts)
    ):
        raise ValueError(f"unsafe archive path: {path!r}")


def _parse_old_inventory(payload: bytes, root: str) -> list[InventoryEntry]:
    entries: list[InventoryEntry] = []
    seen_paths: set[str] = set()
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ValueError("V6 SHA256SUMS is not UTF-8") from error
    if not lines:
        raise ValueError("V6 SHA256SUMS is empty")
    for line_number, line in enumerate(lines, start=1):
        match = _OLD_SUM_ROW.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid historical SHA256SUMS row {line_number}")
        digest, size_text, archived_path = match.groups()
        _safe_archive_path(archived_path)
        corrected_path = archived_path
        duplicated_root = f"{root}/"
        if corrected_path.startswith(duplicated_root):
            corrected_path = corrected_path[len(duplicated_root) :]
        _safe_archive_path(corrected_path)
        if corrected_path.startswith(duplicated_root):
            raise ValueError(f"archive path retains duplicate root: {archived_path!r}")
        if corrected_path in seen_paths:
            raise ValueError(f"duplicate corrected inventory path: {corrected_path!r}")
        seen_paths.add(corrected_path)
        entries.append(InventoryEntry(digest, int(size_text), archived_path, corrected_path))
    return entries


def _verify_original_sidecar(source: Path) -> None:
    sidecar = Path(f"{source}.sha256")
    try:
        fields = sidecar.read_text(encoding="utf-8").split()
    except OSError as error:
        raise ValueError(f"original V6 sidecar is unavailable: {sidecar}") from error
    if len(fields) < 2 or _DIGEST.fullmatch(fields[0]) is None:
        raise ValueError("original V6 SHA-256 sidecar is malformed")
    if hashlib.sha256(source.read_bytes()).hexdigest() != fields[0]:
        raise ValueError("original V6 archive does not match its preserved sidecar")


def _read_verified_source(
    source: Path, *, root_name: str = _ARCHIVE_ROOT, expected_duplicated_prefix_count: int = 26
) -> tuple[str, list[InventoryEntry], dict[str, bytes]]:
    _verify_original_sidecar(source)
    try:
        with ZipFile(source) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise ValueError(f"original V6 archive has a CRC error: {corrupt_member}")
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("original V6 archive contains duplicate member names")
            for name in names:
                _safe_archive_path(name.rstrip("/"))
            manifests = [name for name in names if name.endswith("/SHA256SUMS")]
            if len(manifests) != 1:
                raise ValueError("original V6 archive must contain one rooted SHA256SUMS")
            manifest_name = manifests[0]
            root = manifest_name.removesuffix("/SHA256SUMS")
            if root != root_name:
                raise ValueError(f"unexpected V6 archive root: {root!r}")
            entries = _parse_old_inventory(archive.read(manifest_name), root)
            duplicated_count = sum(e.archived_path != e.corrected_path for e in entries)
            if duplicated_count != expected_duplicated_prefix_count:
                raise ValueError(
                    f"expected {expected_duplicated_prefix_count} duplicated-root rows, "
                    f"found {duplicated_count}"
                )
            expected_names = {f"{root}/{entry.archived_path}" for entry in entries}
            expected_names.add(manifest_name)
            if set(names) != expected_names:
                raise ValueError("original archive has missing or unexpected members")
            artifact_bytes: dict[str, bytes] = {}
            for entry in entries:
                member_name = f"{root}/{entry.archived_path}"
                content = archive.read(member_name)
                if (
                    len(content) != entry.size
                    or archive.getinfo(member_name).file_size != entry.size
                ):
                    raise ValueError(f"V6 size mismatch for {entry.archived_path}")
                if hashlib.sha256(content).hexdigest() != entry.sha256:
                    raise ValueError(f"V6 digest mismatch for {entry.archived_path}")
                artifact_bytes[member_name] = content
            return root, entries, artifact_bytes
    except BadZipFile as error:
        raise ValueError("original V6 archive is not a valid ZIP") from error


def _verify_corrected_archive(
    path: Path, expected: dict[str, bytes], root_name: str = _ARCHIVE_ROOT
) -> dict[str, int | str]:
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("corrected archive has a ZIP CRC error")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValueError("corrected archive contains duplicate member names")
        for name in names:
            _safe_archive_path(name.rstrip("/"))
        root = f"{root_name}/"
        manifest_name = f"{root_name}/SHA256SUMS"
        if manifest_name not in names:
            raise ValueError("corrected archive is missing SHA256SUMS")
        if any(name.startswith(root + root_name + "/") for name in names):
            raise ValueError("corrected archive still contains a duplicated root")
        listed: dict[str, str] = {}
        for line_number, line in enumerate(archive.read(manifest_name).decode().splitlines(), 1):
            match = _STANDARD_SUM_ROW.fullmatch(line)
            if match is None:
                raise ValueError(f"SHA256SUMS is not sha256sum-compatible at line {line_number}")
            digest, relative_path = match.groups()
            _safe_archive_path(relative_path)
            if relative_path.startswith(root_name + "/") or relative_path in listed:
                raise ValueError(f"invalid or duplicate relative checksum path: {relative_path}")
            listed[relative_path] = digest
        expected_relative = {
            name.removeprefix(root): hashlib.sha256(content).hexdigest()
            for name, content in expected.items()
        }
        if listed != expected_relative:
            raise ValueError("corrected SHA256SUMS references do not match preserved files")
        if set(names) != {root + path for path in listed} | {manifest_name}:
            raise ValueError("corrected archive has missing or unexpected members")
        total_bytes = 0
        for relative_path, digest in listed.items():
            member_name = root + relative_path
            content = archive.read(member_name)
            if archive.getinfo(member_name).file_size != len(content):
                raise ValueError(f"ZIP size metadata mismatch for {relative_path}")
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f"SHA256SUMS digest mismatch for {relative_path}")
            if content != expected[member_name]:
                raise ValueError(f"experimental artifact bytes changed for {relative_path}")
            total_bytes += len(content)
        return {
            "artifact_count": len(listed),
            "total_artifact_bytes": total_bytes,
            "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }


def correct_archive(
    source: Path,
    output: Path,
    *,
    expected_duplicated_prefix_count: int = 26,
    replace_output: bool = False,
    root_name: str = _ARCHIVE_ROOT,
) -> dict[str, int | str]:
    """Normalize archive paths and checksum metadata; preserve all payload bytes."""
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("corrected output must not replace the historical V6 archive")
    if output.exists() and not replace_output:
        raise FileExistsError(f"refusing to replace existing output: {output}")
    root, entries, original_bytes = _read_verified_source(
        source,
        root_name=root_name,
        expected_duplicated_prefix_count=expected_duplicated_prefix_count,
    )
    changed_count = sum(e.archived_path != e.corrected_path for e in entries)
    if changed_count != expected_duplicated_prefix_count:
        raise ValueError(
            f"expected {expected_duplicated_prefix_count} duplicate roots, found {changed_count}"
        )
    corrected_names = {f"{root}/{entry.corrected_path}" for entry in entries}
    manifest_name = f"{root}/SHA256SUMS"
    if len(corrected_names) != len(entries) or manifest_name in corrected_names:
        raise ValueError("corrected archive would contain duplicate or manifest-colliding paths")
    corrected_manifest = "".join(
        f"{entry.sha256}  {entry.corrected_path}\n" for entry in entries
    ).encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
        with ZipFile(source) as original, ZipFile(temporary_name, "w") as corrected:
            corrected.comment = original.comment
            renames = {
                f"{root}/{entry.archived_path}": f"{root}/{entry.corrected_path}"
                for entry in entries
            }
            for info in original.infolist():
                destination = renames.get(info.filename, info.filename)
                output_info = copy.copy(info)
                output_info.filename = destination
                output_info.orig_filename = destination
                payload = (
                    corrected_manifest
                    if info.filename == manifest_name
                    else original.read(info.filename)
                )
                corrected.writestr(output_info, payload)
        os.replace(temporary_name, output)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

    corrected_bytes = {
        f"{root}/{entry.corrected_path}": original_bytes[f"{root}/{entry.archived_path}"]
        for entry in entries
    }
    result = _verify_corrected_archive(output, corrected_bytes, root_name)
    sidecar = Path(f"{output}.sha256")
    if sidecar.exists() and not replace_output:
        raise FileExistsError(f"refusing to replace existing sidecar: {sidecar}")
    repo_root = Path(__file__).resolve().parents[2]
    try:
        relative_output = output.relative_to(repo_root).as_posix()
    except ValueError:
        relative_output = output.name
    sidecar.write_text(f"{result['archive_sha256']}  {relative_output}\n", encoding="utf-8")
    result["changed_path_count"] = changed_count
    result["manifest_rows"] = len(entries)
    return result


def main() -> int:
    """Build one packaging-corrected copy without rerunning any experiment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=_DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--replace-output", action="store_true")
    args = parser.parse_args()
    result = correct_archive(args.source, args.output, replace_output=args.replace_output)
    for key, value in result.items():
        print(f"{key}={value}")
    print(f"sidecar={args.output}.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
