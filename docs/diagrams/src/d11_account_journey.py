from lib import MONO, SANS, e, g4, mono_w

SLUG = "account-journey"
EYEBROW = "User journey · for designers and product"
TITLE = "An account's life, as the person behind it feels it"
DESC = ("Account journey for one end user: signing up and signing in feel good, everyday use stays signed in "
        "silently, the low point is a lockout or forgotten password where the API deliberately says little, "
        "and recovery by email restores confidence.")
W, H = 1232, 584
LEVEL = {"HIGH": 88, "MED-HIGH": 128, "NEUTRAL": 168, "MED-LOW": 208, "LOW": 248}
STAGES = [  # name, level, actions (lines), touchpoints, design needs
    ("Sign up", "MED-HIGH", ["Picks a username, email", "and a strong password"],
     ["POST /auth/register", "201 · or 400 with the policy"], ["show the password policy", "before the first error"]),
    ("Sign in", "HIGH", ["Signs in, may tick", "remember me (30 days)"],
     ["POST /auth/login", "HttpOnly cookies set"], ["one generic error for", "every failure"]),
    ("Use the app", "HIGH", ["Works for days without", "signing in again"],
     ["any /api/v1 call", "expired token refreshed"], ["no forced re-login", "list devices: /sessions"]),
    ("Locked out", "LOW", ["Five wrong tries lock", "the account for 15 min"],
     ["same 401 as a typo", "reset-password-request"], ["say 'try again later or", "reset' without confirming"]),
    ("Recover", "MED-HIGH", ["Follows the email link,", "sets a new password"],
     ["reset-password-confirm", "all sessions signed out"], ["confirm success and that", "other devices signed out"]),
]
PAINS = ["NO LOCK MESSAGE", "WAITS FOR EMAIL"]


def col(i):
    return 96 + i * 224


def lines(x, y, rows, family, size, color):
    return "".join(f'<text x="{x}" y="{y + k * (size + 5)}" fill="{color}" font-size="{size}" font-family="{family}" text-anchor="middle">{e(r)}</text>'
                   for k, r in enumerate(rows))


def body():
    right = col(4) + 200
    b = []
    for name, y in (("HIGH", 88), ("NEUTRAL", 168), ("LOW", 248)):
        b.append(f'<line x1="96" y1="{y}" x2="{right}" y2="{y}" stroke="{{ink@0.10}}" stroke-width="1"/>'
                 f'<text x="84" y="{y + 3}" fill="{{muted}}" font-size="8" font-family="{MONO}" text-anchor="end" letter-spacing="0.14em">{name}</text>')
    for y, label in ((272, "ACTIONS"), (360, "TOUCHPOINTS"), (424, "DESIGN NEEDS")):
        b.append(f'<line x1="24" y1="{y}" x2="{right}" y2="{y}" stroke="{{ink@0.10}}" stroke-width="1"/>'
                 f'<text x="84" y="{y + 20}" fill="{{muted}}" font-size="8" font-family="{MONO}" text-anchor="end" letter-spacing="0.14em">{label}</text>')
    pts = [(col(i) + 100, LEVEL[s[1]]) for i, s in enumerate(STAGES)]
    trough = min(range(len(pts)), key=lambda i: -pts[i][1])
    for i in range(len(pts) - 1):
        accent = i + 1 == trough
        stroke, width = ("{accent}", "1.8") if accent else ("{muted}", "1.5")
        b.append(f'<line x1="{pts[i][0]}" y1="{pts[i][1]}" x2="{pts[i + 1][0]}" y2="{pts[i + 1][1]}" stroke="{stroke}" stroke-width="{width}"/>')
    for i, (x, y) in enumerate(pts):
        b.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{{accent}}" stroke="{{paper}}" stroke-width="1.5"/>' if i == trough
                 else f'<circle cx="{x}" cy="{y}" r="5" fill="{{muted}}" stroke="{{paper}}" stroke-width="1.5"/>')
    for i, (name, _, actions, touch, needs) in enumerate(STAGES):
        cx = col(i) + 100
        b.append(f'<text x="{cx}" y="40" fill="{{muted}}" font-size="8" font-family="{MONO}" text-anchor="middle" letter-spacing="0.14em">STAGE {i + 1}</text>'
                 f'<text x="{cx}" y="60" fill="{{ink}}" font-size="12" font-weight="600" font-family="{SANS}" text-anchor="middle">{e(name)}</text>')
        b.append(lines(cx, 296, actions, SANS, 12, "{ink}"))
        b.append(lines(cx, 382, touch, MONO, 9, "{muted}"))
        b.append(lines(cx, 446, needs, MONO, 9, "{muted}"))
    x0 = col(trough) + 100
    for k, pain in enumerate(PAINS):
        w = g4(mono_w(pain, 8) + 12)
        y = 324 + k * 16 if False else 330
        x = x0 - w - 4 if k == 0 else x0 + 4
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="16" rx="2" fill="{{accent@0.05}}" stroke="{{accent@0.50}}" stroke-width="1" stroke-dasharray="3,3"/>'
                 f'<text x="{x + w / 2:g}" y="{y + 11}" fill="{{accent}}" font-size="8" font-family="{MONO}" text-anchor="middle" letter-spacing="0.06em">{pain}</text>')
    ly = 528
    b.append(f'<line x1="32" y1="{ly - 8}" x2="{W - 32}" y2="{ly - 8}" stroke="{{ink@0.10}}" stroke-width="0.8"/>'
             f'<text x="32" y="{ly + 10}" fill="{{muted}}" font-size="8" font-family="{MONO}" letter-spacing="0.14em">LEGEND</text>'
             f'<line x1="112" y1="{ly + 7}" x2="140" y2="{ly + 7}" stroke="{{muted}}" stroke-width="1.5"/><circle cx="126" cy="{ly + 7}" r="4" fill="{{muted}}"/>'
             f'<text x="148" y="{ly + 10}" fill="{{muted}}" font-size="9" font-family="{MONO}">how it feels</text>'
             f'<line x1="272" y1="{ly + 7}" x2="300" y2="{ly + 7}" stroke="{{accent}}" stroke-width="1.8"/><circle cx="286" cy="{ly + 7}" r="4" fill="{{accent}}"/>'
             f'<text x="308" y="{ly + 10}" fill="{{muted}}" font-size="9" font-family="{MONO}">the low point</text>'
             f'<rect x="440" y="{ly}" width="28" height="14" rx="2" fill="{{accent@0.05}}" stroke="{{accent@0.50}}" stroke-dasharray="3,3"/>'
             f'<text x="476" y="{ly + 10}" fill="{{muted}}" font-size="9" font-family="{MONO}">friction to design for</text>')
    return "".join(b)
