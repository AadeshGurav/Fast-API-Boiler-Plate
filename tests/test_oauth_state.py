"""The OAuth callback must only accept the state this browser was given."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_oauth_service
from app.api.routes.oauth import router


@pytest.fixture
def client() -> TestClient:
    oauth_service = MagicMock()
    oauth_service.get_authorization_url.side_effect = lambda provider, state: (
        f"https://idp.example/auth?state={state}"
    )
    app = FastAPI()
    app.state.services = MagicMock()
    app.state.services.config = {"cookie_secure": False}
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_oauth_service] = lambda: oauth_service
    return TestClient(app, follow_redirects=False)


def test_authorize_binds_state_to_an_httponly_cookie(client):
    response = client.get("/api/v1/oauth/google/authorize")

    state = response.headers["location"].split("state=")[1]
    cookie = response.headers["set-cookie"]
    assert f"oauth_state_google={state}" in cookie
    assert "HttpOnly" in cookie


@pytest.mark.parametrize("cookie_state", [None, "something-else"])
def test_callback_rejects_missing_or_mismatched_state(client, cookie_state):
    if cookie_state:
        client.cookies.set("oauth_state_google", cookie_state)

    response = client.get("/api/v1/oauth/google/callback?code=abc&state=forged")

    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()
