ARG CUDA_IMAGE=nvidia/cuda:12.6.3-runtime-ubuntu22.04
FROM rust:1-bullseye AS atlas_distill_builder

WORKDIR /build

COPY atlas-distill/Cargo.toml atlas-distill/Cargo.lock ./atlas-distill/
COPY atlas-distill/src ./atlas-distill/src

RUN cargo build --release --manifest-path atlas-distill/Cargo.toml --bin atlas-distill

FROM ${CUDA_IMAGE}

ARG BACKEND=chgnet
ENV PYTHONUNBUFFERED=1
ENV MLIP_BACKEND=${BACKEND}
ENV MATGL_BACKEND=DGL
ENV ATLAS_DISTILL_BIN=/usr/local/bin/atlas-distill
ENV MLIP_DISTILL_POLICY_ENGINE=auto
ENV MLIP_DISTILL_RIBBON_VERSION=hyperribbon-v1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    g++ \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY gcp/mlip-cell-runner/requirements-common.txt ./
COPY gcp/mlip-cell-runner/requirements-${BACKEND}.txt ./requirements-backend.txt

RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir -r requirements-backend.txt

COPY gcp/mlip-cell-runner/mlip_cell_runner.py ./
COPY python/lupine_distill_runtime ./lupine_distill_runtime
COPY python/lupine_distill ./lupine_distill
# Lean env-field certificates: the report backs the run-time CertificateGate
# (tier-2-refused cells are excluded from correction). Without it in the
# image, the gate's "auto" default resolves to a nonexistent path and the
# gate is silently absent in production.
COPY data/y_matrix_runs/env_field_binding_report.json ./data/y_matrix_runs/env_field_binding_report.json
ENV MLIP_DISTILL_ENV_FIELD_REPORT=/app/data/y_matrix_runs/env_field_binding_report.json
COPY --from=atlas_distill_builder /build/atlas-distill/target/release/atlas-distill /usr/local/bin/atlas-distill

RUN /usr/local/bin/atlas-distill distill-policy --help >/dev/null \
    && python3 /app/mlip_cell_runner.py --help >/dev/null

RUN useradd -m -u 1000 mlip
USER mlip

ENTRYPOINT ["python3", "/app/mlip_cell_runner.py"]
CMD ["--help"]
