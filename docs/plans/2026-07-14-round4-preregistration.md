# Round-4 preregistration — theorem-capped corrections, out-of-sample

> **Status:** DRAFT FOR REGISTRATION 2026-07-14, before any Round-4
> measurement or reference sourcing for the evaluation set. Frozen at
> registration; changes after evaluation data exists void the registration.
> **Prior state:** Round 3 (preregistered, frozen 1s cap:
> `2026-07-13-round3-preregistration.md`) FAILED both groups under its
> registered 2/3 criterion (a0 WIN in both groups; elastic properties
> WORSE or NO-CHANGE — `data/candidates/round3/ROUND3_REPORT.md`), so the
> registered KILL condition TRIGGERED and the correction layer's public
> scope claim is currently "same-class lattice constants only". Round 4 is
> the registered new-evidence path out of that narrowed scope. Also prior:
> the EXPLORATORY prediction-hull analysis
> (`data/candidates/round3/prediction_hull_analysis.json`,
> `PREDICTION_HULL_ANALYSIS.md`) whose null is recorded in §4 below.
> Round-3 results remain governed by Round-3's own frozen registration;
> nothing here re-reads them.

## 1. Registered rule change: the PROVEN caps replace the 1s cap

Basis: the machine-checked capped in-hull correction laws in
`lean-spec/LupineEvidence/Shapes/Certificates.lean` (0 sorry). Quantities in
the Lean statements are ratios x10000 (10000 = ratio 1); `lo`/`hi` are the
calibration ratio hull, `b` the median bias, `s = hi - lo` the spread, `r`
the target's true ratio pred/ref. Quoted exactly:

```lean
theorem capped_inhull_correction_helps_inflation
    (lo hi s b r : Int) (hs : s = hi - lo)
    (_hlo : 10000 < lo) (hle : lo ≤ hi)
    (hb1 : lo ≤ b) (hb2 : b ≤ hi)
    (hr1 : lo ≤ r) (hr2 : r ≤ hi)
    (hcap : 2 * s < b - 10000) :
    ((r - b).natAbs : Int) * 10000 < ((r - 10000).natAbs : Int) * b
```

```lean
theorem capped_inhull_correction_helps_deflation
    (lo hi s b r : Int) (hs : s = hi - lo)
    (_hlo : 0 < lo) (_hle : lo ≤ hi) (_hhi : hi < 10000)
    (hb1 : lo ≤ b) (hb2 : b ≤ hi)
    (hr1 : lo ≤ r) (hr2 : r ≤ hi)
    (hfloor : 5000 ≤ b)
    (hcap : 3 * s < 10000 - b) :
    ((r - b).natAbs : Int) * 10000 < ((r - 10000).natAbs : Int) * b
```

The conclusion `|r - b| * 10000 < |r - 10000| * b` is the division-free form
of `|r/b - 1| < |r - 1|`: the corrected prediction is strictly closer to the
reference. The asymmetry is derived, not assumed: inflation needs the bias
above TWO spreads (`2 * s < b - 10000`, i.e. b - 1 > 2s); deflation needs
THREE spreads AND the floor (`3 * s < 10000 - b` with `5000 ≤ b`, i.e.
1 - b > 3s and b >= 0.5), because deflation divides by b < 1 and amplifies
the same |r - b|.

## 2. Frozen Round-4 correction rule (v2)

For a held-out candidate X, model m, property p, class C:

1. Calibration set = other class-C members with a non-null reference
   (never X). Require >= 2 members, else ABSTAIN.
2. ratios_i = pred_i / ref_i over calibration members.
3. Direction gate: apply only if ALL ratios are strictly on one side of 1,
   else ABSTAIN.
4. **Registered theorem caps (replace Round-3's |b - 1| > s):** let
   b = median(ratios), s = max(ratios) - min(ratios).
   - Inflation side (all ratios > 1): apply only if **b - 1 > 2s**.
   - Deflation side (all ratios < 1): apply only if **1 - b > 3s AND
     b >= 0.5**.
   Else ABSTAIN (reason: `theorem_cap`).
5. corrected = pred / b; else corrected = pred (abstention, risk-free).

Steps 1-3 and 5 are verbatim from the Round-3 frozen rule; only step 4
changes, to the exact caps the theorems prove sufficient. Strictness of the
inequalities matches the Lean hypotheses.

**Honesty boundary carried in the rule itself:** the theorems' remaining
hypothesis — the target ratio r inside the calibration hull [lo, hi] — is
NOT runtime-checkable (r needs the reference). A Round-4 application is
therefore "licensed under the caps, conditional on the in-hull hypothesis",
never an unconditional guarantee. The exploratory analysis quantifies the
residual risk: on Round-3 applied cells, cap-licensed & oracle-in-hull cells
went 5/5 success (theorem-guaranteed), cap-licensed & out-of-hull went 13/15
(no guarantee); Round-1/2: 7/7 and 11/11.

## 3. Primary statistic and criteria (unchanged machinery, computed)

- Per group x property (references non-null): median |rel err| raw vs
  corrected over evaluable held-out cells; exact binomial sign test over
  cells where the rule APPLIED (ties dropped); alpha = 0.1.
- SUCCESS per group: corrected beats raw on >= 2/3 evaluable properties
  with sign-test p < 0.1. FAILURE otherwise, reported verbatim.
- Registered secondary (risk profile, new): count of applied-and-worsened
  cells per group ("licensed failures"). The caps are stricter than
  Round-3's, so application counts will drop (preview on Round-3 cells:
  20/49 applications survive, 18 success / 2 failure vs 36/13 under the 1s
  cap); the registered trade is fewer corrections for a cleaner risk
  profile, and it is evaluated by this count, not asserted.
- Registered theorem-consistency check (post-hoc, once references exist):
  cells that were cap-licensed AND turn out oracle-in-hull must show ZERO
  worsened cells; any violation is reported verbatim as an implementation
  or reference defect (the theorems admit no exception).
- KILL condition: the scope claim is ALREADY narrowed to "same-class
  lattice constants only" by Round-3's triggered KILL. Round 4 can only
  widen it: each group x property that WINS under the v2 rule re-enters the
  claimable scope. If the v2 rule fails both groups again, the narrowed
  scope becomes the program's standing claim and the correction layer is
  frozen (no further cap-tuning rounds without a new proven theorem).

## 4. Prediction-hull proxy: registered NULL, no confirmatory test

Pre-stated decision rule (task order, 2026-07-13): IF the exploratory hull
proxy showed signal, register a confirmatory test of it on Round-4 data;
if no signal, register the caps alone and record the null. Result — NO
SIGNAL; the caps stand alone. Recorded numbers (EXPLORATORY, Fisher exact,
two-sided, pooled over applied cells;
`data/candidates/round3/prediction_hull_analysis.json`):

- **(c) KNOWABLE proxy** (m's raw prediction inside the other models'
  raw-prediction hull), Round-3 primary: in-hull 17/23 success vs
  out-of-hull 19/26 — success rates 73.9% vs 73.1%, **p = 1.0**. Round-1/2
  secondary: 16/17 vs 19/22, p = 0.618. The cross-model prediction hull
  carries no information about correction success.
- **(c2) variant** (LOO-corrected prediction inside that hull), Round-3:
  1/3 vs 35/46, p = 0.168 — direction REVERSED (staying in the raw hull
  after correction weakly co-occurs with failure), n_in = 3; not signal.
- **(d) UNKNOWABLE oracle** (true ratio r inside the calibration ratio
  hull — the theorems' hypothesis), Round-3: in-hull 17/18 success vs
  out-of-hull 19/31 — 94.4% vs 61.3%, **p = 0.0171**; Round-1/2: 19/20 vs
  16/19, p = 0.342 (ceiling: 90% base success rate). The condition that
  predicts success is exactly the one the theorems name, and it is not
  observable at runtime.

Consequence, registered: Round-4 does NOT gate on any cross-model
prediction-hull proxy, and no such gate may be added after Round-4 data
exists. The oracle association is recorded as motivation for the caps'
conditional reading (§2), not as a runtime instrument.

## 5. Evaluation set discipline

- New out-of-sample candidates in >= 2 classes, never used in any
  calibration; the locked candidate list is appended to this document as a
  dated addendum BEFORE any Round-4 model run, and references are sourced
  AFTER the list is locked, under the same provenance discipline as
  Round 3 (weak/null references excluded at registration, recorded
  verbatim).
- Models, properties (a0, B0, C11, C12, C44), and gate instruments carry
  over from Round 3 unchanged; B0 concordance remains descriptive-only
  (errata finding 4).
- Analysis script: `python/scripts/run_round3_analysis.py` extended with
  the v2 cap (step 4) as a registered flag — implementation must be
  committed and tested BEFORE the evaluation set is locked.

## 6. Honesty boundary

n per group remains small; this remains a methodology demonstration, not a
general efficacy claim. The exploratory analysis in §4 used no new
measurements but did read Round-3 outcomes; it therefore cannot license any
Round-3-tuned instrument beyond the theorem caps, whose form comes from the
machine-checked proofs, not from the data.
