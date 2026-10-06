# Rank-only combination retains an average advantage over every individual pair

Date: 2026-10-06. Status: completed exploratory archived-data calculation; independently arithmetic-verified.

## Question and result

Does a positive mean advantage over every individual pair survive after removing pair-distance magnitudes?

The predeclared descriptive criterion passed on both archived panels. Equal-weight fusion of pairwise ranks exceeds the strongest individual pair, M3GNet–MACE-MP-small, by **0.5494 area percentage points on MatPES** and **0.9881 on OMat24**. Thus original distance magnitudes are unnecessary for a positive average advantage over each single pair in this fixed comparison. This does not establish a causal mechanism or generalization.

Fusion does not consistently improve on full disagreement: it loses **0.2629 points on MatPES** and gains only **0.0367 on OMat24**. We retain full disagreement as the existing reference score and do not select a replacement from this reused data. These quantities measure ranking-area differences, not reduced force error.

## Fixed method

This is the single follow-up specified by the [preceding pairwise analysis](./2026-10-06-pairwise-disagreement.md). For each configuration, each of its three pair-distance vectors is converted to ascending midranks. Twice each midrank is computed exactly as `2 × count(lower scores) + count(equal scores) + 1`; these three integer vectors are summed with equal weights. Atoms are ranked by descending sum. Exact numerical equality of preserved scores defines ties, with no fitted tolerance.

The original CHGNet/M3GNet/MACE-MP-small mean force prediction, squared reference error, full disagreement score, force-magnitude control, three pair scores, all configurations and recorded grouping are unchanged. Error capture is the fraction of a configuration’s squared error captured among its top k scored atoms, averaged uniformly over exact ties. Area averages capture minus k/N for k=1,…,N−1. Eight configuration areas are averaged within each recorded group, then 50 groups equally per panel. MatPES has 400 configurations and 3,324 atoms; OMat24 has 400 and 3,912.

The protocol was frozen and hashed before evaluating fusion. The primary criterion required fusion to exceed every individual pair’s panel mean on both panels. Full/control comparisons were specified secondary checks. There were no new predictions, model calls, fits, exclusions or alternative transformations. Local timestamps and hashes provide traceability, not external tamper-proof preregistration.

## All five comparisons

All values below are **area percentage points**, with positive increments favoring fusion. Capture-area values are multiplied by 100 for display.

| Score | MatPES area | OMat24 area | Fusion minus score: MatPES | Fusion minus score: OMat24 |
| --- | ---: | ---: | ---: | ---: |
| Rank fusion | 9.3577 | 10.6318 | — | — |
| Full disagreement | 9.6206 | 10.5951 | -0.2629 | +0.0367 |
| Force magnitude | 7.5837 | 9.2530 | +1.7740 | +1.3788 |
| CHGNet–M3GNet | 8.4795 | 9.0162 | +0.8782 | +1.6156 |
| CHGNet–MACE-MP-small | 6.6997 | 7.8163 | +2.6579 | +2.8155 |
| M3GNet–MACE-MP-small | 8.8083 | 9.6437 | +0.5494 | +0.9881 |

Counts are **fusion better / worse / tied**, using the fixed configuration error targets.

| Comparator | MatPES groups (50) | OMat24 groups (50) | MatPES configurations (400) | OMat24 configurations (400) |
| --- | ---: | ---: | ---: | ---: |
| Full disagreement | 16 / 33 / 1 | 24 / 25 / 1 | 108 / 140 / 152 | 131 / 167 / 102 |
| Force magnitude | 35 / 15 / 0 | 29 / 21 / 0 | 209 / 139 / 52 | 211 / 178 / 11 |
| CHGNet–M3GNet | 28 / 22 / 0 | 27 / 23 / 0 | 178 / 130 / 92 | 206 / 167 / 27 |
| CHGNet–MACE-MP-small | 34 / 15 / 1 | 31 / 18 / 1 | 195 / 124 / 81 | 216 / 147 / 37 |
| M3GNet–MACE-MP-small | 31 / 19 / 0 | 29 / 19 / 2 | 137 / 134 / 129 | 184 / 138 / 78 |

Fusion beats the strongest pair in 31/50 MatPES groups and 29/50 OMat groups, while the corresponding configuration improvements occur in only 137/400 and 184/400 cases. Those counts include many equal-area cases; averages do not imply uniformly better case selection.

## Ties and interpretation

Fusion produces exact ties in **202/400 MatPES configurations** and **233/400 OMat24 configurations**, containing 418 and 467 tie sets respectively. Relative to full disagreement it introduces all of these tie sets; the tie partition changes in those same configuration counts. Relative to each individual pair/control, these are also the introduced tie sets; the strongest pair has one MatPES tie set that fusion removes. All tie sets, curves and per-group results are retained in the private calculation.

The result supports the narrow descriptive hypothesis that combining only pair orderings can retain a positive panel-average advantage over any one pair. It need not reproduce the earlier full score’s advantage size, and does not isolate why combination helps: the pairs share models and geometric constraints. Rank conversion changes spacing and tie structure in addition to discarding magnitudes.

These historical, repeatedly inspected archives are correlated, not independent held-out validation. Group labels are retained without claiming verified trajectories, including the mixed-size MatPES group. Exact model-weight/training-overlap and per-case reference-setting provenance remain incomplete. No novelty, calibration, safe molecular-dynamics alarm, force-accuracy or reduced inference-cost claim follows; the fixed target still uses three models. Historical A6 remains **INCONCLUSIVE**.

## Verification

An independent implementation rebuilt force targets and pair scores with exact rational arithmetic, fused ranks by sorted tie blocks, and computed capture through inclusion probabilities and rank positions. It passed **106,518 numeric and 61,914 structural checks** across 800 configurations, 100 groups and 4,800 capture curves. All increments, sign distributions and tie-set changes were checked. No raw-versus-stored score/error ranking, tie-partition, sign or count discrepancies were found; maximum scaled numerical discrepancy was 3.47e-15. Original targets, comparators and pooled squared error remain unchanged. This verifies arithmetic, not provenance, generalization or scientific novelty.

## Next discriminating step — planned, not started

Stop score-variant exploration on these same 800 configurations. Audit whether an independent, uninspected validation panel is eligible, with a fixed grouping/sampling rule, source split, exact model checkpoints and reference settings, before any new prediction or label-based scoring. Retain full disagreement, rank fusion, all three pairs and force magnitude in the frozen comparison. A documented test split alone does not establish independence from all three models’ training data. If eligibility cannot be established, record the specific missing provenance and keep generalization untested; do not substitute training rows or revive stopped experiments.

## Evidence anchors

The [800-configuration report](./2026-10-06-disagreement-panels.md) and preceding pairwise report describe the unchanged inputs. Raw archives and detailed artifacts remain private; these hashes identify local artifacts without supplying public reproduction inputs.

- Frozen protocol: `ae65d93dfc87688f67e7b701988c905a8e0a37ef231cdee6e390b5bc0e803b84`
- Primary analysis: `a00b183f76e8ffbe0735bf8d58bb6d2e18c9170614d3bca64f29e290349645ff`
- Primary result: `ffe8952bf96189132e80b2911455d967e71b5b3dc9443fd11ed5f44ab19c2c6c`
- Independent verifier: `34b51b1b2d26fff74cd895f6c70c819ccbd559e83082ff84660697bbead4f501`
- Independent verification: `ceb87bd0c799eb148a0d59285001722475382a0e668def15c5b712e9a03ab046`
