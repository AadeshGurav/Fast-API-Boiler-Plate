"""End-to-end authentication through the real app, middleware and services.

Only the Mongo and Redis backends are replaced by in-memory fakes.
"""

from __future__ import annotations

from app.models.user import UserCreate
from tests.conftest import run

PASSWORD = "Str0ng!Passw0rd"
NEW_PASSWORD = "An0ther!Passw0rd"


def register(client, username="ada", email="ada@example.com", **extra):
    return client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": PASSWORD,
            "first_name": "Ada",
            "last_name": "Lovelace",
            **extra,
        },
    )


def login(client, username="ada", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def bearer(login_response) -> dict[str, str]:
    return {"Authorization": f"Bearer {login_response.json()['tokens']['access_token']}"}


def make_admin(env):
    run(
        env.auth_service.register_user(
            UserCreate(
                username="root", email="root@example.com", password=PASSWORD, roles=["admin"]
            )
        )
    )


# ---- registration -----------------------------------------------------------------


def test_public_registration_cannot_choose_roles(env):
    client = env.client()
    response = register(client, roles=["admin"], groups=["admins"])

    assert response.status_code == 201
    assert response.json()["roles"] == ["user"]
    assert response.json()["groups"] == []


def test_registration_enforces_password_policy(env):
    response = env.client().post(
        "/api/v1/auth/register",
        json={
            "username": "weak",
            "email": "weak@example.com",
            "password": "password1",
            "first_name": "W",
            "last_name": "K",
        },
    )
    assert response.status_code == 400
    assert "Password must contain" in response.json()["detail"]


def test_duplicate_email_is_rejected(env):
    client = env.client()
    assert register(client).status_code == 201
    assert register(client, username="ada2").status_code == 400


# ---- access control ---------------------------------------------------------------


def test_protected_route_without_credentials_is_a_401_problem(env):
    response = env.client().get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["status"] == 401


def test_cookie_and_bearer_both_authenticate(env):
    client = env.client()
    register(client)
    response = login(client)

    assert env.client().get("/api/v1/auth/me", headers=bearer(response)).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200  # HttpOnly cookie jar


def test_normal_user_is_forbidden_from_admin_routes_but_admin_is_not(env):
    client = env.client()
    register(client)
    user_login = login(client)
    assert client.get("/api/v1/rbac/roles", headers=bearer(user_login)).status_code == 403

    make_admin(env)
    admin_login = login(env.client(), "root")
    assert env.client().get("/api/v1/rbac/roles", headers=bearer(admin_login)).status_code == 200


# ---- sessions and tokens ----------------------------------------------------------


def test_logout_kills_the_access_token_immediately(env):
    client = env.client()
    register(client)
    response = login(client)
    headers = bearer(response)

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200

    assert env.client().get("/api/v1/auth/me", headers=headers).status_code == 401


def test_refresh_rotates_and_a_replayed_token_revokes_the_session(env):
    client = env.client()
    register(client)
    first = login(client).json()["tokens"]

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200
    second = rotated.json()

    # An attacker replays the stolen, already-rotated token: the session dies.
    anonymous = env.client()
    replay = anonymous.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401

    # ...which also invalidates the legitimate newest tokens.
    headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert env.client().get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        env.client()
        .post("/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]})
        .status_code
        == 401
    )


def test_access_token_cannot_be_used_as_a_refresh_token(env):
    client = env.client()
    register(client)
    tokens = login(client).json()["tokens"]

    response = env.client().post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert response.status_code == 401


# ---- brute force ------------------------------------------------------------------


def test_repeated_failures_lock_the_account_even_for_the_right_password(env):
    client = env.client()
    register(client)

    for _ in range(env.auth_service.max_failed_logins):
        assert login(client, password="wrong").status_code == 401

    locked = login(client)  # correct password
    assert locked.status_code == 401
    assert locked.json()["detail"] == "Invalid credentials"  # no hint it is locked


def test_unknown_user_and_wrong_password_look_identical(env):
    client = env.client()
    register(client)

    unknown = login(client, username="nobody")
    wrong = login(client, password="wrong")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


# ---- password reset ---------------------------------------------------------------


def test_password_reset_is_single_use_and_ends_existing_sessions(env):
    client = env.client()
    register(client)
    headers = bearer(login(client))

    request = client.post("/api/v1/auth/reset-password-request", json={"email": "ada@example.com"})
    assert request.status_code == 200
    (token,) = env.reset_tokens

    confirm = client.post(
        "/api/v1/auth/reset-password-confirm",
        json={"token": token, "new_password": NEW_PASSWORD},
    )
    assert confirm.status_code == 200

    reuse = client.post(
        "/api/v1/auth/reset-password-confirm",
        json={"token": token, "new_password": "Y3t!Another1"},
    )
    assert reuse.status_code == 400

    assert env.client().get("/api/v1/auth/me", headers=headers).status_code == 401
    assert login(env.client(), password=PASSWORD).status_code == 401
    assert login(env.client(), password=NEW_PASSWORD).status_code == 200


def test_reset_request_does_not_reveal_whether_the_email_exists(env):
    client = env.client()
    register(client)
    known = client.post("/api/v1/auth/reset-password-request", json={"email": "ada@example.com"})
    unknown = client.post("/api/v1/auth/reset-password-request", json={"email": "who@example.com"})

    assert known.json() == unknown.json()


def test_every_login_attempt_is_recorded_in_the_audit_log(env):
    client = env.client()
    register(client)
    login(client, password="wrong")
    login(client, username="nobody")
    login(client)

    attempts = run(env.auth_service.data_service.database_service.find_many("login_attempts", {}))
    assert sorted((a["username"], a["success"], a["reason"]) for a in attempts) == [
        ("ada", False, "invalid_password"),
        ("ada", True, None),
        ("nobody", False, "unknown_user"),
    ]


def test_reset_token_lifetime_honours_sub_hour_settings(env):
    client = env.client()
    register(client)
    env.auth_service.password_service.reset_token_lifetime_seconds = 1800

    client.post("/api/v1/auth/reset-password-request", json={"email": "ada@example.com"})

    (record,) = run(
        env.auth_service.data_service.database_service.find_many("password_reset_tokens", {})
    )
    assert (record["expires_at"] - record["created_at"]).total_seconds() == 1800


def test_weak_legacy_hashes_are_upgraded_on_login(env):
    from argon2 import PasswordHasher

    client = env.client()
    register(client)
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)
    user = run(env.services.database_service.get_record("users", {"username": "ada"}))
    run(env.services.data_service.users.update_user(user["id"], {"password": weak}))

    assert login(client).status_code == 200

    stored = run(env.services.database_service.get_record("users", {"username": "ada"}))["password"]
    assert stored != weak and not env.services.password_service.needs_rehash(stored)
    assert login(client).status_code == 200  # the upgraded hash still verifies
