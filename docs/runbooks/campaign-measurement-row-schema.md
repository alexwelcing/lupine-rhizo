# Campaign measurement-row input contract

`tools/ingest_campaign_results.py` consumes newline-delimited JSON (JSONL). Each
nonblank line must decode to one JSON object. The file must contain at least one
row. There is no separate JSON Schema for an input row; this document records
the contract enforced by the ingester and by the EvidenceBundle validation it
runs before writing anything.

A passing one-row example is committed at
`python/tests/fixtures/round4_ingest/measurements-minimal.jsonl`. Its referenced
manifest and artifact are in the same fixture directory.

## Row fields

Every row needs the following fields. Unless stated otherwise, a string must be
nonempty after trimming for the check, although the original string is retained.

| Field | Required type/value | Meaning and validation |
| --- | --- | --- |
| `row_id` | nonempty string, unique in the file | Identifier used in diagnostics and the generated filename. |
| `campaign_manifest_hash` | string equal to `manifest.content_hash` | Binds the row to the manifest's canonical content, not to the manifest file bytes. |
| `previous_row_hash` | `null` on row 1; prior row's `row_hash` thereafter | Orders all nonblank rows into one unbroken hash chain. |
| `row_hash` | `sha256:` plus 64 lowercase hex digits in practice | Must equal the canonical content hash of the complete row with only `row_hash` omitted. The comparison, rather than a separate regex, enforces its shape. |
| `claim_id` | nonempty string | Must name a ClaimContract in `registry/claims/<claim_id>.json` and appear in the manifest's `target_premises`. |
| `premise_id` | nonempty string | Must identify exactly one premise in that ClaimContract and pair with `claim_id` in the manifest. |
| `claim_predicate` | nonempty string | Must exactly match a predicate from one of the premise's baseline EvidenceBundles. |
| `epistemic_status` | one of `confirmatory`, `exploratory`, `descriptive`, `negative`, `unsupported` | Copied to the generated EvidenceBundle. |
| `scope` | object described below | Must be nonempty, schema-valid, and no broader than the union of baseline bundle scopes. |
| `artifact` | nonempty repository-relative path | Resolved below `--root`; the resolved file must remain inside that root and must exist. Absolute paths are accepted only if they resolve inside the root. |
| `artifact_hash` | `sha256:` plus exactly 64 lowercase hex digits | SHA-256 of the artifact's exact bytes. |
| `run_id` | nonempty string | Copied to the generated evidence reference. |
| `thresholds_version` | nonempty string | Names the threshold policy used by the run. The ingester does not resolve or compare this value to the manifest. |
| `provenance` | object | Requires nonempty string members `agent`, `human`, and `timestamp`. Extra input members are ignored when building the bundle, but still affect `row_hash`. |

The row object itself does not reject additional properties. Every additional
property is covered by `row_hash`, but is otherwise ignored unless it is one of
the fields above. In particular, a top-level `measurements` member is hashed but
is not copied into the generated EvidenceBundle.

### Scope

`scope` must contain exactly the members accepted by the EvidenceBundle schema:

- `structures`, `chemistries`, and `properties`: nonempty arrays of unique,
  nonempty strings. Each value must occur in the corresponding dimension of at
  least one baseline EvidenceBundle referenced by the target premise.
- `conditions`: a nonempty object. Values may be a nonempty string, number,
  boolean, or a nonempty array containing those scalar types. Condition names
  and values are not compared with baseline conditions.

The ingester's initial scope check does not reject extra scope members, but the
subsequent EvidenceBundle schema validation does (`additionalProperties` is
false).

## Measurement values and units

Rows are receipts around an artifact, not a validated tabular scientific
measurement schema. The ingester never opens or validates the artifact as JSON;
it only hashes its exact bytes. It also does not evaluate the campaign's
acceptance, kill, or demotion thresholds.

Consequently there is currently **no ingester-enforced field for an individual
adsorption energy**. For the Z3 campaign, the manifest expresses the aggregate
acceptance statistic as:

- metric: `adsorption_energy_mae`
- threshold: numeric `0.1`
- unit: the exact string `eV`

A row can preserve the aggregate result in `scope.conditions`, for example
`"adsorption_energy_mae": 0.08` and `"adsorption_energy_unit": "eV"`, but the
unit is convention only and the ingester does not cross-check either value. Any
per-observation adsorption energies, reference uncertainties/tolerances,
facets, coverages, temperatures, reconstruction states, and reference-state
conventions must live in the content-addressed artifact. Their artifact-level
shape and units are outside this ingester's validated contract.

The EvidenceBundle schema has a typed `measurements` form only for the predicate
`barrier_mae_mev<=40`: metric `barrier_mae`, nonnegative numeric `value`, unit
`meV`, an acceptance test, and a positive sample count. The current ingester does
not propagate a row's `measurements` member, so it cannot ingest that predicate
successfully without code changes.

## Content addresses

All semantic content addresses use the implementation below (described by the
schemas as RFC-8785-compatible canonical JSON):

1. serialize as UTF-8 JSON with object keys sorted, no insignificant whitespace,
   and non-ASCII characters emitted directly;
2. SHA-256 the resulting bytes;
3. prefix the lowercase hexadecimal digest with `sha256:`.

In Python this is `json.dumps(value, ensure_ascii=False, separators=(",", ":"),
sort_keys=True).encode("utf-8")` followed by SHA-256.

The hashes cover different payloads:

| Hash | Payload |
| --- | --- |
| Manifest `content_hash` | Complete manifest object with only `content_hash` omitted. |
| Row `row_hash` | Complete row object with only `row_hash` omitted, including `previous_row_hash` and any unknown fields. |
| ClaimContract `content_hash` | Complete claim object with only `content_hash` omitted. It is checked before ingestion and recomputed after bundle references are appended. |
| EvidenceBundle `bundle_id` | Complete generated bundle before `bundle_id` is added. The row's chain fields and `row_id` are not part of the bundle. |
| Row `artifact_hash` | SHA-256 of the artifact's exact file bytes, not canonical JSON. |
| Generated `campaign_manifest_hash` evidence reference | SHA-256 of the manifest's exact file bytes, not `manifest.content_hash`. |

The last distinction means reformatting a manifest without changing its semantic
`content_hash` leaves row bindings valid but changes the manifest-byte hash in a
newly generated EvidenceBundle.

## Manifest, ClaimContract, and baseline-reference rules

Before rows are materialized, the ingester enforces all of the following:

- the manifest passes `schemas/campaign-manifest.v1.schema.json`, has version 1,
  has a correct `content_hash`, and contains nonempty unique target pairs;
- every declared target pair receives at least one row, and no row targets an
  undeclared pair;
- the ClaimContract passes its schema and has a correct `content_hash`;
- the target premise exists exactly once and already has at least one
  `bundle_references` entry;
- every referenced baseline bundle exists under `evidence/v1/examples`, passes
  the EvidenceBundle schema, and has a canonical `bundle_id`;
- each row's predicate matches a baseline predicate and its three scope arrays
  are subsets of the union of baseline scopes;
- generated bundle filenames do not overwrite different existing content; and
- the complete staged assumption registry and lock can be generated before any
  repository files are changed.

The Z3 manifest and ClaimContract both use the governing premise ID
`hard_materials_z3_adsorption_mae`. The premise cites the pre-execution CatBench
baseline bundle, whose scope is the locked panel's 32 structures and 96 component
systems. A Z3 measurement row can therefore pass the ingester's baseline,
`adsorption_energy_mae<=0.1` predicate, and scope gates before it is materialized.

## Reproducing the passing example safely

The CLI has no `--dry-run` switch: a successful direct invocation writes bundles,
ClaimContracts, and generated registry files below `--root`. Use the test harness
for a non-mutating checkout-level verification.

The unit test copies registry, evidence, manifest, artifact, and rows into a
temporary root before invoking the CLI, so the checked-out registry is not
modified:

```sh
python3 -m unittest \
  python.tests.test_ingest_campaign_results.CampaignResultIngestionTests.test_documented_minimal_measurement_row_ingests
```

To compute or refresh a row chain, process rows in file order. Set the first
`previous_row_hash` to JSON `null`; for every later row set it to the prior
computed hash. Then compute each `row_hash` last, omitting only its own
`row_hash` field from that row's canonical payload.
