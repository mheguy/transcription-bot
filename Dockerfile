# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS base
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

# Create our non-root user
RUN adduser --system --no-create-home python-runner

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.1 /uv /uvx /bin/

# Install dependencies, but not the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY transcription_bot transcription_bot
COPY pyproject.toml uv.lock ./

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    touch README.md && \
    uv sync --frozen --no-dev

# We change to the non-root user after all files are copied
# Root owns the files and we cannot write to them: this is a security measure
USER python-runner

ENTRYPOINT ["uv", "run", "/app/transcription_bot/main.py"]
