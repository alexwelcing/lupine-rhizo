# Research progress: what does model disagreement tell us?

Reviewed 2026-10-06. Status: **completed exploratory archive analysis; arithmetic independently checked**.

## Question and observation

Does prediction-only disagreement rank atom-level force error better than predicted force magnitude on both broader archived panels?

Six archived prediction files were recovered and matched their previously recorded SHA-256 hashes. The analysis used 400 configurations from MatPES and 400 from OMat24: 50 recorded groups with eight configurations each per panel. No new model, DFT or simulation job was run.

| Panel | Configurations | Atoms | Mean capture-area increment | Positive groups | Positive configurations |
| --- | ---: | ---: | ---: | ---: | ---: |
| MatPES | 400 | 3,324 | +0.0203685681 | 37 / 50 | 208 / 400 |
| OMat24 | 400 | 3,912 | +0.0134210015 | 29 / 50 | 207 / 400 |

Both equal-group mean increments are positive. The gains are modest: about **2.04 and 1.34 percentage points in average error-capture area**, respectively. These are ranking gains, **not reductions in force prediction error**. Only about half of individual configurations outperform the control. This supports investigating disagreement further; it does not establish a reliable deployment alarm.

## Frozen calculation

The fixed, equally weighted model roster is CHGNet, M3GNet and MACE-MP-small. For each atom, let the mean predicted force be Fbar. Disagreement is the mean of squared distances from each model prediction to Fbar. Actual error is the squared distance between Fbar and the reference force. The control score is squared predicted force magnitude.

For each configuration and each k from 1 through N-1, compute the fraction of total squared error captured in the k highest-scored atoms. Ties receive expected capture under uniform tie-breaking. Average capture minus k/N across k, then subtract the corresponding area from the force-magnitude control. Average the eight configurations within each recorded group, then the 50 groups in each panel. The fixed primary criterion requires a positive mean increment in both panels. No exclusions, fitted thresholds, tuned weights or inferential p-values were used.

An independent 70-digit calculation from the original force arrays checked 42,954 numeric values and 8,962 structural/hash/join assertions, with zero failures, rank changes or increment-sign changes. Maximum scaled numeric discrepancy was 3.46e-15. This checks the arithmetic, not scientific generalization.

## Pilot and limitations

An earlier five-configuration pilot used a different roster: CHGNet, MACE-MP-0 and SevenNet. Disagreement had positive capture area on four of five configurations, but beat the force-magnitude control on only three. Its strict all-five criterion failed. The broader analysis is a distinct exploratory follow-up, not an exact replication.

- These are historically analyzed archive configurations, not a newly sealed held-out benchmark. Correlated atoms and frames are not independent replications.
- Grouping is based on the recorded material groups. One MatPES group mixes four- and eight-atom structures and repeated step labels; it must not be presented as a verified trajectory.
- MatPES metadata identifies DFT-PBE; OMat metadata identifies PBE+U despite a PBE-bearing filename. Full reference settings, training-overlap audit and exact model-weight provenance remain incomplete.
- Model-ensemble uncertainty is established prior art. This analysis makes no claim of methodological novelty, calibrated uncertainty, generalization or correction certification.
- The historical A6 decision remains **INCONCLUSIVE**. This ranking calculation does not change that decision.
- Raw research archives and private execution records are not published. The hashes below anchor the retained artifacts but do not make this public summary independently reproducible from public inputs alone.

## Next discriminating test

Compare all three pairwise squared force distances while holding the original three-model mean prediction and its error fixed. Use the same capture metric, group weights and control. If a pair matches or exceeds the full disagreement score on either panel, reject the claim that all three models add ranking value on these panels. Examine whether results depend on one model's scale or errors. Selecting the best pair in-sample would not constitute independent validation. This follow-up is **planned, not executed**.

## Evidence anchors

| Artifact retained privately | SHA-256 |
| --- | --- |
| Frozen broader-panel protocol | 27661525752472b24f12c2c1a34442f1018b098d9db9fed8b64aca4b3a36a575 |
| Broader-panel result | 66df43105c309a38729610efe01f6f5f5c32af4e6c8e4fc53f7e3d54ab220e55 |
| Broader-panel analysis code | dd6ee34877bc0ef6855b50555baceab4001ec27f28d08c8d6b0a6f217675caec |
| Independent verification | 6c57375356117c53ae4082125321a5660c9701343fb87dd3fe9af3d913008e5f |
| Pilot result | 9779533b40d92f894156088c84a1579076460f97f2e1f8484b36d23956911174 |

Observation completed on 2026-10-06; broader-panel independent verification completed at 12:57:53.958Z. Public summary reviewed at 13:10:45.000Z.

## Prior research

- [Liu et al., heterogeneous model ensembles (published December 17, 2025)](https://www.nature.com/articles/s41524-025-01905-x): direct prior art for ensemble uncertainty; its model roster and scoring procedure differ.
- [Lu et al., uncertainty and overconfidence in ML interatomic potentials (2023)](https://arxiv.org/html/2309.00195v1): motivates checking agreement against actual error.
