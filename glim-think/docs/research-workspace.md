# Research workspace and model routing

The private `/workspace` surface adds persistent, named research conversations.
Open the same conversation link on the Mac or Linux laptop to continue its
history. The conversation directory is shared by the configured operators;
this is not a multi-tenant workspace with per-user isolation.

## What the operator can do

- Choose a configured model and see the actual model used for the turn.
- Resume a saved conversation, rename it, and cancel a streamed response.
- Ask for saved hypotheses, literature, and lab activity. The evidence tool
  runs bounded, fixed read queries and returns record IDs.
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

## Clef as a model router

Clef scores a fixed set of choices from supplied context. It can classify a
request as quick assistance, deep reasoning, coding, or research. Application
policy then maps the decision to an eligible model profile. It is compatible
with the Jev/System One typed-question approach and has open weights.
See [Cloudflare's announcement](https://blog.cloudflare.com/clef-decision-models/)
and [Clef Flash API](https://developers.cloudflare.com/workers-ai/models/clef-flash/).

The router is disabled by default. Explicit model selection wins. Only
allowlisted configured chat profiles are eligible; low confidence, ambiguity,
invalid output, or a timeout returns the ordinary fallback. A routing decision
does not grant permission to execute tools or launch jobs. Evaluate representative
requests in shadow mode before enabling routing, checking answer quality,
misrouting, total latency, and total model cost against the current baseline.

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
