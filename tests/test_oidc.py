"""Sign-in with OpenID Connect, against an in-memory identity provider with real RSA keys."""

from __future__ import annotations

import time
import urllib.parse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.services.oauth import OAuthService
from tests.conftest import build_test_app, run

ISSUER = "https://idp.example"
CLIENT_ID = "fabp-client"


class FakeIdP:
    """Discovery, JWKS and a token endpoint that mints ID tokens for the last authorize call."""

    def __init__(self):
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.kid = "key-1"
        self.claims = {
            "sub": "idp-42",
            "email": "ada@example.com",
            "email_verified": True,
            "name": "Ada",
        }
        self.nonce = None
        self.code_challenge = None
        self.last_token_request = None
        self.tamper = {}

    def jwks(self):
        public = jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key(), as_dict=True)
        return {"keys": [{**public, "kid": self.kid, "alg": "RS256", "use": "sig"}]}

    def id_token(self):
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "iat": now,
            "exp": now + 300,
            "nonce": self.nonce,
            **self.claims,
            **self.tamper,
        }
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": self.kid})

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token",
                    "jwks_uri": f"{ISSUER}/jwks",
                    "id_token_signing_alg_values_supported": ["RS256"],
                },
            )
        if request.url.path == "/jwks":
            return httpx.Response(200, json=self.jwks())
        if request.url.path == "/token":
            self.last_token_request = dict(urllib.parse.parse_qsl(request.content.decode()))
            return httpx.Response(200, json={"access_token": "at", "id_token": self.id_token()})
        return httpx.Response(404)


@pytest.fixture
def idp():
    return FakeIdP()


@pytest.fixture
def client(tmp_path, idp):
    provider = {
        "issuer": ISSUER,
        "client_id": CLIENT_ID,
        "client_secret": "s3cret",
        "redirect_uri": "http://testserver/api/v1/oauth/acme/callback",
    }
    app, services = build_test_app(tmp_path, oauth_enabled=True, oauth_providers={"acme": provider})
    services.oauth_service = OAuthService(
        services.config,
        services.logger,
        services.data_service,
        services.audit_service,
        transport=httpx.MockTransport(idp.handler),
    )
    return TestClient(app, follow_redirects=False)


def start(client, idp):
    response = client.get("/api/v1/oauth/acme/authorize")
    assert response.status_code == 307, response.text
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(response.headers["location"]).query))
    idp.nonce, idp.code_challenge = query["nonce"], query["code_challenge"]
    return query


def finish(client, state, code="the-code"):
    return client.get("/api/v1/oauth/acme/callback", params={"code": code, "state": state})


def test_a_full_sign_in_creates_an_account_and_a_session(client, idp):
    query = start(client, idp)

    response = finish(client, query["state"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["email"] == "ada@example.com" and body["tokens"]["access_token"]
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['tokens']['access_token']}"}
    )
    assert me.status_code == 200


def test_the_redirect_carries_pkce_and_a_nonce_and_the_exchange_proves_it(client, idp):
    query = start(client, idp)
    assert (
        query["code_challenge_method"] == "S256"
        and query["nonce"]
        and query["scope"] == "openid email profile"
    )

    finish(client, query["state"])

    import base64
    import hashlib

    verifier = idp.last_token_request["code_verifier"]
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    assert expected == idp.code_challenge


@pytest.mark.parametrize("cookie_state", [None, "something-else"])
def test_the_callback_needs_this_browsers_state(client, idp, cookie_state):
    query = start(client, idp)
    client.cookies.clear()
    if cookie_state:
        client.cookies.set("oauth_state_acme", f"{cookie_state}.v.n")

    response = finish(client, query["state"])

    assert response.status_code == 400 and "state" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "tamper",
    [
        {"aud": "someone-else"},
        {"iss": "https://evil.example"},
        {"nonce": "replayed-from-another-sign-in"},
        {"exp": int(time.time()) - 3600},
    ],
    ids=["audience", "issuer", "nonce", "expired"],
)
def test_untrustworthy_id_tokens_are_refused(client, idp, tamper):
    query = start(client, idp)
    idp.tamper = tamper

    response = finish(client, query["state"])

    assert response.status_code == 502


def test_a_token_signed_by_another_key_is_refused(client, idp):
    query = start(client, idp)
    published = idp.jwks()  # the provider keeps publishing its real key...
    idp.jwks = lambda: published
    idp.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)  # ...a forger signs

    assert finish(client, query["state"]).status_code == 502


def test_rotated_keys_are_fetched_again(client, idp):
    first = start(client, idp)
    assert finish(client, first["state"]).status_code == 200

    idp.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    idp.kid = "key-2"
    second = start(client, idp)

    assert finish(client, second["state"]).status_code == 200


def test_an_unverified_email_cannot_sign_in(client, idp):
    idp.claims["email_verified"] = False
    query = start(client, idp)

    response = finish(client, query["state"])

    assert response.status_code == 403 and "verified email" in response.json()["detail"]


def test_unknown_providers_answer_404_and_the_list_shows_configured_ones(client):
    assert client.get("/api/v1/oauth/nope/authorize").status_code == 404
    assert client.get("/api/v1/oauth/providers").json() == [{"name": "acme"}]


def test_a_provider_without_required_settings_stops_start_up(tmp_path):
    with pytest.raises(ValueError, match=r"oauth_providers\.broken needs"):
        build_test_app(tmp_path, oauth_enabled=True, oauth_providers={"broken": {"issuer": ISSUER}})


def test_sign_in_and_linking_are_audited(client, idp):
    query = start(client, idp)
    user_id = finish(client, query["state"]).json()["user"]["id"]

    events, _, _ = run(client.app.state.services.audit_service.list_events(target_id=user_id))

    assert {"user.registered", "oauth.linked"} <= {e["action"] for e in events}
