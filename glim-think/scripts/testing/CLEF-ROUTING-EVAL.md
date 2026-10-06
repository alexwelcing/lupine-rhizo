# Bounded Clef routing evaluation

Run from `glim-think`. This is a manual evaluation of **classification**, using
the application's exported `buildClefRequest` as the shared request definition.
Each case sends one state with three choice questions: route, evidence, workflow.
It never calls a generation model, changes routing configuration, executes a
classified request, or publishes results.

## Call-free preparation

```sh
node scripts/testing/clef-routing-eval.mjs
node scripts/testing/clef-routing-eval.mjs --dataset evals/__datasets__/clef-planning.json
node --test scripts/testing/clef-routing-eval.test.mjs
```

The default dataset is the original 12 handwritten routing cases. The separate
planning dataset adds five synthetic cases covering saved reviews, comparing a PI
decision with measured results, literature, an unclear follow-up, and quoted
routing instructions. Neither dataset claims those research records exist.
The original cases retain their provisional task labels; their additional axes
are observed but unscored. Planning cases label all three axes independently.

Without `--live`, the command only builds/imports local router code and prints a
bounded plan with case IDs and hashes. It makes no CLI or network calls. The
prompts must be nonempty and at most 2,000 characters; the maximum is 24 cases.
This runner does not inject conversation history into a context-free follow-up.

## Explicit live evaluation

The operator must already be signed in through the official `cf auth login`
flow. The runner does not sign in, inspect credential files, copy tokens, or print
authentication details. The account ID is required so the CLI does not need to
discover or select an account interactively.

Start with one case in a **new private directory whose parent already exists**:

```sh
node scripts/testing/clef-routing-eval.mjs \
  --live --case fast-greeting \
  --account-id ACCOUNT_ID \
  --run-dir /absolute/private-output/new-clef-smoke
```

To evaluate all 12 original cases, omit `--case`. To run the five planning cases,
pass `--dataset evals/__datasets__/clef-planning.json`. Repeated `--case ID`
options select cases in dataset order; duplicates and unknown IDs are rejected.
Each live invocation requires a fresh run directory. Do not replay an uncertain
or timed-out case automatically under a different name.

Optional limits: `--timeout-ms 20000`, `--total-ms 300000`,
`--min-confidence 0.7`, `--min-margin 0.15`.
Per-case deadlines are at most 60 seconds; the whole batch is at most 10 minutes.
The default total bound is five minutes. The runner stops the batch on any CLI,
timeout, output-limit, or response-validation failure, leaving the rest unstarted.
The CLI process group is terminated on timeout; this cannot establish whether a
request already sent to Cloudflare completed there. Such outcomes remain unknown.

The default CLI is `hosted-preview/node_modules/cf/bin/cf`; `--cf` selects another
absolute CLI path and `--profile` selects an existing OAuth profile. The reviewed
version is `cf` **1.0.0-beta.12**. A different version is rejected until its body
and retry behavior is reviewed. The official invocation is:

```text
node <cf>/bin/cf ai run @cf/cloudflare/clef-flash --body @<private-temporary.json> --quiet
```

The direct `--body` path skips model-schema discovery. This installed version
constructs its API client with `maxRetries: 0`. Input exists in a private temporary
file only while needed; the directory is removed after the batch. Each CLI call
runs from that clean directory, preventing project `.env`/configuration loading.
The environment retains normal home/profile access, removes inherited API tokens,
API endpoint overrides and debug settings, and disables optional telemetry.

## Receipts and interpretation

The run directory is exclusive and private (0700; files 0600):

- `manifest.json`: run ID, dataset/router/request hashes, limits and case IDs.
- `<case>.intent.json`: durable intent before its one CLI invocation.
- `<case>.receipt.json`: choice, confidence, top-two probability margin, accepted
  versus fallback, expected label, timing, token usage, exit/error category,
  local request ID, and provider request ID when the response supplies one.
- `report.json`: individual receipts and per-axis accuracy, accepted accuracy,
  coverage, confusion counts, latency percentiles, and completed-response usage.

Raw prompts, responses, stderr, account IDs and credentials are not stored in
receipts. Prompt/request hashes enable comparison with the separately held input.
Provider request IDs are `null` if the CLI response has none; local UUIDs are not
presented as provider IDs. Output is bounded to 128 KiB per CLI invocation.

Confidence is read from Clef's own confidence field, independently of the choice
probability. Ties always fall back. Missing labels are unscored. Accepted accuracy
and coverage are both reported so abstention cannot inflate apparent reliability.
Latency includes CLI startup, OAuth handling and API transport, and does not
measure the application's Worker binding latency. Usage totals cover successful,
validated responses only; a failed request may still have consumed provider work.
This small synthetic set is a development diagnostic, not proof of general model
quality, safe autonomous execution, or scientific discovery.

## Official references

- [Cloudflare CLI authentication and credential order](https://developers.cloudflare.com/cf/get-started/)
- [Cloudflare CLI environment controls](https://developers.cloudflare.com/cf/environment-variables/)
- [Clef Flash and Workers AI requests](https://developers.cloudflare.com/workers-ai/models/clef-flash/)
- [Clef input schema](https://developers.cloudflare.com/workers-ai/models/clef-flash/schema-input.json)
- [Clef output schema](https://developers.cloudflare.com/workers-ai/models/clef-flash/schema-output.json)

CLI details were checked against the installed beta.12 `ai run` command and its
API-client implementation. The live response still must pass the documented
choice/distribution/usage validation before a case is reported as completed.
