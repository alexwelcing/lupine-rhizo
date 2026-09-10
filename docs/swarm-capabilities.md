# Swarm capabilities — model specialties and venue routing

Status: live configuration as of 2026-09-09. Companion demo evidence: `docs/swarm-demo/` (capability battery results) and campaign `swarm-capability-demo` in glim-ledger / CampaignConsole.

## Architecture layers

| Layer | What runs there | Strength it exploits |
|---|---|---|
| Cloud control plane | glim-think worker (Cloudflare: Durable Objects, D1, Queues, Vectorize, cron) | Durability, scheduling, provenance, public surfaces; scorecard-routed model calls; zero local dependency |
| Cloud burst compute | GCP Cloud Tasks → tasks-consumer → atlas-distill runners | Reproducible GPU cells, paid campaigns only |
| Local agent runtime | herdr 0.9.0 (pane/worktree management, agent state detection) on each machine | Many parallel agents on local GPUs/CPUs, survives disconnects |
| Cloud→local link | herdr-bridge daemon (systemd, one per machine) | Outbound-only: polls `/bridge/jobs`, drives herdr agents, posts beats back |
| Local agent harness | hermes (profiles, kanban, cron, skills) | Deep tool use, delegation, long-horizon work with the fallback chain |

## Model specialties (with evidence)

| Model | Provider | Specialty | Demonstrated by |
|---|---|---|---|
| GLM-5.3 | zai (API key) | Agentic coding, multi-file surgery, pipeline repair; default workhorse | evidence-nightly producer repair (multi-system: GCS+GH Actions+D1+DO SQL) |
| Claude Fable 5.1 | anthropic (OAuth, Max plan) | Architecture design, code review, long-form scientific writing | herdr-bridge design+build; TMS manuscript draft; glim-think diff review (SHIP verdict) |
| GPT-6 Astra | openai-codex (OAuth) | Long-horizon research, computer use, careful incremental repair | CampaignConsole stranded-work repair; D1 migration CASE/depth surgery |
| Kimi K3 | kimi-coding (API key) | Deep thinking / proof-shaped reasoning | capability battery: covariance rank proof |
| MiniMax M3 | minimax (API key + OAuth) | Agentic tool use, data wrangling | capability battery: kanban DB analytics |
| Gemini 3.8 Flash | gemini (API key) | Vision: photo/figure/video analysis; all hermes image input routes here | capability battery: scientific figure analysis |
| Grok (xAI) | xai-oauth | X/Twitter-aware search | **needs re-login** (credential expired) |
| Copilot pool | copilot | Free-tier auxiliary calls | pooled credentials, on demand |
| HuggingFace serverless | huggingface | 139 open-weight models for cheap/experimental calls | provider cache inventory |

## Venue routing rules

1. **Cloud for control, local for heavy work, GCP for paid burst** (repo AGENTS.md rule; the swarm implements it literally).
2. **Vision → Gemini 3.8 Flash** (hermes `auxiliary.vision`; worker `GOOGLE_MODEL` pin).
3. **Default agentic work → GLM-5.3**; on failure the chain is Fable 5.1 → Astra → K3 (hermes `fallback_providers`).
4. **Writing/review/design → Fable 5.1** when available; **long-horizon web research → Astra**.
5. **Anything durable/scheduled/public → the worker** (crons, ledger, console); **anything interactive/heavy → local hermes via bridge jobs**.
6. Auth posture: Anthropic and OpenAI ride OAuth subscriptions (Max/Codex); zai/kimi/minimax/gemini ride API keys; the worker holds only server-side keys (OAuth impossible there).

## Reproduction commands

```bash
# direct specialty call
hermes -z "…" -m glm-5.3 --provider zai
# cloud→local dispatch (lands in glim-ledger + CampaignConsole)
curl -X POST "$WORKER/bridge/jobs" -H "Authorization: Bearer $HERDR_BRIDGE_TOKEN" \
  -d '{"machine_id":"aledev","agent_kind":"hermes","prompt":"…","campaign_id":"…"}'
# bridge daemon (systemd)
systemctl --user status herdr-bridge
```

## Known gaps

- xAI/Grok credential expired (re-login needed).
- Bridge treats "turn ended, background children pending" as done — single-session prompts only until fixed.
- Cloudflare Access app never configured: browser-admin routes on the worker fail closed (token-only machine access until then).
