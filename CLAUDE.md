# CLAUDE.md - AI Assistant Guide for Fast-API-Boiler-Plate

## Project Overview

Production-ready FastAPI boilerplate with enterprise features: JWT authentication, RBAC, OAuth2, multi-database support, structured logging, metrics, tracing, and a 13-layer middleware stack. Async-first architecture using dependency injection and interface-based design.

- **Language**: Python 3.10+ (`.python-version`: 3.10.19, Docker uses 3.11)
- **Framework**: FastAPI 0.115.13 + Uvicorn 0.34.3 (uvloop)
- **Databases**: MongoDB (Motor async), Redis (async), PostgreSQL (asyncpg), SQLite (aiosqlite)
- **Auth**: JWT (HS256) + Argon2 password hashing + OAuth2 (Google, Apple)

## Repository Structure

```
Fast-API-Boiler-Plate/
├── main.py                      # Entry point - uvicorn server launcher
├── config.py                    # Config class - loads JSON from config.d/
├── app/
│   ├── __init__.py              # Container init, service discovery, FastAPI app creation
│   ├── api/
│   │   ├── app.py               # AppFactory - creates/configures FastAPI instance
│   │   ├── middleware/          # 13 middleware components
│   │   └── routes/              # API endpoint routers
│   ├── core/
│   │   ├── container.py         # Dependency injection container (dependency-injector)
│   │   ├── class_store.py       # Service discovery registry
│   │   ├── dynamic_config.py    # Config base model
│   │   └── interfaces/          # Database and service interfaces
│   ├── database/
│   │   ├── mongodb.py           # Motor async MongoDB driver
│   │   └── redis.py             # Redis async client
│   ├── services/
│   │   ├── auth/                # Authentication (JWT, login, registration)
│   │   ├── rbac/                # Role-based access control
│   │   ├── oauth/               # OAuth2 provider integration
│   │   ├── data/                # Data access / repository layer
│   │   ├── session.py           # Session management
│   │   ├── logger/              # Structured JSON logging
│   │   ├── metrics/             # Prometheus metrics
│   │   ├── tracing/             # OpenTelemetry tracing
│   │   ├── sentry.py            # Error tracking
│   │   ├── password_service.py  # Argon2 hashing & validation
│   │   ├── cache.py             # Cache service
│   │   ├── retry_service.py     # Retry with backoff
│   │   ├── error/               # Centralized error handling
│   │   └── file/                # File upload/download
│   ├── models/                  # Pydantic data models
│   ├── utils/                   # Utility functions
│   ├── static/                  # CSS, JS assets
│   └── templates/               # Jinja2 HTML templates
├── config.d/                    # JSON configuration files (15 files)
├── tests/                       # Test directory (pytest)
├── docs/                        # Documentation
├── Dockerfile                   # python:3.11-slim, non-root user
├── docker-compose.yml           # MongoDB 8.0 + Redis 7.2
├── requirements.txt             # 98 pinned dependencies
├── project.toml                 # Ruff, Black, isort, pytest config
└── setup.cfg                    # Flake8 config
```

## Build & Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure (MongoDB + Redis)
docker-compose up -d

# Run the application
python main.py

# Run with Docker
docker build -t fastapi-app .
docker run -p 8000:8000 fastapi-app
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_example.py

# Run tests matching pattern
pytest -k "test_auth"
```

Test configuration is in `project.toml`:
- Test directory: `tests/`
- File pattern: `test_*.py`
- Framework: pytest + pytest-asyncio for async tests

## Linting & Formatting

```bash
# Format code
black .
isort .

# Lint
flake8 .
ruff check .
ruff check --fix .

# Type checking
mypy .
```

### Style Rules

- **Line length**: 120 characters (all tools)
- **Target Python**: 3.10
- **Black**: string normalization off
- **isort**: profile `black`
- **Ruff**: `select = ["ALL"]`, ignore `ANN401`
- **Flake8**: excludes `.git, __pycache__, docs, env, build, .vscode, .venv, .cursor, uploads, logs`

### CI Pipeline

GitHub Actions runs Flake8 on push and PR (`.github/workflows/flake8.yml`):
- Fails on syntax errors and undefined names (`E9, F63, F7, F82`)
- Reports all other warnings without failing

## Configuration System

All configuration lives in `config.d/` as JSON files. The `Config` class (`config.py`) loads them with priority: `regular < global < local`.

| File | Purpose |
|------|---------|
| `app-config-global.json` | App title, host, port, debug, workers |
| `auth-config-global.json` | JWT secret, token expiry, password policies |
| `mongodb-config-global.json` | MongoDB connection, pool settings |
| `redis-config-global.json` | Redis connection, cache TTL |
| `security-config-global.json` | CORS, security headers, HSTS, CSP |
| `rate-limit-config-global.json` | Rate limit tiers and thresholds |
| `session-config-global.json` | Session TTL, cookie settings |
| `oauth-config-global.json` | OAuth provider configs |
| `rbac-roles-global.json` | Role definitions with inheritance |
| `rbac-permissions-global.json` | Permission catalog |
| `rbac-groups-global.json` | Group-to-role mappings |
| `file-storage-config-global.json` | Upload directory, file size limits |
| `app-logs-config-global.json` | Log levels, rotation, formatting |
| `features-global.json` | Feature flags |
| `sentry-config-global.json` | Sentry DSN |

**Secrets**: Use `*-local.json` files (auto-added to `.gitignore`) for local overrides and secrets. Never commit `-local.json` files.

**Access**: `config.get("key")` or `config.key` (attribute-style).

## Architecture Patterns

### Dependency Injection
The app uses `dependency-injector` for DI. The `Container` (`app/core/container.py`) wires all services. Service discovery happens at startup via `ClassStore.discover_services()` scanning `app.services`, `app.api`, and `app.classes`.

### Application Startup Flow
1. `main.py` validates config and launches uvicorn
2. `app/__init__.py` creates `Container`, discovers services, creates FastAPI app
3. `AppFactory` (`app/api/app.py`) builds the app: middleware stack, routes, optional services

### Data Access (Repository Pattern)
Database operations are in `app/services/data/`:
- `users_ops.py` - User CRUD
- `rbac_ops.py` - Role/permission/group management
- `sessions_ops.py` - Session lifecycle
- `oauth_ops.py` - OAuth account linking
- `files_ops.py` - File operations
- `policies.py` - Authorization policies

### Middleware Stack (order matters)
Applied bottom-to-top (last registered = first executed):
1. Request logging
2. Error handler
3. Sentry
4. CORS
5. Request ID
6. Security headers
7. Timeout
8. Circuit breaker
9. Rate limiter
10. Session
11. Serialization
12. Template context
13. RBAC

## API Routes

All routes are under `/api/v1/`:

| Prefix | Module | Key Endpoints |
|--------|--------|---------------|
| `/auth` | `routes/auth.py` | register, login, refresh, logout, password reset, me |
| `/oauth` | `routes/oauth.py` | authorize, callback, link/unlink providers |
| `/rbac` | `routes/rbac.py` | roles, permissions, groups, user assignments |
| `/sessions` | `routes/sessions.py` | list active, revoke, details |
| `/files` | `routes/files.py` | upload, download, chunked upload, metadata, versions |
| `/` | `app.py` | health check, demo, favicon |

## Key Conventions

### Code Style
- Follow PEP 20 (Zen of Python): explicit over implicit, simple over complex
- Use `from __future__ import annotations` in all modules
- Type hints on all function signatures
- Docstrings with Args/Returns sections (Google style)
- Async-first: use `async def` for all I/O-bound operations

### Models
- All models are Pydantic v2 (`pydantic==2.5.0`)
- Separate models per concern: `User`, `UserCreate`, `UserUpdate`, `UserPublic`, `UserInDB`
- Models live in `app/models/`

### Error Handling
- `ErrorService` centralizes error responses
- `ErrorHandlerMiddleware` catches all unhandled exceptions
- Return standardized JSON error responses
- Log all errors with request context

### Security
- Passwords hashed with Argon2 (`passlib` + `argon2-cffi`)
- JWT tokens: access (short-lived) + refresh (7 days)
- Rate limiting per endpoint tier (auth: 10/300s, api: 1000/60s)
- Security headers via middleware (HSTS, CSP, X-Frame-Options)
- Non-root Docker user

### Logging
- Structured JSON logs via `python-json-logger`
- Async log writers with `asyncio.Queue`
- Request ID propagation via `contextvars`
- Rotating file handlers: `logs/debug.log`, `logs/info.log`, `logs/error.log`

## Docker / Infrastructure

```bash
# Start MongoDB + Redis
docker-compose up -d

# MongoDB: localhost:27017 (root/ag)
# Redis: localhost:6379
```

Services are on the `ag-network` bridge network. MongoDB has a 2GB memory limit and health checks.

## Files to Never Commit
- `config.d/*-local.json` (secrets, local overrides)
- `logs/` directory
- `uploads/` directory
- `.venv/` / `.environment/`
- `.env` files
