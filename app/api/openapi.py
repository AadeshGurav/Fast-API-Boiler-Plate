"""The committed OpenAPI contract: ``python -m app.api.openapi > docs/reference/openapi.json``.

The schema is built from ``config.toml`` defaults only, never from ``config.local.toml``,
``.env`` or ``FABP_*`` variables, so every machine and CI produce the same bytes. A test
compares it with the committed file, so any change to the API's contract shows up in review.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs" / "reference" / "openapi.json"


def build_schema() -> dict[str, Any]:
    """The OpenAPI document the application serves with project defaults."""
    from app.api.app import create_app
    from config import ENV_PREFIX, Config

    saved = {k: v for k, v in os.environ.items() if k.startswith(ENV_PREFIX)}
    for name in saved:
        del os.environ[name]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(ROOT / "config.toml", tmp)
            config = Config(config_dir=tmp)
            # Placeholders: building the schema neither signs tokens nor writes files.
            config.data.update(
                {"jwt_secret": "x" * 64, "log_to_file": False, "file_storage_base_path": tmp}
            )
            return create_app(config).openapi()
    finally:
        os.environ.update(saved)


def render(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    print(render(build_schema()), end="")
