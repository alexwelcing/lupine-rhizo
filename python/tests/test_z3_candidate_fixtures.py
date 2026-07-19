"""Tests for tools/build_z3_candidate_fixtures.py.

Covers: fixture schema acceptance by the runner's fixture contract, content
addressing (filename-embedded SHA-256 matches file bytes), rebuild
determinism, full 32-candidate coverage of the locked panel, split
preservation, and end-to-end acceptance through ``run_row`` with a mock
calculator.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import pytest
from ase.calculators.calculator import Calculator, all_changes

ROOT = Path(__file__).resolve().parents[2]
_TOOLS = ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import build_z3_candidate_fixtures as gen  # noqa: E402
from lupine_distill.fixture_contract import run_row, validate_manifest  # noqa: E402

pytestmark = pytest.mark.unit

PANEL_PATH = gen.DEFAULT_PANEL
CAMPAIGN_MANIFEST = ROOT / "campaigns" / "v1" / "z3.campaign-manifest.v1.json"
NAME_PATTERN = re.compile(r"^(?P<candidate_id>.+)\.sha256-(?P<digest>[0-9a-f]{64})\.json$")


class PerAtomEnergyCalculator(Calculator):
    """Deterministic mock: energy is a fixed constant per atom."""

    implemented_properties = ["energy"]

    def __init__(self, energy_per_atom: float = 0.5):
        super().__init__()
        self.energy_per_atom = energy_per_atom

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        self.results = {"energy": self.energy_per_atom * len(atoms)}


@pytest.fixture(scope="module")
def panel() -> dict:
    return json.loads(PANEL_PATH.read_bytes())


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory, panel: dict) -> dict:
    output_dir = tmp_path_factory.mktemp("z3-fixtures")
    entries, manifest = gen.build_all(
        panel,
        gen.sha256_hex(PANEL_PATH.read_bytes()),
        PANEL_PATH,
    )
    manifest_path = gen.write_outputs(entries, manifest, output_dir)
    return {
        "output_dir": output_dir,
        "entries": entries,
        "manifest": manifest,
        "manifest_path": manifest_path,
    }


def _load_fixture(built: dict, filename: str) -> dict:
    return json.loads((built["output_dir"] / filename).read_bytes())


def test_all_32_candidates_covered(built: dict, panel: dict) -> None:
    panel_ids = [candidate["candidate_id"] for candidate in panel["candidates"]]
    assert len(panel_ids) == 32
    assert sorted(built["manifest"]["candidates"]) == sorted(panel_ids)
    assert built["manifest"]["candidate_count"] == 32
    assert sorted(candidate_id for candidate_id, _f, _d, _c in built["entries"]) == sorted(panel_ids)


def test_panel_binds_to_campaign_manifest() -> None:
    campaign = json.loads(CAMPAIGN_MANIFEST.read_text(encoding="utf-8"))
    recorded = campaign["execution"]["candidate_panel"]["sha256"]
    digest = hashlib.sha256(PANEL_PATH.read_bytes()).hexdigest()
    assert recorded == f"sha256:{digest}"


def test_hash_name_integrity(built: dict) -> None:
    for candidate_id, filename, digest, content in built["entries"]:
        match = NAME_PATTERN.fullmatch(filename)
        assert match is not None, filename
        assert match.group("candidate_id") == candidate_id
        assert match.group("digest") == digest
        assert hashlib.sha256(content).hexdigest() == digest
        on_disk = (built["output_dir"] / filename).read_bytes()
        assert on_disk == content
        assert hashlib.sha256(on_disk).hexdigest() == digest
        record = built["manifest"]["candidates"][candidate_id]
        assert record["fixture"] == filename
        assert record["sha256"] == digest


def test_manifest_is_machine_checkable(built: dict, panel: dict) -> None:
    manifest = built["manifest"]
    assert manifest["schema"] == gen.MANIFEST_SCHEMA
    assert manifest["panel"]["sha256"] == hashlib.sha256(PANEL_PATH.read_bytes()).hexdigest()
    splits = {candidate["candidate_id"]: candidate["split"] for candidate in panel["candidates"]}
    for candidate_id, record in manifest["candidates"].items():
        assert record["split"] == splits[candidate_id]


def test_rebuild_is_byte_identical(tmp_path: Path, panel: dict, built: dict) -> None:
    entries, manifest = gen.build_all(
        panel,
        gen.sha256_hex(PANEL_PATH.read_bytes()),
        PANEL_PATH,
    )
    assert [entry[:3] for entry in entries] == [entry[:3] for entry in built["entries"]]
    assert [entry[3] for entry in entries] == [entry[3] for entry in built["entries"]]
    assert gen.fixture_bytes(manifest) == gen.fixture_bytes(built["manifest"])
    rebuilt_dir = tmp_path / "rebuilt"
    gen.write_outputs(entries, manifest, rebuilt_dir)
    original_files = sorted(path.name for path in built["output_dir"].iterdir())
    assert sorted(path.name for path in rebuilt_dir.iterdir()) == original_files
    for name in original_files:
        assert (rebuilt_dir / name).read_bytes() == (built["output_dir"] / name).read_bytes()


def test_fixtures_pass_schema_validation(built: dict, panel: dict) -> None:
    splits = {candidate["candidate_id"]: candidate["split"] for candidate in panel["candidates"]}
    for candidate_id, filename, _digest, _content in built["entries"]:
        fixture = _load_fixture(built, filename)
        assert fixture["schema"] == "lupine.mlip.fixture_manifest.v2"
        assert fixture["metadata"]["split"] == splits[candidate_id]
        result = validate_manifest(fixture)
        assert result["release_ready"] is True, result["blockers"]
        assert result["blockers"] == []
        assert result["row_counts"]["adsorption_energy"] == 1


def test_run_row_accepts_every_fixture(built: dict) -> None:
    for candidate_id, filename, _digest, _content in built["entries"]:
        fixture = _load_fixture(built, filename)
        result = run_row("adsorption_energy", fixture, PerAtomEnergyCalculator())
        assert result["n_structures"] == 1
        prediction = result["predictions"][0]
        assert prediction["candidate_id"] == candidate_id
        assert prediction["status"] == "completed"
        assert math.isfinite(prediction["adsorption_energy_ev"])
        assert math.isfinite(prediction["signed_error_ev"])
        assert result["metrics"]["successful_candidates"] == 1
        assert result["metrics"]["failed_candidates"] == 0
