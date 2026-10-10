from lib import MONO, diamond, label_above, label_side, legend, node, path

SLUG = "api-token-check"
EYEBROW = "Flowchart · for developers and security reviewers"
TITLE = "An API token can never do more than its owner can right now"
DESC = ("API token check: a fabp_pat_ bearer token is looked up by its SHA-256 hash; an unknown or expired "
        "token, or one whose owner is no longer active, answers 401; the permission the route needs must be "
        "covered by the token's scopes and also held by the owner today, otherwise 403; only then does the "
        "route run.")
W, H = 960, 680


def body():
    b = [
        path("M 360,64 V 86"),
        path("M 360,160 V 198"),
        path("M 360,272 V 310"),
        path("M 360,384 V 422"),
        path("M 360,496 V 530", "accent"),
        path("M 456,124 H 638", "dashed"),
        path("M 456,236 H 638", "dashed"),
        path("M 456,348 H 638", "dashed"),
        path("M 456,460 H 638", "dashed"),
        label_side(360, 180, "YES"),
        label_side(360, 292, "YES"),
        label_side(360, 404, "YES"),
        label_side(360, 514, "YES", "accent"),
        label_above(548, 124, "NO", "dashed"),
        label_above(548, 236, "NO", "dashed"),
        label_above(548, 348, "NO", "dashed"),
        label_above(548, 460, "NO", "dashed"),
        node(240, 24, 240, 40, "Bearer fabp_pat_…", "looked up by SHA-256 hash", kind="input", rx=20),
        diamond(360, 124, 96, 36, "Known, unexpired?"),
        diamond(360, 236, 96, 36, "Owner active?"),
        diamond(360, 348, 96, 36, "Scopes cover it?"),
        diamond(360, 460, 96, 36, "Owner holds it?"),
        node(260, 532, 200, 48, "Route runs", "no session · no refresh", kind="focal", rx=20),
        node(640, 100, 248, 160, "401 problem", "revoked · expired · suspended", kind="external", rx=20),
        node(640, 324, 248, 160, "403 problem", "scopes ∩ current permissions", kind="external", rx=20),
    ]
    b.append(f'<text x="640" y="520" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'A token cannot create or revoke tokens;</text>'
             f'<text x="640" y="534" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'removing a role narrows every token at once.</text>')
    b.append(legend(632, W, [("muted", "check"), ("dashed", "refused"), ("accent", "allowed"),
                             ("focal", "success"), ("external", "early answer")]))
    return "".join(b)
