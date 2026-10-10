"""Health, readiness, metrics and the admin-only operational routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_auth_flow import bearer, login, make_admin, register


@pytest.mark.parametrize("path", ["health", "live", "ready", "startup"])
def test_probes_are_public_and_never_500(env, path):
    response = env.client().get(f"/api/v1/{path}")

    assert response.status_code in (200, 503), response.text
    assert response.headers["x-request-id"]


def test_ready_reports_dependency_state_without_leaking_errors(env):
    body = env.client().get("/api/v1/ready").json()

    assert body["checks"]["database"]["status"] == "ready"
    assert body["checks"]["cache"]["status"] == "ready"
    assert "Traceback" not in str(body)


@pytest.fixture
def metrics_env(tmp_path):
    """The real app with metrics switched on."""
    from tests.conftest import build_test_app

    app, services = build_test_app(tmp_path, metrics_enabled=True)

    class Env:
        pass

    Env.app, Env.services, Env.auth_service = app, services, services.auth_service
    Env.client = staticmethod(lambda: TestClient(app))
    return Env


def test_metrics_require_an_admin(metrics_env):
    env = metrics_env
    client = env.client()
    register(client)
    assert client.get("/api/v1/metrics").status_code == 401
    assert client.get("/api/v1/metrics", headers=bearer(login(client))).status_code == 403

    make_admin(env)
    admin = env.client().get("/api/v1/metrics", headers=bearer(login(env.client(), "root")))
    assert admin.status_code == 200
    assert "http_requests_total" in admin.text


def test_metric_series_are_labelled_by_route_template(metrics_env):
    env = metrics_env
    client = env.client()
    for random_path in ("/wp-admin/a", "/wp-admin/b", "/x/1", "/x/2"):
        client.get(random_path)
    make_admin(env)
    text = env.client().get("/api/v1/metrics", headers=bearer(login(env.client(), "root"))).text

    assert "wp-admin" not in text and 'endpoint="/x/' not in text  # scanners add no series
    assert 'endpoint="unmatched"' in text


def test_two_apps_in_one_process_do_not_collide_on_metric_names(tmp_path):
    from tests.conftest import build_test_app

    build_test_app(tmp_path, metrics_enabled=True)
    build_test_app(tmp_path, metrics_enabled=True)  # used to raise DuplicateTimeseries


def cors_client(tmp_path):
    from tests.conftest import build_test_app

    app, _ = build_test_app(tmp_path, cors_origins=["https://app.example.com"])
    return TestClient(app)


def test_security_headers_and_cors_are_present_even_on_rejections(tmp_path):
    response = cors_client(tmp_path).get(
        "/api/v1/auth/me", headers={"Origin": "https://app.example.com"}
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_cors_preflight_is_answered_without_credentials(tmp_path):
    response = cors_client(tmp_path).options(
        "/api/v1/files/",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]


def test_unknown_origins_get_no_cors_grant(env):
    response = env.client().get("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_validation_errors_are_problem_documents_without_echoing_input(env):
    response = env.client().post(
        "/api/v1/auth/login", json={"username": "ada", "password": ["not", "a", "string"]}
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert "not" not in str(response.json().get("errors"))  # submitted input is not reflected


def test_rate_limit_answers_429_with_retry_after_and_is_per_client_tier(tmp_path):
    from tests.conftest import build_test_app

    app, _ = build_test_app(
        tmp_path,
        rate_limit_enabled=True,
        rate_limit_tiers={"default": {"requests": 2, "window": 60}},
    )
    client = TestClient(app)

    statuses = [client.get("/").status_code for _ in range(3)]
    limited = client.get("/")

    assert statuses == [200, 200, 429]
    assert limited.headers["retry-after"].isdigit()
    assert limited.headers["content-type"].startswith("application/problem+json")
    assert client.get("/api/v1/live").status_code == 200  # probes are never throttled
