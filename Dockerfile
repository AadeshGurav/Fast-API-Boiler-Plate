# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FABP_APP_HOST=0.0.0.0 \
    FABP_REDIS_HOST=redis \
    FABP_MONGO_HOST=mongodb

WORKDIR /app

# Dependencies first: this layer is only rebuilt when requirements.txt changes.
COPY requirements.txt requirements-s3.txt requirements-postgres.txt ./
ARG INSTALL_S3=false
ARG INSTALL_POSTGRES=false
RUN pip install --upgrade pip && pip install -r requirements.txt \
    && if [ "$INSTALL_S3" = "true" ]; then pip install -r requirements-s3.txt; fi \
    && if [ "$INSTALL_POSTGRES" = "true" ]; then pip install -r requirements-postgres.txt; fi

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
