# Errata and red-team dispositions — 2026-07-13 session artifacts

> **Status:** Accepted findings from an adversarial internal review (hostile-referee
> pass over all 2026-07-13 artifacts). Each finding is recorded with its
> disposition. Corrections that require new computation are REGISTERED in the
> Round-3 preregistration rather than silently patched.

## Accepted as stated (claims corrected)

1. **Round 2 was post-hoc rule selection, not a preregistered trial.**
   `run_round2_corrections.py` chose the sign-gate rule, LOO-median estimator,
   and min-members=2 AFTER seeing Round 1 fail, and evaluated on the same 9
   candidates. Disposition: Round 2 is RELABELED "exploratory rule selection."
   The rule is frozen verbatim in the Round-3 prereg and will be evaluated on
   out-of-sample candidates only.

2. **The Lean layer does not license the implemented gate.**
   `wrong_direction_*_worsens` requires the TARGET's error side as hypothesis;
   the code checks only that LOO classmates share a side. Counterexample inside
   our own data: FeNi B0 / mace-mp-small (pred 143.1 < ref 176.7) received a
   deflation licensed by three classmates' unanimous >1 ratios — the exact
   scenario the theorem forbids — and the sign-gated arm is worse than raw on
   both B0 rows. Disposition: the claim is corrected to "the gate excludes one
   failure mode on calibration members"; `theorem_basis` wording retracted in
   errata; Round-3 registers (a) a magnitude cap (abstain when |bias-1| exceeds
   the LOO ratio spread) and (b) a Lean theorem matching what is implemented,
   or no theorem language at all.

3. **"Gate efficacy 1.8x" is a class-composition (Simpson's) artifact.**
   Within class: HEA issued 4.31% vs refused 1.81% (the gate refused the MOST
   accurate HEA); perovskites 10.08% vs 11.28%. The known-good control
   (CsPbI3) was refused — a 1/1 control false-refusal. Disposition: the pooled
   1.8x claim is WITHDRAWN. Risk-coverage will be reported within-class only,
   with control refusals tabulated as false positives.

4. **fcc B0 dispersion is anti-correlated with error (rho = -0.63, n=9).**
   No B0 concordance verdict (v1 or v2 era) carries uncertainty content;
   Li2S's b0 FLAG is descriptive arithmetic only. LiS's REFUSED verdict
   survives independently on Born (all four models C44 < 0) — that is the
   load-bearing evidence. Disposition: B0 concordance demoted to descriptive
   program-wide; only Born (exact physics) and bcc a0 (rho 0.89, still n=7)
   currently carry any empirical dispersion-error license.

5. **Prereg-excluded cells appeared in headline tables.** CsSnI3 Cij (weak
   1.22 GPa C12 reference => 260-435% cell errors dominating the c12 median)
   and CsGeI3 a0 were excluded by prereg S4 but included in both rounds' arm
   tables. Disposition: Round-1/2 arm tables to be regenerated with exclusions
   applied and absolute-GPa deltas alongside; until then the perovskite c12
   improvement claim is withdrawn.

6. **thresholds.v3 perovskite class is circular** (calibration corpus = the
   gated candidates; rho=1.0 license computed on the same 5 compounds).
   Disposition: perovskite class marked provisional/in-sample; no perovskite
   claim gates on v3 until an out-of-sample perovskite corpus exists.

7. **The relative-dispersion metric is undefined at sign-crossing medians.**
   V's C44 (cross-model median ~0) produces dispersion 237.7 and a bcc refuse
   threshold of 167.6 that can never fire; v2's global c44 refuse inherits the
   same cell. Disposition: registered metric fix — denominator floor or
   absolute-spread normalization for C44-like properties; v2/v3 regeneration
   under the fixed metric is a Round-3 deliverable; V/Cr audited as
   calibration cells.

8. **Round-1's preregistered primary statistic was never computed**, and the
   Cij bias arm silently failed to load (criterion degraded 2-of-3 -> 2-of-2).
   Disposition: a criteria-evaluation script will append the honest PASS/FAIL
   per group to Round-1's report ("HEA: criteria FAILED" expected).

9. **Round-2 a0 gains partly absorb reference conventions** (high-T lattice
   references vs athermal predictions; Vegard-estimate and tetrataenite-
   caveated references in HEA). Disposition: a0 corrections to be decomposed
   into published thermal-expansion offset + residual model bias; per-material
   n reported instead of per-cell n.

10. **The 60-346x defect-vs-bulk dispersion ratio is a normalization
    artifact.** Energy-difference dispersions are not commensurable with
    length dispersions; the defensible statements are the absolute spreads
    (0.5-1.8 eV) and the vs-B0/vs-C11 ratios (2-34x / 0.8-8.5x). The 346x cell
    is driven by a physically suspect negative E_vac that should be flagged
    invalid, not pooled; Sn rows are n=3 MACE-family-only. Disposition:
    headline restated in absolute terms; negative-E_vac cells flagged; the
    vs-a0 column footnoted as non-commensurable.

11. **Barrier panel is single-supercell and finite-size error is common-mode**
    (invisible to dispersion by construction); only neutral PBE NEB values are
    convention-consistent comparators. Disposition: Round-3 registers one
    3x3x3 scaling point per compound (one model) before any kinetics
    threshold derivation; experimental dH_m comparisons framed as
    trend/ordering, PBE-NEB as the absolute anchor (LiF: 0.66-0.73 eV vs our
    MACE 0.59-0.68).

12. **asym = 0.0000 is a builder symmetry identity, not convergence
    evidence**; a real convergence defect (LiI/mace-mp-medium image below
    endpoint by ~3 meV) went unflagged. Disposition: replace the asymmetry
    check with endpoint-vs-band-minimum and a symmetry-breaking perturbation
    check (registered code fix).

## What survives untouched

- Round 1's kill of the cross-class correction (honest, preregistered).
- All Born-based refusals (exact physics, no calibration dependency).
- The threshold-migration arithmetic certificates (they certify arithmetic,
  and say so).
- The Schottky panel's referenced finding: all models underestimate pair
  formation 40-105% while preserving the halide-series ordering (absolute-eV
  claim, conductivity-derived anchors, conventions stated).
- The barrier panel's MACE-vs-PBE-NEB agreement on LiF (0.59-0.68 vs
  0.66-0.73 eV) and the 0.13-0.20 eV cross-model spreads as ABSOLUTE numbers.
- The early-stop wall-time result (verdicts identical by construction).
- The instrument itself: determinism, provenance, same-probe calibration.

*The strongest artifact of the day remains Round 1: preregistered, failed,
and reported as failed. The damage concentrated where claims outran their
licenses; the licenses, not the claims, are what Round 3 fixes.*
