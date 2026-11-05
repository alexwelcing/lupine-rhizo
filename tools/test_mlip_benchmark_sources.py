from __future__ import annotations

import json
from pathlib import Path

import mlip_benchmark_sources
from local_artifacts import manifest_local_paths, requires_local_artifact


def test_real_material_source_packet_validates() -> None:
    requires_local_artifact(*manifest_local_paths())
    manifest = mlip_benchmark_sources.load_manifest()
    issues = mlip_benchmark_sources.validate_source_packet(manifest)

    assert issues == []


def test_ni_inventory_tracks_ready_eam_and_meam_candidate() -> None:
    manifest = mlip_benchmark_sources.load_manifest()
    rows = mlip_benchmark_sources.ni_inventory(manifest)

    assert sum(row["status"] == "ready_local_evidence" for row in rows) >= 3
    assert any(str(row["pair_style"]).startswith("meam") for row in rows)
    assert any(row["publication_use"] == "primary_candidate" for row in rows)


def test_ni_bulk_results_extract_real_local_evidence() -> None:
    requires_local_artifact(*manifest_local_paths(fields=("result_json",)))
    manifest = mlip_benchmark_sources.load_manifest()
    rows = mlip_benchmark_sources.ni_bulk_results(manifest)

    assert len(rows) >= 3
    mishin = next(row for row in rows if row["label"] == "Mishin-1999")
    assert mishin["success"] is True
    assert mishin["c11"] > 200
    assert mishin["c11_reference"] == 246.5
    assert mishin["c11_abs_error"] < 5


def test_validation_rejects_missing_citation_key(tmp_path: Path) -> None:
    source_path = tmp_path / "manifest.json"
    manifest = mlip_benchmark_sources.load_manifest()
    manifest = json.loads(json.dumps(manifest))
    manifest["sources"][0]["citation_keys"] = []
    source_path.write_text(json.dumps(manifest), encoding="utf-8")

    loaded = mlip_benchmark_sources.load_manifest(source_path)
    issues = mlip_benchmark_sources.validate_source_packet(loaded, check_local=False)

    assert any("citation_keys" in issue for issue in issues)


def test_repo_path_normalizes_only_the_leading_legacy_directory(tmp_path: Path) -> None:
    resolve = mlip_benchmark_sources.resolve_repo_path
    assert resolve(tmp_path, "atlas-distill/lammps_runs/Ni/potential") == (
        tmp_path / "distill/lammps_runs/Ni/potential"
    )
    assert resolve(tmp_path, "distill/lammps_runs/Ni/potential") == (
        tmp_path / "distill/lammps_runs/Ni/potential"
    )
    assert resolve(tmp_path, "nested/atlas-distill/potential") == (
        tmp_path / "nested/atlas-distill/potential"
    )
    assert resolve(tmp_path, "atlas-distill-other/potential") == (
        tmp_path / "atlas-distill-other/potential"
    )
    absolute = (tmp_path / "atlas-distill/potential").as_posix()
    assert resolve(Path("/unused-root"), absolute) == Path(absolute)
    assert resolve(tmp_path, None) is None
    assert resolve(tmp_path, " ") is None
