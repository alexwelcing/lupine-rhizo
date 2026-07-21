# Z1 Sparse-DFT Pilot — Union-Anchor Economics

**Schema:** `lupine.z1.union_anchor_economics.v1` · **Data:** `data/candidates/z1-union-anchor-economics.json` · **Script:** `tools/analysis/union_anchor_economics.py` · **Recorded:** 2026-07-21

Cross-model cost analysis of the frozen sparse-anchor protocol
(`docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md`) on the locked
30-path Z1 panel, computed **from the recorded Round-4 float64 campaign
artifacts only — no DFT was run**. This note is the durable record of numbers
previously computed ad hoc in a chat session; the recomputed values below are
authoritative where they differ (see §4).

## 1. Method

Per model `m` and path `p`, the model's recorded `predicted_image_energies_ev`
profile (completed predictions only, mirrored from
`gcp/sparse-dft-pilot/run_pilot.py:guided_paths`) selects extrema, and the
frozen rule (`gcp/mlip-cell-runner/z1_sparse_dft.py`, byte-equivalent copy in
the analysis script) builds the anchor set:

> A(m,p) = {0, n−1, argmin} ∪ {argmax−w … argmax+w}, clamped and de-duplicated;
> w = 2 when n ≤ 6 images, else 1.

- **Naive total** = Σ_m Σ_p |A(m,p)| — each model pays its own sparse DFT.
- **Union total** = Σ_p |∪_m A(m,p)| — one DFT evaluation per unique image
  index per path, shared across models (endpoints are naturally shared).
- **Agreement**: per path, whether the models' argmax (saddle) indices, resp.
  both argmin and argmax indices, coincide — exact and within ±1 image, under
  two conventions (§3).

Sources (sha256 recorded in the JSON): panel
`gs://shed-489901-atlas-inputs/z1/data/candidates/z1_nebdft2k_barriers.lock.json`;
artifacts `gs://shed-489901-atlas-outputs/z1/campaign-float64/<model>/cell_result.json`
with model dirs **`chgnet`, `mace-mp-small`, `mace-mp-medium`, `mace-mpa-0-medium`**.
All 30 panel paths are analyzed, including the seven large-cell paths deferred
from DFT *execution* (`data/candidates/z1-sparse-dft-deferred.json` lists
indices 2, 8, 10, 18, 20, 23, 28 — its prose says "six", the list holds seven;
they are excluded from GPAW runs, not from this prediction-side analysis).

## 2. Headline numbers (recomputed)

| Basis | Paths | Model-path pairs | Naive | Union | Saved | Ratio |
| --- | --- | --- | --- | --- | --- | --- |
| All analyzable paths (primary) | **29/30** | 111/120 | **558** | **154** | **72.4%** | **3.6×** |
| Fully-covered paths only | 26/30 | 104/120 | 520 | 136 | 73.8% | 3.8× |

Cross-model agreement over the 29 analyzable paths:

| Statistic | Available-models convention | All-four-required convention |
| --- | --- | --- |
| Saddle (argmax) exact | 23/29 | 20/29 |
| Saddle within ±1 | 26/29 | 23/29 |
| Both extrema exact | 10/29 | 9/29 |
| Both extrema within ±1 | 12/29 | 11/29 |

## 3. The 29-vs-30 reconciliation

The panel has 30 paths (indices 0–29). **The true analyzable denominator is
29**: path index **14 (`mp-756912_1_1_1_0_0`) failed CI-NEB convergence under
the frozen protocol in all four model artifacts**, so no model profile exists
to guide anchors — it is the one path with incomplete artifacts *across
models*, and it is excluded with its per-model failure records in the JSON.

Three more paths have partial coverage (agreement there is computed over the
models present, which is why two conventions are reported): index 8 lacks
mace-mp-small; index 13 lacks mace-mp-small and mace-mpa-0-medium; index 18
lacks chgnet and mace-mp-small (all recorded campaign failures, never imputed).
Only 26 paths carry all four models.

## 4. Discrepancy vs the prior chat-session numbers

The prior session reported: 624 naive vs 132 union (79% fewer, 4.7×), saddle
agreement 20/29, both-extrema agreement 12/29.

- **Economics do not reproduce.** Recomputed: **558 naive, 154 union, 72.4%
  (3.6×)** over the 29 analyzable paths; 520/136/73.8% (3.8×) over the 26
  fully-covered paths. No variant under the frozen anchor rule on these
  artifacts yields 624/132: 624 is near a (wrong) ±2-window-everywhere naive
  count (625), but that variant's union is 166, and 132 is below even the
  mean *single-model* anchor total (139.5) — union ≥ any individual model's
  total on the same path set, so 132 is arithmetically incompatible with a
  4-model union on this panel. The artifacts are unchanged since (the chgnet
  artifact is byte-identical to the 2026-07-20 cached copy; GCS object
  timestamps predate the prior session), so the chat figures most plausibly
  suffered definitional/arithmetic drift. **The recomputed values stand.**
- **Agreement counts reconcile cleanly.** 20/29 saddle-exact is exactly the
  all-four-required convention; 12/29 matches both-extrema **within ±1**
  (available-models), not exact agreement. Under one consistent convention:
  saddle exact 23/29 (available) or 20/29 (all-four); both extrema **exact**
  10/29 (available) or 9/29 (all-four). The prior "12/29 both extrema" was
  the ±1-tolerance number, not exact.

## 5. Scaling note — union grows sub-linearly in model count

Union cost saturates quickly: models largely nominate the same images, so each
added model costs its full naive share but adds few *new* unique anchors.

| Models | Naive (mean over subsets) | Union (mean over subsets) | Union, cumulative fixed order (chgnet → +mace-mp-small → +mace-mp-medium → +mace-mpa-0-medium) |
| --- | --- | --- | --- |
| 1 | 139.5 | 139.5 | 142 |
| 2 | 279.0 | 147.8 | 144 |
| 3 | 418.5 | 152.0 | 152 |
| 4 | 558.0 | 154.0 | 154 |

Going from 1 → 4 models multiplies naive cost ~4× but union cost only ~1.10×
(139.5 → 154 mean; 142 → 154 cumulative). Sharing anchors across an ensemble
of guides is therefore close to free: four models' worth of guidance for ~10%
more DFT than one, and the marginal union growth per added model is already
flat at k=3.

## Reproduce

```bash
python3 tools/analysis/union_anchor_economics.py \
    --out data/candidates/z1-union-anchor-economics.json           # pulls from GCS
python3 tools/analysis/union_anchor_economics.py --local <dir> \
    --out data/candidates/z1-union-anchor-economics.json           # offline artifacts
```
