# Discovery tooling evaluation: fastbrowse and Prove2Me

Date: 2026-09-21
Status: evaluation complete, experiments proposed, nothing public yet
Owner decision needed: sections 6 and 7
Companion artifacts: `schemas/web-evidence-receipt.v1.schema.json`,
`tools/web_evidence_receipt.py`, ADR 0007

## 0. The question and the answer

The question was whether two external tools, fastbrowse (a browser agent that
cites verbatim page quotes) and Prove2Me (a crowdsourced Lean 4 formalization
platform), can help Lupine research faster, advance discovery, and share what
it finds.

The short answer: they slot into two different ends of the loop this repo
already runs, and both fit unusually well because they share our house rule
that a claim is only as good as its receipt.

| Loop stage | Tool | What it adds | Ready today? |
| --- | --- | --- | --- |
| Gather evidence from the web | fastbrowse | Every answer carries verbatim quotes with URL and page-capture hash. Cheap enough to run hundreds of lookups. | Yes for public pages. Needs two API keys. Pre-alpha software. |
| Prove and stress-test claims | Prove2Me | External provers and disprovers attack our Lean statements; blind read-back audits check faithfulness; permanent attribution. | Yes for a private mission. Public release needs a license and Lean-version decision. |
| Share discoveries | Prove2Me Formalpedia + Ledger | Theorem pages that others can import, plus our Library record. | Ledger unchanged; Formalpedia after public release. |

Everything below was verified on 2026-09-21 against the live sites, the
published paper, the installed package, and this repository.

## 1. fastbrowse: what it is

Source: https://www.fastbrowse.ai/, https://github.com/agent-labs-dev/fastbrowse,
PyPI `fastbrowse` 0.4.2 (released 2026-09-20). MIT license. Python 3.13+.
The README says "highly experimental and not recommended for production use yet."

**Architecture.** A choice model called Jev indexes the interactive controls
that are actually on the page and picks one. A separate LLM (routed through
OpenRouter) plans and reads. The product claim: "every claim in the final
answer is backed by a verbatim quote from the page." Runs end in one of nine
statuses: `complete`, `unverified`, `needs_confirmation`, `needs_login`,
`blocked`, `needs_input`, `stuck`, `budget_exceeded`, `error`. Only `complete`
means every claim was backed.

**Safety model.** Irreversible actions (submit, pay, delete, send) stop the run
unless `--authorize` is passed. Secrets are injected at typing time from
environment variables or Bitwarden; the model sees only the secret's name.

**Evidence record.** Verified from the installed package: each evidence item
carries `source_id`, `url`, `frame_id`, `captured_at`, `capture_sha256`,
`start`, `end`, and `quote`. The run result also carries `status`, `answer`,
`data` (schema-validated structured output), `steps`, `cost.lines`, and
`final_url`. This is exactly the shape a provenance receipt needs.

**Cost and reliability, from the project's own evals (2026-09-20 uncapped run).**

| Metric | fastbrowse | Hosted Browser Use |
| --- | --- | --- |
| Pass rate | 41/42 | 42/42 |
| Median cost per task | $0.0057 | $0.4070 |
| Median time per task | 21.0 s | 24.8 s |

Serial repeats of the same 42 tasks scored 38/42, so single-pass numbers carry
a few points of noise. Default models are `google/gemini-3.8-flash` for reading
and `google/gemini-3.5-flash-lite` for planning, overridable per purpose.

**Interfaces.** CLI `uvx fastbrowse "<task>" --start URL --json`. Python SDK
`run_task(task, start=, output_schema=PydanticModel, limits=Limits(max_dollars=))`.
MCP server `fastbrowse-mcp` with per-call ceilings (`--max-dollars`,
`--max-seconds`, `--max-steps`) and `--allow-authorize` off by default.

**Requirements.** `AI_GATEWAY_API_KEY` or `TYPESAFE_API_KEY` for Jev,
`OPENROUTER_API_KEY` for the LLM, Chrome locally or `BROWSER_USE_API_KEY` for
`--cloud`.

**What was verified here.** The CLI installs under `uvx --python 3.13` and both
`fastbrowse --help` and `fastbrowse-mcp --help` match the documented flags. No
task was executed because this environment has no API keys.

## 2. Prove2Me: what it is

Source: https://prove2.me/, paper arXiv:2608.28433 (Chen, Marwaha, Lu, Yuen,
Peng, submitted 2026-08-28), workspace
https://github.com/prove2me/prove2me_workspace. Grew out of a Spring 2026
Columbia course on machine-assisted mathematics.

**Model.** A mission turns one paper, textbook, or open problem into small Lean
4 statements. A captain assembles the core statements and milestones and audits
them for faithfulness. Agents (Claude Code, Codex, Cursor, and others) prove
them; the Lean kernel checks every submission server-side. Proved statements
join Formalpedia, a public library where "the contributor who proved the
theorem receives permanent attribution." Disproofs are first-class: submit a
verified proof of the negation.

**API.** Base `https://prove2.me/api/v1`, version 0.10.7 (health endpoint
checked live). Every listing endpoint returns 401 without a bearer token, so
there is no anonymous browsing through the API. Auth is an API key exchanged
for a one-hour token at `POST /agent/refresh`. The skill doc's rule: "NEVER
send your API key or access token to any domain other than the base URL."

**Environments.** Three pinned Lean/Mathlib environments:

| Lean | Mathlib commit prefix | Default |
| --- | --- | --- |
| v4.33.1 | `0df444a360` | yes |
| v4.30.0 | `c5ea00351c` | no |
| v4.29.0-rc3 | `777aaa61dc` | no |

**Submission rules.** The proof is a top-level theorem named `solution` whose
type matches the target's `formal_statement` exactly. No importing your own
target. No `sorry` in your code (imported open lemmas may carry it). Verdicts:
`ACCEPTED`, `SKETCH_ACCEPTED` (imports open lemmas, becomes a reduction), `CE`,
`WA`, `SORRY`, `FAILED`, `ERROR`. Reductions decompose a theorem into child
lemmas; the parent auto-resolves when all children are proved.

**Contribution.** `POST /submit-problem` takes `theorem_name`,
`theorem_title`, `formal_statement` (ending `:= by sorry`),
`natural_language_statement`, optional `preamble`, `source`, `tags`, `env`,
`private`. `POST /submit-definition` publishes sorry-free reusable
definitions. Both are asynchronous publish jobs. Theorems are immutable once
published; the fix path is deprecate and resubmit. Limit of 100 pending jobs
per account.

**Roles.** Solver (prove open statements), captain (draft a proposal with
milestones, hand to a human for audit, then curate), auditor (write blind
read-backs: a sub-agent sees only the Lean and testifies what it literally
asserts, never the source). Mission types: OpenProblem, Textbook,
ResearchPaper. Private missions run the full workflow without moderator
review; "Make public" is permanent.

**Licensing.** All public theorems, definitions, and proofs are Apache 2.0.

**Live campaigns today.** Two: odd numbers as sums of primes (number theory)
and the matrix multiplication exponent (complexity). Nothing yet in
statistics, analysis, or physics, so a materials-science mission would be the
first of its kind there.

**Uploading an existing project.** The `upload_full_project.md` playbook
converts a built Lean project into platform nodes by mechanical extraction.
Two constraints matter for us: the source project's Mathlib pin must be
matched to a platform environment, and target axioms must stay within
`propext`, `Classical.choice`, `Quot.sound`.

## 3. Where this repo already is

Lupine's loop is gather → hypothesize → measure → prove → publish, with
receipts at every step. Relevant existing machinery:

- **Citation audits are manual.** `lit-review/citation-verification-2026-07-21.md`
  checked 163 identifiers against arXiv and Crossref and found three bad
  citations. That is the job fastbrowse-style cited lookups are built for.
- **Literature enters through a schema.** `schemas/literature-hypothesis.v1.schema.json`
  and `tools/lit_to_manifest.py` turn a literature hypothesis into a frozen
  campaign manifest. A web receipt is the layer below that: the raw quoted
  source a hypothesis cites.
- **The theorem commons is our stated amplifier.** The Research Command
  Center names "the theorem commons (shared gates + shared anchors)" as the
  multiplier on the Z1 pilot. Prove2Me is a working theorem commons with an
  API, an audit protocol, and attribution, and we do not have to build it.
- **Our Lean layer is Mathlib-light where it matters.** `lean-spec/` pins Lean
  v4.29.0 and Mathlib `8a178386` (ATLAS's pin). `LupineEvidence/Shapes/Certificates.lean`
  is dependency-free core Lean. `Materials/Theory/SharpLicense.lean` is integer
  arithmetic over `Mathlib.Tactic`. `Materials/Theory/UniversalCorrection/Anchor.lean`
  uses `Mathlib.Data.Real.Basic` and `linarith`. These port to a v4.33.1
  environment with low risk.
- **Twenty modules use `native_decide`.** `ErrorLandscape/Emblems.lean`,
  `ErrorLandscape/MasterMatrix.lean`, and most `DiscoveryChains/Chain*.lean`
  rely on it. `native_decide` adds the `Lean.ofReduceBool` axiom, which the
  Prove2Me upload playbook excludes. Those modules are not upload candidates
  as written.

## 4. How fastbrowse fits: cited web evidence intake

**Principle.** A browser agent's answer never enters the ledger. Its quotes
do, as a receipt, and the receipt says whether the run was fully cited.

**What now exists.** `schemas/web-evidence-receipt.v1.schema.json` defines the
receipt: tool and version, task text, run status, `citable` flag, the quotes
with URL, capture time, capture hash, span, and a SHA-256 of each quote, the
known dollar cost, and a hash of the raw run file. `tools/web_evidence_receipt.py`
builds a receipt from `fastbrowse --json` output and re-checks one. It marks a
receipt `citable` only when the run status is `complete` and at least one
quote exists. Editing a quote by hand breaks two hashes and fails `check`. Ten
unit tests cover this; no network or API key is needed.

**Intended flow.**

```text
fastbrowse --json  →  data/web_evidence/raw/<run>.json
                   →  tools/web_evidence_receipt.py build  →  data/web_evidence/receipts/<id>.json
                   →  cited rows in lit-review digests / literature-hypothesis sources
                   →  tools/web_evidence_receipt.py check in CI
```

**Good first tasks.** Lookups against public reference pages where we already
know the answer and where getting it wrong has cost us before:

1. arXiv and Crossref title lookups for the 163 identifiers in the 2026-07-21
   citation audit. Ground truth is checked in.
2. Rows of `docs/research/matbench-leaderboard-2026-09-09.csv` re-derived from
   the live leaderboard.
3. NIST IPR and OpenKIM potential metadata (DOI, pair style, publication) for
   the Ni potentials in `data/mlip_benchmarks/manifest_sources.json`.
4. Materials Project structure metadata for the Z1 barrier panel's `mp-` ids.

**Operating rules for v0.**

- Public pages only. No `--authorize`, no `--secret`, no Lupine credentials.
- Cap every run: `--max-dollars 0.05` for lookups, `--max-steps 30`.
- Commit the raw `--json` file alongside the receipt so the hash chain is
  checkable.
- Third-party routing: page text and task prompts go to OpenRouter and the Jev
  gateway. Fine for public reference pages; do not point it at unpublished
  Lupine material.
- The `answer` field is for humans. Digests cite `quotes[]`.

## 5. How Prove2Me fits: the theorem commons, rented

**Three things it gives us that a GitHub repo does not.**

1. **Adversarial checking of our statements.** Anyone's agent can submit a
   disproof. Our Lean gate proves what we assert; it cannot tell us that we
   asserted the wrong thing. A public disproof would.
2. **Blind faithfulness audits.** The read-back protocol has an independent
   agent translate our Lean back to prose without seeing the source. That
   is the check our `docs/formal-proof-ledger.md` does by hand.
3. **Attribution and reuse.** Formalpedia pages are permanent, credited, and
   importable by other missions. That is the "every team that joins makes
   every other team faster" mechanism from the Command Center, with
   citation tracking built in.

**Candidate first mission: "Calibration-only correction licenses for in-hull
MLIP correction."** Mission type ResearchPaper, source
`paper/gates-licenses-paper/` and `Materials/Theory/SharpLicense.lean`.

| Item | Kind | Why it is a good first node |
| --- | --- | --- |
| `CubicElastic`, `bornStable`, `ConcordanceWindow` from `Shapes/Certificates.lean` | definitions | core Lean, no Mathlib, decidable |
| `sharp_inhull_correction_helps_inflation` | theorem | integer arithmetic, self-contained hypotheses |
| `sharp_inhull_correction_helps_deflation` | theorem | same |
| `sharp_inflation_necessary` | theorem | a necessity result; a natural disproof target if we are wrong |
| `old_inflation_cap_implies_sharp` | theorem | shows the frozen caps are a special case; a good milestone |

Rounding-robust variants and the `Anchor` interval theorems are the second
wave. `native_decide`-dependent receipt modules stay home.

**Why start private.** A private mission exercises registration, definition
upload, problem upload, and `solution` verification end to end with no
moderator step and no irreversible release. It also lets us measure the real
cost of re-elaborating against Lean v4.33.1 and a different Mathlib.

## 6. Risks and blockers

| Risk | Severity | Mitigation |
| --- | --- | --- |
| fastbrowse is pre-alpha; output shapes may change | medium | receipt tool validates field-by-field and fails closed; pin the version in receipts |
| A `complete` run can still quote a wrong page | medium | receipts are `observed` evidence, never a claim status; digests still cite the primary source |
| Page text sent to third-party model providers | low for public pages | public reference pages only in v0 |
| Lean toolchain mismatch (ours v4.29.0 / Mathlib `8a178386`; theirs v4.33.1 or v4.29.0-rc3 with different Mathlib) | medium | port the Mathlib-light modules first; measure elaboration diffs in the private mission |
| `native_decide` axiom excluded | known | excludes 20 modules; not the candidates above |
| Public theorems are Apache 2.0; this repo's code is AGPL-3.0 and prose CC-BY-SA-4.0 | owner decision | publishing a theorem publicly relicenses that statement and proof; decide per mission before "Make public" |
| Public release is permanent; theorems are immutable | high if wrong | private first; captain audit plus read-backs before release |
| Credentials | low | API key lives in `credentials.json` outside the repo; never sent elsewhere |
| Registration needs a human to relay a 6-digit code | trivial | one-time |

## 7. Proposed experiments and gates

**E1: cited lookups against known truth.** Budget under $1. Ten lookup tasks
from section 4, each `--max-dollars 0.05`. Pass if at least 9 of 10 finish
`complete` and every quote agrees with the checked-in ground truth. Record
cost, wall time, and the status histogram in a receipt set under
`data/web_evidence/`. Kill condition: fewer than 7 of 10 `complete`, or any
`complete` receipt whose quote contradicts ground truth.

**E2: agent-loop integration.** Run `fastbrowse-mcp --max-dollars 0.25` as an
MCP tool for one new lit-review digest. Compare the receipt set against a
hand-built digest on the same topic for coverage and time. Pass if the cited
digest is produced in under half the analyst time with no uncited claims.

**E3: private Prove2Me round-trip.** Register, mint an API key, port the
section 5 definitions and the two sharp theorems to the v4.33.1 environment,
upload privately, submit `solution` proofs, receive `ACCEPTED`. Record every
elaboration difference between our pin and theirs. Pass if at least one
theorem round-trips. Kill condition: the port needs a `sorry` or a new axiom.

**E4: captain proposal with read-backs.** Draft the ResearchPaper mission,
attach independent read-backs to every item, and hand the review to the owner.
Public release is an explicit owner decision covering the license change and
the permanence.

Order: E1 and E3 can run in parallel and are independent. E2 follows E1. E4
follows E3 and stops at the owner's desk.

## 8. What sharing looks like if this works

A Lupine claim would carry three receipts instead of one: the LAMMPS or DFT
trace it rests on, the Lean theorem in `lean-spec/` that gates it, and a
Formalpedia page where an outside prover either confirmed it or failed to
disprove it. The Ledger article links all three. No content contract change is
needed for that link today; the manifest already carries a `proven` status and
free-form article markdown. If Formalpedia links become routine, an optional
`external_verification` entry field in `library-content.v1` is the natural
follow-up, and it belongs in Rhizo's exporter first.

## Sources

- https://www.fastbrowse.ai/
- https://github.com/agent-labs-dev/fastbrowse and `docs/evals.md` there
- https://pypi.org/project/fastbrowse/ (0.4.2, 2026-09-20)
- https://prove2.me/, `/about`, `/faq`, `/start.md`, `/skill.md`,
  `/references/{mission_solver,mission_captain,prove,contribute,upload_full_project}.md`
- https://prove2.me/api/v1/health (version 0.10.7, checked 2026-09-21)
- https://arxiv.org/abs/2608.28433
- https://github.com/prove2me/prove2me_workspace
