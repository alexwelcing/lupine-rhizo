# Multi-stage build for distill
# Stage 1: Build the Rust binary (standalone — distill has no workspace
# parent and no path-dependencies on sibling crates, so a flat copy is enough).
FROM rust:1.88-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy manifest + lockfile first for cargo layer caching
COPY distill/Cargo.toml distill/Cargo.lock ./

# Copy source
COPY distill/src ./src

# Build release binary
RUN cargo build --release --bin distill

# Stage 2: Minimal runtime image
FROM debian:bookworm-slim AS runtime

WORKDIR /app

# Install runtime dependencies (SSL certs for ureq + reqwest)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 distill

# Copy binary from builder
COPY --from=builder /app/target/release/distill /usr/local/bin/distill

# Copy benchmark data
COPY distill/benchmarks ./benchmarks

# Set ownership
RUN chown -R distill:distill /app
USER distill

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD distill --version || exit 1

# Default entrypoint
ENTRYPOINT ["distill"]
CMD ["--help"]
