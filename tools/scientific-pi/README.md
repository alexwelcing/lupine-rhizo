# Scientific PI: subscription CLI workers

This is the execution adapter for a bounded research cycle:

1. **Proposer**: Codex on the Mac reads current primary literature and formulates a falsifiable hypothesis.
2. **Independent critic**: Claude Code on aledev challenges the supplied proposal, prior-art boundary, confounds, and proposed discriminating test.
3. **Adjudicator**: Codex considers that critique and records a decision and revised test design.

The adapter never starts an experiment, sends a message, publishes a page, or schedules another run. It accepts an explicit job, invokes the installed official CLI once, validates its completed response, and exports a receipt for glim-think's durable ledger. A completed CLI call is **not** scientific validation or approval to execute its proposed experiment.

## Authentication and isolation

Python 3.9+ and the official CLI must already be installed and signed in on the host that runs it. The intended setup is ChatGPT sign-in for Codex on the Mac and Claude.ai sign-in for Claude Code on aledev. The script reads each CLI's public `login status` / `auth status` interface, never credential files. Credentials remain in their local official stores. API-key and alternative-provider environment overrides are removed from the child process.

Codex is run with a read-only sandbox, a fresh temporary working directory, `--ignore-user-config`, and disabled shell, editing-related command runtime, hooks, plugins, apps, memories, delegation, computer/browser control, image generation, and optional local automation features. The Code Mode **host remains enabled** because this Codex build requires that wrapper for web retrieval. Underlying tool permissions remain restricted. The full JSONL stream is checked for forbidden/unrecognized item types before accepting a result.

Claude is run with `--safe-mode --restricted`, an empty strict MCP configuration, disabled slash commands, no session persistence, no permission prompts, and an explicit tool list. Literature work can use only `WebSearch,WebFetch`; packet critique uses `--tools ''`. **Do not add `--bare`**: that mode changes the authentication path and is unsuitable for the intended subscription login. Required isolation flags are checked against installed help before inference; hidden `--max-turns` is checked by parsing it with `--help`. Managed organization policies still apply.

Future Claude jobs use `--output-format stream-json --verbose --include-partial-messages`. The runner checks startup tool/plugin/MCP metadata and every observed tool call, terminates on a forbidden action or unknown protocol event, and accepts only one successful final result with matching session identity and valid structured output. `StructuredOutput` is allowed solely as the CLI's schema-formatting tool. No-tools criticism may not claim it independently verified the cited papers. Codex literature proposals require at least one completed web-search event. Claude literature proposals require a completed observed search or a positive server web-search counter. These checks establish retrieval activity, not the scientific correctness of retrieved material.

Startup/session/model information and event counts survive a timeout in the receipt, while incomplete message content remains only in the private bounded log. A partial response, session ID, or even a final event before a process timeout never becomes an accepted review. Unknown capability strings and documented metadata-only warning/status events are treated as data; unknown event types, permissions denied, startup customizations, undeclared tools, and changed session identities fail closed. This future diagnostic improvement does **not** resume or replay the original timed-out critique. Legacy buffered JSON transcripts remain parseable for offline evidence review; their receipts clearly state that a full tool trace was unavailable.

## Interface

The same file is usable on either host. Remote transport remains the original named-device Homebase controller; this directory contains no SSH, Tailscale, daemon, or credential-copy code.

The manual controller connects these adapters into one cycle:

```sh
python3 tools/pi-cycle.py --brief /absolute/brief.json \
  --state-dir /absolute/private-runs --cycle-id new-cycle-id
```

Its brief contains exactly `question` and `context` strings. Optional `--adopt-discovery completed-job-id` reuses only a validated completed Codex proposal with matching brief, role, machine, and hashes; it does not retry failed work. The private SQLite ledger records validated completed packets and identity-checked failed receipts with a null result. A failure stops the cycle before the next stage. Existing stopped cycles and ledgers are not retrospectively changed. Controller CLI paths currently target this Homebase Mac and pinned aledev.

```sh
python3 tools/scientific-pi/pi_runner.py run \
  --job /absolute/private/path/proposer-job.json \
  --state-dir /absolute/private/path/pi-runs \
  --cli /absolute/path/to/codex
```

Example job (the question is illustrative, not an executed study):

```json
{
  "schema_version": 1,
  "job_id": "discovery-unique-id",
  "campaign_id": "lupine-research-cycle-id",
  "machine_id": "mac",
  "provider": "codex",
  "role": "proposer",
  "question": "Which test would distinguish a shared MLIP transfer bias from an evaluation confound?",
  "context": "Provide only the evidence authorized for this research question.",
  "model": null,
  "tool_mode": "web",
  "timeout_seconds": 240,
  "max_output_bytes": 524288,
  "max_turns": 8,
  "review_of": null,
  "critique_of": null
}
```

`model: null` uses the CLI default; if the CLI does not report its actual model, the receipt records `null`, never a guessed model. `max_turns` bounds Claude's reasoning loop. Both providers have a hard wall-clock limit and aggregate stdout/stderr byte limit. Preflight has up to three additional five-second bounds. Future remote reviews use the one-shot asynchronous interface below with a 300-second inference deadline, independent of the short Homebase launch/status calls. The asynchronous hard ceiling is 600 seconds. The original synchronous 95-second critique timed out and has not been replayed; no completed Claude review has been established by the lifecycle tests.

### One-shot asynchronous remote work

For a **new** authorized job, the host exposes two Python functions:

```python
ack = launch_job(job, "/absolute/private/pi-runs", "/absolute/path/to/claude")
state = read_state("/absolute/private/pi-runs", job["job_id"])
```

Equivalent local CLI entrypoints are `launch --job ... --state-dir ... --cli ...` and `read-state --state-dir ... --job-id ...`. `launch` reserves `STATE/.launches/JOB_ID/` exclusively, writes an immutable intent containing the normalized job hash and a content-addressed runner snapshot, then creates exactly one detached worker. Its stdin is closed; stdout/stderr use private local files, so an SSH disconnect does not own the worker's terminal. The worker claims its identity once, writes its PID/process-group/launch identity, and runs the existing bounded runner. It has no queue, server, or general background loop.

Launch acknowledgment has `status: launched`, `launch_id`, `worker_pid`, `job_sha256`, and `automatic_retry: false`. A known process-creation failure returns `launch_failed`; failure after process creation returns `launch_unknown`. **Neither permits resubmission.** Any existing launch intent or execution directory permanently reserves that job ID, including after a crash or failed launch. Metadata-only failures preserve the intent even when an acknowledgment cannot be saved.

`read_state` performs no launch or filesystem write. It returns `{job_id,status,completion_unknown,receipt,result,launch}`. Before a complete worker exit record and matching terminal receipt, its status is `pending` with no result. A PID is diagnostic evidence only. Completion requires a matching immutable intent, worker ownership and exit record, normalized job hash, zero process exit, session identity, accepted scientific schema, and result hash. Failed receipts remain failed; timeouts remain completion-unknown. A controller may issue bounded read-only status calls after a definite launch acknowledgment. A failed or uncertain launch/transport must stop without relaunching or treating elapsed time as success.

Each launched job's snapshot and stdio are private. The parent may reap its own finished OS children; this is process cleanup, not another job or a status claim. Tests use fake CLIs to prove detachment, exclusive identity, status validation, and deadline cleanup. They do not establish live Claude completion or authorize another research request.

For a critic, set `provider: "claude"`, `role: "critic"`, `tool_mode: "none"`, and include:

```json
"review_of": {
  "job_id": "the-completed-proposer-job-id",
  "packet_sha256": "sha256-of-canonical-result-json",
  "packet": {"...": "the complete validated proposer result"}
}
```

For adjudication, use Codex with `role: "adjudicator"`, `tool_mode: "none"`, retain the same `review_of`, and add `critique_of` with the independent critic's job ID, result hash, and complete packet. The critic must name the exact original proposer job and packet hash. Canonical hashes use Python `json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()`.

Output schemas are available without authentication or inference:

```sh
python3 tools/scientific-pi/pi_runner.py schema --role proposer
python3 tools/scientific-pi/pi_runner.py schema --role critic
python3 tools/scientific-pi/pi_runner.py schema --role adjudicator
```

Schemas require primary sources, closest prior art, possible novelty explicitly marked unverified, competing explanations, a falsifier, a cheap test with a baseline and decision rule, and explicit `not_started` execution. Adjudication must respond to independent critique. At least two distinct external HTTPS primary sources are required. An internal research-brief source may additionally use exactly `urn:lupine:JOB_ID:context`, with `publication_kind: primary_research_report`; no other URN is accepted. Validation checks structure, linkage, and claim boundaries; it does not establish that a citation or scientific argument is correct. Validated results are capped at 48 KiB for Homebase transport.

## Durable state and no replay

Before inference, the runner atomically creates `STATE/JOB_ID/` and writes a manifest. It refuses any existing job ID, even if the earlier attempt failed, timed out, or crashed. No automatic retries are performed. A corrected task must receive a deliberately assigned new identity; it must not conceal or overwrite the earlier receipt.

The job directory contains private, mode-0600 files:

- `manifest.json`: input, canonical input hash, runner version and no-retry rule.
- `started.json`: original runner PID and start time, when inference was launched.
- `stdout.log`, `stderr.log`: bounded local protocol evidence. Never upload these automatically.
- `receipt.json`: final completion state, timing, exit status, usage when available, actual model when reported, session ID and evidence hashes.
- `result.json`: present only after a valid successful completion.
- `ledger-beat.json`: metadata-only body compatible with authenticated `POST /feed/beats` and the `lab_beats` ledger.
- `bridge-result.json`: advisory legacy `{status, output_excerpt, beat}` projection, **not ready to submit** to the current scientific-job API. Current bridge submission additionally requires a valid machine-scoped claim token and a validated scientific receipt supplied by its controller. This runner neither acquires nor stores claim tokens, and never enqueues or claims bridge work.

The runner prints only the receipt to stdout. It never uploads anything. The surrounding controller can review and submit the metadata-only ledger beat, or project the final adjudicated hypothesis into glim-think's scientific receipt contract. Keep raw packets, local credential stores, and device state outside Git and the public Library.

On timeout, output overflow, interrupt, or a streaming protocol/tool-policy violation, the entire child process group receives termination followed by a bounded kill. Such a result has `completion_unknown: true`; cancellation does not prove the remote model backend stopped immediately. Missing/failed completion events, forbidden tool attempts, bad schemas, and hash mismatches never become success. Provider-internal retry events, if reported by Claude, are counted separately; the runner itself never replays a job.

Read-only recovery after an outer transport timeout:

```sh
python3 tools/scientific-pi/pi_runner.py status \
  --state-dir /absolute/private/path/pi-runs --job-id the-original-job-id
```

A manifest without a terminal receipt reports `completion_unknown`. Do not rerun a remote command to resolve it; inspect the original process and preserved evidence through an authorized read-only path.

If a parser bug rejects an otherwise completed original CLI process, `reconcile` can validate the saved transcript offline after that parser is corrected:

```sh
python3 tools/scientific-pi/pi_runner.py reconcile \
  --state-dir /absolute/private/path/pi-runs --job-id the-original-job-id \
  --reason 'Describe the precise parser correction and supporting evidence.'
```

This never runs a subprocess or makes an inference call. It is restricted to `invalid_result` receipts from an original zero exit with no timeout/interrupt/output stop. It checks manifest linkage, stream sizes, and previously recorded stream hashes when available. The original receipt and export files are preserved as `*.initial.json`; the accepted receipt records the reconciliation reason/time, prior receipt hash, and zero new inference calls. Older receipts lacking stream hashes explicitly retain that limitation. A reconciliation lock prevents duplicate acceptance. Timeouts, nonzero exits, and unknown process state cannot be reconciled into success. The local hashes provide traceability, not a signed or tamper-proof audit log.

## Focused tests

```sh
python3 -m unittest discover -s tools/scientific-pi/tests -v
```

Fixtures are clearly fictional protocol data, not research results. Tests cover completion validation, cross-agent packet hashes, streaming startup/partial/unknown events, immediate forbidden-tool termination, missing/failed receipts, once-only identity, output limits, and actual process-group termination. They never call a model or a remote device.

## Supported CLI references

- [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference)
- [Codex authentication](https://developers.openai.com/codex/auth)
- [Claude Code programmatic use](https://code.claude.com/docs/en/headless)
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Claude Code authentication](https://code.claude.com/docs/en/authentication)

Runtime flags were checked against Codex 0.160.0 and Claude Code 2.1.283. Future CLI changes fail the preflight/protocol gates and require review before use.
