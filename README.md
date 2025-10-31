# FastAPI Enterprise Foundation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()

> **A modern, production-grade FastAPI boilerplate for enterprise apps. Async, secure, modular, and extensible.**

---

## 🚀 Features

| 🧩 | **Modular Architecture** | Dependency Injection (via `dependency-injector`), Service Layer, Repository Pattern (MongoDB, Redis, PostgreSQL, SQLite), Factory Pattern, ClassStore for extensibility, Modular API Routing, Extensible Service Registration |
|----|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 🔒 | **Security First**      | RBAC (Role-Based Access Control), JWT Authentication (access/refresh tokens, HttpOnly cookies, rotation, expiry), Session Management (Redis-backed, TTL, cookies, extension), Rate Limiting, CORS Protection |
| ⚡ | **Async Everything**     | Full async support for DB, cache, and API. Unified Data Service (async CRUD, upsert, cache-first reads, cache invalidation, lifecycle management)                                                            |
| 🗄️ | **Database Agnostic**   | MongoDB (Motor), Redis (async), PostgreSQL (SQLAlchemy async), SQLite (aiosqlite)                                                                                                                          |
| 🧰 | **Rich Middleware**      | Middleware Stack: CORS, error handler, rate limiter, session, serialization, template context. Centralized Error Handling (logging, formatting, returning errors)                                           |
| 📝 | **Jinja2 Templates**     | Inheritance, includes, filters, context injection, static file integration                                                                                                                                    |
| 🛠️ | **Dynamic Config**      | Loads from `config.d/*.json`, supports global/local overrides, attribute and dict access, auto .gitignore for local secrets                                                                                  |
| 📊 | **Comprehensive Logging**| Rotating file logging (debug, info, error logs), console output, contextual info, log directory management                                                                                                    |
| 🧪 | **Testing & Linting**    | Type hints & modern Python, Testing Support (Pytest, test discovery via `project.toml`), Linting & Formatting (Black, isort, Flake8, Ruff)                                                                      |
| ⚡ | **Caching Layer**        | Redis-backed, decorator for function result caching, pattern-based cache clearing                                                                                                                              |
| 🚨 | **Error Tracking**       | Sentry integration for error tracking, performance monitoring, session tracking, breadcrumbs, user context, custom filtering, and distributed tracing                                                           |

---

## 🏗️ Architecture Overview

```FastAPI App
│
├── app/
│   ├── api/           # Routers, middleware, dependencies
│   ├── core/          # DI container, interfaces, class store
│   ├── database/      # Async DB backends
│   ├── services/      # Business logic, auth, session, data, cache
│   ├── utils/         # Utility functions
│   ├── static/        # Static files
│   └── templates/     # Jinja2 templates
│
├── config.d/          # JSON config files
├── main.py            # Entrypoint
├── config.py          # Config loader
└── ...
```

---

## 📚 More
- [Usage & Getting Started Guide](USAGE_README.md)
- [Developer & Contributor Guide](DEVELOPER_README.md)
- [Sentry Integration Guide](SENTRY_INTEGRATION.md)
- [API Docs](/docs)

---

## 📄 License

This project is licensed under the [MIT License](./LICENSE).

---

*For installation, usage, and contribution, see the linked guides above.*

---

© 2024 FastAPI Enterprise Foundation
