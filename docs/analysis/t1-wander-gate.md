# T1 — The Convention-Wander Gate

**Theorem line:** T1 (first theorem contributed from our own campaign failure) ·
**Script:** `tools/analysis/t1_wander.py` (stdlib-only) · **Tests:** `tools/analysis/test_t1_wander.py` ·
**Wired into:** `gcp/sparse-dft-pilot/union_pilot.py` assembly (`per_path[].t1_gate`, `t1_summary`) ·
**Amendment:** `docs/plans/2026-07-21-sparse-dft-pilot-amendment-01.md` (§A1) · **Recorded:** 2026-07-21

Per evaluated image of a NEB path, the cross-engine offset is
`offset(image) = E_GPAW(image) − E_VASP(image)`. **T1 reports the offset mean
and the offset wander (max − min) per path, and gates on the wander.**

## 1. Measured evidence — one failure, one win, same wander

| Path | Anchors | Offset wander | Cross-engine barrier error | Verdict vs ≤40 meV gate |
| --- | --- | --- | --- | --- |
| path-7, `mp-770939_10_1_1_0_1` | 4 (images 0,1,2,4) | **139.4 meV** | **118.8 meV** | FAIL |
| smoke path, `mp-760344` | chgnet-guided set | **~122 meV** | **32.2 meV** | WIN |

Path-7 numbers are reproduced by the gate from the receipt
(`/tmp/z1-sparse-local/chgnet/path-7.json`, imported as union checkpoints
`lupine.z1.union_pilot.anchor.v1`): per-image offsets −14756.1, −14698.1,
−14616.8, −14666.2 meV → wander **139.3758 meV**, mean −14684.3 meV, driven by
the image pair **(0, 2)**. The smoke-path figures are the recorded trigger
evidence of amendment 01 (its anchor receipts predate the union checkpoint
layout; only `/tmp/gpaw-pilot/run.py` survives).

The two rows are the whole argument: **two paths, two opposite verdicts, the
same wander magnitude.** Under a single VASP-referenced basis, the pilot's
verdict measures where the engine-convention wander happens to land, not
protocol quality. Wander is *necessary but not sufficient* for a cross-engine
failure — the smoke path won because its wander landed off the
barrier-defining images. That is exactly why T1 is a **gate with a
contamination flag, not a hard refusal**.

## 2. Why the wander, not the mean

A barrier is an energy *difference between different structures*:
`barrier = max_i E(i) − min_i E(i)`. A constant offset — however large —
cancels in every difference; the −14.7 eV mean above is barrier-irrelevant.
Only *variation* of the offset across images injects into the comparison, and
the worst-case injection over a path is bounded by the wander:

```
|barrier_GPAW − barrier_VASP| ≤ wander = max offset − min offset
```

(proof sketch in §5). With measured wander ~3× the 40 meV verdict gate, every
cross-engine verdict on these paths was one unlucky landing away from
flipping. Amendment 01 therefore splits the basis (same-engine primary,
VASP-referenced secondary) and promotes T1 to its own experiment.

## 3. Gate semantics

Default threshold is the frozen verdict gate, 40 meV
(`WIN_THRESHOLD_MEV` in `gcp/mlip-cell-runner/z1_sparse_dft.py`).

- `wander ≤ 40 meV` → **clean**: the path's cross-engine numbers may be
  quoted at face value (they remain secondary to the same-engine basis).
- `wander > 40 meV` → **contaminated**: the path's cross-engine
  (VASP-referenced) verdict is downgraded to **"convention-contaminated"** —
  it measures engine-convention luck, and the same-engine basis of amendment
  A1 is the *only* trustworthy score for that path. Path-7's 118.8 meV FAIL
  stays in the record under exactly this label: a T1 datapoint, not a
  protocol verdict.
- Fewer than two evaluated images → **insufficient_data**: a one-point wander
  carries no information; the gate abstains rather than declaring "clean".

The gate also reports the **driver pair** — the (min-offset, max-offset)
image pair whose difference *is* the wander — so a contaminated path names
its own contaminated span (path-7: images 0↔2, which are also the
barrier-defining extrema of its sparse profile; the contamination sits
directly on the barrier). Per-image drift vs a least-squares linear trend in
image index, and a Spearman rank monotonicity, are reported alongside as
diagnostics (path-7: slope ≈ +22.1 meV/image, ρ = 0.8 — the offset shallows
overall along the reaction coordinate).

In `campaign.json` (`lupine.z1.union_pilot.campaign.v1`, additive fields
only): `per_path[].t1_gate = {wander_mev, verdict, driver_pair}`,
`t1_summary.paths_contaminated` / `contaminated_path_indices`, and
`thresholds.t1_gate_mev`. The gate is wired into `union_pilot.py` assembly as
a **reported line item** — it downgrades interpretation, never refuses a path.

## 4. Why this is the theorem-commons loop working

T1 is the first theorem contributed from our *own* campaign failure. The loop
ran: a frozen preregistration produced a FAIL → the per-anchor receipts
localized the cause to a *protocol-external* quantity (engine-convention
wander) → an amendment split the basis so each verdict measures one thing →
the localized cause became a **reusable gate that anyone comparing barriers
across engines can apply to their own receipts**, before quoting a
cross-engine number. The failure is now load-bearing: it defines the
hypothesis (`wander ≤ ε`) under which cross-engine barrier comparisons are
trustworthy at tolerance ε, and it ships as a stdlib-only function with the
measured counterexample pair encoded in its tests. Every future path in this
pilot — and any external GPAW↔VASP, or generally engine-A↔engine-B, barrier
comparison — gets flagged by the same gate instead of rediscovering the
contamination as a spurious verdict.

## 5. Future work — Lean formalization sketch

The gate is the decidable hypothesis check of an elementary transfer theorem.
State `barrier f s = s.max' f − s.min' f` over a nonempty `Finset ι`; the
offset `o : ι → ℝ` is the cross-engine convention difference. Then:

```lean
theorem barrier_transfer_of_bounded_offset_wander
    {ι : Type*} (s : Finset ι) (hs : s.Nonempty)
    (E o : ι → ℝ) {ε : ℝ}
    (h : ∀ x ∈ s, ∀ y ∈ s, |o x - o y| ≤ ε) :
    |barrier (fun i => E i + o i) s - barrier E s| ≤ ε := ...
```

Proof idea (two inequalities, both one-liners from `Finset.le_max'` /
`Finset.min'_le`): with `x*`/`x⁻` the extrema of `E + o`,
`barrier (E+o) − barrier E ≤ o x* − o x⁻ ≤ ε`, because
`barrier E ≥ E x* − E x⁻`; with `y*`/`y⁻` the extrema of `E`,
`barrier E − barrier (E+o) ≤ o y⁻ − o y* ≤ ε`. No library changes are needed
for the statement; the hypothesis is decidable on receipts because
`max_{x,y} |o x − o y| = max o − min o = wander`, i.e. **the gate IS the
hypothesis evaluated on data**, with `ε` the verdict gate. Two honest
boundary notes for the formalization: the converse is false (bounded wander
is sufficient, not necessary — the smoke path's 32.2 meV win under 122 meV
wander is the counterexample, since only the offset difference between the
*barrier-defining* pair enters the error), and a refined theorem bounding the
error by `|o(argmax) − o(argmin)|` alone would formalize that observation at
the cost of needing the extrema identified — which the sparse protocol is
itself trying to estimate. The wander form is the version checkable *before*
trusting any verdict.

## Reproduce

```bash
# unit + real-receipt tests (receipt-cross-checks skip if /tmp files absent)
python3 -m pytest tools/analysis/test_t1_wander.py -q
python3 -m pytest gcp/sparse-dft-pilot/test_union_pilot.py -q

# gate on the real path-7 anchor pool (offline assembly; no GPAW)
python3 gcp/sparse-dft-pilot/union_pilot.py \
    --workdir /tmp/z1-union-local --local /tmp/z1-union-local/inputs \
    --paths 7 --assemble-only --no-import --out /tmp/campaign.json
# -> path-7: wander=139.4 meV, t1_gate=contaminated, driver_pair=[0, 2]
```
