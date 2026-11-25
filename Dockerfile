FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY src ./src

FROM python:3.12-slim AS runtime

WORKDIR /app

RUN groupadd --system appuser && useradd --system --gid appuser appuser

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/tmp/uv-cache
ENV UV_NO_SYNC=1

USER appuser

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "src.adapters.inbound.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
