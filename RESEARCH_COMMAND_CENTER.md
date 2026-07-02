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

- **Creative direction / brand exploration** — Five MiniMax matrices generated; winners emerging.
  - Status: 🟢 winners emerging
  - v1–v5 matrices: 60 images total in `media/projects/brand-exploration/assets/images/`.
  - Combined gallery: `media/projects/brand-exploration/renders/gallery_all.html`
  - Synthesis: `media/projects/brand-exploration/renders/synthesis.md`
  - Winners:
    - Cover/hero: `v3/shape-of-wrongness_wide.jpg`
    - Bits→atoms: `v4/bits-to-atoms_wide.jpg` (soft) or `v5/bits-to-atoms_wide.jpg` (bold)
    - Upstream cascade: unresolved after five attempts
  - Next step: Replace upstream-cascade with a new motif, or move to deliverables (OG card, one-pager hero, deck slides).
  - Owner: media director

- **Content design system / brand book** — Templates and components for every long-form surface shipped.
  - Status: 🟢 shipped
  - Deliverables: `lupine-science/docs/content-design-system.md`, `articles/_templates/*.md`, extended `public/articles/styles.css`, `public/articles/components.html`, builder support for format classes.
  - Next step: Stress-test by converting the A6 pilot report or a proof pack to the new format.
  - Owner: researcher

- **Brand & pitch vibe** — Pitch-ready brand system locked and shipped.
  - Status: 🟢 package shipped
  - Deliverables: `lupine-science/docs/brand-guidelines.md`, `public/one-pager.html`, site hero alignment, canonical brand config update.
  - Next step: Apply the winning brand-exploration stills to the 1200×630 OG/social card and deck backgrounds.
  - Owner: media director

- **A6 bridge pilot** — Full 5,000-permutation / 2,000-bootstrap pilot completed with a 1,000-replicate geometry-preserving (coupling-aware) null. Results committed.
  - Status: 🟢 pilot complete
  - Report: `lupine-rhizo/data/a6_bridge/report_pilot_mptrj_v2_5000.md`
  - Key finding: Force-field magnitude correlation (`mag_corr`) survives the stratified null (Fisher χ² = 51.10, df = 6) but is not significant against the geometry-preserving null, suggesting the shared pattern may be partly mechanical/elastic on this tiny 5-structure pilot. `atom_cos` and `field_cos` survive in some pairs even under rotation.
  - Next step: Scale to multi-config trajectories (MatPES/MPtrj/OMat24) so the energy null is non-degenerate and the force-field test has statistical room to separate shared core from coupling.
  - Owner: researcher

- **Day-in-the-life social content** — 5-image carousel + X thread committed.
  - Status: 🟢 ready to share
  - Next step: Post to X from `media/projects/day-in-the-life/renders/x_thread.md`.
  - Owner: media director

- **Lupine Science public front door** — Live at [lupine.science](https://lupine.science).
  - Status: 🟢 live
  - Next step: Deploy updated hero copy, one-pager, content system, and refreshed OG card once creative winners are chosen.
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

- Fixed the A6 pilot `build_output()` signature mismatch and committed the fix.
- Fixed the coupling-aware null so it combines results without requiring a bootstrap replicate set.
- Ran and committed the full 5,000-permutation / 2,000-bootstrap / 1,000-coupling-null A6 pilot.
- Locked pitch-ready brand guidelines, built a print-ready one-pager, and aligned the public site hero with the pitch narrative.
- Updated the canonical `brand.config.json` and brand narrative to the trust-layer one-liner.
- Built a content design system with templates, shared components, and builder support for articles, white papers, research guides, tutorials, proof packs, and reports.
- Built a brand-exploration make/evaluate/mutate loop: gallery, procedural playground, prompt mutator, and MiniMax generation matrix.
- Renewed MiniMax plan and generated v1–v5 12-image matrices (60 images), tightening the style suffix each round to land on-brand winners.

## Blockers

- A6 full-scale run still needs MatPES/MPtrj/OMat24 multi-config trajectory manifests beyond the pilot/synthetic subsets.
- Hermes dashboard is tailnet-gated only; acceptable until shared.
- Public ledger refreshes by TTL; no active purge permission.

## Upcoming Bets

- Decide: iterate on upstream-cascade replacement or move to deliverables.
- Generate the new OG/social card and deck slides from the winning stills.
- Stress-test the content design system with a real report or proof pack.
- Post the day-in-the-life thread to X.
- Materialize the MatPES/MPtrj/OMat24 manifest and re-run A6 at scale.
- Publish "From fantasy frameworks to makeable materials" article.
- Add LUPI landing page.
