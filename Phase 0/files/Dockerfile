# syntax=docker/dockerfile:1
# --- Base ---------------------------------------------------------------
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- Dependencies (cached layer) ---------------------------------------
FROM base AS deps
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# --- Runtime ------------------------------------------------------------
FROM base AS runtime
# Copy installed deps
COPY --from=deps /install /usr/local
# App source
COPY . .

# Non-root user
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
