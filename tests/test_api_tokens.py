"""Personal access tokens: scopes, the owner ceiling, revocation, expiry and limits."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.test_features import UPLOAD, admin_client, signed_in


def create(client, scopes, **extra):
    return client.post("/api/v1/tokens", json={"name": "ci", "scopes": scopes, **extra})


def as_token(env, token):
    client = env.client()
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def stored(env):
    return env.services.database_service.backend.collections["api_tokens"]


def test_the_secret_is_shown_once_and_stored_hashed(env):
    client = signed_in(env)

    created = create(client, ["files:read"])
    token = created.json()["token"]
    listed = client.get("/api/v1/tokens").json()

    assert created.status_code == 201 and token.startswith("fabp_pat_")
    assert listed["total"] == 1 and "token" not in listed["tokens"][0]
    assert token.startswith(listed["tokens"][0]["prefix"])
    assert token not in str(stored(env)) and "token_hash" not in str(listed)


def test_scopes_limit_what_a_token_can_do(env):
    client = signed_in(env)
    token = create(client, ["files:read"]).json()["token"]
    api = as_token(env, token)

    assert api.get("/api/v1/files").status_code == 200
    assert api.post("/api/v1/files/upload", files=UPLOAD).status_code == 403
    assert api.get("/api/v1/sessions/active").status_code == 403


def test_a_token_never_exceeds_its_owner(env):
    client = signed_in(env)
    token = create(client, ["*"]).json()["token"]

    assert as_token(env, token).get("/api/v1/users").status_code == 403  # users:read is staff-only
    assert as_token(env, token).get("/api/v1/admin/audit-events").status_code == 403


def test_tokens_cannot_manage_tokens(env):
    client = signed_in(env)
    token = create(client, ["tokens:read", "tokens:write"]).json()["token"]
    api = as_token(env, token)

    assert create(api, ["files:read"]).status_code == 403
    assert api.get("/api/v1/tokens").status_code == 403


def test_revoked_expired_and_unknown_tokens_are_refused(env):
    client = signed_in(env)
    created = create(client, ["files:read"]).json()
    api = as_token(env, created["token"])
    assert api.get("/api/v1/files").status_code == 200

    assert client.delete(f"/api/v1/tokens/{created['id']}").status_code == 204
    assert api.get("/api/v1/files").status_code == 401
    assert client.delete(f"/api/v1/tokens/{created['id']}").status_code == 404

    expiring = create(client, ["files:read"]).json()
    stored(env)[-1]["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    assert as_token(env, expiring["token"]).get("/api/v1/files").status_code == 401

    forged = as_token(env, "fabp_pat_" + "x" * 43).get("/api/v1/files")
    assert forged.status_code == 401 and forged.json()["code"] == "http_error"


def test_suspending_the_owner_stops_their_tokens(env):
    client = signed_in(env)
    user_id = client.get("/api/v1/auth/me").json()["id"]
    token = create(client, ["files:read"]).json()["token"]

    admin_client(env).patch(f"/api/v1/users/{user_id}", json={"status": "suspended"})

    assert as_token(env, token).get("/api/v1/files").status_code == 401


def test_other_users_cannot_revoke_your_token(env):
    owner = signed_in(env)
    token_id = create(owner, ["files:read"]).json()["id"]
    other = signed_in(env, username="bob", email="bob@example.com")

    assert other.delete(f"/api/v1/tokens/{token_id}").status_code == 404
    assert owner.get("/api/v1/tokens").json()["total"] == 1


def test_invalid_requests_are_refused_with_a_reason(env):
    client = signed_in(env)

    assert create(client, ["Files read"]).status_code == 400
    assert create(client, ["files:read"], expires_in_days=10_000).status_code == 400
    assert create(client, []).status_code == 422

    env.services.auth_service.api_tokens.per_user = 2
    create(client, ["files:read"])
    create(client, ["files:read"])
    limited = create(client, ["files:read"])
    assert limited.status_code == 400 and "revoke one" in limited.json()["detail"]


def test_use_is_recorded_and_changes_are_audited(env):
    client = signed_in(env)
    created = create(client, ["files:read"]).json()
    as_token(env, created["token"]).get("/api/v1/files")
    client.delete(f"/api/v1/tokens/{created['id']}")

    events = admin_client(env).get(
        "/api/v1/admin/audit-events", params={"target_id": created["id"]}
    )

    assert [e["action"] for e in events.json()["events"]] == ["token.revoked", "token.created"]


def test_last_used_is_updated(env):
    client = signed_in(env)
    created = create(client, ["files:read"]).json()

    as_token(env, created["token"]).get("/api/v1/files")

    assert client.get("/api/v1/tokens").json()["tokens"][0]["last_used_at"] is not None
