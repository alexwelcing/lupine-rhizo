# Tungsten defect and migration task review

## Protocol frozen before full-text inspection

This review follows a separately declared source-feasibility screen, not a
reopening of the earlier four-query candidate-order trial. That trial remains
incomplete. A single broad tungsten query returned four selected primary-paper
titles; the retained 518-string identity screen and inspected checkpoint
metadata had no match. This is bounded deduplication, not proof of all-history
unfamiliarity.

The first title in returned order is Suárez-Recio et al.,
[arXiv:2505.13744v2](https://arxiv.org/abs/2505.13744v2), revised 8 September
2025. The abstract is accessible. It already exposed an author claim of
improved defect energetics and a 0.048 eV energy from an Arrhenius-like fit
of temperature-dependent defect counts. This review is therefore not blind
to those abstract-level outcomes. Numerical comparison tables and the fitting
equation have not been inspected.

### Decision and falsifier

The task is to decide which existing specification, if any, can legitimately
interpret the paper's model/reference comparison and reported migration energy.

1. A finite candidate-order conclusion requires a common explicitly named
   candidate family, material/composition, energy reference and comparable
   DFT/model values. A first eligible table with at least three configurations
   would support a listed-minimum calculation only. Use the first model
   column after DFT, not the best-performing column. If the table or common
   task is absent, record that limitation without substituting a plot/model.
2. The current anchored Arrhenius specification bounds a scalar rate under
   its barrier and prefactor assumptions. A temperature fit of a defect count
   alone is not automatically such a rate. Inspect the actual equation,
   observation time, initial populations and treatment of prefactors,
   multiple processes and fitting exposure. A demonstrated rate estimator
   with the required common mechanism would support applying the rate
   contract; a count-only or mixed-process fit would leave that mapping
   unproved. Do not decide from the word Arrhenius alone.

### Bounds and evidence labels

Read one version-pinned primary HTML representation and its relevant
table/equation passages; no PDF download, figure digitization, model archive,
new source search or alternate-route retry after failure. No simulation,
provider call, model delegation, corpus admission, fitting, deployment or
physical recommendation. Freeze Rhizo implementation at
`0475e1fa1928d4d4e42515fe65506178fc321467` throughout the review.

Same-agent interpretation and any exact arithmetic will be distinguished from
independent validation. Original source claims remain attributed. Fitting
exposure and model artifact identities stay unknown unless established by the
text. Source representation identity is distinct from model/data identity.
Stop after classifying these two applicability questions; no new metric,
feature or additional paper is required.

## Review outcome, 5 November 2026

Protocol commit `180f13528f4461bc8b5db82106225e9fa009f0f6`
preceded full-text inspection. Only the specified v2 HTML was read; no PDF,
supplementary table, model file or trajectory was acquired. Table and equation
anchors below identify the source representation; original source-byte and
model digests remain unknown.

### Listed interstitial decision

Table 1 supplies the first eligible three-configuration panel. Section 4.3
states a common DFT/MD simulation cell for defect energies. The first model
after DFT is MLIP-W. No vacancy or binding-energy row is mixed into this SIA
choice.

| Configuration | DFT (eV) | MLIP-W (eV) |
| --- | ---: | ---: |
| 110 dumbbell | 11.04 | 10.97 |
| 111 dumbbell | 10.76 | 10.86 |
| Octahedral | 13.11 | 12.80 |

The exact source-aware baseline selects 111 in both columns. Assuming
independent closed nearest-rounding intervals of +/-0.005 eV, its advantage
over 110 is [0.27,0.29] eV for DFT and [0.10,0.12] eV for MLIP-W; both
remain strictly positive. Same-agent scaled-integer endpoint arithmetic checks
all three pair intervals per column, and all eight rounding-box corners per
column retain the same unique minimum. These are deterministic printing
assumptions, not source uncertainty or confidence intervals.

The public fixture preserves the six values, original anchors, fitting-family
exposure and unknown identities. The current exact CLI and complete existing
report reader are evaluated against that baseline without changing their
implementation. Hosted acceptance is recorded in the PR/continuation receipt;
this document does not predeclare a passing execution. Agreement alone would
be a negative finding for added decision accuracy on this one listed-choice
task, while verifying automated arithmetic and qualification transport.
It would not close the abandoned two-paper protocol or prove human-time savings.

### Count-to-rate concern: partly resolved by the source

Section 2.6, Eq.2 explicitly defines an average flux as
`v = delta_n / (N delta_t)`; all observation windows are 100 ps. A constant
normalization therefore leaves the fitted log-slope unchanged. Our initial
concern that an unspecified count had simply been called a rate is not
sustained by that equation. The paper reports the resulting effective energy
as 0.048 +/-0.001 eV. Its raw count differences and fit uncertainty were not
reconstructed here.

A remaining applicability question is whether this finite-window, many-defect
flux shares the microscopic barrier/prefactor contract used by our scalar-rate
bound. It includes sink capture and recombination; the classifier also varies
with temperature and potential. The paper's reported effective energy is not
by itself an authenticated barrier for a single hop.

For clarity, an analytic competing model illustrates the missing premise.
Assume a constant initial susceptible population `n0`, one first-order loss
rate `k = nu exp(-beta E)`, temperature-independent `nu`, and a window `t`.
Then the removed population is `n0 (1-exp(-kt))`. Its average flux is
`J = n0 (1-exp(-kt))/(N t)`. Differentiating at fixed `n0,N,t,nu` gives
`-d log J/d beta = E x/(exp(x)-1)`, with `x=kt`. The apparent slope approaches
`E` only in the small-depletion limit and is smaller under saturation.
This elementary model is our conditional analysis, not a fit to this paper,
a demonstrated cause of its value, a novel theorem or a new physical execution.
Time-resolved loss fractions, multiple window lengths and classifier controls
would discriminate this possibility; those data are stated available on request,
and no author was contacted.

### Exposure and decision consequence

The source describes training on bulk, boundary and defect families; its overall
energy/force errors use training data, and finite-temperature force snapshots
come from MLIP-W trajectories. Exact row overlap, model hashes and independent
reference-state validation remain unresolved. Source claims of general accuracy
are not silently promoted.

Retain two separate records of meaning: a bounded listed-configuration ordering,
and an author-reported effective flux activation estimate. Do not feed the latter
into a microscopic rate bound without the estimator, population, time-window and
mechanism mapping. Existing manual source-aware reasoning reaches both limits;
no automatic theorem, new inspector or simulation recommendation follows.

This adds one reviewed publication to the scoped failure/applicability map,
not a corpus admission or an independent validation. The review stops here.
