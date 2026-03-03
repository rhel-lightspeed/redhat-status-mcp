# Stage 1: Builder — UBI 10 full image has Python 3.12 + pip
FROM registry.access.redhat.com/ubi10:latest@sha256:b9e5730d0b6dba45e82c15fb8f49c6082e01cdcb5e4f6ba96535dab42a4d2cf0 AS builder

ARG PSEUDO_VERSION=0.1.0a

WORKDIR /build

# Install pip then uv for fast, reproducible dependency resolution
RUN dnf install -y python3-pip && dnf clean all && python3 -m pip install uv

# Provide the version to avoid the need to pass in the .git directory.
# https://setuptools-scm.readthedocs.io/en/latest/usage/#with-dockerpodman
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${PSEUDO_VERSION}

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only (skip the project itself for now)
RUN uv sync --no-dev --no-install-project

# Copy source and install the package itself (no deps, already installed)
COPY src/ ./src/
RUN uv pip install . --no-deps && \
    sed -i 's|^#!.*python.*|#!/app/.venv/bin/python3|' /build/.venv/bin/redhat-status-mcp

# Stage 2: Runtime — minimal UBI 10 Python 3.12 image
FROM registry.access.redhat.com/ubi10/python-312-minimal:latest@sha256:1cce9e5cea5dc250f2d8327f27580cf31d6a5430304928bff37be84391f4ec61

ARG PSEUDO_VERSION=0.1.0a
ARG VERSION=0.1.0a

WORKDIR /app

LABEL com.redhat.component=redhat-status-mcp
LABEL description="MCP server exposing Red Hat status page data to LLMs"
LABEL io.k8s.description="MCP server exposing Red Hat status page data to LLMs"
LABEL io.k8s.display-name="Red Hat Status MCP"
LABEL io.openshift.tags="rhel,mcp,status"
LABEL konflux.additional-tags=${VERSION}
LABEL name=redhat-status-mcp
LABEL release=${PSEUDO_VERSION}
LABEL summary="Red Hat Status MCP Server"
LABEL url="https://gitlab.cee.redhat.com/rhel-lightspeed/enhanced-shell/redhat-status-mcp"
LABEL vendor="Red Hat, Inc."
LABEL version=${VERSION}

# Copy the virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default to streamable-http for networked container deployments.
# Override with MCP_TRANSPORT=sse or MCP_TRANSPORT=stdio as needed.
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

ENTRYPOINT ["redhat-status-mcp"]
