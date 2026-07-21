# Lupine Science Research Command Center

Last updated: 2026-07-21 (focus reset — owner directive: "focus on focusing on our research direction")

## North Star

Build the makeability layer for AI-driven materials discovery: trustworthy predictions, machine-checkable certificates, and a public record that labs, model builders, and formalizers can collaborate on.

## The Research Direction (focused, 2026-07-21)

**Thesis:** universal MLIPs drift farthest exactly where the science is hardest. Lupine corrects them **at runtime — no retraining, no fine-tuning** — using theorem-gated sparse DFT anchors. The proof vehicle is the Z1 barrier pilot; the amplifier is the theorem commons (shared gates + shared anchors: every team that joins makes every other team faster).

Everything currently running serves this thesis or is explicitly parked below. Nothing else starts until P0 lands.

## Priority Stack

**P0 — Z1 sparse-DFT pilot to verdict (the only thing that matters until done)**
- Critical path: path 16 completes → convergence revalidation (Gamma / h=0.20, adopt-if-≤5 meV, amendment 02 decision) → union-anchor driver over the 23 active paths → chgnet verdict vs the ≤40 meV gate + **measured cost ledger** → then remaining models, one at a time.
- Watchdog: cron `02c262c1` (2-hourly) handles the path-16 → revalidation handoff automatically.
- Frozen: GPAW fd/h=0.18/(2,2,2)/PBE (amendment 01 governs; same-engine gate primary, VASP secondary, T1 wander reported per path).

**P1 — in flight, land and close**
- PR #73: T1 convention-wander gate + revalidation runner (Codex P2s fixed; merge on green).
- PR #72: Z2 spin-capable runner (Codex P1 fixed; hermes reviewer+qa sign-off required, then merge). **Execution of Z2 SOC stays owner-gated.**

**P2 — queued immediately after P0 verdict**
- Aggregate chgnet verdict + measured costs; publish run costs (owner: "publish actual run costs").
- Amendment 02 (convergence loosening) if revalidation passes — propagates to all later models.
- Union-anchor driver economics measured on real energies (commons baseline number).

**Parked (do not touch without owner decision)**
- Deferred big-7 paths (≥159 atoms) — `waiting` on stronger hardware, verdicts PENDING.
- Z2 SOC heavy execution — compute budget decision required.
- Spin-capable runner beyond PR #72; Round-4 elastic recompute (team finishing independently; land its receipts when done).
- Further Savings Stack marketing — the book is live; no new marketing until P0 results exist.

**Not doing (scope guards)**
- No training or fine-tuning models. Runtime correction only (owner directive; cost-slope guard).
- No new experimental domains, no cloud fleet (cancelled 2026-07-20; local box is the compute plan).
- No new panels, campaigns, or sites until P0 lands.

## How we work (operating rules that held up)

- Preregistration before results; amendments are dated documents, never silent changes (see amendment 01).
- Primary records get committed immediately with sha256 sidecars (the 624/132 retraction is why).
- Codex review is read on every PR before merge (4 catches this week, incl. the P1 generic-image breaker).
- Hermes teams own tasks end-to-end (implement → self-verify → reviewer → qa); director reviews independently before landing.
- Deploys are fully automated post-merge (owner directive 2026-07-20, no human gates).
- Honest voice everywhere: proof-first, derived estimates labeled, retractions recorded in the same record that replaces them.

## Team (Hermes-driven)

| Agent | Profile | Role |
|---|---|---|
| **Coordinator** | `coordinator` | Orchestrates research, tracks progress, dispatches work. |
| **Researcher** | `researcher` | Science execution: experiments, formalization, digests, elastic recompute. |
| **Software-engineer** | `software-engineer` | Runners, packaging, CI (Z2 spin runner delivered 2026-07-21). |
| **Reviewer / QA** | `reviewer` / `qa` | Sign-off gates before landing. |
| **Media Director** | skill + MiniMax | Brand assets, films, booklet art. |

Reach us: `https://aledev.taild6f8cb.ts.net/` (profile switcher).

## Live properties

- lupine.science — PR/venture side; The Savings Stack booklet + dataset live (2026-07-21).
- library.lupine.science — full transparent detail; `savings-stack` group (12 entries).

## History

- 2026-07-19: Round-4 campaign complete (both ionics failed confirmatory criterion; theorem consistency green) — see git history for the 2026-07-19 command center.
- 2026-07-20: sparse-DFT premise validated; preregistration frozen; first real result 32.2 meV WIN (mp-760344); cloud fleet cancelled; seven big cells deferred.
- 2026-07-21: path-7 FAIL 118.8 meV → root cause T1 convention wander (139.4 meV on the barrier-defining pair) → amendment 01 (same-engine gate) + T1 wander gate built (first self-contributed commons theorem); Savings Stack book published.
