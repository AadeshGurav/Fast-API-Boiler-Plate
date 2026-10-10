from lib import MONO, label_above, legend, node, path

SLUG = "auth-sequence"
EYEBROW = "Sequence · for developers and security reviewers"
TITLE = "Sign in once, refresh silently, catch a stolen token"
DESC = ("Authentication sequence: login creates a server-side session and a token pair bound to it; when "
        "the access token expires the refresh cookie is rotated transparently, and replaying an "
        "already-rotated refresh token revokes the whole session and answers 401.")
W, H = 960, 704

LANES = {"client": 120, "api": 360, "auth": 600, "store": 840}
MESSAGES = [  # y, from, to, label, style
    (112, "client", "api", "POST /AUTH/LOGIN", "link"),
    (144, "api", "auth", "LOGIN_USER()", "muted"),
    (176, "auth", "store", "SESSION + HASH", "muted"),
    (208, "store", "auth", "OK", "dashed"),
    (240, "auth", "api", "TOKENS · SID", "dashed"),
    (272, "api", "client", "200 · COOKIES", "accent"),
    (320, "client", "api", "GET /FILES · EXPIRED", "link"),
    (400, "api", "auth", "REFRESH_TOKENS()", "muted"),
    (432, "auth", "store", "ROTATE HASH", "muted"),
    (464, "api", "client", "200 · NEW COOKIES", "dashed"),
    (536, "auth", "store", "REVOKE SESSION", "muted"),
    (568, "api", "client", "401 · PROBLEM", "dashed"),
]


def body():
    b = [f'<line x1="{x}" y1="72" x2="{x}" y2="616" stroke="{{ink@0.22}}" stroke-width="1" stroke-dasharray="3,3"/>'
         for x in LANES.values()]
    # alt fragment
    b.append('<rect x="96" y="344" width="768" height="248" rx="4" fill="{ink@0.02}" stroke="{ink@0.22}" stroke-width="1"/>'
             '<rect x="96" y="344" width="40" height="16" rx="2" fill="{paper}" stroke="{ink@0.22}" stroke-width="1"/>'
             f'<text x="116" y="356" fill="{{muted}}" font-size="8" font-family="{MONO}" text-anchor="middle" letter-spacing="0.12em">ALT</text>'
             f'<text x="132" y="376" fill="{{muted}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">[refresh token is the current one]</text>'
             '<line x1="104" y1="496" x2="856" y2="496" stroke="{ink@0.20}" stroke-width="1" stroke-dasharray="4,3"/>'
             f'<text x="132" y="516" fill="{{muted}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">[else · an already-rotated token was replayed]</text>')
    for y, src, dst, lab, style in MESSAGES:
        x1, x2 = LANES[src], LANES[dst]
        end = x2 - 2 if x2 > x1 else x2 + 2
        b.append(path(f"M {x1},{y} H {end}", style))
        b.append(label_above((x1 + x2) // 2, y, lab, style))
    b.append(node(48, 24, 144, 48, "Client", "browser · app", "APP", "input"))
    b.append(node(288, 24, 144, 48, "API", "middleware + routes", "API"))
    b.append(node(528, 24, 144, 48, "AuthService", "tokens · sessions", "SVC", "focal"))
    b.append(node(768, 24, 144, 48, "Session store", "MongoDB + cache", "DB", "store"))
    b.append(legend(648, W, [("link", "HTTP call"), ("muted", "internal call"), ("dashed", "return"),
                             ("accent", "headline success")]))
    return "".join(b)
