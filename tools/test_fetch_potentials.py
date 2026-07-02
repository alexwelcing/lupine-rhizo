from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import fetch_potentials

PAYLOAD = b"pair potential payload\n"
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()


def sample_manifest() -> dict:
    return {
        "schema": "lupine.mlip.benchmark_sources.v1",
        "sources": [
            {"source_id": "nist-ipr", "urls": ["https://www.ctcms.nist.gov/potentials/"]},
        ],
        "local_ni_classical_inventory": [
            {
                "baseline_id": "ni-mishin-1999-eam-alloy",
                "nist_implementation_id": "1999--Mishin-Y--Ni--LAMMPS--ipr1",
                "local_dir": "atlas-distill/lammps_runs/Ni_Mishin-1999",
                "potential_file": "atlas-distill/lammps_runs/Ni_Mishin-1999/Ni99.eam.alloy",
                "result_json": "atlas-distill/lammps_runs/Ni_Mishin-1999/result.json",
            },
            {
                "baseline_id": "ni-lee-2003-meam",
                "nist_implementation_id": "2003--Lee-B-J--Ni--LAMMPS--ipr1",
                "local_dir": "atlas-distill/lammps_runs/Ni_Lee-2003",
                "potential_file": "atlas-distill/lammps_runs/Ni_Lee-2003/library.meam",
                "result_json": None,
            },
        ],
    }


@pytest.mark.unit
def test_plan_resolves_manifest_paths_and_urls(tmp_path: Path) -> None:
    items = fetch_potentials.plan(sample_manifest(), root=tmp_path, pins={})

    assert [item["baseline_id"] for item in items] == [
        "ni-mishin-1999-eam-alloy",
        "ni-lee-2003-meam",
    ]
    mishin = items[0]
    assert mishin["target"] == tmp_path / "atlas-distill/lammps_runs/Ni_Mishin-1999/Ni99.eam.alloy"
    assert mishin["sha256"] is None
    assert any(
        url.endswith("potential_LAMMPS/1999--Mishin-Y--Ni--LAMMPS--ipr1/Ni99.eam.alloy")
        for url in mishin["urls"]
    )


@pytest.mark.unit
def test_pinned_hashes_collects_nested_fixture_values(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "fixture.json").write_text(
        json.dumps(
            {
                "reference_provenance": {
                    "eam_reference": {
                        "potential_file": "atlas-distill/lammps_runs/Ni_Mishin-1999/Ni99.eam.alloy",
                        "potential_file_sha256": f"sha256:{PAYLOAD_SHA256}",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    pins = fetch_potentials.pinned_hashes((fixture_dir,))

    assert pins == {
        "atlas-distill/lammps_runs/Ni_Mishin-1999/Ni99.eam.alloy": PAYLOAD_SHA256,
    }


@pytest.mark.unit
def test_fetch_item_downloads_and_verifies_pinned_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetched_urls: list[str] = []

    def fake_fetch(url: str, timeout_s: float = 1.0) -> bytes:
        fetched_urls.append(url)
        return PAYLOAD

    monkeypatch.setattr(fetch_potentials, "fetch_url", fake_fetch)
    items = fetch_potentials.plan(sample_manifest(), root=tmp_path, pins={})
    items[0]["sha256"] = PAYLOAD_SHA256

    status, detail = fetch_potentials.fetch_item(items[0])

    assert status == "fetched"
    assert "sha256 verified" in detail
    assert len(fetched_urls) == 1
    assert items[0]["target"].read_bytes() == PAYLOAD


@pytest.mark.unit
def test_fetch_item_rejects_hash_mismatch_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fetch_potentials, "fetch_url", lambda url, timeout_s=1.0: b"wrong bytes")
    items = fetch_potentials.plan(sample_manifest(), root=tmp_path, pins={})
    items[0]["sha256"] = PAYLOAD_SHA256

    status, detail = fetch_potentials.fetch_item(items[0])

    assert status == "failed"
    assert "sha256 mismatch" in detail
    assert not items[0]["target"].exists()


@pytest.mark.unit
def test_fetch_item_skips_present_verified_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(url: str, timeout_s: float = 1.0) -> bytes:
        raise AssertionError("network must not be touched for present files")

    monkeypatch.setattr(fetch_potentials, "fetch_url", explode)
    items = fetch_potentials.plan(sample_manifest(), root=tmp_path, pins={})
    items[0]["sha256"] = PAYLOAD_SHA256
    items[0]["target"].parent.mkdir(parents=True)
    items[0]["target"].write_bytes(PAYLOAD)

    status, _ = fetch_potentials.fetch_item(items[0])

    assert status == "present"


@pytest.mark.unit
def test_main_list_mode_prints_plan_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def explode(url: str, timeout_s: float = 1.0) -> bytes:
        raise AssertionError("--list must not download")

    monkeypatch.setattr(fetch_potentials, "fetch_url", explode)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest()), encoding="utf-8")

    rc = fetch_potentials.main(
        ["--manifest", str(manifest_path), "--root", str(tmp_path), "--list"]
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "ni-mishin-1999-eam-alloy: missing" in out
    assert "url: https://" in out


@pytest.mark.unit
def test_main_returns_nonzero_when_any_fetch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_fetch(url: str, timeout_s: float = 1.0) -> bytes:
        raise OSError("proxy refused")

    monkeypatch.setattr(fetch_potentials, "fetch_url", fail_fetch)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest()), encoding="utf-8")

    rc = fetch_potentials.main(["--manifest", str(manifest_path), "--root", str(tmp_path)])

    assert rc == 1
