# lupine-ops

Operational tooling for the Lupine Science fleet — manifest,
ledger, MLIP deployment shape, plus a periodic Cloud Run health/cost
reporter binary.

> **Status: keep.** This crate is an active dependency of `atlas-distill`
> (the Rust agents import `lupine_ops::ledger`, `lupine_ops::elastic`,
> `lupine_ops::statics`, and `lupine_ops::mlip_ops`). Do not archive or
> move without updating `atlas-distill/Cargo.toml` and the agent imports.

## `monitor_cloud_run`

Rust binary that authenticates to GCP, walks Cloud Run services and jobs
in `--project / --region`, queries Cloud Monitoring for a 24h request
proxy (true cost requires BigQuery billing export), and queries
`run.googleapis.com/container/billable_instance_time` for region-scoped Cloud
Run Job telemetry. Schedule cap reporting reconciles measured UTC-day billable
runtime against immutable Cloud Run execution templates. Scheduled dispatches
carry `LUPINE_SCHEDULE_NAME`; the monitor uses each execution's bounded UTC-day
duration to apportion the job-level billable metric exactly once. Owner-noted
manual and legacy unscheduled execution durations stay in the denominator but
are not charged to any schedule. The generation-matched GCS admission ledger
remains the floor while work is in flight. A missing ledger object means no
reservations today; API, permission, malformed-ledger, or missing execution
provenance fails the poll instead of becoming a healthy-looking zero.
Replaces the never-shipped `monitor_cloud_run.py` referenced in
`docs/handoff/04_autonomous_handoff_protocol.md`.

### Auth

Pick whichever fits where the binary runs:

- **Local dev** — `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json`.
- **Cloud Run / GCE / GKE Workload Identity** — `gcp_auth` resolves the
  attached service account automatically.

The service account needs `roles/run.viewer`, `roles/monitoring.viewer`, and
read access to `gs://<project>-atlas-inputs/mlip-budget-ledgers/`.

### Build

```
cargo build --release --bin monitor_cloud_run
```

### Run

```
# One-shot summary for the default project (shed-489901 / us-central1).
cargo run --release --bin monitor_cloud_run -- --once

# Custom project, tighter cost cap, fan results to a Worker ingest URL.
cargo run --release --bin monitor_cloud_run -- \
    --project shed-489901 \
    --region us-central1 \
    --cost-cap-usd 25 \
    --report-url https://glim-think.workers.dev/ingest/cloud-run-health

# Long-running daemon (5 minute cadence).
cargo run --release --bin monitor_cloud_run -- --interval-secs 300
```

### CLI

```
monitor_cloud_run [--project shed-489901] [--region us-central1]
                  [--once] [--interval-secs 300]
                  [--budget-ledger-url gs://.../mlip-budget-ledgers]
                  [--cost-cap-usd 50] [--report-url <url>]
```

`--once` runs a single check then exits. Default is the loop with
`--interval-secs` cadence (default 300s).

### Output

Human-readable summary lands on stdout; the same payload — shaped as
`PollSummary` — is POSTed to `--report-url` if provided. The CF Worker
consumer can match on `services[].short_name` (`lupine-site`,
`atlas-distill`, etc.) and `flags[]` for alerting.
