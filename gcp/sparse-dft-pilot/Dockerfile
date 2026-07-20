FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install --no-cache-dir \
      ase==3.28.0 \
      gpaw==26.7.0 \
      numpy==1.26.4 \
      google-cloud-storage==2.18.0

COPY gcp/mlip-cell-runner/z1_barrier.py ./
COPY gcp/mlip-cell-runner/z1_sparse_dft.py ./
COPY gcp/sparse-dft-pilot/run_pilot.py ./

ENTRYPOINT ["python3", "run_pilot.py"]
