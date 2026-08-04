#!/usr/bin/env python3
"""Build-time proof that the Z2 image contains the reviewed scientific contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import rfc8785
from z2_soc_tc import derive_spin_observables

REQUIRED_MANIFEST_CONTENT_HASH = (
    "sha256:73f7b9bf8e03d76fc46936911ddd95da7479289fabfd0375cd9b3a66132c7bbc"
)
REQUIRED_PANEL_SHA256 = (
    "sha256:7d37fd513d3e77c0fced043283bbb8b9a8b98cd241677de00665fe5095c704d8"
)


def main() -> int:
    root = Path(__file__).resolve().parent
    if not (root / "campaigns").exists():
        root = Path(__file__).resolve().parents[2]
    manifest_path = root / "campaigns" / "v1" / "z2.campaign-manifest.v1.json"
    panel_path = root / "data" / "candidates" / "z2_soc_tc_panel.lock.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload = {key: value for key, value in manifest.items() if key != "content_hash"}
    actual_manifest_hash = "sha256:" + hashlib.sha256(rfc8785.dumps(manifest_payload)).hexdigest()
    if manifest.get("content_hash") != REQUIRED_MANIFEST_CONTENT_HASH:
        raise SystemExit("packaged Z2 manifest does not declare the reviewed content hash")
    if actual_manifest_hash != REQUIRED_MANIFEST_CONTENT_HASH:
        raise SystemExit("packaged Z2 manifest content does not match the reviewed hash")

    actual_panel_hash = "sha256:" + hashlib.sha256(panel_path.read_bytes()).hexdigest()
    if actual_panel_hash != REQUIRED_PANEL_SHA256:
        raise SystemExit("packaged Z2 panel bytes do not match the reviewed hash")
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    if len(panel.get("materials", [])) != 7:
        raise SystemExit("packaged Z2 panel must contain exactly seven materials")

    # Independent constants distinguish reviewed Eq. (4) from the superseded
    # J=J_parallel, Delta=(J_perpendicular-J_parallel)/J_parallel mapping.
    factor = 4.0
    prediction = derive_spin_observables(
        {"spin": 1.0, "nearest_neighbors": 2, "lattice": "honeycomb"},
        {"parallel_energy_ev": 0.0, "perpendicular_energy_ev": 0.0},
        {
            "parallel_energy_ev": factor * 0.005,
            "perpendicular_energy_ev": factor * 0.0055,
        },
    )
    if abs(prediction["exchange_mev"] - 5.25) > 1e-12:
        raise SystemExit("packaged runner does not execute reviewed Eq. (4) exchange_mev")
    if abs(prediction["exchange_anisotropy"] - (0.5 / 10.5)) > 1e-12:
        raise SystemExit("packaged runner does not execute reviewed Eq. (4) exchange_anisotropy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
