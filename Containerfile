# Stage 1: Builder — UBI 10 full image has Python 3.12 + pip
FROM registry.access.redhat.com/ubi10:latest AS builder

WORKDIR /build

# Install pip then uv for fast, reproducible dependency resolution
RUN dnf install -y python3-pip && dnf clean all && python3 -m pip install uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only (skip the project itself for now)
RUN uv sync --no-dev --no-install-project

# Copy source and install the package itself (no deps, already installed)
COPY src/ ./src/
RUN uv pip install . --no-deps && \
    sed -i 's|^#!.*python.*|#!/app/.venv/bin/python3|' /build/.venv/bin/redhat-status-mcp

# Stage 2: Runtime — minimal UBI 10 Python 3.12 image
FROM registry.access.redhat.com/ubi10/python-312-minimal:latest

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["redhat-status-mcp"]
