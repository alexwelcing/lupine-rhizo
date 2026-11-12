# Methodology — How We Know, and How We Catch Ourselves

The reusable core of Lupine is not a result, it is a discipline. Three techniques do
most of the work, and the same techniques are what kill our own bad claims.

## 1. Matched-n comparison

Elements (and potential families) differ in how many potentials exist for them.
Sample size *alone* tightens correlations. So any cross-group correlation is
**confounded by n** until proven otherwise.

The control: down-sample every group to a common n (bootstrap), then compare. A claim
only survives if the effect persists at matched n.

- Killed [d-band](conjectures/dband-correlation.md): full-sample ρ = −0.02; the
  apparent signal was n, not d-band.
- Killed [MEAM-2D](conjectures/meam-intrinsic-2d.md): at matched n = 7, MEAM PR = 1.36
  overlaps Tersoff PR = 1.01.

## 2. Contamination gating

A small fraction of corrupt records can manufacture a dramatic effect. Before
believing any strong result in a noisy corpus, audit the records *driving* it.

- Killed the [BCC/FCC "causal shield"](conjectures/bccfcc-causal-shield.md): the
  r 0.90 vs 0.04 split was 19 corrupt records (~1.5 %). Post-purge: a modest residual,
  no Cauchy relation.
- Now enforced structurally: ingest gate + idempotent purge (see
  [Data & Provenance](data-provenance.md)).

## 3. Ecological-fallacy / stratified evaluation

Correlations pooled across heterogeneous groups can invert when a confounder
(element identity) is ignored — Simpson's paradox / Robinson's ecological fallacy.
Correct analysis requires stratified evaluation and random-effects meta-analysis
(DerSimonian–Laird), not naive pooling.

- Withdrew a pooled "1.8× gate efficacy": it was a class-composition artifact. Within
  classes the gate refused the most accurate high-entropy alloy and the known-good
  control, and the perovskite difference was small (10.08% issued vs 11.28% refused)
  ([errata #3](plans/2026-07-13-errata-and-red-team-dispositions.md)).
- Withdrew our own Simpson's-paradox claim for BCC elastic constants: the reversal was
  shown only on a synthetic example, and on the recorded NIST data the pooled and
  within-element correlations do not reverse sign (Lean-checked computation). The
  causal-graph argument is a stated conjecture, not a proof
  ([formal proof ledger](formal-proof-ledger.md)).
- Random-effects pooling of correlation coefficients assumes independent groups. The
  Fisher-z random-effects intervals we once built on dependent C11/C12/C44 rows were
  anti-conservative and are no longer reported as inference
  ([TMS proceedings manuscript](../paper/tms2027-proceedings/manuscript.tex)).

## 4. Amendments after results

Our rule: an amendment written after any outcome has been seen is labelled
outcome-dependent, and the original gate's verdict is reported next to the amended
one. Example: the Z1 sparse-DFT pilot's
[amendment 01](plans/2026-07-21-sparse-dft-pilot-amendment-01.md) moved the primary
gate to a same-engine basis after path 7 failed the original gate; the
[ledger](conjectures/ledger.md) reports the pilot as a same-engine self-consistency
check with the VASP-referenced error beside it.

Human sign-off on an amendment is a commit carrying the owner's `Signed-off-by:`
line or an approving review on the pull request that adds it, not a quoted
conversation (rule from 2026-11-12; amendment 01's approval predates it and is
recorded only as a quoted conversation). The outcome-dependent label applies
whatever the sign-off. See [How we use AI agents and handle data](ai-and-data.md#amendments).

## The stance

Strong results in a noisy corpus deserve **suspicion before celebration**. Every
refuted claim is published with its confounder named (the
[conjecture ledger](conjectures/ledger.md) is the register). A method that catches its
own mistakes is the asset; the surviving claims inherit its credibility.

## Lineage

Sloppy models: Brown & Sethna (2003), Transtrum & Sethna (2011). Ecological fallacy:
Robinson (1950), Bickel et al. (1975). Meta-analysis: DerSimonian & Laird (1986).
Causal inference: Pearl (2014).
