#!/usr/bin/env python3
"""Create the deterministic corrected A6 review bundle."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = (
    "report_a6_decide_corrected.md",
    "a6_decide_analysis.json",
    "a6_execution_ledger.json",
    "manifests/input-lock.json",
    "manifests/matpes-pbe-2025.2.manifest.json",
    "manifests/omat24-validation-aimd-pbe-1000-nvt.manifest.json",
    "build_a6_manifests.py",
    "analyze_a6_decide.py",
    "verify_a6_decide.py",
    "build_corrected_ledger.py",
    "render_corrected_report.py",
    "run_repository_validator.py",
    "inspect_mptrj_test.py",
    "build_corrected_bundle.py",
)
HASH_MANIFEST = "a6_decide_corrected_hashes.json"
ARCHIVE = "a6-decide-corrected-deliverables.tar.gz"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    hashes = {name: sha256_file(ROOT / name) for name in FILES}
    (ROOT / HASH_MANIFEST).write_text(json.dumps({
        "schema": "lupine.a6_decide.corrected_artifact_hashes.v1",
        "files": hashes,
    }, indent=2, sort_keys=True) + "\n")

    members = sorted((*FILES, HASH_MANIFEST))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name in members:
            data = (ROOT / name).read_bytes()
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    with (ROOT / ARCHIVE).open("wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
            compressed.write(buffer.getvalue())

    print(json.dumps({
        "archive": ARCHIVE,
        "archive_sha256": sha256_file(ROOT / ARCHIVE),
        "hash_manifest": HASH_MANIFEST,
        "hash_manifest_sha256": sha256_file(ROOT / HASH_MANIFEST),
        "member_count": len(members),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
