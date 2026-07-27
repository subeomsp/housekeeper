# syntax=docker/dockerfile:1

# Build/run image for the Voice Inventory Agent backend.
# The image is built by the platform (e.g. Render); no local Docker is required.
FROM python:3.12-slim

# uv, copied from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application (context is the backend/ directory) and finish the sync.
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Apply migrations, then serve. The platform provides $PORT at runtime;
# DATABASE_URL must be supplied as an environment variable (never baked in).
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
