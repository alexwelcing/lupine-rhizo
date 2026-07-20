# Plan — Port the proven direction gate into the runtime correction session (H3)

**Date:** 2026-07-20 · **Status:** design approved by director · **Origin:** synthesis hypothesis H3 (`lit-review/synthesis-mlip-correction-2026-07-20.md`) + owner directive (improve speed and accuracy by enforcing the theorem system at runtime)

## Problem

The proven correction gate — direction gate (all calibration ratios strictly one side of 1), spread cap (`abs(b-1) > s` where `s = max-min`), and the Round-4 theorem caps (inflation `b-1 > 2s`; deflation `1-b > 3s AND b ≥ 0.5`) — lives only in offline campaign scripts (`python/scripts/run_round3_analysis.py:278-334`, `tools/round4_cloud_campaign.py:370-376`). What actually runs at runtime (`python/lupine_distill_runtime/session.py::DistillSupportModel.fit`, lines 426-621) computes **un-gated additive mean biases** checked only by magnitude caps and a ≥2% lift rule. The Lean laws (`LupineEvidence/Shapes/Certificates.lean`: `wrong_direction_*`, `capped_inhull_correction_helps_*`) are therefore not enforced on the runtime path.

## Scope H3a — direction-gated runtime corrections

1. **New module `python/lupine_distill_runtime/direction_gate.py`** (pure, no I/O):
   - `GatedCorrection` dataclass: `applied: bool`, `b: float|None`, `s: float|None`, `n_calibration: int`, `abstain_reason: str|None`, `theorem_refs: tuple[str, ...]`, `cap_version: str`.
   - `direction_gated_correction(ratios: Sequence[float], *, cap_version: str = "round4-v2", min_members: int = 2) -> GatedCorrection` implementing exactly the frozen rule + theorem caps:
     - `n < min_members` → abstain `insufficient_calibration`
     - not one-side → abstain `direction` (theorem_refs += wrong_direction_inflation_worsens / _deflation_worsens by sign of median)
     - round4-v2 caps: inflation applies iff `b-1 > 2s`; deflation applies iff `1-b > 3s and b ≥ 0.5`; else abstain `theorem_cap` (theorem_refs += capped_inhull_correction_helps_inflation / _deflation)
     - round3-frozen cap retained as an option (`abs(b-1) > s`) for replay compatibility — but default round4-v2
   - Correction value contract: runtime applies multiplicatively (`pred / b`) like the offline rule; callers must not reinterpret as additive bias.
2. **Class-aware support fitting** in `session.py::DistillSupportModel.fit`:
   - Read optional `class`/`group` label per support structure (default: single implicit class — behavior identical to today when no labels exist).
   - For each row, group support structures by (row property, class); compute calibration ratios per cell; feed `direction_gated_correction`; apply when `applied` else abstain and record the reason.
   - Event recording: every abstain/apply emits a policy event carrying `abstain_reason`, `b`, `s`, `n_calibration`, and `theorem_refs` (these flow into `distill_events.jsonl` and the artifact's `distill` block exactly like existing skip/refusal actions).
   - Back-compat: no class labels anywhere ⇒ identical outputs to current code (pinned by existing tests).
3. **Do NOT change**: Lean files (the laws already exist), the offline campaign scripts (they are the reference implementation — the port must match them), the barrier row's distill refusal (Z1 correction is H1/Round-5 work).

## Scope H3b — overhead instrumentation

1. `session.py`: `perf_counter` spans around `fit_support`, correction application, and guard/gate evaluation; expose as `session.overhead` dict `{support_fit_s, correction_s, guards_s}`; surface in `distill_runtime.summary` and the runner artifact.
2. Feed `theorem_hooks` a real baseline when available (runner records `raw_duration_s` for the same cell with distill off during A/B runs); stop shipping `observed_speedup: None` silently — emit `null` with a `reason` when no baseline exists.

## Acceptance

- `pytest python/tests gcp/mlip-cell-runner` green, including new tests: golden replications of the proven offline gate decisions on Round-3/4 fixtures (same apply/abstain outcomes), abstention event payloads, back-compat with unlabeled support sets, cap-version selection, overhead keys present in the artifact.
- `lake build` untouched and green (no Lean edits).
- Zero sorry / zero new axioms (unchanged by construction).
- PR body maps each acceptance item to evidence.

## Non-goals (explicit)

- Z1 scalar pilot (H1) and Z3 active-Δ (H2): Round-5 preregistration items, sequenced after this port.
- Applying ribbon corrections in the Python engine (still candidate-only; separate registered work).
