# Research workspace and model routing

The private `/workspace` surface adds persistent, named research conversations.
Open the same conversation link on the Mac or Linux laptop to continue its
history. The conversation directory is shared by the configured operators;
this is not a multi-tenant workspace with per-user isolation.

## What the operator can do

- Use **Auto · Clef planning** in the private preview or choose a configured
  model directly, and see the actual model used for the turn. Inspect the latest
  routing decision and up to 20 recent decision metadata entries.
- Resume a saved conversation, rename it, and cancel a streamed response.
- Ask for saved hypotheses, literature, and lab activity. The evidence tool
  runs bounded, fixed read queries and returns record IDs.
- Open **Research runs** for imported local PI cycles: the original question,
  discovery, independent critique, decision, source links and execution receipts.
  Pending, stopped and completed discussions remain distinct. Chat can read the
  same saved runs through `read_research_runs`, one scientific packet at a time.
- Follow **See the research** to the public
  [Lupine Library Research Index](https://library.lupine.science/#/read/research-index).

The new workspace does not dispatch experiments, execute model-generated
commands, or publish chat output. Library publication uses the curated content
export described below. Existing research agents retain their own capabilities.

## Models

`GET /workspace/models` returns a credential-free catalog. `configured` means
that the binding or key exists; it does not verify entitlement or model health.
Failed provider calls must remain visible to the operator.

| Profile | Default model | Purpose |
| --- | --- | --- |
| `workers-flash` | `@cf/zai-org/glm-5.3-flash` | New interactive fast profile, low reasoning effort |
| `workers-deep` | `@cf/moonshotai/kimi-k2.6` | Cloudflare deep profile |
| `minimax` | `MiniMax-M3` | Existing MiniMax deep route and budget |
| `zai` | `glm-5.3` | Z.ai deep route |
| `openai` | `gpt-6.1-sol` | OpenAI Responses API |
| `anthropic` | `claude-sonnet-5-5` | Anthropic Messages API |
| `google` | `gemini-3.8-flash` | Native Gemini API, including AI Gateway |
| `fast` | configured Workers AI model, otherwise Llama 4 Scout | Existing background compatibility route |
| `clef` | `@cf/cloudflare/clef-flash` | Typed routing decisions, not a chat profile |

Provider model overrides remain supported: `WORKERS_AI_MODEL`,
`WORKERS_AI_DEEP_MODEL`, `MINIMAX_MODEL`, `ZAI_MODEL`, `OPENAI_MODEL`,
`ANTHROPIC_MODEL`, and `GOOGLE_MODEL`. `DEEP_PROVIDER` optionally selects a
configured provider. Without a preference, deep routing continues to consult
the model scorecard. The interactive deep-agent hook now uses that same
asynchronous selector as synthesis, including the MiniMax budget check.
An exhausted budget can cause a fallback for automatic deep-agent selection.
An explicit workspace choice fails visibly rather than silently changing models.

Model descriptions and current IDs were checked against the official
[Cloudflare catalog](https://developers.cloudflare.com/workers-ai/models/),
[OpenAI model guide](https://developers.openai.com/api/docs/guides/latest-model),
[Anthropic catalog](https://platform.claude.com/docs/en/models/overview),
[Google catalog](https://ai.google.dev/gemini-api/docs/models),
[Z.ai guide](https://docs.z.ai/guides/llm/glm-5.3), and
[MiniMax guide](https://platform.minimax.io/docs/guides/text-generation).
Account availability and performance on Lupine tasks still require validation.

## Clef as a request planner

Clef scores a fixed set of choices from supplied context. It can classify a
request as quick assistance, deep reasoning, coding, or research. One batched call
also asks which saved evidence would help (`none`, `research_runs`, `ledger`,
`both`) and the research task (`answer`, `literature`, `hypothesis`, `critique`,
`analysis`). Application policy maps an accepted route to an eligible model and
passes independently accepted evidence/task hints to the response. It is compatible
with the Jev/System One typed-question approach and has open weights.
See [Cloudflare's announcement](https://blog.cloudflare.com/clef-decision-models/)
and [Clef Flash API](https://developers.cloudflare.com/workers-ai/models/clef-flash/).

The reusable router remains disabled by default. The isolated private preview
enables Auto with `fast` → `workers-flash` and the other three route choices →
`workers-deep`. Manual model selection bypasses Clef. All three axes require
confidence at least `0.7` and probability margin at least `0.15`, with ties
rejected. A rejected route retains the ordinary default while independently
accepted evidence/task hints may still apply. The preview deadline is `1500` ms;
there is one classifier attempt and no retry.

Only the latest user text is sent, at most 2,000 characters with beginning and end
retained for longer requests. The classifier receives no conversation history or
tool results. Matching tool continuations reuse a validated decision; a fresh
user turn classifies again. The private conversation stores up to 20 bounded
decision metadata entries and a continuation cache, without raw classifier
output or prompt text in that metadata. Ordinary conversation history is separate.

Only configured chat profiles remain eligible. Evidence hints select among the
existing read tools; they cannot grant permissions, launch jobs or establish that
a requested record exists. The ledger provides bounded reports, not direct access
to underlying experiment artifacts. Classifier confidence is not scientific
certainty. See [Clef request planning](clef-routing.md) and the
[17-case synthetic evaluation](clef-evaluation-2026-10-06.md) for measured label
agreement, coverage, latency and limits. The
[private evaluation runner](../scripts/testing/CLEF-ROUTING-EVAL.md) makes
classification calls only; answer quality and hosted behavior need separate checks.

## Authentication and deployment

Cloudflare Access must cover `/workspace*` and
`/agents/research-workspace/*` on the worker's hostname. Configure
`CF_ACCESS_TEAM_DOMAIN`, `CF_ACCESS_AUD`, and the intended `ADMIN_EMAIL`.
The worker validates Access before serving the client, directory, history, or
WebSocket upgrade; missing configuration fails closed. Browser requests must
be same-origin. Existing trusted service-token access is retained.

Wrangler migration `v6` adds `ResearchWorkspace` SQLite Durable Objects. It
does not migrate or reset any existing agent's storage. The client is bundled
locally, with no runtime CDN dependency. The Wrangler build hook also runs for
the existing direct CI deployment command.

```sh
npm ci
npm run build:workspace
npm run lint
npm test
npx wrangler deploy --dry-run
```

Local previews may set `DEV_MODE=true` in an untracked `.dev.vars`; never set
it on a deployed worker. A successful bundle or mocked test is not proof of
live authentication, provider entitlement, streaming, or cross-device recovery.
Validate those on an authenticated staging deployment before production use.

## Private local research receipts

The existing local `tools/pi-cycle.py` ledger remains the authority for the
Mac discovery → aledev critique → Mac PI decision workflow. The workspace holds
a private, read-only projection in the same D1 `LEDGER`, using migration
`0020_workspace_research_runs.sql`. This is separate from the parked Progress
feed, which contains report analyses rather than execution receipts.

Several deliberately named cycles may reference the same completed discovery
job and packet. This means the original evidence was adopted, not that discovery
ran again. Critique and decision jobs keep their own identities, and failed or
stopped cycles remain visible. The CLI adapter now handles exact observed builtin
and empty-command metadata without granting tools, compresses the reviewed
handoff, and checks Homebase's command-size limit before transmission. See the
[scientific PI guide](../../tools/scientific-pi/README.md) for protocol validation,
transport bounds and the backward-compatible stage-ledger migration.

From the repository root, export one local cycle to a new private file:

```sh
python3 tools/pi-export.py --state-dir /path/to/private/pi-runs \
  --cycle-id the-cycle-id --output /path/to/private/research-snapshot.json
```

The exporter makes no network, model or device call. It reads SQLite in read-only
mode, validates job manifests, roles, receipts, packet hashes and exact prior-stage
links, and checks completed process exit status. A manifest without a receipt is
**pending**, not proof that the model ran. The refined scientific question in a
proposal is preserved separately from the original operator question.

Open `/workspace?view=research-runs`, expand the operator import control, choose
the exported JSON file or paste it, then preview the run and stage states before
explicitly selecting **Import snapshot**. Import uses
`POST /workspace/research-runs/import` with `Content-Type: application/json`.
It requires verified operator Access, independently of legacy service-token or
development bypasses, and rejects cross-origin browser requests. The response
acknowledges `{id,status,duplicate}`. No new machine secret or shared bearer is
created; unattended machine ingestion is not configured by this change.

`GET /workspace/research-runs` returns `{runs,truncated}` (newest 20); GET with a
run ID appended returns `{run}`. Missing storage or malformed saved records fail
visibly. Each import is limited to 192 KiB; each scientific packet to 48 KiB. Original
packet JSON bytes are fingerprinted before parsing so Python/JavaScript numeric
formatting cannot invalidate a legitimate packet. Updates use an atomic stored
fingerprint check. Older snapshots, changed started-job identities, terminal-stage
edits, and any stage change after a stopped/completed cycle are rejected. Reusing
an import never reruns work.

Snapshots exclude local CLI paths, raw provider/transport logs, credentials and
Homebase data. Receipt fields are allowlisted; stop messages are replaced with a
generic stage-status explanation. Private host paths found inside scientific
content cause export to fail rather than rewriting reviewed packet bytes.
An import is an operator-attested local record, not a provider-signed proof or
independent verification of its scientific claims. A completed discussion leaves
the proposed experiment **not started**, novelty **unverified**, and publication
**held**. The displayed capture time describes a snapshot; use Refresh after a
new import, rather than inferring live activity from an old pending record.

The `read_research_runs` tool lists bounded metadata or one selected stage packet,
with receipt attribution. Its text is evidence, never executable instructions.
It cannot launch, retry, cancel, modify or publish research. Access to actual
research runs does not grant the older synthetic evidence fixture scientific
validity in hosted preview.

### Verified live acceptance — 2026-10-06

Cycle `pi-20261006-risk-tradeoff-07` completed all three research stages with
zero process exit codes and validated exact job/result-hash links. It adopted
the earlier completed Codex discovery 01 on the Mac (04:14:53.095Z–04:15:49.108Z),
received critique 07 from `claude-opus-5-5` on aledev
(04:38:13.642Z–04:40:01.317Z), and completed Codex decision 07 on the Mac
(04:40:03.759Z–04:40:49.952Z). All times are UTC. Codex did not report an actual
model identifier; its recorded model remains `null`.

The complete snapshot was imported through the signed-in private UI at about
04:48 UTC. This was manual launch and operator import, not unattended dispatch.
Earlier failed receipts are preserved, discovery was shared without rerunning
it, and automatic retry remains off. Separate local CPU analysis findings do
not mean the PI's proposed experiment ran: it remains **not started**, novelty
is **unverified**, and public Library publication is **held**.

## Cloudflare's new CLI on the Mac

The separate `cf` CLI is in open beta. It supports account-wide API discovery
and structured output. This upgrade was prepared with `cf@1.0.0-beta.12` on
Node 22.22.3. Use a pinned local installation and `cf auth whoami` to verify
its own login; Wrangler credentials are separate.

```sh
npm install --save-exact cf@1.0.0-beta.12
npx cf auth login
npx cf auth whoami
npx cf cli search 'list Workers deployments'
```

Use Wrangler for this repository's deployment until a deliberate migration is
reviewed. Do not run `cf dev`, `cf build`, or `cf deploy` here as a substitute:
the beta can auto-configure a project. Account/resource commands also do not
inherit `wrangler.toml`'s account selection. See the official
[cf getting-started guide](https://developers.cloudflare.com/cf/get-started/)
and [Wrangler compatibility notes](https://developers.cloudflare.com/cf/wrangler/).

## Publication to Lupine Library

Release order is: validate the upgraded system privately, demonstrate useful
evidence-backed runs, then prepare a series of reviewable progress clips showing
the results and their limits. Obtain explicit user acceptance of the system and
clips before any new Library publication, including public Library previews.
Progress-clip creation is follow-up work; this upgrade does not implement or
generate clips. Keep publication manual and subject to that acceptance gate.

The Research Index and its **Show me the research** reading journey are in the
Rhizo curated export, with report dates, catalog statuses, corrections, proof
scope, and reproduction links preserved. After acceptance, publish by regenerating
`exports/library-content/latest`, syncing it into the Library reader's
`content/latest`, verifying hashes/provenance, then building and deploying the
reader. A local export is not yet a live page. Do not automatically publish
private conversations, internal agenda payloads, or unreviewed model output.
