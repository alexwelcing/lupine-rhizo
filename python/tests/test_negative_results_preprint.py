from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "paper/negative-results-preprint/build_artifacts.py"
SPEC = importlib.util.spec_from_file_location("negative_results_build_artifacts", BUILDER)
assert SPEC and SPEC.loader
build_artifacts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_artifacts)


def test_z3_completion_rejects_missing_candidate_model_cell() -> None:
    raw = json.loads(
        (ROOT / "data/candidates/z3/source/z3-candidate-measurements.json").read_text()
    )
    expected_models = {
        "chgnet",
        "mace-mp-medium",
        "mace-mp-small",
        "mace-mpa-0-medium",
    }
    raw["candidates"][0]["model_measurements"].pop()

    with pytest.raises(ValueError, match="complete model panel"):
        build_artifacts.validate_z3_completion(raw, expected_models)


@pytest.mark.parametrize(
    ("field", "value"),
    [("model_count", 3), ("raw_measurement_count", 127)],
)
def test_z3_completion_rejects_contradictory_declared_counts(field: str, value: int) -> None:
    raw = json.loads(
        (ROOT / "data/candidates/z3/source/z3-candidate-measurements.json").read_text()
    )
    raw[field] = value
    expected_models = {
        "chgnet",
        "mace-mp-medium",
        "mace-mp-small",
        "mace-mpa-0-medium",
    }

    with pytest.raises(ValueError, match=field):
        build_artifacts.validate_z3_completion(raw, expected_models)


def test_global_operator_claim_tokens_are_derived_from_locked_values() -> None:
    source = build_artifacts.build_source_data(build_artifacts.verify_inputs())
    mutated = copy.deepcopy(source)
    mutated["global_operator"]["measurement"]["raw_mae_gpa"] = 20.0
    mutated["global_operator"]["measurement"]["corrected_mae_gpa"] = 30.0
    manuscript = (ROOT / "paper/negative-results-preprint/manuscript.tex").read_text()

    with pytest.raises(SystemExit, match="20.00.*30.00"):
        build_artifacts.verify_claims(mutated, manuscript=manuscript)


def test_global_operator_claim_guard_requires_actual_degradation() -> None:
    source = build_artifacts.build_source_data(build_artifacts.verify_inputs())
    mutated = copy.deepcopy(source)
    measurement = mutated["global_operator"]["measurement"]
    measurement["raw_mae_gpa"], measurement["corrected_mae_gpa"] = (
        measurement["corrected_mae_gpa"],
        measurement["raw_mae_gpa"],
    )
    manuscript = (ROOT / "paper/negative-results-preprint/manuscript.tex").read_text()

    with pytest.raises(SystemExit, match="degradation guard changed"):
        build_artifacts.verify_claims(mutated, manuscript=manuscript)


def test_locked_inputs_include_raw_z3_registry_and_global_operator_lock() -> None:
    assert "data/candidates/z3/source/z3-candidate-measurements.json" in build_artifacts.EXPECTED
    assert "paper/negative-results-preprint/global-operator.lock.json" in build_artifacts.EXPECTED


def test_corrected_library_exports_match_sources_and_manifest() -> None:
    export_root = ROOT / "exports/library-content/latest"
    manifest = json.loads((export_root / "manifest.json").read_text())
    by_source = {entry["source"]: entry for entry in manifest["files"]}
    catalog = {entry["id"]: entry for entry in manifest["catalog"]["entries"]}
    assert "systematic under-prediction" not in catalog["z1-barrier-campaign-round4"]["subtitle"]

    for relative in (
        "docs/validation/z1-barrier-campaign-round4-results.md",
        "docs/validation/z3-adsorption-delta-campaign-round4-results.md",
    ):
        source_bytes = (ROOT / relative).read_bytes()
        exported_bytes = (export_root / f"articles/{relative}").read_bytes()
        assert exported_bytes == source_bytes
        assert by_source[relative]["bytes"] == len(exported_bytes)
        assert by_source[relative]["sha256"] == hashlib.sha256(exported_bytes).hexdigest()


@pytest.mark.parametrize(
    ("relative_path", "mutation"),
    [
        (
            "data/candidates/z3/source/z3-candidate-measurements.json",
            lambda document: document["candidates"][0]["model_measurements"].pop(),
        ),
        (
            "paper/negative-results-preprint/global-operator.lock.json",
            lambda document: document["measurement"].update(
                {"raw_mae_gpa": 20.0, "corrected_mae_gpa": 30.0}
            ),
        ),
    ],
)
def test_check_rejects_reviewer_adversarial_mutations(
    tmp_path: Path, relative_path: str, mutation
) -> None:
    for locked_path in build_artifacts.EXPECTED:
        destination = tmp_path / locked_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / locked_path, destination)
    copied_builder = tmp_path / "paper/negative-results-preprint/build_artifacts.py"
    shutil.copyfile(BUILDER, copied_builder)

    target = tmp_path / relative_path
    document = json.loads(target.read_text())
    mutation(document)
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")

    result = subprocess.run(
        [sys.executable, str(copied_builder), "--check"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert f"digest mismatch: {relative_path}" in result.stderr
