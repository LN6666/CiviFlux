# Reference build; see docs/CURRENT_RUNBOOK.md. Pin resolved image digests for a release.
FROM node:22.23.2-bookworm-slim AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
FROM python:3.12.13-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libgl1 libglu1-mesa && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir uv==0.11.23
COPY pyproject.toml uv.lock .python-version ./
COPY core/ ./core/
COPY api/ ./api/
COPY adapters/ ./adapters/
COPY ontology/ ./ontology/
RUN uv sync --frozen --no-dev --no-editable
COPY --from=web /build/web/dist ./web/dist
COPY config/ ./config/
COPY cases/synthetic/ ./cases/synthetic/
ENV PYTHONPATH=/app/core:/app
ENV CIVIFLUX_WORKSPACE=/workspace
ENV QWEN_API_ALLOW_EGRESS=0
ENV QWEN_API_MAX_CALLS=0
ENV SIMPLEJEV_ALLOW_EGRESS=0
ENV SIMPLEJEV_MAX_CALLS=0
# Host network is required on Linux so the API can bind only to loopback.
CMD ["uv", "run", "--frozen", "--no-dev", "python", "-m", "api", "--port", "8765"]
