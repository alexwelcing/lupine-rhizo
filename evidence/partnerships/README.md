# Lupine Science Partner & Client Prospect Research

Research corpus for institutional evaluation and outreach, assembled 2026-08-01/02 by
the hermes research team. **Repository-only distribution** — not published on
lupine.science.

## Verification status (as of 2026-08-02)

- **136 organizations** across 11 categories (battery/cell makers 20, materials/chemicals
  18, university groups 18, climate-tech ventures 16, national labs 14, automotive 12,
  industrial gas/energy 10, compute/cloud 8, semiconductor/hardware 8, defense/aerospace 6,
  pharma/catalysis 6).
- Tier-1/2 records (93): **33 official-source-validated**, 60 explicitly
  `needs-verification`. Fail-closed standard: a record is promoted only with claim-level
  official-source proof (named program/facility, named decision-maker or officially named
  team, dated 2024–2026 event, prospect-specific Lupine mapping, claim URLs). Nothing is
  promoted from search snippets alone.
- Mechanical validator: `validate_partnerships.py` — 1,973 checks, 0 errors
  (`python evidence/partnerships/validate_partnerships.py`; see `validation-report.json`).
- Independent review: `independent-review.json` (ACCEPT on the fail-closed basis).
- Full per-URL probe: `live-source-audit.json` (254 claim URLs re-opened).

## Economics guardrail (binding for all outreach text)

Use only these figures: **72.4% fewer DFT evaluations** (558 naive → 154 union anchors,
29 paths) and **$14.65 per 129 anchors** (Z1 measured run). Do not revive the retracted
"4.65 cloud-equivalent" figure.

## Files

- `partner-prospects.json` — canonical machine-readable list (136 records with
  `claim_validation` status per tier-1/2 record).
- `partner-prospects.md` — human-readable rendering, top-10 first contacts.
- `tier-1-outreach-one-pager.md`, `tier-2-outreach-one-pager.md` — outreach scripts with
  per-prospect Lupine proof links.
- `source-verification.json` — reachability summary for all 136 official sources.
- `live-source-audit.json` — per-URL probe results.
- `validate_partnerships.py` — mechanical validator (run after any edit).
- `validation-report.json`, `independent-review.json` — audit receipts.

## Working this list further

Continuation work (see board card): complete claim-level verification for the 60
`needs-verification` tier-1/2 records using the same standard; then outreach sequencing
for the 33 validated records. Any edit must keep the 136 IDs stable, keep the economics
guardrail, and re-run `validate_partnerships.py`.
