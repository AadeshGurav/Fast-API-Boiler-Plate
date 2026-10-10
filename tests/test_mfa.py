"""Two-factor authentication: RFC 6238 codes, enrolment, two-step sign-in, replay and lockout."""

from __future__ import annotations

import base64

import pytest

from app.services.auth import totp
from tests.test_auth_flow import PASSWORD, bearer, login
from tests.test_features import admin_client, signed_in

RFC_SECRET = base64.b32encode(b"12345678901234567890").decode()


@pytest.mark.parametrize(
    ("unix_time", "code"),
    [(59, "287082"), (1111111109, "081804"), (1234567890, "005924"), (2000000000, "279037")],
)
def test_codes_match_the_rfc_6238_vectors(unix_time, code):
    assert totp.code_at(RFC_SECRET, totp.current_step(unix_time)) == code


def test_one_step_of_clock_skew_is_accepted_and_two_are_not():
    now = 1_700_000_000
    step = totp.current_step(now)

    assert totp.matching_step(RFC_SECRET, totp.code_at(RFC_SECRET, step - 1), now=now) == step - 1
    assert totp.matching_step(RFC_SECRET, totp.code_at(RFC_SECRET, step + 2), now=now) is None
    assert totp.matching_step(RFC_SECRET, "12345", now=now) is None
    assert totp.matching_step(RFC_SECRET, "abcdef", now=now) is None


class Clock:
    """Moves the TOTP clock forward one 30-second step per ``tick()``."""

    def __init__(self, monkeypatch):
        self.now = 1_800_000_000.0
        monkeypatch.setattr(totp.time, "time", lambda: self.now)

    def tick(self):
        self.now += totp.STEP_SECONDS


@pytest.fixture
def clock(monkeypatch):
    return Clock(monkeypatch)


def enrol(client, clock):
    setup = client.post("/api/v1/auth/mfa/totp", json={"password": PASSWORD})
    assert setup.status_code == 201, setup.text
    secret = setup.json()["secret"]
    confirmed = client.post("/api/v1/auth/mfa/totp/confirm", json={"code": code(secret, clock)})
    assert confirmed.status_code == 200, confirmed.text
    clock.tick()
    return secret, confirmed.json()["recovery_codes"]


def code(secret, clock):
    return totp.code_at(secret, totp.current_step(clock.now))


def challenge(client=None, env=None):
    response = login(client or env.client())
    assert response.status_code == 401
    problem = response.json()
    assert problem["code"] == "mfa_required"
    return problem["details"]["mfa_token"]


def finish(client, mfa_token, value):
    return client.post("/api/v1/auth/login/mfa", json={"mfa_token": mfa_token, "code": value})


# ---- enrolment --------------------------------------------------------------------


def test_setup_needs_the_password_and_a_working_code(env, clock):
    client = signed_in(env)

    assert client.post("/api/v1/auth/mfa/totp", json={"password": "wrong"}).status_code == 403
    setup = client.post("/api/v1/auth/mfa/totp", json={"password": PASSWORD}).json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    assert f"secret={setup['secret']}" in setup["otpauth_uri"]

    bad = client.post("/api/v1/auth/mfa/totp/confirm", json={"code": "000000"})
    assert bad.status_code == 403
    assert client.get("/api/v1/auth/mfa").json()["totp_enabled"] is False

    good = client.post("/api/v1/auth/mfa/totp/confirm", json={"code": code(setup["secret"], clock)})
    codes = good.json()["recovery_codes"]
    assert good.status_code == 200 and len(codes) == 10 and len(set(codes)) == 10
    assert client.get("/api/v1/auth/mfa").json() == {
        "totp_enabled": True,
        "recovery_codes_left": 10,
    }
    assert client.post("/api/v1/auth/mfa/totp", json={"password": PASSWORD}).status_code == 409


def test_the_secret_is_encrypted_at_rest(env, clock):
    client = signed_in(env)
    secret, _ = enrol(client, clock)

    stored = env.services.database_service.backend.collections["mfa_totp"][0]

    assert secret not in str(stored)
    assert stored["recovery_codes"] and all(len(h) == 64 for h in stored["recovery_codes"])


# ---- sign-in --------------------------------------------------------------------------


def test_sign_in_needs_a_code_once_enabled(env, clock):
    secret, _ = enrol(signed_in(env), clock)
    client = env.client()

    token = challenge(client)
    assert client.get("/api/v1/auth/me").status_code == 401  # the password alone opens nothing

    done = finish(client, token, code(secret, clock))
    assert done.status_code == 200
    assert env.client().get("/api/v1/auth/me", headers=bearer(done)).status_code == 200
    assert "fastapi_boilerplate_access_token" in done.cookies


def test_a_code_works_only_once(env, clock):
    secret, _ = enrol(signed_in(env), clock)
    used = code(secret, clock)

    assert finish(env.client(), challenge(env=env), used).status_code == 200
    assert finish(env.client(), challenge(env=env), used).status_code == 401


def test_recovery_codes_work_once_each(env, clock):
    client = signed_in(env)
    _, codes = enrol(client, clock)

    assert finish(env.client(), challenge(env=env), codes[0].upper()).status_code == 200
    assert finish(env.client(), challenge(env=env), codes[0]).status_code == 401
    assert client.get("/api/v1/auth/mfa").json()["recovery_codes_left"] == 9


def test_wrong_codes_lock_the_account(env, clock):
    secret, _ = enrol(signed_in(env), clock)
    token = challenge(env=env)

    for _ in range(env.services.config["auth_max_failed_logins"]):
        assert finish(env.client(), token, "000000").status_code == 401

    assert finish(env.client(), token, code(secret, clock)).status_code == 401
    assert login(env.client()).status_code == 401  # locked: same answer as a wrong password


def test_challenge_tokens_are_not_access_tokens_and_vice_versa(env, clock):
    secret, _ = enrol(signed_in(env), clock)
    token = challenge(env=env)

    assert (
        env.client()
        .get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        .status_code
        == 401
    )
    other = signed_in(env, username="bob", email="bob@example.com")
    access = other.headers["Authorization"].removeprefix("Bearer ")
    assert finish(env.client(), access, code(secret, clock)).status_code == 401


def test_an_expired_challenge_is_refused(env, clock, monkeypatch):
    secret, _ = enrol(signed_in(env), clock)
    monkeypatch.setitem(env.services.config.data, "mfa_challenge_minutes", 1)
    tokens = env.auth_service.tokens
    expired = tokens.create_mfa_token("someone", False, minutes=-1)

    assert finish(env.client(), expired, code(secret, clock)).status_code == 401


# ---- changes ----------------------------------------------------------------------


def test_turning_off_needs_password_and_code_then_sign_in_is_password_only(env, clock):
    client = signed_in(env)
    secret, _ = enrol(client, clock)

    no_code = client.request(
        "DELETE", "/api/v1/auth/mfa/totp", json={"password": PASSWORD, "code": "000000"}
    )
    assert no_code.status_code == 403
    clock.tick()
    off = client.request(
        "DELETE", "/api/v1/auth/mfa/totp", json={"password": PASSWORD, "code": code(secret, clock)}
    )
    assert off.status_code == 204
    assert login(env.client()).status_code == 200


def test_regenerating_recovery_codes_invalidates_the_old_ones(env, clock):
    client = signed_in(env)
    secret, old = enrol(client, clock)

    new = client.post(
        "/api/v1/auth/mfa/recovery-codes", json={"password": PASSWORD, "code": code(secret, clock)}
    ).json()["recovery_codes"]

    assert finish(env.client(), challenge(env=env), old[1]).status_code == 401
    assert finish(env.client(), challenge(env=env), new[1]).status_code == 200


def test_mfa_changes_are_audited(env, clock):
    client = signed_in(env)
    secret, codes = enrol(client, clock)
    finish(env.client(), challenge(env=env), codes[0])
    client.request(
        "DELETE", "/api/v1/auth/mfa/totp", json={"password": PASSWORD, "code": code(secret, clock)}
    )

    page = admin_client(env).get("/api/v1/admin/audit-events", params={"target_type": "user"})
    actions = {e["action"] for e in page.json()["events"]}

    assert {"mfa.enabled", "mfa.recovery_code_used", "mfa.disabled"} <= actions


def test_an_administrator_can_reset_a_lost_second_factor(env, clock):
    client = signed_in(env)
    user_id = client.get("/api/v1/auth/me").json()["id"]
    enrol(client, clock)
    admin = admin_client(env)

    assert client.delete(f"/api/v1/admin/users/{user_id}/mfa").status_code == 403
    assert admin.delete(f"/api/v1/admin/users/{user_id}/mfa").status_code == 204
    assert admin.delete(f"/api/v1/admin/users/{user_id}/mfa").status_code == 404
    assert login(env.client()).status_code == 200
    events = admin.get("/api/v1/admin/audit-events", params={"action": "mfa.reset"}).json()
    assert events["events"][0]["target_id"] == user_id
