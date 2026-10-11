"""The whole application on each real database CI provides: migrations, indexes, sign-in,
two-factor, files, audit and jobs, through the real middleware stack.

Runs only for the non-fake entries of ``CONTRACT_DATABASES`` (e.g. ``mongodb,postgres``).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.services.auth import totp
from tests.contract.conftest import _drop, _selected
from tests.test_auth_flow import PASSWORD, bearer, login, register

REAL = [name for name in _selected("CONTRACT_DATABASES", "fake") if name != "fake"]


@pytest.fixture(params=REAL or [pytest.param("none", marks=pytest.mark.skip("no real database"))])
def client(request, tmp_path):
    import shutil

    from app.api.app import create_app
    from app.api.openapi import ROOT
    from config import Config

    shutil.copy(ROOT / "config.toml", tmp_path)  # roles and groups; nothing machine-local
    config = Config(config_dir=tmp_path)
    config.data.update(
        {
            "app_database_provider": request.param,
            "app_database": f"fabp_app_{uuid.uuid4().hex[:12]}",
            "app_cache_provider": "memory",
            "jwt_secret": "x" * 64,
            "mfa_encryption_key": "y" * 64,
            "log_to_file": False,
            "cookie_secure": False,
            "rate_limit_enabled": False,
            "jobs_run_in_api": False,
            "file_storage_base_path": str(tmp_path / "uploads"),
        }
    )
    app = create_app(config)
    with TestClient(app) as test_client:  # runs the lifespan: connect, migrate, index
        test_client.services = app.state.services
        yield test_client
        run_drop = getattr(app.state.services.database_service, "backend", None)
        test_client.portal.call(_drop, run_drop)


def test_accounts_two_factor_files_audit_and_jobs(client):
    services = client.services
    assert register(client).status_code == 201
    client.headers.update(bearer(login(client)))

    # files: upload, list, download
    uploaded = client.post(
        "/api/v1/files/upload", files={"file": ("a.pdf", b"%PDF-1.4 hi", "application/pdf")}
    )
    assert uploaded.status_code == 201, uploaded.text
    assert client.get("/api/v1/files").json()["total"] == 1
    file_id = uploaded.json()["file_id"]
    download = client.get(f"/api/v1/files/{file_id}")
    assert download.content == b"%PDF-1.4 hi", download.text

    # two-factor: enrol, then sign in with a code
    secret = client.post("/api/v1/auth/mfa/totp", json={"password": PASSWORD}).json()["secret"]
    now = totp.current_step()
    assert (
        client.post(
            "/api/v1/auth/mfa/totp/confirm", json={"code": totp.code_at(secret, now - 1)}
        ).status_code
        == 200
    )
    challenge = login(client).json()["details"]["mfa_token"]
    done = client.post(
        "/api/v1/auth/login/mfa", json={"mfa_token": challenge, "code": totp.code_at(secret, now)}
    )
    assert done.status_code == 200, done.text

    # audit: the enrolment was recorded
    events, total, _ = client.portal.call(
        lambda: services.audit_service.list_events(action="mfa.enabled")
    )
    assert total == 1 and events[0]["at"].tzinfo is not None

    # jobs: enqueue, run, done
    ran = []

    @services.job_service.handler("smoke.job")
    async def smoke(payload):
        ran.append(payload)

    client.portal.call(services.job_service.enqueue, "smoke.job", {"ok": True})
    assert client.portal.call(services.job_service.run_once) == 1 and ran == [{"ok": True}]
