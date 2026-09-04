# FastAPI backend (agentic RAG pipeline).
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Dependencies first so code changes do not invalidate the layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

# --workers 1: the generate-limit counter and the job registry (main.py) live
# in process memory. A second worker would not share either, silently
# multiplying the hourly cap and losing half the running jobs. Move both to
# Redis before ever raising this.
#
# --proxy-headers --forwarded-allow-ips='*': the container has no way to know
# its own upstream's address, so it trusts whatever reverse proxy fronts it to
# set X-Forwarded-For honestly. Without this every anonymous client behind the
# proxy looks like the proxy itself and shares one rate-limit bucket.
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]
