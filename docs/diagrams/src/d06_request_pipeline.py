from lib import SERIF, label_above, legend, node, path

SLUG = "request-pipeline"
EYEBROW = "Flowchart · for developers and security reviewers"
TITLE = "Every request passes six gates before your route runs"
DESC = ("Request pipeline: a request is tagged with an id and security headers, then its body, origin and "
        "CORS are checked, errors are caught, load is shed, idempotent retries are replayed, and the caller "
        "is authenticated and authorized; any gate can answer early with a problem+json response.")
W, H = 960, 720

STEPS = [  # name, middleware, rejection label (None = never rejects)
    ("Identify", "request id · security headers", None),
    ("Guard the body", "size · idle body · CSRF origin · CORS", "413 · 408 · 403"),
    ("Catch errors", "error handler · access log", "500"),
    ("Shed load", "timeout · concurrency · rate limit", "429 · 503 · 504"),
    ("Replay retries", "Idempotency-Key", "REPLAY · 409 · 422"),
    ("Authenticate · authorize", "session cookies · RBAC", "401 · 403"),
]
X, SW, SH = 180, 240, 56
CX = X + SW // 2  # 300


def body():
    b = []
    tops = [96 + i * 80 for i in range(len(STEPS))]
    # arrows first
    b.append(path(f"M {CX},64 V 96"))
    for y in tops[:-1]:
        b.append(path(f"M {CX},{y + SH} V {y + 80}"))
    b.append(path(f"M {CX},{tops[-1] + SH} V 576", "accent"))
    for (_, _, reject), y in zip(STEPS, tops):
        if reject:
            cy = y + SH // 2
            b.append(path(f"M {X + SW},{cy} H 640"))
            b.append(label_above(530, cy, reject))
    b.append(node(220, 16, 160, 48, "Request", "HTTP · ASGI scope", kind="input", rx=20))
    for i, ((name, mw, _), y) in enumerate(zip(STEPS, tops), 1):
        b.append(node(X, y, SW, SH, name, mw, f"{i:02d}"))
    b.append(node(200, 576, 200, 56, "Your route handler", "permission already checked", "ROUTE", "focal", rx=20))
    b.append(node(640, 144, 240, 400, "Problem response", "application/problem+json", "EXIT", "external", rx=20))
    b.append(f'<text x="640" y="588" fill="{{muted}}" font-size="14" font-style="italic" font-family="{SERIF}">Early answers still flow back out</text>'
             f'<text x="640" y="608" fill="{{muted}}" font-size="14" font-style="italic" font-family="{SERIF}">through gates 1–2: CORS and security</text>'
             f'<text x="640" y="628" fill="{{muted}}" font-size="14" font-style="italic" font-family="{SERIF}">headers ride on every rejection.</text>')
    b.append(legend(668, W, [("muted", "request flow"), ("accent", "accepted"), ("input", "start"),
                             ("focal", "your code"), ("external", "early answer")]))
    return "".join(b)
