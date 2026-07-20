FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Build toolchain for gpaw's C extension (PyPI serves sdists for this tag;
# BLAS headers let it link optimized BLAS instead of the noblas fallback).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libopenblas-dev libxc-dev \
    && rm -rf /var/lib/apt/lists/*

# GPAW 26.7 compiles as C++; make g++ the default driver so C++ headers resolve.
ENV CC=g++ CXX=g++

RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir \
      ase==3.29.0 \
      gpaw==26.7.0 \
      numpy==2.4.6 \
      google-cloud-storage==2.18.0

COPY gcp/mlip-cell-runner/z1_barrier.py ./
COPY gcp/mlip-cell-runner/z1_sparse_dft.py ./
COPY gcp/sparse-dft-pilot/run_pilot.py ./

ENTRYPOINT ["python3", "run_pilot.py"]
