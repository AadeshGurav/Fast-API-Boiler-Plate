"""Change password, profile, user administration and idempotency keys."""

from __future__ import annotations

from tests.conftest import run
from tests.test_auth_flow import NEW_PASSWORD, PASSWORD, bearer, login, make_admin, register

UPLOAD = {"file": ("note.txt", b"hello", "text/plain")}


def signed_in(env, username="ada", email="ada@example.com"):
    client = env.client()
    register(client, username=username, email=email)
    client.headers.update(bearer(login(client, username)))
    return client


# ---- change password / profile ---------------------------------------------------------


def test_change_password_needs_the_current_one_and_ends_other_sessions(env):
    client = signed_in(env)
    other_device = env.client()
    other_device.headers.update(bearer(login(other_device)))

    wrong = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "nope", "new_password": NEW_PASSWORD},
    )
    assert wrong.status_code == 403

    weak = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "password1"},
    )
    assert weak.status_code == 400 and "Password must contain" in weak.json()["detail"]

    ok = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert ok.status_code == 200 and ok.json()["other_sessions_ended"] == 1
    assert client.get("/api/v1/auth/me").status_code == 200  # this session survives
    assert other_device.get("/api/v1/auth/me").status_code == 401
    assert login(env.client(), password=PASSWORD).status_code == 401
    assert login(env.client(), password=NEW_PASSWORD).status_code == 200


def test_users_can_edit_their_own_profile(env):
    client = signed_in(env)

    response = client.patch("/api/v1/auth/me", json={"first_name": "Ada", "last_name": "L"})

    assert response.status_code == 200
    assert response.json()["metadata"]["first_name"] == "Ada"
    assert client.get("/api/v1/auth/me").json()["metadata"]["last_name"] == "L"


# ---- user administration -----------------------------------------------------------------


def admin_client(env):
    make_admin(env)
    client = env.client()
    client.headers.update(bearer(login(client, "root")))
    return client


def test_normal_users_cannot_list_users_but_admins_can_with_paging(env):
    for i in range(3):
        register(env.client(), username=f"user{i}", email=f"u{i}@example.com")
    normal = signed_in(env)
    assert normal.get("/api/v1/users").status_code == 403

    admin = admin_client(env)
    page = admin.get("/api/v1/users?page=1&page_size=2").json()
    assert page["total"] == 5 and len(page["users"]) == 2 and page["has_next"] is True
    assert len(admin.get("/api/v1/users?page=3&page_size=2").json()["users"]) == 1
    assert "password" not in str(page) and "password_hash" not in str(page)


def test_suspending_a_user_signs_them_out_and_blocks_login(env):
    victim = signed_in(env)
    admin = admin_client(env)
    victim_id = victim.get("/api/v1/auth/me").json()["id"]

    assert (
        admin.patch(f"/api/v1/users/{victim_id}", json={"status": "suspended"}).status_code == 200
    )

    assert victim.get("/api/v1/auth/me").status_code == 401
    assert login(env.client()).status_code == 401
    assert admin.patch(f"/api/v1/users/{victim_id}", json={"status": "active"}).status_code == 200
    assert login(env.client()).status_code == 200


def test_admins_cannot_disable_themselves_and_unknown_users_404(env):
    admin = admin_client(env)
    me = admin.get("/api/v1/auth/me").json()["id"]

    assert admin.patch(f"/api/v1/users/{me}", json={"status": "inactive"}).status_code == 400
    assert admin.get("/api/v1/users/nobody").status_code == 404
    assert admin.patch("/api/v1/users/nobody", json={"status": "inactive"}).status_code == 404


# ---- idempotency ----------------------------------------------------------------------------


def test_retried_post_with_the_same_key_is_replayed_not_rerun(env):
    client = signed_in(env)
    headers = {"Idempotency-Key": "upload-attempt-0001"}

    first = client.post("/api/v1/files/upload", files=UPLOAD, data={"tags": "a"}, headers=headers)
    # same bytes + tag, so dedup alone would also return the same file; prove it did not re-run
    run_count_before = len(run(env.services.database_service.find_many("files", {})))
    second = client.post("/api/v1/files/upload", files=UPLOAD, data={"tags": "a"}, headers=headers)

    assert first.status_code == 201 and second.status_code == 201
    assert (
        second.headers["idempotent-replayed"] == "true"
        and "idempotent-replayed" not in first.headers
    )
    assert second.json() == first.json()
    assert len(run(env.services.database_service.find_many("files", {}))) == run_count_before


def test_same_key_with_a_different_body_is_rejected(env):
    client = signed_in(env)
    headers = {"Idempotency-Key": "upload-attempt-0002"}
    client.post("/api/v1/files/upload", files=UPLOAD, headers=headers)

    other = client.post(
        "/api/v1/files/upload",
        files={"file": ("x.txt", b"different", "text/plain")},
        headers=headers,
    )

    assert other.status_code == 422


def test_keys_are_scoped_per_user_and_validated(env):
    ada = signed_in(env)
    eve = signed_in(env, "eve", "eve@example.com")
    headers = {"Idempotency-Key": "shared-key-12345"}

    a = ada.post("/api/v1/files/upload", files=UPLOAD, headers=headers).json()
    e = eve.post("/api/v1/files/upload", files=UPLOAD, headers=headers)

    assert e.status_code == 201 and "idempotent-replayed" not in e.headers
    assert e.json()["file_id"] != a["file_id"]
    assert (
        ada.post(
            "/api/v1/files/upload", files=UPLOAD, headers={"Idempotency-Key": "short"}
        ).status_code
        == 400
    )


def test_failed_requests_are_not_stored_so_a_retry_really_retries(env):
    client = signed_in(env)
    headers = {"Idempotency-Key": "upload-attempt-0003"}
    bad = client.post(
        "/api/v1/files/upload", files={"file": ("x.html", b"<b>", "text/html")}, headers=headers
    )
    assert bad.status_code == 400  # 4xx IS replayed...
    again = client.post(
        "/api/v1/files/upload", files={"file": ("x.html", b"<b>", "text/html")}, headers=headers
    )
    assert again.status_code == 400 and again.headers["idempotent-replayed"] == "true"


def test_requests_without_a_key_are_untouched(env):
    client = signed_in(env)
    one = client.post("/api/v1/files/upload", files=UPLOAD).json()
    two = client.post("/api/v1/files/upload", files=UPLOAD)

    assert (
        "idempotent-replayed" not in two.headers and two.json()["file_id"] == one["file_id"]
    )  # dedup


def test_only_admins_can_delete_users_and_not_themselves(env):
    victim = signed_in(env)
    victim_id = victim.get("/api/v1/auth/me").json()["id"]
    assert victim.delete(f"/api/v1/users/{victim_id}").status_code == 403  # lacks users:delete

    admin = admin_client(env)
    me = admin.get("/api/v1/auth/me").json()["id"]
    assert admin.delete(f"/api/v1/users/{me}").status_code == 400
    assert admin.delete(f"/api/v1/users/{victim_id}").status_code == 204

    assert victim.get("/api/v1/auth/me").status_code == 401
    assert admin.get(f"/api/v1/users/{victim_id}").status_code == 404
    assert admin.delete(f"/api/v1/users/{victim_id}").status_code == 404


def test_large_json_bodies_are_streamed_through_not_buffered(env, monkeypatch):
    monkeypatch.setattr("app.api.middleware.idempotency.MAX_BUFFERED_REQUEST", 10)
    client = signed_in(env)
    headers = {"Idempotency-Key": "big-body-attempt-1"}
    payload = {"filename": "renamed-" + "x" * 50 + ".pdf"}  # well over the 10-byte buffer limit
    file_id = client.post("/api/v1/files/upload", files=UPLOAD).json()["file_id"]

    first = client.put(f"/api/v1/files/{file_id}", json=payload, headers=headers)
    second = client.put(f"/api/v1/files/{file_id}", json=payload, headers=headers)
    different = client.put(
        f"/api/v1/files/{file_id}", json={"filename": "other-" + "y" * 50 + ".pdf"}, headers=headers
    )

    assert first.status_code == 200 and first.json()["filename"] == payload["filename"]
    assert second.headers["idempotent-replayed"] == "true" and second.json() == first.json()
    assert different.status_code == 422  # streamed bodies are compared by length
