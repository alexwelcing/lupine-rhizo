# Pairwise score ablation: a small average benefit from combining all three pairs

Date: 2026-10-06. Status: completed exploratory archived-data calculation, independently arithmetic-verified.

## Question and result

Does the full three-model disagreement score rank the original ensemble's errors better than every individual pairwise force-distance score on both archived panels?

The fixed descriptive criterion passed: the full score has a higher equal-group mean error-capture area than each pair on both panels. The nearest pair is M3GNet–MACE-MP-small; the full score adds **0.8123 area percentage points on MatPES** and **0.9514 on OMat24**. These are gains in a ranking-area statistic, not reductions in force error.

## Fixed comparison

We retained the original CHGNet, M3GNet and MACE-MP-small equal-weight mean prediction, its reference errors, the force-magnitude control, all 800 configurations and the same 100 recorded groups. Only the score used to rank atoms changed. Each pair score is the squared Euclidean distance between its two predicted force vectors. The full disagreement score equals the sum of the three pair scores divided by nine.

For each configuration, the capture curve measures the fraction of total squared error among the k highest-scored atoms. Exact score ties receive the expected capture under uniform tie-breaking. The area averages capture minus k/N over k=1,...,N−1. We average eight configurations per recorded group, then 50 groups per panel. No fitting, new model evaluation, selected threshold or exclusion was introduced.

The earlier checkpoint specified all three comparisons and the unchanged target. The local protocol was frozen before this calculation. Local hashes and times are traceability, not a tamper-proof external preregistration.

## Every pair

All values below are **area percentage points**. Positive full-minus-pair favors the full score; positive pair-minus-control favors the pair over force magnitude.

| Pair score | Full minus pair: MatPES | Full minus pair: OMat24 | Pair minus control: MatPES | Pair minus control: OMat24 |
| --- | ---: | ---: | ---: | ---: |
| CHGNet–M3GNet | 1.1411 | 1.5789 | 0.8958 | -0.2368 |
| CHGNet–MACE-MP-small | 2.9208 | 2.7789 | -0.8840 | -1.4368 |
| M3GNet–MACE-MP-small | 0.8123 | 0.9514 | 1.2246 | 0.3907 |

Full-minus-control remains +2.0369 points on MatPES and +1.3421 on OMat24, as in the previous analysis.

The means hide variation. Against the nearest pair, full is better/worse/tied in **27/21/2 MatPES groups** and **32/16/2 OMat24 groups**. At the configuration level the corresponding counts are **135/112/153** and **179/106/115**. MatPES's median group advantage is only **0.0361 points**. Full disagreement is therefore not uniformly better on individual cases.

## What this does and does not establish

The comparison supports added average ranking value from combining pair scores on these particular panels. It does not distinguish complementary ordering from pair-distance magnitude effects. The three pairs also share model members and geometric constraints; they are not independent estimators.

The target prediction still uses all three models. This score ablation does not establish cheaper two-model inference, improved RMSE, calibration, molecular-dynamics safety or generalization. The data are historical and correlated, with incomplete training-overlap and reference-setting provenance. The mixed-size MatPES group is retained without treating it as a verified trajectory. No novelty claim is made. Historical A6 remains **INCONCLUSIVE**.

## Verification

An independent implementation reconstructed force arrays using exact rational arithmetic, calculated capture by inclusion probabilities and rank positions, and audited all pair curves, correlations, group summaries, signs and supplemental control counts. It passed **104,934 numeric and 47,521 structural checks** across all 800 configurations and 100 groups. No score/error rank changes or near-zero sign changes were found. Maximum scaled numeric discrepancy was 3.47e-15. The original three-model prediction, error, force-magnitude control and pooled squared error were verified unchanged. This checks the calculation, not the archive provenance or generalization.

The private result is preserved. A separate supplemental artifact supplies the pre-specified positive/zero/negative counts against the force-magnitude control that were omitted from the first result's summary; the primary scores and criterion were not changed. All configuration curves and group results remain private.

## Next discriminating test — planned, not started

Use the equal-weight sum of within-configuration pair midranks as a new score, with integer doubled midranks to preserve exact ties. Keep the three-model target, all controls and aggregation unchanged. Require the fused score to beat every individual pair on both panels. This single label-free transformation tests whether a positive mean advantage over every individual pair survives after removing pair-distance magnitudes. Passing need not recover the original advantage’s size. A failure would not prove magnitude dominance because ranks also discard spacing and can create ties.

## Evidence anchors

The preceding [800-configuration analysis](./2026-10-06-disagreement-panels.md) supplies the input/provenance context. Raw archives and detailed private results are not published; hashes identify artifacts without providing public reproduction inputs.

- Frozen protocol: `87bd4fdb70a0e5b23205678bd48458e5f6bd5a2a0f879e064267e6f411a5a594`
- Primary analysis: `cad5ac22a3f60e208c3f77998ea475c2dc38fce748a428ce2ac237282f05901e`
- Primary result: `329c95481aa45c4f7635ff379e59d862961b3d919634c3ba737db9993ca8ff3f`
- Supplemental control counts: `bd24cb97f828bd674ce8046829a43ae0e65038e08f584e806044be7305f6d79f`
- Independent arithmetic verification: `a48b726c9a0c866c088f5496f1afc55aca07605322966e8c982a7db7e146cb84`
