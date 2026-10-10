from lib import MONO, label_above, legend, node, path

SLUG = "mfa-sign-in"
EYEBROW = "Sequence · for developers, designers and security reviewers"
TITLE = "Two-factor sign-in: the password opens nothing on its own"
DESC = ("Two-factor sign-in sequence: a correct password answers 401 mfa_required with a five-minute "
        "challenge token instead of a session; the client sends it back with an authenticator or recovery "
        "code; a valid code newer than the last accepted one is claimed with a conditional write and opens "
        "the session, while a wrong or replayed code counts towards the account lockout and answers 401.")
W, H = 960, 680

LANES = {"client": 120, "api": 360, "auth": 600, "store": 840}
MESSAGES = [  # y, from, to, label, style
    (112, "client", "api", "POST /AUTH/LOGIN", "link"),
    (144, "api", "auth", "PASSWORD + MFA?", "muted"),
    (176, "auth", "store", "FACTOR ENABLED", "muted"),
    (208, "api", "client", "401 MFA_REQUIRED", "dashed"),
    (264, "client", "api", "POST /LOGIN/MFA", "link"),
    (296, "api", "auth", "TOKEN + CODE", "muted"),
    (368, "auth", "store", "CLAIM TIME STEP", "muted"),
    (400, "api", "client", "200 · COOKIES", "accent"),
    (480, "auth", "store", "COUNT FAILURE", "muted"),
    (512, "api", "client", "401 · PROBLEM", "dashed"),
]


def body():
    b = [f'<line x1="{x}" y1="72" x2="{x}" y2="584" stroke="{{ink@0.22}}" stroke-width="1" stroke-dasharray="3,3"/>'
         for x in LANES.values()]
    b.append('<rect x="96" y="320" width="768" height="232" rx="4" fill="{ink@0.02}" stroke="{ink@0.22}" stroke-width="1"/>'
             '<rect x="96" y="320" width="40" height="16" rx="2" fill="{paper}" stroke="{ink@0.22}" stroke-width="1"/>'
             f'<text x="116" y="332" fill="{{muted}}" font-size="8" font-family="{MONO}" text-anchor="middle" letter-spacing="0.12em">ALT</text>'
             f'<text x="144" y="332" fill="{{muted}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">[code valid and newer than the last accepted step]</text>'
             '<line x1="104" y1="432" x2="856" y2="432" stroke="{ink@0.20}" stroke-width="1" stroke-dasharray="4,3"/>'
             f'<text x="132" y="452" fill="{{muted}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">[else · wrong, expired or replayed: same lockout as a wrong password]</text>')
    for y, src, dst, lab, style in MESSAGES:
        x1, x2 = LANES[src], LANES[dst]
        end = x2 - 2 if x2 > x1 else x2 + 2
        b.append(path(f"M {x1},{y} H {end}", style))
        b.append(label_above((x1 + x2) // 2, y, lab, style))
    b.append(f'<text x="128" y="236" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">details.mfa_token · valid 5 min · typed "mfa", never an access token</text>')
    b.append(node(48, 24, 144, 48, "Client", "web · mobile app", "APP", "input"))
    b.append(node(288, 24, 144, 48, "API", "/auth/login · /login/mfa", "API"))
    b.append(node(528, 24, 144, 48, "AuthService", "MFAService · tokens", "SVC", "focal"))
    b.append(node(768, 24, 144, 48, "Stores", "mfa_totp · users", "DB", "store"))
    b.append(legend(624, W, [("link", "HTTP call"), ("muted", "internal call"), ("dashed", "return"),
                             ("accent", "session opened")]))
    return "".join(b)
