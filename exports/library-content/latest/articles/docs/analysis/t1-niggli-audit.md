# Niggli audit — path-15 (Bi-Li-S, mp-1222404), 2026-07-24

**Question:** are the anchors on the 34.4° rhombohedral cell grid-suspect? (GPAW fd warned "results may be wrong".)

**Method:** recompute basin (img0) and saddle (img2) at adopted settings (h=0.20, Gamma) on the raw cell vs the Niggli-reduced cell (`ase.build.niggli_reduce`). Verdict threshold: barrier shift >40 meV = grid-suspect.

**Results:**
- raw img0: −430.7262 eV (matches campaign checkpoint exactly); raw img2: −429.6101 eV (matches checkpoint)
- Niggli img0: −469.7732 eV; Niggli img2: −468.6536 eV (cell representation shifts absolute energies ~39 eV)
- **Barrier raw: 1.1161 eV vs Niggli: 1.1196 eV → shift +3.5 meV**

**Verdict: VALID.** The skewed cell's barrier matches the Niggli-reduced barrier within 3.5 meV — the ~39 eV representation offset cancels in the energy difference. This is the third recorded instance of the offset-cancellation pattern (convention offsets in T1, settings offsets in amendment 02, cell-representation offsets here): barriers are robust to constant offsets; only wander matters. No anchor recomputation needed; path-15's data stands as-is.
