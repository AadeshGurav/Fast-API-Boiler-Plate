"""Passkeys through the real app, with a software authenticator (P-256, "none" attestation)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct

import cbor2
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from tests.conftest import build_test_app, run
from tests.test_auth_flow import bearer, login, register

ORIGIN = "https://app.example.com"
RP_ID = "example.com"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SoftAuthenticator:
    """What a phone or laptop does inside navigator.credentials, in software."""

    def __init__(self, rp_id=RP_ID):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = os.urandom(16)
        self.rp_id = rp_id
        self.sign_count = 0
        self.user_handle = None

    def _cose_key(self) -> bytes:
        numbers = self.key.public_key().public_numbers()
        return cbor2.dumps(
            {
                1: 2,
                3: -7,
                -1: 1,
                -2: numbers.x.to_bytes(32, "big"),
                -3: numbers.y.to_bytes(32, "big"),
            }
        )

    def _auth_data(self, flags: int, attested: bool) -> bytes:
        data = (
            hashlib.sha256(self.rp_id.encode()).digest()
            + bytes([flags])
            + struct.pack(">I", self.sign_count)
        )
        if attested:
            data += (
                b"\x00" * 16
                + struct.pack(">H", len(self.credential_id))
                + self.credential_id
                + self._cose_key()
            )
        return data

    @staticmethod
    def _client_data(kind: str, challenge: str, origin: str) -> bytes:
        return json.dumps(
            {"type": kind, "challenge": challenge, "origin": origin, "crossOrigin": False}
        ).encode()

    def create(self, options: dict, origin=ORIGIN) -> dict:
        self.user_handle = options["user"]["id"]
        client_data = self._client_data("webauthn.create", options["challenge"], origin)
        attestation = cbor2.dumps(
            {"fmt": "none", "attStmt": {}, "authData": self._auth_data(0x45, attested=True)}
        )  # UP|UV|AT
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "attestationObject": b64(attestation),
                "transports": ["internal"],
            },
            "clientExtensionResults": {},
        }

    def get(self, options: dict, origin=ORIGIN, user_verified=True) -> dict:
        self.sign_count += 1
        client_data = self._client_data("webauthn.get", options["challenge"], origin)
        auth_data = self._auth_data(0x05 if user_verified else 0x01, attested=False)
        signature = self.key.sign(
            auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256())
        )
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "authenticatorData": b64(auth_data),
                "signature": b64(signature),
                "userHandle": self.user_handle,
            },
            "clientExtensionResults": {},
        }


@pytest.fixture
def app_client(tmp_path):
    app, services = build_test_app(
        tmp_path, passkeys_enabled=True, webauthn_rp_id=RP_ID, webauthn_origins=[ORIGIN]
    )
    return TestClient(app), services


def signed_in(client):
    register(client)
    client.headers.update(bearer(login(client)))
    return client


def enrol(client, device):
    options = client.post("/api/v1/auth/passkeys/registration/options").json()
    response = client.post(
        "/api/v1/auth/passkeys",
        json={
            "challenge_id": options["challenge_id"],
            "name": "Laptop",
            "credential": device.create(options["options"]),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def sign_in(client, device, **kwargs):
    options = client.post("/api/v1/auth/passkeys/login/options").json()
    return client.post(
        "/api/v1/auth/passkeys/login",
        json={
            "challenge_id": options["challenge_id"],
            "credential": device.get(options["options"], **kwargs),
        },
    )


def test_register_then_sign_in_without_a_password(app_client):
    client, _ = app_client
    signed_in(client)
    device = SoftAuthenticator()
    enrol(client, device)
    client.headers.pop("Authorization")

    response = sign_in(client, device)

    assert response.status_code == 200, response.text
    token = response.json()["tokens"]["access_token"]
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()[
            "username"
        ]
        == "ada"
    )


def test_options_require_a_passkey_that_verifies_the_user(app_client):
    client, _ = app_client
    signed_in(client)

    options = client.post("/api/v1/auth/passkeys/registration/options").json()["options"]

    assert options["rp"]["id"] == RP_ID
    assert options["authenticatorSelection"]["userVerification"] == "required"
    assert options["authenticatorSelection"]["residentKey"] == "required"


def test_a_passkey_from_another_site_or_origin_is_refused(app_client):
    client, _ = app_client
    signed_in(client)
    options = client.post("/api/v1/auth/passkeys/registration/options").json()

    phished = client.post(
        "/api/v1/auth/passkeys",
        json={
            "challenge_id": options["challenge_id"],
            "credential": SoftAuthenticator().create(
                options["options"], origin="https://evil.example"
            ),
        },
    )

    assert phished.status_code == 400
    assert client.get("/api/v1/auth/passkeys").json() == []


def test_challenges_are_single_use(app_client):
    client, _ = app_client
    signed_in(client)
    device = SoftAuthenticator()
    enrol(client, device)
    options = client.post("/api/v1/auth/passkeys/login/options").json()
    answer = device.get(options["options"])
    body = {"challenge_id": options["challenge_id"], "credential": answer}

    assert client.post("/api/v1/auth/passkeys/login", json=body).status_code == 200
    assert client.post("/api/v1/auth/passkeys/login", json=body).status_code == 401


def test_sign_in_without_user_verification_is_refused(app_client):
    client, _ = app_client
    signed_in(client)
    device = SoftAuthenticator()
    enrol(client, device)

    assert sign_in(client, device, user_verified=False).status_code == 401


def test_a_cloned_authenticator_is_caught_by_its_signature_counter(app_client):
    client, _ = app_client
    signed_in(client)
    device = SoftAuthenticator()
    enrol(client, device)
    assert sign_in(client, device).status_code == 200

    device.sign_count -= 1  # a copy that lags behind the real device
    assert sign_in(client, device).status_code == 401


def test_removed_passkeys_and_suspended_users_cannot_sign_in(app_client):
    client, services = app_client
    signed_in(client)
    device = SoftAuthenticator()
    passkey = enrol(client, device)

    assert client.delete(f"/api/v1/auth/passkeys/{passkey['id']}").status_code == 204
    assert sign_in(client, device).status_code == 401

    enrol(client, device := SoftAuthenticator())
    user_id = client.get("/api/v1/auth/me").json()["id"]
    run(services.auth_service.set_user_status(user_id, "suspended"))
    assert sign_in(client, device).status_code == 401


def test_api_tokens_cannot_manage_passkeys(app_client):
    client, _ = app_client
    signed_in(client)
    token = client.post("/api/v1/tokens", json={"name": "ci", "scopes": ["*"]}).json()["token"]

    response = client.post(
        "/api/v1/auth/passkeys/registration/options", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_disabled_passkeys_answer_503(tmp_path):
    app, _ = build_test_app(tmp_path)

    assert TestClient(app).post("/api/v1/auth/passkeys/login/options").status_code == 503


def test_passkey_changes_are_audited(app_client):
    client, services = app_client
    signed_in(client)
    passkey = enrol(client, SoftAuthenticator())
    client.delete(f"/api/v1/auth/passkeys/{passkey['id']}")
    events, _, _ = run(services.audit_service.list_events(target_type="user"))

    assert {"passkey.added", "passkey.removed"} <= {e["action"] for e in events}
