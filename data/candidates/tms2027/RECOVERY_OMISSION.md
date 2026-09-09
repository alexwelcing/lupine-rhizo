# Recovery omission: 352-row live-ledger Q1 analysis

Decision date: 2026-09-09
Decision: OMIT the unrecovered live-ledger Q1 point estimates, null results, and correction numbers from the TMS proceedings manuscript.

## Required intact recovery set

The working contract requires all of the following before exact Q1 numbers can be used: the 352-row snapshot, analysis scripts, null outputs, frozen seeds, content hashes, and refuter record. A partial or newly reconstructed substitute does not satisfy that provenance contract.

## Recovery attempt

The timeboxed search covered:

1. Current Lupine repositories under `/home/alex/Dev/lupine`, including filename and content searches for `352`, `352-row`, `Q1`, `live-ledger`, `snapshot`, `null`, and `seed`.
2. Local git history and all fetched `lupine-rhizo` refs (`git log --all -S352`, path searches for Q1/ledger/null artifacts), plus GitHub code search in `alexwelcing/lupine-rhizo`.
3. Retained Hermes kanban workspaces under `/home/alex/.hermes/kanban/boards/lupine/workspaces`, including prior `lupine-rhizo` checkouts and archived analysis-null code.
4. The live GLIM Worker read surfaces on 2026-09-09:
   - `GET https://glim-think-v1.aw-ab5.workers.dev/health` reported 1,877 current D1 records, not a provenance-locked 352-row snapshot.
   - `GET /research/causal-geometry` exposed only aggregate status/counts.
   - `GET /feed` exposed aggregate metrics and ten recent activity rows, not a complete ledger export or Q1 artifact chain.
   - The checked-in OpenAPI surface has no read-only endpoint that exports the historical records table or a named 352-row snapshot.
5. A direct read-only Wrangler D1 query was attempted only as a final recovery check. It failed closed before querying because this non-interactive workspace has no `CLOUDFLARE_API_TOKEN`; no D1 rows were recovered by that route.

## What was found

Current repositories retain narrative and aggregate claims derived from later/current ledger states, including a live 1,877-record ledger and current aggregate metrics. They do not provide the exact, hash-bound 352-row Q1 package required by the manuscript contract. The current 1,877-row state must not be back-selected or treated as the missing historical snapshot.

## Fail-closed disposition

The intact recovery set was not found within the recovery timebox. Therefore:

- omit every exact statistic attributed specifically to the 352-row live-ledger Q1 analysis;
- do not quote its PR, matched-null, correction, confidence, or significance values;
- do not regenerate a plausible 352-row subset from the current 1,877-row ledger;
- retain only the qualitative provenance statement that the live-ledger result is promising but not reproducible from the recovered record.

This omission is the required deliverable under the working contract, not evidence that the historical result was false.
