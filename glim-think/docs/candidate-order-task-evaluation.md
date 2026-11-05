# Frozen finite-candidate task evaluation

Protocol frozen on 5 November 2026 before discovery of the new numerical panels.
The evaluated implementation is Rhizo
`e2c1e956b701fece4b924eeb1598a9dbba3fb8e3`, especially
`atlas-distill/src/commands/candidate_order.rs` (blob
`2e6f451f646daefc6eb2233f75d2fa1b2170f096`) and the existing complete
application reader. No implementation tuning after outcomes is allowed in this
evaluation. Any discovered defect gets a separate repair/regression receipt.

## Question and comparison

For previously unused, source-reported point-defect energy panels, does the
existing checker improve the correctness or scope of a finite-choice conclusion
over a competent source-aware calculation? The task is to determine whether a
reported model preserves the DFT-lowest listed configuration under stated
tabulation bounds, while retaining ties, unknown identities, fitting exposure
and the distinction between a listed minimum and a physical global minimum.

The baseline is exact signed-gap/closed-interval reasoning on the same
transcribed inputs: subtract each pair, and compute possible, guaranteed and
unique minima directly from lower/upper endpoints. It receives the same source
qualifiers and does not assume independence, exhaustive search or physical
validity. There is no RMSE-only straw comparator. Identity/no intervention is
the default; no potential is refitted or recommended for execution.

This is a prospectively frozen **system task on published observations**, not a
prospective physical experiment, a human study or proof of model-training
holdout. Same-agent source transcription and adjudication are disclosed.
The source tables are held out from changes to this implementation; this alone
does not make the underlying models or experiments independently validated.

## Selection and stopping rules

1. Run only these two discovery queries, restricted to primary arXiv sources:
   - `"self-interstitial" "formation energies" "potential" "2025"`
   - `"self-interstitial" "formation energies" "potential" "2026"`
2. Inspect at most four distinct titles from these results, in returned order
   within the 2025 query followed by the 2026 query. Deduplicate DOI/arXiv
   versions. Retain exclusions, including failures; do not rank by effect size.
   Exclude publications already in the pinned corpus/source-review history or
   used to design the current map/checker. Screen identities before table review.
3. Select at most two eligible publications, with one first eligible table each:
   at least three named point-defect configurations of the same material and
   composition, comparable total formation energies in eV per defect, and DFT
   plus at least one named model. Use the first named model column in table
   order. No digitization of plots, mixture of reference columns, arbitrary unit
   substitution or replacement with another model family.
4. Read at most two full primary-source documents. A failed source request
   stops that source without an alternate-route retry. Missing tables,
   comparability or identity stay explicit. Fewer than two eligible panels is
   an incomplete evaluation, not a negative decision-value finding.
5. Treat printed scalar values as exact nominal inputs and separately use
   independent closed half-last-digit intervals, explicitly an assumed
   nearest-rounding convention, not reported uncertainty. Preserve printed
   lexemes, units, column/row identities, table/page anchors and source revision.
   An explicit source reporting rule supersedes the generic rounding assumption.
6. Retain source/model/training/protocol/candidate-set unknowns. A source hash
   identifies the reviewed text representation; it does not authenticate model
   weights or configurations. No private corpus bytes enter public CI.

The source-identity screen reads only the existing manifest/base/delta
representation, hash-verifies its pins and emits identifiers rather than
numerical outcomes. It has a 32 MiB read ceiling and creates no local files.
Discovery and transcription are bounded in memory. No local build/download,
new inference, simulation, auth change, cloud data write or stopped-job replay
is authorized by this protocol.

## Frozen outcomes and implementation checks

For each nominal and rounding-bound panel, record:

- Baseline and checker signed pair orders; possible/guaranteed/unique minima;
  and whether the model and DFT have the same unique listed minimum.
- Explicit unknowns and source qualifications retained or lost at the complete
  CLI/report-reader boundary. No automatic scientific/global-minimum claim.
- Exact agreement, disagreement and abstention counts. A difference is
  adjudicated against the source and interval specification; it is not
  automatically credited to either method.
- The final task answer's scope and whether the checker adds a justified
  conclusion unavailable to the competent baseline. Equal conclusions are an
  explicit negative result for incremental decision accuracy on these cases,
  not proof of no possible utility.
- Source-preparation errors, eligibility stops and developer familiarity.
  Do not count missing inputs or an all-abstention policy as success.

Use the current Rust CLI and full existing validator/renderer in hosted CI with
public, reviewed small fixtures. Respect the existing 512 KiB/ten-second CLI and
bounded acceptance-step ceilings. No benchmark/model/physical execution is
implied. Automated wall time is not human review effort. No claim of saved-run,
knowledge-graph, authenticated browser or deployed acceptance follows from this
checker comparison alone; those have separate versioned evidence.

The purpose is to close a task-evaluation gap, not manufacture a paper or force
positive improvement. Preserve a complete negative result. An eligibility or
source-access failure leaves the task evaluation unresolved.
