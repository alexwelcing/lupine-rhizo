#!/usr/bin/env python3
import json
from pathlib import Path

from lupine_distill.fixture_contract import validate_manifest

paths = (
    Path("manifests/matpes-pbe-2025.2.manifest.json"),
    Path("manifests/omat24-validation-aimd-pbe-1000-nvt.manifest.json"),
)
results = {}
for path in paths:
    contract = validate_manifest(json.loads(path.read_text()))
    results[str(path)] = {
        "release_ready": contract["release_ready"],
        "blockers": contract["blockers"],
        "forces": contract["row_counts"]["forces"],
    }
print(json.dumps(results, indent=2, sort_keys=True))
if not all(item["release_ready"] for item in results.values()):
    raise SystemExit(1)
