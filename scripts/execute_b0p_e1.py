"""Execute and archive one evidence-sufficient B0/P E1 calibration run."""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from experiments.execution.tooling.b0p_e1_execution import (
    create_e1_archive,
    perform_e1_execution,
    verify_e1_execution,
)
from experiments.execution.tooling.hashing import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation-directory", type=Path, required=True)
    parser.add_argument("--p-method-input-directory", type=Path, required=True)
    parser.add_argument("--adaptation-evidence-sidecar", type=Path, required=True)
    parser.add_argument("--semantic-verification-directory", type=Path, required=True)
    parser.add_argument(
        "--reference", type=Path, default=ROOT / "experiments/pilots/DEV_B0P_E1_REFERENCE_V1.json"
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--uv", default="uv")
    args = parser.parse_args(argv)

    manifest: dict[str, Any] = perform_e1_execution(
        args.preparation_directory,
        method_p_input_directory=args.p_method_input_directory,
        adaptation_evidence_sidecar=args.adaptation_evidence_sidecar,
        semantic_verification_directory=args.semantic_verification_directory,
        reference_path=args.reference,
        run_id=args.run_id,
        repository=args.repository,
        docker_executable=args.docker,
        uv_executable=args.uv,
    )
    run_directory = args.repository / "experiments/results" / args.run_id
    archive, archive_sha256 = create_e1_archive(run_directory)
    archive_sidecar = archive.with_suffix(archive.suffix + ".sha256")
    if archive_sidecar.read_text(encoding="ascii") != f"{archive_sha256}  {archive.name}\n":
        raise RuntimeError("E1 archive checksum sidecar does not match")
    if sha256_file(archive) != archive_sha256:
        raise RuntimeError("E1 archive bytes differ from the sealed SHA-256")
    with tempfile.TemporaryDirectory(prefix="b0p-e1-readback-") as temporary:
        with zipfile.ZipFile(archive) as source:
            if source.testzip() is not None:
                raise RuntimeError("E1 ZIP integrity check failed")
            if any(
                Path(item.filename).is_absolute() or ".." in Path(item.filename).parts
                for item in source.infolist()
            ):
                raise RuntimeError("E1 ZIP contains an unsafe extraction path")
            source.extractall(temporary)
        extracted = Path(temporary) / args.run_id
        readback = verify_e1_execution(extracted, repository=args.repository)
    print(
        json.dumps(
            {
                "manifest": manifest,
                "archive_path": str(archive),
                "archive_sha256": archive_sha256,
                "archive_sidecar_path": str(archive_sidecar),
                "clean_extraction_readback": readback,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
