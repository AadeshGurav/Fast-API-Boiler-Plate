# One entry point for everything a contributor does. `make help` lists the targets.
PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

.DEFAULT_GOAL := help
.PHONY: help setup up down reset-data run test lint fmt config config-docs graph hooks docker-build docker-up

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-14s %s\n", $$1, $$2}'

setup:  ## Create the venv, install dependencies, generate .env (random passwords) and config.local.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --quiet --upgrade pip
	$(BIN)/pip install --quiet -r requirements-dev.txt
	@test -f .env || { \
	  mongo=$$($(BIN)/python -c 'import secrets;print(secrets.token_urlsafe(24))'); \
	  redis=$$($(BIN)/python -c 'import secrets;print(secrets.token_urlsafe(24))'); \
	  jwt=$$($(BIN)/python -c 'import secrets;print(secrets.token_urlsafe(64))'); \
	  mport=$$($(BIN)/python scripts/free_port.py 27017); rport=$$($(BIN)/python scripts/free_port.py 6379); aport=$$($(BIN)/python scripts/free_port.py 8000); \
	  sed -e "s/MONGO_ROOT_PASSWORD=.*/MONGO_ROOT_PASSWORD=$$mongo/" -e "s/FABP_MONGO_PASSWORD=.*/FABP_MONGO_PASSWORD=$$mongo/" \
	      -e "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$$redis/" -e "s/FABP_REDIS_PASSWORD=.*/FABP_REDIS_PASSWORD=$$redis/" -e "s/FABP_JWT_SECRET=.*/FABP_JWT_SECRET=$$jwt/" \
	      -e "s/APP_HOST_PORT=.*/APP_HOST_PORT=$$aport/" -e "s/FABP_APP_PORT=.*/FABP_APP_PORT=$$aport/" \
	      -e "s/MONGO_HOST_PORT=.*/MONGO_HOST_PORT=$$mport/" -e "s/FABP_MONGO_PORT=.*/FABP_MONGO_PORT=$$mport/" \
	      -e "s/REDIS_HOST_PORT=.*/REDIS_HOST_PORT=$$rport/" -e "s/FABP_REDIS_PORT=.*/FABP_REDIS_PORT=$$rport/" \
	      .env.example > .env; echo "created .env"; }
	@test -f config.local.toml || { cp config.local.toml.example config.local.toml; echo "created config.local.toml"; }

up:  ## Start MongoDB and Redis
	docker compose up -d --wait

down:  ## Stop MongoDB and Redis (data is kept)
	docker compose down

reset-data:  ## Delete the local dev databases (Docker volumes) -- needed after regenerating .env
	docker compose --profile app down -v

run:  ## Run the API (generates a JWT secret on first start)
	$(BIN)/python main.py

test:  ## Run the test suite (needs no running services)
	$(BIN)/python -m pytest -q

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

graph:  ## Refresh the code knowledge graph in graphify-out/ (needs: pipx install graphifyy==0.9.80)
	graphify update .

hooks:  ## Install git hooks: ruff before each commit, graph refresh after each commit
	$(BIN)/pip install --quiet pre-commit && $(BIN)/pre-commit install
	graphify hook install

docker-up:  ## Run the whole stack (API + MongoDB + Redis) in Docker
	docker compose --profile app up -d --build --wait

docker-build:  ## Build the production image
	docker build -t fastapi_boilerplate:local .
