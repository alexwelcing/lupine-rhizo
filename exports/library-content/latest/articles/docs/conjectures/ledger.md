# The Hypothesis Ledger

Every claim Lupine has seriously tested, where it stands, and *why it moved*. This is
the structured counterpart to the narrative changelog: the changelog tells the story,
the ledger tells the state. Failed, abstained and withdrawn results stay here with
the same prominence as the ones that held.

**Updated 2026-11-11.** This revision adds the registered campaigns that were
missing (Rounds 1, 3, 4 and 5, the Z1 sparse-DFT pilot, Projection Law Round 2,
the classical-to-MLIP transfer test, the stopped 128-group study and two withdrawn
claims), sets the hyper-ribbon row to Open to match its own page, and replaces a
citation of a Lean theorem name that does not exist (`noSimpsonsInBccEam`) with the
one that does. Nothing listed here has been peer-reviewed.

## Status legend

| Status | Meaning |
|--------|---------|
| **Supported** | Survives the strongest test we have applied so far, within its stated scope. |
| **Open** | Live; evidence is partial, mixed, descriptive or same-engine only. |
| **Failed** | A gate written in advance was not met. |
| **Abstained** | The registered rule declined to issue a verdict (for example, no model had the required physics, or a direction gate did not pass). |
| **Refuted by us** | We tried to confirm it and the effect did not survive a fair test. The confounder is named. |
| **Self-corrected** | We *announced* something, then found our own error and retracted it. |
| **Withdrawn** | We stopped claiming it, or relabelled it as not evidence. |

**Lean-checked arithmetic** is a badge, never a status: Lean 4 checks the
arithmetic and stated inequalities behind published numbers; it does not check the
physics, the reference data or the pipeline. A Lean check on its own does not move an
empirical claim beyond Open.

An amendment written after any outcome was seen is labelled outcome-dependent, and the
original gate's verdict is reported next to the amended one.

## Registered campaigns and preregistered tests

| Campaign / test | Status | One-line resolution | Record |
|------------|--------|---------------------|--------|
| Round 1: cross-class de-bias correction, 2 groups | **Failed** | Failed both groups; alloys moved significantly in the wrong direction (p = 3.1×10⁻⁵). | [manuscript, Appendix A](../../paper/gates-licenses-paper/manuscript.md) |
| Round 2: direction-gated in-class correction rule | **Withdrawn** | The rule was chosen after Round 1 failed and scored on the same candidates; relabelled exploratory rule selection, not evidence (errata #1). | [errata](../plans/2026-07-13-errata-and-red-team-dispositions.md) |
| Pooled "1.8× gate efficacy" | **Withdrawn** | A class-composition (Simpson's) artifact: within class, the gate refused the most accurate HEA and the known-good control (errata #3). | [errata](../plans/2026-07-13-errata-and-red-team-dispositions.md) |
| Round 3: frozen-rule correction, rocksalt ionics and perovskites, out-of-sample | **Failed · registered kill triggered** | Both groups failed (1 of 5 properties won in each, a0 only). The registered kill narrowed the public correction scope to same-class lattice constants (2026-07-13). Round 4 did not replicate the a0 result (see the Round 4 lattice- and elastic-constant row). | [Round-3 report](../../data/candidates/round3/ROUND3_REPORT.md) |
| Round 4 Z1: four foundation MLIPs predict Li-ion migration barriers within 40 meV | **Failed** (2026-07-19) | On a 30-path panel, MACE-MP-0 small and medium, MACE-MPA-0 medium and CHGNet missed the gate (MAE 135.0–242.5 meV on completed paths); unchanged at float64. Sign imbalance is model-dependent (mace-mp-small 17 of 26 negative), not universal. | [Z1 results](../validation/z1-barrier-campaign-round4-results.md) |
| Round 4: lattice- and elastic-constant correction on rocksalt ionics and perovskites (ratio rule, theorem cap) | **Failed** | Ionics 0/4 confirmatory properties; perovskites 0/1 after a post-measurement amendment moved perovskite elastic constants to exploratory. The analysis tool was also written after the measurements existed. a0 did not reach significance under this rule (ionics 5 improved, 2 worsened, p = 0.45; perovskites 4/0, p = 0.125). Separate from the cubic-metal elastic result below. | [Round-4 report](../../data/candidates/round4/ROUND4_REPORT.md) · [amendment](../plans/2026-07-19-round4-preregistration-amendment.md) |
| Round 4 Z3: Δ-correction brings catalyst adsorption energies within 0.1 eV | **Failed** | Every validation-selected correction made holdout error worse (CHGNet 0.69 → 2.27 eV; corrected holdout MAE 2.27–5.91 eV). | [Z3 results](../validation/z3-adsorption-delta-campaign-round4-results.md) |
| Round 4 Z2: magnetocrystalline-anisotropy ranking | **Abstained** | No declared model had the spin-orbit-resolved physics the test needed; scalar-energy rows abstain by the frozen rule. Scope was set to abstention by owner decision on 2026-07-19 before any scientific execution (zero cloud runs); the four rows replay the frozen abstention rule. A separate spin-orbit/Tc campaign is prepared but not run. | [Z2 audit](../campaigns/z2-abstention-audit.md) |
| Z1 sparse-DFT union-anchor pilot (23 of 30 paths; 7 large paths deferred) | **Open · same-engine only** | Sparse anchors matched dense GPAW profiles within the same engine (0.0–6.8 meV), but against the published VASP references the MAE was 693.0–705.7 meV. Amendment 01 moved the primary gate to the same-engine basis after path 7 had failed the original 40 meV VASP-referenced gate (118.8 meV); this is outcome-dependent. On paths of 7 or fewer images, sparse is nearly dense by construction. | [verdict](../analysis/z1-union-campaign-verdict.md) · [amendment 01](../plans/2026-07-21-sparse-dft-pilot-amendment-01.md) |
| Round 5 Z1: direction-gated barrier correction | **Abstained** | All four models abstained at the direction gate; no correction was applied. | [score](../../data/candidates/z1r5/correction-score.json) · [preregistration](../plans/2026-07-20-round5-z1-correction-preregistration.md) |
| Projection Law June experiments: MatPES 4×2 factorial and ACWF DFT-implementation test | **Failed** (4 of 7 registered predictions: 2 of 4 MatPES, 2 of 3 ACWF) · refutation conditions not triggered | MatPES: clustering by functional S_func = +0.317 vs by architecture S_arch = −0.093, permutation p = 0.029; this was not reproduced by the later Round-2 test below. ACWF: S_table = +0.526 vs S_code = +0.265, p = 0.017; the two failed predictions were auxiliary. | [ProjectionLaw_Round2.md §4.1, §5](https://github.com/alexwelcing/lupine/blob/main/paper2/ProjectionLaw_Round2.md) |
| Projection Law Round 2 (3×3×3, 4 MatPES labels × PBE/approximate r2SCAN, 16 cubic metals, DFT targets) | **Failed** (H1 and H2a kill conditions triggered) | 3d/4d functional-clustering effect −0.14, permutation p = 0.13; H2b cosine 0.53 against a registered 0.8; H4 conformal coverage 86.7% against a registered 90% (MAE/MSE passed); H3 pending. QET and TensorNet are closely related TensorNet-family models, and the four MatPES models share training data, so they are not four independent architectures. | [ProjectionLaw_Round2.md §4.2](https://github.com/alexwelcing/lupine/blob/main/paper2/ProjectionLaw_Round2.md) · [TMS manuscript](../../paper/tms2027-proceedings/manuscript.tex) |
| Classical alignment predicts foundation-MLIP alignment | **Refuted by us** | After Born screening, per-element orderings are unrelated (Spearman ρ = 0.26, p = 0.34, 15 elements). | [TMS manuscript §4](../../paper/tms2027-proceedings/manuscript.tex) |
| Cubic-metal elastic bias direction (16 metals, four MatPES labels, 128 cases) | **Open** | One bias direction per functional transfers out of sample, but only when the held-out reference sets how far to correct: 17.84 → 10.36 GPa is an oracle ceiling, not a deployable correction. The best no-target estimator (consensus, 14.41 GPa) harmed 50 of 128 cases. r2SCAN targets are approximate (scalar shifts of PBE). | [layer-2 paper](../../paper/lupine-layer2-3x3x3-final-paper.md) · [ProjectionLaw_Round2.md](https://github.com/alexwelcing/lupine/blob/main/paper2/ProjectionLaw_Round2.md) |
| Small cell (1×1×1) matches 3×3×3 for elastic constants; global LOO-PCA correction | **Supported** (cell size) · **Failed** (correction) | TensorNet/PBE 1×1×1 matched 3×3×3 (14.55 vs 14.61 GPa MAE); the global correction made it worse (63.40 GPa). | [preprint](../../mlip-elastic-benchmark/mlip-elastic-benchmark-preprint-2026-06-27.md) |
| Proposed 128-group MPtrj ranking study | **Abstained** (stopped before execution) | The source audit did not establish that candidate rows were independent of the checkpoints' training data, so the study stopped under its own rule. | [stop record](../research-progress/2026-10-06-roster-readiness.md) |

## Error-geometry hypotheses

| Hypothesis | Status | One-line resolution |
|------------|--------|---------------------|
| Hyper-ribbon universality (classical potentials) | **Open** | Descriptive only. Historical counts are not re-verified ("559 potentials" are 559 model–element tensors with 423 distinct KIM ids); low participation ratios are partly rank-limited; universality and correction value unproven. The Lean item compares a hard-coded constant (0.398 < 0.5) — Lean-checked arithmetic, not evidence. → [page](hyper-ribbon-universality.md) · [count audit](../plans/2026-09-09-tms-manuscript-sprint.md) |
| Hyper-ribbon transfers classical → MLIP | **Open** (re-audit 2026-06-11) | The pre-screening "14 of 15" count is retired. Born screening excludes 7/45 foundation-model tensors; directional structure remains at n = 8–11 models (rank-1 share 0.56–0.94), but classical alignment does not predict MLIP alignment (ρ = 0.26, p = 0.34). → [page](hyper-ribbon-mlip-transfer.md) |
| Projected hyper-ribbon release | Open | New Lean-first release lane: check projected-ribbon gates, then require replay plus cloud evidence before promotion. |
| Cross-MLIP orthogonal error modes | Supported | MACE and CHGNet have orthogonal error directions on Ag/Nb/Pd. |
| Au escapes the ribbon under foundation MLIPs | Open | Confirmed for MACE+CHGNet; Ag escape refuted. |
| Fe magnetic MLIP failure mode | Open · under re-audit | The old PR > 2 trio claim is frozen after Born screening excluded CHGNet-Fe; Fe remains a magnetic/mechanical-stability failure-mode target. |
| D-band controls error correlation | **Refuted by us** | Sample-size confounder (full-sample ρ = −0.02). |
| MEAM is intrinsically 2-D | **Refuted by us** | Matched-n bootstrap: MEAM overlaps Tersoff. |
| BCC/FCC "causal shield" | **Self-corrected** | The dramatic r 0.90 vs 0.04 was 1.5 % data contamination. |
| Simpson's paradox in BCC elastic constants | **Withdrawn** | The paradox was demonstrated on a synthetic example (`generate_simpsons_example` in `distill/src/causal.rs`). On the recorded NIST data, pooled and within-element correlations do not reverse sign (`simpsonsDetectedEmpirical` in `Materials/Analysis/Causal.lean`, a `native_decide` computation — Lean-checked arithmetic). The causal-graph argument (`MetaScience.lean`) is a stated conjecture, not a proof. → [formal audit](../formal-audit.md) |

## 2026-06-07 cross-MLIP elastic import

| Hypothesis | Status | One-line resolution |
|------------|--------|---------------------|
| Parameter-basis Vandermonde decay in foundation MLIPs | **Refuted by us** | The 4-model Fisher sweep fails rho >= 1.5; MACE parameter-basis rho is flat while CHGNet/SchNet only reach about rho 0.4. |
| MACE irrep-basis Vandermonde threshold | **Refuted by us** | Irrep coefficients show real geometric decay (rho 0.3865, R2 0.9807), but still fail the pre-registered rho >= 1.5 threshold. |
| Weak-form acceleration/refusal theorem | Open | Scalar weak-form gate now builds in Lean; full Lipschitz/reach formalization and deeper-model runtime evidence remain open. |
| Layerwise distance as MLIP/MD uncertainty signal | Open | Layer-0 distance correlates with force error and helps mixed-reference refusal, but Cu-only reference tuning failed and force-calibrated follow-up is needed. |
| Cross-MLIP elastic run v7 (Cloud Run) | Supported | 45 MACE/CHGNet/SevenNet elastic calculations are preserved; Fe is a MACE-disagreement sentinel, while Ta/V/Pt have the highest 3-MLIP PR values. |

See also:
[MLIP universality import (2026-06-07)](../science/kimi-mlip-universality-import.md) ·
[Cross-MLIP Cloud Experiment Runbook](../runbooks/cross-mlip-cloud-experiment.md).

## Why this shelf exists

The most defensible thing Lupine produces is not a single result — it is a *method that
catches its own mistakes*. The d-band and MEAM refutations and the BCC/FCC
self-correction all came from the same matched-n / contamination-gate discipline, and
the registered campaigns above show the same rule applied to our own corrections:
most of them failed or abstained, and we report them. A corpus you can trust is one
that publishes what it killed.

See also: [Formal Proof Ledger](../formal-proof-ledger.md) ·
[Methodology](../methodology.md) · [Data & Provenance](../data-provenance.md) ·
[How we use AI agents and handle data](../ai-and-data.md).
