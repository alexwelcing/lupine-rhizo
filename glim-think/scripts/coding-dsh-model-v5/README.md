# DSH subscription composition v5: preserve the first withheld-response diagnostic

This version changes guest diagnostics only. The actual v4 attempt completed
8 model turns, then its ninth HTTP200 response contained `stop_reason: error`.
The existing transport correctly withheld it as an invalid terminal. The shared
account operation and coding attempt remain unknown and must not be replayed.
The raw rejected response usage is not part of accepted usage totals. V5 does
not relax that validator, settle the operation, enlarge budgets or run another
attempt.

V4 recorded the unknown ninth turn but left `firstFailure` empty until a later
master request filled it with a secondary stopped/exhausted message. V5 now
records a fixed first broker-response diagnostic before stopping. Only known
protocol states/reasons and a matching ordinal/request-ID shape may appear in
that diagnostic; arbitrary provider text, prompts and reasoning are never
copied. Unqualified responses receive fixed generic labels. Up to four later
preflight refusals are retained separately, without replacing the initial cause.

The diagnostic does not authenticate a provider terminal, release output or
reclassify the guest turn. Even a claimed not-dispatched denial leaves the guest
record unknown until separately authoritative evidence establishes otherwise.
HTTP failures, malformed JSON, aborted output delivery and queued local stops
retain fixed boundary classifications. Provider fallback and automatic replay
remain forbidden. This preparation is local only; no v5 model execution or
production deployment is claimed.

The additional tests exercise the primary-then-secondary sequence, malformed
response privacy, identity mismatch, accessors, detached bounded metadata and
absence of result release/replay. Run `transport-diagnostics.test.mjs` with the
inherited suites below.

# Inherited v4 completion policy

V3 completed sixteen real MiniMax model turns, but used all of them before the
worker wrote its assessment. This separate recipe adds enforced completion
budgets. It does not increase the immutable sixteen-call, 4096-output-token or
900-second ceilings. Earlier recipes, attempts and evidence remain unchanged.

The fixed command is `python3 glim-think/scripts/coding-dsh-model-v5/execute.py`.
Only a separately authorized `dsh-subscription` attempt may execute it. The
one-task broker capability arrives through `LUPINE_CODING_MODEL_CONFIG_JSON`;
the guest never receives provider or operator credentials. Root in the guest is
not an isolation boundary against its parent process: the scoped capability is
bounded and minimized.

## Completion policy

- One Runtime-identified master gets at most six reservations; one exact
  ticket-linked worker gets at most ten. Only three master reservations are
  available before a genuine ready worker report and valid assessment files.
- Reservations include queued turns, are synchronous and are never refunded.
  They are not provider invocations. The transport/broker records actual
  dispatch and settlement independently. A local known-no-send role refusal
  preserves other-role capacity; an unknown provider outcome stops all roles.
- Exploration execution ends after global reservation eight. Worker tools then
  allow only `assessment_write` and `orchestrator_report`. Master finalization
  permits `orchestrator_read` and `orchestrator_reply`. Tool definitions and
  system context stay fixed throughout each session.
- Tool-owned `finalizeContent` appends a fresh JSON budget snapshot before the
  actual Harness freezes and persists each completed tool result. Existing
  history is never rewritten. Guards return bounded explanations when refusing
  late exploration. Original deadline checks remain in force.
- A role-budget refusal followed by a continuously idle, empty model queue for
  one second terminates the host as incomplete. This prevents an idle wait until
  the original task deadline. Active or uncertain work is not declared complete.

The allocation prevents the worker from consuming reserved master calls. It
cannot guarantee useful prose, sufficient source coverage or completion. A
controlled failure stays failed/incomplete. The host never fabricates an
`orchestrator_report` or marks a ticket ready itself.

## Stable tool surface and artifacts

The Runtime requires the inherited `read` name to be registered. It stays
registered but is denied alongside the five unavailable placeholders. Each
trusted agent scope receives one own `assessment_write` tool. Master and worker
surfaces remain respectively sixteen and eight tools. Native `bash` supports
bounded source inspection during exploration, with 30-second and 64-KiB output
caps; it receives no broker capability in its environment.

The writer validates the exact revision, eight named domains, three proposals
with failure/recovery tests, limitations/exclusions, bounded text and cited
paths that exist as blobs in the pinned Git commit. From one structured payload
it writes readable Markdown and JSON at:

```
.lupine-coding-evidence/repository-assessment.json
.lupine-coding-evidence/repository-assessment.md
```

Both files are exclusive writes, bounded to 64 KiB each, hash-read back and
immutable after success. Partial writes remain uncertain and cannot be
overwritten. Identical repeat calls can only read back the same pair.
`incomplete` status cannot pass ready admission. A ready report requires complete
declared source coverage and a valid pair. The pair is checked again after
quiescence and cleanup; alteration or absence fails the command. File existence
and model assertions do not prove actual source reading or finding correctness.
Independent semantic review, scientific acceptance and publication are separate.

The eleven artifact paths remain unchanged from v3. Failed runs retain explicit
absence markers when deliverables were not produced. Partial tickets are
captured on failure. Bash exit codes are separate from the Harness error flag.

## Source and protocol qualification

The prototype stays pinned to `6337fc823ce20251c8de8085948165c81aaa701e`, the
reviewed rc.3 lock and official Node 22.22.3. `schema-registration-v4.patch`
retains the exact Zod metadata projection and adds supported tool-output
finalization. Original/derived source, helper and patch hashes are in
`projection-identity.json`; setup and model phases recheck installed source
pins. No new dependency install runs locally.

The route remains `MiniMax-M3.1-Flash` through the secret-owning subscription
broker. Identity, exact sanitized history, stable system/tools, private reasoning
exclusion, archive-before-settlement and no-replay requirements are unchanged.
No provider, broker or Worker source is altered by this recipe.

Tests use synthetic fetch responses, extracted pinned source methods and actual
previously retained Zod/util-values files. They qualify local behavior, not a
new live provider run or full Harness boot. Run:

```
node --test scripts/coding-dsh-model-v5/{transport,source-shape,completion-budget}.test.mjs
python3 scripts/coding-dsh-model-v5/execute.test.py
```

Set `CODING_DSH_ZOD_PACKAGE_PATH` and `CODING_DSH_UTIL_VALUES_FILE` to the
hash-joined retained sources for
`node --test scripts/coding-dsh-model-v5/zod-schema.test.mjs`.

External message delivery, provider HTTP counts, billed USD, crash recovery and
comprehensive network isolation remain unqualified. The assessment is private
and pending independent/human review.
