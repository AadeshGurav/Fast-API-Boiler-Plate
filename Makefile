# One entry point for everything a contributor does. `make help` lists the targets.
PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

.DEFAULT_GOAL := help
.PHONY: help setup up up-postgres up-mail down reset-data run test fuzz lint fmt config config-docs openapi lock graph hooks docker-build docker-up

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-14s %s\n", $$1, $$2}'

setup:  ## Create the venv, install dependencies, generate .env (random passwords) and config.local.toml
	@if command -v uv >/dev/null 2>&1; then \
	  uv sync --frozen --all-extras --quiet; \
	else \
	  echo "uv not found: using pip (install uv for a faster, locked setup: https://docs.astral.sh/uv/)"; \
	  $(PYTHON) -m venv $(VENV) && $(BIN)/pip install --quiet --require-hashes -r requirements-dev.txt; \
	fi
	@test -f .env || { \
	  mongo=$$($(BIN)/python -c 'import secrets;print(secrets.token_urlsafe(24))'); \
	  redis=$$($(BIN)/python -c 'import secrets;print(secrets.token_urlsafe(24))'); \
	  jwt=$$($(BIN)/python -c 'import secrets;print(secrets.token_urlsafe(64))'); \
	  mfa=$$($(BIN)/python -c 'import secrets;print(secrets.token_urlsafe(64))'); \
	  pg=$$($(BIN)/python -c 'import secrets;print(secrets.token_urlsafe(24))'); pport=$$($(BIN)/python scripts/free_port.py 5432); \
	  mport=$$($(BIN)/python scripts/free_port.py 27017); rport=$$($(BIN)/python scripts/free_port.py 6379); aport=$$($(BIN)/python scripts/free_port.py 8000); \
	  sed -e "s/MONGO_ROOT_PASSWORD=.*/MONGO_ROOT_PASSWORD=$$mongo/" -e "s/FABP_MONGO_PASSWORD=.*/FABP_MONGO_PASSWORD=$$mongo/" \
	      -e "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$$redis/" -e "s/FABP_REDIS_PASSWORD=.*/FABP_REDIS_PASSWORD=$$redis/" -e "s/FABP_JWT_SECRET=.*/FABP_JWT_SECRET=$$jwt/" -e "s/FABP_MFA_ENCRYPTION_KEY=.*/FABP_MFA_ENCRYPTION_KEY=$$mfa/" \
	      -e "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$$pg/" -e "s/FABP_POSTGRES_PASSWORD=.*/FABP_POSTGRES_PASSWORD=$$pg/" \
	      -e "s/POSTGRES_HOST_PORT=.*/POSTGRES_HOST_PORT=$$pport/" -e "s/FABP_POSTGRES_PORT=.*/FABP_POSTGRES_PORT=$$pport/" \
	      -e "s/APP_HOST_PORT=.*/APP_HOST_PORT=$$aport/" -e "s/FABP_APP_PORT=.*/FABP_APP_PORT=$$aport/" \
	      -e "s/MONGO_HOST_PORT=.*/MONGO_HOST_PORT=$$mport/" -e "s/FABP_MONGO_PORT=.*/FABP_MONGO_PORT=$$mport/" \
	      -e "s/REDIS_HOST_PORT=.*/REDIS_HOST_PORT=$$rport/" -e "s/FABP_REDIS_PORT=.*/FABP_REDIS_PORT=$$rport/" \
	      .env.example > .env; echo "created .env"; }
	@test -f config.local.toml || { cp config.local.toml.example config.local.toml; echo "created config.local.toml"; }

up:  ## Start MongoDB and Redis
	docker compose up -d --wait

up-postgres:  ## Start PostgreSQL too (then set app_database_provider = "postgres")
	docker compose --profile postgres up -d --wait

up-mail:  ## Start Mailpit: catches every email, inbox at http://127.0.0.1:8025
	docker compose --profile mail up -d

down:  ## Stop MongoDB and Redis (data is kept)
	docker compose down

reset-data:  ## Delete the local dev databases (Docker volumes) -- needed after regenerating .env
	docker compose --profile app down -v

run:  ## Run the API (generates a JWT secret on first start)
	$(BIN)/python main.py

test:  ## Run the test suite (needs no running services)
	$(BIN)/python -m pytest -q

fuzz:  ## Fuzz every API operation from the OpenAPI contract (Schemathesis, about a minute)
	$(BIN)/python -m pytest -q -m fuzz

lint:  ## Lint and format-check
	$(BIN)/ruff check app tests main.py config.py
	$(BIN)/ruff format --check app tests main.py config.py

fmt:  ## Format and auto-fix
	$(BIN)/ruff check --fix app tests main.py config.py
	$(BIN)/ruff format app tests main.py config.py

config:  ## Show every effective setting and where it came from; fails on mistakes
	$(BIN)/python -m app.settings show

config-docs:  ## Regenerate docs/CONFIGURATION.md from the settings model
	$(BIN)/python -m app.settings docs > docs/CONFIGURATION.md

lock:  ## Re-resolve uv.lock after editing dependencies in pyproject.toml, and export requirements*.txt
	uv lock
	@$(MAKE) --no-print-directory export-requirements

export-requirements:
	uv export --frozen --no-dev --no-emit-project --quiet -o requirements.txt
	uv export --frozen --no-dev --no-emit-project --quiet --extra s3 -o requirements-s3.txt
	uv export --frozen --no-dev --no-emit-project --quiet --extra postgres -o requirements-postgres.txt
	uv export --frozen --no-dev --no-emit-project --quiet --extra observability -o requirements-observability.txt
	uv export --frozen --all-extras --no-emit-project --quiet -o requirements-dev.txt

openapi:  ## Regenerate the committed API contract, docs/reference/openapi.json
	$(BIN)/python -m app.api.openapi > docs/reference/openapi.json

graph:  ## Refresh the code knowledge graph in graphify-out/ (needs: pipx install graphifyy==0.9.80)
	graphify update .

hooks:  ## Install git hooks: ruff before each commit, graph refresh after each commit
	$(BIN)/pip install --quiet pre-commit && $(BIN)/pre-commit install
	graphify hook install

docker-up:  ## Run the whole stack (API + MongoDB + Redis) in Docker
	docker compose --profile app up -d --build --wait

docker-build:  ## Build the production image
	docker build -t fastapi_boilerplate:local .
