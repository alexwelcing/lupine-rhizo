# Z3 cloud execution runbook

Status observed: 2026-07-18 (UTC)

## Authenticated execution plane

The active `gcloud` principal is `alexwelcing@gmail.com`. It can describe and execute resources in project `shed-489901`. Always pass the project and region explicitly because the local gcloud default project is unrelated.

- Project: `shed-489901` (project number `350452481649`)
- Region: `us-central1`
- Runtime service account: `atlas-distill-runner@shed-489901.iam.gserviceaccount.com`
- Runtime IAM observed: `roles/storage.objectAdmin`, `roles/cloudsql.client`, `roles/cloudtasks.enqueuer`
- Raw Z3 output root: `gs://shed-489901-atlas-outputs/z3-campaign/raw/`
- Endpoint shape: Cloud Run Job resource `projects/shed-489901/locations/us-central1/jobs/<job>` (not an HTTP service URL)

No credential material is stored in this repository. Cloud Run uses Application Default Credentials from the job service account. The operator uses the active gcloud credential.

## Frozen-model endpoint map

| Campaign model | Cloud Run Job | Image observed | Ready |
| --- | --- | --- | --- |
| `chgnet` | `mlip-cell-chgnet` | `.../mlip-cell-chgnet:adsorption-368470928684-r2` | `True` |
| `mace-mp-small` | `mlip-cell-mace-mp-small` | `.../mlip-cell-mace-mp-small:z3-adsorption-aliases-20260718` | `True` |
| `mace-mp-medium` | `mlip-cell-mace-mp-medium` | `.../mlip-cell-mace-mp-small:z3-adsorption-aliases-20260718` | `True` |
| `mace-mpa-0-medium` | `mlip-cell-mace-mpa-0-medium` | `.../mlip-cell-mace-mp-small:z3-adsorption-aliases-20260718` | `True` |

The runner cross-checks every selected model against `campaigns/v1/z3.campaign-manifest.v1.json`, including its frozen model artifact hash.

Redeployment note (2026-07-19): the four jobs are being redeployed with image tag `z3-adsorption-fixed-20260719`, built from the defect-fixed runner sources on `main`. This tag supersedes the `adsorption-368470928684-r2` and `z3-adsorption-aliases-20260718` tags recorded in the table above.

## Reproducible submission and capture

`gcp/z3-campaign/run_measurement.py` submits one single-candidate fixture to the correct job and optionally downloads and validates the raw `cell_result.json`.

Preflight without cloud spend:

```bash
python gcp/z3-campaign/run_measurement.py \
  --model-id chgnet \
  --fixture-url gs://shed-489901-atlas-inputs/z3-campaign/<fixture-sha256>/CO-Pt111.json \
  --candidate-id CO-Pt111 \
  --run-id z3-20260718 \
  --dry-run
```

Execute and capture locally:

```bash
python gcp/z3-campaign/run_measurement.py \
  --model-id chgnet \
  --fixture-url gs://shed-489901-atlas-inputs/z3-campaign/<fixture-sha256>/CO-Pt111.json \
  --candidate-id CO-Pt111 \
  --run-id z3-20260718 \
  --capture-dir tmp/z3-raw
```

The fixture, not this transport wrapper, defines the candidate structures and observable. Use a fixture containing exactly one candidate when one output record per candidate is required. The default row is `adsorption_energy`; the downloaded artifact must report the requested model and row and contain exactly one completed prediction for the requested candidate with a finite `adsorption_energy_ev`, or the wrapper fails.

Artifacts are separated by run, model, candidate, and row:

```text
gs://shed-489901-atlas-outputs/z3-campaign/raw/<run>/<model>/<candidate>/<row>/cell_result.json
```

## Live adsorption smoke evidence

The reviewed adsorption fixture contract was deployed to all four jobs. Build `b598dee0-9cd2-4c91-b0ec-1b8253d1bf01` produced the shared alias-aware MACE image. Each model then loaded on an NVIDIA L4, evaluated all three systems in the content-addressed synthetic fixture, wrote a raw artifact to GCS, and passed the runner's local capture validation.

Fixture:

```text
gs://shed-489901-atlas-inputs/z3-campaign/36847092868491ec2c996d9bb2cb7221a4f087d0f5b0f3c7d470602791c3235b/CO-Pt111-synthetic.json
```

| Model | Successful execution | Package | Raw adsorption energy | Captured artifact SHA-256 |
| --- | --- | --- | --- | --- |
| `chgnet` | `mlip-cell-chgnet-xfdpn` | `chgnet 0.4.2` | `-0.0431604385 eV` | `5aa348506ad3e3c5f94c96620bcf5956cfe5576ec37d6ee5a03ea2485b1e3679` |
| `mace-mp-small` | `mlip-cell-mace-mp-small-r427h` | `mace-torch 0.3.16 / small` | `-0.0230913162 eV` | `ac3957c17a062ecb2a75ed5dd6373358e11658905a44de35161c91b26a489d09` |
| `mace-mp-medium` | `mlip-cell-mace-mp-medium-55cr7` | `mace-torch 0.3.16 / medium` | `0.2282776833 eV` | `1bc7b9c805cb548dd78e3f94525b3add4aac640cf1aa70a1e086f6c4ac5fe2ae` |
| `mace-mpa-0-medium` | `mlip-cell-mace-mpa-0-medium-5dttx` | `mace-torch 0.3.16 / medium-mpa-0` | `0.2035150528 eV` | `ddc38e693ff5731a099094b7af2273ac2aa73029008d2c6322921d9df3910c1a` |

The CHGNet artifact is under run `z3-smoke-20260718a`; the three MACE artifacts are under `z3-smoke-20260718b`. The complete paths follow the storage layout above. Every listed Cloud Run execution completed with `succeededCount=1`.

These smokes prove the execution path, not Z3's scientific accuracy. The fixture is explicitly synthetic software-validation data. The campaign worker must not treat these values as experimental evidence; the campaign remains dependent on its separately locked candidate/reference panel and delta-learning artifacts.

## Verification

```text
uv run pytest -q gcp/z3-campaign/test_run_measurement.py
5 passed

PYTHONPATH=python:gcp/mlip-cell-runner uv run --with pytest --with ase --with numpy --with requests \
  pytest -q gcp/mlip-cell-runner/test_runner_backends.py \
  gcp/mlip-cell-runner/test_fixture_contract.py \
  gcp/mlip-cell-runner/test_runner_offline.py \
  gcp/z3-campaign/test_run_measurement.py
23 passed
```
