# How we use AI agents and handle data

**Status: Published** · 2026-11-11 · not peer-reviewed; corrections are dated in
the body.

Lupine Science is founder-led (Alex Welcing, founder). We do the work with AI
coding and research agents, under rules that live in code and CI rather than on
this page. This page names each mechanism that exists, says how far it reaches,
and links the file where you can check it. Where a mechanism covers less than
its name suggests, we say so.

## Who is responsible

- AI assistance is disclosed. A human author is responsible for every public
  claim.
- The operator (the founder) reviews every public research-activity summary
  before it is imported ([public research activity](public-research-activity.md)).
- Key-person risk is real. We reduce it by publishing the data, the code and the
  failure ledger ([conjecture ledger](conjectures/ledger.md)), so the record can
  be checked without us.

## The mechanisms and what they cover

**(a) Status changes in the machine registry need new evidence.**
[`anti-laundering.yml`](../.github/workflows/anti-laundering.yml) runs
[`tools/check_status_evidence.py`](../tools/check_status_evidence.py) on pull
requests that touch `registry/`, `snapshots/` or `evidence/`. It rejects a status
change in the assumption registry (`registry/assumptions.v1.json`), the
status-event snapshot (`snapshots/status-events.v1.json`) or the locked ontology
unless the change carries an evidence-bundle hash that did not exist before.
Coverage limits: it runs on pull requests only; it does not read the claim
files under `registry/claims/`, the Markdown ledgers
([conjecture ledger](conjectures/ledger.md),
[formal proof ledger](formal-proof-ledger.md)) or the status lines of articles
on lupine.science. Those are edited by hand and reviewed like any other change.

**(b) Public research-activity records pass a reviewed import.**
The contract in [public-research-activity.md](public-research-activity.md) and
the validator in `glim-think/src/workspace/researchActivityContracts.ts` reject
unknown fields, local paths, email and device identifiers, private, IP and
tailnet URLs, credential query parameters and credential-shaped strings.
Records are immutable. A correction must keep the same terminal state, so failed
or stopped work cannot be relabelled completed. There is no automatic
ingestion. The validator catches common accidental disclosure; it does not show
that prose is true, which is why the operator reviews each record first.

**(c) The model review stage is bounded.**
[`tools/scientific-pi/`](../tools/scientific-pi/README.md) runs a three-step
cycle (proposal, critique, adjudication) through the providers' official
command-line tools. It never starts an experiment, sends a message, publishes a
page or schedules another run. Each call gets an explicit tool list. The cycle
controller ([`tools/pi-cycle.py`](../tools/pi-cycle.py)) runs packet critiques and
adjudications with no tools; the runner itself also accepts a critic job with web
retrieval when one is submitted directly. **Literature jobs can search the web
and fetch web pages.** Codex runs in a read-only sandbox in a fresh
temporary directory, with shell, editing, plugins and delegation disabled. Any
forbidden or unrecognised action stops the job, and a stopped job is never
retried under the same identity. A completed review is a recorded discussion:
the experiment it proposes stays "not started" and its novelty "unverified".
These calls use the providers' signed-in command-line tools, not API keys; API
key overrides are removed from the child process.

**(d) A model score is a recommendation, not evidence.**
[AGENTS.md](../AGENTS.md) (Clef decision use): a model score is not scientific
evidence, novelty validation, experiment authorization or publication approval.
A successful model call is not a successful experiment.

**(e) Lean must build with no `sorry`; counts are generated.**
[`lean-spec.yml`](../.github/workflows/lean-spec.yml) runs `lake build` and
[`lean-spec/scripts/check_no_sorry.sh`](../lean-spec/scripts/check_no_sorry.sh) on
changes under `lean-spec/`. The theorem inventory
in [`lean-spec/theorem-count.json`](../lean-spec/theorem-count.json) is written
by `lean-spec/scripts/generate-lean-count.mjs`, never typed by hand, and
`scripts/check-stale-lean-counts.mjs` flags known stale hand-typed totals.
Lean 4 checks the arithmetic and stated inequalities behind published numbers;
it does not check the physics, the reference data or the pipeline.

**(f) The HPC lane is designed to run offline, on a facility's own hardware.**
[hpc/ADMIN_REVIEW.md](../hpc/ADMIN_REVIEW.md): local manifests go in and local
JSON comes out. With no beat URL and a pre-fetched model cache, the runner makes
no outbound connections; the offline test
(`gcp/mlip-cell-runner/test_runner_offline.py`) runs a mock calculator and makes
the runner's HTTP calls fail. MLIP backends download checkpoints on first use,
so an air-gapped cluster needs a one-time connected pre-fetch
([hpc/slurm/README.md](../hpc/slurm/README.md)). Telemetry is off unless
`LUPINE_OTEL_ENABLED` is set. The Apptainer container has not yet been built on
a facility cluster.

## Where data goes

- **Agent model calls** go to commercial model providers. The glim-think Worker
  calls provider APIs with keys held as Cloudflare Worker secrets (the providers
  are listed in `glim-think/docs/secrets.md`). The model review stage uses the
  providers' own signed-in command-line tools (Codex and Claude Code).
- **Kimi.** Background literature surveys (labelled AI-drafted) and one internal
  review were produced with Kimi (Moonshot AI) tools. glim-think's `workers-deep`
  profile runs a Kimi model hosted on Cloudflare Workers AI
  (`glim-think/src/agents/modelProfiles.ts`).
- **Traces.** When its Phoenix secrets are set, glim-think exports
  OpenTelemetry traces of agent model calls to Phoenix Cloud (Arize); the spans
  carry clipped prompt and reply text (`glim-think/PHOENIX.md`,
  `glim-think/src/telemetry/rpc.ts`). With the secrets unset, traces go to a
  no-op endpoint. The Distill flywheel tools send metrics-only traces through
  the same relay, opt-in. The model-review child processes run with OpenTelemetry
  settings removed.
- **Benchmark runs** use Lupine's Google Cloud project (Cloud Run jobs) or a
  local workstation. A run at a research facility would stay on that facility's
  machines; none has run yet.
- **Public outputs.** Everything committed to this repository is public. The
  Library reads only `exports/library-content/latest/`, which is regenerated by
  script and checked for schema, hashes and local paths; the public
  research-activity feed reads only the reviewed import above.
- Recorded run artifacts keep cloud project ids and bucket names as provenance.
  They are not credentials. Keys and tokens are never committed.

## Amendments

Our rule: an amendment written after any outcome has been seen is labelled
outcome-dependent, and the original gate's verdict is reported next to the
amended one. Example: amendment 01 to the Z1 sparse-DFT pilot
([amendment](plans/2026-07-21-sparse-dft-pilot-amendment-01.md)) moved the
primary gate to a same-engine comparison after path 7 had failed the original
40 meV gate (118.8 meV). The result is reported as a same-engine
self-consistency check, with the VASP-referenced error (693.0–705.7 meV MAE)
shown beside it ([verdict](analysis/z1-union-campaign-verdict.md);
[ledger](conjectures/ledger.md)).

Human sign-off (rule from 2026-11-12): an amendment counts as approved only
when the approval is in the repository's own record, either as a commit that
carries the owner's `Signed-off-by:` line or as an approving review on the
pull request that adds the amendment. A quoted conversation is not a sign-off.
Sign-off does not replace the outcome-dependent label: an amendment written
after an outcome keeps that label however it was approved. Amendment 01
predates this rule; its approval is recorded only as a quoted conversation.
This is a written rule, not a CI check.

## Automation that can change this repository

[`glim-think-evolver.yml`](../.github/workflows/glim-think-evolver.yml) is a
prompt A/B workflow that runs weekly and on demand. By default it is disarmed and
runs plan-only: it writes, commits and opens nothing. When a repository
variable arms it, it can commit a prompt change under `glim-think/src/registry/`
on a new branch and open a pull request. It never merges: a human reviews and
merges each Evolver pull request (the auto-merge step was removed on
2026-11-12; `glim-think/evals/evolver.ts`). Its writes are limited to that
prompt-registry path, and deploying the Worker is a separate, manually
triggered workflow. Whether `main` itself requires a pull request review is a
repository setting, not something this file can show.

Retired 2026-11-12: an autonomous Kimi CLI loop (`kimi --yolo`, every tool call
auto-approved) that ran under a `lupine-ops` supervisor binary, with no human
review step. We no longer run it, and the supervisor binary and its runbooks
were removed from this repository (they remain in git history).

## What we do not publish

Personal host names, tailnet URLs, machine names, personal email addresses,
cloud project numbers, IAM roles tied to a person, credential paths, private
chat URLs, signed URLs and agent persona rosters. One workstation name still
appears in glim-think code identifiers and test fixtures (a bridge role id and a
database constraint) until a planned migration renames them, and git history
keeps earlier versions of every file. If you find anything else in a tracked
file, tell us: alex@lupinesci.com.
