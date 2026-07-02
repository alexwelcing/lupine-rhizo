# Fig 5 spec — run-time correction experiment (placeholder)

`data/y_matrix_runs/envfield_experiment/` was not present when the other
figures were built, so Fig 5 could not be generated from artifacts. When the
correction experiment lands, generate Fig 5 (7 in, two panels) from its
REPORT/JSON artifacts:

- **Panel (a): static corrections.** Grouped bars per property
  (gamma_100, gamma_110 [blind facet], gamma_111, E_vac; bulk-sanity a0/B0
  shifts as a marginal note) for the experiment's (model, material) cells
  (per the manuscript: (CHGNet, Ni) and (CHGNet, Cu)): raw prediction vs
  field-corrected prediction vs reference. Same Okabe-Ito palette as
  Figs 1–4 (`common.MODEL_COLORS`); reference as a black tick/line, raw in
  the model color at 50% alpha, corrected in the model color solid.
- **Panel (b): force errors.** Force RMSE on rattled Ni(110) slabs vs the
  stronger-model proxy reference: raw vs corrected, split into surface
  atoms / all atoms (grouped bars, log y if the spread demands it).
  Annotate MD sanity from the run artifacts (energy drift, wall-time
  overhead of the correction) as small text if present in the REPORT.

Requirements carried over from this pipeline: recompute every number from
the experiment JSONs (no hand-typed values), record input SHA-256s in
`figures_manifest.json`, vector PDF + 300 dpi PNG at 7 in width, fonts
embedded (pdf.fonttype 42), no in-figure titles, deterministic outputs
(strip PDF CreationDate; seed anything stochastic).
