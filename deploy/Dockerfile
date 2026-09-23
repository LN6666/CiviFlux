# Base OCI indexes were resolved with `docker buildx imagetools inspect` on 2026-09-24.
# Pin both the human-readable tag and digest so an upstream retag cannot change this build.
FROM node:22.23.2-bookworm-slim@sha256:48e4b67d85f87bd551df43704e24d252f56cc5f8e9718841aace50f19948f0f9 AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY web/ ./
RUN npm run build
FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2
WORKDIR /app
# Use one immutable Debian archive snapshot rather than the moving bookworm indexes.
RUN set -eux; \
    printf '%s\n' \
      'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260920T000000Z bookworm main' \
      'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20260920T000000Z bookworm-updates main' \
      'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20260920T000000Z bookworm-security main' \
      > /etc/apt/sources.list; \
    rm -f /etc/apt/sources.list.d/debian.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends libgomp1 libgl1 libglu1-mesa libxrender1; \
    rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir uv==0.11.23
COPY pyproject.toml uv.lock .python-version ./
COPY core/ ./core/
COPY api/ ./api/
COPY adapters/ ./adapters/
COPY ontology/ ./ontology/
RUN uv sync --frozen --no-dev --no-editable --no-python-downloads
COPY --from=web /build/web/dist ./web/dist
COPY config/ ./config/
COPY cases/synthetic/ ./cases/synthetic/
COPY deploy/container_smoke.py ./deploy/container_smoke.py
ENV PYTHONPATH=/app/core:/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV CIVIFLUX_WORKSPACE=/workspace
ENV QWEN_API_ALLOW_EGRESS=0
ENV QWEN_API_MAX_CALLS=0
ENV SIMPLEJEV_ALLOW_EGRESS=0
ENV SIMPLEJEV_MAX_CALLS=0
# Directly execute the frozen environment; `uv run` could re-resolve on startup.
# Host network is required for the production loopback API on Linux; the CI smoke
# instead uses --network none and talks to the API inside the same container.
CMD ["/app/.venv/bin/python", "-m", "api", "--port", "8765"]
