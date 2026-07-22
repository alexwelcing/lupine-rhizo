# T1 wander mechanism — metallic saddles and SCF fragility (2026-07-22)

**Question:** why does the GPAW↔VASP offset wander (T1) vary 30× across the Z1 panel — 135 meV (path-7) to 4212 meV (path-0)?

**Evidence (path-0, Ag-F-Li, `mp-761269_2_1_1_-1_0`):**
- Adopted settings (h=0.20, Gamma): img3 GPAW **converged** at −492.718 eV (matches campaign checkpoint).
- h=0.18, Gamma: img3 **did not converge** — 454 iterations, residual exploding to 12.4. The −471 eV figure from that run is meaningless.
- Electronic structure at the saddle: **Gap = 0.018 eV (metallic), Fermi level ≈ 0.67 eV**; endpoints are well-behaved.
- Both engines agree the saddle is img3 and the basin is img0 — same extrema — but GPAW puts the saddle 5.79 eV above the basin where VASP (LiTraj nebDFT2k, CI-NEB PBE) puts it 1.58 eV.

**Finding:** the wander is **intrinsic to the system class**, not a settings artifact. Metallic / near-zero-gap transition states in GPAW fd mode (default smearing) vs VASP CI-NEB settings converge to different electronic descriptions on the saddle image specifically; the offset wander concentrates on exactly that image (per the same-extrema identity, `barrier_sub_eq_offset_sub`, the entire barrier error is the saddle-vs-basin offset difference).

**Consequences:**
1. The frozen settings (h=0.18, (2,2,2)) were never viable on this cell class — SCF does not converge. This retroactively explains part of path-16's 16.3 h / 62 CPU-hour failure.
2. The union campaign's adopted settings are validated as *converged* on the worst-behaved path; anchors are usable data.
3. The same-engine basis (amendment 01) is the only meaningful verdict basis for metallic-saddle paths; VASP-referenced numbers for those paths are T1-contaminated **with a mechanism**, not just a flag.
4. The T1 law (`abs_barrier_sub_le_wander`) prices the failure: measured VASP-referenced MAE 1246 meV vs mean wander 1269 meV over the first 7 complete paths.
5. Future engine-equivalence work on LiTraj-class panels must address smearing/occupation policy at metallic saddles explicitly (e.g., wider smearing, occupation control, or spin-polarized restarts) — a candidate theorem line: saddle-metallicity detector (gap < ε at the model-predicted saddle ⇒ require occupation audit before any cross-engine verdict).

**Artifacts:** `/tmp/z1-diagnose/img3-adopted.txt`, `/tmp/z1-diagnose/img3-h018.txt` (GPAW outputs); campaign receipts `/tmp/z1-union-local/anchors/path-0/`.
