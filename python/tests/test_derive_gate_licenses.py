"""Tests for derive_gate_licenses.py (licenses.v1 registry generation).

Synthetic input artifacts only. The script is imported from python/scripts
like the other runner tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import derive_gate_licenses as dgl  # noqa: E402

from lupine_distill.statics import InputValidationError  # noqa: E402
from lupine_distill.statics.licenses import (  # noqa: E402
    CORPUS_IN_SAMPLE,
    CORPUS_REFERENCE_BOUND,
    LICENSES_SCHEMA_ID,
    STATUS_ANTI_CORRELATED,
    STATUS_DESCRIPTIVE,
    STATUS_LICENSED,
    load_license_registry,
)

pytestmark = pytest.mark.unit


def _rho_entry(rho: float, n: int, **extra: object) -> dict:
    return {
        "n_materials": n,
        "spearman_rho_dispersion_vs_median_rel_error": rho,
        "per_material": {},
        **extra,
    }


def _by_class_payload() -> dict:
    return {
        "schema": dgl.BY_CLASS_SCHEMA,
        "generated_at": "2026-07-13T15:35:44+00:00",
        "sources": {
            "metals": "data/y_matrix_runs/bound",
            "perovskites": "data/candidates/round1/report.json",
        },
        "by_class": {
            "metals-fcc": {
                "a0": _rho_entry(0.067, 9),
                "B0": _rho_entry(-0.633, 9),
            },
            "metals-bcc": {
                "a0": _rho_entry(0.893, 7),
                "B0": _rho_entry(0.321, 7),
            },
            "perovskites": {
                "a0": _rho_entry(
                    -0.8,
                    4,
                    small_n_warning="n=4 < 5: a single material determines "
                    "the rank ordering",
                ),
                "b0": _rho_entry(1.0, 5),
            },
        },
    }


def _pooled_payload() -> dict:
    return {
        "schema": dgl.POOLED_SCHEMA,
        "generated_at": "2026-07-13T13:16:34+00:00",
        "evidence_dir": "data/y_matrix_runs/bound",
        "properties": {
            "a0": _rho_entry(0.566, 21),
            "B0": _rho_entry(0.164, 21),
        },
    }


def _build(by_class: dict | None = None, pooled: dict | None = None) -> dict:
    return dgl.build_registry(
        by_class or _by_class_payload(),
        pooled or _pooled_payload(),
        by_class_path="in/by_class.json",
        pooled_path="in/pooled.json",
        generated_at="2026-07-13T16:00:00+00:00",
    )


class TestBuildRegistry:
    def test_statuses_follow_the_registered_rule(self) -> None:
        by_class = _build()["by_class"]
        assert by_class["metals-bcc"]["a0"]["status"] == STATUS_LICENSED
        assert by_class["metals-bcc"]["b0"]["status"] == STATUS_DESCRIPTIVE
        assert by_class["metals-fcc"]["a0"]["status"] == STATUS_DESCRIPTIVE
        assert by_class["metals-fcc"]["b0"]["status"] == STATUS_ANTI_CORRELATED
        assert by_class["perovskites"]["a0"]["status"] == STATUS_DESCRIPTIVE
        assert by_class["perovskites"]["b0"]["status"] == STATUS_DESCRIPTIVE

    def test_rho_and_n_recorded_verbatim(self) -> None:
        by_class = _build()["by_class"]
        # Even the refused perovskite b0 shows its in-sample rho = 1.0.
        assert by_class["perovskites"]["b0"]["rho"] == pytest.approx(1.0)
        assert by_class["perovskites"]["b0"]["n"] == 5
        assert by_class["metals-fcc"]["b0"]["rho"] == pytest.approx(-0.633)

    def test_property_keys_lowercased(self) -> None:
        by_class = _build()["by_class"]
        assert set(by_class["metals-fcc"]) == {"a0", "b0"}

    def test_corpus_kinds_and_caveats(self) -> None:
        by_class = _build()["by_class"]
        assert by_class["metals-bcc"]["a0"]["corpus_kind"] == CORPUS_REFERENCE_BOUND
        assert by_class["metals-bcc"]["a0"]["corpus"] == "data/y_matrix_runs/bound"
        for prop in ("a0", "b0"):
            entry = by_class["perovskites"][prop]
            assert entry["corpus_kind"] == CORPUS_IN_SAMPLE
            assert entry["corpus"] == "data/candidates/round1/report.json"
            assert any("circular" in caveat for caveat in entry["caveats"])
        assert any(
            "n=4 < 5" in caveat
            for caveat in by_class["perovskites"]["a0"]["caveats"]
        )

    def test_b0_ceiling_override_recorded_and_capping(self) -> None:
        registry = _build()
        overrides = registry["program_overrides"]
        assert len(overrides) == 1
        assert overrides[0]["property"] == "b0"
        assert overrides[0]["license_ceiling"] == STATUS_DESCRIPTIVE
        assert "lift_requires" in overrides[0]
        # The ceiling caveat travels on every b0 entry; the fcc b0
        # anti-correlated warning survives the ceiling.
        for class_name in ("metals-fcc", "metals-bcc", "perovskites"):
            caveats = registry["by_class"][class_name]["b0"]["caveats"]
            assert any("license_ceiling" in caveat for caveat in caveats)
        assert registry["by_class"]["metals-fcc"]["b0"]["status"] == (
            STATUS_ANTI_CORRELATED
        )

    def test_ceiling_caps_a_would_be_licensed_b0(self) -> None:
        payload = _by_class_payload()
        payload["by_class"]["metals-bcc"]["B0"] = _rho_entry(0.9, 7)
        by_class = _build(by_class=payload)["by_class"]
        assert by_class["metals-bcc"]["b0"]["status"] == STATUS_DESCRIPTIVE

    def test_provenance_and_discipline_recorded(self) -> None:
        registry = _build()
        assert registry["schema"] == LICENSES_SCHEMA_ID
        derived = registry["derived_from"]
        assert derived["path"] == "in/by_class.json"
        assert derived["schema"] == dgl.BY_CLASS_SCHEMA
        assert derived["generated_at"] == "2026-07-13T15:35:44+00:00"
        assert derived["pooled_path"] == "in/pooled.json"
        assert derived["pooled_schema"] == dgl.POOLED_SCHEMA
        rule = registry["derivation_rule"]
        assert rule["licensed_min_rho"] == 0.5
        assert rule["anti_correlated_max_rho"] == -0.5
        assert rule["n_min"] == 5
        assert rule["corpus_kind_required_for_status"] == CORPUS_REFERENCE_BOUND
        assert len(registry["update_discipline"]) == 5
        assert any(
            "immutable" in note for note in registry["update_discipline"]
        )

    def test_pooled_context_recorded_without_status(self) -> None:
        pooled = _build()["pooled_context"]
        assert pooled["properties"]["a0"] == {"rho": 0.566, "n": 21}
        assert pooled["properties"]["B0"] == {"rho": 0.164, "n": 21}
        assert "confers no status" in pooled["note"]

    def test_unregistered_class_fails_closed_to_in_sample(self) -> None:
        payload = _by_class_payload()
        payload["by_class"]["covalent-intermetallic"] = {"a0": _rho_entry(0.99, 9)}
        by_class = _build(by_class=payload)["by_class"]
        entry = by_class["covalent-intermetallic"]["a0"]
        assert entry["corpus_kind"] == CORPUS_IN_SAMPLE
        assert entry["status"] == STATUS_DESCRIPTIVE
        assert any("unregistered" in caveat for caveat in entry["caveats"])

    def test_generated_registry_round_trips_through_loader(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "licenses.v1.json"
        path.write_text(json.dumps(_build()), encoding="utf-8")
        registry = load_license_registry(path)
        assert registry.licenses[("metals-bcc", "a0")].status == STATUS_LICENSED
        assert registry.licenses[("metals-fcc", "b0")].status == (
            STATUS_ANTI_CORRELATED
        )

    def test_missing_by_class_mapping_rejects(self) -> None:
        payload = _by_class_payload()
        del payload["by_class"]
        with pytest.raises(InputValidationError, match="by_class"):
            _build(by_class=payload)


class TestMain:
    def _write_inputs(self, tmp_path: Path) -> tuple[Path, Path]:
        by_class = tmp_path / "by_class.json"
        by_class.write_text(json.dumps(_by_class_payload()), encoding="utf-8")
        pooled = tmp_path / "pooled.json"
        pooled.write_text(json.dumps(_pooled_payload()), encoding="utf-8")
        return by_class, pooled

    def test_writes_a_loadable_registry(self, tmp_path: Path) -> None:
        by_class, pooled = self._write_inputs(tmp_path)
        out = tmp_path / "licenses.v1.json"
        rc = dgl.main(
            ["--by-class", str(by_class), "--pooled", str(pooled), "--out", str(out)]
        )
        assert rc == 0
        registry = load_license_registry(out)
        assert registry.licenses[("metals-bcc", "a0")].status == STATUS_LICENSED

    def test_refuses_to_overwrite_without_force(self, tmp_path: Path) -> None:
        by_class, pooled = self._write_inputs(tmp_path)
        out = tmp_path / "licenses.v1.json"
        argv = ["--by-class", str(by_class), "--pooled", str(pooled), "--out", str(out)]
        assert dgl.main(argv) == 0
        assert dgl.main(argv) == 1  # immutable registries: no silent rewrite
        assert dgl.main([*argv, "--force"]) == 0

    def test_wrong_input_schema_fails(self, tmp_path: Path) -> None:
        by_class, pooled = self._write_inputs(tmp_path)
        payload = _by_class_payload()
        payload["schema"] = "lupine.wrong.v1"
        by_class.write_text(json.dumps(payload), encoding="utf-8")
        out = tmp_path / "licenses.v1.json"
        rc = dgl.main(
            ["--by-class", str(by_class), "--pooled", str(pooled), "--out", str(out)]
        )
        assert rc == 1
        assert not out.exists()
