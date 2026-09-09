# TMS 2027 and Lupine Science Progress Review — WORKING CONTRACT (authoritative for the manuscript sprint)

**Date:** 2026-09-01 (captured into repo 2026-09-09)
**Meeting:** TMS 2027 Annual Meeting & Exhibition
**Accepted contribution:** Poster, *From Transferability to Prediction: The Error Geometry of Interatomic Potentials*
**Proceedings manuscript deadline:** 2026-09-09 (TODAY — submit this evening)

## Executive decision

There is a strong TMS paper in the Lupine record, but it is not the universal-law paper described by the accepted abstract.

The defensible contribution is a reference-, stability-, lineage-, and protocol-aware framework for measuring interatomic-potential error, together with a documented sequence of negative and conditional results. The program has shown that attractive low-dimensional and correction claims can disappear under better denominators, physical stability gates, coupling-aware nulls, genuinely held-out tests, and independent reference checks. That self-correction is the paper.

The proposed central claim is:

> In cubic-metal elasticity, prediction-error covariance is often anisotropic, but neither a universal hyper-ribbon nor a transferable correction axis is established. Transferability must therefore be qualified locally—by model family, observable, material class, reference convention, and data exposure—and tested prospectively with stability gates and independent density-functional-theory anchors.

The all-electron PBE/r2SCAN elastic anchor should not be made a dependency of the September 9 manuscript. It has not run, its registered 15-metal roster and the completed 16-metal benchmark overlap on only 14 metals, and the staged runner/analysis chain is incomplete. It belongs in the paper as a preregistered closing experiment unless those issues are fixed first.

## Overall scientific status

| Program | Status | What is defensible now | What is not defensible now |
|---|---|---|---|
| Classical elastic corpus | **Usable substrate; analysis rebuild required** | 965 KIM model objects queried; 559 Born-stable model–element tensors retained; 423 distinct KIM model IDs; 1,677 scalar elastic constants across 15 metals | "Roughly 900 published potentials," "559 independent potentials," or 1,677 independent observations |
| Classical error geometry | **Descriptive signal; universal classifier invalid** | Strong anisotropy in several elastic residual clouds; median reported participation ratio 1.09/3 as a descriptive statistic | Universal hyper-ribbon, log-linear sloppy-model universality, or 98% systematic-error inference from centered PR |
| Live-ledger elastic null test | **Promising but not reproducible from current repositories** | Narrative records a pooled shared-stiffness signal bounded to the elastic block | Exact PR, null, and correction numbers in a manuscript until the 352-row snapshot, scripts, seeds, outputs, hashes, and refuter record are recovered |
| Random-effects/meta-analysis | **Descriptive only; refit required** | Strong heterogeneity among elements is visually and descriptively clear | Current Fisher-z confidence intervals, prediction interval, or any inference treating three Cij rows and related model versions as independent |
| BCC/FCC and d-band explanations | **Retracted/refuted** | Sampling depth, contamination, and reference composition are important confounders | Causal BCC/FCC shield, d-band driver, or identified causal mechanism |
| MatPES 4×2 functional study | **Mixed result** | Initial functional-label association; stricter Round-2 H1/H2a failures; explicit uncertainty and missing anchor | Causal exchange-correlation attribution or a conserved cross-paradigm direction |
| 16-metal elastic benchmark | **Completed against curated targets** | 128 model/functional/metal cases; raw aggregate MAE 17.84 GPa; registered failures reported | All-electron truth, clean r2SCAN truth, or four fully independent architectures |
| Elastic correction | **Oracle ceiling; deployment failed** | A training-derived direction can capture held-out residual energy when the held-out target supplies the coefficient | Reference-free correction, unconditional no-harm, or prediction based on 17.84→10.36 GPa |
| Cross-property Y-matrix | **Strong negative/conditional result** | Coupling-aware nulls prevent false positives; low-dimensionality not confirmed in 4/6 tests and no shared mode survives 3/3 pair tests | Universal cross-property ribbon or transfer of one correction across property families |
| Round-3/4 elastic gates | **Negative, well documented** | Frozen correction improves same-class lattice constant in a narrow setting; broad property-win criteria fail | Broad elastic-tensor correction or general runtime license |
| Environment error field | **Promising separate draft** | Blind coordination-field test reports r=0.906 over 36 cells; useful nonlinear alternative to a global linear ribbon | Generalization beyond the tested FCC/mixed-reference scope or broad force-level correction without external replication |
| Z1 migration barriers | **Strong negative result** | Four foundation models fail a 40 meV DFT-NEB gate with MAE 135.0–242.5 meV; sign imbalance is model-dependent | "Every completed path underpredicts" or universal barrier underprediction |
| Sparse barrier anchors | **Same-engine mechanism result** | Reference-profile simulation is promising; 129 GPAW points on 23 short paths establish sparse-vs-dense same-engine reconstruction | External DFT accuracy, DFT-grade accuracy, or a prospective long-path savings claim |
| Z3 adsorption correction | **Strong negative result** | All four validation-selected corrections worsen untouched holdout MAE | General delta-correction efficacy from the frozen small-budget design |
| Formal Lean layer | **Strong guardrail** | Conditional algebra, failure boundaries, and claim contracts are machine checked | Empirical validation of theorem hypotheses or "proof" that a physical correction works |
| Public site/ledger | **Scientifically out of sync** | Valuable public record and provenance surface | Several headline values and statuses lag later errata, null-aware results, and the accepted poster status |

## The central denominator correction

| Quantity | Count | Meaning |
|---|---:|---|
| KIM model objects queried | 965 | Retrieval/search universe |
| Born-stable model–element tensors retained | 559 | Analysis records, not unique publications or models |
| Distinct KIM model IDs in the retained CSV | 423 | Closest current model-object count |
| Author/year-style short labels | 233 | Coarser labels that can merge model versions or parameterizations |
| Scalar Cij values | 1,677 | 559 tensors × {C11, C12, C44}; dependent components |
| Multi-element geometry groups | 42 | Groups with at least three materials in the committed revalidation JSON |

The proceedings paper should name the unit every time a sample size appears. "Potential," "model ID," "parameterization," "lineage," "model–element tensor," and "elastic-constant component" are not interchangeable.

## Why the current universal hyper-ribbon result does not survive audit

The committed 42-group geometry file material counts: 3 materials → 21 groups; 4 → 3; 5 → 5; 6 → 3; 7 → 3; 8 → 2; 9 → 3; 12 → 2.

For the 21 groups with three materials, mean-centering three observations in a three-variable space forces covariance rank to at most two. The current implementation then tests already sorted eigenvalues for monotonic decay; monotonicity is therefore built in, and a two-eigenvalue log spectrum is exactly linear. Those groups are structurally predisposed to pass the classifier. All 42 reported PR uncertainty intervals reach at least 2, and half reach approximately 3. The point estimate "all are low-dimensional" is not an uncertainty-supported universality result.

There is also a provenance gap: the stored monotonicity values do not match the current Rust implementation for strictly descending eigenvalues, and no committed generator reproduces the 42-group JSON.

Use **anisotropic elastic-error covariance** or **low-dimensional descriptive structure**, not **universal hyper-ribbon**. The sloppy-model hyper-ribbon is a parameter-induced model manifold; a covariance ellipsoid across published residuals is not automatically the same object.

## Error measurement that the manuscript should standardize

### 1. Define the signed residual and its scale

For model i, material m, property k, reference tier r, and protocol p:

e_imk^(r,p) = (ŷ_imk^(p) − y_mk^(r,p)) / s_mk^(r,p)

Report at least two scales: absolute physical units (GPa) for decision relevance; a preregistered dimensionless scale (relative error or reference uncertainty) for cross-property geometry. Do not compare classical PR from absolute GPa residuals with MLIP PR from relative residuals as if they were the same quantity.

### 2. Separate bias, disagreement, and total risk

μ = E[e], C = E[(e−μ)(e−μ)ᵀ], M = E[eeᵀ] = C + μμᵀ.

- Centered covariance C measures inter-model disagreement geometry.
- Mean vector μ measures shared signed bias.
- Uncentered second moment M measures total quadratic risk — the object needed for a shared-bias fraction.

For a common reference, centered residuals satisfy e_i − ē = ŷ_i − ȳ: the reference cancels. Centered PCA therefore cannot by itself establish accuracy, inherited DFT bias, or closeness to experiment. The current inversion of median centered PR into "about 98% systematic error" must be removed.

### 3. Treat failures as outcomes

Born instability, failed lattice/strain fits, convergence failures, and missing properties must appear in the primary denominator funnel. Geometry can then be reported conditionally among valid tensors, with a separate failure-rate endpoint.

### 4. Use matched physical nulls

Every geometry claim should be compared with nulls that preserve: same n, d, missingness mask, and marginal scales; elastic coupling and Born-stability constraints; material and property families; model lineage/version dependence. The Y-matrix result is the clearest evidence: raw mode cosines as high as 0.96 fell inside a coupling-aware null reaching 0.98.

### 5. Make prediction genuinely prospective

A correction test must hold out the full deployment unit—preferably an entire model lineage and/or material—while learning normalization, basis direction, coefficient estimator, gates, and hyperparameters inside the training fold. The current 69% and 17.84→10.36 GPa results use the held-out target to estimate the correction magnitude; they are oracle directional ceilings, not target-free prediction. Required comparators: raw prediction, mean/family correction, diagonal or ridge baselines, random basis, abstention baseline. Report both mean improvement and number harmed.

## DFT-anchor audit

### Anchor taxonomy
1. **Prediction controls:** completed MACE, CHGNet, Orb, or related model outputs. Not truth.
2. **Reference targets:** literature DFT or experiment. May be mixed, approximate, finite-temperature, or convention-mismatched.
3. **Computed ab-initio anchors:** new calculations under one frozen protocol with raw outputs and convergence evidence.

### All-electron elastic anchor — Status: pending and not execution-ready
Registered 15 metals: Al, Cu, Ni, Ag, Au, Pt, Pd, **Pb**, Fe, Cr, Mo, W, V, Nb, Ta. Completed 16-metal benchmark: Ag, Al, Au, **Ca**, Cr, Cu, Fe, Mo, Nb, Ni, Pd, Pt, **Sr**, Ta, V, W. Intersection = 14. Blockers: expected PBE/r2SCAN result JSONs do not exist; startup script calls an uncommitted FHI-aims runner; convergence file and WIEN2k cross-check workflow absent; two advertised analysis comparisons incomplete, a third absent; magnetic order/starting moments/convergence failures/exclusions not operationally frozen; ACWF comparison uses (V0,B0,B1) vs this anchor's (C11,C12,C44).

Safe wording for the 16-metal benchmark:
> The completed 16-metal, 128-case benchmark measures MLIP discrepancy against a curated 0 K target table comprising mostly published PBE tensors, a PW91 fallback for Au, and approximate scalar-rescaled r2SCAN targets. The preregistered paired all-electron PBE/r2SCAN elastic-constant anchor has not yet been executed, so the decomposition of fitting error from functional and reference-standard offsets remains pending.

### Barrier anchors — safe wording:
> On 30 chemistry-held-out DFT-NEB paths, all four tested foundation potentials failed the 40 meV barrier gate. Sparse reference-profile simulation was promising, while a 23-path GPAW campaign established same-engine reconstruction only; GPAW–VASP convention wander prevented external validation, and seven large-path tests remain deferred.

## Audit of the accepted abstract

| Accepted abstract claim | Verdict |
|---|---|
| Finite-data models must transfer beyond calibration | Keep |
| OpenKIM/NIST as institutional answers | Reframe as repositories, tests, and provenance infrastructure |
| Failure is a measurable object requiring field standards | Keep as thesis, not novelty |
| Roughly 900 published potentials | Replace with the denominator funnel |
| Random-effects meta-analysis reveals the hyper-ribbon | Remove |
| Drivers identified by causal inference | Remove |
| Same sloppy-model hyper-ribbon | Replace with anisotropic elastic-error covariance |
| Survives 14/15 metals across classical→MLIP | Withdraw |
| Makes transferability predictable | Replace with conditions required for prospective prediction |
| Falsifiability and public self-correction | Keep, in neutral evidentiary language |

NOTE: The repository also contains a stale TMS file describing an oral talk in a different symposium with a different title. It must be archived or replaced so it cannot be mistaken for the accepted poster record.

## Recommended TMS manuscript

### Title
If the accepted title must remain unchanged, keep it and make "prediction" the endpoint of a qualification protocol rather than a result already achieved:
> **From Transferability to Prediction: The Error Geometry of Interatomic Potentials**
If TMS permits a title refinement:
> **From Transferability to Prediction? A Reference-Resolved Audit of Interatomic-Potential Error Geometry**

### Four-panel paper/poster structure
1. **Denominator and provenance funnel** — 965 queried → 559 stable model–element tensors → 423 KIM IDs → 42 multi-element analysis groups. Show instability and missingness as outcomes.
2. **Geometry under finite-sample and physical nulls** — Plot PR against group size, highlight the 21 n=3 groups, recompute absolute/relative/standardized versions with coupling/missingness-aware nulls.
3. **Cross-paradigm and correction falsification** — Non-transfer of classical alignment to foundation models; the 14.55→63.40 GPa global-operator failure. Clearly separate the 17.84→10.36 GPa oracle ceiling.
4. **Qualification and DFT-reference stack** — model→parent-DFT, DFT-functional/implementation, DFT→experiment discrepancies; mark the paired all-electron elastic anchor as pending.

Keep barrier, adsorption, environment-field, and formal-theorem programs in one compact discussion table. Do not pool them numerically with elasticity.

### Revised proceedings abstract (214 words)

Transferability is often summarized by a scalar error pooled across models, materials, and properties. We audit a vector alternative: the covariance geometry of errors in the three independent elastic constants of cubic metals. From 965 OpenKIM model objects queried, 559 mechanically admissible model–element tensors were retained across 15 elements; 42 potential groups covered at least three elements. These groups show strong descriptive anisotropy, with a median participation ratio of 1.09 out of 3. Registered stress tests, however, sharply limit the interpretation. Half of the 42 classical groups contain only three materials, which rank-limits a centered three-variable covariance; the classical analysis uses absolute errors whereas the foundation-model analysis uses relative errors; and cross-property participation-ratio and mode-alignment tests do not exceed coupling-aware nulls. After Born screening, classical alignment does not predict foundation machine-learning-potential alignment (Spearman correlation 0.26, p=0.34), while a global leave-one-out elastic correction increases mean error from 14.55 to 63.40 gigapascals. We therefore do not infer a universal hyper-ribbon or generally predictable transferability. The supported conclusion is narrower: error geometry is measurable only relative to a specified model family, observable, material class, and reference convention. We propose a qualification protocol combining vector residuals, stability gates, dependence-aware resampling, provenance-locked references, prospective prediction tests, and all-electron density-functional-theory anchors; the required elastic anchors remain pending.

**Keywords:** interatomic potentials; transferability; error measurement; elastic constants; model qualification

## Claim freeze for the proceedings paper

### Keep
- Exact denominator funnel and provenance.
- Mechanical instability and harness failure as endpoints.
- Descriptive anisotropy with finite-sample caveats.
- Registered null and negative results.
- Mixed outcomes of the MatPES study.
- Oracle-versus-deployable correction distinction.
- Pending all-electron elastic anchor.
- Correction scope is local to observable, class, reference, and protocol.
- Machine-checked theorems as conditional guardrails.

### Remove or retire
- roughly 900 published potentials;
- 559 independent potentials or 1,677 independent observations;
- universal hyper-ribbon or sloppy-model universality class;
- centered PR implies 98% systematic error;
- 14 of 15 and classical-to-MLIP survival;
- causal BCC/FCC, d-band, or exchange-correlation attribution;
- deployable correction or unconditional no-harm;
- all-electron elastic anchor completed;
- four independent MatPES architectures;
- universal barrier underprediction;
- sparse DFT "strong win," "DFT-grade accuracy," or realized 72.4% savings;
- empirical claims justified merely by Lean proofs.

## Remaining execution items (Sep 9 — today)

| Item | Deliverable | Go/no-go condition |
|---|---|---|
| Recovery attempt | 352-row live-ledger snapshot, Q1 scripts, null outputs, seeds, hashes | If not recovered intact, OMIT its exact numbers |
| Geometry recompute | Classical geometry under absolute, relative, standardized gauges; matched n/d/missingness/lineage nulls | No strict hyper-ribbon claim unless it clears the frozen null across strata |
| Canonical results | One canonical results JSON + four figures; every number bound to source rows | Public/manuscript figures from the same object |
| Full draft | Complete proceedings draft around measurement + qualification | DFT anchor described as pending, not promised |
| Independent pass | Statistics/physics/referee review | Every headline has estimand, unit, denominator, reference, holdout definition |
| Revise + poster layout | Revised manuscript | No stale oral/symposium record in submission materials |
| Compile | Reviewer PDF, TMS format, 150–250 word abstract, ≥3 keywords, references, data statement, copyright form | Clean build and claim-lock check |
| Submit | Final read and submission | Submit only the evidence-frozen version |

TMS proceedings requirements: manuscript deadline September 9, 2026; copyright form with submission; LaTeX source package + reviewer PDF; abstract 150–250 words; ≥3 keywords; references; data statement.

## Key source locations

- Classical manuscript and corpus: `lupine/paper/immi-paper.tex`, `lupine/atlas-distill/benchmarks/kim_elastic_results_all.csv`, `nist_populated_all.csv`
- 42-group geometry: `lupine/replication/error-geometry/data/classical/manifold_revalidation_42potentials.json`
- Round-2 manuscript: `lupine/paper2/ProjectionLaw_Round2.md`
- All-electron anchor spec/blocker: `lupine/replication/error-geometry/prereg_r2b_dft_anchor_spec.md`, `lupine/docs/science/h3_blocker.md`
- Cross-property results: `lupine-rhizo/docs/plans/y-matrix-confirmatory-results-2026-07-01.md`
- Red-team errata: `lupine-rhizo/docs/plans/2026-07-13-errata-and-red-team-dispositions.md`
- Round-3/4 correction reports: `lupine-rhizo/data/candidates/round3/ROUND3_REPORT.md`, `round4/ROUND4_REPORT.md`
- Barrier sparse-anchor verdict: `lupine-rhizo/docs/analysis/z1-union-campaign-verdict.md`
- Negative-results preprint: `lupine-rhizo/paper/negative-results-preprint/manuscript.tex`
