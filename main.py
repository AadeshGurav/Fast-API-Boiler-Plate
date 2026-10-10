"""Run the API: ``python main.py`` (or ``make run``).

All behaviour comes from configuration (see docs/CONFIGURATION.md); ``python -m
app.settings show`` prints the effective values.
"""

from __future__ import annotations

import sys

import uvicorn

from config import Config, ConfigError


def main() -> int:
    """Validate configuration, then start the server."""
    try:
        config = Config()
        config.ensure_secret("jwt_secret")
    except ConfigError as e:
        print(f"Configuration is invalid:\n{e}", file=sys.stderr)
        return 1

    if config["app_host"] == "0.0.0.0":  # noqa: S104 - this is the warning about it
        print(
            "WARNING: binding to 0.0.0.0 exposes the app on every network interface; "
            "do this only in a container or behind a reverse proxy.",
            file=sys.stderr,
        )

    uvicorn.run(
        "app.api.app:create_app",
        factory=True,
        host=config["app_host"],
        port=config["app_port"],
        workers=1 if config["app_reload"] else config["app_workers"],
        reload=config["app_reload"],
        log_level=config["uvicorn_log_level"],
        access_log=config["log_uvicorn"],
        proxy_headers=False,  # client IPs come from trusted_proxy_count, not blind trust
        server_header=False,
        date_header=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
