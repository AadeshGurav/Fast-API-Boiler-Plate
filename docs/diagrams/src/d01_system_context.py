from lib import hv, hvh, label_above, label_side, legend, node, path, vhv, zone

SLUG = "system-context"
EYEBROW = "Architecture · for decision makers"
TITLE = "One service, three data stores, everything else optional"
DESC = ("System context: browser and mobile clients reach a single FastAPI service through an optional "
        "reverse proxy; the service keeps records and background jobs in MongoDB or PostgreSQL, cache and limits in Redis, and file bytes on "
        "local disk or S3, and can optionally use OpenID Connect identity providers, an SMTP server and observability tools.")
W, H = 960, 528


def body():
    b = [zone(656, 56, 208, 284, "DATA YOU OWN")]
    # arrows first
    b += [
        path("M 160,200 H 208", "link"),
        path("M 336,200 H 392", "link"),
        path(hvh(568, 180, 672, 112, mid=616), "muted"),
        path("M 568,200 H 672", "muted"),
        path(hvh(568, 220, 672, 288, mid=616), "muted"),
        path(vhv(436, 240, 296, 392, mid=316), "dashed-link"),
        path("M 480,240 V 392", "dashed-link"),
        path(vhv(524, 240, 664, 392, mid=316), "dashed"),
    ]
    b += [
        label_above(184, 200, "HTTPS", "link"),
        label_above(364, 200, "HTTP", "link"),
        label_above(644, 112, "RECORDS"),
        label_above(620, 200, "CACHE"),
        label_above(644, 288, "BYTES"),
        label_side(296, 358, "SIGN-IN", "dashed-link", side="left"),
        label_side(480, 356, "EMAIL", "dashed-link"),
        label_side(664, 358, "METRICS", "dashed"),
    ]
    b += [
        node(32, 168, 128, 64, "Client apps", "web · mobile · CLI", "USER", "input"),
        node(208, 168, 128, 64, "Reverse proxy", "TLS · your choice", "EDGE", "optional"),
        node(392, 160, 176, 80, "FastAPI service", "one deployable · /api/v1", "API", "focal"),
        node(672, 80, 176, 64, "Database", "MongoDB or PostgreSQL", "DB", "store"),
        node(672, 168, 176, 64, "Redis", "cache · limits · replay", "KV", "store"),
        node(672, 256, 176, 64, "File storage", "local disk or S3", "OBJ", "store"),
        node(216, 392, 160, 56, "Identity providers", "Google · Entra · Okta", "IDP", "external"),
        node(400, 392, 160, 56, "SMTP server", "resets · email jobs", "MAIL", "external"),
        node(584, 392, 160, 56, "Observability", "Prometheus · OTel · Sentry", "OPS", "optional"),
    ]
    b.append(legend(488, W, [("link", "HTTP"), ("muted", "internal"), ("dashed", "optional"),
                             ("focal", "the service"), ("store", "data store"), ("external", "third party")]))
    return "".join(b)
