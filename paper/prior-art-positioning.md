# Prior art and positioning: the environment error field vs. Delta-ML and rescaling

> Draft section for `environment-error-field-2026-07-02.md` (Related Work / Discussion).
> Citation keys refer to `references-envfield.md`. All sources verified 2026-07-02.

## Relation to Delta-ML and learned corrections

The idea that a cheap model's systematic error can be learned and added back is
Delta-ML [ramakrishnan2015]: train a regressor on (baseline, reference) pairs so
that E_target ≈ E_baseline + ΔE_ML. The lineage runs from molecular corrections
(semiempirical→G4MP2 [ramakrishnan2015]; DFT→CC via density features [bogojeski2020];
DFT-PES→CCSD(T) with PIP fits [nandi2021]; semiempirical+NN in AIQM1 [zheng2021aiqm1])
to condensed-phase MLP baselines corrected to coupled-cluster accuracy [oneill2025],
and, for uMLIPs specifically, to fine-tuning-as-correction: frozen transfer
learning [radova2025], few-structure fine-tunes for sublimation enthalpies
[kaur2025], alloy- and steel-specific fine-tunes [steels2025], and referencing-aware
cross-functional transfer [huang2025crossfunctional]. All of these share one economics: the
correction is *learned*, so it requires per-system reference data — typically
thousands of points for Delta-ML proper [ramakrishnan2015, nandi2021], tens to
hundreds of DFT structures for foundation-model fine-tuning [kaur2025, radova2025]
— and produces either a second trained model or new weights, with no statement of
where the correction may be applied.

Our correction differs on each axis. It is **measured, not learned**: three standard
observables (two facet energies, one vacancy energy) fix the field Δε(c) in closed
form — no regression, no gradient step, no held-out set. It is **an energy, not a
calibration**: because the field is a function of local coordination, its inverse is
an additive term −Σᵢ P(cᵢ) with analytic forces, deployable in MD, unlike post-hoc
output-space calibration in the isotonic/Platt lineage [ayer1955, barlow1972,
zadrozny2002, guo2017] or UQ recalibration for materials models [tran2020uq, pernot2022].
It **transfers within a property family by construction** — the γ₁₀₀-fitted field
blind-predicts the unfitted γ₁₁₀ (r = 0.906, 36 cells, zero free parameters) — where
the transferability of a learned correction is exactly the question the fine-tuning
literature leaves open (no published transferability-of-correction study surfaced in
either verified synthesis; our H4 is, to that search's limit, the first). And it
carries **provable applicability gates**: where reference rankings invert (MPtrj
stacking faults), a kernel-checked impossibility theorem refuses correction rather
than emitting a number — a guarantee no learned corrector offers.

## Relation to one-point rescaling (Deng et al.)

The closest published correction is the single-data-point fix of Deng et al.
[deng2024softening]: PES softening of MPtrj-trained uMLIPs is systematic enough that a
single additional reference point substantially recovers the force error, per system.
(Their abstract states "fine-tuning with a single additional data point"; whether this
is best read as a closed-form global rescale or a one-point fine-tune should be checked
against their full text before the final draft calls it a "linear rescale.") We confirm
their premise and sharpen it: their per-system, near-uniform correction is the **zeroth
mode of the field** — a constant Δε across coordinations, equivalently the prefactor c
of the family power law with α forced to 1. Our measurements show why a uniform
correction saturates: the exponent is not 1 (surfaces α ≈ 1.10, all four models), the
warp is family-monotone rather than scalar (per-model scalars fail at every grain we
tested — H4), and the error is environment-resolved (surface, vacancy, and bulk probes
disagree by 15–60×). Where their correction is per-system and near-uniform, ours is
environment-resolved, property-derived from three anchors, force-bearing with analytic
gradients, and equipped with refusal theorems. Our own R2 measurement supplies the
matching bias/variance picture: OMat24-lineage retraining moved the softening scalar
s → 0.97 (removing the bias) while per-metal spread persisted — the field's prefactor
approaches identity without its higher modes vanishing.

## Honest overlaps

Both programs exploit the same fact: uMLIP errors are *systematic*, not noise
[deng2024softening, focassio2025surfaces, chipsff2025]. Deng et al.'s correction is
contained in our field as its leading term; our three-anchor protocol collapses to
theirs when the field is flat. Fine-tuning strictly dominates our correction wherever abundant
system-specific DFT is affordable — including the order-scrambled cells our gates
refuse, which retraining can fix and our field provably cannot. The field's claim is
not maximal accuracy; it is the best correction available at the cost of three table
lookups, with a proof of where it applies.
