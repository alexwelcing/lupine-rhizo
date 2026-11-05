# Hyper-Ribbon Transfers Classical → MLIP

**Status: Open — under Born-screened re-audit**

## Current status after Born screening

The pre-screening “14/15 elements stay on the ribbon” count is no longer citable
as a settled MLIP-transfer result. Born stability screening (see
`replication/error-geometry/`, prereg commits `dffbe595`/`ebf39e33`) excludes 7
of 45 foundation-model elastic tensors — including **CHGNet-Fe** (C11 < |C12|),
MACE-V, and Orb-v3 Al/Nb/Pb/Pt — so any per-element participation-ratio or
on-ribbon count computed from the unscreened trio inputs must be recomputed.

What survives is narrower but still important: at n = 8–11 Born-stable models per
element, the error axis remains strongly one-dimensional for all 15 elements
(rank-1 share 0.56–0.94). The current claim is therefore directional
low-dimensional structure in screened inputs, not a restored 14/15 per-element
count.

## Claim

The hyper-ribbon is not a quirk of classical force fields. The live question is
which parts of that low-dimensional error geometry survive when modern foundation
machine-learning interatomic potentials (MLIPs) are added to the corpus after
mechanical-stability screening.

## Historical evidence (pre-screening; do not cite as current counts)

Ingested one foundation MLIP at a time on the 15 IMMI elements:

- **MACE-MP-0:** 14/15 elements stay on the hyper-ribbon.
- **CHGNet** (added on top): 14/15 still on the ribbon.
- **Orb-v3** (completing the trio): 14/15 still on the ribbon; the held-out
  exception (Fe) is consistent across all three — see
  [Fe persistent outlier](fe-persistent-outlier.md).

Separately, the corpus was **de-myopized**: it had been ~99.5 % elastic-constant
records. Recovering real lattice constants ($a_0$) from MLIP provenance (45 records)
and forcing a joint $C_{ij}+a_0$ manifold, the ribbon **survives** (participation
ratio 1.05–2.05). This is a historical reported result, not a demonstrated exclusion
of an observable-selection or scale artifact. Its exact generator, normalization,
complete-case sample and model/reference dependence must be recovered before
that interpretation is used. The maintained Distill raw-error PCA path
must not be assumed to be the generator of this separate result.

## Why it matters

This remains the genuinely important target: the prior — stated explicitly before
the test — was that the ribbon/dichotomy would *not* transfer from classical to
MLIP. The screened directional signal suggests the geometry may still transfer,
but the old element count cannot be promoted until it is recomputed on valid
tensors.

## Next

Before further calculation, recover the pinned input and normalization contract
for the existing joint-property result. Use the same eligible observations for
any matched comparison and retain the Born-screening exclusions. The old
transfer count remains open; this is not an instruction to replay simulations.

Adding $E_\text{coh}$ or $a_0$ requires a declared dimensionless scale and sample
contract. A $B_0$ derived as $(C_{11}+2C_{12})/3$ from the same constants adds no
independent measurement; a separately fitted equation-of-state value has its own
protocol. See [the calculation and proof boundaries](../science/objects.md).
