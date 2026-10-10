from d10_data_model import entity
from lib import MONO, legend

SLUG = "security-data"
EYEBROW = "ER · for developers and security reviewers"
TITLE = "Security records hang off the user; no secret is stored readable"
DESC = ("Security data model: a user owns API tokens (stored as SHA-256 hashes with scopes and expiry), "
        "at most one two-factor record (an encrypted authenticator secret, the last accepted time step and "
        "hashed recovery codes), and is the actor or target of audit events (append-only, with IP address, "
        "user agent and request id, expiring after audit_retention_days).")
W, H = 960, 520

ENTITIES = {
    "api_tokens": (32, 40, ["# id", "→ user_id", "token_hash (SHA-256)", "prefix · name · scopes[]", "expires_at TTL · last_used_at"]),
    "users": (368, 128, ["# id", "username · email", "roles[] · groups[]", "status · locked_until"]),
    "mfa_totp": (704, 40, ["→ user_id (unique)", "secret (Fernet-encrypted)", "confirmed_at · last_step", "recovery_codes[] (hashed)",
                           "codes_version"]),
    "audit_events": (368, 312, ["# id · at TTL", "→ actor_id · target_id", "action · target_type", "ip · user_agent · request_id",
                                "details (no secrets)"]),
}


def body():
    line = 'fill="none" stroke="{muted}" stroke-width="1.2"'
    b = [
        f'<path d="M 368,168 H 264 Q 256,168 256,160 V 148" {line}/>',   # tokens
        f'<path d="M 592,168 H 808 Q 816,168 816,160 V 148" {line}/>',   # mfa
        f'<path d="M 480,224 V 312" {line}/>',                            # audit
    ]

    def card(x, y, t, anchor="start"):
        return (f'<text x="{x}" y="{y}" fill="{{soft}}" font-size="8" font-family="{MONO}" '
                f'text-anchor="{anchor}" letter-spacing="0.06em">{t}</text>')

    b += [card(360, 162, "1", "end"), card(264, 162, "N"),
          card(600, 162, "1"), card(824, 162, "0..1"),
          card(488, 240, "1"), card(488, 306, "N")]
    for name, (x, y, fields) in ENTITIES.items():
        b.append(entity(name, x, y, fields)[0])
    b.append(f'<text x="32" y="464" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'Tokens and recovery codes: hashes only. Two-factor secret: encrypted with mfa_encryption_key. '
             'All three are read from the database, never the cache.</text>')
    b.append(legend(480, W, [("focal", "aggregate root")]))
    return "".join(b)
