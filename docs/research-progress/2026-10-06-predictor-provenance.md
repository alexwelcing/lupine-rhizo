# An offline guard for predictor identity and cached evidence

Date: 2026-10-06. **Evidence kind: workflow repair.** This change addresses a
specific prerequisite for a new force-ranking study. It produces no new
scientific performance result.

## Question

Can a prospective run prove which loaded predictor produced each cached force
prediction, reject an incompatible cache, and preserve the original producer
when later runs reuse those predictions?

The earlier [source recovery](2026-10-06-pinned-source-overlap.md) recovered
execution-image identities but not the exact historical weights or cache
producers. An image label can be consistent with different weights or effective
settings. Newly pinned predictors therefore require their own prospective
identity; this repair cannot retroactively identify the historical roster.

## What changed

- An opt-in strict path requires an explicit expected model identity, actual
  loaded-state digest and observed inference-configuration digest. The check
  happens before cache access or prediction, after clearing stale in-memory
  calculator results. Verified identity is recorded in execution provenance;
  a legacy display label is not an identity pin.
- The first adapter is limited to CHGNet package 0.4.2, CPU, the `forces` baseline
  row, legacy graph conversion and Distill off. Unsupported adapters/settings
  fail closed; the default legacy path explicitly reports unknown provenance.
- The versioned state digest includes parameter names, shapes, dtypes, tensor
  bytes and registered buffers, including nonpersistent buffers. A scalar and
  a length-one tensor have different identities. This is a loaded-state hash,
  not a file hash or signature.
- Strict cache context binds the predictor identity. Reused entries retain
  their original producer and timestamp while new entries receive their own.
  Incompatible, malformed or incomplete provenance fails without replacing the
  existing cache. Write-only cannot downgrade an existing strict cache.
- Batch defaults/cells cannot weaken an inherited strict setting or replace its
  pin. Unsupported strict work fails before batch model loading. Incomplete,
  failed or nonfinite strict force outputs cannot receive a completed result.
- Generic and Z2 image recipes include the helper; the unified image already
  includes its directory. Existing lightweight CI now exercises the new guard
  alongside runner and packaging regressions. No runner image was built or
  deployed during this visit.

The supported upstream interface was checked against CHGNet v0.4.2's
[model](https://github.com/CederGroupHub/chgnet/blob/v0.4.2/chgnet/model/model.py),
[calculator](https://github.com/CederGroupHub/chgnet/blob/v0.4.2/chgnet/model/dynamics.py)
and [graph converter](https://github.com/CederGroupHub/chgnet/blob/v0.4.2/chgnet/graph/converter.py).
The implementation hashes observed effective settings as well as loaded state;
constructor labels alone are insufficient.

## Verification and limits

Final local check: **133 runner/provenance/packaging tests passed**. The public
activity contract and import checks also passed, and Library built its 94 reviewed
articles. These are software checks, not scientific experiment results.

The software checks use fake calculators/tensors and tiny offline fixtures.
They test changed weights/settings, unknown or mismatched identities, cache
preservation, original producers on partial reuse, and batch downgrade attempts.
Independent adversarial review also identified scalar-shape identity collision,
unsupported batch preload and completion-state risks; those paths have explicit
regressions. The fixture suite does not load vendor models or prove compatibility
with a real CHGNet installation. That separate acceptance check is still needed.

This is a scoped adapter, not complete provenance for arbitrary PyTorch objects,
training-lineage proof or cross-machine bitwise reproducibility. Compiled fast
graph conversion and other model families are unsupported. Concurrent writers
to a checkpoint are unsupported and require overlap prevention. Legacy evidence
remains unknown; stopped research invocations remain stopped.

Candidate outcome columns were not opened, no panel was sampled, and no real
model loaded or predicted. The prior inventory of 9,304 configurations in 8,844
linked components is not an approved independent holdout. Historical A6 remains
INCONCLUSIVE.

## Next discriminating step

The [distinct proposed study](2026-10-06-prospective-ranking-protocol.md) specifies
128 eligible groups, one configuration per group, three pinned model families,
a fixed selection seed, fixed ranking scores and explicit descriptive decisions.
It is **PROPOSED / NOT_STARTED**. All three strict adapters, reference compatibility,
model-training independence and existing resource bounds are prerequisites.

Next produce a bounded four-source roster/reference readiness matrix: one
checkpoint/provenance package per model family plus one source reference/split
packet. Either establish eligibility with concrete evidence or stop this
validation claim and identify the incompatibility. Do not spend another visit
rechecking historical image labels or treating a dataset named test as proof of
independence.

## Public representation

Library records this as **Workflow repair**, with its actual evidence dates,
limitations and next test. The producer and consumer accept this explicit kind
without manufactured research-cycle receipts. Raw private archives, identities,
model packets and controller data are not published.
