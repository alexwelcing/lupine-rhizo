# Honest Errors Integration Evaluation

## Repo Roles and Current State

| Repo | Role | Current Formalization | Gaps for Honest Errors |
|------|------|----------------------|------------------------|
| `lupine` | Main research repo | `lean-spec/OpenDistillationFactory` with correction schemes, UniversalCorrection registry, theory modules | Missing Honest Errors contract layer, discovery chains, error taxonomy, master matrix |
| `lupine-rhizo` | Empirical-formal bridge | EvidenceBundle, ClaimContract, assumptions registry, UniversalCorrection registry, D1, CI, expanded OpenDistillationFactory (climate series) | Missing Honest Errors contract layer, discovery chains, barrier/Arrhenius domain evidence |
| `lupine-ledger` | Content publishing | Articles, docs, GLOSSARY | No formalization, no Honest Errors content |
| `lupine-science` | Public website | Articles, videos, schemas | No formalization, no Honest Errors presentation |
| `lupi-viewer` | Molecule viewer | UI/3D visualization | No Honest Errors visualization |

## Integration Options by Repo

### Option A: lupine-rhizo as primary integration target

**What to add:**
- `OpenDistillationFactory/HonestErrors/` — Taxonomy, Evidence, Acceptance, ErrorBudget, StageGates, Endpoint
- `OpenDistillationFactory/DiscoveryChains/` — 11 chain contracts with acceptance tests and gates
- `OpenDistillationFactory/ErrorLandscape/` — nine emblems + master matrix
- `registry/claims/` — barrier-accuracy, magnetocrystalline, adsorption-energy ClaimContracts
- `evidence/v1/` — barrier error EvidenceBundles from the report

**Why:** rhizo already has the empirical-formal bridge infrastructure (EvidenceBundle, ClaimContract, CI, D1). The Honest Errors layer is a scientific-contract layer that fits naturally.

**Risk:** rhizo becomes very large. The ActivatedBarriers first-principles math might be better in lupine.

### Option B: lupine as primary integration target

**What to add:**
- `OpenDistillationFactory/ActivatedBarriers/` — Graph/VacancyLift, Response/Quadratic, Response/Barrier, Envelope/TwoChannel, Singular/SaddleNode, Examples/LineVacancy
- `OpenDistillationFactory/HonestErrors/` — contract layer (same as Option A)
- `OpenDistillationFactory/DiscoveryChains/` — chain contracts

**Why:** lupine has the base OpenDistillationFactory with correction schemes. The ActivatedBarriers math is first-principles and belongs with the theory modules.

**Risk:** lupine doesn't have the empirical-formal bridge (EvidenceBundle, ClaimContract, registry). Would need to port that infrastructure too.

### Option C: Keep ActivatedBarriersFormal separate, link via lakefile

**What to add:**
- Add `ActivatedBarriersFormal` as a lakefile dependency in both lupine and lupine-rhizo
- Import only the needed modules in each repo

**Why:** Clean separation of concerns. The formalization companion stays versioned independently.

**Risk:** Dependency management complexity. Two repos need to stay in sync with the companion.

## Recommended Path

**Phase 1 (immediate):** lupine-rhizo gets the Honest Errors contract layer + discovery chains. This is what `t_5111bc23`, `t_0d008511`, `t_d9e7523a` are doing. The empirical-formal bridge extends to the barrier/Arrhenius domain via new ClaimContracts and EvidenceBundles.

**Phase 2 (short-term):** lupine gets the ActivatedBarriers first-principles modules (`Graph/VacancyLift`, `Response/Quadratic`, `Response/Barrier`, `Envelope/TwoChannel`, `Singular/SaddleNode`, `Examples/LineVacancy`). These connect to the existing correction schemes in `OpenDistillationFactory/Materials/Distillation/`.

**Phase 3 (medium-term):** lupine-ledger publishes the report as structured articles (23 chapters), plus `CLAIM_LEDGER.md`, `INTEGRATION_FINDINGS.md`, `TRUST_BOUNDARY.md` as formalization docs.

**Phase 4 (long-term):** lupine-science gets public presentation (articles, interactive error taxonomy, discovery chain cards). lupi-viewer gets nine material class visualizations.

## Concrete Next Steps

1. **Land current Phase 1 tasks** — `t_5111bc23` (Honest Errors integration), `t_0d008511` (discovery chains), `t_d9e7523a` (error emblems). Verify lake build passes in lupine-rhizo.

2. **Create lupine integration task** — Add ActivatedBarriers first-principles modules to lupine's OpenDistillationFactory. Use the same zero-sorry, zero-new-axiom policy.

3. **Extend empirical-formal bridge** — Add barrier-accuracy ClaimContracts to lupine-rhizo's `registry/claims/` with EvidenceBundles from the report's 574 DFT-NEB paths.

4. **Content publishing** — Break the 215-page report into lupine-ledger articles (one per chapter + exhibits).

5. **Public presentation** — Create lupine-science articles for the error taxonomy, discovery chains, and correction stack.

## Decision Point

Do you want me to:
- **A)** Start Phase 2 (lupine integration) in parallel while Phase 1 tasks run, or
- **B)** Wait for Phase 1 to complete, then do a unified integration with a single PR?

I recommend **A** — parallel work is faster and the two phases touch different repos with minimal overlap.
