# Developer & Contributor Guide

> **For those who want to extend, maintain, or contribute to FastAPI Enterprise Foundation.**

---

## 🗂️ Code Structure

- `app/`
  - `api/` — API routers, middleware, dependencies
  - `core/` — Dependency injection container, interfaces, class store
  - `database/` — Async DB backends (MongoDB, Redis, PostgreSQL, SQLite)
  - `services/` — Business logic: auth, session, data, cache, error, logger
  - `utils/` — Utility functions (e.g., lifespan)
  - `static/` — Static files (CSS, JS)
  - `templates/` — Jinja2 templates (base, index, advanced, partials)
- `config.d/` — JSON config files (global/local, per-service)
- `main.py` — Entrypoint for running with Uvicorn
- `config.py` — Dynamic config loader

---

## 🧩 Adding Features or Services

- **New Service:**
  - Add to `app/services/`, implement interface if needed, register in `app/core/container.py`.
- **New API Route:**
  - Add to `app/api/routes/`, register in the main router.
- **New Middleware:**
  - Add to `app/api/middleware/`, register in `app/api/app.py`.
- **New DB Backend:**
  - Implement in `app/database/`, subclass `DatabaseInterface`.
- **New Config:**
  - Add a JSON file to `config.d/`, use `Config` for access.

---

## 🧪 Testing

- **Framework:** Pytest
- **Test Discovery:** `tests/` directory, `test_*.py` files
- **Run Tests:** `pytest`
- **Test Config:** See `project.toml` for test settings

---

## 🧹 Linting & Formatting

- **Black:** `black .`
- **isort:** `isort .`
- **Flake8:** `flake8 .`
- **Ruff:** `ruff .`
- **CI:** See `.github/workflows/flake8.yml`

---

## ⚙️ Extending Configuration

- Add new config keys to a JSON file in `config.d/` (use `*-global.json` for shared, `*-local.json` for secrets/overrides)
- Access config via `config["key"]` or `config.key`
- Config auto-loads and merges all files in `config.d/`

---

## 🤝 Contribution Guidelines

- Follow the Zen of Python (see `.cursorrules`)
- Write clear docstrings and type hints
- Prefer explicit, simple, and readable code
- Add/modify tests for new features
- Use dependency injection for all services
- Document new APIs and services
- Run linting and tests before PRs
- For major changes, open an issue or discussion first

---

For usage and setup, see the [Usage & Getting Started Guide](USAGE_README.md).
⬅️ [Back to Main README](README.md) 