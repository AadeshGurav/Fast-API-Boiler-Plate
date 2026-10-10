"""The security audit log: which changes are recorded, by whom, and who may read them."""

from __future__ import annotations

from app.services.data.schema import collection_indexes
from tests.conftest import run
from tests.test_auth_flow import NEW_PASSWORD, PASSWORD
from tests.test_features import admin_client, signed_in


def events(admin, **params):
    response = admin.get("/api/v1/admin/audit-events", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_password_change_is_recorded_with_actor_ip_and_request_id(env):
    client = signed_in(env)
    user_id = client.get("/api/v1/auth/me").json()["id"]
    client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        headers={"X-Request-ID": "req-audit-1", "User-Agent": "audit-test"},
    )

    page = events(admin_client(env), action="user.password_changed")

    assert page["total"] == 1
    event = page["events"][0]
    assert event["actor_id"] == user_id and event["target_id"] == user_id
    assert event["ip_address"] and event["user_agent"] == "audit-test"
    assert event["request_id"].startswith("req-audit-1")
    assert event["details"] == {"sessions_ended": 0}
    assert "password" not in str(event["details"]).replace("sessions_ended", "")


def test_registration_is_attributed_to_the_new_account(env):
    client = signed_in(env)
    user_id = client.get("/api/v1/auth/me").json()["id"]

    event = events(admin_client(env), action="user.registered", target_id=user_id)["events"][0]

    assert event["actor_id"] == user_id


def test_admin_changes_are_recorded_as_the_admin(env):
    victim = signed_in(env)
    victim_id = victim.get("/api/v1/auth/me").json()["id"]
    admin = admin_client(env)
    admin_id = admin.get("/api/v1/auth/me").json()["id"]

    admin.post(f"/api/v1/rbac/users/{victim_id}/roles", params={"role_id": "manager"})
    admin.delete(f"/api/v1/rbac/users/{victim_id}/roles/manager")
    admin.patch(f"/api/v1/users/{victim_id}", json={"status": "suspended"})
    admin.delete(f"/api/v1/users/{victim_id}")

    page = events(admin, target_id=victim_id, actor_id=admin_id)
    actions = [e["action"] for e in page["events"]]

    assert actions == [  # newest first
        "user.deleted",
        "user.status_changed",
        "rbac.role_removed",
        "rbac.role_assigned",
    ]
    assert page["events"][3]["details"] == {"role": "manager"}
    assert page["events"][2]["details"] == {"role": "manager"}


def test_refused_changes_are_not_recorded(env):
    victim = signed_in(env)
    victim_id = victim.get("/api/v1/auth/me").json()["id"]
    admin = admin_client(env)

    admin.post(f"/api/v1/rbac/users/{victim_id}/roles", params={"role_id": "no-such-role"})

    assert events(admin, action="rbac.role_assigned")["total"] == 0


def test_session_revocations_are_recorded(env):
    client = signed_in(env)
    user_id = client.get("/api/v1/auth/me").json()["id"]
    client.delete("/api/v1/sessions/all")

    event = events(admin_client(env), action="session.revoked_all")["events"][0]

    assert event["target_id"] == user_id and event["details"] == {"count": 1}


def test_filters_and_paging(env):
    for i in range(3):
        signed_in(env, username=f"user{i}", email=f"user{i}@example.com")
    admin = admin_client(env)  # registers a fourth account, the administrator

    first = events(admin, action="user.registered", page=1, page_size=3)
    last = events(admin, action="user.registered", page=2, page_size=3)

    assert first["total"] == 4 and len(first["events"]) == 3 and first["has_next"] is True
    assert len(last["events"]) == 1 and last["has_next"] is False
    future = "2999-01-01T00:00:00Z"
    assert events(admin, since=future)["total"] == 0
    assert events(admin, until=future)["total"] >= 3


def test_only_administrators_can_read_the_log(env):
    client = signed_in(env)

    assert client.get("/api/v1/admin/audit-events").status_code == 403
    assert env.client().get("/api/v1/admin/audit-events").status_code == 401


def test_a_failing_audit_write_does_not_block_the_change(env, monkeypatch):
    client = signed_in(env)

    async def broken_insert(collection, data):
        raise RuntimeError("audit store down")

    monkeypatch.setattr(env.services.audit_service.data_service, "insert", broken_insert)

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 200


def test_audit_events_expire_after_the_configured_retention(env):
    env.services.config.data["audit_retention_days"] = 30

    indexes = collection_indexes(env.services.config)["audit_events"]

    assert {"keys": [("at", 1)], "expireAfterSeconds": 30 * 24 * 3600} in indexes


def test_services_can_record_outside_a_request(env):
    run(env.services.audit_service.record("custom.event", target_type="thing", target_id="t1"))

    event = events(admin_client(env), action="custom.event")["events"][0]

    assert event["actor_id"] is None and event["ip_address"] is None
