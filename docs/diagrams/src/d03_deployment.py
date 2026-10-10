from lib import MONO, SANS, e, g4, hvh, label_above, label_side, legend, mono_w, node, path, zone

SLUG = "deployment"
EYEBROW = "Deployment · for operators"
TITLE = "Where it runs: one image, three backing services"
DESC = ("Deployment view: clients reach a reverse proxy over HTTPS; the proxy forwards to the API container "
        "(python 3.11-slim image, any number of replicas once Redis and S3 are used); the API talks to MongoDB "
        "8.0, Redis 7.2 and optional S3-compatible storage, with database ports bound to loopback.")
W, H = 960, 496


def infra(x, y, w, tag, name, sub, chips, kind="backend", badge=None):
    h = 60 + len(chips) * 32 - 8 + 12
    out = [node(x, y, w, h, "", None, tag, kind)]  # box + tag; name drawn below at a fixed spot
    out.append(f'<text x="{x + 12}" y="{y + 36}" fill="{{ink}}" font-size="12" font-weight="600" font-family="{SANS}">{e(name)}</text>'
               f'<text x="{x + 12}" y="{y + 50}" fill="{{muted}}" font-size="9" font-family="{MONO}">{e(sub)}</text>')
    cy = y + 60
    for cname, version in chips:
        out.append(f'<rect x="{x + 8}" y="{cy}" width="{w - 16}" height="24" rx="4" fill="{{ink@0.05}}" stroke="{{muted}}" stroke-width="0.8"/>'
                   f'<text x="{x + 16}" y="{cy + 16}" fill="{{ink}}" font-size="12" font-family="{SANS}">{e(cname)}</text>'
                   f'<text x="{x + w - 16}" y="{cy + 16}" fill="{{muted}}" font-size="9" font-family="{MONO}" text-anchor="end">{e(version)}</text>')
        cy += 32
    if badge:
        bw = g4(mono_w(badge, 8, 0.14) + 8)
        out.append(f'<rect x="{x + w - 8 - bw}" y="{y + 6}" width="{bw}" height="12" rx="2" fill="{{paper}}" stroke="{{ink@0.30}}" stroke-width="0.8"/>'
                   f'<text x="{x + w - 8 - bw / 2:g}" y="{y + 15}" fill="{{ink}}" font-size="8" font-family="{MONO}" text-anchor="middle" letter-spacing="0.14em">{e(badge)}</text>')
    return "".join(out), h


def body():
    b = [zone(176, 32, 160, 376, "EDGE", dashed=True),
         zone(384, 32, 256, 376, "APP HOST · DOCKER", dashed=True),
         zone(720, 32, 224, 376, "DATA · LOOPBACK", dashed=True)]
    b += [
        path("M 120,220 H 192", "link"),
        path("M 320,220 H 400", "link"),
        path(hvh(624, 182, 736, 100, mid=672), "link"),
        path("M 624,220 H 736", "link"),
        path(hvh(624, 258, 736, 340, mid=672), "dashed-link"),
        label_above(156, 220, "HTTPS", "link"),
        label_above(360, 220, "HTTP 8000", "link"),
        label_side(672, 140, "27017", "link"),
        label_above(696, 220, "6379", "link"),
        label_side(672, 300, "HTTPS", "dashed-link"),
    ]
    b.append(node(24, 188, 96, 64, "Clients", "browsers · apps", "USER", "input"))
    for part in (
        infra(192, 176, 128, "EDGE", "Reverse proxy", "TLS · timeouts", [("your proxy", "any")], "external"),
        infra(400, 144, 224, "POD", "API container", "python main.py · :8000", [("fastapi_boilerplate", "1.0.0"),
              ("python", "3.11-slim"), ("uvicorn", "0.54.0")], "backend", badge="xN"),
        infra(736, 56, 192, "VM", "MongoDB", "TCP 27017 · records", [("mongo", "8.0")], "focal"),
        infra(736, 176, 192, "VM", "Redis", "TCP 6379 · cache", [("redis", "7.2-alpine")], "store"),
        infra(736, 296, 192, "MANAGED", "Object storage", "optional · S3 / MinIO", [("boto3", "1.43")], "optional"),
    ):
        b.append(part[0])
    b.append(legend(448, W, [("link", "network path"), ("dashed-link", "optional"), ("focal", "single point of failure"),
                             ("optional", "optional service")]))
    return "".join(b)
