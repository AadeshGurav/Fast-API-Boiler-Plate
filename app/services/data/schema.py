"""Indexes the application needs, declared once and applied by the data layer.

The database backends stay generic; this module is the only place that knows
which collections exist and how they are queried.
"""

from __future__ import annotations

from typing import Any

ASCENDING = 1
DESCENDING = -1

COLLECTION_INDEXES: dict[str, list[dict[str, Any]]] = {
    "users": [
        {"keys": [("id", ASCENDING)], "unique": True},
        {"keys": [("username", ASCENDING)], "unique": True},
        # Sparse: users created through OAuth may have no email yet.
        {"keys": [("email", ASCENDING)], "unique": True, "sparse": True},
        {"keys": [("created_at", DESCENDING)]},
    ],
    "sessions": [
        {"keys": [("id", ASCENDING)], "unique": True},
        {"keys": [("user_id", ASCENDING), ("created_at", DESCENDING)]},
        # Expired sessions are useless (tokens bound to them already fail); purge them.
        {"keys": [("expires_at", ASCENDING)], "expireAfterSeconds": 0},
    ],
    "login_attempts": [
        {"keys": [("user_id", ASCENDING), ("timestamp", DESCENDING)]},
        {"keys": [("timestamp", ASCENDING)], "expireAfterSeconds": 90 * 24 * 3600},
    ],
    "temporary_permissions": [
        {"keys": [("id", ASCENDING)], "unique": True},
        {"keys": [("entity_id", ASCENDING)]},
        {"keys": [("end_time", ASCENDING)]},
    ],
    "oauth_accounts": [
        {"keys": [("user_id", ASCENDING), ("provider", ASCENDING)], "unique": True},
    ],
    "files": [
        {"keys": [("file_id", ASCENDING), ("version", DESCENDING)], "unique": True},
        {"keys": [("user_id", ASCENDING), ("hash", ASCENDING)]},
        # Serves the listing (equality on the first three, then sorted by created_at).
        {
            "keys": [
                ("user_id", ASCENDING),
                ("is_latest", ASCENDING),
                ("deleted_at", ASCENDING),
                ("created_at", DESCENDING),
            ]
        },
        {"keys": [("user_id", ASCENDING), ("tags", ASCENDING)]},
    ],
    "audit_events": [
        {"keys": [("id", ASCENDING)], "unique": True},
        {"keys": [("actor_id", ASCENDING), ("at", DESCENDING)]},
        {"keys": [("target_type", ASCENDING), ("target_id", ASCENDING), ("at", DESCENDING)]},
        {"keys": [("action", ASCENDING), ("at", DESCENDING)]},
        # The time-to-live index on "at" is added from settings: see collection_indexes().
    ],
    "api_tokens": [
        {"keys": [("id", ASCENDING)], "unique": True},
        {"keys": [("token_hash", ASCENDING)], "unique": True},
        {"keys": [("user_id", ASCENDING), ("created_at", DESCENDING)]},
        # Expired tokens are useless (authentication checks expiry too); let the store purge them.
        {"keys": [("expires_at", ASCENDING)], "expireAfterSeconds": 0},
    ],
    "jobs": [
        {"keys": [("id", ASCENDING)], "unique": True},
        # Serves the worker's "due jobs" query.
        {"keys": [("status", ASCENDING), ("run_at", ASCENDING)]},
        {"keys": [("status", ASCENDING), ("lease_until", ASCENDING)]},
        {"keys": [("idempotency_key", ASCENDING)], "unique": True, "sparse": True},
        {"keys": [("created_at", DESCENDING)]},
        # The time-to-live index on "finished_at" is added from settings: see collection_indexes().
    ],
    "passkeys": [
        {"keys": [("id", ASCENDING)], "unique": True},
        {"keys": [("credential_id", ASCENDING)], "unique": True},
        {"keys": [("user_id", ASCENDING), ("created_at", DESCENDING)]},
    ],
    "webauthn_challenges": [
        {"keys": [("id", ASCENDING)], "unique": True},
        {"keys": [("expires_at", ASCENDING)], "expireAfterSeconds": 0},
    ],
    "webhooks": [
        {"keys": [("id", ASCENDING)], "unique": True},
    ],
    "mfa_totp": [
        {"keys": [("user_id", ASCENDING)], "unique": True},
    ],
    "password_reset_tokens": [
        {"keys": [("token_hash", ASCENDING)], "unique": True},
        # Expired reset tokens are useless; let MongoDB purge them.
        {"keys": [("expires_at", ASCENDING)], "expireAfterSeconds": 0},
    ],
}


def collection_indexes(config: Any) -> dict[str, list[dict[str, Any]]]:
    """``COLLECTION_INDEXES`` plus the indexes whose options come from settings."""
    day = 24 * 3600
    return {
        **COLLECTION_INDEXES,
        "audit_events": [
            *COLLECTION_INDEXES["audit_events"],
            {
                "keys": [("at", ASCENDING)],
                "expireAfterSeconds": config["audit_retention_days"] * day,
            },
        ],
        # Unfinished jobs have finished_at = None, which a TTL index never expires.
        "jobs": [
            *COLLECTION_INDEXES["jobs"],
            {
                "keys": [("finished_at", ASCENDING)],
                "expireAfterSeconds": config["jobs_retention_days"] * day,
            },
        ],
    }
