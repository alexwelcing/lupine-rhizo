# Synthesis — MLIP runtime correction: literature review → hypothesis register (2026-07-20)

**Status:** director synthesis of the four-track literature review (LIT-A/B/C done; LIT-D2 recovering) mapped onto our measured Round-4 results and the existing correction architecture. Inputs: `lit-review/correction-mechanisms.md`, `lit-review/underbinding-failures.md`, `lit-review/china-umlip-corrections.md`; the architecture map from the director's explore pass (runtime vs offline correction paths).

## What the literature now establishes about our measured failures

1. **Our Z1/Z3 underbinding signature is the literature's documented failure mode, at our measured direction.** Deng et al. (npj Comput. Mater. 2025, DOI 10.1038/s41524-024-01500-6): systematic energy/force underprediction for M3GNet, CHGNet, MACE-MP-0 on surfaces, defects, barriers, high-energy configs — attributed to near-equilibrium-biased pretraining; barrier MAEs 0.34/0.39/0.49 eV. Bheemaguli et al. (Digital Discovery 2026, DOI 10.1039/D5DD00534E): CHGNet/M3GNet underpredict on 73.1%/78.2% of 574 literature-derived migration paths. Our Z1 finding (all-negative signed errors, 135–243 meV MAE) is the same phenomenon at preregistered scale.
2. **The one demonstrated barrier fix is transition-state-targeted fine-tuning, at ~3k labels, in-loop.** Lian et al. (J. Mater. Chem. A 2025, DOI 10.1039/D5TA05355B): TS-inclusive fine-tuning cut held-out barrier MAE 0.23→0.09 eV and ran inside NEB and 200 ps MD. Not small-budget.
3. **Small-budget corrections exist but are structurally narrow.** Deng et al.'s one-scalar fix (1 DFT label, force MAE 0.190→0.166 eV/Å; 10 labels → 0.125) repairs a near-global multiplicative softening slope — matching our Z1 *shape* (multiplicative under-prediction), and structurally incapable of representing our Z3 *field* (sign-changing, family/size-structured).
4. **For heterogeneous fields, the literature's answer is local, on-policy residuals, not global shifts.** Embedding-GPR Δ (Christiansen & Hammer, JCP 2025, DOI 10.1063/5.0268264) and active SOAP-GPR Δ (Pitfield et al., PCCP 2026, DOI 10.1039/D5CP04302F): corrections fitted from the model's own embeddings and updated from DFT points acquired *inside* the search loop. Consistent with why our frozen 6-point delta failed — the fit must see the actual error field where the search walks.
5. **No published production runtime abstention/gating policy exists** (LIT-C negative finding). Gated attention (DPA-1) is architecture; task heads (DPA-2) are label routing; ensembles are acquisition signals. Our Lean-licensed refusal machinery is genuinely novel territory — the library review confirms no prior art to copy, only signals to calibrate.

## Hypothesis register (testable, each tied to our theorem machinery)

- **H1 — Scalar slope calibration is a valid Z1 first move.** The Z1 under-prediction is multiplicative within chemistry families (all-negative signed errors). A per-family scalar energy/force slope, fitted on ≤10 high-energy DFT points per family and licensed by our direction theorems (wrong_direction_inflation_worsens as the gate), should cut barrier MAE ≥2× at trivial cost. *Test:* preregister per-family scalar correction on the locked 30-path panel (fit on a small disjoint high-energy set, score on the same 30 paths).
- **H2 — Z3 needs on-policy local residuals, not a frozen delta.** Replace the refuted static delta with a GPR residual on model embeddings, fitted on DFT points acquired by the actual screening/search loop (active Δ). *Test:* preregister an active-Δ protocol on the 32-row CatBench panel (fit from ≤20 on-policy acquisitions; success = corrected holdout MAE ≤ 0.5× baseline, not the overfit 0.1 eV gate).
- **H3 — The runtime gate must move from offline scripts into `DistillSupportModel`.** The proven sign-gate + theorem caps (2s/3s+floor) live only in offline analysis; runtime corrections are un-gated mean biases. Porting the gate into the runtime path with Lean license checks (and a per-cell overhead timer) will improve accuracy *and* produce the first honest speed numbers (support-set evaluation dominates; batch caching exists but is unmeasured).
- **H4 — Abstention thresholds must be calibrated per (model, property, class), not borrowed.** Literature offers signals (ensemble spread, descriptor distance, GPR variance) but no calibrated universal gate. *Test:* conformal-style calibration of refusal thresholds on our held-out panels; coverage/error curves as the deliverable; Lean layer certifies the *threshold-free* direction laws only.
- **H5 — Training-distribution is the deepest lever we don't control.** DPA-1's OC2M (surface/adsorbate) and MatterSim's active 0–5000 K sampling address the root cause (near-equilibrium bias). Short of retraining, TS/high-energy augmentation (H1/H2) is the only proven patch; if a partner GPU budget appears, a TS-augmented fine-tune (~3k labels) is the literature's demonstrated 0.23→0.09 eV route.

## What this means for the correction-system work program

1. **Accuracy first:** port the proven gate into runtime (H3) — it is the highest-certainty improvement because every piece is already proven in isolation (offline gate, Lean laws, runtime session).
2. **Speed second:** instrument the correction path end-to-end (support-fit vs correction vs guards), then attack the dominant support-set evaluation cost (batch caching is built, unmeasured; ribbon fits are candidates, not applied).
3. **New observables:** H1 (Z1 scalar pilot) and H2 (Z3 active-Δ) are the preregistration candidates for Round 5 — each framed against the locked panels we already own.
4. **Certified inference:** H4's calibration study completes the refusal story the literature lacks; LIT-D2's recovered digest will fill the mechanism/cost details before Round 5 preregistration.

## Provenance

- Digests: hermes researchers t_c49221d8 (LIT-B), t_aea25e09 (LIT-A), t_851c912e (LIT-C), t_dc3e11a8 + t_46e55864 (LIT-D/LIT-D2). All strict-provenance (DOIs/arXiv ids, quoted numbers, unaccessed items marked).
- Our measurements: Z1/Z3 campaign reports (`docs/validation/`), claims registry (withdrawn/refuted), Lean refutation theorems (PR #49).
- Architecture map: director explore pass, 2026-07-20 (runtime vs offline correction paths, gap list).
