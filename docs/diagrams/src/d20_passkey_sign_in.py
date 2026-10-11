from lib import MONO, label_above, legend, node, path

SLUG = "passkey-sign-in"
EYEBROW = "Sequence · for developers, designers and security reviewers"
TITLE = "A passkey signs one challenge, for one site, once"
DESC = ("Passkey sign-in: the client asks for options and gets a single-use challenge; the browser asks the "
        "device's authenticator, which checks the user (biometric or PIN) and signs the challenge with a key "
        "that only works on this site's origin; the API verifies the signature, origin, user verification "
        "and signature counter, deletes the challenge, and opens a session without a password or code.")
W, H = 960, 616

LANES = {"device": 120, "client": 360, "api": 600, "store": 840}
MESSAGES = [  # y, from, to, label, style
    (112, "client", "api", "POST LOGIN/OPTIONS", "link"),
    (144, "api", "store", "SAVE CHALLENGE", "muted"),
    (176, "api", "client", "OPTIONS + ID", "dashed"),
    (232, "client", "device", "CREDENTIALS.GET", "muted"),
    (264, "device", "client", "SIGNED · UV", "dashed"),
    (320, "client", "api", "POST /LOGIN", "link"),
    (352, "api", "store", "TAKE CHALLENGE", "muted"),
    (384, "api", "store", "PUBLIC KEY", "muted"),
    (440, "api", "client", "200 · COOKIES", "accent"),
]


def body():
    b = [f'<line x1="{x}" y1="72" x2="{x}" y2="488" stroke="{{ink@0.22}}" stroke-width="1" stroke-dasharray="3,3"/>'
         for x in LANES.values()]
    for y, src, dst, lab, style in MESSAGES:
        x1, x2 = LANES[src], LANES[dst]
        end = x2 - 2 if x2 > x1 else x2 + 2
        b.append(path(f"M {x1},{y} H {end}", style))
        b.append(label_above((x1 + x2) // 2, y, lab, style))
    b.append(f'<text x="384" y="408" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'verify: signature · origin · rp id · user verified · counter grows</text>')
    b.append(f'<text x="96" y="296" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'Face ID / Touch ID / PIN; the key never leaves the device</text>')
    b.append(node(48, 24, 144, 48, "Authenticator", "phone · laptop · key", "DEV", "security"))
    b.append(node(288, 24, 144, 48, "Client app", "navigator.credentials", "APP", "input"))
    b.append(node(528, 24, 144, 48, "API", "PasskeyManager", "SVC", "focal"))
    b.append(node(768, 24, 144, 48, "Stores", "passkeys · challenges", "DB", "store"))
    b.append(legend(568, W, [("link", "HTTP call"), ("muted", "call"), ("dashed", "return"),
                             ("accent", "session opened")]))
    return "".join(b)
