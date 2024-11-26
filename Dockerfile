# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-slim AS base
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_FROZEN=1

# Create our non-root user
RUN adduser --system --no-create-home python-runner

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.1 /uv /uvx /bin/

# Install dependencies, but not the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    /bin/uv sync --no-install-project --all-extras --no-dev

COPY transcription_bot transcription_bot
COPY pyproject.toml uv.lock ./

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    touch README.md && \
    /bin/uv sync --no-dev

# We change to the non-root user after all files are copied
# Root owns the files and we cannot write to them: this is a security measure
USER python-runner

ENTRYPOINT ["/app/.venv/bin/python"]

CMD [ "-c", "import sys;print('Provide an entrypoint script!');sys.exit(1)" ]
