# =========================================================================
# EpidemiTracker - Backend Django (multi-stage)
# Stage 1 : build dépendances Python (+ libs système pour GeoDjango/PostGIS)
# Stage 2 : runtime minimal
# =========================================================================
ARG PYTHON_VERSION=3.11-slim-bookworm

# ---------- builder ----------
FROM python:${PYTHON_VERSION} AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    libffi-dev \
    libssl-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    pkg-config \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=0
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip wheel setuptools \
 && /opt/venv/bin/pip install -r requirements.txt \
 && if [ "$INSTALL_DEV" = "1" ]; then /opt/venv/bin/pip install -r requirements-dev.txt; fi

# ---------- runtime ----------
FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    libjpeg62-turbo \
    libpng16-16 \
    libfreetype6 \
    gdal-bin \
    libgdal32 \
    libgeos-c1v5 \
    libproj25 \
    libmagic1 \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY . /app

RUN mkdir -p /app/media /app/staticfiles /app/keys /app/logs \
 && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS -H "X-Forwarded-Proto: https" http://127.0.0.1:8000/healthz/ || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
