# A smooth, environment-resolved error field underlies the systematic property errors of universal machine-learned interatomic potentials

> **Draft v0.2 — 2026-07-02.** Replaces v0.1 after statistical hardening,
> figure generation, and bibliography verification. §2.5 awaits the run-level
> correction experiment (slots marked `[PENDING-RUN]`); all other numbers are
> final. Citations `[key]` resolve in `paper/references-envfield.md` (77
> verified entries). Figures in `paper/figures/envfield/` with SHA-256 input
> manifest. Statistical methods and weakened-claim registers follow
> `data/y_matrix_runs/analysis/STATS.md` exactly.

## Abstract

Universal machine-learned interatomic potentials (uMLIPs) err systematically
on the properties that dominate materials practice — surfaces, vacancies,
planar faults — while matching references closely on bulk observables
[deng2024softening, focassio2025surfaces, chipsff2025]. We show that for
face-centered-cubic metals these errors are consistent with projections of a
single object: a smooth error field over local atomic environments, with
coordination deficit as leading coordinate. Measured per (model, material)
from three standard observables (γ₁₀₀, γ₁₁₁, and the vacancy formation
energy), the field predicts a fourth, never-fitted observable that probes an
unfitted coordination: across 36 (model, material) cells the blind γ₁₁₀
prediction attains r = 0.906, exceeding all 10,000 within-model material
permutations (p = 10⁻⁴ against a null whose mean is 0.44, not zero;
material-clustered 95% CI [0.82, 0.96]), with zero adjustable parameters.
The field organizes previously disconnected observations: near-universal
preservation of cross-material rankings amid large magnitude errors; an
approximately log-affine error form whose exponent orders by property family
within every model while training lineage moves the prefactor toward unity;
and the failure of scalar corrections at every grain. Because the field is a
function of environments, its inverse is an additive energy with analytic
forces, deployed here beside a live CHGNet calculator: it recovers the
fitted observables exactly through full relaxations, improves the blind
facet at run time (γ₁₁₀ error 9.7 → 1.5 % for Ni, 28.0 → 13.7 % for Cu),
leaves the bulk structurally untouched, and runs stable molecular dynamics
at 15.6 % overhead — while leaving near-equilibrium force errors unchanged,
a null result that cleanly scopes the first-shell field as an energy-level
correction and identifies the continuous-coordinate extension required for
forces. Where rankings invert, we prove — machine-checked — that no
monotone correction exists.
All quantitative claims, including negative ones, are sealed as
proof-assistant-verified theorems over provenance-hashed data.

## 1. Introduction

Foundation uMLIPs [batatia2022mace, deng2023chgnet, chen2022m3gnet,
mace-mp-0] bring near-DFT accuracy to million-atom simulation, and community
benchmarks document rapid progress on bulk energetics and stability
[matbench-discovery, matcalc-2025]. The same benchmarks, and dedicated
studies, document persistent failures away from equilibrium: surface
energies under-predicted by every MPtrj-trained model
[focassio2025surfaces], elastic tensors and equations of state markedly
harder than relaxed geometries [chipsff2025], and a pervasive "softening" of
the potential-energy surface traced to near-equilibrium bias in training
data [deng2024softening, omat24]. Two questions remained open in the
literature we could verify (§4.5): whether cross-property error structure
exists for foundation models — the closest study concerns classical
potentials of a single element [ni47metrics] — and whether a correction
fitted on one property class transfers to another; no
transferability-of-correction study has been published to our knowledge.

Here we answer both for fcc metals, and the answers compose. Cross-property
error structure exists, but not where prior tools looked: it is absent in
linear property-space statistics (pre-registered participation-ratio and
mode-alignment tests fall inside coupling-aware nulls) and present as a
*smooth field over local atomic environments*. The field is measurable from
three observables, transfers blind to a fourth (§2.4), converts into a
run-time force-bearing correction (§2.5), and carries provable applicability
boundaries (§2.6). Throughout, claims are sealed as machine-checked theorems
(§4.4); we report one instance where the proof kernel rejected a claim that
had survived our statistical filter, and the corrected count.

## 2. Results

### 2.1 The error landscape (Fig. 1)

We evaluated four uMLIPs — CHGNet 0.4.2 [deng2023chgnet], MACE-MP-0 small
and medium [mace-mp-0], and MACE-MPA-0 (OMat24 lineage) [omat24] — on a
21-material × up-to-9-property matrix (§4.1) against 228
provenance-annotated published references (§4.2). Bulk observables are
accurate (median |relative error|: lattice constants < 0.5 %, formation
enthalpies ≈ 3 %); defect-family observables err 15–60× worse per model
(bootstrap CIs exclude parity for all four; Fig. 1b). This split — the
defect/bulk asymmetry of [deng2024softening] quantified on a matched,
reference-bound matrix — motivates everything that follows.

### 2.2 Rankings survive where magnitudes fail (Fig. 2)

Across materials, predicted rankings track reference rankings closely for
surfaces (Spearman ρ = 0.88–1.00 per model; MACE-MPA-0's γ₁₁₁ ranking
reproduces the reference permutation exactly), vacancies (0.84–0.93), and
B₀ (0.82–0.85), while the corresponding magnitude errors reach tens of
percent. All 22 reference-ordered facet hierarchies are reproduced by all
models. The single fracture is diagnostic: stacking-fault rankings collapse
for the three MPtrj-trained models (ρ = 0.11–0.46) and survive in the
OMat-lineage model (0.93) — we return to why in §2.4. Ordinal faithfulness
is the invertibility condition for any monotone error model; its selective
failure marks where no such model can apply.

### 2.3 The error is approximately log-affine; the exponent orders by family (Fig. 3)

Regressing log-prediction on log-reference yields R² = 0.93–0.98 (surfaces,
B₀): the error acts as pred ≈ c·T^α within a property family. Two
regularities follow, stated in the registers our statistics support (§4.3).
*Family ordering:* in all four models the fitted surface exponent exceeds
the vacancy and B₀ exponents (8/8 point-orderings, a deterministic property
of this dataset); as statistical claims, 5/8 paired-bootstrap differences
exclude zero nominally and 1/8 after Holm correction. *Cross-model
compatibility:* the four surface exponents (1.065–1.138) spread less
between models than single-model uncertainty (variance ratio 0.39) —
consistent with, though not demonstrating, a family-owned exponent.
Training lineage acts on the prefactor: surfaces c = 0.66 (CHGNet) → 0.98
(MPA-0), and pooled warp magnitude orders strictly by lineage
(0.051 < 0.099 < 0.120 < 0.388). A two-parameter log-affine correction
matches an 8-knot isotonic correction out-of-sample (paired-difference CIs
include zero) with six fewer parameters; against raw predictions the
correction is decisive for CHGNet (27.96 % → 10.04 %, clustered
p = 4×10⁻⁴) and directional for MACE-small (12.05 % → 7.45 %, p = 0.061).
Scalar (α = 1) corrections fail at every grain we tested — per-model,
per-material, within-family — consistent with α ≠ 1.

### 2.4 The environment error field and its blind test (Fig. 4)

The regularities of §2.2–2.3 follow if the model's energy error is a smooth
function of local coordination, accumulated per atom:

  E_model(config) − E_ref(config) ≈ Σᵢ Δε(cᵢ),   Δε(12) ≡ 0 (fcc bulk).  (1)

Each property then samples the field at its characteristic coordinations —
fcc(100) top-layer atoms at c = 8, (111) at 9, vacancy first neighbors at
11, (110) at 7 and 11 — so per (model, material) three observables measure
three field values:

  Δε(8) = δγ₁₀₀·A₁₀₀,  Δε(9) = δγ₁₁₁·A₁₁₁,  Δε(11) = δE_vac/12,  (2)

with δ the signed error and A the area per surface atom. The field
hypothesis is then falsifiable with no free parameters: γ₁₁₀'s error
involves the *unfitted* coordination 7, predicted by linear continuation of
the field below c = 8. Across 36 cells the prediction attains r = 0.906
(Fig. 4b) — exceeding all 10,000 within-model material permutations
(p = 10⁻⁴; the honest null has mean r = 0.44 because pooling across models
shares error scales, and we report against it, not against zero) — with
material-clustered 95% CI [0.82, 0.96] and no single material carrying the
result (leave-one-material-out r = 0.857–0.944). Per model, the prediction
is individually significant for CHGNet (r = 0.86), MACE-small (0.90), and
MPA-0 (0.96), but not MACE-medium (0.47, p = 0.10, n = 9): the field claim
is carried by three of the four models. The median residual improves on
predict-zero marginally under clustering (0.066 vs 0.104 J/m², p = 0.036);
26 of 36 cells improve strictly at 10⁻⁴ J/m² integer precision (one
additional cell's improvement vanishes at that precision — a margin caught
by the proof kernel, §4.4).

The field explains the fracture of §2.2: an intrinsic stacking fault alters
no first-neighbor counts, so a first-shell field is blind to it — SFE
errors are ungoverned residue, and MPtrj models, whose training
distribution samples faulted stackings sparsely, scramble SFE rankings
while everything first-shell-visible stays ordered.

### 2.5 From field to run time: an energy-level correction (Fig. 5)

Equation (1) inverts into an additive correction energy
E_corr = −Σᵢ P(cᵢ), with P the cubic through the three measured knots and
P(12) = 0, cᵢ a smooth-cutoff coordination, and analytic forces via the
chain rule (verified against numerical differentiation to 10⁻⁶ eV/Å on
rattled slabs), deployed beside the live CHGNet calculator. Three
validation levels, as measured:

*Statics.* The corrected calculator, run through the full property
pipeline (relaxations included), recovers the three fitted observables
exactly — a closure test showing the bond-counting field survives real
relaxation — and improves the **blind** facet at run time: γ₁₁₀ error
9.7 % → 1.5 % (Ni) and 28.0 % → 13.7 % (Cu). The bulk is structurally
untouched: coordination remains 12 across the EOS window, so E_corr
vanishes identically there (measured a₀ shift 0.0000 Å).

*Forces (null result).* Force RMSE against a stronger-model proxy
(MACE-MPA-0) on twenty rattled Ni(110) slabs is unchanged (0.2594 →
0.2595 eV/Å overall; 0.1926 → 0.1932 on surface atoms). The mechanism is
instructive: the first-shell field corrects energy *differences between
coordination environments*, and its force footprint is confined to the
cutoff switching shell, which 0.08 Å thermal displacements do not cross.
Near-equilibrium force error lives in the PES curvature — the softening
exponent of §2.3 — not in the coordination step. Version 1 is therefore
an **energy-level** correction (property values, and by extension
energy differences between coordination states); correcting forces
requires a field over a continuous environment coordinate, which we
identify as the necessary v2.

*Dynamics.* 1,000 steps of 300 K Langevin NVT on the corrected Ni(110)
slab run stably (the ≈5 eV total-energy rise matches 3/2·N·k_BT
equilibration from a cold start); the unoptimized correction overlay adds
15.6 % wall time to the CHGNet step, with an obvious path to negligible
cost via a compiled pairwise implementation (the term is EAM-embedding
shaped and LAMMPS-overlay compatible [lammps-docs]).

### 2.6 Provable boundaries (kernel-checked)

Correction has jurisdiction only where order survives. Where it does not,
we prove impossibility rather than report failure: MACE-MP-small orders
SFE(Ni) ≤ SFE(Al) while the references order the reverse; a quantified
monotonicity lemma then shows no monotone correction maps both predictions
to their references (machine-checked with concrete witnesses). Two further
boundaries: separately-fitted classical-potential families share no field —
leave-element-out calibration of 623 ledger EAM elastic records *degrades*
them — and already-converged cells refuse correction (MPA-0's surfaces,
where raw error sits at the anchor-noise floor). Classical potentials
retain their own value proposition: a consistent EAM family beats CHGNet on
20/24 matched surface cells at ~6× less compute without a GPU
(kernel-checked cell facts), a deployment-relevant baseline for
correction economics.

## 3. Discussion

**Relation to prior corrections.** Δ-machine-learning [ramakrishnan2015]
and its descendants — from coupled-cluster corrections [bogojeski2020,
nandi2021, zheng2021aiqm1, oneill2025] to uMLIP fine-tuning [radova2025,
kaur2025, steels2025, huang2025crossfunctional] — *learn* corrections from
per-system reference data and yield new weights with no statement of
applicability. The present correction is *measured*, not learned: three
anchor observables fix a closed-form field; transfer within the family is
the tested content of the method (γ₁₀₀ → γ₁₁₀ blind, §2.4); and
applicability is gated by proof (§2.6). The one-data-point rescaling of
[deng2024softening] is the field's zeroth mode — a constant Δε — and our
measurements show why it saturates: the error is environment-resolved
(15–60× defect/bulk asymmetry) and its log-affine exponent differs from
unity. Conversely, wherever abundant system-specific DFT is affordable,
fine-tuning strictly dominates, including in the order-scrambled cells our
gates refuse. Output-space calibration — the isotonic lineage
[ayer1955, barlow1972, zadrozny2002, guo2017] and materials-UQ
recalibration [tran2020uq, pernot2022] — corrects numbers after the run;
Eq. (1) corrects forces during it.

**Mechanism (hypothesis).** A smooth regressor trained on a
configuration distribution dominated by near-equilibrium, high-coordination
environments will interpolate confidently there and extrapolate with
correlated bias into under-sampled coordination regimes; the bias, shared
across materials because the descriptor space is shared, appears as a
smooth Δε(c). This is testable independently of our data: the coordination
histogram of MPtrj vs OMat24 [mptrj, omat24] should predict the field's
magnitude, and the sloppy-model geometry of the fitted models
[transtrum2010, transtrum2011, kurniawan2022] should exhibit the
corresponding stiff direction. We propose both as follow-up.

**Relation to the error-geometry program.** Pre-registered linear analyses
(participation ratios, mode cosines against coupling-preserving nulls)
found no cross-property structure — apparent cosine alignments of 0.96 fell
inside nulls reaching 0.98, a false positive avoided only by the null
design. The structure is nonlinear: one smooth function per (model,
material, family). Low-dimensionality of model error [transtrum2010]
survives, in curved form, one level below the observables.

**Limitations.** Coverage: fcc first-shell coordination only; bcc and
hcp surfaces, alloys, and finite-temperature observables are untested;
the field needs at least a second-shell coordinate to govern planar
faults. Statistics: n = 9 materials per model for the blind test; one of
four models is individually non-significant; exponent family-ordering is
statistically resolved for only a subset after multiplicity correction.
Physics: relaxation contributions are folded into effective knots
(unrelaxed bond counting); vacancy references mix DFT functionals; the
force validation uses a stronger model as proxy, not DFT, and returned a
null — the v1 field does not correct near-equilibrium forces (§2.5), so
claims of run-time benefit are limited to energetics until a
continuous-coordinate field is built and tested.
Scope of verification: the proof kernel certifies data-analysis
arithmetic and stated inequalities over the measured dataset — it does
not certify physics.

## 4. Methods

### 4.1 The property matrix
21 materials (Ag, Al, Au, Ca, Cr, Cu, Fe, Mo, Nb, Ni, Pd, Pt, Sr, Ta, V, W;
Si; B2-NiAl; L1₂-Ni₃Al; MgO; NaCl) × 4 models × up to 9 properties (a₀,
B₀, B₀′, E_vac, γ₁₀₀, γ₁₁₀, γ₁₁₁, γ_SFE, ΔH_f). Statics: Birch–Murnaghan
EOS (±6 % volume, 11 points, recentring); fixed-cell FIRE relaxation
(fmax 0.01 eV/Å); slabs ≥ 8 layers, 12 Å vacuum; displaced-slab intrinsic
SFE evaluating both Shockley branches; 3×3×3 vacancy supercells. Each
cell is provenance-hashed and bit-reproducible (≤ 10⁻¹¹). Fe carries a
documented model-deficiency annotation (its anomalous B₀ is
window-independent and unaffected by magnetic initialization, which we
verified changes neither calculator's energy by even one ulp; an earlier
state-preparation hypothesis of ours is preserved, falsified, in the
registration's amendment log).

### 4.2 References
228 published values, 8 property families, compiled under a no-fabrication
rule: every value carries a citation verified at compilation time
[tran2016, dejong2015, angsten2014, ma-dudarev2019, ...20 primaries in
references file]; unverifiable values are recorded as explicit gaps.
Binding prefers DFT-PBE, falls back to experiment, and mechanically
refuses method-mismatched entries.

### 4.3 Statistics
Pre-registered hypotheses with kill conditions; coupling-aware nulls
(within-family structure preserved, cross-family alignment permuted;
1,000 seeded draws); leave-one-out throughout; material-clustered
bootstrap (10,000 draws) for all headline CIs; within-model material
permutation (10,000 draws) for the blind-test null; Holm step-down within
pre-specified claim families; ~47 sampling-based tests inventoried, with
the primary blind-test claim surviving paper-wide Bonferroni. Weakened
registers adopted wherever hardening reduced a claim; the full audit is
released with the data.

### 4.4 Machine verification
All quantitative outcomes — positive, negative, and impossible — are
encoded as decidable Lean 4 theorems over integer-scaled data carrying
SHA-256 provenance of their sources: ordering claims as inequality chains
over predictions (the kernel verifies the order, not a summary), the
isotonic correction as a Lean function whose outputs the kernel computes,
impossibility results as quantified lemmas with concrete witnesses. Eight
modules, 100+ theorems, zero `sorry`. During preparation the kernel
rejected one claimed blind-prediction win whose margin vanished at
integer precision (`decide` refused `813 < 813`); the count in §2.4 is
the corrected one, and the figure pipeline independently reproduced the
same boundary case.

### 4.5 Literature verification
Two ~100-agent deep-research sweeps with three-vote adversarial
verification of every extracted claim (25 and 22 claims confirmed 3–0;
sources and transcripts released). One initially-cited preprint was found
withdrawn during bibliography verification and is struck with a dated
correction preserved in the working documents.

## Data, code, and proof availability
Evidence payloads, reference compilations with per-value provenance,
binding reports, analysis artifacts (seeds included), figure pipeline with
input-hash manifest, statistical-hardening script, and all Lean modules
with build configuration are available in the project repository; every
theorem type-checks under Lean 4.30 with the pinned toolchain.
