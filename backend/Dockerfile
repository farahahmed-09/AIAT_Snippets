FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg curl fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY ai_core ./ai_core
# Fail fast with an actionable message when the operator cloned without
# `--recurse-submodules` (ai_core/ is an empty placeholder in that case).
RUN test -f ai_core/pyproject.toml || ( \
    echo "ERROR: backend/ai_core/ is empty — run 'git submodule update --init --recursive' before docker build" \
    && exit 1)
RUN pip install --upgrade pip && pip install ./ai_core && pip install .

COPY app ./app

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app -d /app -s /usr/sbin/nologin app \
    && mkdir -p /app/beat /app/.cache \
    && chown -R app:app /app
ENV HOME=/app XDG_CACHE_HOME=/app/.cache
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
