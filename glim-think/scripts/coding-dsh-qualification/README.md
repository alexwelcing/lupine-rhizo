# Prepared DSH scripted qualification for the coding runner

This repaired recipe revision is prepared and locally checked, but has **not**
been installed or executed. The first hosted DSH qualification installed its
captured dependency graph, then failed at bundle construction because the graph
omitted `dsh-scope`; no actual Runtime/Harness task ran. That failed attempt and
its artifacts remain immutable. This revision adds three verified runtime-import
peers before a distinct follow-up task. Keep the first core coding-runner smoke and its source
bundle immutable. A run of this recipe requires a second distinct authorized
coding task, attempt, source bundle and input digest after core acceptance.

The target is an actual Superagent Runtime joined to actual installed Harness
agent loops, session persistence and tool services. A deterministic transport
chooses the tools. There is no provider credential, login, neural-model request,
real token measurement, research campaign or schedule. It is code-execution
qualification, not a new model execution mode or proof of autonomous research.

## One bounded command

From the pinned Rhizo checkout in the disposable coding container:

```sh
python3 glim-think/scripts/coding-dsh-qualification/bootstrap-node.py
```

Use the ordinary `lupine.coding-task.v1` manifest with `mode='code-execution'`,
`timeoutSeconds=900` and an exact source-bundle digest. The recipe requires
`enableInternet=true` for the pinned public Node/GitHub/npm artifacts.
No inference route is used, but networking remains permitted by that outer
setting; this recipe does not claim kernel egress isolation or zero total HTTP.
An offline rerun needs a separately prepared, reviewed dependency image/tree.

The declared runtime path downloads the official Linux x64 Node 22.22.3 archive
once from `https://nodejs.org/dist/v22.22.3/node-v22.22.3-linux-x64.tar.gz`.
The expected SHA-256 is
`c7a10d6816da8eaaa7534dd73c71c6e2b2c391dbbf845e364902d156615dd1b8`,
joined to the retained official checksums receipt. There is no system-Node or
runtime-download fallback. The single download has a 40-second absolute limit,
64 MiB compressed cap, verified HTTPS and no redirects or inherited proxy.
All bootstrap preparation shares a 50-second limit. The archive digest is
checked before extraction with Python's data filter, an exact top directory,
32,768-member and 512 MiB expanded-file caps. Missing Python filter support or
an unsupported OS/architecture fails closed. The fresh scratch and extracted
runtime are private to this disposable container; they are not copied to agents.

Bootstrap stdout preserves stage/error and runtime identity, including the
actual extracted executable hash. A successful bootstrap passes its identity
to the qualification summary. A bootstrap failure does not claim that later
recipe artifacts were produced. No extra export path is allocated.
The command maintains one 850-second internal deadline inside the unchanged
900-second runner command ceiling, starting before Node bootstrap; setup time
reduces the remaining recipe budget. Individual one-shot phases cap source
fetch at 120 seconds, installation from the reviewed lock at 300, bundling
at 45 and the joined task at 60. The remaining deadline can only shorten those
caps. There are no command/provider retries. npm lifecycle scripts are disabled,
and a fresh child HOME plus separate empty npm configs and disabled global/system
git config prevent account/config inheritance. These are work/time/output
bounds, not a guarantee of package-cache disk consumption or platform cost.

## Source and dependency identities

`source-lock.json` joins the retained parent fixture/build/patch to the new
portable files. The prototype is fetched once at
`6337fc823ce20251c8de8085948165c81aaa701e`, checked out detached, and compared
against the retained package hash. The exact snapshot setup patch is checked
and applied; the resulting Runtime/setup file hashes must match the retained
cloud qualification. Existing historical sources/archives are unchanged.

The original four exact top-level packages remain
`@deepseek-ai/dsh@0.2.1-rc.3`, `esbuild@0.28.2`, `proper-lockfile@4.1.2` and
`zod@4.4.3`. Three additional explicit `0.2.1-rc.3` pins are `dsh-scope`,
`dsh-sandbox` and `dsh-session-persistence` under `@deepseek-ai`. Official
integrity-bound JavaScript establishes their static imports from the selected
services. Their own runtime imports resolve to modules already in the captured
graph. Metadata-only PTC/filesystem/compaction peers are not broadly installed;
this remains the native-tool scripted composition, not every Harness mode.

`dependency-lock.json` derives from the first hosted lock, SHA-256
`0ebeb5a735422c8e29c1a16722aae5b9bb2da99754fa0084c806ce42bdd0325b`.
All 644 original non-root package records remain identical, and the root's
non-dependency fields remain unchanged. The root gains three pins and the graph
gains their three package records: 648 entries including the root, up from 645.
This is an explicit augmentation, not an unchanged dependency graph. There is
no fresh lock resolution. The recipe checks the reviewed full lock hash, count,
top-level pins, registry locations and integrity entries before `npm ci` with
lifecycle scripts disabled and `--legacy-peer-deps`, then verifies npm left the
reviewed lock unchanged. Installation and build success of this augmented graph
still require a distinct hosted observation.
The installed Harness package manifest and six service files must match the
original retained hashes; the three added modules must match their newly
qualified official JavaScript hashes. Bundling deliberately maps all prototype
`@deepseek-ai/*` imports to those installed rc.3 packages. The alpha-era peer
graph is not asserted to work unchanged. `build-runtime-bundle.mjs` records
the actual Node/esbuild versions, compiled bundle hash and bundled-input
hashes. Its target is now Node 22.19, matching the minimum supported engine;
the original cloud build used Node 24 as its bundler target. This portability
change has not yet been execution-qualified.

## Explicit bridge and task scope

The portable `joined-runtime-agent.mjs` derives from the retained joined fixture.
It replaces former `/workspace` paths with explicit staging paths and reads a
bounded snapshot of this coding artifact's actual Git revision and README.
The arithmetic fixture remains synthetic `[1,2,4] → 7`; it is not a material
prediction or a whole-repository evaluation.

It uses the same explicit snapshot setup port, actual AgentRegistry handles
behind a custom session-controller bridge, cwd-to-workspace map, permission
bookkeeping, a no-listen HTTP registration bridge, exact read-only git-config
subprocess bridge and local idempotent channel. It does not mount the shipped
full session controller or credential/account/provider-native/poller plugins.
The transport permits only the authored route/read/sum/report sequence;
unsupported fixture tools fail. The result must contain one arithmetic tool,
one successful report, a completed Ticket and at most 16 admitted scripted requests.
A seventeenth request is refused before scripted output; the first refused request
is retained, and any refusal prevents qualification even if a Ticket completed.
These request counts are not model responses or provider token counts.

The script performs best-effort Runtime/agent/root disposal and records any
failure. Container destruction belongs to the outer runner and is not attested
by the inner script. A stored ready report is distinct from a final channel
receipt: final-report delivery and joined crash/restart remain unqualified.

## Selected output and failure preservation

Use exactly these seven relative artifact paths in the task manifest:

```json
[
  ".lupine-coding-evidence/dsh-qualification.json",
  ".lupine-coding-evidence/dsh-package-lock.json",
  ".lupine-coding-evidence/dsh-installed-identities.json",
  ".lupine-coding-evidence/dsh-build-identity.json",
  ".lupine-coding-evidence/dsh-pinned-snapshot.json",
  ".lupine-coding-evidence/dsh-source-lock.json",
  ".lupine-coding-evidence/joined-runtime-result.json"
]
```

Each is at most 2 MiB; the recipe reserves space within 8 MiB total, below the
runner's 16-file allowance. Command text is the short invocation above, below
16 KiB. Paths must not already exist: no evidence is overwritten. Raw Session
histories, SQLite databases, dependency trees and caches remain in owned
disposable scratch, outside the explicit export list.

Failure returns nonzero and preserves command status, signal, bounded output
excerpts and hashes for both stdout and stderr, including successful commands.
Timeout, spawn or buffer errors retain captured bytes with incomplete-capture
status rather than asserting complete output. A requested artifact whose stage did not run contains a
typed `lupine.qualification-artifact-absent.v1` record with `produced=false`
and null measurement. Such a record is neither a package lock nor a successful
runtime result. Timeouts and incomplete output cannot be promoted into success.
The coding ledger still requires archived/read-back evidence and outer-container
cleanup, then a separate acceptance decision. No Library publication follows.
