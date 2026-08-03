# Round-4 Cloud Run execution cost ledger (draft; needs verification)

Status: `needs-verification` — operational estimate for review, not an approved public economics claim.

Run: `correction-round4-20260719`
Project/region: `shed-489901/us-central1`
Execution date: 2026-07-19
Candidate lock: `sha256:b7562637c860b15b92f64659f0b063bc6d2b6c0c12899e21f370359cccb914f1`

## Method

This follows the measured-time × allocated-resource × rate structure used by `docs/analysis/z1-union-cost-ledger.md`, but uses the actual Cloud Run Job resources and Cloud Run execution durations rather than a local-cloud-equivalent rate.

For each successful registered execution:

- billable duration is the Cloud Run reported successful execution duration (`Completed` condition message), rounded as reported to 0.01 s;
- allocation is 4 vCPU, 16 GiB memory, and one NVIDIA L4 without zonal redundancy;
- rate inputs are the default Cloud Run Jobs rates shown for Iowa (`us-central1`) on the official Cloud Run pricing page, read 2026-08-03:
  - CPU: $0.000018 per vCPU-second;
  - memory: $0.000002 per GiB-second;
  - NVIDIA L4 without zonal redundancy: $0.0001867 per GPU-second.

Formula: `duration_s × (4 × CPU_rate + 16 × memory_rate + 1 × L4_rate)`.

This is a gross list-price estimate before the Cloud Run free tier, credits, committed-use discounts, taxes, storage, logging, network transfer, or Artifact Registry charges. It is not an invoice reconciliation. Same-region transfer is excluded; the pricing page states that transfer to Google Cloud resources in the same region is not charged. The approved public economics remain frozen elsewhere; this draft must not be substituted for or combined with them.

## Measured executions

| Model | Cloud Run execution | Successful duration (s) | vCPU-h | GiB-h | L4 GPU-h | Gross list-price estimate (USD) |
|---|---|---:|---:|---:|---:|---:|
| CHGNet | `mlip-cell-chgnet-round4-8bbp8` | 83.15 | 0.092389 | 0.369556 | 0.023097 | 0.024171705 |
| MACE-MP small | `mlip-cell-mace-round4-mp-small-k94mk` | 173.72 | 0.193022 | 0.772089 | 0.048256 | 0.050500404 |
| MACE-MP medium | `mlip-cell-mace-round4-mp-medium-mmcjq` | 143.83 | 0.159811 | 0.639244 | 0.039953 | 0.041811381 |
| MACE-MPA-0 medium | `mlip-cell-mace-round4-mpa-0-medium-6979j` | 123.95 | 0.137722 | 0.550889 | 0.034431 | 0.036032265 |
| **Total** | 4 successful executions / 32 model×material cells | **524.65** | **0.582944** | **2.331778** | **0.145736** | **0.152515755** |

## Evidence receipts

- Repository execution receipt: `data/candidates/round4/execution-receipt.json`.
- Machine-readable results and 64 per-row artifact hashes: `data/candidates/round4/report.json`.
- Frozen endpoint receipt: `gcp/mlip-cell-runner/round4_endpoints.lock.json`, SHA-256 `7eeddc4b09258c120e7994820944fb2e8394b345b9bd662c9c580cb964fd3e34`.
- Official pricing source: <https://cloud.google.com/run/pricing> (Cloud Run Jobs, Iowa/us-central1; accessed 2026-08-03).

## Review gate

Before any public use, verify the four durations directly against Cloud Run execution descriptions and reconcile this list-price estimate against the billing export for 2026-07-19. Until then, preserve `needs-verification`.
