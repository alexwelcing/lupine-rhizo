# The Discovery Formalization Protocol — trusted process runs for unproven structures

> Status: lab-visit working protocol, 2026-07-02. Companion to the
> environment-error-field manuscript (validated machinery), the HPC
> visitation lane (`hpc/`), the MOF makeability prospectus
> (lupine.science article), and the certificate claim-shapes
> (`lean-spec/LupineEvidence/Shapes/`).

## The problem a lab actually has

Everything in benchmark culture assumes a reference bank. A lab exploring a
new Li–S phase or an unproven MOF linker has none: the question is not "how
close to the published value" but *what can be trusted about a structure
nobody has made — and how quickly can a bad candidate be killed*. Discovery
compute is dominated by candidates that should never have been run. The
cheapest true statement in materials AI is a fast, justified **no**.

Our machinery was validated on knowns (21 materials, 4 models, 484
reference-bound measurements, everything machine-checked). This protocol is
the same machinery re-based onto what needs **no references at all**, plus
an anchor discipline for what does.

## The gate ladder (refusal-first, cheapest statement first)

Every candidate structure passes through gates in cost order. Each gate
emits a machine-checkable certificate — pass, flag, or refusal — and a
refusal at gate k means gates k+1..n are never paid for.

**Gate 0 — Coverage.** Does the model's training distribution contain
environments like this candidate's? (Li–S: sulfur-rich, polysulfide-like
coordination; MOFs: linker torsions, open-metal sites.) Out-of-coverage
candidates are flagged *before any simulation*. Cost: descriptor
arithmetic, milliseconds.

**Gate 1 — Concordance.** Run the candidate through N foundation models
(seconds each on one GPU). Cross-model dispersion is a measured,
data-derived error bar: we calibrated dispersion-vs-true-error on our
84-cell corpus, so a candidate's dispersion percentile against that
baseline is an honest uncertainty statement with provenance — no DFT
required. Wide disagreement on the property that matters = flag or refuse.

**Gate 2 — Internal invariants.** Physics the prediction must satisfy
regardless of ground truth: Born mechanical stability of the predicted
elastic tensor; positive defect energetics; rattle-and-return dynamical
sanity; symmetry conservation; force/energy self-consistency. A candidate
whose own predicted physics is inconsistent is refused **with the violated
inequality as a decidable certificate**. Cost: seconds to minutes.

**Gate 2½ — Self-consistency (discovered by the Li–S demonstration).** One
model, two routes to the same quantity: the bulk modulus from the stress-
derived elastic tensor must agree with the bulk modulus from the model's own
energy–volume curve. In the first live run this single reference-free check
cleanly separated a stress/energy-inconsistent model (CHGNet, 21–57 %
internal disagreement on the Li–S subjects) from a self-consistent family
(MACE variants, 0.3–0.5 %) — *before* any cross-model or reference
comparison. Cost: already computed by Gate 2's inputs; the check is free.

**Gate 3 — Anchors.** Only survivors earn reference compute: a small number
of DFT calculations (3–8) placed on the *specific chemistry of the use
case* — the number our anchor-efficiency results justify. The anchors fit
the family exponent and, where coordination-resolved, the environment error
field for THIS system class; the corrected model then screens the entire
candidate family at MLIP cost with calibrated error bars.

**Gate 4 — Certificates and the carry-forward.** Every outcome — pass,
kill, and provable impossibility — is sealed as typed, machine-checked
claims (the `Certificates` shapes). The fitted calibration + gates for the
chemistry become a **named gearbox** (e.g. `LiS-cathode-v1`,
`MOF-Zr-linker-v1`): a reusable asset that every subsequent run in that
family starts from, and that accretes anchors and refusal knowledge run
over run. The lab's discovery program compounds instead of restarting.

## Why refusal is the product

Three properties no screening pipeline currently offers:

1. **Refusals carry proofs.** Where a candidate's ranking-inversion or
   coverage gap makes correction impossible, that impossibility is a
   quantified theorem with the candidate's own numbers as witnesses — not
   a heuristic score. (Pattern already live: the monotone-impossibility
   lemma that gates MPtrj stacking-fault corrections.)
2. **Thresholds have provenance.** Concordance limits derive from our
   measured dispersion-error relation, not from taste; the derivation is
   in the artifact and the number is checkable.
3. **The record self-corrects.** Certificates land in the ledger with the
   same lifecycle as all claims — supported, refuted, corrected, open —
   so a gate that mis-fires becomes a documented correction, not folklore.

## Use-case notes

**Li–S.** The hard unknowns are sulfur-rich: polysulfide speciation,
lithiation pathways, cathode-phase stability. MPtrj-era coverage of S-rich
environments is thin, so Gate 0/1 do heavy lifting; Gate 3 anchors belong
on the Li–S composition line (hull-adjacent phases), making the corrected
model a voltage/stability screener for the whole line. Demonstration in
`data/discovery_gates/`: Li₂S (known-good) versus rocksalt LiS (unproven
composition) through the full ladder.

**MOFs.** The makeability prospectus (lupine.science) frames the target:
theorem-backed synthesizability statements. This protocol supplies its
evidence layer — coverage gates for linker chemistry, concordance across
models on binding and framework stability, invariant gates on predicted
mechanics (frameworks that shear-collapse in their own model refuse
themselves), anchors on the node–linker motif, and a per-family gearbox
that carries across the combinatorial linker space, which is exactly where
reusability pays most.

## What the lab runs (deliverable shape)

One command per candidate set against a gearbox config; outputs per
candidate: gate verdicts with wall-times, certificates (Lean-checkable),
calibrated predictions with error bars where gates passed, and a refusal
dossier where they didn't. All artifacts provenance-hashed; the gearbox
updated in place. Integration points: LAMMPS log ingestion for labs whose
runs already exist; the offline Apptainer/SLURM lane for clusters
(`hpc/README.md`); contribution packets back to the corpus.

## Honest boundaries (stated up front, as always)

Mechanical stability is not thermodynamic stability — Born gates catch
self-inconsistent candidates, not hull-unstable ones; hull gates need the
formation-energy lane and element references. Dynamical sanity via
rattle-return is a proxy, not phonons. Coverage gates (v1) proxy training
distributions through dispersion calibration rather than direct histogram
access. Force-level correction awaits the continuous-coordinate field. Each
boundary is a registered next step, and the protocol's own gates will be
run against known unknowns before any lab bets on them.
