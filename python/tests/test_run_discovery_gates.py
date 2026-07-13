"""Tests for the discovery-gates runner (per-property thresholds + gate order).

The runner is a script, not package code, so these tests import it from
python/scripts. Everything here is CPU-only (EMT); the GPU MLIPs never load.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from ase.calculators.emt import EMT

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_discovery_gates as rdg  # noqa: E402

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# provisional_refusal_reasons (the early-stop decision)
# --------------------------------------------------------------------------


def _sub(per_model: dict, concordance: dict) -> dict:
    return {"per_model": per_model, "gates": {"concordance": concordance}}


def _concordance_gate(level: str) -> dict:
    return {"values": {"level": level}}


class TestProvisionalRefusalReasons:
    def test_clean_subject_has_no_reasons(self) -> None:
        sub = _sub(
            {"m1": {"born_passed": True}, "m2": {"born_passed": True}},
            {"a0": _concordance_gate("pass"), "c44": _concordance_gate("flag")},
        )
        assert rdg.provisional_refusal_reasons(sub) == []

    def test_measurement_error_refuses(self) -> None:
        sub = _sub(
            {"m1": {"error": "boom"}, "m2": {"born_passed": True}},
            {},
        )
        reasons = rdg.provisional_refusal_reasons(sub)
        assert len(reasons) == 1
        assert "measurement error" in reasons[0]
        assert "m1" in reasons[0]

    def test_born_failure_refuses(self) -> None:
        sub = _sub(
            {"m1": {"born_passed": False}, "m2": {"born_passed": True}},
            {"a0": _concordance_gate("pass")},
        )
        reasons = rdg.provisional_refusal_reasons(sub)
        assert len(reasons) == 1
        assert "Born failure" in reasons[0]

    def test_concordance_refusal_refuses(self) -> None:
        sub = _sub(
            {"m1": {"born_passed": True}, "m2": {"born_passed": True}},
            {"c11": _concordance_gate("refuse"), "c44": _concordance_gate("refuse")},
        )
        reasons = rdg.provisional_refusal_reasons(sub)
        assert len(reasons) == 1
        assert "concordance refusal" in reasons[0]
        assert "c11" in reasons[0] and "c44" in reasons[0]

    def test_flag_alone_does_not_refuse(self) -> None:
        sub = _sub(
            {"m1": {"born_passed": True}},
            {"b0": _concordance_gate("flag")},
        )
        assert rdg.provisional_refusal_reasons(sub) == []

    def test_reasons_compose(self) -> None:
        sub = _sub(
            {"m1": {"error": "boom"}, "m2": {"born_passed": False}},
            {"c44": _concordance_gate("refuse")},
        )
        assert len(rdg.provisional_refusal_reasons(sub)) == 3


# --------------------------------------------------------------------------
# End-to-end runner on EMT (CPU): v2 thresholds + both gate orders
# --------------------------------------------------------------------------


def _write_full_evidence(
    directory: Path, material: str, model: str, values: dict[str, float]
) -> None:
    payload = {
        "schema": "lupine.mlip.calc_evidence.v1",
        "material": material,
        "source": {"model_id": model, "backend": "ase", "device": "cpu"},
        "properties": [
            {"name": name, "value": value, "unit": "GPa" if name != "a0" else "Angstrom"}
            for name, value in values.items()
        ],
    }
    (directory / f"{material}_{model}.evidence.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _make_baseline(directory: Path) -> None:
    """Six materials x two models with all five gate properties."""
    for i in range(6):
        base = {"a0": 4.0, "B0": 100.0, "C11": 200.0, "C12": 90.0, "C44": 50.0}
        spread = 0.02 * (1 + i)
        _write_full_evidence(
            directory, f"M{i}", "m1", {k: v * (1 - spread) for k, v in base.items()}
        )
        _write_full_evidence(
            directory, f"M{i}", "m2", {k: v * (1 + spread) for k, v in base.items()}
        )


def _emt_factory(device: str) -> tuple[object, str]:
    assert device == "cpu"
    return EMT(), "emt (ase built-in)"


TEST_PANEL = (
    rdg.Subject(label="Ni_fcc", formula="Ni", structure_type="fcc", role="test"),
    rdg.Subject(label="Cu_fcc", formula="Cu", structure_type="fcc", role="test"),
)


@pytest.fixture()
def emt_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Runner patched to EMT models and a synthetic v2 baseline."""
    monkeypatch.setitem(rdg.PANELS, "emt-test", TEST_PANEL)
    monkeypatch.setattr(
        rdg, "MODEL_REGISTRY", {"emt-a": _emt_factory, "emt-b": _emt_factory}
    )
    baseline = tmp_path / "elastic_baseline"
    baseline.mkdir()
    _make_baseline(baseline)
    out_dir = tmp_path / "out"

    def run(*extra: str) -> dict:
        argv = [
            "--device", "cpu",
            "--panel", "emt-test",
            "--models", "emt-a,emt-b",
            "--dynamic-model", "emt-a",
            "--thresholds", "v2",
            "--elastic-baseline-dir", str(baseline),
            "--out-dir", str(out_dir),
            "--dynamic-supercell", "2",
            *extra,
        ]
        assert rdg.main(argv) == 0
        return json.loads((out_dir / "report.json").read_text(encoding="utf-8"))

    return run


class TestRunnerEndToEnd:
    def test_early_stop_v2_report(self, emt_runner) -> None:
        report = emt_runner("--gate-order", "early-stop")
        assert report["thresholds_version"] == "v2"
        assert report["gate_order"] == "early-stop"
        # Per-property thresholds, all five, each with its own provenance.
        assert set(report["concordance_thresholds"]) == set(
            rdg.CONCORDANCE_PROPERTIES
        )
        for t in report["concordance_thresholds"].values():
            assert t["n_samples"] == 6
            assert "elastic_baseline" in t["source"]
        for label in ("Ni_fcc", "Cu_fcc"):
            sub = report["subjects"][label]
            # Two identical EMT models: dispersion 0 -> concordance passes,
            # Born passes -> nothing refused -> dynamic gate RAN (not skipped).
            assert "dynamic_return" in sub["gates"]
            assert "dynamic_return_skipped" not in sub["gates"]
            assert sub["overall_verdict"] == "CERTIFIED"

    def test_legacy_order_matches_verdicts(self, emt_runner) -> None:
        early = emt_runner("--gate-order", "early-stop")
        legacy = emt_runner("--gate-order", "legacy")
        assert legacy["gate_order"] == "legacy"
        for label in ("Ni_fcc", "Cu_fcc"):
            assert (
                early["subjects"][label]["overall_verdict"]
                == legacy["subjects"][label]["overall_verdict"]
            )

    def test_v1_thresholds_still_reachable(self, emt_runner, tmp_path: Path) -> None:
        bound = tmp_path / "bound"
        bound.mkdir()
        for i in range(6):
            _write_full_evidence(bound, f"M{i}", "m1", {"B0": 100.0 - i})
            _write_full_evidence(bound, f"M{i}", "m2", {"B0": 100.0 + i})
        report = emt_runner("--thresholds", "v1", "--bound-dir", str(bound))
        assert report["thresholds_version"] == "v1"
        # v1 transfers ONE threshold set to every property.
        values = {
            (t["flag"], t["refuse"])
            for t in report["concordance_thresholds"].values()
        }
        assert len(values) == 1
