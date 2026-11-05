# Failure map: from an error score to a materials decision

Reviewed 4 November 2026. This is a scoped synthesis of completed analyses,
not a new simulation, a corpus-wide audit or a prevalence estimate. The
literature examples below cover eight publications; repeated reference columns,
model panels and rounding corners are not independent studies. Synthetic
obstructions and product-contract findings are listed separately.

The recurring issue is loss of decision-relevant information. An accurate
calculation can still answer the wrong question if its reference, observable,
feasible alternatives or physical interpretation changes. A stronger contract
must specify those choices before applying an error bound.

## Source-grounded cases

| Case and observation date | Discriminating result | What the result requires |
| --- | --- | --- |
| **Reference multiplicity — Qi 2023**, 26 October. Table I, six TiAl elastic components. | With unit component weights, MTP-minus-MLP3 squared-error difference is +160 GPa² against the DFT column and −240 against the experimental column. Counting one of each gives −80; counting the same DFT column twice gives +80. Duplication was counterfactual arithmetic, not an added observation. | Fix reference weights independently of row counts. The experiment is composition-qualified; neither mixed nominal winner survives the stated independent printing boxes. This is a sensitivity example, not a physically admissible pooled ranking. |
| **Decision functional — Wang 2022**, 26 October. Table V, bcc V. | Against the same-work DFT vector, DP-HYB has smaller component SSE than GAP (16.34 versus 30.77 GPa²), but larger worst relative harmonic strain-energy error (7.2034% versus 2.2603%). | Choose the intended loss. The energy statement assumes aligned cubic stiffness matrices and a positive-definite reference; changing the reference to the experimental column reverses this energy preference. It is not a general potential ranking. |
| **Reference domain — Leimeroth 2024, Zhou 2018 and Nichols 2024**, 26 October. Thirteen selected cubic panels. | Five reference matrices are indefinite. For bcc Zr, a strain on the reference null cone has zero reference energy and nonzero predicted energy. A finite ratio of modal discrepancies therefore cannot bound relative energy over all strains. | Check the positive-reference domain before dividing by reference energy. Preserve signed modes and static/finite-temperature distinctions; matching instability signatures does not repair the denominator. This is tabulated harmonic analysis, not complete physical stability validation. |
| **Ordering control — Olsson 2005**, 4 November. Table II, paramagnetic bcc Cr interstitials. | Model energies [5.60, 5.62, 6.83] eV and VASP [5.66, 5.68, 6.78] eV both select the listed 110 configuration. The nearest gap is 0.02 eV in both; assumed printing boxes give [0.01, 0.03] eV. | Retain a positive control. These relaxed defect energies enter fitting; agreement is not independent held-out validation or a global-ground-state claim. A competent source-aware comparison reaches the same decision. |
| **Barrier ordering — Ko 2015**, 4 November. Table XI, Ni migration in hcp Ti. | Out-of-basal minus in-basal barrier is +0.088 eV for DFT and −0.151 eV for 2NN-MEAM. Assumed printing intervals [0.087, 0.089] and [−0.152, −0.150] preserve the reversal. | Preserve the direction and initial/path identities. Unknown prefactors prevent a rate-order conclusion; hop barriers alone do not determine a diffusion tensor. The source already reports Ti-rich migration limitations, so this is not a newly discovered physical failure. |
| **Feasible alternatives — Kobayashi 2017**, 4 November. Table II, Al–Mg–Si binary compounds. | Mg3Si has negative PBE formation energy (−7 meV/atom), yet Mg + Mg2Si is lower by 95 meV/atom at the same overall composition. Restricting compounds to Si fraction ≤1/4 omits Mg2Si at 1/3 and incorrectly makes Mg3Si a vertex of that restricted hull. | Compare composition-balanced alternatives, including mixtures of phases outside the requested bulk-composition window. This deliberate restriction is our retrospective counterexample, not an allegation about the authors' procedure. A finite-hull vertex does not establish stability against omitted phases. |

These are purposively selected reported-table cases. Original corpus eligibility
exclusions remain in force; no pooled physical-error dataset is created here.
Printing boxes are independent closed nearest-rounding assumptions, not reported
uncertainties or confidence intervals. Exact model artifacts, matching physical
protocols and row-level fitting exposure remain unresolved where stated.

The Olsson and Ko plans preceded numerical inspection on 4 November. The
Kobayashi selection is retrospective: numerical source lines were visible before
its analysis plan. None is an independent replication or a new model execution.

## Synthetic obstructions and a product-contract correction

| Contract | Checked obstruction or correction | Current evidence boundary |
| --- | --- | --- |
| Absolute vacancy labels versus a centered score | Adding 0.1 eV to every label gives centered MSE 0 and full MSE 0.01 eV². Full MSE decomposes into within-species variation, squared overall bias and species-mean imbalance. | The finite equal-site-weight identity and constant-error obstruction are proved in Lean. Exact Rust and TypeScript contract tests are separate from that proof and from physical accuracy. See [vacancy evidence](vacancy-reference-evidence.md). |
| Sampled range versus forward barrier | Profiles [1, 3, 0] and [2, 3, 0], with first image initial, share range 3 but have forward barriers 2 and 1. | Lean proves the equality condition and initial-anchored transfer bound. This synthetic example does not identify a bad historical path. See [barrier evidence](anchored-barrier-evidence.md). |
| Barrier evidence versus conductivity prose | Ledger's structurally valid CT2 blocker inferred an orders-of-magnitude conductivity error from a barrier percentage. A source-bound review now qualifies that interpretation and exposes missing premises and review history. | [Ledger PR 38](https://github.com/alexwelcing/lupine-ledger/pull/38) passed its 65-test/content/build checks; deployment was skipped. This is a draft correction to machine-readable content, not a measured live-reader incident or validation of the underlying barrier percentage. |

## Mathematical synthesis and existing alternatives

The useful distinction is between transformations that preserve a decision and
information discarded by a score:

- **Absolute formation labels:** centering discards the overall level. A centered
  score cannot certify an absolute-energy task. Reference calibration and
  elemental-energy gauge invariance are separate obligations.
- **A fixed list of comparable candidates:** a common energy shift preserves all
  signed gaps. Direct interval gaps retain ties and distinguish possible,
  guaranteed and uniquely lowest choices.
- **A sampled forward barrier:** a common energy shift cancels, but the designated
  initial image cannot be replaced by the sampled minimum without a premise.
- **Bulk phase mixtures:** affine composition-dependent energy shifts cancel in
  balanced reaction differences. The composition constraints and competitor set
  must be fixed before a hull decision is meaningful.
- **A rate or transport interpretation:** temperature, prefactors and the physical
  network/population model add premises that an energy-error statistic cannot
  supply.

This is a synthesis of standard linear algebra, interval reasoning, finite
extrema and convex-mixture thermodynamics. It is not a universal correction
theorem. The positive-reference condition in relative strain energy is a domain
condition, not an energy-zero invariance.

For the phase case, write the admissible competing mixtures as

    C_i = {lambda >= 0 : sum(lambda) = 1,
           sum(lambda_j x_j) = x_i, lambda_i = 0},
    D_e(i) = e_i - min_{lambda in C_i} sum(lambda_j e_j).

Assume C_i is nonempty and use the same finite candidates and constraints for
reference r and prediction p. If every residual delta_j = p_j-r_j lies in
[a,b], then

    delta_i-b <= D_p(i)-D_r(i) <= delta_i-a,
    |D_p(i)-D_r(i)| <= b-a.

Every weighted residual lies in [a,b], which bounds the difference between the
two minima. Adding the same affine composition function to all energies,
including elemental endpoints, leaves D unchanged. A cheaper admissible
decomposition remains a witness when candidates are added with their energies
preserved. In contrast, absence of such a witness in a finite list does not prove
absence among omitted phases. These arguments are not new Lean proofs or
executable correctness guarantees.

The comparison baseline must already know source qualifiers and ordinary
methods. It is not a scalar-RMSE-only straw comparator. On Olsson, Ko and
Kobayashi, that competent baseline reaches the same reported decision as our
arithmetic components. No added decision accuracy or speed benefit has been
demonstrated.

Closest work includes Piersante and Natarajan,
[Machine learning interatomic potentials for solid-state precipitation,
arXiv:2601.12984v1](https://arxiv.org/html/2601.12984v1), Section IV.1 and Figure 6.
It already distinguishes fixed-composition ordering from hull stability and
evaluates semi-grand rankings over exchange chemical potential. It is a preprint;
our 4 November review read the primary HTML, not new underlying simulation data.
Ordinary convex-hull construction gives the same phase decisions here. These
overlaps leave novelty unestablished.

For the elastic cases, the
[Kelvin/cubic representation](https://arxiv.org/html/cond-mat/0509705v3)
and [unstressed harmonic stability criteria](https://www.coudert.name/papers/10.1103_PhysRevB.90.224104.pdf)
are established methods. Neither a changed task loss nor a reference-domain
check should be presented as a new physical discovery.

## Implementation and acceptance evidence

The existing [candidate-order contract](candidate-order-evidence.md) already
accepts balanced mixture alternatives if they are constructed in a common
composition and energy convention. This example does not justify another
inspector.

For Kobayashi, three alternatives were expressed as the same four-atom reaction
unit, 3 Mg + 1 Si: L12 Mg3Si; Mg + C1 Mg2Si; and the elements. The actual
dependency-free interval/gap/minimum function bodies from
`candidateOrderContracts.ts` at
`03d3a0b2a08dd727c48981e7cd6f8c54104d202c` were exercised in memory after native
TypeScript type erasure. PBE and NN choose Mg + Mg2Si; the tabulated Jelinek
MEAM chooses the elements. The arithmetic agrees with the separate rational
analysis.

That component evaluation did **not** run Zod validation, the complete report
assessor, the Rust CLI, React interaction or an authenticated browser route.
Olsson and Ko component evaluations have the same boundary. Synthetic hosted
Rust/TypeScript tests at that revision are a separate receipt.

The phase analysis compared exact mixture enumeration with a separately written
lower-hull algorithm: nine nominal method/system panels and 240 rounding-corner
panels, with 42 nominal and 1,152 corner classifications. Those are same-agent
arithmetic checks, not independent reviews. The 28 PBE/model comparison rows and
four repeated-prediction PBEsol comparisons represent one publication and
14 compound configurations. The NN configurations are training data.
Parenthetical PBEsol values are same-work functional alternatives; the two-value
Mg3Si/Mg2Si check is not a complete PBEsol hull.

[Rhizo PR 158](https://github.com/alexwelcing/lupine-rhizo/pull/158) remains draft.
Its implementation revision above passed the normal Lean, Verify, glim-think
and atlas checks, with deployment skipped. Source-bound component calculations,
formal specification checks, synthetic runtime tests, full report acceptance
and deployed behavior must remain separately reported.

## What would justify the next investment

The next unresolved claim is whether exposing these contracts prevents an
otherwise accepted wrong inference in a complete evidence workflow. The
Ledger correction demonstrates one content-review mechanism, but neither
inspection tool has demonstrated an incremental decision benefit over a
competent source-aware baseline.

The [public-source acceptance bridge](candidate-order-source-acceptance.md)
exercises the existing Olsson control, Ko reversal and Kobayashi balanced-mixture
cases through the complete producer and report validator. It checks exact
outputs, corrupted assessments, explicit unknown context and retained source
anchors. This integration gate and its execution receipts are separate from
physical acceptance, interactive browser behavior and added decision value.
A future comparison of user decisions or review effort needs its own
predeclared protocol and actual observations.

Stop feature expansion if the existing tools reproduce the competent baseline
without an identifiable workflow gap. Continue only for a demonstrated omission,
incorrect acceptance, stale evidence dependency or measurable review benefit.
Another scalar metric or theorem with no decision consequence is not the next
acceptance criterion. No new provider call, simulation, deployment or physical
promotion follows from this document.

## Primary-source anchors and review provenance

- **Qi 2023:** [arXiv:2305.11825v2](https://arxiv.org/pdf/2305.11825v2),
  Table I, PDF page 8; DOI 10.1103/PhysRevMaterials.7.103602.
  Original comparison review 26 October, not repeated on 4 November.
- **Wang 2022:** [arXiv:2209.12322v1](https://arxiv.org/pdf/2209.12322v1),
  Table V, PDF page 9; DOI 10.1103/PhysRevMaterials.6.113603.
  Task-loss and protocol reviews 26 October.
- **Leimeroth 2024:** [Phys. Rev. Materials 8, 043602](https://doi.org/10.1103/PhysRevMaterials.8.043602),
  Table I; **Zhou 2018:** [retained primary manuscript](https://www.osti.gov/servlets/purl/1498764),
  Table III, PDF page 11; **Nichols 2024:** [arXiv:2411.07960v1](https://arxiv.org/pdf/2411.07960v1),
  Supplement Table III, PDF page 33. Domain review 26 October.
  Leimeroth was text-checked; Zhou and Nichols had retained visual-page checks.
- **Olsson 2005:** [Phys. Rev. B 72, 214119](https://doi.org/10.1103/PhysRevB.72.214119),
  Table II, PDF page 3, and Section III. Retained source/preview review 4 November.
- **Ko 2015:** [primary manuscript](https://pure.mpg.de/rest/items/item_2248813_6/component/file_3189515/content),
  Table XI, PDF page 15, and Section II A; DOI 10.1103/PhysRevB.92.134107.
  Retained source/preview review 4 November. Per-defect fitting typography was
  not visually resolved.
- **Kobayashi 2017:** [accepted manuscript](https://link.aps.org/accepted/10.1103/PhysRevMaterials.1.053604),
  Equation 11, printed page 12; Table II, physical PDF page 16 / printed page 15.
  Retained text review and analysis 4 November, 17:53–18:04 UTC; no new PDF-page review.

The current review links previously completed evidence; it does not refresh
original observation times. Only this reviewed literature/methods synthesis
and implementation references are included. Private campaign packets, raw
corpus archives, local paths and model/controller state are excluded.
