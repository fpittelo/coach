# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir --target=/install/wheels dist/*.whl

# Stage 2: Final minimal runtime stage
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="coach-mcp" \
      org.opencontainers.image.description="Model Context Protocol server for Intervals.icu endurance coaching" \
      org.opencontainers.image.authors="Frederic Pitteloud" \
      org.opencontainers.image.vendor="fpittelo" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.source="https://github.com/fpittelo/coach" \
      org.opencontainers.image.documentation="https://github.com/fpittelo/coach/blob/main/README.md"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/site-packages \
    MCP_TRANSPORT=stdio \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    INTERVALS_ATHLETE_ID=0 \
    INTERVALS_BASE_URL=https://intervals.icu/api/v1

# Create non-root user and group (UID/GID 10001)
RUN groupadd -g 10001 coach && \
    useradd -u 10001 -g coach -s /bin/false -m -d /home/coach coach

WORKDIR /app

# Copy installed site-packages from builder
COPY --from=builder --chown=coach:coach /install/wheels /app/site-packages
COPY --chown=coach:coach src/ /app/src/

ENV PATH="/app/site-packages/bin:${PATH}" \
    PYTHONPATH="/app/src:/app/site-packages:${PYTHONPATH}"

# Switch to non-root user
USER coach:coach

EXPOSE 8000

# Entrypoint running coach_mcp server
ENTRYPOINT ["python", "-m", "coach_mcp.server"]
