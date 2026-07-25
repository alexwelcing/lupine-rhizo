"""Tests for the Phase-0 visualization bundle contract (plan: golden bundles).

Covers, per docs/plans/2026-07-24-visualization-pipeline-plan.md:

- schema validation of the four golden bundles (paths 16, 0, 14, 27);
- determinism: two independent clean builds are byte-identical;
- fail-closed rejection: corrupted energy, off-by-one profile length,
  reordered atoms, wrong/undeclared units, changed source hash;
- missingness encoding (status + null, never NaN/Infinity);
- path-14 all-guides-failed representation;
- path-16 contaminated-success representation (same-engine strong_win AND T1
  contaminated — never a plain cross-engine win).

Tests split in two groups: golden-bundle tests run anywhere against the
committed bundles under data/visualization/bundles/; build-side tests need the
local Z1 sources (/tmp/z1-union-local, /tmp/z1-diagnose) and skip without them.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools" / "analysis"
sys.path.insert(0, str(TOOLS_DIR))

import build_visualization_bundle as bvb  # noqa: E402

BUNDLE_SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "visualization" / "lupine.visualization-bundle.v1.schema.json").read_text()
)
RECIPE_SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "visualization" / "lupine.figure-recipe.v1.schema.json").read_text()
)
BUNDLES_ROOT = REPO_ROOT / "data" / "visualization" / "bundles"

SOURCES_ROOT = Path("/tmp/z1-union-local")
DIAGNOSTICS_ROOT = Path("/tmp/z1-diagnose")
HAVE_SOURCES = (SOURCES_ROOT / "anchors").is_dir() and (SOURCES_ROOT / "inputs").is_dir()

GOLDEN_PATHS = [16, 0, 14, 27]
# Pinned golden bundle digests (Phase-0 acceptance fixtures). Updated in the
# commit that (re)builds the golden bundles; the pin test skips when no
# bundles are committed yet.
GOLDEN_DIGESTS = {
    16: "0486da415ae5791a926ab7862df043a2bfd428fba874a14104b8041669c0f16d",
    0: "c3da4be89ab2ea990c351491076408f434b4bea412b64e1fe0966e832a44401f",
    14: "898693f0a59f9059aa192fb81667c1dacae1660fdcb5bae41b5551623d7236e1",
    27: "91e28ec5f064dc6075c0889e146b5e195854513abf23ed3a67750399c938587e",
}


def _golden_dirs() -> dict[int, Path]:
    found: dict[int, Path] = {}
    for manifest_path in sorted(BUNDLES_ROOT.glob("sha256/*/*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("schema") == "lupine.visualization-bundle.v1":
            found[manifest["path_index"]] = manifest_path.parent
    return found


def golden_dir(path_index: int) -> Path:
    directory = _golden_dirs().get(path_index)
    if directory is None:
        pytest.skip(f"golden bundle for path {path_index} is not committed")
    return directory


def golden_manifest(path_index: int) -> dict:
    return json.loads((golden_dir(path_index) / "manifest.json").read_text())


pytestmark = pytest.mark.unit


# --- Golden bundle contract --------------------------------------------------------


@pytest.mark.parametrize("path_index", GOLDEN_PATHS)
def test_golden_bundle_schema_valid(path_index):
    manifest = golden_manifest(path_index)
    jsonschema.validate(manifest, BUNDLE_SCHEMA)


@pytest.mark.parametrize("path_index", GOLDEN_PATHS)
def test_golden_bundle_verify_green(path_index):
    """--verify recomputes every derived scalar from stored arrays."""
    assert bvb.verify_bundle(golden_dir(path_index)) == []


@pytest.mark.parametrize("path_index", GOLDEN_PATHS)
def test_golden_bundle_id_and_canonical(path_index):
    directory = golden_dir(path_index)
    raw = (directory / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    assert bvb.canonical_json(manifest) == raw, "manifest is not canonical JSON"
    identity = {k: v for k, v in manifest.items() if k != "bundle_id"}
    assert manifest["bundle_id"] == bvb.digest_id(
        bvb.sha256_bytes(bvb.canonical_json(identity))
    )
    digest = manifest["bundle_id"].removeprefix("sha256:")
    assert digest == GOLDEN_DIGESTS[path_index], (
        f"golden bundle digest for path {path_index} drifted: {digest}; "
        "rebuild the goldens deliberately and re-pin GOLDEN_DIGESTS in the same commit"
    )
    assert directory.name == digest and directory.parent.name == digest[:2]


@pytest.mark.parametrize("path_index", GOLDEN_PATHS)
def test_missingness_encoding(path_index):
    """Missing = status + null; no NaN/Infinity anywhere in the manifest."""
    raw = (golden_dir(path_index) / "manifest.json").read_text()
    for token in ("NaN", "Infinity"):
        assert token not in raw
    manifest = json.loads(raw)

    def walk(node):
        if isinstance(node, dict):
            if set(node) >= {"status", "value"} and node.get("value") is None:
                assert isinstance(node["status"], str) and node["status"]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, float):
            assert math.isfinite(node)

    walk(manifest)
    # Representative absent values are status+null, not empty strings.
    assert manifest["method"]["spin"]["status"] == "not_recorded"
    assert manifest["method"]["spin"]["value"] is None
    assert manifest["coordinates"]["migrating_atom_ids"]["value"] is None


@pytest.mark.parametrize("path_index", GOLDEN_PATHS)
def test_neb_wording_never_time(path_index):
    """The non-negotiable rule: image index is a reaction-path sequence."""
    manifest = golden_manifest(path_index)
    reaction = manifest["coordinates"]["reaction_coordinate"]
    assert reaction["unit"] == "image_index"
    assert "reaction-path sequence" in reaction["definition"]
    assert "NOT time" in reaction["definition"]
    for series in manifest["series"]:
        assert series["unit"] == "eV"
    # No frame/coordinate field may be named as time or temperature.
    for frame in manifest["coordinates"]["frames"]:
        assert not any("time" in key.lower() or "temp" in key.lower() for key in frame)


def test_path16_contaminated_success():
    """Seemingly good cross-engine result that is T1-contaminated: the verdict
    must be same-engine strong_win AND T1 contaminated, not a plain win."""
    manifest = golden_manifest(16)
    gates = manifest["quality_gates"]
    verdict = gates["verdict"]
    assert verdict["same_engine"] == "strong_win"
    assert verdict["t1"] == "contaminated"
    assert verdict["cross_engine_contaminated"] is True
    assert verdict["label"] == "strong_win_t1_contaminated"
    assert verdict["label"] != "win"
    # Cross-engine error passes the 40 meV gate numerically ...
    cross = gates["cross_engine"]
    assert cross["dense_vs_reference_abs_error_mev"] == pytest.approx(32.72969285660565)
    assert cross["dense_vs_reference_abs_error_mev"] <= gates["thresholds_mev"]["win"]
    # ... but the T1 wander (117.27 meV > 40) marks it contaminated.
    assert gates["t1"]["wander_mev"] == pytest.approx(117.27167851484046)
    assert gates["t1"]["wander_mev"] > gates["thresholds_mev"]["t1_gate"]
    assert gates["t1"]["driver_pair"] == [1, 3]
    assert cross["primary"] is False
    assert gates["same_engine"]["primary"] is True


def test_path14_all_guides_failed():
    """All four guides failed; the dense extension supplied the profile."""
    manifest = golden_manifest(14)
    provenance = {m["model"]: m for m in manifest["model_provenance"]}
    assert set(provenance) == {"chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium"}
    for model in provenance.values():
        assert model["status"] == "failed"
        assert model["failure_reason"]
    # No model series may exist; the profile is GPAW dense-extension only.
    kinds = {s["kind"] for s in manifest["series"]}
    assert "model" not in kinds
    selection = manifest["selection"]
    assert selection["per_model"] == {}
    assert selection["nominated_union"] == []
    assert selection["dense_extension"]["applied"] is True
    assert selection["dense_extension"]["supplied_indices"] == [0, 1, 2, 3, 4, 5, 6]
    assert selection["evaluated"] == [0, 1, 2, 3, 4, 5, 6]
    verdict = manifest["quality_gates"]["verdict"]
    assert verdict["same_engine"] == "no_guidance"
    assert verdict["label"] == "no_guidance_t1_contaminated"


def test_path27_only_t1_clean():
    manifest = golden_manifest(27)
    verdict = manifest["quality_gates"]["verdict"]
    assert verdict["t1"] == "clean"
    assert verdict["cross_engine_contaminated"] is False
    assert verdict["label"] == "strong_win_t1_clean"
    assert manifest["quality_gates"]["t1"]["wander_mev"] <= 40.0


def test_path0_diagnostics_separately_bound():
    """Path-0 binds its separate diagnostic receipts (metallic saddle);
    other paths must record diagnostics as absent."""
    manifest = golden_manifest(0)
    diagnostics = manifest["diagnostics"]
    assert diagnostics["status"] == "bound"
    assert diagnostics["image_index"] == 3
    runs = {run["label"]: run for run in diagnostics["runs"]}
    assert runs["adopted_h0.20"]["gap_ev"] == pytest.approx(0.019)
    assert runs["sensitivity_h0.18"]["gap_ev"] == pytest.approx(0.018)
    assert runs["adopted_h0.20"]["scf"]["converged"] is True
    assert runs["sensitivity_h0.18"]["fermi_level_ev"] == pytest.approx(0.676)
    # The adopted diagnostic energy binds to the image-3 anchor energy.
    gpaw = next(s for s in manifest["series"] if s["series_id"] == "gpaw_total_energy")
    assert runs["adopted_h0.20"]["energy_ev"] == gpaw["values"][3]
    assert manifest["quality_gates"]["t1"]["driver_pair"] == [0, 3]
    assert manifest["quality_gates"]["t1"]["wander_mev"] == pytest.approx(4212.3309263396295)
    # Path 16 has no bound diagnostics: absent, status + null semantics.
    assert golden_manifest(16)["diagnostics"]["status"] == "absent"


def test_figure_recipe_schema():
    recipe = {
        "schema": "lupine.figure-recipe.v1",
        "recipe_id": "sha256:" + "a" * 64,
        "created_at": "2026-07-25T00:00:00+00:00",
        "source": {
            "bundle_id": "sha256:" + "b" * 64,
            "manifest_sha256": "sha256:" + "c" * 64,
            "trajectory_sha256": None,
            "profile_sha256": "sha256:" + "d" * 64,
            "catalog_record_version": "z1-union-pilot@1",
        },
        "viewer": {
            "name": "lupi",
            "git_commit": "80997f80071859c30bf191795eb035b6c12142bf",
            "build_id": "lupi-80997f8",
            "canonical_view_schema_version": 2,
        },
        "frame": {"image_index": 3, "decoded_frame_digest_v3": "sha256:" + "e" * 64},
        "science_overlay": {
            "visible_series_ids": ["gpaw_total_energy", "vasp_reference_total_energy"],
            "annotation_ids": ["t1_driver_pair"],
            "profile_digest": "sha256:" + "f" * 64,
        },
        "view": {
            "camera": {
                "position": [0.0, 0.0, 30.0],
                "target": [0.0, 0.0, 0.0],
                "up": [0.0, 1.0, 0.0],
                "projection": "perspective",
                "fov_degrees": 45.0,
            },
            "cell": {"visible": True},
            "bonds": {"visible": True, "mode": "inferred"},
            "filter": {"hidden_species": [], "hidden_atom_ids": []},
            "color": {"scheme": "cpk", "background": "#ffffff"},
            "layers": ["atoms", "cell", "profile-panel"],
            "dimensions": {"width": 1920, "height": 1080},
        },
    }
    jsonschema.validate(recipe, RECIPE_SCHEMA)
    bad = json.loads(json.dumps(recipe))
    bad["recipe_id"] = "not-a-digest"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, RECIPE_SCHEMA)
    bad = json.loads(json.dumps(recipe))
    del bad["frame"]["image_index"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, RECIPE_SCHEMA)
    bad = json.loads(json.dumps(recipe))
    bad["frame"]["time_seconds"] = 1.5  # NEB images are never time
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, RECIPE_SCHEMA)


# --- Verify-side fail-closed rejections (tampered copies of golden bundles) ---------


def rebundle(tmp_path: Path, path_index: int, mutate) -> Path:
    """Copy a golden bundle, mutate its manifest, and re-seal it canonically.

    Re-sealing (recomputed bundle_id, directory layout, sidecars) means the
    semantic verify checks — not the packaging checks — are what must fail.
    """
    source = golden_dir(path_index)
    work = tmp_path / "bundle"
    shutil.copytree(source, work)
    manifest = json.loads((work / "manifest.json").read_text())
    mutate(manifest)
    identity = {k: v for k, v in manifest.items() if k != "bundle_id"}
    manifest["bundle_id"] = bvb.digest_id(bvb.sha256_bytes(bvb.canonical_json(identity)))
    raw = bvb.canonical_json(manifest)
    hex_digest = manifest["bundle_id"].removeprefix("sha256:")
    target = tmp_path / "bundles" / "sha256" / hex_digest[:2] / hex_digest
    target.parent.mkdir(parents=True)
    work.rename(target)
    (target / "manifest.json").write_bytes(raw)
    (target / "manifest.json.sha256").write_text(
        f"{bvb.sha256_bytes(raw)}  manifest.json\n", encoding="utf-8"
    )
    return target


def test_verify_rejects_corrupted_energy(tmp_path):
    def mutate(manifest):
        series = next(s for s in manifest["series"] if s["series_id"] == "gpaw_total_energy")
        series["values"][2] += 1.5

    failures = bvb.verify_bundle(rebundle(tmp_path, 16, mutate))
    assert any("barrier" in f or "wander" in f or "recompute" in f for f in failures), failures


def test_verify_rejects_series_detached_from_source(tmp_path):
    """Codex P1-1: a resealed manifest whose displayed series no longer matches
    its frozen source bytes is rejected. The constant offset preserves model
    extrema (and therefore every recomputed anchor set), so only dereferencing
    the series' source pointers catches it."""

    def mutate(manifest):
        series = next(
            s for s in manifest["series"] if s["series_id"] == "model_total_energy/chgnet"
        )
        series["values"] = [value + 0.5 for value in series["values"]]

    failures = bvb.verify_bundle(rebundle(tmp_path, 16, mutate))
    assert any("does not match its declared source" in f for f in failures), failures


def test_verify_rejects_resealed_verdict_strings(tmp_path):
    """Codex P1-2: per-model verdict strings and the aggregate label changed
    together are re-derived from the stored numeric errors, not trusted."""

    def mutate(manifest):
        gates = manifest["quality_gates"]
        for same in gates["same_engine"]["per_model"].values():
            same["verdict"] = "loss"
        gates["verdict"]["same_engine"] = "loss"
        gates["verdict"]["label"] = "loss_t1_contaminated"

    failures = bvb.verify_bundle(rebundle(tmp_path, 16, mutate))
    assert any("verdict" in f for f in failures), failures


def test_verify_rejects_diagnostic_fact_reseal(tmp_path):
    """Codex P1-3: path-0 diagnostic electronic facts are re-parsed from the
    frozen diagnostic receipts at verify time."""

    def mutate(manifest):
        manifest["diagnostics"]["runs"][0]["gap_ev"] = 0.5

    failures = bvb.verify_bundle(rebundle(tmp_path, 0, mutate))
    assert any("gap_ev" in f for f in failures), failures


def test_verify_rejects_diagnostic_energy_reseal(tmp_path):
    """Codex P1-3: the adopted diagnostic energy must still bind to the frozen
    receipt and to the stored GPAW image-3 value."""

    def mutate(manifest):
        manifest["diagnostics"]["runs"][0]["energy_ev"] += 0.25

    failures = bvb.verify_bundle(rebundle(tmp_path, 0, mutate))
    assert any("energy" in f for f in failures), failures


def test_verify_rejects_off_by_one_profile(tmp_path):
    def mutate(manifest):
        series = next(s for s in manifest["series"] if s["series_id"] == "gpaw_total_energy")
        series["values"] = series["values"][:-1]
        series["value_status"] = series["value_status"][:-1]

    failures = bvb.verify_bundle(rebundle(tmp_path, 16, mutate))
    assert any("cardinality" in f for f in failures), failures


def test_verify_rejects_wrong_units(tmp_path):
    def mutate(manifest):
        manifest["coordinates"]["units"] = "nm"

    failures = bvb.verify_bundle(rebundle(tmp_path, 16, mutate))
    assert any("schema" in f or "units" in f for f in failures), failures


def test_verify_rejects_changed_source_hash(tmp_path):
    target = rebundle(tmp_path, 16, lambda manifest: None)
    asset = next((target / "assets").rglob("*.json"))
    payload = bytearray(asset.read_bytes())
    payload[-5] ^= 0x01
    asset.write_bytes(bytes(payload))
    failures = bvb.verify_bundle(target)
    assert any("hash changed" in f for f in failures), failures


def test_verify_rejects_reordered_atoms_in_source(tmp_path):
    """Atom identity/order lives in the frozen panel excerpt; reordering it
    breaks the content address and verify must fail closed."""
    target = rebundle(tmp_path, 16, lambda manifest: None)
    panel_asset = next(
        a for a in json.loads((target / "manifest.json").read_text())["assets"]
        if a["role"] == "panel_path_excerpt"
    )
    asset_path = target / panel_asset["uri"]
    excerpt = json.loads(asset_path.read_text())
    symbols = excerpt["input_images"][2]["symbols"]
    assert symbols[0] != symbols[7]
    symbols[0], symbols[7] = symbols[7], symbols[0]
    asset_path.write_bytes(bvb.canonical_json(excerpt))
    failures = bvb.verify_bundle(target)
    assert any("hash changed" in f for f in failures), failures


# --- Build-side fail-closed rejections (need local Z1 sources) ----------------------


@pytest.fixture()
def source_tree(tmp_path):
    """A tamperable copy of the Z1 sources for path 16 (fresh per test)."""
    if not HAVE_SOURCES:
        pytest.skip("local Z1 sources not present")
    root = tmp_path
    candidates = root / "candidates"
    candidates.mkdir()
    for name in ("z1-union-campaign.json", "z1_nebdft2k_barriers.lock.json"):
        for suffix in ("", ".sha256"):
            shutil.copy(REPO_ROOT / "data" / "candidates" / f"{name}{suffix}", candidates)
    anchors = root / "anchors"
    shutil.copytree(SOURCES_ROOT / "anchors" / "path-16", anchors / "path-16")
    models = root / "models"
    for model in bvb.MODELS:
        (models / model).mkdir(parents=True)
        shutil.copy(SOURCES_ROOT / "inputs" / model / "cell_result.json", models / model)
    return {
        "panel": candidates / "z1_nebdft2k_barriers.lock.json",
        "campaign": candidates / "z1-union-campaign.json",
        "anchors": anchors,
        "models": models,
    }


def build16(tree):
    return bvb.build_bundle(
        16, tree["panel"], tree["campaign"], tree["anchors"], tree["models"], None
    )


def resign(path: Path) -> None:
    """Re-sign a tampered source's .sha256 sidecar so the semantic check — not
    the sidecar hash gate — is what fires."""
    sidecar = path.with_name(path.name + ".sha256")
    if sidecar.is_file():
        sidecar.write_text(f"{bvb.sha256_file(path)}  {path.name}\n")


def test_build_clean(source_tree):
    manifest, _ = build16(source_tree)
    assert manifest["quality_gates"]["verdict"]["label"] == "strong_win_t1_contaminated"


def test_build_rejects_corrupted_energy(source_tree):
    receipt = source_tree["anchors"] / "path-16" / "anchor-2.json"
    record = json.loads(receipt.read_text())
    record["gpaw_energy_ev"] += 1.5
    receipt.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    with pytest.raises(bvb.BundleError, match="cross-check"):
        build16(source_tree)


def test_build_rejects_nonfinite_energy(source_tree):
    receipt = source_tree["anchors"] / "path-16" / "anchor-1.json"
    receipt.write_text('{"gpaw_energy_ev": NaN}\n')
    with pytest.raises(bvb.BundleError):
        build16(source_tree)


def test_build_rejects_off_by_one_profile(source_tree):
    panel = json.loads(source_tree["panel"].read_text())
    panel["paths"][16]["reference"]["energies_ev"] = panel["paths"][16]["reference"][
        "energies_ev"
    ][:-1]
    source_tree["panel"].write_text(json.dumps(panel))
    resign(source_tree["panel"])
    with pytest.raises(bvb.BundleError, match="frame mismatch"):
        build16(source_tree)


def test_build_rejects_model_profile_length_mismatch(source_tree):
    artifact = source_tree["models"] / "chgnet" / "cell_result.json"
    record = json.loads(artifact.read_text())
    prediction = next(p for p in record["predictions"] if p["path_id"] == "mp-760344_10_4_0_1_0")
    prediction["predicted_image_energies_ev"] = prediction["predicted_image_energies_ev"][:-1]
    artifact.write_text(json.dumps(record))
    with pytest.raises(bvb.BundleError, match="cross-check"):
        build16(source_tree)


def test_build_rejects_reordered_atoms(source_tree):
    panel = json.loads(source_tree["panel"].read_text())
    symbols = panel["paths"][16]["input_images"][2]["symbols"]
    assert symbols[0] != symbols[7]
    symbols[0], symbols[7] = symbols[7], symbols[0]
    source_tree["panel"].write_text(json.dumps(panel))
    resign(source_tree["panel"])
    with pytest.raises(bvb.BundleError, match="atom identity"):
        build16(source_tree)


def test_build_rejects_undeclared_units(source_tree):
    panel = json.loads(source_tree["panel"].read_text())
    image = panel["paths"][16]["input_images"][0]
    image["positions_nm"] = image.pop("positions_angstrom")
    source_tree["panel"].write_text(json.dumps(panel))
    resign(source_tree["panel"])
    with pytest.raises(bvb.BundleError, match="units"):
        build16(source_tree)


def test_build_rejects_changed_source_hash(source_tree):
    campaign = source_tree["campaign"]
    payload = bytearray(campaign.read_bytes())
    payload[100] ^= 0x01
    campaign.write_bytes(bytes(payload))
    with pytest.raises(bvb.BundleError, match="hash changed"):
        build16(source_tree)


# --- The Phase-0 gate: two independent clean builds are byte-identical ---------------


@pytest.mark.skipif(not HAVE_SOURCES, reason="local Z1 sources not present")
def test_determinism_two_clean_builds(tmp_path):
    outputs = []
    for name in ("build-a", "build-b"):
        outdir = tmp_path / name
        result = subprocess.run(
            [
                sys.executable,
                str(TOOLS_DIR / "build_visualization_bundle.py"),
                "--path-index",
                "16",
                "--outdir",
                str(outdir),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        summary = json.loads(result.stdout)
        outputs.append((outdir, summary))
    (dir_a, summary_a), (dir_b, summary_b) = outputs
    assert summary_a["bundle_id"] == summary_b["bundle_id"]
    manifest_a = (dir_a / "sha256" / summary_a["bundle_id"].removeprefix("sha256:")[:2]
                  / summary_a["bundle_id"].removeprefix("sha256:") / "manifest.json").read_bytes()
    manifest_b = (dir_b / "sha256" / summary_b["bundle_id"].removeprefix("sha256:")[:2]
                  / summary_b["bundle_id"].removeprefix("sha256:") / "manifest.json").read_bytes()
    assert manifest_a == manifest_b, "two clean builds must be byte-identical"
