## Multi-stage Dockerfile for local-rlm
# Builder stage: install build deps, run `uv sync` and `pip install .` into /install
FROM python:3.14-slim AS builder

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install build/system dependencies needed for wheels and WeasyPrint
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        ca-certificates \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-xlib-2.0-0 \
        libffi-dev \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install minimal Python tooling required during build
RUN pip install --no-cache-dir uv

# Copy lockfiles and install REPL group (preloads heavy DS libs into wheel cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --group repl || true

# Copy source and install the project into an isolated prefix
COPY src/ src/
COPY configs/ configs/
COPY tasks/ tasks/
COPY README.md ./

# Install the project and its runtime dependencies into /install
RUN pip install --no-cache-dir --prefix /install .

# Final runtime image: smaller, only runtime dependencies + system libs
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install system libraries required at runtime (WeasyPrint, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-xlib-2.0-0 \
        libffi-dev \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application sources (for runtime imports and mounts)
COPY src/ src/
COPY configs/ configs/
COPY tasks/ tasks/
COPY README.md ./

# Install uvicorn runtime (keep as explicit runtime dependency)
RUN pip install --no-cache-dir uvicorn

# Ensure small runtime-only Python deps required by the web routes are present
RUN pip install --no-cache-dir markdown weasyprint

# Create runtime directories and dspy cache location
RUN mkdir -p /app/logs /app/runs /app/workspaces /home/rlm/.dspy_cache

# Create a non-root user and set ownership
RUN groupadd -r rlm && useradd -r -g rlm rlm && chown -R rlm:rlm /app /home/rlm/.dspy_cache

# Expose port and declare persistent volumes
EXPOSE 8000
VOLUME ["/app/runs", "/app/logs", "/app/workspaces", "/app/.dspy_cache"]

# Run as non-root user
USER rlm

# Entrypoint: run uvicorn on the ASGI app
ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
