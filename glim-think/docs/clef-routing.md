# Clef request planning

The workspace's **Auto · Clef planning** option asks Clef Flash three fixed-choice
questions in one batched call. Application policy checks each answer before use.

| Question | Choices | Effect of an accepted answer |
| --- | --- | --- |
| Model route | `fast`, `deep`, `code`, `research` | Recommend an explicitly mapped, configured generation profile. |
| Saved evidence | `none`, `research_runs`, `ledger`, `both` | Suggest which existing read tools would help answer the request. |
| Research task | `answer`, `literature`, `hypothesis`, `critique`, `analysis` | Suggest how to organize the response. |

`research_runs` refers to imported PI proposals, critiques, decisions and stage
receipts. `ledger` refers to bounded saved papers, hypotheses and reported lab
activity, without direct access to underlying experiment artifacts. `both`
suggests comparing those sources. A choice does not establish that a record exists.

Clef does not generate the chat response, establish scientific certainty, or
authorize tools, jobs, experiments, deployment, spending or publication. Model
selection still passes through `selectModelProfile` and its provider/budget checks.
The workspace's tools remain `read_evidence` and `read_research_runs`.

## Defaults and private preview

The reusable router is **disabled by default**. The isolated private preview
explicitly enables `auto` with the fixed policy below; other deployments are
unchanged. A manual model choice bypasses Clef and its planning hints.

| Variable | Generic default | Private preview |
| --- | --- | --- |
| `CLEF_ROUTER_MODE` | `disabled` | `auto` |
| `CLEF_ROUTER_TASK_PROFILES` | unset | `fast` → `workers-flash`; `deep`, `code`, `research` → `workers-deep` |
| `CLEF_ROUTER_MIN_CONFIDENCE` | `0.7` | `0.7` |
| `CLEF_ROUTER_MIN_MARGIN` | `0.15` | `0.15` |
| `CLEF_ROUTER_TIMEOUT_MS` | `1200` | `1500` |

The preview policy is fixed inside its environment adapter, rather than accepted
from arbitrary extra bindings. Access still protects all workspace requests.
See the [preview guide](../hosted-preview/README.md).

`shadow` classifies but keeps the default model and does not apply evidence/task
hints. Task mappings express operator preference, not a measured ranking of
models. `fast` must map to an eligible fast profile; the other tasks to eligible
deep profiles. Unknown profiles, decision models and invalid mappings are
rejected. An unmapped route keeps the default.

## Independent gates and fallback

Each answer must match the expected model and choice schema, contain exactly its
allowed finite probabilities in `[0,1]`, sum to one within `0.001`, and select a
highest-probability choice. Clef's confidence is a separate API field, not the
selected choice's probability.

Each axis is accepted independently at confidence **≥ 0.7** and top-two probability
margin **≥ 0.15**. Ties always fall back. A rejected route keeps the default model
while an independently accepted planning hint can still help the response in
`auto` mode. Rejected hints are omitted.

Malformed output, low confidence, ambiguity, missing mappings, provider failure
or timeout preserve the ordinary fallback. The workspace defaults to
`workers-flash`; the standalone router defaults to `fast` unless supplied another
configured default. Invalid manual selections fail visibly. Catalog eligibility
does not prove live availability, response quality, tool support or affordability.

## Context and conversation recovery

- Only the latest supplied user text goes to Clef, capped at 2,000 characters.
  Long text retains its beginning and end with a marked omission in the middle.
  Conversation history, tool payloads and environment credentials are not added.
- One Workers AI call carries all three questions, without retry. The deadline
  aborts and bounds the local wait even if cancellation is ignored; it cannot
  prove that already-started remote work stopped.
- Matching tool continuations reuse a validated decision only when the latest
  text, selected profile, routing policy and configured model catalog still match.
  Fresh user turns classify again. A changed provider/model invalidates reuse.
- The private conversation keeps at most **20** decision metadata entries and a
  validated continuation cache. Metadata contains choices, scores, reasons,
  timing and provider/model identity, not raw prompts or classifier responses.
  Ordinary chat history is stored separately.
- The interface shows the latest decision, fallback/manual state, truncation
  notice and recent decisions. Classifier confidence is not scientific certainty.

## Recorded evaluation

The 2026-10-06 evaluation made **17 classifier calls and zero generation calls**
on public synthetic fixtures. All 17 route choices matched provisional labels;
9 passed the unchanged confidence/margin gates. The five labeled planning cases
matched both additional axes, with accepted coverage of 1/5 for evidence and 3/5
for research task. These measure label agreement and abstention on a small set,
not general quality or scientific truth.

See the [sanitized evaluation summary](clef-evaluation-2026-10-06.md) for latency,
usage and limits, and the [private evaluation runner guide](../scripts/testing/CLEF-ROUTING-EVAL.md)
for reproduction. The runner imports the shared request builder, records its
hash, and stores bounded receipts privately without raw prompts or credentials.
Later prompt/policy edits require their own evaluation; recorded metrics do not
establish that every subsequent version behaves identically.

Call-free checks from `glim-think`:

```sh
node scripts/testing/clef-routing-eval.mjs
node scripts/testing/clef-routing-eval.mjs --dataset evals/__datasets__/clef-planning.json
node --test scripts/testing/clef-routing-eval.test.mjs
npx vitest run src/agents/__tests__/clefRouter.test.ts
```

Measure downstream usefulness and response quality alongside agreement, coverage,
latency and cost. The observed fallbacks are not a reason to lower thresholds.

## API provenance

The input follows Cloudflare's [Clef Flash API](https://developers.cloudflare.com/workers-ai/models/clef-flash/):
`AI.run("@cf/cloudflare/clef-flash", {model:"clef-flash", state, questions})`.
The [choice response schema](https://developers.cloudflare.com/workers-ai/models/clef-flash/schema-output.json)
provides choice, probabilities and confidence for each question. Schema validation
checks response structure, not the truth of a classification.
