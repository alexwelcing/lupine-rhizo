# Prepared DSH scripted qualification for the coding runner

This recipe has been prepared and syntax-checked locally. It has **not** been
installed or executed. Keep the first core coding-runner smoke and its source
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
`timeoutSeconds=900` and an exact source-bundle digest. This first-resolution
recipe requires `enableInternet=true` for public GitHub/npm acquisition.
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
fetch at 120 seconds, npm lock resolution at 180, installation at 300, bundling
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

Exact top-level packages are the documented official
`@deepseek-ai/dsh@0.2.1-rc.3`, `esbuild@0.28.2`, `proper-lockfile@4.1.2` and
`zod@4.4.3`. The recipe first produces a bounded package lock and validates the
top-level pins, npm-registry tarball locations and SHA-512 integrity entries
before `npm ci --ignore-scripts`. `--legacy-peer-deps` is explicit. Dependencies
bundled inside another integrity-bound tarball inherit that archive boundary.
The first resolution is **not** a pre-existing frozen transitive graph: its
complete captured lock is the reproducibility input for a later repeat.

The installed Harness package manifest and six installed service files must
match retained hashes. Bundling deliberately maps all prototype
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
