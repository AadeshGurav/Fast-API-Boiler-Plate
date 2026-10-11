# syntax=docker/dockerfile:1

# ---- build: resolve nothing, install exactly what uv.lock says ----------------------------
FROM ghcr.io/astral-sh/uv:0.12.18 AS uv
FROM python:3.11-slim AS build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
ARG INSTALL_S3=false
ARG INSTALL_POSTGRES=false
ARG INSTALL_OBSERVABILITY=false
RUN extras="" \
    && if [ "$INSTALL_S3" = "true" ]; then extras="$extras --extra s3"; fi \
    && if [ "$INSTALL_POSTGRES" = "true" ]; then extras="$extras --extra postgres"; fi \
    && if [ "$INSTALL_OBSERVABILITY" = "true" ]; then extras="$extras --extra observability"; fi \
    && uv sync --frozen --no-dev $extras

# ---- runtime: the virtualenv and the app, no installer ------------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    FABP_APP_HOST=0.0.0.0 \
    FABP_REDIS_HOST=redis \
    FABP_MONGO_HOST=mongodb

# The base image's pip, setuptools and wheel vendor copies of urllib3, msgpack and others that
# image scanners flag; the app needs no installer at run time.
RUN pip uninstall -y pip setuptools wheel

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY app ./app
COPY config.toml ./
COPY config.py main.py ./

# Run unprivileged; /app/the working directory (generated secrets) and /app/uploads must be writable.
RUN useradd --create-home appuser \
    && mkdir -p /app/uploads /app/logs \
    && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/live', timeout=3).status == 200 else 1)"

# Every setting can be given as FABP_<NAME> (docs/CONFIGURATION.md). Secrets: FABP_JWT_SECRET,
# FABP_MONGO_PASSWORD, FABP_REDIS_PASSWORD ... or mount /app/config.secrets.toml.
CMD ["python", "main.py"]
