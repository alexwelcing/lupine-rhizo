# Prediction-hull membership vs correction success — EXPLORATORY

> **Label:** EXPLORATORY. No new measurements; existing Round-1/2/3
> artifacts only. Does not amend any frozen registration.
> Generated 2026-07-13T17:44:06.335272+00:00 by
> `python/scripts/analyze_prediction_hull.py`.

## Hypothesis

The proven capped in-hull correction theorems license a correction
only under an in-hull hypothesis on the target's true ratio
r = pred/ref — unknowable at runtime. Tested here: whether a
KNOWABLE cross-model prediction hull is a usable proxy for it, on
cells where the frozen Round-3 rule APPLIED.

- **(c) proxy (knowable):** model m's raw prediction inside the
  other models' raw-prediction hull for the same candidate/property.
- **(c2) variant (knowable):** m's LOO-bias-corrected prediction
  inside that same cross-model raw-prediction hull.
- **(d) oracle (unknowable):** true ratio r inside m's LOO
  calibration ratio hull — the theorems' hypothesis; upper bound.
- **Outcome:** success iff |corrected err| < |raw err|.

## Round-3 cells (PRIMARY): proxy (c) — raw prediction in hull

| scope | in&succ | in&fail | out&succ | out&fail | succ-rate in | succ-rate out | Fisher p |
|---|---|---|---|---|---|---|---|
| pooled | 17 | 6 | 19 | 7 | 74% | 73% | 1 |
| a0 | 16 | 0 | 16 | 0 | 100% | 100% | 1 |
| b0 | 0 | 3 | 0 | 2 | 0% | 0% | 1 |
| c11 | 1 | 2 | 0 | 3 | 33% | 0% | 1 |
| c12 | 0 | 1 | 0 | 1 | 0% | 0% | 1 |
| c44 | 0 | 0 | 3 | 1 | - | 75% | 1 |

## Round-3 cells: variant (c2) — corrected prediction in hull

| scope | in&succ | in&fail | out&succ | out&fail | succ-rate in | succ-rate out | Fisher p |
|---|---|---|---|---|---|---|---|
| pooled | 1 | 2 | 35 | 11 | 33% | 76% | 0.1679 |
| a0 | 0 | 0 | 32 | 0 | - | 100% | 1 |
| b0 | 0 | 0 | 0 | 5 | - | 0% | 1 |
| c11 | 0 | 2 | 1 | 3 | 0% | 25% | 1 |
| c12 | 0 | 0 | 0 | 2 | - | 0% | 1 |
| c44 | 1 | 0 | 2 | 1 | 100% | 67% | 1 |

## Round-3 cells: oracle (d) — true ratio in calibration hull

| scope | in&succ | in&fail | out&succ | out&fail | succ-rate in | succ-rate out | Fisher p |
|---|---|---|---|---|---|---|---|
| pooled | 17 | 1 | 19 | 12 | 94% | 61% | 0.01709 |
| a0 | 16 | 0 | 16 | 0 | 100% | 100% | 1 |
| b0 | 0 | 1 | 0 | 4 | 0% | 0% | 1 |
| c11 | 1 | 0 | 0 | 5 | 100% | 0% | 0.1667 |
| c12 | 0 | 0 | 0 | 2 | - | 0% | 1 |
| c44 | 0 | 0 | 3 | 1 | - | 75% | 1 |

## Round-1/2 cells (SECONDARY, same frozen rule re-applied)

### proxy (c)

| scope | in&succ | in&fail | out&succ | out&fail | succ-rate in | succ-rate out | Fisher p |
|---|---|---|---|---|---|---|---|
| pooled | 16 | 1 | 19 | 3 | 94% | 86% | 0.618 |
| a0 | 16 | 0 | 12 | 0 | 100% | 100% | 1 |
| c11 | 0 | 0 | 5 | 0 | - | 100% | 1 |
| c44 | 0 | 1 | 2 | 3 | 0% | 40% | 1 |

### oracle (d)

| scope | in&succ | in&fail | out&succ | out&fail | succ-rate in | succ-rate out | Fisher p |
|---|---|---|---|---|---|---|---|
| pooled | 19 | 1 | 16 | 3 | 95% | 84% | 0.3416 |
| a0 | 14 | 0 | 14 | 0 | 100% | 100% | 1 |
| c11 | 3 | 0 | 2 | 0 | 100% | 100% | 1 |
| c44 | 2 | 1 | 0 | 3 | 67% | 0% | 0.4 |

## Reading

- Round-3 proxy (c), pooled: in-hull 17/23 success vs out-of-hull 19/26; Fisher p = 1.
- Round-3 variant (c2), pooled: in-hull 1/3 success vs out-of-hull 35/46; Fisher p = 0.1679.
- Round-3 oracle (d), pooled: in-hull 17/18 success vs out-of-hull 19/31; Fisher p = 0.01709.
- Round-1/2 proxy (c), pooled: in-hull 16/17 success vs out-of-hull 19/22; Fisher p = 0.618.
- Round-1/2 oracle (d), pooled: in-hull 19/20 success vs out-of-hull 16/19; Fisher p = 0.3416.

## Round-4 cap preview (informative only)

- Round-3: 20/49 applied cells keep their license under the proven caps (32 inflation-side, 17 deflation-side applied cells); licensed cells: 18 success / 2 failure. Theorem consistency: licensed & oracle-in-hull 5 success / 0 failure (the theorems guarantee 0 failures here); licensed & out-of-hull 13 / 2 (no guarantee).
- Round-1/2: 18/39 applied cells keep their license under the proven caps (16 inflation-side, 23 deflation-side applied cells); licensed cells: 18 success / 0 failure. Theorem consistency: licensed & oracle-in-hull 7 success / 0 failure (the theorems guarantee 0 failures here); licensed & out-of-hull 11 / 0 (no guarantee).

## Honesty boundary

Exploratory, small n, cells within a group share calibration members
and are not independent; Fisher p-values are descriptive screening
numbers, not confirmatory claims. Pooled tables mix properties with
very different base rates (every applied a0 cell succeeds regardless
of hull status, so a0 contributes no within-property association and
the pooled oracle signal is carried by the property mix plus the
elastic-property cells — see the per-property rows before quoting
any pooled p). Any use of the proxy must be registered before
Round-4 data exists (it was not — see the Round-4 preregistration,
which registers the caps alone and records this null).
