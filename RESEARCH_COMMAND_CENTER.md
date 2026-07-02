# Lupine Science Research Command Center

Last updated: 2026-07-02

## North Star

Build the makeability layer for AI-driven materials discovery: trustworthy predictions, machine-checkable certificates, and a public record that labs, model builders, and formalizers can collaborate on.

## Team (Hermes-driven)

| Agent | Profile | Model | Role |
|---|---|---|---|
| **Coordinator** | `coordinator` | `kimi-k2.7-code` | Orchestrates research, tracks progress, dispatches work. Primary contact. |
| **Researcher** | `researcher` | `kimi-k2.7-code` | Executes science work: cleanup, triage, Lean formalization, A6 bridge, experiments. |
| **Media Director** | skill | `kimi-k2.7-code` / MiniMax | Produces launch films, images, articles, audio, pitch visuals, content design system, creative exploration loops. |

**How to reach us:** `https://aledev.taild6f8cb.ts.net/` — use the profile switcher to pick `coordinator` (default) or `researcher`.

## Active Initiatives

- **Brand / pitch deliverables** — Production assets and pitch deck from the winning still are shipped.
  - Status: 🟢 shipped
  - Deliverables: `media/projects/brand-exploration/renders/deliverables/` (OG card, site hero, one-pager cover, deck backgrounds), `renders/deliverables/slides/` (9-slide narrative in 16:9 and 4:3).
  - Deployed: `public/og-lupine-science.jpg`, `public/ribbon-still.jpg`, `public/one-pager-assets/cover-shape-of-wrongness.jpg`.
  - Next step: Generate social cards / X thread for the proof-pack and pitch deck.
  - Owner: media director

- **Public proof-pack: environment-error-field paper** — Web-native proof-pack published on `lupine.science`.
  - Status: 🟢 published
  - Article: `/articles/a-smooth-environment-resolved-error-field/`
  - Source: `articles/a-smooth-environment-resolved-error-field.md`
  - Hero: `v7/error-vector-alignment_wide_v7.jpg`
  - Figures: Fig 1 (error landscape), Fig 4 (field + blind test), Fig 5 (run-time correction).
  - Next step: Drive traffic; consider a companion social thread.
  - Owner: researcher + media director

- **A6 bridge protocol** — Full 5,000-permutation / 2,000-bootstrap pilot completed with a 1,000-replicate geometry-preserving (coupling-aware) null. Results committed.
  - Status: 🟢 pilot complete
  - Report: `lupine-rhizo/data/a6_bridge/report_pilot_mptrj_v2_5000.md`
  - Key finding: Force-field magnitude correlation (`mag_corr`) survives the stratified null (Fisher χ² = 51.10, df = 6) but is not significant against the geometry-preserving null, suggesting the shared pattern may be partly mechanical/elastic on this tiny 5-structure pilot. `atom_cos` and `field_cos` survive in some pairs even under rotation.
  - Next step: Scale to multi-config trajectories (MatPES/MPtrj/OMat24) using the newly merged y-matrix / envfield corpus.
  - Owner: researcher

- **Content design system / brand book** — Templates and components for every long-form surface shipped.
  - Status: 🟢 shipped
  - Deliverables: `lupine-science/docs/content-design-system.md`, `articles/_templates/*.md`, extended `public/articles/styles.css`, `public/articles/components.html`, builder support for format classes.
  - Next step: Continuously apply to new articles and proof packs.
  - Owner: researcher

- **Day-in-the-life social content** — 5-image carousel + X thread committed.
  - Status: 🟢 ready to share
  - Next step: Post to X from `media/projects/day-in-the-life/renders/x_thread.md`.
  - Owner: media director

- **Lupine Science public front door** — Live at [lupine.science](https://lupine.science).
  - Status: 🟢 live
  - Next step: Deploy latest commits (already committed; ensure published).
  - Owner: media director

- **LUPI launch** — 30-second film + "Why LUPI?" article shipped.
  - Status: 🟢 shipped
  - Next step: Drive traffic and gather feedback.
  - Owner: media director

- **Remote access & operations** — Tailscale SSH + Hermes dashboard verified on iOS/Mac/Windows.
  - Status: 🟢 verified
  - Owner: infrastructure

- **Hermes v0.17.0** — Operational; dashboard build fixed.
  - Status: 🟢 operational
  - Owner: infrastructure

## Done Recently

- Merged latest remote `lupine-science` work (new article "The Order Is Right, the Size Is Wrong") and resolved the articles index conflict.
- Merged latest remote `lupine-rhizo` work: y-matrix / environment-error-field manuscript, figures, evidence corpus, LAMMPS-to-Lean bridge, offline HPC lane, library catalog updates, Lean evidence module, and CI fixes.
- Published the environment-error-field paper as a public proof-pack on `lupine.science`.
- Built a 9-slide pitch deck in 16:9 and 4:3 from the winning brand still, informed by the envfield results.
- Produced production brand deliverables: OG card, site hero, one-pager cover, deck backgrounds.
- Ran v6/v7 brand-exploration matrices, selected `v7/error-vector-alignment_wide_v7.jpg` as the upstream-cascade replacement.
- Updated `build-articles.py` to use per-article hero images for OG/Twitter cards.
- Updated the public site OG/Twitter meta tags and refreshed the public-ledger fallback entries.

## Blockers

- A6 full-scale run still needs MatPES/MPtrj/OMat24 multi-config trajectory manifests beyond the pilot/synthetic subsets.
- Hermes dashboard is tailnet-gated only; acceptable until shared.
- Public ledger refreshes by TTL; no active purge permission.

## Upcoming Bets

- Scale A6 bridge to the merged y-matrix / envfield multi-config corpus.
- Post social thread for the new proof-pack and pitch deck.
- Materialize the MatPES/MPtrj/OMat24 manifest and re-run A6 at scale.
- Add LUPI landing page.
