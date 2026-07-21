# Amendment 02 to the Z1 sparse-DFT pilot preregistration

- **Base documents:** `docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md` (frozen), `docs/plans/2026-07-21-sparse-dft-pilot-amendment-01.md`
- **Amendment date:** 2026-07-21
- **Decision basis:** owner-approved revalidate-first sequencing (2026-07-21) and the pre-agreed adoption criterion (|Δbarrier| ≤ 5 meV, one-path revalidation, recorded in the pilot plan and amendment 01 §A4)
- **Evidence:** `data/candidates/z1-convergence-revalidation-path7.json` (sha256 sidecar) — 8 GPAW evaluations on path-7 (mp-770939_10_1_1_0_1) anchors [0,1,2,4], measured 2026-07-21

## A2.1 Verdicts (measured, not simulated)

| Variant | Settings change | Barrier Δ vs frozen | Criterion | Verdict |
|---|---|---|---|---|
| variant-g | kpts (2,2,2) → (1,1,1) Gamma-only | **−4.72 meV** | ≤5 meV | **PASS — adopt** |
| variant-h | h 0.18 → 0.20 | **+0.40 meV** | ≤5 meV | **PASS — adopt** |

Both loosenings are adopted for the Z1 union-anchor campaign on this panel: **kpts=(1,1,1), h=0.20**, all other settings frozen (fd mode, XC=PBE).

## A2.2 Mandatory disclosures (standing line items)

- **variant-g margin is 0.28 meV.** The Gamma barrier delta (−4.72 meV) clears the criterion by a hair. The criterion was frozen before the numbers existed, so adoption stands; the margin is recorded here and must be quoted wherever this amendment is cited.
- **variant-g shift wander is 13.3 meV** across the four anchors (shifts +234.11, +231.85, +229.39, +220.81 meV). The adoption rests on the barrier delta, not on shift uniformity; the wander is a recorded quantity and the T1 wander-gate continues to report per-path wander in every campaign record.
- **variant-h mean shift is −4.33 eV** with wander of only 1.03 meV across anchors — a large, nearly constant absolute-energy offset that cancels in energy differences. This is the second recorded instance (after T1) of the convention-offset pattern: means can be huge; only wander matters for barriers.
- **Frozen receipts remain as the sensitivity record.** Path-7's four frozen anchors (and any future frozen receipts) are not discarded; they are the documented sensitivity study. No barrier verdict ever mixes parameter sets within one profile — the union driver enforces checkpoint params-identity (`params_match`) on resume, assembly, and import.
- **Scope:** this adoption covers the Z1 union campaign on the locked 30-path panel only. A new panel, chemistry family, engine, or functional requires its own one-path revalidation under the same criterion.

## A2.3 What this unlocks (measured)

- variant-g anchor wall-times on path 7: 305–398 s (vs ~45 min frozen) — a ~9× per-anchor speedup; variant-h adds ~40% further reduction on top in combined settings.
- The union campaign (~125 anchors over 23 active paths) moves from ~375 h serial (investment-grade, deferred 2026-07-21) to an estimated ~1–2 days on the local box — **feasible now, without new hardware.**
- The seven deferred ≥159-atom paths remain `waiting` (they were deferred for memory and time at frozen settings; re-assessment under adopted settings is a separate decision, not this amendment).

## A2.4 What does NOT change

- Amendment 01's comparison structure: same-engine gate primary (≤40 meV WIN / ≤15 meV strong), VASP-referenced secondary, T1 wander-gate reported per path.
- No retraining; runtime correction only. The deferred big-7 stay deferred. The frozen-settings full-panel route stays investment-grade as a *comparison basis* — it is no longer the execution plan.
