"""Tests for claim_table: fixture round-trip, missing-key failure, deterministic order."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "tms2027_proceedings_results.json"


@pytest.fixture(scope="session")
def fixture_results() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def rendered(fixture_results: dict) -> str:
    from claim_table.core import render_markdown

    return render_markdown(fixture_results)


def test_fixture_is_the_canonical_results_object(fixture_results: dict) -> None:
    assert fixture_results["schema"] == "lupine.tms2027.proceedings.results.v1"
    assert fixture_results["recovery_outputs_present"] is False
    # consistency gates in the shipped object are all green
    assert all(fixture_results["consistency"].values())


def test_load_results_reads_fixture() -> None:
    from claim_table.core import load_results

    loaded = load_results(FIXTURE)
    assert loaded["schema"] == "lupine.tms2027.proceedings.results.v1"


def test_table_has_header_and_one_row_per_headline(fixture_results: dict, rendered: str) -> None:
    from claim_table.core import build_rows

    rows = build_rows(fixture_results)
    lines = rendered.splitlines()
    assert lines[0] == "| Value | Binding key |"
    assert lines[1] == "|---|---|"
    assert len(lines) == 2 + len(rows)
    # every row is exactly two columns (leading, middle, trailing pipe)
    assert all(line.count("|") == 3 for line in lines[2:])
    # spot-bind a handful of known headline values to their binding keys
    got = {row.binding_key: row.rendered for row in rows}
    assert got["derived.funnel.kim_model_objects_queried"] == "965"
    assert got["derived.funnel.born_stable_model_element_tensors"] == "559"
    assert got["derived.geometry.pr_median"] == "1.0863"
    assert got["quoted.layer2_raw_mae_gpa.value"] == "17.84"
    assert got["quoted.z1_mae_range_mev.value"] == "[135.0, 242.5]"


def test_binding_keys_partition_by_section(fixture_results: dict, rendered: str) -> None:
    from claim_table.core import build_rows

    keys = [row.binding_key for row in build_rows(fixture_results)]
    assert keys
    assert all(key.startswith("derived.") or key.startswith("quoted.") for key in keys)
    # per-record arrays are record detail, not headlines
    assert not any(".per_group" in key for key in keys)
    # every quoted entry contributes exactly its .value leaf
    expected_quoted = {f"quoted.{name}.value" for name in fixture_results["quoted"]}
    assert expected_quoted == {k for k in keys if k.startswith("quoted.")}


def test_deterministic_ordering(fixture_results: dict, rendered: str) -> None:
    from claim_table.core import build_rows, render_markdown

    keys = [row.binding_key for row in build_rows(fixture_results)]
    assert keys == sorted(keys)
    # key insertion order in the JSON must not affect output
    shuffled = {
        "schema": fixture_results["schema"],
        "quoted": dict(reversed(list(fixture_results["quoted"].items()))),
        "derived": dict(reversed(list(fixture_results["derived"].items()))),
    }
    assert render_markdown(shuffled) == rendered
    # repeated renders are byte-identical
    assert render_markdown(fixture_results) == rendered


def test_missing_required_key_fails_closed(tmp_path: Path) -> None:
    from claim_table.core import MissingKeyError, load_results

    stripped = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del stripped["quoted"]
    bad = tmp_path / "missing_quoted.json"
    bad.write_text(json.dumps(stripped), encoding="utf-8")

    with pytest.raises(MissingKeyError) as excinfo:
        load_results(bad)
    assert "quoted" in str(excinfo.value)


def test_cli_missing_key_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    stripped = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del stripped["derived"]
    bad = tmp_path / "no_derived.json"
    bad.write_text(json.dumps(stripped), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "claim_table", str(bad)],
        capture_output=True,
        text=True,
        cwd=PACKAGE_ROOT,
    )
    assert proc.returncode == 3, proc.stderr
    assert "derived" in proc.stderr


def test_cli_prints_table_for_fixture(capsys: pytest.CaptureFixture) -> None:
    from claim_table.__main__ import main

    assert main([str(FIXTURE)]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "| Value | Binding key |"
    assert "derived.funnel.scalar_cij_values" in out
    assert "quoted.layer2_raw_mae_gpa.value" in out


def test_cli_usage_error_without_args() -> None:
    from claim_table.__main__ import main

    assert main([]) == 2
