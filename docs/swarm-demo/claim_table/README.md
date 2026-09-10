# claim_table

Reads the TMS 2027 proceedings canonical results object
(schema `lupine.tms2027.proceedings.results.v1`, produced by
`lupine-rhizo/paper/tms2027-proceedings/build_artifacts.py`) and prints a
two-column markdown table of every headline value with its binding key.

```bash
python -m claim_table <results.json>
```

- `derived.*` keys are numbers recomputed from committed source rows;
  `quoted.*` keys are frozen-report quotes, each bound to its `source`.
- A headline value is a scalar leaf or compact scalar list; per-record arrays
  (e.g. `derived.geometry.per_group`) are record detail and are skipped.
- Rows sort lexicographically by binding key, so output is deterministic.

Exit codes: 0 ok, 2 usage, 3 unreadable/invalid results object.

Run tests: `python -m pytest` (fixture: `tests/fixtures/tms2027_proceedings_results.json`,
a verbatim copy of the canonical `results.json`).
