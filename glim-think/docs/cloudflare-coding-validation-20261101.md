# Cloudflare coding runner validation — 2026-11-01

The dedicated `lupine-coding-runner-v01` completed one bounded coding task against
the pinned `alexwelcing/lupine-rhizo` source. Its successful execution received a
separate acceptance decision in Rhizo's D1 ledger; the corresponding agenda task
is `done`. This acceptance covers the coding execution and captured artifacts.
It does not establish scientific validity, model-backed execution, or publication.

The core acceptance record is dated **17:47:04 UTC**. It identifies Worker version
`e1d9a276-c26d-47df-94ee-24b91e6d9ae6`, runner core commit `02a2440`, and shared
source commit `967fb3b1e37a10f88bdbc39ca8e95fb7c8945e00` in
[PR #157](https://github.com/alexwelcing/lupine-rhizo/pull/157). These are recorded
release identities, not a claim that the PR is merged.

## Verified execution

- **54 local focused tests passed**, with no failures; the isolated TypeScript
  check passed.
- The hosted guest checked out commit
  `e4c159bdb44066f8739de867184619a195f83462`, ran **six selected synthetic contract
  tests** with six passes and zero failures/skips, compiled the selected Python
  file for syntax, and captured a guest-only file change and its patch.
- The guest reported UID **0**, Git **2.47.3**, Python **3.13.5**, and Node
  **24.22.1**. Its managed `cloudflare/debian-trixie` image is an alias, not a
  digest-pinned image. Internet access was explicitly enabled for package setup.
- The terminal recorded exit **0**, confirmed cleanup, and committed ledger
  persistence. The offline operational audit independently hashed all **14**
  downloaded evidence objects and passed **68** checks. A separate acceptance
  SQL review passed **17** checks; returned D1 rows show `succeeded`, `accepted`,
  and agenda status `done` for this attempt.
- An identical live submission returned HTTP **200**, `created:false`, the same
  terminal hash, and unchanged claim/update timestamps and cleanup count.
  Unauthenticated access to its evidence returned **403**.

The successful attempt is `coding-cloudflare-shallow-source-20261101-01`.
Its immutable terminal receipt SHA-256 is
`34afbb846c48dbe8f3a6370d78ca1565c2b77dea068fa11c21c1c10e750d2cc1`.

## Retained failures and source correction

Two earlier attempts remain `failed` and their agenda tasks remain `blocked`,
with no acceptance decision. Both stopped before the operator command. The first
retained only bootstrap diagnostics, so its exact failing stage is unresolved.
The second preserved source reception and checkout output: reception verified the
bundle, then Git 2.47 rejected missing parent objects during ordinary checkout.

The fix introduced an explicit `git-shallow-bundle-v1` source kind whose boundary
must equal the requested commit. It writes that boundary before local unbundling,
then verifies exact checkout, the shallow marker, one visible commit, and strict
Git integrity checks. It preserves the current commit and tree without claiming
complete ancestor history. The original `git-bundle` path and both failed records
were left unchanged; the successful run used a distinct authorized task.

## Operational scope

Evidence resides in the separate private R2 bucket, outside the guest. Operator
and provider credentials are not supplied to the guest. No inference was
requested by this qualification, and no recurring schedules were added.
`glim-think-v1` and `lupine-research-team-v02` were not redeployed by this release.

Until the main Rhizo scheduler exclusion is released, coding agenda tasks must be
preclaimed to `cloudflare-coding-runner` with the exact canonical manifest hash.
Unknown execution is never automatically replayed; terminal reconciliation only
retries persistence of frozen evidence. See [runner operations](cloudflare-coding-runner.md).

Operator-local provenance is retained under
`work/cloudflare-coding-implementation-20261101/`: `core-completion.json`,
`independent-core-live-review.json`, `independent-core-acceptance-sql-review.json`,
`core-live-idempotency-and-evidence-auth.json`, and
`private/core-ledger-after-acceptance.json`. The 14 raw objects and their download
manifest remain private; this document does not publish them.

## DSH qualification: retained first build failure

The first separate DSH task installed and verified Node 22.22.3 and the selected
Harness service files, then exited 1 while building the Runtime. The captured
lock had 645 package entries; npm reported 554 installed packages. Its installation
mode omitted the required `@deepseek-ai/dsh-scope` peer, and the build could not
resolve that module. These are different dependency counts, not model activity.

All 17 evidence objects were downloaded and independently hash-checked. Cleanup
and ledger recording were confirmed. The joined Runtime/Harness fixture had not
started; its output is an explicit absence record. The failed task and its
terminal hash `3f45135a493cd043c885a5f0590bf472eb397966daf0f386a517d362a4f2db24`
remain immutable. The corrected composition was tested separately, as recorded below.

The accepted core run does not establish a DSH model loop or subscription
inference route. Any scripted integration result must remain distinct from
actual provider inference and scientific acceptance.

## DSH Runtime and Harness: successful scripted integration

The distinct `coding-dsh-peer-qualification-20261101-01` attempt ran the actual
pinned Superagent Runtime with Harness **0.2.1-rc.3** in Cloudflare and returned
exit **0**. It used source commit
`755e7b567eff7cdecf850775afde9e0a7f69c6c7`, official Node **22.22.3**, and the
reviewed dependency lock. All **644** baseline non-root records remained unchanged;
three explicitly pinned peers were added. The exact lock hash remained unchanged
after installation. There was no fresh dependency resolution.

The fixture mounted nine actual Harness services and completed one durable
Ticket through **eight scripted transport requests** and four tools:
`orchestrator_route`, `read`, `bash`, and `orchestrator_report`. The bounded
arithmetic tool returned **7** for the synthetic fixture `[1, 2, 4]`. The tool
named `bash` is a registered fixture that executes that exact bounded Node
process; it does not qualify the shipped unrestricted DSH shell. This checks
orchestration and tool dispatch, not a materials prediction or a model response.
The script reported successful service disposal, and the outer runner
separately recorded container cleanup and ledger persistence.

All **17** archived evidence objects were downloaded and hash-verified. The
terminal receipt is
`239a9f5005095cfe3f3a3f53f9092f62157fb2cf3fd5ff15c16063e41b67abd6`.
An independent audit passed **73** checks. Separate acceptance was recorded in
Rhizo and read back as `accepted` with agenda status `done`. The first DSH failure
and both earlier source-import failures remain unchanged. npm reported **557**
installed packages, distinct from the **648** lock entries.

This composition uses the documented snapshot/session/workspace/permission and
no-listen bridges, with a deterministic transport in place of a model provider.
It does not qualify the shipped full native plugin graph, final channel report
delivery, crash/restart recovery, included-subscription inference, or scientific
acceptance. No provider token usage was measured. Public Node/Git/npm
setup required network traffic; zero total HTTP traffic is not claimed. Frozen
preparation recipes retain their pre-execution descriptions; this dated record
states what actually ran.


## Included-plan coding and durable queue scheduling

A later, separately reviewed release added a binding-only MiniMax broker in
`lupine-research-team-v02` and a durable exact-task queue in
`lupine-coding-runner-v01`. The live coding Worker is
`0f426b3e-c3bc-4a25-b668-d85468386596`; the research Worker is
`f9228459-74df-4ad6-a9a7-c6a118533723`. The existing native and Claude runtime
bundles are unchanged. The main `glim-think-v1` service was not redeployed.

The enabled queue admits at most one task at a time, four attempts per day and
sixteen over this policy's lifetime. Each attempt reserves 1,230 seconds without
refund. Durable Object alarms dispatch authorized entries; there is no idle
polling alarm, recurring chat task, or autonomous task generation. The scientific
research supervisor remains paused. Enabling this queue does not resume it.

The broker routes only to the existing included MiniMax subscription. Provider
and operator credentials stay outside the guest. The guest receives a scoped
attempt capability with a sixteen-call ceiling and original deadline. Fresh
observations of credit controls and authenticated quota remain admission gates;
this browser-dependent proof lifecycle is not fully unattended. Claude OAuth is
not connected to this coding runner, and no new sign-in was required for MiniMax.

Validation before these releases included **141 coding tests**, isolated
TypeScript and Worker dry-run checks, and **1,985 research-package tests** with
nine skipped, zero failed and 25,969 assertions. Source/runtime preservation was
checked separately from model execution. The following attempts are distinct;
none rewrites a historical failure or reuses its model allowance.

### Model attempts and precise failure attribution

1. `coding-repository-assessment-20261101-01` ended `unknown` with incomplete
   command evidence, confirmed cleanup and **zero broker calls**. An oversized
   tool surface was reproduced locally, but the generic archived error does not
   identify its first failing predicate; the hidden-schema issue below could
   occur earlier. A separately reviewed disposition released only its scheduler
   hold after joining the terminal receipt, ledger and closed zero-call broker.
   Its outcome and reserved budget remain unchanged.
2. `coding-repository-assessment-v2-20261101-01` ended `failed` with **zero broker
   calls**. Real Zod schema conversion attached hidden `~standard` metadata that
   the strict JSON boundary rejected. The v3 recipe removes only that exact,
   identity-checked root metadata while retaining JSON-schema bytes and all
   other rejection rules. Its tests use actual pinned Zod and DSH utilities:
   **80 Node tests and eight Python tests passed**. Earlier synthetic coverage
   had substituted `structuredClone` at this boundary and missed the defect.
3. `coding-repository-assessment-v3-20261101-01` reached **16 completed MiniMax
   model turns**: three orchestrator turns and thirteen worker turns. The actual
   sixteen-tool orchestrator and eight-tool worker surfaces worked. The worker
   continued inspection until a seventeenth turn was refused before dispatch;
   no assessment was produced. This is a finishing/budget orchestration failure,
   not a provider outage or schema failure. The broker closed with no pending
   unknown operation; container cleanup and ledger recording were confirmed.

The third terminal SHA-256 is
`37d7db1340ac641f8a75a078283a963dd8fa6a02b2e8f6d37f8bc3ce4ce19fde`.
Its source revision is `3b68498f8a61f2a83be4c9faf9fc9cdf8f746981`, distinct from the
Worker deployment revision. All 21 archived objects (524,911 bytes) were
retrieved and hash-verified. The usage receipts report 57,437 input tokens, 4,684 output tokens and
305,662 cache-read tokens, with zero cache-creation tokens reported. These are
provider usage fields, not billed dollars or independently measured tokenization.
An independent review passed 58 checks across all objects and joined model
operations. The tracked-source patch is empty; untracked output is captured
separately. Assessment files contain explicit absence records,
not substitute reports. None of these three model attempts received coding,
scientific, or publication acceptance. Provider HTTP request count and billed
USD remain unknown; model turns are not an HTTP count.


### Separately versioned completion controls

The v4 guest recipe keeps the total sixteen-call limit and original task deadline.
It allocates six calls to the master and ten to the worker, reserves master
finalization capacity, and closes exploration after global call eight. A fixed
writer creates immutable JSON/Markdown findings; the existing `ready` report is
refused until the artifacts validate. Final readback catches later alteration.
Known local role refusals preserve the other role's reserve; unknown provider
outcomes retain the existing whole-attempt stop.

Both the author and independent reviewer ran **104 Node tests and eight Python
process-boundary tests**; the independent review also passed **85 source, patch
and preservation checks**. A
separate three-turn offline check passed **20 assertions** across the actual guest
adapter and broker core, using synthetic store/archive/provider implementations.
It verified distinct immutable budget-feedback snapshots, continuation-prefix
integrity and server-only retention of synthetic private reasoning. This fixture
did not execute Harness, native tools, real provider inference or platform storage.

The v4 recipe hash is
`281b5e73d583dda3632d24a38b07deab3501140e8122c86b5e9b9ab694182887`;
its adapter hash is
`8af187cbf5bc0af0c6c805fd1adfd5dac17989e84604589cff5ebb4a6341108e`.
The worker's structured coverage and source-path checks are not independent
semantic acceptance or proof that each file was read. A failure retains explicit
incomplete state, not a manufactured successful report.


### V4 live result: provider error response and retained ownership

The distinct `coding-repository-assessment-v4-20261101-01` attempt was dispatched
by the Cloudflare alarm at **21:00:36 UTC**, using source commit
`0e47b7935b8d932edcf7daecf230c5f9b528a4ab`. It checked out the exact 63,334,542-byte
bundle. The command ended with exit **1** and confirmed container cleanup and
ledger recording. Its terminal is **unknown**, reason
`model-terminal-unconfirmed`, with SHA-256
`6e5672758013ad2ec9aa72e8fe124df57a6d3d374dbc888d86a83d57992e1748`.
All **21** captured objects (510,973 bytes) were retrieved and hash-verified.

Eight calls completed and reached Harness: three master and five worker turns.
The ninth operation was dispatched and returned HTTP **200**, but its exact
10,982-byte archived response used **`stop_reason: "error"`**. The unchanged
MiniMax validator rejected that control value; the account retained
`invalid-provider-response` and the broker retained `provider-unknown`.
Independent offline execution of the exact validation helpers identified this
predicate. The response contained zero tool-use blocks and was never released to
Harness. Private reasoning and message text are not published. Raw usage fields
in this unaccepted response are excluded from completed-call totals.

This failure occurred at nine local reservations, without a role-budget refusal;
it does not establish a budget or conversation-prefix failure. A subsequent
master request encountered the already stopped transport and produced a generic
error. That later error is not the primary cause. The writer was never attempted,
and the assessment files remain explicit absence records. There is no new coding
acceptance, scientific acceptance or publication.

Read-only account metadata confirms that the exact ninth request still owns the
shared MiniMax account pool. The scheduler retains an unresolved **active** slot
(`active=1`, `held=0`, `queued=0`), with **four attempts / 4,920 reserved seconds**
and no next alarm. The policy remains enabled; neither its daily budget nor its
ownership rules were reset. The account admission gate is `attention`, reason
`account-pool-owned-no-replay`. A new login or quota observation does not resolve
that ownership.

The existing zero-dispatch scheduler disposition is inapplicable: this attempt
has eight completed calls and a ninth confirmed dispatch. The old compactor
acknowledgement and task-specific scientific reconciliation paths also do not
apply to this primary coding operation. Further recovery needs a separately
reviewed operator acknowledgement for this exact captured error response,
binding the account operation revision, original receipt, closed broker,
container cleanup and ledger terminal. It must preserve the unknown outcome,
reservation, unaccepted usage and prohibition on replay. No such authority was
added or invoked during these trials. No further model attempt was launched.


### V5 diagnostic preparation; no further live attempt

The final independent V4 audit passed **108 checks**, joining all 21 archived
objects, nine installed identities and 21 recipe pins. It confirmed that the
primary error response, shared account ownership and scheduler reservation
remain unchanged. The provider's underlying reason for the error is unknown.

The separately versioned v5 recipe preserves the first broker failure before a
later local refusal can mask it. Diagnostics retain only fixed, bounded protocol
metadata. Interrupted output delivery is labelled incomplete and possibly
partial; it is not misrepresented as zero delivery. The initial review finding
and its correction are recorded separately.

The author passed **111 Node tests and eight mocked-process Python tests**. The
independent reviewer reran **seven focused diagnostic tests** and passed **96
identity and preservation checks**; the full author counts were verified from
logs, not independently rerun or added to these counts. The final source lock is
`ecf45076ae03bfa0888733af49394d2da10f653402a3724b0c07596efaddc12a` and adapter hash is
`daf191e2c0300feee89b2717469a0e459bcdf3bca36564032279845ba5a5e438`.

This is local diagnostic preparation only. It changes no provider terminal
validation, Worker or broker source, model cap, ownership, settlement or replay
rule. No v5 task was enqueued, run or deployed. Four scheduled attempts consumed
the installed daily reservation budget. The exact-identity operator recovery
contract remains a proposal requiring separate implementation and review, not an
available release action. No new subscription-model assessment was accepted.
