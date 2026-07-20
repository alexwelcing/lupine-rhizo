# Campaign result ingestion contract

This document specifies the contract implemented by
`tools/ingest_campaign_results.py` at commit `2a18abb`. It distinguishes fields
that the ingester validates from conventions used by campaign producers. The
input rows do not have their own JSON Schema; validation is assembled in Python
and, for data copied into a generated EvidenceBundle, by
`evidence/v1/schema.json`.

## 1. Inputs and file granularity

The command has exactly three arguments:

```text
python3 tools/ingest_campaign_results.py \
  --root <repository-root> \
  --manifest <manifest.json> \
  --measurements <rows.jsonl>
```

`--manifest` and `--measurements` are required. `--root` defaults to the parent
of `tools/` (`tools/ingest_campaign_results.py:416-421`). Paths are resolved to
absolute paths before ingestion (`tools/ingest_campaign_results.py:424-429`).

The measurements input is **one JSON Lines file**. Each nonblank physical line
must decode as one JSON object; blank lines are skipped; at least one row is
required (`tools/ingest_campaign_results.py:58-76`):

```python
lines = path.read_text(encoding="utf-8").splitlines()
...
if not line.strip():
    continue
row = json.loads(line)
if not isinstance(row, dict):
    raise ValueError(...)
...
if not rows:
    raise ValueError("measurement input contains no evidence rows")
```

There is no alternate batch JSON array/object format and no per-candidate CLI
mode. A multi-candidate batch is represented by multiple JSON-object lines in
one JSONL file. A single candidate is represented by a one-line JSONL file. The
chain covers all nonblank rows in file order, even when rows target different
premises (`tools/ingest_campaign_results.py:209-227`).

## 2. Exact row contract

A top-level row is an open object: the ingester does not reject unknown members.
Unknown members participate in `row_hash` but are otherwise ignored. The one
exception is that the known measurement members described below may be copied
into the generated EvidenceBundle. This follows directly from hashing the
complete dictionary except `row_hash` (`tools/ingest_campaign_results.py:221-224`)
and constructing the bundle from a fixed field list
(`tools/ingest_campaign_results.py:246-296`).

Unless a row value is subsequently constrained more tightly, “nonempty string”
means `isinstance(value, str)` and `value.strip()` is truthy. The original,
untrimmed value is retained (`tools/ingest_campaign_results.py:111-115`).

### Required top-level members

| Member | Accepted JSON type/value | Enforced meaning | Code reference |
| --- | --- | --- | --- |
| `row_id` | nonempty string | Unique among all rows in this input file. It is used in diagnostics and the generated filename. | `tools/ingest_campaign_results.py:212-216`, `:299-301` |
| `campaign_manifest_hash` | value exactly equal to the manifest’s `content_hash` string | Semantic binding to the selected manifest. This is not a hash of manifest file bytes. | `tools/ingest_campaign_results.py:217-218`, `:304-308` |
| `previous_row_hash` | JSON `null` on the first nonblank row; exact preceding computed `row_hash` string on every later row | Forms one ordered chain over the file. | `tools/ingest_campaign_results.py:209-227` |
| `row_hash` | exact computed string `sha256:<64 lowercase hex>` | Content address described in section 5. Shape is enforced by equality to the computed value rather than a separate regex. | `tools/ingest_campaign_results.py:221-227` |
| `claim_id` | nonempty string | Together with `premise_id`, must be a pair declared exactly once in `manifest.target_premises`; resolves `registry/claims/<claim_id>.json`. | `tools/ingest_campaign_results.py:310-332`, `:152-164` |
| `premise_id` | nonempty string | Must identify exactly one premise in the selected ClaimContract. Every manifest target pair must receive at least one row. | `tools/ingest_campaign_results.py:310-332`, `:336-348` |
| `claim_predicate` | nonempty string | Must exactly equal a predicate in one of the target premise’s baseline EvidenceBundles. | `tools/ingest_campaign_results.py:349-356` |
| `epistemic_status` | one of `confirmatory`, `exploratory`, `descriptive`, `negative`, `unsupported` | Copied into the generated EvidenceBundle. | `tools/ingest_campaign_results.py:35-41`, `:252-255` |
| `scope` | object; exact nested contract below | Copied into the bundle and must be no broader than baseline evidence for three dimensions. | `tools/ingest_campaign_results.py:134-149`, `:197-206`, `:349-360` |
| `artifact` | nonempty string resolving to a file inside `--root` | The path is joined to `--root`, resolved, and recorded in POSIX repository-relative form. An absolute path works only if it resolves inside `--root`. The file must exist. | `tools/ingest_campaign_results.py:104-108`, `:256-262` |
| `artifact_hash` | `sha256:` followed by exactly 64 lowercase hexadecimal digits | Must equal SHA-256 of the artifact’s exact bytes. | `tools/ingest_campaign_results.py:32`, `:89-95`, `:258-262` |
| `run_id` | nonempty string | Copied into the generated evidence reference. | `tools/ingest_campaign_results.py:270-281` |
| `thresholds_version` | nonempty string | Copied verbatim. It is not resolved or compared with the manifest. | `tools/ingest_campaign_results.py:270-281` |
| `provenance` | object with `agent`, `human`, and `timestamp` as nonempty strings | Those three values are copied; `preregistration_id` is taken from the manifest, not the row. Unknown input provenance members are ignored except by `row_hash`. | `tools/ingest_campaign_results.py:263-290` |

`timestamp` is only checked as a nonempty string by the ingester. Although the
EvidenceBundle schema annotates it with `"format": "date-time"`
(`evidence/v1/schema.json:223-250`), the validator is constructed without a
`FormatChecker` (`tools/ingest_campaign_results.py:79-86`), so date-time syntax
is not enforced.

### `scope`

The generated bundle schema permits exactly these members
(`evidence/v1/schema.json:123-149`):

- `structures`: nonempty array of unique, nonempty strings.
- `chemistries`: nonempty array of unique, nonempty strings.
- `properties`: nonempty array of unique, nonempty strings.
- `conditions`: nonempty object. Each value must be a nonempty string, a JSON
  number, a boolean, or a nonempty array of those scalar types
  (`evidence/v1/schema.json:91-121`).

For each of the first three arrays, every value must be in the union of that
dimension across the premise’s referenced baseline EvidenceBundles
(`tools/ingest_campaign_results.py:167-206`). `conditions` keys and values are
not compared with baseline conditions. The Python precheck does not reject
extra `scope` members, but generated-bundle schema validation does because
`additionalProperties` is false (`evidence/v1/schema.json:123-149` and
`tools/ingest_campaign_results.py:359-360`).

### Optional typed measurements

There are two mutually compatible input representations:

1. Canonical: optional top-level `measurements`. If the key exists, its value is
   copied unchanged.
2. Legacy: top-level `metric`, `value`, `unit`, `acceptance_test`, and
   `sample_count`. If none exists, no legacy measurement is generated. If any
   exists, all five are required and are assembled into a one-element array.

Canonical `measurements` takes precedence when both representations are present
(`tools/ingest_campaign_results.py:230-243`). Legacy fields remain covered by
`row_hash` even when canonical `measurements` takes precedence.

Any generated `measurements` value must pass this exact schema
(`evidence/v1/schema.json:50-55`, `:196-221`):

| Member | Required value/type |
| --- | --- |
| `measurements` | array with at least one element |
| element `metric` | exact string `barrier_mae` |
| element `value` | JSON number greater than or equal to 0 |
| element `unit` | exact string `meV` |
| element `acceptance_test` | object with no extra members |
| `acceptance_test.comparator` | exact string `less_than_or_equal` |
| `acceptance_test.threshold` | JSON number greater than or equal to 0 |
| `acceptance_test.outcome` | `pass` or `fail` |
| element `sample_count` | integer greater than or equal to 1 |

For predicate `barrier_mae_mev<=40`, `measurements` is mandatory in the
generated bundle (`evidence/v1/schema.json:66-75`). For other predicates it is
optional, but if supplied it still must have the barrier-measurement shape above.

## 3. Manifest reference format

The input row does **not** require a `campaign_manifest` path member. The
manifest is selected by the CLI’s `--manifest <path>` argument. A row binds to
it only through:

```json
{"campaign_manifest_hash": "<manifest.content_hash>"}
```

The equality check is verbatim at `tools/ingest_campaign_results.py:217-218`:

```python
if row.get("campaign_manifest_hash") != manifest_hash:
    raise ValueError(f"measurement {row_id} is not bound to the campaign manifest")
```

A row may contain an extra `campaign_manifest` member as producer metadata, but
the ingester ignores it except when computing `row_hash`.

The generated EvidenceBundle reference is different. It is constructed as
(`tools/ingest_campaign_results.py:270-281`):

```python
{
    "campaign": manifest["campaign_id"],
    "campaign_manifest": relative_path(manifest_path, root, "campaign manifest"),
    "campaign_manifest_hash": bytes_hash(manifest_path),
    "run_id": ...,
    "artifact": relative_artifact,
    "artifact_hash": expected_artifact_hash,
    "thresholds_version": ...,
}
```

Therefore the generated `campaign_manifest` is the resolved, POSIX,
repository-relative path, and the generated `campaign_manifest_hash` is SHA-256
of the manifest’s exact file bytes. The manifest must resolve inside `--root`.
This byte hash is deliberately not the row’s semantic
`campaign_manifest_hash`/manifest `content_hash`.

The manifest itself must be a JSON object, pass
`schemas/campaign-manifest.v1.schema.json`, have version 1, have nonempty
`campaign_id` and `preregistration_id`, contain at least one target, and have a
valid semantic `content_hash` (`tools/ingest_campaign_results.py:48-55`,
`:118-131`). The complete schema-required manifest member list is in
`schemas/campaign-manifest.v1.schema.json:8-23`.

## 4. Units and conversions

The ingester performs **no unit conversion**. It does not inspect the artifact’s
scientific values, does not evaluate the manifest’s acceptance/kill/demotion
rules, and does not cross-check arbitrary unit strings in `scope.conditions` or
unknown row members. It only hashes artifact bytes
(`tools/ingest_campaign_results.py:89-95`, `:256-262`).

For the Z3 adsorption campaign, energy producers must supply adsorption energies
and the aggregate adsorption-energy MAE in **eV**. The governing manifest fixes
`adsorption_energy_mae <= 0.1 eV`
(`campaigns/v1/z3.campaign-manifest.v1.json:24-28`) and uses eV again for its
demotion threshold (`campaigns/v1/z3.campaign-manifest.v1.json:39-40`). This is
a producer/artifact contract, not a conversion enforced by this ingester. A row
or artifact expressed in meV will not be converted to eV by this tool; it must be
converted before the row and its hashes are produced.

The only typed row measurement currently accepted by the generated
EvidenceBundle schema is the unrelated barrier MAE form, whose unit is exactly
`meV` (`evidence/v1/schema.json:196-220`). Thus Z3 adsorption aggregates belong
in the content-addressed artifact and/or producer metadata such as
`scope.conditions`, not in the current typed `measurements` field.

## 5. Byte-for-byte hash reproduction

There are three distinct algorithms. Do not use one in place of another.

### 5.1 Row `row_hash`: RFC 8785 bytes

For each row in file order:

1. Parse that line with Python `json.loads` (`tools/ingest_campaign_results.py:63-73`).
2. Set `previous_row_hash` to JSON `null` for the first row, or to the preceding
   row’s computed hash for every later row.
3. Remove only the top-level member whose key is exactly `row_hash`. Include all
   other members, including unknown members, `previous_row_hash`, and
   `campaign_manifest_hash`.
4. Serialize the resulting object with `rfc8785.dumps`. RFC 8785 recursively
   sorts object property names by their UTF-16 code units, emits no insignificant
   whitespace, applies its specified JSON string and IEEE-754 number rendering,
   and encodes the result as UTF-8 bytes. Object insertion order therefore does
   not control the output; array order is retained.
5. Compute SHA-256 over those bytes, encode the digest as lowercase hexadecimal,
   and prefix `sha256:`.

The implementation is verbatim (`tools/ingest_campaign_results.py:219-227`):

```python
if row.get("previous_row_hash") != previous_hash:
    raise ValueError(f"measurement hash chain is broken at {row_id}")
canonical_row = rfc8785.dumps(
    {key: value for key, value in row.items() if key != "row_hash"}
)
actual_hash = "sha256:" + hashlib.sha256(canonical_row).hexdigest()
if row.get("row_hash") != actual_hash:
    raise ValueError(f"measurement row_hash mismatch at {row_id}")
previous_hash = actual_hash
```

A reproducer must use an RFC 8785 implementation, especially for floating-point
numbers and non-ASCII object keys. Merely calling generic `json.dumps(...,
sort_keys=True)` is not a byte-for-byte specification of this hash.

### 5.2 Semantic manifest, claim, and bundle hashes: project canonical bytes

The manifest `content_hash`, ClaimContract `content_hash`, and generated
EvidenceBundle `bundle_id` use the imported `content_hash` helper. Its exact
serialization is (`tools/generate_assumptions.py:23-30`):

```python
def canonical_bytes(document: Any) -> bytes:
    return json.dumps(
        document, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def content_hash(document: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(document)).hexdigest()
```

Consequently these hashes use Python’s `json.dumps` behavior, recursively sort
object keys by Python string (Unicode code-point) order, retain array order, emit
no spaces between tokens, emit non-ASCII characters directly, encode as UTF-8,
and use SHA-256 with the `sha256:` prefix. Despite RFC-8785-compatible wording
in some schemas, this helper—not `rfc8785.dumps`—is the byte-for-byte
implementation.

The omitted member differs by object:

- manifest: omit only `content_hash` (`tools/ingest_campaign_results.py:124-128`);
- pre-ingestion ClaimContract validation: omit only `content_hash`
  (`tools/ingest_campaign_results.py:98-101`, `:159-160`);
- updated ClaimContract: omit only `content_hash` before assigning the new value
  (`tools/ingest_campaign_results.py:377-381`);
- EvidenceBundle: hash the constructed bundle before adding `bundle_id`
  (`tools/ingest_campaign_results.py:266-296`). Row-only fields such as
  `row_id`, chain hashes, and unknown producer metadata are not in that bundle
  unless they are explicitly copied by the construction code.

### 5.3 Exact-byte hashes

`artifact_hash` and the generated evidence reference’s
`campaign_manifest_hash` use raw file bytes:

```python
payload = path.read_bytes()
return "sha256:" + hashlib.sha256(payload).hexdigest()
```

This is verbatim from `tools/ingest_campaign_results.py:89-95`. No JSON parsing,
canonicalization, newline normalization, or text encoding occurs. Any byte-level
reformat changes these hashes.

## 6. Validation and dry-run behavior

The CLI has **no** `--validate`, `--check`, or `--dry-run` option; `parse_args`
only declares `--root`, `--manifest`, and `--measurements`
(`tools/ingest_campaign_results.py:416-421`). A successful invocation writes:

- generated EvidenceBundles under `evidence/v1/examples/`;
- updated ClaimContracts under `registry/claims/`; and
- regenerated assumption registry/snapshot outputs through `materialize`.

Those writes occur at `tools/ingest_campaign_results.py:404-413`. Before them,
the tool builds the proposed claims, bundles, registry, and lock in a temporary
staging tree (`tools/ingest_campaign_results.py:383-403`), so validation errors
before the real-write loop fail without those writes. This is transactional
prevalidation, not a user-selectable dry run.

For a non-mutating validation, invoke the normal CLI against a disposable copy
or temporary `--root` containing all required paths. The manifest and artifact
paths encoded or supplied for that run must resolve inside that temporary root.
For example:

```text
tmp=$(mktemp -d)
cp -a registry evidence campaigns data "$tmp"/
python3 tools/ingest_campaign_results.py \
  --root "$tmp" \
  --manifest "$tmp/campaigns/v1/<manifest>.json" \
  --measurements "$tmp/data/candidates/<campaign>/measurements.jsonl"
rm -rf "$tmp"
```

The command exits 0 and prints sorted JSON of the form
`{"ingested_bundle_ids": [...]}` on success. A caught `KeyError`, `TypeError`,
or `ValueError` exits 2 and prefixes the stderr diagnostic with
`ingestion failed:` (`tools/ingest_campaign_results.py:424-434`). Filesystem
errors arising after the validated staging phase are not part of that caught
error set.

## 7. Other fail-closed preconditions

A structurally valid row still fails unless all repository relationships are
valid:

- Every manifest target is a unique `{claim_id, premise_id}` pair and receives
  at least one row; rows may not target undeclared pairs
  (`tools/ingest_campaign_results.py:310-332`).
- The selected ClaimContract passes its schema and its existing semantic hash is
  canonical (`tools/ingest_campaign_results.py:152-164`).
- The premise already references at least one baseline EvidenceBundle; every
  referenced bundle must exist, pass its schema, and have a canonical
  `bundle_id` (`tools/ingest_campaign_results.py:167-194`).
- Row predicate and three-dimensional scope must be supported by those baseline
  bundles (`tools/ingest_campaign_results.py:349-360`).
- A generated filename may be reused only when its existing parsed JSON object
  equals the proposed bundle (`tools/ingest_campaign_results.py:361-370`).
- The full generated registry and lock must build in staging before real files
  are written (`tools/ingest_campaign_results.py:383-403`).
