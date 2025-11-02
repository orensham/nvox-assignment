FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

WORKDIR /app

COPY pyproject.toml uv.lock /app/
COPY packages /app/packages
RUN uv sync --frozen --no-dev --no-editable --package=nvox-api

FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PATH="/app/.venv/bin:${PATH}"

COPY apps/nvox-api/src /app/
COPY apps/nvox-api/config /app/config
COPY --from=builder /app/.venv /app/.venv

CMD ["fastapi", "run", "main.py", "--port", "8000"]
