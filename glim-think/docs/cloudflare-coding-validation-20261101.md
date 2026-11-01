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
