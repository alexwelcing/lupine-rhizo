# Round-4 preregistration amendment — post-lock repairs (2026-07-19)

> **Status:** AMENDMENT to `2026-07-14-round4-preregistration.md`, dated
> 2026-07-19, after Round-4 measurement artifacts existed. The frozen
> registration is not rewritten and cannot be rescued retroactively; this
> amendment records three registration defects found in pre-review, the
> concrete repair applied to each, and the exact scope of every resulting
> change to the analysis outputs. Raw measurement artifacts
> (`data/candidates/round4/cloud_artifacts/**`) are hash-locked evidence and
> are byte-identical before and after this amendment.

## 1. Violation: analysis tool implemented after the candidate lock

Preregistration §5 required the v2 analysis implementation to be "committed
and tested BEFORE the evaluation set is locked". The evaluation set was
locked 2026-07-17 (`data/candidates/round4_targets.lock.json`, SHA-256
`b7562637c860b15b92f64659f0b063bc6d2b6c0c12899e21f370359cccb914f1`). The
analysis tool that executed the campaign, `tools/round4_cloud_campaign.py`,
was implemented and first committed on 2026-07-19, after the lock and after
the measurements. This is a preregistration violation; the Round-4 analysis
was not, in fact, frozen before evaluation data existed.

**Mitigation (fix-forward, not absolution):** the tool is now committed on
the campaign branch with the repository test suite green, so the analysis is
at least reproducible and reviewable from this point. The measurement
results it produced are immutable: all 64 per-cell result artifacts are
SHA-256-addressed in `data/candidates/round4/report.json` and re-verify
byte-for-byte, and both measurement rows form an intact hash chain over the
report and campaign-manifest hashes. The tool therefore cannot have been
tuned against undisclosed intermediate states without detection from here
forward, but the pre-lock freeze §5 promised did not happen and is recorded
as void.

## 2. Repair: execution binding named the wrong jobs; per-cell image digest null

The campaign's endpoint receipt embedded the frozen endpoint lock
(`gcp/mlip-cell-runner/round4_endpoints.lock.json`), which names the shared
pre-round jobs (`mlip-cell-chgnet`, `mlip-cell-mace-mp-small`,
`mlip-cell-mace-mp-medium`, `mlip-cell-mace-mpa-0-medium`). The Round-4
measurements did not run on those jobs. Per the captured execution receipt
(`data/candidates/round4/execution-receipt.json`, run
`correction-round4-20260719`), they ran on isolated Round-4 jobs:

- `mlip-cell-chgnet-round4` (execution `mlip-cell-chgnet-round4-8bbp8`),
  image `mlip-cell-chgnet@sha256:6a443b3817f9c2e580e1eeefddc1a032efb00fd785b377fa526039b3f4130617`
- `mlip-cell-mace-round4-mp-small` (execution `mlip-cell-mace-round4-mp-small-k94mk`),
  image `mlip-cell-mace-round4@sha256:37b83d134c8e20e8f26603b50a4e8b0b4359632c2e2b2b2bc1dc553716315b53`
- `mlip-cell-mace-round4-mp-medium` (execution `mlip-cell-mace-round4-mp-medium-mmcjq`),
  same MACE image digest
- `mlip-cell-mace-round4-mpa-0-medium` (execution `mlip-cell-mace-round4-mpa-0-medium-6979j`),
  same MACE image digest

Both digests equal the immutable image digests recorded in the frozen
endpoint lock, so the measured binaries are exactly the locked ones; only
the job names in the receipt were wrong. Separately, every hash-locked cell
artifact carries `execution.runner_image_digest: null` — the runner did not
record its own digest at capture time. Because those artifacts are
hash-locked, the null cannot be repaired in place.

**Repair applied:** `report.json` now carries a `measurement_binding`
section binding each registered model to its isolated job, execution name,
and measurement-time image digest (each flagged against the endpoint-lock
digest), alongside the untouched endpoint lock and execution receipt. The
live Cloud Run jobs have since been redeployed with `z1-barrier-20260719`
tagged images for the Z1 campaign (verified read-only via
`gcloud run jobs describe`, 2026-07-19); current live state is NOT the
measurement binding and is recorded nowhere as such. Both locked digests
remain present in Artifact Registry (verified 2026-07-19), so replay against
the exact measured binaries stays possible.

## 3. Correction: B0 removed from the confirmatory denominator

Preregistration §5 states "B0 concordance remains descriptive-only (errata
finding 4)". The executed analysis nonetheless computed group verdicts over
all five properties, counting B0 in the 2/3 confirmatory denominator for
both groups. **Repair applied:** `tools/round4_cloud_campaign.py` now tags
every group/property summary with a disposition and computes group verdicts
over confirmatory properties only. B0 is still measured, corrected, and
reported — descriptively, with its scope note attached.

## 4. Rescope: perovskite elastic constants are exploratory-only

**Rationale.** The elastic instrument measures clamped-ion finite
differences (±0.5% strain) on cells isotropically scaled to the nearest
sealed 2.5%-spaced volume, then compares against relaxed or experimental
references. For the perovskite group this is not a defensible confirmatory
comparison: when a model's equilibrium a0 sits between probe volumes the
constants are evaluated on a strained cell — up to 1.25% from the model's
own equilibrium — and no internal relaxation is applied, while the
references are relaxed (JARVIS OptB88-vdW) or experimental. The resulting
error is dominated by the instrument's volume mismatch and clamped-ion
approximation rather than by the correction law under test, so a win or loss
on these cells would not evidence the registered hypothesis either way.

**Repair applied:** perovskite C11/C12/C44 summaries are marked
`exploratory` in the analysis and excluded from confirmatory statistics;
their numbers remain in the report verbatim with the scope note attached.
Rocksalt elastic constants are unaffected and remain confirmatory.
**Follow-up:** task `round4-elastic-relaxed-recompute` — re-evaluate
perovskite elastic constants at each model's own relaxed equilibrium volume
with internal relaxation enabled before any confirmatory use of these
properties (tracked in `RESEARCH_COMMAND_CENTER.md`).

## 5. Effect on the registered outcomes

Under the corrected accounting the confirmatory sets are
ionics-rocksalt {a0, C11, C12, C44} (n=4) and perovskites {a0} (n=1). No
property's win/loss outcome changed, and no group verdict changed:
ionics-rocksalt FAIL (0/4), perovskites FAIL (0/1), theorem consistency
still zero licensed oracle-in-hull worsened cells. The registered conclusion
of Round 4 — the correction scope remains "same-class lattice constants
only" and cap tuning is frozen absent a new theorem — is unchanged.
`report.json`, `ROUND4_REPORT.md`, and the two hash-chained measurement rows
were regenerated from the untouched hash-locked cell artifacts; the row
chain, manifest hash, and all 64 artifact hashes re-verify under the
regenerated outputs.

This amendment changes no registered criterion, threshold, cap, or
candidate, and authorizes no re-measurement.
