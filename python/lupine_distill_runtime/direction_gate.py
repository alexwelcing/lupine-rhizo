"""Direction-gated runtime corrections: port of the proven offline gate.

This module is the runtime mirror of the offline reference implementations —
the frozen Round-3 rule in ``python/scripts/run_round3_analysis.py``
(``apply_frozen_rule``) and the Round-4 theorem caps in
``tools/round4_cloud_campaign.py`` (``correction``) — so the Lean laws in
``lean-spec/LupineEvidence/Shapes/Certificates.lean`` are enforced on the
runtime correction path instead of only in offline campaign scripts.

The gate is fail-closed. A correction is applied only when every calibration
ratio lies strictly on one side of 1 AND the median bias clears the cap for
the selected ``cap_version``:

- ``"round4-v2"`` (default): inflation applies iff ``b - 1 > 2s``; deflation
  applies iff ``1 - b > 3s and b >= 0.5`` — the sufficient conditions of
  ``capped_inhull_correction_helps_inflation`` / ``_deflation``.
- ``"round3-frozen"``: the registered Round-3 cap ``abs(b - 1) > s``, kept
  for replay compatibility. The Lean theorems explicitly do not
  retroactively license this weaker cap, so it carries no theorem refs.

Correction value contract: the runtime applies the licensed correction
multiplicatively (``pred / b``), exactly like the offline rule; callers must
not reinterpret ``b`` as an additive bias.

Pure functions only — no I/O, no numpy, no runtime session state.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

#: Default cap version: the Round-4 theorem caps.
DEFAULT_CAP_VERSION = "round4-v2"
#: Registered Round-3 frozen cap, retained for replay compatibility.
ROUND3_FROZEN_CAP_VERSION = "round3-frozen"
CAP_VERSIONS = (DEFAULT_CAP_VERSION, ROUND3_FROZEN_CAP_VERSION)

#: Minimum number of calibration ratios required to form a gate decision,
#: matching ``MIN_CALIBRATION_MEMBERS`` in the offline Round-3 analysis.
MIN_CALIBRATION_MEMBERS = 2

ABSTAIN_INSUFFICIENT_CALIBRATION = "insufficient_calibration"
ABSTAIN_DIRECTION = "direction"
ABSTAIN_THEOREM_CAP = "theorem_cap"
ABSTAIN_REASONS = (
    ABSTAIN_INSUFFICIENT_CALIBRATION,
    ABSTAIN_DIRECTION,
    ABSTAIN_THEOREM_CAP,
)

#: Theorem references, named as "<Lean module> <theorem>" for
#: ``lean-spec/LupineEvidence/Shapes/Certificates.lean``.
THEOREM_WRONG_DIRECTION_INFLATION = "Shapes.Certificates wrong_direction_inflation_worsens"
THEOREM_WRONG_DIRECTION_DEFLATION = "Shapes.Certificates wrong_direction_deflation_worsens"
THEOREM_CAPPED_INHULL_INFLATION = "Shapes.Certificates capped_inhull_correction_helps_inflation"
THEOREM_CAPPED_INHULL_DEFLATION = "Shapes.Certificates capped_inhull_correction_helps_deflation"


@dataclass(frozen=True)
class GatedCorrection:
    """One direction-gate decision over a calibration-ratio cell.

    ``theorem_refs`` names the Lean certificates behind an abstention
    (wrong-direction laws for ``direction`` abstains, capped-in-hull laws
    for ``theorem_cap`` abstains under ``round4-v2``); it is empty for
    applied corrections, whose license is evidenced by the cap arithmetic
    (``b``, ``s``) itself, and for ``round3-frozen`` decisions, which
    predate the Round-4 theorems.
    """

    applied: bool
    b: float | None
    s: float | None
    n_calibration: int
    abstain_reason: str | None
    theorem_refs: tuple[str, ...]
    cap_version: str

    def corrected_value(self, pred: float) -> float:
        """Apply the multiplicative contract: ``pred / b`` when licensed.

        Abstentions (and the degenerate zero-bias case, which the Round-4
        caps structurally exclude) return the prediction unchanged.
        """
        if not self.applied or not self.b:
            return pred
        return pred / self.b

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe payload for policy events and diagnostics."""
        return {
            "applied": self.applied,
            "b": self.b,
            "s": self.s,
            "n_calibration": self.n_calibration,
            "abstain_reason": self.abstain_reason,
            "theorem_refs": list(self.theorem_refs),
            "cap_version": self.cap_version,
        }


def _direction_abstain_refs(b: float) -> tuple[str, ...]:
    """Wrong-direction theorem refs, chosen by the sign of the median bias."""
    if b > 1.0:
        return (THEOREM_WRONG_DIRECTION_INFLATION,)
    if b < 1.0:
        return (THEOREM_WRONG_DIRECTION_DEFLATION,)
    return (THEOREM_WRONG_DIRECTION_INFLATION, THEOREM_WRONG_DIRECTION_DEFLATION)


def direction_gated_correction(
    ratios: Sequence[float],
    *,
    cap_version: str = DEFAULT_CAP_VERSION,
    min_members: int = MIN_CALIBRATION_MEMBERS,
) -> GatedCorrection:
    """Evaluate the direction gate over one calibration-ratio cell.

    ``ratios`` are the calibration set's ``pred / ref`` ratios (the offline
    pre-filter applies: null / non-finite / zero references cannot form
    ratios, so non-finite entries are dropped here exactly as the offline
    ``prediction()`` / ``reference()`` helpers drop them).

    Decision order matches the reference implementations:
    insufficient calibration (``n < min_members``) -> direction (ratios not
    strictly one side of 1) -> theorem cap for the selected ``cap_version``.
    """
    if cap_version not in CAP_VERSIONS:
        raise ValueError(f"unsupported direction-gate cap_version: {cap_version}")
    values = [float(ratio) for ratio in ratios if math.isfinite(float(ratio))]
    n = len(values)
    if n < min_members:
        return GatedCorrection(
            applied=False,
            b=None,
            s=None,
            n_calibration=n,
            abstain_reason=ABSTAIN_INSUFFICIENT_CALIBRATION,
            theorem_refs=(),
            cap_version=cap_version,
        )
    b = float(statistics.median(values))
    s = float(max(values) - min(values))
    if all(ratio > 1.0 for ratio in values):
        side = "inflation"
    elif all(ratio < 1.0 for ratio in values):
        side = "deflation"
    else:
        return GatedCorrection(
            applied=False,
            b=b,
            s=s,
            n_calibration=n,
            abstain_reason=ABSTAIN_DIRECTION,
            theorem_refs=_direction_abstain_refs(b),
            cap_version=cap_version,
        )
    if cap_version == ROUND3_FROZEN_CAP_VERSION:
        licensed = abs(b - 1.0) > s
        cap_refs: tuple[str, ...] = ()
    elif side == "inflation":
        licensed = (b - 1.0) > 2.0 * s
        cap_refs = (THEOREM_CAPPED_INHULL_INFLATION,)
    else:
        licensed = (1.0 - b) > 3.0 * s and b >= 0.5
        cap_refs = (THEOREM_CAPPED_INHULL_DEFLATION,)
    if not licensed:
        return GatedCorrection(
            applied=False,
            b=b,
            s=s,
            n_calibration=n,
            abstain_reason=ABSTAIN_THEOREM_CAP,
            theorem_refs=cap_refs,
            cap_version=cap_version,
        )
    return GatedCorrection(
        applied=True,
        b=b,
        s=s,
        n_calibration=n,
        abstain_reason=None,
        theorem_refs=(),
        cap_version=cap_version,
    )
