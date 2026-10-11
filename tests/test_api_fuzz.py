"""Property-based API fuzzing with Schemathesis: generated requests from the OpenAPI contract.

Every operation is called with many generated inputs, signed in as an administrator, and must
never answer 5xx, and must answer with the status codes, content types and bodies the schema
declares. Marked ``fuzz`` and kept out of ``make test`` (it takes a minute); run it with
``make fuzz`` (CI does, on every pull request).
"""

from __future__ import annotations

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.checks import not_a_server_error
from schemathesis.specs.openapi.checks import (
    content_type_conformance,
    response_schema_conformance,
    status_code_conformance,
)

from tests.conftest import build_test_app
from tests.test_auth_flow import PASSWORD, make_admin

pytestmark = pytest.mark.fuzz

# Uploads take multipart bodies that only exercise the multipart parser; the two-step sign-in
# needs a live challenge; OAuth answers a deliberate 503 while no provider is configured. All
# three have targeted tests elsewhere.
EXCLUDED = r"^/api/v1/(files/upload|auth/login/mfa|oauth/)"


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    app, services = build_test_app(
        tmp_path_factory.mktemp("fuzz"), passkeys_enabled=True, webauthn_rp_id="localhost"
    )
    env = type("Env", (), {"auth_service": services.auth_service})
    make_admin(env)
    return app


schema = schemathesis.pytest.from_fixture("api_schema").exclude(path_regex=EXCLUDED)


@pytest.fixture(scope="module")
def api_schema(app):
    from fastapi.testclient import TestClient

    client = TestClient(app)
    token = client.post(
        "/api/v1/auth/login", json={"username": "root", "password": PASSWORD}
    ).json()["tokens"]["access_token"]
    loaded = schemathesis.openapi.from_asgi("/openapi.json", app)
    loaded.config.headers = {"Authorization": f"Bearer {token}"}
    return loaded


@schema.parametrize()
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_every_operation_honours_its_contract(case):
    case.call_and_validate(
        checks=[
            not_a_server_error,
            status_code_conformance,
            content_type_conformance,
            response_schema_conformance,
        ]
    )
