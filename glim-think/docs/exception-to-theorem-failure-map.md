# Failure map: from an error score to a materials decision

Updated 5 November 2026 UTC; original review dates are retained. This is a scoped synthesis of completed analyses,
not a new simulation, a corpus-wide audit or a prevalence estimate. The
literature examples below cover eighteen publications; repeated reference columns,
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
| **Composition holdout and estimator — Guo 2022**, 4 November review of the 2 February preprint. Supplement Table IV, LiCl–KCl eutectic. | GAP reports conductivity 0.659 W/(m K), versus RIM 0.856 and a cited experimental 0.690. The eutectic composition was excluded from GAP fitting, and the supplement reports energy/force errors on 120 independent test samples. | This is a favorable reported comparison, not a common-test energy-error ranking of the two potentials. The conductivity uses density-fluctuation extrapolation; the models use different simulated densities and the cited experimental temperature remains unaudited. Fitting exclusion alone does not establish independence from model selection. |
| **Selection role and reference lineage — Attarian 2024 preprint**, 4 November. Sections 2.1, 3.1 and 3.2; Tables 4–5. | The authors choose Pot_2 using the results of Figures 2 and 3; Figure 3 includes the eutectic composition excluded from fitting. Separate unary ACE models give NaCl densities [1.55, 1.28, 1.45, 1.57] g/cm³ at 1200 K, against 1.49 ±0.5%. | Preserve fitting exclusion without upgrading it to selection-independent evaluation. The unary models are separately refitted to different DFT targets, with additional active learning; their Table 4 training errors are not a common-reference test. Do not attach the mixture Pot_2 holdout claim to these unary results. |
| **Observable identity and fitting role — Mahata 2022**, 4 November. Table 6, Al-Cu alloys. | Five nominal liquidus discrepancies range from -5 to +22 K, including a marked eutectic entry. The source prioritized solidus/liquidus temperatures during fitting and initialized both phases at the alloy composition. | The inspected methods do not establish final phase compositions/fractions or a liquidus boundary at each overall composition. Preserve the reported values without treating temperature convergence as independent liquidus validation or missing evidence as proof of non-equilibration. |
| **Sampling precision — Zhu 2021**, 4 November. Table 1, six elemental/potential pairs. | Al TOR-TILD is reported as 824 +/- 0.1 K against a cited experimental 933 K: -109 K nominal discrepancy despite a small standard error of the mean. | Separate numerical convergence, seed sampling, physical reference and fitting role. The paper demonstrates unary phases; its precision does not validate an alloy liquidus method. See the [two-study coexistence review](phase-coexistence-evidence.md). |
| **Auxiliary-reference role — Zhu 2017**, 4 November. Cu TOR-TILD. | The [linked review](auxiliary-reference-evidence.md) separates a reference's standalone prediction from the corrected target. | Preserve target identity and both phase corrections; target evaluation is separate from physical validation. |
| **Representation versus fitting — Bartók 2018**, 4 November. Table III, silicon stable stacking fault. | GAP reports 0.002 J/m² against DFT/PW91 0.047 J/m². The authors state that GAP can distinguish the relevant environments and suggest extending its database. They separately attribute exact-zero results from several shorter-range potentials to limited range. | A small or printed-zero prediction does not establish identical model inputs. Preserve the stated explanation as an author report; an independently demonstrated representation obstruction needs the exact model, configurations and representation. |
| **Dependent reference and task — Mishin 2005**, 4 November. Tables 4–5, Fe and Ni vacancies. | Fe has nominal formation/migration discrepancies +0.13/−0.17 eV, summing to −0.04 eV. However, the 0.91 eV migration reference was derived from the reported activation and formation values. Ni component discrepancies reinforce: ADP +0.03/+0.04 eV; EAM −0.03/−0.11 eV. | Preserve the reference dependency and fitted-property status. Agreement in a summed activation estimate does not separately validate vacancy population or jump kinetics. The Fe component signs are not certified by the reported uncertainty envelopes. |
| **Reference choice control — Fellinger 2010**, 4 November. Table IV, Nb vacancies. | EAM-minus-same-work-DFT discrepancies are +0.38 eV for formation and +0.22 eV for migration, summing to +0.60 eV. They reinforce rather than cancel; all three predictions nevertheless fall within the separately reported experimental literature ranges. | Keep DFT and experimental comparisons separate. These ranges have unresolved joint provenance and confidence meaning; membership does not isolate potential error or independently validate diffusion. The activation row is a sum of the components, not a third independent calculation. |

| **Preparation path and crystallization — Mendelev 2019**, 5 November. Tables I-III and Sections 4, 7-9. | FS1 has smaller nominal density and mixing-enthalpy errors at Cu64.5Zr35.5, yet the authors report Laves nucleation/growth after slower cooling and reheating; FS2 passes that bounded test. Correct static phase ordering alone does not explain the contrast. | Preserve liquid-crystal driving forces, kinetics, fitting exposure and preparation history. A finite absence of nucleation is not experimental glass-forming validation. The competent source-aware baseline already reaches this conclusion. |
| **Protocol-dependent agreement — Paduraru 2007**, 5 November. Tables 3-4 and glass-preparation methods. | EMT gives a 620 K glass transition versus cited 670 K after cooling at 0.54 K/ps; Table 3 contains an acknowledged L11 formation-energy discrepancy of -0.3795 eV/atom. | Retain the cooling protocol and state/reference limits. The L11 discrepancy does not establish failure in the later Mendelev test; potential artifacts and compositions differ. No new classifier or cross-paper ranking follows. |

These are purposively selected reported-table cases. Original corpus eligibility
exclusions remain in force; no pooled physical-error dataset is created here.
Printing boxes are independent closed nearest-rounding assumptions, not reported
uncertainties or confidence intervals. Exact model artifacts, matching physical
protocols and row-level fitting exposure remain unresolved where stated.

The Olsson and Ko plans preceded numerical inspection on 4 November. The
Kobayashi selection is retrospective: numerical source lines were visible before
its analysis plan. None is an independent replication or a new model execution.

The molten-salt selection used metadata before this review's numerical reads.
The papers were already in the historical corpus, so this is not independent
blinding. Six existing comparison rows were reviewed: two conductivities and
four NaCl densities. No observations or studies were added to the corpus.
The Guo numerical check used retained primary-source text; its earlier failed
PDF/screenshot routes were not retried. Attarian Table 5 was checked against an
existing page preview. Both retained versions are preprints; equivalence to
their final journal articles and the original experimental references remains
unverified.

For Guo, the nominal model-minus-reference discrepancies are −0.031 and
+0.166 W/(m K). This calculation does not isolate potential error from state,
reference or estimator effects. For Attarian, the nominal density discrepancies
are +0.06, −0.21, −0.04 and +0.08 g/cm³. Expanding the reported experimental
percentage gives [1.48255, 1.49745] g/cm³; all four printed predictions lie outside
that interval. No confidence level is inferred. The source's reported maximum
MD density uncertainty, 0.0003 g/cm³, is a sampling statement, not a bound on
DFT-method or surrogate bias. This review does not assign the discrepancies
causally or establish a universally best DFT method.

The selection wording is evidence about the authors' stated decision rationale,
not an allegation of invalid fitting or proof of undocumented optimization.
The source explicitly attributes the Pot_2 choice to Figures 2 and 3. The fitting
exclusion remains true; independence from that selection step is not established.
A later evaluator must retain the model branch, reference method, split unit
(configuration or composition), and fitting/selection/evaluation roles together.
An existing free-text qualification can express this; no new inspector or
automatic independence classifier has been justified.


The coexistence review covers eleven existing rows from Mahata and Zhu. Their
numbers were originally extracted on 7 October; the 4 November review checked
methods, uncertainty meanings and selected source pages. No corpus observations
or studies were added. The original eligibility exclusions remain. See the
[two-study review](phase-coexistence-evidence.md) for the boundary calculation,
fitting limits and the observation that would resolve the alloy claim.

## Silicon: a representation hypothesis not established

Eight existing stable-fault observations were reviewed against Table III and
the surrounding discussion on PDF page 22. The source describes a diamond
silicon (111) glide-plane fault, using an 18-atom, nine-bilayer cell and relaxation
along the surface normal. The inspected paths do not establish a globally
minimal physical pathway. These configurations were excluded from GAP training;
the other models' task-specific fitting exposure remains unresolved.

The authors identify second-neighbor environments differing from diamond and
state that GAP has enough range and flexibility to distinguish them. Their
suggestion that more training configurations could improve the result is not
an executed retraining result or proof of a unique cause. Their per-atom error
estimate is not a calibrated confidence bound. The limited-range explanation
for other potentials remains a separate source claim, not evidence that GAP
has the same limitation.

This review therefore does not support classifying GAP's small positive
prediction as an unavoidable representation error. Conversely, it does not
independently verify representation adequacy: exact potential files, fault and
reference coordinates, and evaluated representations were not established.
A model-specific collision or cutoff argument must be demonstrated before
using it to certify an irreducible error. A reported numerical discrepancy
alone cannot supply that premise.

The retained PDF matched its prior SHA-256 pin, and the existing page 22 preview
was visually checked. Methods on page 21 and representation/locality discussion
on pages 7 and 11 were checked as retained text, without a new visual review.
All four qualification files matched their pins and contained no explicit
target for these eight IDs; original pooled-analysis exclusions remain in
force. Observations retain their 7 October extraction time. No rows, studies,
model executions or independent validations were added. The existing source
qualification fields can retain these limits; no new checker is justified.

## Vacancy activation: component errors and dependent references

Thirteen existing rows were reviewed across Mishin and Fellinger. In the Fe
example, the reference relation is explicitly `M = Q - F`: nominal formation
`F = 2.0 eV`, activation `Q = 2.91 eV`, and inferred migration `M = 0.91 eV`.
The model gives 2.13 and 0.74 eV, hence 2.87 eV in total. Summing the reference
components recovers the original activation measurement; it supplies no new
independent observation. Both defect properties entered fitting.

The reported envelopes `F = 2.0 +/- 0.2 eV` and `Q = 2.91 +/- 0.04 eV`
imply the deterministic outer range `M in [0.67, 1.15] eV`, preserving
`M = Q - F`. With assumed nearest-rounding half-last-digit boxes for the
two-decimal model values, component-discrepancy ranges are
`[-0.075, 0.335]` and `[-0.415, 0.075] eV`; their dependent sum is
`[-0.09, 0.01] eV`. No statistical independence or confidence level is
assigned. Nominal cancellation therefore does not establish oppositely signed
physical errors. The alternative 0.55 eV migration reference remains separate.

For the Ni controls, corresponding printing-box sum-discrepancy ranges are
`[0.05, 0.09] eV` for ADP and `[-0.16, -0.12] eV` for EAM. The tabulated
reference components sum to 2.90 eV; the text separately cites an activation
measurement of 2.88 eV. Those distinct reference chains must not be silently
interchanged. For Nb against same-work DFT, the sum-discrepancy range is
`[0.58, 0.62] eV`. The source uses different EAM and DFT supercell sizes
(8,191 and 249 atoms), and its fitting database includes a vacancy configuration;
these comparisons do not isolate physical error or establish held-out exposure.

Under a stated dilute-vacancy, common-prefactor model, equilibrium self-diffusion
contains both a vacancy-population factor and a jump-rate factor. An externally
fixed vacancy population removes formation energy from the jump-rate exponent.
Thus preserving `F + M` alone cannot certify both tasks. Actual diffusivity
also needs temperature, free-energy/entropy terms, prefactors and correlation
assumptions; none was invented or evaluated here. This is a standard conditional
distinction, not a new transport theorem.

Both PDF pins, the base/manifest and all four qualification pins matched.
Existing previews of Mishin pages 8–9 and Fellinger page 9 were visually checked;
additional method passages were read as retained text. Four exact nominal
decompositions and 64 endpoint checks passed, with a separate Number arithmetic
cross-check. These are same-agent calculations. No explicit qualification target
matched the selected IDs, but all original pooled-analysis exclusions remain.
No new corpus rows, studies, simulations or independent validations were added.
Existing source qualifications can express these dependencies; this review
does not justify a new inspector or demonstrate an improvement over the
source-aware baseline.

## Cu-Zr vitrification: phase ordering is not a kinetic decision

Reviewed 5 November 2026 UTC. The selection protocol was frozen at 00:07:21 UTC
before this visit's numerical inspection: all 14 retained Mendelev 2019 rows
and all 24 Paduraru 2007 rows. Selection used study/material/observable metadata;
these historical sources are not blinded or independent. The task was whether
reported liquid/glass agreement supports choosing a potential for vitrification.
The comparator was competent reading of the same tables and methods, including
fitting exposure and preparation history.

### Mendelev: an observed decision contrast, with a limited explanation

At Cu64.5Zr35.5 and 1573 K, Table II gives FS1/FS2 density discrepancies of
-0.1/-0.6 atom/nm³ against 59.2 +/- 0.3, and mixing-enthalpy discrepancies of
+0.032/-0.034 eV/atom against -0.185. FS1 has the smaller nominal absolute
discrepancy on both listed properties. The density's reported plus/minus has
not been given an assumed confidence interpretation; the close enthalpy
ordering is a nominal printed-value comparison, not a certified preference.
FS1 used this composition in development, whereas FS2 used Cu46Zr54.
At that latter composition, Table III gives density discrepancies +0.1/-0.6
atom/nm³ against AIMD at 1000 K, and mixing-enthalpy discrepancies +0.057/-0.004
eV/atom against experiment at 1573 K. These distinct temperatures, observables
and fitting roles cannot be combined into a single validation score.

Sections 4 and 7 report similar liquid structure and viscosity for the two
potentials. Nevertheless, the authors' 5,000-atom periodic-cell simulations
found Laves nuclei in FS1 after cooling from 1300 to 300 K at 10^9 K/s, and
growth after reheating to 900 K; FS2 did not show the corresponding growth.
Directly cooling the FS1 liquid to 900 K did not show growth either. Thus both
the competing crystal and preparation path matter. These are author-reported
executions, not simulations or curve measurements performed by this review.

A static-hull explanation is insufficient. Table I's MgZn2-prototype
formation-energy errors are -0.034 eV/atom for FS1 and -0.050 for FS2.
Section 3 reports that FS2 nevertheless makes the Laves phases metastable
relative to other compounds. Section 8 explicitly cautions that metastability
does not prevent nucleation: the stable competing compounds require
partitioning. The authors instead examine liquid-crystal free-energy
differences and interface kinetics. Their nucleation-rate estimate uses
approximations, including a Turnbull relation whose limitations they discuss;
this review does not promote it into a certified rate or cooling threshold.
The three retained Cu2Zr prototypes alone do not reconstruct a full hull.

Absence of observed nucleation in a finite simulation is not experimental
glass-forming validation. Section 4 states that its test alone cannot establish
that FS2 describes a good glass former. Section 9's broader composition result
also retains cooling-rate limits, and Section 8 cautions about rates below
10^9 K/s. The source supports a bounded preference for its reported simulation
task, not universal suitability.

### Paduraru: preparation-dependent agreement, not a second failed potential

The EMT study provides a contrasting evidence pattern. Its reported Cu50Zr50
glass transition is 620 K versus a cited experimental 670 K. Preparation used
25 K cooling steps averaging 0.54 K/ps, with Langevin thermalization followed
by NPT dynamics, and 2,048- and 42,600-atom cells. The experimental cooling
protocol is unresolved here. This is a protocol-dependent transition
comparison, not a matched equilibrium melting point.

For Table 4, nearest-neighbor distance discrepancies are
[-0.01, -0.09, -0.06] Å against EXAFS and [-0.12, -0.05, -0.03] Å against XRD.
Coordination discrepancies are [+0.34, +0.84, +0.19] and
[-0.16, +1.44, -0.21], respectively. These repeat the same predicted quantities
against two measurement methods. The zero-temperature modulus discrepancies
are +7.49 GPa (bulk) and -2.05 GPa (shear); the experimental state is not fully
audited. No uncertainty is invented for unreported values.

Table 3's L11 formation-energy discrepancy is -0.3795 eV/atom. The authors
acknowledge this exception and judge the layered structure unlikely to matter
for their glass application. That judgment is not a demonstrated
representation obstruction or evidence that this EMT potential fails the later
Mendelev cooling/annealing test. The papers use different potentials and
compositions; no artifact equivalence or cross-paper simulation ranking is
established. B2 fitting data remain distinguished from the stated glass tests.

### Disposition and verification

The hypothesis that liquid/glass agreement is sufficient for the vitrification
decision is not supported. The Mendelev source directly supplies a contrary
reported example, and Paduraru's agreement does not establish the missing
nucleation/path evidence. A competent source-aware baseline reaches this
conclusion without another metric or inspector. No incremental user-decision
accuracy, review-time benefit or novel mechanism has been demonstrated here.

The practical requirement is to preserve preparation history, competing-phase
scope, observation duration and the difference between reported non-observation
and verified glass-forming behavior when these sources enter a decision.
A downstream consumer that drops those qualifiers would justify a targeted
repair; this review has not yet observed such a product defect. Do not expand
the candidate-order checker into a glass-forming classifier.

The pinned base, manifest, both primary PDFs and all four qualification files
were checked. No qualification explicitly targeted these 38 IDs; all original
pooled-analysis exclusions remain. Exact decimal subtraction for all 38 rows
agreed with their retained discrepancies. Existing previews covered Mendelev
Tables I-III and Paduraru Tables 3-4/moduli; the glass-transition value and
methods were checked in retained text only. No previews were regenerated.
These are same-agent checks, not independent extraction or physical validation.
The bounded source/container read consumed 19,323,325 bytes under 32 MiB.
No corpus rows/studies, model executions or compatibility promotions were added.

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
- **Equilibrium observable and uncertainty:** a coexistence temperature needs phase
  composition/boundary identity before a liquidus comparison; a standard error
  of a numerical mean does not bound physical discrepancy.
- **Auxiliary-reference role:** an exact reference-to-target correction cancels
  the reference convention, but numerical convergence and target-model accuracy
  remain separate obligations. See the [linked Cu review](auxiliary-reference-evidence.md).
- **Generalization evidence:** an excluded fitting composition, an independent
  configuration set, and a benchmark used for selection have different roles.
  A small surrogate-to-DFT fitting error does not bound a downstream physical
  property without a sensitivity argument and a suitable physical reference.
  These are standard validation distinctions, not a new theorem.

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


## Prior-work disposition: dependencies and search certificates

A bounded methods review on 4 November 2026 compared the current specification
with primary treatments of measurement dependence and optimization certificates.

[JCGM 100:2008](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf/cb0ef43f-baa5-11cf-3f85-4dcd86f77bd6),
Section 5.2, equations (13)–(16), includes covariance terms for correlated inputs;
Section 5.2.4 explains how common standards or reference data introduce shared
dependence. Preserving primitive inputs is therefore established practice.
For our linear relation `M = Q - F`, finite-variance random variables would give

    Var(M) = Var(Q) + Var(F) - 2 Cov(Q,F),
    Cov(F,M) = Cov(F,Q) - Var(F),
    Var(F+M) = Var(Q).

These are exact covariance identities, not estimated uncertainties for the Fe
example. Its retained reporting envelopes do not supply a joint probability
model or numerical covariances. The deterministic analysis keeps the relation
`F+M=Q` and does not turn the inferred component into independent evidence.
This is an application of standard dependency handling, not a new uncertainty
propagation method.

[Boyd and Vandenberghe, *Convex Optimization*](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf),
Section 5.5.1, printed pages 241–242, bounds a feasible point's suboptimality
by its objective minus a valid dual lower bound. That certificate does not
require convexity; obtaining arbitrarily small duality gaps needs additional
conditions. Our finite-family application needs only a valid lower bound:
if `L_F <= m_F`, then `H_F(p_F)-m_F <= H_F(p_F)-L_F`.
No such lower bound was established for the inspected physical path searches.

The [existing path-selection inequality](anchored-barrier-evidence.md)
is ordinary order reasoning: pointwise offsets in `[a,b]` pass through the
maximum on each profile and then the minimum over the same candidate family.
Selected-profile gaps and the initial-energy difference enter by exact
decomposition. This finite argument needs no convexity, and it does not
establish coverage of continuous paths or an unknown candidate family.

The reviewed claims are therefore applications and formal specifications of
standard mathematics. No uncovered mathematical novelty was established by
this bounded review; that is not a literature-wide absence claim. Retain the
empirical failure map and tested evidence contracts, but require demonstrated
decision or review value before promoting a broader contribution. A proof of
the conditional inequality cannot supply missing source identities, shared
configuration coverage, search certificates or physical validity.

The primary PDFs were read through extracted text; screenshot tools did not
deliver inspectable pages, so no visual PDF check is claimed. Skaf and Boyd's
[2010 suboptimal-set paper](https://stanford.edu/~boyd/papers/expl_subopt.html)
was read at abstract level only; its convex-set exploration does not certify
the nonconvex physical searches considered here. No new corpus admission,
simulation, numerical uncertainty estimate or independent review occurred.

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

- **Guo 2022:** [2 February 2022 ChemRxiv preprint](https://www.cambridge.org/engage/api-gateway/coe/assets/orp/resource/item/61fb07df32e10e139bd27770/original/a-composition-transferable-machine-learning-potential-for-li-cl-k-cl-molten-salts-validated-by-hexrd.pdf),
  main-text fitting exclusion; supplement Sections A, F and G and Table IV,
  physical PDF pages 8 and 11–12. Final-article DOI
  10.1103/PhysRevB.106.014209 is bibliographic linkage, not version equivalence.
  Retained primary text reviewed 4 November; no new visual PDF review.
- **Attarian 2024:** [arXiv:2409.17869v1](https://arxiv.org/pdf/2409.17869v1),
  fitting/model lineage page 8; selection statement page 16 and Figure 3;
  Section 3.2 and Table 4; Table 5, page 26. Retained PDF pin, derived text and
  existing Table 5 preview checked 4 November. Final-article DOI
  10.1016/j.commatsci.2024.113409 is bibliographic linkage only.

- **Mahata 2022:** [accepted manuscript](https://par.nsf.gov/servlets/purl/10324339),
  fitting/methods pages 9-10 and 17-18; Table 6, page 19.
  DOI 10.1016/j.commatsci.2021.110902. Retained methods text and existing
  Table 6 preview reviewed 4 November.
- **Zhu 2021:** [published article](https://pure.tudelft.nl/ws/files/86400576/1_s2.0_S0927025620305565_main.pdf),
  interface method PDF page 3; Table 1/Figure 8 PDF page 8 (printed page 7);
  unary scope and sampling discussion PDF page 9.
  DOI 10.1016/j.commatsci.2020.110065. Retained methods text and existing
  method/table previews reviewed 4 November.

- **Zhu 2017:** [Phys. Rev. B 96, 224202](https://journals.aps.org/prb/pdf/10.1103/PhysRevB.96.224202),
  Section III A and Table V, PDF pages 6 and 8. Primary text reviewed
  4 November; page rendering was not completed and potential files were not pinned.
  This is one additional reviewed publication, not a corpus admission.

- **Bartók 2018:** [Phys. Rev. X 8, 041048](https://journals.aps.org/prx/abstract/10.1103/PhysRevX.8.041048),
  Table III and fault-environment discussion, PDF page 22; protocol page 21;
  representation and locality discussion pages 7 and 11. Retained published
  PDF pin, eight existing rows and page 22 preview checked 4 November.
  The paper-linked archive is an artifact-discovery lead, not verified
  executable identity or configuration provenance.

- **Mishin 2005:** [Acta Materialia 53, 4029–4041](https://doi.org/10.1016/j.actamat.2005.05.001),
  fitting Section 4.2, PDF page 7; Table 4, footnote h and activation discussion,
  page 8; Table 5 and separate activation reference, page 9. Existing page 8–9
  previews and retained PDF pin checked 4 November. Original experimental
  references were not independently reviewed.
- **Fellinger 2010:** [arXiv:1003.2210v2](https://arxiv.org/abs/1003.2210v2),
  Table I and fitting discussion; Section III B, PDF page 8; Table IV, page 9.
  Retained preprint PDF pin and existing page 9 preview checked 4 November;
  DOI 10.1103/PhysRevB.81.144119 identifies the linked journal article, not a
  separately verified final-version comparison.

- **Mendelev 2019:** [retained author manuscript](https://www.osti.gov/servlets/purl/1580710),
  DOI 10.1063/1.5131500. Tables I-III, PDF page 21; fitting Sections 2-3,
  pages 4-8; cooling/annealing Section 4, pages 8-10; interpretation and
  limits Sections 7-9, pages 12-17. Retained primary PDF pin, text and existing
  page 21 preview checked 5 November UTC. Original model files and numerical
  curves were not acquired or authenticated.
- **Paduraru 2007:** [author-hosted primary PDF](https://dcwww.fysik.dtu.dk/~schiotz/papers/AdvEngMater_9_505.pdf),
  DOI 10.1002/adem.200700047. Table 3, PDF page 2; preparation and glass
  transition, page 3; Table 4 and modulus comparison, page 4.
  Retained PDF pin and existing pages 2 and 4 previews checked 5 November UTC;
  page 3 was text-checked only. Original experimental references were not
  independently reviewed.

The current review links completed evidence; it does not refresh
original observation times. Only this reviewed literature/methods synthesis
and implementation references are included. Private campaign packets, raw
corpus archives, local paths and model/controller state are excluded.
