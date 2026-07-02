#!/usr/bin/env python3
"""Fetch machine-local classical potential files listed in the MLIP source packet.

Reads data/mlip_benchmarks/manifest_sources.json and downloads each inventory
entry's potential file into its expected path under the repo root. SHA-256 is
verified when a committed fixture pins a hash for the file; otherwise the
computed hash is printed so it can be pinned. Stdlib only, so it runs on a
bare HPC login node.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "mlip_benchmarks" / "manifest_sources.json"
PIN_FIXTURE_DIRS = (
    ROOT / "data" / "mlip_benchmarks" / "fixtures",
    ROOT / "gcp" / "mlip-cell-runner" / "fixtures",
)
# The NIST IPR github mirror is keyed by implementation id; the ctcms Download
# path is a best-effort fallback for entries whose page uses the same key.
MIRROR_URL_TEMPLATES = (
    "https://raw.githubusercontent.com/lmhale99/potentials-library/master/potential_LAMMPS/{implementation_id}/{filename}",
    "https://www.ctcms.nist.gov/potentials/Download/{implementation_id}/1/{filename}",
)
DOWNLOAD_TIMEOUT_S = 60


def load_manifest(path: pathlib.Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source manifest must be a JSON object")
    return payload


def inventory_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for section in ("local_ni_classical_inventory", "sources"):
        for entry in manifest.get(section, []):
            if isinstance(entry, dict) and entry.get("local_dir") and entry.get("potential_file"):
                entries.append(entry)
    return entries


def candidate_urls(entry: dict[str, Any]) -> list[str]:
    filename = pathlib.PurePosixPath(str(entry["potential_file"])).name
    urls = [url for url in entry.get("download_urls", []) if isinstance(url, str) and url]
    implementation_id = entry.get("nist_implementation_id")
    if isinstance(implementation_id, str) and implementation_id:
        urls.extend(
            template.format(implementation_id=implementation_id, filename=filename)
            for template in MIRROR_URL_TEMPLATES
        )
    return urls


def _collect_pins(node: Any, pins: dict[str, str]) -> None:
    if isinstance(node, dict):
        potential_file = node.get("potential_file")
        digest = node.get("potential_file_sha256")
        if isinstance(potential_file, str) and isinstance(digest, str):
            pins[potential_file] = digest.removeprefix("sha256:")
        for value in node.values():
            _collect_pins(value, pins)
    elif isinstance(node, list):
        for value in node:
            _collect_pins(value, pins)


def pinned_hashes(fixture_dirs: tuple[pathlib.Path, ...] = PIN_FIXTURE_DIRS) -> dict[str, str]:
    """Map posix-style potential_file paths to SHA-256 hashes pinned by committed fixtures."""
    pins: dict[str, str] = {}
    for directory in fixture_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            _collect_pins(payload, pins)
    return pins


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_url(url: str, timeout_s: float = DOWNLOAD_TIMEOUT_S) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return response.read()


def plan(
    manifest: dict[str, Any],
    root: pathlib.Path = ROOT,
    pins: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if pins is None:
        pins = pinned_hashes()
    items: list[dict[str, Any]] = []
    for entry in inventory_entries(manifest):
        relative = str(entry["potential_file"])
        items.append(
            {
                "baseline_id": entry.get("baseline_id") or entry.get("source_id") or relative,
                "relative_path": relative,
                "target": root / pathlib.PurePosixPath(relative),
                "urls": candidate_urls(entry),
                "sha256": pins.get(relative),
            }
        )
    return items


def fetch_item(item: dict[str, Any]) -> tuple[str, str]:
    """Return (status, detail). Statuses: present, fetched, unpinned, failed."""
    target: pathlib.Path = item["target"]
    pinned = item["sha256"]
    if target.exists():
        digest = file_sha256(target)
        if pinned is None:
            return "unpinned", f"present; computed sha256 {digest} (pin this)"
        if digest == pinned:
            return "present", "present; sha256 verified"
        return "failed", f"present but sha256 mismatch: got {digest}, pinned {pinned}"
    if not item["urls"]:
        return "failed", "missing and no download url could be derived"
    errors: list[str] = []
    for url in item["urls"]:
        try:
            payload = fetch_url(url)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            errors.append(f"{url}: {exc}")
            continue
        digest = hashlib.sha256(payload).hexdigest()
        if pinned is not None and digest != pinned:
            errors.append(f"{url}: sha256 mismatch: got {digest}, pinned {pinned}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        if pinned is None:
            return "unpinned", f"fetched from {url}; computed sha256 {digest} (pin this)"
        return "fetched", f"fetched from {url}; sha256 verified"
    return "failed", "all urls failed: " + " | ".join(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT, help="Repo root to fetch into")
    parser.add_argument("--only", action="append", default=None, metavar="BASELINE_ID")
    parser.add_argument("--list", action="store_true", dest="list_only", help="Print the fetch plan without downloading")
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    items = plan(manifest, root=args.root)
    if args.only:
        wanted = set(args.only)
        items = [item for item in items if item["baseline_id"] in wanted]
        missing_ids = wanted - {item["baseline_id"] for item in items}
        if missing_ids:
            print("unknown baseline ids: " + ", ".join(sorted(missing_ids)), file=sys.stderr)
            return 2

    if args.list_only:
        for item in items:
            state = "present" if item["target"].exists() else "missing"
            pin = item["sha256"] or "unpinned"
            print(f"{item['baseline_id']}: {state} {item['relative_path']} sha256={pin}")
            for url in item["urls"]:
                print(f"  url: {url}")
        return 0

    failures = 0
    for item in items:
        status, detail = fetch_item(item)
        print(f"{item['baseline_id']}: {status}: {item['relative_path']}: {detail}")
        if status == "failed":
            failures += 1
    if failures:
        print(f"{failures} of {len(items)} potential files failed; see messages above", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
