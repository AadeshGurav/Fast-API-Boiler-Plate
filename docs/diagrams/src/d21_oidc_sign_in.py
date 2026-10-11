from lib import MONO, label_above, legend, node, path

SLUG = "oidc-sign-in"
EYEBROW = "Sequence · for developers and security reviewers"
TITLE = "Sign in with any identity provider, and trust only what is signed"
DESC = ("OpenID Connect sign-in: the API sends the browser to the provider with a state, a PKCE challenge "
        "and a nonce, keeping their secrets in an HttpOnly cookie; the provider returns a code; the API "
        "checks the state, exchanges the code with the PKCE verifier, verifies the ID token's signature "
        "against the provider's keys, its issuer, audience, expiry and nonce, then links or creates the "
        "account and opens a session.")
W, H = 960, 672

LANES = {"browser": 120, "api": 360, "idp": 600, "store": 840}
MESSAGES = [  # y, from, to, label, style
    (112, "browser", "api", "GET /AUTHORIZE", "link"),
    (144, "api", "idp", "DISCOVERY", "dashed-link"),
    (176, "api", "browser", "307 + COOKIE", "dashed"),
    (240, "browser", "idp", "SIGN IN THERE", "link"),
    (272, "idp", "browser", "CODE + STATE", "dashed"),
    (328, "browser", "api", "GET /CALLBACK", "link"),
    (360, "api", "idp", "CODE + VERIFIER", "link"),
    (392, "idp", "api", "ID TOKEN", "dashed"),
    (424, "api", "idp", "JWKS (CACHED)", "dashed-link"),
    (488, "api", "store", "LINK ACCOUNT", "muted"),
    (520, "api", "browser", "200 · COOKIES", "accent"),
]


def body():
    b = [f'<line x1="{x}" y1="72" x2="{x}" y2="560" stroke="{{ink@0.22}}" stroke-width="1" stroke-dasharray="3,3"/>'
         for x in LANES.values()]
    for y, src, dst, lab, style in MESSAGES:
        x1, x2 = LANES[src], LANES[dst]
        end = x2 - 2 if x2 > x1 else x2 + 2
        b.append(path(f"M {x1},{y} H {end}", style))
        b.append(label_above((x1 + x2) // 2, y, lab, style))
    b.append(f'<text x="136" y="204" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'cookie: state · PKCE verifier · nonce (HttpOnly, 10 min)</text>')
    b.append(f'<text x="376" y="452" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'verify: signature · iss · aud · exp · nonce</text>')
    b.append(node(48, 24, 144, 48, "Browser", "your front end", "APP", "input"))
    b.append(node(288, 24, 144, 48, "API", "OIDCClient", "SVC", "focal"))
    b.append(node(528, 24, 144, 48, "Identity provider", "Google · Entra · Okta", "IDP", "external"))
    b.append(node(768, 24, 144, 48, "Stores", "users · oauth_accounts", "DB", "store"))
    b.append(legend(624, W, [("link", "HTTP"), ("dashed-link", "provider metadata"), ("muted", "call"),
                             ("dashed", "return"), ("accent", "session opened")]))
    return "".join(b)
