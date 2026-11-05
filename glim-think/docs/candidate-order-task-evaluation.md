# Frozen finite-candidate task evaluation

Protocol frozen on 5 November 2026 before discovery of the new numerical panels.
The evaluated implementation is Rhizo
`e2c1e956b701fece4b924eeb1598a9dbba3fb8e3`, especially
`atlas-distill/src/commands/candidate_order.rs` (blob
`2e6f451f646daefc6eb2233f75d2fa1b2170f096`) and the existing complete
application reader. No implementation tuning after outcomes is allowed in this
evaluation. Any discovered defect gets a separate repair/regression receipt.

## Discovery amendment before any numerical outcomes

The two original year-qualified queries returned no results on 5 November 2026.
No title, numerical panel or model outcome was observed, and no primary-source
request failed. Preserve the original protocol at commit
`8d5c4abf69ed264f832aae9ad39200a2ccd2f445`; this is not a source retry or a
change to physical/table eligibility. Publication year is not part of the
finite-candidate contract. The replacement discovery pass therefore removes
that irrelevant restriction and uses the two queries below. All other
eligibility rules, four-title/two-document limits, comparator, frozen
implementation and outcome criteria remain unchanged. No additional discovery
pass is authorized by this amendment.

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
   - `"self-interstitial" "formation energies" "machine learning"`
   - `"self-interstitial" "formation energies" "molybdenum"`
2. Inspect at most four distinct titles from these results, in returned order
   within the machine-learning query followed by the molybdenum query. Deduplicate DOI/arXiv
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

## Recorded outcome: selection incomplete

The initial two year-qualified queries and the two amended queries each
returned an empty search result through the available web search tool. No
titles were selected, no full primary-source document was requested, and no
numerical table or checker output was inspected. This is a discovery outcome,
not evidence that suitable publications do not exist, and not a negative
decision-value result. The amended discovery pass is closed; do not repeat it
or substitute another route silently. No source HTTP/access failure occurred
in these four queries. Inspecting the metadata of an available second search
interface did not make another search request.

The original protocol commit
`8d5c4abf69ed264f832aae9ad39200a2ccd2f445` and pre-outcome amendment
`dd6b14a022a1cdeb6566249ad1471b8a373cef71` remain immutable. The branch's
checker implementation remains unchanged from `e2c1e956b701fece4b924eeb1598a9dbba3fb8e3`.

The source-identity exclusion screen verified 90 retained base/delta files plus
the manifest, reading 15,752,232 bytes under its 32 MiB ceiling. It collected
518 identifier/citation/title strings in memory without presenting numerical
outcomes. These are identity strings, not new studies or an independence audit.
No private files were uploaded. The manifest remains SHA-256
`6dc5596e771de4448bedc0ad5240769fdc8d41424f7b85f2cb277ab6eb5eba73`.

## Retained evaluation audit

Before this protocol, a separate bounded read-only audit selected the two
latest graph-context retrieval evaluations and an explicitly withheld-task
evaluation by their roles/names, without selecting on results. Its 512 KiB
aggregate read ceiling initially admitted three files (507,671 bytes), then
stopped before the 205,630-byte pass66 outcome. A stat-only check established
that the selected pass41 protocol fit the same remaining allowance; reading
its 5,765 bytes brought the final total to 513,436 bytes across four files.
The 25,469-byte pass41 outcome did not fit and was not read. Neither result
file was retried, and the ceiling was not enlarged or bypassed.

- Pass67 protocol, frozen 18 October 2026 11:42:39 UTC, SHA-256
  `149b3260ffbe249fd60779ef727c0dff6779efc653c5e95690fa417ed18e5944`,
  explicitly describes eight familiar tasks across six earlier studies.
  Requirements were frozen before the new retrieval outputs, but source facts
  were already known. It expressly disclaims independence, blindness and
  measurement of human/model decision mistakes.
- Its retained evaluation SHA-256
  `357d5e955ba5387598490c523aee5df0e7b3f8171b6acd540c8489948765be01`
  binds that protocol and reports an unchanged graph. Lexical retrieval,
  breadth-first expansion and balanced qualification traversal each return
  all 13 required context items and all eight complete premise bundles.
  This is a complete tie on the declared coverage measures, not improved
  decision accuracy. The exporter pin is
  `d464acb77ff780a45abb3a57900c6f0fcb3287cf68358adb089fceb3e7ee7fb6`.
- Pass66 protocol SHA-256
  `3807f53a5539da60806d619356f313cc0d4c5ca018ba3aea0f82ecfc3eb87792`
  explicitly calls its six cases familiar and non-prospective. It measures
  required-context coverage and cap diagnostics, not answer correctness.
  Its outcome was not read in this bounded audit.

- Pass41 protocol SHA-256
  `8fd1da489f75a0caeeed8175a4ca474aa14cd59421e30225aa3a2f40e814b636`,
  frozen 18 October 2026 05:40:58 UTC, specifies twelve evaluator-withheld
  implementation-acceptance cases across three retained studies. It records
  that the evaluator had not inspected the implementation and had not disclosed
  the oracle to the implementer. Its comparator is exact task-aware Fraction
  arithmetic; superiority over correct manual arithmetic and blind physical
  validation are explicitly disclaimed. This is a meaningful historical
  acceptance lead, but the protocol alone does not establish observed results,
  current-version integration or a prospective physical holdout.

These results justify retaining the coverage evidence at its actual level;
they do not close the current prospective task-value requirement. The earlier
graph context exporter is a separate historical implementation, not the current
runtime claim-graph fix. Neither this audit nor the empty discovery pass adds
corpus rows, an independent validation, a simulation or a positive scientific
finding.

The next evaluation needs a concretely identified, accessible case set before
committing to a new acquisition protocol, while fixing its task rule and
implementation before inspecting outcomes. Current source-aware arithmetic
and the exact checker implement the same interval decision contract; equal
answers would be expected and cannot alone establish reduced review effort or
new physical accuracy. Any proposed value claim must name an actual workflow
failure or measurable task consequence. Keep the full program active; neither
a coverage tie nor an incomplete selection is completion.


## Separate acceptance-harness failure

Documentation head `1d02e88a3657643d8ca67f6abb36dfff349acb77`
passed Verify, glim-think and Lean. Atlas run `41948690407` passed all 141
Rust tests and all 23 individual CLI/browser checks, but its browser suite's
after-hook failed with `ENOTEMPTY` while removing Chrome's temporary profile.
The overall run therefore failed; deployment job `126987905987` was skipped.
The earlier cleanup signalled Chrome, waited for its main-process exit, and
could delete the profile while browser writers were still shutting down. The
repair requests graceful `Browser.close`, observes the child close event,
and bounds forced termination before deleting the test-owned profile. It
performs no deletion retry and preserves the profile if closure is unobserved.
This changes test teardown only, not the frozen checker/reader or scientific
outcomes. The failed run remains immutable and is not replayed.


## Subsequent targeted historical-lineage assessment

A separate 128 KiB/four-file assessment followed the protocol's specifically
withheld-oracle claim; it did not rerun an evaluation or retry a failed source.
It read three files totaling 47,116 bytes and stopped at an implementation-pin
mismatch. The pass41 result SHA-256
`54e5b6d926f037f1af5387255dc6e70210df48bfec5a46cce223e83d6782f9e9`
reports 12/12 passes and binds the inspected input/oracle/database pins.
Freeze receipt `395fc9d5a65737b40b1129e08e4c367bb7d2ca21423c2731fa96ac31add5a7d2`
names calculator SHA-256
`f0005c70d969bab6f0662c0c2292834a8165a229623c4023b0de7fc456e722f1`.
The current local calculator instead hashes to
`dc0d4e956ab640ebb21a4da5816310315ecfc083e7283c54308ff66dea64dbf0`.
Historical reported acceptance therefore remains distinct from current-version
acceptance. No claim of superiority over its exact manual baseline follows.

Both available search interfaces subsequently returned results for a known-site
control; no general search outage was established. A separately declared
one-query/four-title feasibility screen identified an accessible primary source.
The [tungsten review](tungsten-task-review.md) freezes its own applicability
questions before full-text inspection, records abstract-level outcome exposure,
and does not replace this closed, incomplete two-paper selection trial.
