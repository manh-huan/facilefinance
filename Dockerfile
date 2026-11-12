# Image shared by the `api` and `worker` services; the command is set in docker-compose.yml.
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first (cached layer), then the project.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY apps ./apps
COPY config ./config
COPY locales ./locales
COPY migrations ./migrations
COPY alembic.ini* ./
RUN uv sync --frozen --no-dev

RUN useradd --system --no-create-home app
USER app
