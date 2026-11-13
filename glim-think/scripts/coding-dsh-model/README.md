# Scoped DSH model transport

This composition connects the pinned DeepSeek Superagent prototype Runtime and
Harness 0.2.1-rc.3 to Lupine's MiniMax included-subscription broker. It is a new
model-capable recipe; the accepted `coding-dsh-qualification` scripted fixture is
unchanged. Running preparation is not model execution or route admission.

The original recipe still supplies the exact prototype revision, reviewed
648-entry dependency lock, nine installed source identities, setup patch and
build recipe. `source-lock.json` pins that frozen parent and this new recipe.
`bootstrap-node.py` uses the same declared Node 22.22.3 download, integrity and
deadline rules. `prepare.mjs` installs/builds with a fresh home and explicit
credential-free environment, writes `model-prepared.json`, and stops. It never
calls a model. No retry plugin, provider credentials plugin, account login,
external source, polling schedule or listening server is mounted.

The separately admitted code command receives `LUPINE_CODING_MODEL_CONFIG_JSON`:

```json
{
  "endpoint": "https://lupine-coding-runner-v01.aw-ab5.workers.dev/coding/tasks/ATTEMPT/model",
  "capability": "EPHEMERAL_ONE_ATTEMPT_CAPABILITY",
  "taskId": "TASK",
  "attemptId": "ATTEMPT",
  "inputSha256": "EXACT_MANIFEST_DIGEST",
  "maxRequests": 16,
  "deadlineAtMs": 0,
  "model": "MiniMax-M3.1-Flash",
  "maxOutputTokens": 4096
}
```

These placeholders are not an executable permit. The capability is neither an
operator token nor a provider credential. The runner must bind it durably to the
exact admitted task, attempt, source/input digest and original expiry. Setup
children receive none of this configuration. The runtime removes the variable
from its environment and does not pass it to its native tools. Arbitrary native
code in this dedicated guest remains within the authorized task's trust boundary;
this composition is not a kernel sandbox or a claim of general egress denial.

`run-agent.mjs` also requires a pinned repository file `.lupine-coding-task.json`:

```json
{
  "schema": "lupine.dsh-coding-instruction.v1",
  "taskId": "TASK",
  "instruction": "The explicit bounded coding task, including required tests and deliverable paths."
}
```

The fixed command is `python3 glim-think/scripts/coding-dsh-model/execute.py`
from the pinned repository root. It runs preparation without the capability,
then runs the model command with the exact Node executable from
`.lupine-coding-evidence/model-prepared.json`.
The model command uses the lesser of the original preparation deadline and the
runner permit deadline; it never opens a new 850/900-second window. Root orchestration
must set the model configuration only on the latter command and must preserve
preparation errors instead of attempting inference after failed setup.

## Protocol and translation

`transport.mjs` posts `lupine.coding-model-turn.v1` with task/attempt/input identity,
a global ordinal, DSH session ID and an Anthropic-shaped body. It sends at most
16 turns, serializing distinct sessions without replay. Payload limits are
256 KiB for the provider body, 300 KiB for the HTTP envelope and 128 KiB for the
response. Every completed response must join the exact identity, canonical body
SHA, reported model, private archive SHA, transport receipt SHA and confirmed
durable settlement before the adapter emits any content.

Supported DSH content is a leading text system message; text user messages;
assistant text/native tool calls; and correlated text tool results. Tool
definitions map `parameters` to `input_schema`; result `toolCallId` maps to
`tool_use_id`. Consecutive tool results become one ordered user message. The
first version freezes each session's system/tools. Developer updates, deferred
tools, image/file/reasoning blocks, sampling overrides, altered histories,
missing results and unknown types are refused before HTTP. This is an explicit
subset, not full Harness adapter compatibility.

The broker restores provider-private thinking from its own previous archived
response only after exact sanitized history-prefix matching. It must not trust
assistant history invented by the guest. The guest receives only text and
`tool_use`, then emits Harness `block-start`, deltas, `block-end`, `usage` and
`finish`. These are buffered events after settlement, not a provider streaming
latency measurement. A transport exception, malformed/late result or abandoned
emission stops the attempt; subsequent turns cannot retry it. Provider retry
policy is explicitly zero. Denials and unknowns require controller inspection.

Usage retains provider input/output and separate optional cache fields. Missing
cache usage remains null in telemetry and is omitted in Harness usage; no total,
reasoning-token count, provider HTTP count or billed USD is invented. Each record
includes session, ordinal, request/output sizes, identities, receipt hashes and
whether output reached Harness. A completed coding report is not scientific
acceptance or permission to publish.

## Tools and evidence

The actual Runtime uses the separately attributed snapshot setup/session/workspace
bridges from the accepted composition. One local instruction source and one
worker are enabled. Native `read` checks a repository-relative resolved path and
reads at most 64 KiB. Native `bash` runs the authorized coding task in the pinned
repository with an explicit empty-credential environment, 30-second per-command
ceiling and bounded capture. It can edit code; its permissions come from the
dedicated coding guest, not from the metadata permission bridge. The outer
container must confirm destruction, including descendants, before success.

Successful preparation and model composition emit seven preparation artifacts plus `model-runtime-result.json`
and a bounded `model-worktree.patch`. Model inputs and raw sessions stay private
in the disposable guest. The runtime artifact contains metadata and hashes of
tool outputs/reports, not raw thinking. The tracked diff excludes untracked
deliverables; their exact paths must be declared in the task artifact list.
Local final-channel delivery and crash recovery remain separate unqualified gates.

Offline adapter checks use only authored broker responses:

```sh
node --test scripts/coding-dsh-model/transport.test.mjs
```

Passing these tests does not establish actual MiniMax inference, fresh quota,
credits-OFF evidence, installed Worker binding, hosted guest connectivity or
scientific usefulness. Those require distinct reviewed live receipts.
