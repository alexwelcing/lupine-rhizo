# Research Index

Use this page to see what Lupine has investigated, what the evidence supports,
what remains open, and what changed after a correction. Start with the question
you want answered; each route leads to a report or ledger already in the Library.

## See the research

| What you want to see | Start here | What it tells you |
| --- | --- | --- |
| Where the claims stand | [The Hypothesis Ledger](./conjectures/ledger.md) | Supported, open, refuted, and corrected claims, with the reason each moved. |
| An experiment's conclusion | [Z1 Union Campaign — Verdict of Record](./analysis/z1-union-campaign-verdict.md) | A recorded verdict, its reference standard, limitations, and unresolved questions. |
| What running it cost | [Z1 Union Campaign — Measured Cost Ledger](./analysis/z1-union-cost-ledger.md) | Measured runtime and estimated cloud-equivalent/electricity costs; keep them separate from projected savings and actual billing. |
| A result that did not hold | [Born-Screening Re-Audit](./born-screening-re-audit.md) | Which earlier conclusions were narrowed, what remains supported, and which gates are still open. |
| What is formally checked | [Formal Proof Ledger](./formal-proof-ledger.md) | The machine-checked statements and their scope. A theorem does not by itself validate an empirical model. |
| How to check a result yourself | [Reproduce Our Results](./reproduce.md) | Reproduction paths, required inputs, and the commands behind the records. |
| How the program changed | [Changelog & Progress](../CHANGELOG.md) | Dated changes to the work; a recorded change is not automatically a deployed release. |

## Dated reports to open

These dates come from each report's title, execution line, or publication line.
They are report dates, not deployment dates or a live feed of new experiments.
The status column preserves the publication catalog's label; the report's scope
and qualifications determine what that label supports.

| Report date | Report | Catalog status | What to look for |
| --- | --- | --- | --- |
| 2026-07-24 | [Z1 Union Campaign — Verdict](./analysis/z1-union-campaign-verdict.md) | Supported | Same-engine self-consistency, with external-reference accuracy and remaining gates explicitly separated. |
| 2026-07-24 | [Z1 Union Campaign — Cost Ledger](./analysis/z1-union-cost-ledger.md) | Supported | Measured wall time, assumed price rates, and per-path costs. This is not a cloud invoice. |
| 2026-07-19 | [Z1 Barrier Campaign — Round 4](./validation/z1-barrier-campaign-round4-results.md) | Refuted by us | The preregistered accuracy gate failed on both precision chains; incomplete paths remain visible. |
| 2026-07-19 | [Z3 Adsorption Campaign — Round 4](./validation/z3-adsorption-delta-campaign-round4-results.md) | Refuted by us | All four validation-selected corrections worsened held-out accuracy relative to their raw baselines. |
| 2026-06-20 | [Born-Screening Re-Audit](./born-screening-re-audit.md) | Self-corrected | Invalid tensors narrowed earlier claims; open recomputation gates remain open. |

## Follow a claim from question to evidence

1. Read its status and scope in [The Hypothesis Ledger](./conjectures/ledger.md).
2. Follow the linked experiment or report. Check the material, model, reference
   standard, sample size, and limitations before comparing numbers.
3. Read the relevant [corrections](./born-screening-re-audit.md) and
   [methodology](./methodology.md). A failed test or narrowed claim is a result too.
4. Use the [proof ledger](./formal-proof-ledger.md) for mathematical obligations
   and the [reproduction guide](./reproduce.md) for empirical checks. These answer
   different questions.

For example, the [Z1 verdict](./analysis/z1-union-campaign-verdict.md) explicitly
separates a same-engine self-consistency check from external-reference accuracy.
Read that distinction alongside its [cost ledger](./analysis/z1-union-cost-ledger.md)
before treating the campaign as an accuracy or savings claim.

## Open work and working papers

- [Internal Science Program](./internal-science-program.md): the questions the
  program intends to investigate.
- [Classical-to-MLIP Transfer](./conjectures/hyper-ribbon-mlip-transfer.md): a
  hypothesis page with its own status and scope.
- [Fe Magnetic MLIP Failure Mode](./conjectures/fe-persistent-outlier.md) and
  [Au Escape](./conjectures/au-mlip-escape.md): follow their evidence and open gates.
- [MLIP Flywheel Readiness](./mlip-flywheel-readiness.md): what is ready and what
  still needs evidence before the next promotion.
- [Working Papers](./papers-working.md): manuscripts and companion material;
  a working paper is not a peer-reviewed publication.
- [Academic Review](./reviews/academic-review-projection-law-2026-06-16.md) and
  [Adversarial Review](./reviews/adversarial-review-projection-law-2026-06-16.md):
  scrutiny of the paper suite and its unresolved issues.

## Reading status correctly

- **Proposed / open:** a question or incomplete investigation, not a validated finding.
- **Supported:** evidence supports the stated scope; it is not a claim of universal validity.
- **Refuted / self-corrected:** preserve the failed test and the correction alongside the original story.
- **Proven (Lean):** a machine-checked mathematical statement under its stated assumptions.
- **Live evidence:** a catalog label for an evolving report. The text in this
  Library is still a publication snapshot; the label does not prove that a job
  is running now or that the page is current to this minute.

An agent's confidence or an answer generated by a model is not measured evidence.
A task marked complete is not a scientific verdict. Follow the source receipts.

## Published Library and live research work

The Library reads a curated, versioned content bundle from the science repository.
It changes when that bundle is regenerated, synced into the Library reader, built,
and deployed. Upgrading glim-think's models does not automatically publish new
research here.

The live glim-think ledger separately holds hypotheses, claims, questions,
benchmark records, and agenda tasks. Its knowledge-library API can list those
records and export an OKF bundle. Those records need publication selection and
review before entering this public Library; internal task payloads, model output,
and private provenance should not be copied wholesale.

Use the Library for published explanations and evidence trails. Use the research
control plane for current job state and unreviewed work. Neither surface should
imply that a queued experiment ran, or that an exported article is already live.

## Background reading

These imported technical reviews inform the research program. They are background
reading, not primary Lupine results; the claim state belongs in the
[Hypothesis Ledger](./conjectures/ledger.md).

### Multi-fidelity, UQ & ensembles
- [`multi_fidelity_uq_glimMER_report.md`](./multi_fidelity_uq_glimMER_report.md) — cross-potential
  meta-analysis and systematic bias correction; the "glimMER" PCA-of-errors correction idea.
- [`bayesian_active_learning_report.md`](./bayesian_active_learning_report.md) — Gaussian-process
  surrogates and active learning for potential selection at scale.
- [`weather_climate_ensembles_report.md`](./weather_climate_ensembles_report.md) — multi-model
  ensemble-weighting strategies ported from climate science.

### Error prediction & topology
- [`gnn_error_prediction_report.md`](./gnn_error_prediction_report.md) — GNNs predicting where a
  potential fails from local chemical environment.
- [`tda_error_landscapes_report.md`](./tda_error_landscapes_report.md) — persistent homology of
  high-dimensional error surfaces.

### Benchmarking & physical models
- [`phonon_benchmarking_report.md`](./phonon_benchmarking_report.md) — phonon spectra as a
  "gold standard" validation; executive summary in [`KEY_FINDINGS_SUMMARY.md`](./KEY_FINDINGS_SUMMARY.md).
- [`rg_coarsegraining_report.md`](./rg_coarsegraining_report.md) — renormalization-group coarse-graining
  for deriving effective potentials.

### Theory & information
- [`sloppy_models_report.md`](./sloppy_models_report.md) — Fisher-information eigenvalue analysis;
  stiff vs. sloppy directions (the mathematical background for the hyper-ribbon — see
  [`science/objects.md`](./science/objects.md)).
- [`info_theoretic_report.md`](./info_theoretic_report.md) — Kolmogorov complexity, rate-distortion,
  and entropy applied to model selection.

### Program context
- [`funding_landscape_report.md`](./funding_landscape_report.md) — federal materials-informatics /
  UQ funding landscape (2025–2026).
