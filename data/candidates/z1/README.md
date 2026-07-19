# Z1 campaign measurement artifact

`measurements.jsonl` contains one RFC 8785-canonical aggregate row for each
model in the governing Z1 CampaignManifest. `artifact-manifest.json` records
the measurement file's exact-byte SHA-256 hash, row-chain bounds, and every raw
source artifact used to derive the rows.

Regenerate both generated files from the byte-preserved `raw/` and `source/`
inputs at the repository root:

```bash
uv run --with rfc8785==0.1.4 python tools/build_z1_measurement_rows.py
```

Verify that checked-in outputs are current without rewriting them:

```bash
uv run --with rfc8785==0.1.4 python tools/build_z1_measurement_rows.py --check
```

Do not edit either generated file by hand.