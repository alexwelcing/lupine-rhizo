# Lupine Rhizo

Lupine Science measures where machine-learned models of atoms go wrong, against
published references and pass/fail gates set in advance, and publishes every
verdict, failures included.

## What is here

- **Scoring engines** in Rust and Python (`distill/`, `python/`).
- **Benchmark runners** for the cloud and for your own cluster (`gcp/`, `hpc/`).
- **Evidence:** preregistered campaigns, the claim registry and run records
  (`campaigns/`, `registry/`, `evidence/`).
- **Lean checks** of the arithmetic behind published numbers; they do not check the
  physics, the reference data or the pipeline (`lean-spec/`).
- **Exports** that feed the public Library (`exports/`).

## Status

Working drafts, not peer-reviewed. Failures and abstentions are published beside what held.

## Start here

- [Results](https://lupine.science/results/): what held and what did not
- [Corrections](https://lupine.science/corrections/): what we retracted, and why
- [Hypothesis ledger](docs/conjectures/ledger.md): every tested claim and its status
- [Negative-results preprint](paper/negative-results-preprint/): three locked negative results
- [Replication kit](replication/error-geometry/): recompute the statistics yourself

## More

- [Overview](docs/overview.md): ways to check the work, and what Lean does and does not check
- [Results in detail](docs/results-detail.md): each result with its scope, failures included
- [Repository map](docs/repository-map.md): folders, boundary and related repositories
- [Development](docs/development.md): quick checks, toolchain notes and licence detail
- [How we use AI agents and handle data](docs/ai-and-data.md)

## License

You can reuse our code (MIT) and our first-party text and data (CC BY 4.0) with
attribution and no share-alike obligations. Third-party material keeps its own
terms; see [NOTICE.md](NOTICE.md).

## Contact

Research partners, model builders, press and investors: alex@lupinesci.com.
