"""Outgoing webhooks: subscriptions, destination checks, publishing, signed delivery, retries."""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.data.schema import collection_indexes
from app.services.webhooks import sign
from tests.conftest import run
from tests.test_features import admin_client, signed_in

PUBLIC_IP = "93.184.216.34"


@pytest.fixture
def hooks(env, monkeypatch):
    services = env.services
    run(services.database_service.ensure_indexes(collection_indexes(services.config)))
    service = services.webhook_service
    received: list[httpx.Request] = []
    service.status = 204

    def receiver(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(service.status)

    service.transport = httpx.MockTransport(receiver)

    async def resolve(host, port):
        return {"internal.example": ["10.0.0.5"], "localhost": ["127.0.0.1"]}.get(host, [PUBLIC_IP])

    monkeypatch.setattr(service, "_resolve", resolve)
    service.received = received
    return service


def subscribe(admin, events=("*",), url="https://hooks.example/in"):
    return admin.post("/api/v1/admin/webhooks", json={"url": url, "events": list(events)})


def jobs(env):
    return env.services.database_service.backend.collections.get("jobs", [])


def test_the_secret_is_shown_once_and_encrypted_at_rest(env, hooks):
    admin = admin_client(env)
    created = subscribe(admin)
    secret = created.json()["secret"]

    assert created.status_code == 201 and secret.startswith("whsec_")
    assert "secret" not in admin.get("/api/v1/admin/webhooks").json()[0]
    assert secret not in str(env.services.database_service.backend.collections["webhooks"])


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("http://hooks.example/in", "https"),
        ("https://internal.example/in", "private"),
        ("https://localhost/in", "private"),
        ("ftp://hooks.example/in", "http(s)"),
    ],
)
def test_unsafe_destinations_are_refused(env, hooks, url, reason):
    response = subscribe(admin_client(env), url=url)

    assert response.status_code == 400 and reason in response.json()["detail"]


def test_audit_events_are_published_to_matching_subscriptions(env, hooks):
    admin = admin_client(env)
    subscribe(admin, events=["user.registered"])
    subscribe(admin, events=["rbac.*"], url="https://other.example/in")

    signed_in(env, username="newbie", email="newbie@example.com")

    deliveries = [j for j in jobs(env) if j["name"] == "webhook.deliver"]
    assert len(deliveries) == 1
    message = deliveries[0]["payload"]["message"]
    assert message["type"] == "user.registered"
    assert set(message["data"]) == {"actor_id", "target_type", "target_id", "details"}  # no IP/UA


def test_delivery_is_signed_per_standard_webhooks(env, hooks):
    secret = subscribe(admin_client(env)).json()["secret"]
    signed_in(env, username="newbie", email="newbie@example.com")

    run(env.services.job_service.run_once())

    request = next(r for r in hooks.received if json.loads(r.content)["type"] == "user.registered")
    headers = request.headers
    expected = sign(
        secret, headers["webhook-id"], int(headers["webhook-timestamp"]), request.content
    )
    assert headers["webhook-signature"] == expected
    assert headers["webhook-id"].startswith("msg_")


def test_a_failing_receiver_is_retried_with_the_same_message_id(env, hooks):
    admin = admin_client(env)
    hook_id = subscribe(admin, events=["webhook.test"]).json()["id"]
    admin.post(f"/api/v1/admin/webhooks/{hook_id}/test")
    hooks.status = 500

    run(env.services.job_service.run_once())

    job = next(j for j in jobs(env) if j["name"] == "webhook.deliver")
    assert job["status"] == "queued" and "answered 500" in job["last_error"]
    first_id = hooks.received[-1].headers["webhook-id"]

    hooks.status = 200
    job["run_at"] = job["created_at"]  # due now
    run(env.services.job_service.run_once())

    assert hooks.received[-1].headers["webhook-id"] == first_id  # receivers can de-duplicate
    assert job["status"] == "done"


def test_deliveries_to_a_removed_webhook_are_dropped(env, hooks):
    admin = admin_client(env)
    hook_id = subscribe(admin).json()["id"]
    admin.post(f"/api/v1/admin/webhooks/{hook_id}/test")
    assert admin.delete(f"/api/v1/admin/webhooks/{hook_id}").status_code == 204

    run(env.services.job_service.run_once())

    assert hooks.received == []


def test_webhook_changes_are_audited_but_never_published(env, hooks):
    admin = admin_client(env)
    subscribe(admin)

    events = admin.get("/api/v1/admin/audit-events", params={"action": "webhook.created"}).json()
    assert events["total"] == 1
    assert not [
        j
        for j in jobs(env)
        if j["payload"].get("message", {}).get("type", "").startswith("webhook.created")
    ]


def test_only_administrators_manage_webhooks(env, hooks):
    assert signed_in(env).get("/api/v1/admin/webhooks").status_code == 403
