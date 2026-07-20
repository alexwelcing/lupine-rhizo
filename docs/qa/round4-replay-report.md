# Round-4 QA Replay Report — D1 → gate-manifest → Lean → licenses

**Date:** 2026-07-20 · **Executor:** director (Kimi, M3 Max) · **Mode:** zero manual evidence assembly — every leg is tool-executed and hash-recorded.
**Durability note:** committed to the repo at creation time (the Round-3 replay's evidence died in a scratch workspace; not twice).

## Verdict: PASS — the chain holds end-to-end with real Round-4 verdicts inside

| Leg | Evidence | Result |
|---|---|---|
| D1 contract schema | `t_30e4047e` (completed): 12 fresh migrations + 24-command reconciliation reapplication on real Wrangler 4.103.0/D1; canonical bytes identical before/after, FK check empty, supersession survived | **PASS** (by reference) |
| Runtime gate manifest | `tools/atlas_theorem_sync.py --compile-gates` → 3 gates: `correction_gate → deny (contradicting_evidence)` ×2, `apply_frozen_rule → allow (scope_matched_same_class_a0)` | **PASS** |
| Lean formal layer | `lake build` (3760 jobs) with `z1_gate_refuted`, `z3_gate_refuted`, `AcceptanceGateRefuted`, `z2AbstentionRecord` (PR #49) | **PASS** |
| Publication linter | `tools/check_publication_claims.py` → "publication ClaimContract check passed" | **PASS** |

## Hash chain (this replay's fingerprints)

| Artifact | SHA-256 (first 16) |
|---|---|
| `registry/snapshots/current.lock.json` | `d07eff3a713e5616` |
| runtime gate manifest (round4) | `c55d8acbd34d7ab1` |
| `config/lean_build_evidence.json` | `e85b31a0480c7e7a` |

## What the chain now certifies

- **Z1** — `discovery.z1.barrier-accuracy.v1`: (withdrawn, refuted). Four negative EvidenceBundles; Lean `z1_gate_refuted` (best case 135.0 meV vs the 40 meV ceiling).
- **Z3** — `discovery.z3.adsorption-accuracy.v1`: (withdrawn, refuted). Four negative EvidenceBundles; Lean `z3_gate_refuted` (best corrected case 2.2719 eV vs the 0.1 eV ceiling).
- **Z2** — abstained by design; no gate theorem exists, matching zero cloud executions.
- **Round-3 correction surface** — B0 gates deny (contradicting evidence), a0 allows under matched scope: unchanged and consistent with the Round-3 record.

## Recorded limitations / follow-ups

1. **D1 leg by reference, not fresh execution**: the local Cloudflare MCP token (`~/.cloudflare/api-token`) lacks D1 resource permissions (API code 10000 on `d1/database/glim-ledger`). The D1 contract leg is therefore cited from `t_30e4047e`'s completed real-Wrangler validation rather than re-executed. Follow-up: widen the MCP token with D1 read scope (or use the CI-held deploy token in a dispatched replay workflow) so the next replay runs all four legs fresh.
2. **Lean evidence pin**: `config/atlas_theorem_registry.v1.json` pins revision `bad604c…` (pre-HonestErrors module inventory); a full re-pin belongs to the documented post-merge one-file re-pin flow (Codex round-2 finding, partially repaired in PR #38).
3. **Z2 supersession path**: `t_052adac7` (spin-capable runner + honest panel + ClaimContract) is the only route that may replace the abstention record with measurement rows.

## Replay procedure (for the next executor)

```bash
# 1. Runtime gate manifest from the locked registry
python tools/atlas_theorem_sync.py --compile-gates --out-gates /tmp/runtime-gate-manifest.round4.json
# 2. Lean layer
cd lean-spec && lake build   # expect 3760+ jobs, zero errors
# 3. Publication linter
python tools/check_publication_claims.py
# 4. Fingerprints
sha256sum registry/snapshots/current.lock.json /tmp/runtime-gate-manifest.round4.json config/lean_build_evidence.json
```
