# TMS 2027 proceedings results

`results.json` is the single canonical numeric object for the proceedings manuscript and public figures. It embeds the 42 geometry rows and the source rows needed by each plot, while `source_files` records repository revisions, SHA-256 digests, paths, and row/JSON locators for every manuscript number.

The bundle deliberately keeps these two estimands separate:

- `17.84 → 10.36 GPa` is an oracle directional ceiling because the held-out target supplies the projection coefficient; it is not deployable.
- `14.55 → 63.40 GPa` is the reference-free global-operator test and is a failure.

The paired all-electron PBE/r2SCAN anchor remains `PENDING`.

## Rebuild and verify

From the `lupine-rhizo` repository root:

```sh
python paper/tms2027-proceedings/results/build_results.py all \
  --lupine-root /path/to/read-only/lupine
python -m unittest paper/tms2027-proceedings/results/test_results.py
```

`build` reads the reviewed sources and fails before writing if any frozen cardinality or value has drifted. `figures` reads only `results.json`; it does not read source repositories. `verify` checks the canonical claims and all four PDF/PNG output pairs.

Outputs:

- `denominator-provenance-funnel.{pdf,png}`
- `participation-ratio-by-group-size.{pdf,png}`
- `correction-falsification.{pdf,png}`
- `qualification-dft-reference-stack.{pdf,png}`
