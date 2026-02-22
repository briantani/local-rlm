# Use a slim Python image for smaller size
FROM python:3.14-slim

# Basic environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install system dependencies (including WeasyPrint deps). Keep layers minimal.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    ca-certificates \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python tools (pin versions if you have them in the project)
RUN pip install --no-cache-dir uv uvicorn

# Copy project configuration files (lockfile expected in repo for reproducible builds)
COPY pyproject.toml ./
COPY uv.lock ./

# Install runtime dependencies (group 'repl' used by project)
RUN uv sync --frozen --no-install-project --no-dev --group repl

# Copy application sources
COPY src/ src/
COPY configs/ configs/
COPY tasks/ tasks/
COPY README.md ./

# Install the project itself (finalize dependencies, includes web deps like FastAPI)
RUN uv sync --frozen --no-dev

# Create runtime directories
RUN mkdir -p /app/logs /app/runs /app/workspaces /app/.dspy_cache

# Create a non-root user and set ownership for security
RUN groupadd -r rlm && useradd -r -g rlm rlm && chown -R rlm:rlm /app

# Expose port and mount points
EXPOSE 8000
VOLUME ["/app/runs", "/app/logs", "/app/workspaces", "/app/.dspy_cache"]

# Run as non-root user
USER rlm

# Use a robust uvicorn invocation as the container entrypoint
ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
