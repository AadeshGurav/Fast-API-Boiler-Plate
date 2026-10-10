from lib import MONO, SANS, e, g4, legend, mono_w

SLUG = "data-model"
EYEBROW = "ER · for developers"
TITLE = "The core collections all hang off a user"
DESC = ("Core data model (security records are in the next diagram): users own sessions, login attempts, file versions, OAuth links, password-reset tokens "
        "and temporary permission grants; roles and groups are configuration, not collections.")
W, H = 960, 568

ENTITIES = {  # name: (x, y, w, fields, focal)
    "sessions": (32, 24, ["# id (sid)", "→ user_id", "refresh_token_hash", "previous hash · rotated_at", "expires_at TTL · revoked_at"]),
    "files": (368, 24, ["# file_id + version", "→ user_id", "storage_path · hash · size", "is_latest · deleted_at", "tags · metadata"]),
    "login_attempts": (704, 24, ["→ user_id", "username · success · reason", "ip_address · user_agent", "timestamp TTL 90 d"]),
    "oauth_accounts": (32, 236, ["→ user_id + provider", "provider_user_id"]),
    "users": (368, 200, ["# id", "username · email (unique)", "password (Argon2id)", "roles[] · groups[]", "status · email_verified",
                         "failed_login_count", "locked_until · last_login"]),
    "temporary_permissions": (704, 248, ["# id", "→ entity_id (user | group)", "permission_id", "start_time · end_time", "revoked_at"]),
    "password_reset_tokens": (368, 404, ["# token_hash", "→ user_id", "expires_at TTL · used_at"]),
}


def entity(name, x, y, fields, w=224):
    h = g4(28 + len(fields) * 14 + 10)
    focal = name == "users"
    fill, stroke = ("{accent@0.08}", "{accent}") if focal else ("{white}", "{ink}")
    tw = g4(mono_w("ENTITY", 7, 0.08) + 8)
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{{paper}}"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
           f'<rect x="{x + 8}" y="{y + 8}" width="{tw}" height="12" rx="2" fill="transparent" stroke="{stroke}" stroke-opacity="0.5" stroke-width="0.8"/>',
           f'<text x="{x + 8 + tw / 2:g}" y="{y + 17}" fill="{stroke}" font-size="7" font-family="{MONO}" text-anchor="middle" letter-spacing="0.08em">ENTITY</text>',
           f'<text x="{x + 16 + tw}" y="{y + 19}" fill="{{ink}}" font-size="12" font-weight="600" font-family="{SANS}">{e(name)}</text>',
           f'<line x1="{x}" y1="{y + 28}" x2="{x + w}" y2="{y + 28}" stroke="{{ink@0.12}}" stroke-width="1"/>']
    for i, f in enumerate(fields):
        out.append(f'<text x="{x + 12}" y="{y + 44 + i * 14}" fill="{{muted}}" font-size="9" font-family="{MONO}">{e(f)}</text>')
    return "".join(out), h


def card(x, y, t, anchor="start"):
    return f'<text x="{x}" y="{y}" fill="{{soft}}" font-size="8" font-family="{MONO}" text-anchor="{anchor}" letter-spacing="0.06em">{t}</text>'


def body():
    line = 'fill="none" stroke="{muted}" stroke-width="1.2"'
    b = [
        f'<path d="M 480,200 V 136" {line}/>',                                    # files
        f'<path d="M 368,220 H 152 Q 144,220 144,212 V 136" {line}/>',           # sessions
        f'<path d="M 368,272 H 256" {line}/>',                                     # oauth
        f'<path d="M 592,220 H 808 Q 816,220 816,212 V 120" {line}/>',           # login attempts
        f'<path d="M 592,304 H 704" {line}/>',                                     # temporary permissions
        f'<path d="M 480,340 V 404" {line}/>',                                     # reset tokens
        card(488, 192, "1"), card(488, 150, "N"),
        card(360, 214, "1", "end"), card(152, 150, "N"),
        card(360, 266, "1", "end"), card(264, 266, "N"),
        card(600, 214, "1"), card(824, 134, "N"),
        card(600, 298, "1"), card(696, 298, "N", "end"),
        card(488, 356, "1"), card(488, 398, "N"),
    ]
    for name, (x, y, fields) in ENTITIES.items():
        b.append(entity(name, x, y, fields)[0])
    b.append(legend(528, W, [("focal", "aggregate root")]))
    b.append(f'<text x="320" y="538" fill="{{muted}}" font-size="9" font-family="{MONO}"># key · → points at a user · TTL: MongoDB expires it · roles &amp; groups live in config.toml</text>')
    return "".join(b)
