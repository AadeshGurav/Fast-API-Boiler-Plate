"""Pure-ASGI middleware behaviour on a bare app, independent of the real stack."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from app.api.middleware.error_handler import ErrorHandlerMiddleware
from app.api.middleware.timeout import TimeoutMiddleware
from config import Config


def build(tmp_path, **settings) -> TestClient:
    config = Config(config_dir=tmp_path)
    config.data.update(settings)
    app = FastAPI()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret internals")

    @app.get("/slow")
    async def slow():
        await asyncio.sleep(1)

    @app.get("/stream")
    async def stream():
        async def chunks():
            for i in range(3):
                yield f"{i}\n".encode()

        return StreamingResponse(chunks())

    app.add_middleware(TimeoutMiddleware, config=config, logger=MagicMock())
    app.add_middleware(
        ErrorHandlerMiddleware, config=config, logger=MagicMock(), error_service=None
    )
    return TestClient(app, raise_server_exceptions=False)


def test_escaping_exceptions_become_generic_problem_500s(tmp_path):
    response = build(tmp_path).get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert "secret internals" not in response.text


def test_slow_requests_get_a_504(tmp_path):
    response = build(tmp_path, request_timeout_seconds=0.05).get("/slow")

    assert response.status_code == 504


def test_streaming_responses_pass_through_intact(tmp_path):
    assert build(tmp_path).get("/stream").text == "0\n1\n2\n"
