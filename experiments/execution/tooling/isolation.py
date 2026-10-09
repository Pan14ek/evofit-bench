"""Run method commands inside a constrained Docker container."""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - fixed Docker executable and validated argv, never a shell
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from experiments.execution.tooling.errors import IsolationError
from experiments.execution.tooling.hashing import sha256_bytes
from experiments.execution.tooling.inputs import MethodId, verify_method_bundle

IMAGE_DIGEST_PATTERN = re.compile(r"^(?:[A-Za-z0-9./:_-]+@)?sha256:[a-f0-9]{64}$")
MAX_TIMEOUT_SECONDS = 3600
MAX_MEMORY = "2g"
MAX_CPUS = "2.0"
MAX_PIDS = 128


@dataclass(frozen=True)
class ContainerExecution:
    """Host-captured result from one isolated container invocation."""

    exit_code: int | None
    timed_out: bool
    started_at_utc: str
    ended_at_utc: str
    duration_ms: float
    stdout_sha256: str
    stderr_sha256: str
    stdout_path: Path
    stderr_path: Path


def build_docker_command(
    method_input_directory: Path,
    output_directory: Path,
    image_digest: str,
    command: list[str],
    method_id: MethodId,
    timeout_seconds: int,
) -> list[str]:
    """Build a restrictive Docker argv without shell interpolation."""
    if IMAGE_DIGEST_PATTERN.fullmatch(image_digest) is None:
        raise IsolationError("Method runtime image must be pinned by a full SHA-256 digest")
    if not command or any("\x00" in argument for argument in command):
        raise IsolationError("Method command must be a non-empty argument list without NUL bytes")
    if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise IsolationError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")
    method_bundle = method_input_directory.resolve(strict=True)
    output_root = output_directory.resolve(strict=True)
    if not method_bundle.is_dir() or not output_root.is_dir():
        raise IsolationError("Method input and output paths must both be directories")
    if (
        method_bundle == output_root
        or method_bundle in output_root.parents
        or output_root in method_bundle.parents
    ):
        raise IsolationError("Method input and output directories must not contain one another")
    if "," in str(method_bundle) or "," in str(output_root):
        raise IsolationError("Docker bind-mount paths cannot contain commas")
    verify_method_bundle(method_bundle, expected_method_id=method_id)
    if any(output_root.iterdir()):
        raise IsolationError("Method output directory must be empty before invocation")

    uid = os.getuid() if hasattr(os, "getuid") else 65534
    gid = os.getgid() if hasattr(os, "getgid") else 65534
    command_line = [
        _docker_executable(),
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--ipc=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        f"--pids-limit={MAX_PIDS}",
        f"--memory={MAX_MEMORY}",
        f"--cpus={MAX_CPUS}",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m",
        f"--user={uid}:{gid}",
        "--workdir=/input",
        "--env=HOME=/tmp",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        "--mount",
        f"type=bind,source={method_bundle},target=/input,readonly",
        "--mount",
        f"type=bind,source={output_root},target=/output",
        image_digest,
        *command,
    ]
    return command_line


def run_isolated_method(
    method_input_directory: Path,
    output_directory: Path,
    image_digest: str,
    command: list[str],
    method_id: MethodId,
    timeout_seconds: int = 600,
) -> ContainerExecution:
    """Execute one method command and preserve its exact stdout/stderr bytes."""
    arguments = build_docker_command(
        method_input_directory,
        output_directory,
        image_digest,
        command,
        method_id,
        timeout_seconds,
    )
    started = datetime.now(UTC)
    monotonic_start = time.monotonic()
    timed_out = False
    exit_code: int | None
    stdout = b""
    stderr = b""
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603 - fixed Docker argv, no shell
            arguments,
            check=False,
            capture_output=True,
            timeout=timeout_seconds,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        exit_code = None
        stdout = _bytes_or_empty(error.stdout)
        stderr = _bytes_or_empty(error.stderr)
    except OSError as error:
        raise IsolationError(
            "Docker runtime is unavailable; refusing a host-process fallback"
        ) from error

    ended = datetime.now(UTC)
    duration_ms = (time.monotonic() - monotonic_start) * 1000
    stdout_path = output_directory / "__runner_stdout.bin"
    stderr_path = output_directory / "__runner_stderr.bin"
    _write_log_exclusively(stdout_path, stdout)
    _write_log_exclusively(stderr_path, stderr)
    return ContainerExecution(
        exit_code=exit_code,
        timed_out=timed_out,
        started_at_utc=_iso_utc(started),
        ended_at_utc=_iso_utc(ended),
        duration_ms=duration_ms,
        stdout_sha256=sha256_bytes(stdout),
        stderr_sha256=sha256_bytes(stderr),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )


def _write_log_exclusively(path: Path, content: bytes) -> None:
    try:
        with path.open("xb") as file_handle:
            file_handle.write(content)
    except FileExistsError as error:
        raise IsolationError(
            f"Container attempted to occupy a reserved runner log path: {path.name}"
        ) from error


def _docker_executable() -> str:
    return shutil.which("docker") or "docker"


def _bytes_or_empty(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    return value.encode("utf-8") if isinstance(value, str) else value


def _iso_utc(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


__all__ = ["ContainerExecution", "build_docker_command", "run_isolated_method"]
