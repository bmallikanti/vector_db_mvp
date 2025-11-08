# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching)
COPY pyproject.toml /app/
RUN pip install --upgrade pip setuptools wheel && pip install .

# Copy source
COPY app /app/app
COPY interactive_cli.py /app/interactive_cli.py

# Default envs (can be overridden by docker-compose)
ENV HOST=0.0.0.0 \
    PORT=8000 \
    TEMPORAL_ADDRESS=temporal:7233

# Default command is API; worker will override in docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


