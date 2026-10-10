"""Regression tests for the findings of the security audit."""

from __future__ import annotations

import asyncio
import io
import ssl

import pytest
from PIL import Image

from app.models.oauth import OAuthProvider, OAuthUserInfo
from app.models.session import DeviceInfo
from app.models.user import UserCreate
from app.services.file.image_processor import ImageProcessor
from app.services.file.spreadsheet_processor import SpreadsheetProcessor
from app.services.file.xlsx_patch import UnsupportedWorkbookError, patch_sheet_xml
from app.services.oauth.base import OAuthBase
from tests.conftest import run

PASSWORD = "Str0ng!Passw0rd"
DEVICE = DeviceInfo(ip_address="203.0.113.7", user_agent="pytest", fingerprint="f")


def make_user(env, name, roles=None, email=None):
    run(
        env.auth_service.register_user(
            UserCreate(
                username=name,
                email=email or f"{name}@example.com",
                password=PASSWORD,
                roles=roles or [],
            )
        )
    )


def bearer(client, name):
    reply = client.post("/api/v1/auth/login", json={"username": name, "password": PASSWORD})
    return {"Authorization": "Bearer " + reply.json()["tokens"]["access_token"]}


def user_id(client, headers, name):
    users = client.get("/api/v1/users", headers=headers).json()["users"]
    return next(u["id"] for u in users if u["username"] == name)


# ---- authorization ------------------------------------------------------------------


def test_manager_cannot_suspend_an_administrator_but_can_suspend_a_user(env):
    make_user(env, "root", ["admin"])
    make_user(env, "mgr", ["manager"])
    make_user(env, "bob")
    client = env.client()
    manager, admin = bearer(client, "mgr"), bearer(client, "root")

    admin_id = user_id(client, admin, "root")
    blocked = client.patch(
        f"/api/v1/users/{admin_id}", json={"status": "suspended"}, headers=manager
    )
    assert blocked.status_code == 403
    assert client.get("/api/v1/auth/me", headers=admin).status_code == 200

    bob_id = user_id(client, admin, "bob")
    allowed = client.patch(f"/api/v1/users/{bob_id}", json={"status": "suspended"}, headers=manager)
    assert allowed.status_code == 200

    # An administrator may still suspend another administrator.
    make_user(env, "root2", ["admin"])
    root2_id = user_id(client, admin, "root2")
    assert (
        client.patch(
            f"/api/v1/users/{root2_id}", json={"status": "suspended"}, headers=admin
        ).status_code
        == 200
    )


def test_oauth_sign_in_does_not_inherit_a_pre_registered_unverified_account(env):
    client = env.client()
    squatter = {
        "username": "squatter",
        "email": "victim@example.com",
        "password": PASSWORD,
        "first_name": "a",
        "last_name": "b",
    }
    assert client.post("/api/v1/auth/register", json=squatter).status_code == 201
    stale = bearer(client, "squatter")

    service = env.services
    oauth = OAuthBase(service.config, service.logger, service.data_service)
    info = OAuthUserInfo(
        provider_user_id="g-victim", email="victim@example.com", email_verified=True, name="V"
    )
    user = run(oauth.create_or_link_user(info, OAuthProvider.GOOGLE))

    assert user.username == "squatter"  # same account, linked to the real owner
    wrong = client.post("/api/v1/auth/login", json={"username": "squatter", "password": PASSWORD})
    assert wrong.status_code == 401  # the squatter's password no longer works
    assert client.get("/api/v1/auth/me", headers=stale).status_code == 401  # nor their session


def test_unlinked_provider_identity_cannot_sign_in(env):
    service = env.services
    oauth = OAuthBase(service.config, service.logger, service.data_service)
    info = OAuthUserInfo(
        provider_user_id="g-1", email="a@example.com", email_verified=True, name="A"
    )
    first = run(oauth.create_or_link_user(info, OAuthProvider.GOOGLE))
    run(oauth.create_or_link_user(info, OAuthProvider.GOOGLE))  # second sign-in warms any cache

    assert run(oauth.unlink_oauth_account(first.id, OAuthProvider.GOOGLE))

    unverified = info.model_copy(update={"email_verified": False})
    with pytest.raises(ValueError):
        run(oauth.create_or_link_user(unverified, OAuthProvider.GOOGLE))


# ---- login --------------------------------------------------------------------------


def test_login_username_is_bounded(env):
    reply = env.client().post(
        "/api/v1/auth/login", json={"username": "u" * 65, "password": PASSWORD}
    )
    assert reply.status_code == 422


def test_parallel_wrong_guesses_cannot_outnumber_the_lockout_threshold(env, monkeypatch):
    make_user(env, "alice")
    auth = env.auth_service
    verifications = 0
    real_verify = auth.password_service.averify_password

    async def counting_verify(password, hashed):
        nonlocal verifications
        if hashed != auth._timing_hash:  # the dummy hash is the "locked out" path
            verifications += 1
        return await real_verify(password, hashed)

    monkeypatch.setattr(auth.password_service, "averify_password", counting_verify)

    async def burst():
        return await asyncio.gather(
            *(auth.authenticate("alice", f"wrong-{i}", DEVICE) for i in range(30)),
            return_exceptions=True,
        )

    run(burst())
    assert verifications <= auth.max_failed_logins  # the rest were refused without a check
    record = run(env.services.data_service.users.get_user_by_username("alice", fresh=True))
    assert record.get("locked_until") is not None


# ---- spreadsheets -------------------------------------------------------------------


def test_sheet_xml_with_comments_or_cdata_is_refused():
    sheet = '<worksheet xmlns="x"><sheetData><!--<row r="1">--></sheetData></worksheet>'
    with pytest.raises(UnsupportedWorkbookError):
        patch_sheet_xml(sheet, {(1, 1): "y"})
    with pytest.raises(UnsupportedWorkbookError):
        patch_sheet_xml("<worksheet><sheetData><![CDATA[x]]></sheetData></worksheet>", {(1, 1): 1})


def test_parsing_stops_at_the_cell_limit():
    import openpyxl

    workbook = openpyxl.Workbook()
    for _ in range(10):
        workbook.active.append(list(range(10)))
    buffer = io.BytesIO()
    workbook.save(buffer)

    with pytest.raises(ValueError, match="limit"):
        SpreadsheetProcessor._parse(buffer.getvalue(), "xlsx", 50)
    assert SpreadsheetProcessor._parse(buffer.getvalue(), "xlsx", 1000)


# ---- files --------------------------------------------------------------------------


def test_image_beyond_the_pixel_limit_is_refused_before_decoding():
    buffer = io.BytesIO()
    Image.new("L", (8000, 7500)).save(buffer, "PNG")  # 60 MP: Pillow only warns here

    with pytest.raises(Image.DecompressionBombError):
        ImageProcessor._render_thumbnails(buffer.getvalue(), [64])


def test_dot_only_filenames_do_not_reach_the_storage_path(env):
    for name in (".", "..", "..."):
        path = env.file_service._generate_storage_path("u", "f", 1, name)
        assert path.endswith("/file")


def test_rename_is_length_checked(env):
    make_user(env, "carol")
    client = env.client()
    headers = bearer(client, "carol")
    upload = client.post(
        "/api/v1/files/upload", files={"file": ("a.txt", b"hello", "text/plain")}, headers=headers
    )
    file_id = upload.json()["file_id"]
    too_long = client.put(f"/api/v1/files/{file_id}", json={"filename": "n" * 256}, headers=headers)
    assert too_long.status_code == 422


def test_downloads_are_not_cacheable_by_shared_caches(env):
    make_user(env, "dave")
    client = env.client()
    headers = bearer(client, "dave")
    file_id = client.post(
        "/api/v1/files/upload", files={"file": ("a.txt", b"hello", "text/plain")}, headers=headers
    ).json()["file_id"]
    reply = client.get(f"/api/v1/files/{file_id}", headers=headers)
    assert reply.headers["cache-control"] == "private, no-store"


def test_chunks_much_larger_than_the_declared_average_are_refused(env):
    handler = env.file_service.chunked_upload_handler
    run(
        handler.start_upload(
            user_id="u1",
            upload_id="upload-0001",
            total_chunks=3,
            total_size=1000,
            filename="a.txt",
            content_type="text/plain",
        )
    )
    assert run(handler.save_chunk("u1", "upload-0001", 1, b"x" * 600)) is True  # <= 2 x 334
    assert run(handler.save_chunk("u1", "upload-0001", 2, b"x" * 5000)) is False


# ---- outbound / config --------------------------------------------------------------


def test_smtp_starttls_verifies_the_server_certificate(monkeypatch):
    from app.services import mailer

    seen = {}

    class FakeSMTP:
        def __init__(self, *args, **kwargs): ...
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self, context=None):
            seen["context"] = context

        def login(self, *args): ...
        def send_message(self, message): ...

    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    config = {"smtp_host": "h", "smtp_port": 587, "smtp_starttls": True, "smtp_username": ""}
    mailer._send_blocking(config, mailer.EmailMessage())

    assert seen["context"].verify_mode == ssl.CERT_REQUIRED
    assert seen["context"].check_hostname is True


def test_sentry_never_sends_request_bodies(monkeypatch):
    from unittest.mock import MagicMock

    from app.services import sentry

    captured = {}
    monkeypatch.setattr(sentry.sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))
    config = {
        "sentry_dsn": "https://key@example.invalid/1",
        "sentry_environment": "t",
        "app_version": "1",
        "sentry_traces_sample_rate": 0.0,
        "sentry_profiles_sample_rate": 0.0,
    }
    sentry.SentryService(MagicMock(), config)

    assert captured["max_request_body_size"] == "never"
    assert "new_password" in captured["event_scrubber"].denylist


def test_placeholder_jwt_secret_is_refused():
    from pydantic import ValidationError

    from app.settings import Settings

    with pytest.raises(ValidationError, match="placeholder"):
        Settings(jwt_secret="change-me-generated-by-make-setup")


# ---- second round: quota, CSRF, slow bodies, CORS, purging soft-deleted files ------------


def upload(client, headers, name="a.txt", data=b"hello"):
    return client.post(
        "/api/v1/files/upload", files={"file": (name, data, "text/plain")}, headers=headers
    )


def test_storage_quota_counts_soft_deleted_files_and_hard_delete_frees_it(env):
    make_user(env, "erin")
    client = env.client()
    headers = bearer(client, "erin")
    env.file_service.user_quota = 12

    first = upload(client, headers, "a.txt", b"0123456789")
    assert first.status_code == 201
    assert upload(client, headers, "b.txt", b"abcdef").status_code == 400  # 10 + 6 > 12

    file_id = first.json()["file_id"]
    assert client.delete(f"/api/v1/files/{file_id}", headers=headers).status_code == 200
    assert upload(client, headers, "b.txt", b"abcdef").status_code == 400  # soft delete keeps bytes

    purge = client.delete(f"/api/v1/files/{file_id}?hard_delete=true", headers=headers)
    assert purge.status_code == 200  # a soft-deleted file can be purged
    assert upload(client, headers, "b.txt", b"abcdef").status_code == 201


def test_a_file_cannot_collect_unbounded_versions(env):
    make_user(env, "finn")
    client = env.client()
    headers = bearer(client, "finn")
    env.file_service.max_versions = 2
    file_id = upload(client, headers).json()["file_id"]
    version = lambda data: client.post(  # noqa: E731
        f"/api/v1/files/{file_id}/versions",
        files={"file": ("a.txt", data, "text/plain")},
        headers=headers,
    )
    assert version(b"two").status_code == 201
    assert version(b"three").status_code == 400


def test_cookie_authenticated_writes_from_foreign_origins_are_refused(env):
    make_user(env, "gina")
    client = env.client()
    login = client.post("/api/v1/auth/login", json={"username": "gina", "password": PASSWORD})
    assert login.status_code == 200  # the cookies are now in the client's jar

    hostile = client.post("/api/v1/auth/logout", headers={"Origin": "https://evil.example"})
    assert hostile.status_code == 403
    assert hostile.json()["code"] == "csrf_origin_rejected"
    opaque = client.post("/api/v1/auth/logout", headers={"Origin": "null"})
    assert opaque.status_code == 403

    # Same-origin browsers, and non-browser clients (no Origin), still work.
    assert client.post(
        "/api/v1/auth/logout", headers={"Origin": "http://testserver"}
    ).status_code in (
        200,
        204,
    )


def test_bearer_requests_are_not_subject_to_the_origin_check(env):
    make_user(env, "hank")
    client = env.client()
    headers = bearer(client, "hank")
    client.cookies.clear()
    reply = client.post(
        "/api/v1/auth/logout", headers={**headers, "Origin": "https://evil.example"}
    )
    assert reply.status_code != 403


def test_localhost_origins_are_only_trusted_in_debug(tmp_path):
    from fastapi.testclient import TestClient

    from tests.conftest import build_test_app

    app, _ = build_test_app(tmp_path)
    reply = TestClient(app).get("/api/v1/auth/me", headers={"Origin": "http://localhost:3000"})
    assert "access-control-allow-origin" not in reply.headers


def test_a_stalled_request_body_is_cut_off():
    from starlette.types import Message

    from app.api.middleware.body_limit import BodySizeLimitMiddleware

    sent: list[Message] = []

    async def app(scope, receive, send):  # pragma: no cover - never reached
        await receive()
        await receive()

    async def receive() -> Message:
        await asyncio.sleep(10)  # the client never sends the rest
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = BodySizeLimitMiddleware(app, max_body_bytes=1000, idle_timeout=0.05)
    scope = {"type": "http", "method": "POST", "headers": [(b"content-length", b"100")]}
    run(middleware(scope, receive, send))

    assert sent[0]["status"] == 408


def test_declared_content_types_must_be_well_formed(env):
    service = env.file_service
    assert service._validate_file_type("text/plain; charset=utf-8")
    for bad in ("text/plain\r\nX-Injected: 1", "text/plain\nx", "nonsense", "text/"):
        assert not service._validate_file_type(bad), bad


def test_console_log_lines_cannot_be_forged_by_request_text():
    import logging

    from app.services.logger import _ConsoleFormatter

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "GET /a\nERROR | forged", None, None)
    assert "\n" not in _ConsoleFormatter().format(record)


def test_code_graph_is_tracked_but_kept_out_of_builds_and_checks():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    assert "graphify-out" in (root / ".dockerignore").read_text()
    assert 'extend-exclude = ["graphify-out"]' in (root / "pyproject.toml").read_text()
    assert "graphify-out/**" in (root / ".github/workflows/ci.yml").read_text()
    assert "^graphify-out/" in (root / ".pre-commit-config.yaml").read_text()
