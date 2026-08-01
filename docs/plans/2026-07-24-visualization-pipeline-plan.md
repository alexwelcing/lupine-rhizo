# From science run to citable visualization

Date: 2026-07-24
Status: proposed architecture
Scope: Lupine science outputs rendered and inspected in Lupi, from the current Z1 campaign to roughly one million runs

## Decision in one page

Build a publication pipeline, not a larger version of the path-16 demo.

Each completed science run should produce a schema-validated, immutable visualization bundle. The bundle binds source calculations, coordinates, per-image values, selection/gate semantics, and provenance by SHA-256. A publisher writes its assets to content-addressed GCS paths, uploads the manifest last, and then updates a query index. Lupi loads the manifest as one object, so geometry and scientific overlays cannot be paired by hand or drift apart. Figures and movies are digest-bound derivatives rendered only for selected records.

Keep `lupi.live` as the canonical viewer. If Lupine branding needs `viewer.lupine.science`, make it a redirect to a stable Lupi collection route. A second deployment would duplicate auth, release, rollback, CORS, and monitoring work without improving the data pipeline.

Do not expand `packages/core/src/scienceDataCatalog.ts` into a run registry. At the inspected Lupi commit it contains eight compile-time, Zenodo-only LAMMPS records; client-side discovery is capped at 25 results. Keep it as a small curated showcase. Put run discovery behind paginated runtime indexes and immutable catalog snapshots.

The first milestone is not a 23-path gallery. It is a science contract and four golden bundles:

- path 16: a seemingly good cross-engine result that is T1-contaminated;
- path 0: the large-wander mechanism case;
- path 14: all four guides failed and dense extension supplied the profile;
- path 27: the only T1-clean path.

That set forces the contract to represent success, contamination, model failure, dense completion, and missingness before automation hides mistakes at scale.

### Non-negotiable scientific rule

Z1 contains NEB reaction-path images, not time samples. The viewer and every exported artifact must say "reaction-path sequence," "NEB image," or name a defined reaction coordinate. Playback must not imply dynamics, kinetics, or equal elapsed time.

### Program kill conditions

Stop promotion, rather than patching around the result, if any of these occur:

1. a bundle cannot reproduce its reported barrier, extrema, anchor set, guidance deficit, and T1 verdict from stored arrays;
2. trajectory and profile cardinality, atom identity/order, units, or source hashes disagree;
3. a viewer or renderer can load unverified mutable bytes under a citable link;
4. a figure receipt does not bind source bundle, view recipe, viewer build, renderer fingerprint, and output digest;
5. the catalog path requires one code change, Firestore document, CI job, or pre-rendered movie per run;
6. the system labels an NEB image index as time or temperature.

## What is wrong with the initial P1-P5 plan

The initial plan proved that Lupi can load and replay a path-16 extxyz payload. That was the right prototype. Its proposed production path has four category errors.

First, the structure sequence and thermo table are attached separately. This permits a valid geometry file to be paired with the wrong profile. It also makes manual drop-zone behavior part of the scientific record.

Second, the plan treats `scienceDataCatalog.ts` as a general catalog contract. The current type is intentionally narrow: Zenodo, `lammps-dump|lammps-data`, CC-BY-4.0, and source-coordinate metadata. It cannot express multi-file computation bundles, arbitrary provenance, quality states, energy-series semantics, or a million records.

Third, a saved-view slug or MP4 is treated as evidence. Both are presentation state. Current saved-view schema v1 is mutable and does not bind payload, profile, catalog version, or viewer build. A movie also cannot expose missing values, source provenance, or later inspection. The citable record is the immutable science bundle plus a digest-bound render receipt.

Fourth, "MCP automation later" assumes capabilities that do not exist as one end-to-end path. The browser MCP exports deterministic PNG/JPEG/WebP/GLB, not MP4. Browser capture yields WebM on Chromium/Firefox. The legacy remote renderer accepts local template/procedural molecules, PNG only, and no view override. Its live health contract reports atoms-only rendering and validation-only `render-request-v1`. D1 and Queue are reserved/commented future configuration, not provisioned services.

One UI bug is scientifically dangerous now: `ThermoMinimap` requests `Temp`, then falls back to the first numeric column. In the Z1 sidecar that column is `TimeStep`, used here as image index, so the viewer applies a temperature-like blue-to-red map to image number. Z1 needs first-class energy and T1 panels. The thermo minimap is not an acceptable substitute.

## Scientific display contract

### Per-path view

A path view must let a reader inspect the mechanism and audit the stated barrier without opening another file.

#### Geometry

- Show `image i of n`, the declared cell and PBC state, and stable atom IDs.
- Identify the migrating atom or atoms. Unwrap periodic motion with a declared minimum-image convention so a hop does not jump across the cell on screen.
- Provide endpoint, saddle, and final-state small multiples alongside synchronized playback.
- Mark whether bonds are source topology or viewer inference. When mechanism interpretation depends on coordination, show the actual distances or coordination values rather than relying on drawn bonds.
- Store the wrapped source coordinates and any unwrapped display coordinates separately.

#### Reaction coordinate and energy

- Use image index and, when available, a declared cumulative path coordinate. State the formula and units for an arc-length or mass-weighted coordinate.
- Plot model, sparse GPAW anchors, dense GPAW extension, and VASP reference as separate series. State the zero convention for each curve; retain absolute values in the bundle even if the display uses each engine's path minimum.
- Use filled points for evaluated anchors, outlined marks for nominations, a distinct mark for union-only anchors, and explicit tags for dense-extension values. Missing values remain missing; a line must not turn them into observations.
- Mark each series' argmin and argmax, the tie rule, barrier-defining pair, and barrier.
- Show guidance misses and the same-engine deficit. The view should state the subset theorem used by Z1: exact recovery follows when the evaluated set contains both dense-profile extrema.
- Show model failure and abstention with the denominator. Path 14 must remain visible as an all-guides-failed case rather than disappearing from an average.

#### Convention wander and diagnostics

- Plot the per-image offset `E_GPAW(i) - E_VASP(i)`.
- Display T1 wander, threshold, verdict, and driver pair, linked to the relevant geometry frames.
- Make same-engine evidence primary. Cross-engine evidence is secondary and visibly marked contaminated when the wander gate fails.
- Include SCF status, iterations/residual, gap, Fermi level, smearing/occupations, and spin policy when a bound diagnostic source supplies them. Do not infer them from `z1-union-campaign.json`. In particular, any path-0 gap/SCF panel must bind its separate diagnostic receipt.

The verified Z1 campaign has 23 active paths and 129/129 evaluated anchors. All four model summaries are `strong_win` on the same-engine basis. Path 16 has cross-engine error 32.7296928566 meV but wander 117.271678515 meV, so its cross-engine result is contaminated under the 40 meV gate. Path 0 has wander 4212.33092634 meV with driver images [0, 3]. Path 14 has no guiding models and uses dense extension. Path 27 is the sole clean path. These are acceptance fixtures, not optional gallery examples.

### Campaign views

A million-run system should default to summaries and frozen selection policies, not one million movies.

Required campaign-level outputs are:

1. a completeness matrix by path and model, including failed, deferred, partial, quarantined, superseded, and retracted records;
2. barrier comparisons with signed residuals, identity line, threshold bands, and honest denominators;
3. extrema/anchor guidance quality: exact and ±1 image capture, anchor-set size, and same-engine deficit;
4. union economics: naive versus union anchor counts and marginal growth as models are added;
5. T1 wander distribution and barrier-error-versus-wander view, with clean/contaminated status and the error bound shown;
6. mechanism outliers selected by a versioned rule, such as maximum wander, maximum guidance deficit, all guides failed, or only clean path;
7. an image-resolution and convergence audit, including image count/spacing and achieved force convergence.

The present dense extensions have at most seven images. Sparse and dense agreement therefore has limited power by construction. Do not generalize it as broad sparse-DFT validation until longer, better-resolved paths have been tested.

## Canonical bundle contract

Add these files in `lupine-rhizo` during phase 1:

- `schemas/visualization/lupine.visualization-bundle.v1.schema.json`
- `schemas/visualization/lupine.figure-recipe.v1.schema.json`
- `tools/analysis/build_visualization_bundle.py`
- `python/tests/test_visualization_bundle.py`

The manifest is canonical JSON. `bundle_id` is a SHA-256 over canonical manifest content with the identity field omitted during hashing. Zero-based image indices are mandatory.

Minimum fields:

```text
schema, bundle_id, campaign_id, campaign_version, run_id, path_id
created_at, status, supersedes, retraction
source_artifacts[]: role, uri, bytes, sha256, schema, git_commit
producer: tool, version, git_commit, container_digest, normalized_parameters
method: engine, code/version, XC, PAW/pseudopotentials, basis/grid/cutoff,
        k-points, charge, spin, occupations/smearing, convergence,
        NEB optimizer/tangent/springs/climbing image/fmax/steps/endpoints
model_provenance[]: model, checkpoint digest/source, package/version,
                    dtype, device, receipt digest, failure reason
coordinates: units, per-frame lattice, PBC, stable atom IDs/species/order,
             wrapped convention, optional unwrapped convention,
             migrating atom IDs, reaction-coordinate definition/values
series[]: quantity, engine/model, absolute/relative, unit, zero convention,
          values, per-value status, source artifact and JSON pointer
selection: rule ID/version, extrema and tie policy, nominated/union/evaluated/
           dense-extension sets, guidance misses and deficits
quality_gates: thresholds, denominator policy, same/cross-engine results,
               T1 offset series/wander/driver pair/verdict
assets[]: role, media type, format, bytes, sha256, object URI
provenance: creators, organization, citation, license, source revision,
            preregistration, amendments, claim/evidence IDs
quality: complete|partial|invalid|quarantined|verified|published, checks, warnings
```

Represent missingness with a status and optional null value, never undocumented NaN or Infinity. Keep raw, normalized, derived, and presentation layers separate. Every derived scalar must be recomputable from the stored arrays. A corrected view or caption mints a new recipe; changed science bytes mint a new bundle. Supersession and retraction edges preserve the history without mutating cited objects.

For Z1 the converter must bind both `data/candidates/z1-union-campaign.json` and the coordinate-bearing `data/candidates/z1_nebdft2k_barriers.lock.json`. The verified files are 72,081 and 4,021,811 bytes, respectively. The campaign record does not contain coordinates.

`trajectory.extxyz` remains a parser-compatible display asset. The canonical scientific profile is JSON, not a LAMMPS thermo file. A temporary `.thermo` derivative may support the existing UI, but it must be labeled as a generated compatibility file and excluded from scientific identity.

### Validation and quarantine

The publisher fails closed on:

- hash, byte-count, schema, or finite-number failure;
- trajectory/profile frame mismatch;
- changed atom identity, species, or ordering across frames;
- absent/invalid cell or undeclared coordinate units;
- non-monotone declared path coordinate;
- derived extrema, barriers, anchor sets, guidance misses, or T1 quantities that do not recompute;
- evaluated anchors outside the allowed image set;
- missing source pointers for displayed values;
- a figure that points to a different bundle or frame digest.

Partial runs remain catalogable for completeness accounting but cannot become public figures. Unknown schema versions go to quarantine. Adapters are versioned code, not silent coercions.

## Storage and publication transaction

Use separate private ingestion/quarantine and public publication boundaries. A representative GCS layout is:

```text
objects/sha256/<first2>/<digest>.<ext>
bundles/<campaign>/<run>/<bundle-digest>/manifest.json
campaigns/<campaign>/<campaign-manifest-digest>.json
figures/sha256/<first2>/<artifact-digest>.<ext>
catalog-snapshots/<schema>/<snapshot-digest>.jsonl.zst
aliases/runs/<run-id>.json
aliases/campaigns/<campaign-id>.json
aliases/views/<slug>.json
```

Immutable objects are create-only with `ifGenerationMatch=0`. Upload and verify all assets first, upload the bundle manifest last, then emit `bundle.published.v1` and update the index. The idempotency key is the ordered source-artifact digests, converter version, and canonical normalized options. A replay returns the existing bundle.

Aliases contain only a target digest/revision and generation. They are discovery conveniences, not citation targets, and updates require generation preconditions plus an audit record. Published/cited objects do not expire. Raw, staging, failed-render, and unpromoted assets receive explicit lifecycle policies.

A reconciler checks manifest-to-object reachability, size/digest metadata, orphaned objects, index lag, stale aliases, and invalid retention state. It must be able to rebuild the query index from immutable manifests.

Serve public bytes by exact content-addressed paths with Range, `ETag`, `Cache-Control: public,max-age=31536000,immutable`, `nosniff`, and the exact content type. Verify hashes during publication and audit; do not full-buffer and rehash every ranged object at the edge. The current research proxy's 16 MiB full-buffer path remains appropriate only for its small curated external records.

## Catalog and discovery

The source of truth is the immutable set of bundle and campaign manifests. The browser never lists a bucket and never downloads a global manifest.

Phase 2 can begin with sharded immutable JSONL snapshots, for example 10,000 records per shard plus a small root index. Before interactive holdings exceed roughly 10,000 records, add a paginated runtime API:

```text
GET /v1/runs?campaign=&cursor=&limit=&elements=&quality=&model=
GET /v1/bundles/<bundle-id>
GET /v1/campaigns/<campaign-id>
```

Use cursor pagination, a maximum page size of 100, ETags, and cached immutable bundle responses. Keep a columnar/BigQuery index for analytics and reconciliation. Choose the online lookup store only after the owner sets query facets and ownership. D1 is not available today merely because future bindings appear in configuration; it would need provisioning and an operational owner.

`scienceDataCatalog.ts` may receive one curated "Z1 Union Campaign" record that points to the campaign collection. It must not mirror paths or runs.

## Lupi integration

Add a run-manifest provider separate from the current Zenodo research provider. One load operation resolves and verifies the manifest, trajectory, profile, annotations, and named view. Manual sidecar attachment is not a production path.

The first-class science panel displays:

- campaign/run/path and exact bundle revision;
- source digest, quality state, and citation;
- image index/reaction coordinate and current-frame energies;
- series identity, units, and zero convention;
- anchors, extrema, guidance misses, dense extension, and model failures;
- T1 offset/wander/threshold/verdict/driver pair;
- explicit parser warnings and source-versus-inferred visual features.

Loading fails closed on a bad digest, redirect, media type, frame count, profile length, or atom identity. Extend remote URL policy only for exact Lupine content-addressed paths, with tests for redirects, query strings, malformed digests, and wrong extensions. A same-origin `lupi.live/v1/artifacts/sha256/...` route is preferable to opening an arbitrary bucket prefix.

The locally inspected Lupi source was commit `80997f80071859c30bf191795eb035b6c12142bf`. The live release reported by health was newer (`ef40d830334d0870febc48b1ae08e007e2ca8cab`). Recheck both source and live capability at implementation time rather than treating either snapshot as permanent.

## Saved views and citation identity

Saved view v2 is an immutable figure recipe:

```text
source: bundle ID, manifest SHA-256, trajectory/profile SHA-256,
        catalog record version
viewer: Lupi git commit/build ID, canonical-view schema version
frame: image index, decoded frame digest v3
science_overlay: visible series and annotation IDs, profile digest
view: camera, cell/bond/filter/color/layer state, dimensions
```

The recipe ID is `sha256(canonical recipe JSON)`. Friendly slugs are aliases to recipe revisions. Loading verifies every bound digest and rejects or warns on unsupported viewer schema.

Public reads remain anonymous. Firebase Google/GitHub sign-in can continue for human/community authoring, but existing mutable `lupiViews` must remain separate from reviewed `publishedViews`. Backend publication requires an editor/reviewer gate and records owner, reviewer, source manifest, recipe digest, viewer build, timestamps, and supersedes relation. Automation uses workload identity and service accounts, never a personal browser credential.

## Figure and movie production

Treat each publication artifact as a build product. The render key is:

```text
sha256(bundle digest + canonical view recipe + renderer fingerprint + output contract)
```

Run a pinned container with the chosen Lupi build, Chromium, fonts, chart compositor, and ffmpeg. Use browser MCP for deterministic state setting and frame export where its contract supports it. Compose axes, legends, scientific annotations, and profile panels outside the WebGL canvas, then encode a pinned frame sequence to MP4. Do not call browser MediaRecorder output reproducible MP4.

The receipt records source/recipe/spec IDs, decoded frame digest v3, viewer build, renderer/container/font/GPU fingerprint, output SHA-256, dimensions, frame rate, codec, command versions, timestamps, and logs. CPU and GPU rendering may need separate accepted fingerprints. Golden fixtures use an explicit pixel tolerance if cross-machine identity is not chosen.

Start with qualified PNG. Add MP4 only after headless trajectory loading, overlays, cell/bonds/annotations, and receipt execution pass end to end. Current live renderer capability is atoms-only PNG and does not execute `render-request-v1`; do not promise more before closing that gap.

Render lazily for policy-selected flagship, extrema, failure, aggregate, or article records. Do not pre-render one or more derivatives for every run. GitHub Actions validates schemas, converter determinism, and a small golden render set, then dispatches work. A bounded asynchronous worker fleet handles rendering with idempotency, retries, a dead-letter queue, per-campaign quotas, and cached success.

MCP remains an operator and debugging interface. It is not the event bus, state machine, or correctness boundary.

## Hosting, auth, and operations

Use `lupi.live` for the UI and control surface. Its exact-SHA deploy, candidate verification, promotion, rollback, and reconciliation path is already more mature than a new host. An optional `viewer.lupine.science` 308 redirect can provide branding after collection routes are stable.

A self-hosted second viewer is deferred unless one of these conditions becomes true:

- Lupi cannot accept the manifest/science-panel changes;
- required data-governance or embargo boundaries cannot be enforced;
- availability or release ownership becomes contractually unacceptable.

Operational requirements before broad publication:

- SLOs for UI availability, artifact fetch latency/success, catalog freshness, publication latency, and render queue age/success;
- metrics for accepted/rejected bytes, immutable-copy conflicts, index lag, alias failure, Range/cache behavior, auth error class, render cache/retry/DLQ/seconds, and campaign spend;
- no run ID as a metric label;
- alerts and runbooks for checksum mismatch, missing object, CORS/Range regression, auth callback failure, rule denial/spam, stale alias, queue age/DLQ, renderer drift, egress spikes, and viewer rollback;
- GCS versioning/retention for manifests and published aliases, scheduled Firestore export, and tested index rebuild;
- quarterly restore/reindex and cited-view replay drills;
- synthetic anonymous deep-link, exact-frame/digest, Range 206, ETag, unauthorized-publisher, and canonical-render checks.

## Scale and cost

### At 100 runs

Manual profile attachment, hand-authored TypeScript records, slug creation, and screenshot QA already become unreliable. The bundle validator, campaign manifest, and exact source binding must exist before this point.

### At 10,000 runs

Repository catalogs, full JSON listings, per-run Git commits/Actions, Firestore as a run registry, bucket scans, and synchronous edge hashing become bottlenecks. Runtime pagination, event idempotency, a DLQ, and reconciliation must already be in production.

### At 1,000,000 runs

Storage/object count, index hot keys and pagination, egress, retention, renderer quota, DLQ replay, and cardinality-safe observability dominate. Separate "all validated runs are searchable" from "selected runs have rendered figures." Use aggregate summaries and on-demand geometry.

Illustrative storage, using a regional Standard GCS rate near $0.020 per GB-month, is:

| retained bytes per run | total for 1M runs | approximate storage/month |
|---:|---:|---:|
| 0.25 MB | 250 GB | $5 |
| 1 MB | 1 TB | $20 |
| 5 MB | 5 TB | $100 |
| 25 MB | 25 TB | $500 |

These are planning examples, not a quote. Region, operations, replication, retrieval, public egress, and rendering may dominate. Measure bytes, requests, cache hit rate, egress, CPU-seconds, and cost labels per campaign. The budget equation is

`retained_GB × storage_rate + uncached_egress_GB × egress_rate + operations + render_vCPU_s + render_RAM_s`.

A 10 MB movie for every run adds 10 TB before views or replicas and should be rejected as a default.

## Phased rollout and acceptance gates

### Phase 0: science contract and golden bundles

Deliver the two schemas, deterministic converter, validator, and bundles for paths 16, 0, 14, and 27. Build first-class energy/T1 panel prototypes; do not use the thermo minimap.

Gate: two independent builds produce byte-identical canonical manifests and regenerate every source-derived scalar. Corruption, off-by-one profiles, reordered atoms, bad units, and source-hash changes are rejected. Path-0 electronic diagnostics are absent unless separately bound.

### Phase 1: content-addressed publisher

Implement create-only object upload, asset-first/manifest-last publication, quarantine, aliases with generation preconditions, and reconciliation. Publish the four golden bundles privately, then two public canaries.

Gate: replay is idempotent; an interrupted publication is not discoverable; index rebuild and object/alias reconciliation pass; exact Range and cache behavior are tested.

### Phase 2: runtime catalog and manifest-native Lupi load

Ship sharded snapshots or a small paginated index, the run-manifest provider, exact URL policy, and first-class science panel. Add one curated Z1 campaign entry rather than per-run TypeScript rows.

Gate: an anonymous user opens a digest-pinned path and receives the correct structure, profile, anchor/extrema marks, quality state, T1 verdict, and citation in one operation. Mismatched assets fail closed.

### Phase 3: saved-view v2 and Library links

Implement immutable recipe IDs, reviewed publication revisions, mutable aliases, anonymous reads, and editor-controlled promotion. Link Library records to exact revisions.

Gate: changing an alias cannot change a cited revision; an old cited view still loads after viewer rollback; unsupported schema/build combinations are explicit.

### Phase 4: reproducible figures

Render digest-bound PNGs for the golden set in a pinned environment. Add MP4 after deterministic frame-sequence encoding and complete overlay support. Store receipts and compare golden artifacts.

Gate: cached replay returns the same artifact key; source, recipe, or renderer changes mint a new key; captions and figures identify denominator and frozen selection rule.

### Phase 5: campaign integration

Connect a `run.completed` or campaign-finalized event to conversion and publication through an idempotent queue. Add bounded concurrency, retries, DLQ, quotas, SLOs, alerts, and cost telemetry. Promote only policy-selected records and derivatives.

Gate: duplicate/out-of-order events, late files, schema drift, queue saturation, renderer failure, and index outage have tested recovery paths. No personal OAuth or manual browser step is required.

## Owner decisions required

1. Confirm `lupi.live` as canonical, with `viewer.lupine.science` redirect-only unless a documented fork trigger is met.
2. Decide whether all validated runs are publicly searchable, only promoted runs are public, or campaigns can be embargoed. Set raw/staging retention at the same time.
3. Choose online index ownership and required query facets before 10,000 records. Options include a provisioned Lupi D1 service or an existing Lupine evidence/catalog database; BigQuery remains the analytics/rebuild index.
4. Name the publisher/reviewer group and define what makes a view revision citable. GCS identity is reproducible but not archival; decide whether selected releases also receive Zenodo/DataCite identity.
5. Set the render policy and initial campaign budgets: which frozen rules select PNG/MP4 derivatives, and what storage/egress/render ceiling applies.
6. Choose the reproducibility target: pixel-identical across machines or identical only within a declared renderer fingerprint and tolerance.

## Explicitly rejected alternatives

- One `scienceDataCatalog.ts` entry per run. It couples science publication to frontend builds and fails far below one million records.
- One giant campaign manifest. It becomes a hot mutable object and forces whole-campaign transfer for one path.
- Manual structure/profile attachment. It permits scientifically wrong pairings.
- Mutable `latest` URLs or friendly slugs as citations. They do not identify bytes.
- A Firestore saved view for every run. A view is authored presentation state, not run identity.
- One Git commit, GitHub Actions job, or pre-rendered PNG/MP4 per run. It creates avoidable control-plane and storage costs.
- Full-payload SHA-256 verification inside the edge Worker on every cache miss. Verify at ingest, use immutable digest paths, and preserve streaming Range requests.
- Static-figure-only publication. Figures are article derivatives, not inspectable records.
- A self-hosted viewer fork now. It duplicates a product surface before the data contract exists.
- Personal Firebase/OAuth credentials in automation. Use workload identity and audited backend publication.
- MCP or an LLM as the workflow state machine. Use deterministic schemas, event IDs, conditional writes, queues, and reconciliation.
- Calling NEB playback a time trajectory or reusing the temperature minimap for image-indexed energies.

## Evidence and traceability

This plan synthesizes Kanban swarm root `t_cc461bc2`, worker tasks `t_f442712c`, `t_b2fa688e`, and `t_28beef7c`, and verifier gate `t_de5e3b92`. The verifier passed the gate against Lupi commit `80997f80071859c30bf191795eb035b6c12142bf`, Lupine-rhizo commit `4e0a7c33585eb1af6cda74cb30e8cbab5ad734ce`, and the live Lupi health contract.

Repository sources checked by the swarm include:

- `data/candidates/z1-union-campaign.json`
- `data/candidates/z1_nebdft2k_barriers.lock.json`
- `docs/analysis/z1-union-campaign-verdict.md`
- `docs/analysis/z1-union-anchor-economics.md`
- `docs/analysis/t1-wander-gate.md`
- `docs/analysis/t1-wander-mechanism.md`
- Lupi `packages/core/src/scienceDataCatalog.ts`
- Lupi `packages/ui/src/molecules/providers/research.ts`
- Lupi `packages/ui/src/ThermoMinimap.tsx`
- Lupi `packages/ui/src/savedViews.ts`
- Lupi `packages/ui/src/remoteMoleculeUrlPolicy.ts`
- Lupi `packages/ui/src/renderArtifactSource.ts`
- Lupi `apps/mcp-worker/src/scienceData.ts`
- Lupi `apps/web/public/browser-mcp-manifest.json`
- Lupi `apps/render-backend/src/protocol.mjs`
- Lupine-rhizo `cloudflare/cdn-proxy/src/worker.ts`

Scientific framing follows climbing-image and improved-tangent NEB conventions: Henkelman, Uberuaga, and Jónsson, *J. Chem. Phys.* 113 (2000), DOI `10.1063/1.1329672`; Henkelman and Jónsson, *J. Chem. Phys.* 113 (2000), DOI `10.1063/1.1323224`. Record design should remain compatible with FAIR's machine-actionable principles: Wilkinson et al., *Scientific Data* 3, 160018 (2016), DOI `10.1038/sdata.2016.18`.

---

## Codex review notes (2026-08-01, appended at merge)

Open design items carried into the next revision (VIS-3 implementation):

1. **Exact canonical encoding** (Codex P1): the bundle's canonical byte form needs a normative spec — field order, float precision, coordinate frame, and digest domain separation for manifest vs. assets vs. derivatives. To be fixed in the `lupine.visualization-bundle.v1` schema itself.
2. **Durable publication wiring** (Codex P1): the publisher's write order (assets → index → manifest-last) must be implemented against the GCS content-addressed layout with the query-index update as a separate, recoverable step; reconciliation on partial failure is required.
3. **Deterministic `created_at`** (Codex P2): bundle timestamps derive from source content, not wall clock, so identical inputs yield identical digests.
4. **Compatibility derivatives** (Codex P2): figure/movie derivatives live in a separate tree with their own digests; the manifest references, never embeds.
5. **Bundle tooling phases** (Codex P2): builder → validator → publisher ship as separate tools so the contract is checkable before publication exists.

These do not change the plan's direction; they define the precision the first implementation (VIS-3) must reach.
