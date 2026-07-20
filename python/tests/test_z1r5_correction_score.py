from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("score_z1r5", ROOT / "tools" / "score_z1r5_correction.py")
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
sys.modules.setdefault("score_z1r5", tool)
spec.loader.exec_module(tool)


def test_direction_gate_requires_one_sided_errors():
    assert tool.direction_gate([-1.0, -2.0, -0.5]) == (True, "all_negative")
    assert tool.direction_gate([1.0, 2.0, 0.5]) == (True, "all_positive")
    ok, reason = tool.direction_gate([-1.0, 2.0])
    assert ok is False and reason == "direction"
    ok, reason = tool.direction_gate([])
    assert ok is False


def test_theorem_caps_round4_v2():
    # inflation applies iff b-1 > 2s
    ok, side = tool.theorem_caps([1.4, 1.5, 1.6])
    assert ok is True and side == "inflation"
    ok, _ = tool.theorem_caps([1.01, 1.4, 1.9])
    assert ok is False
    # deflation requires 1-b > 3s AND b >= 0.5
    ok, side = tool.theorem_caps([0.7, 0.75, 0.72])
    assert ok is True and side == "deflation"
    ok, _ = tool.theorem_caps([0.2, 0.3, 0.9])
    assert ok is False


def test_fit_linear_recovers_known_line():
    a, b = tool.fit_linear([(1.0, -50.0), (2.0, -100.0), (3.0, -150.0), (1.5, -75.0)])
    assert a == pytest.approx(0.0)
    assert b == pytest.approx(-50.0)


def test_family_of():
    assert tool.family_of("C-Fe-Li-O-P") == "phosphate"
    assert tool.family_of("Cl-Cr-Li") == "halide"
    assert tool.family_of("Bi-Li-S") == "sulfide"
    assert tool.family_of("B-Li-O-Ti") == "borate"
    assert tool.family_of("Ca-Li-N-Si") == "nitride"
    assert tool.family_of("Al-Li-O-V") == "oxide"
