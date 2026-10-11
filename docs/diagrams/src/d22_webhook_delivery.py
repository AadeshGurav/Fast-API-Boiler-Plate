from lib import MONO, label_above, label_side, legend, node, path, zone

SLUG = "webhook-delivery"
EYEBROW = "Data flow · for developers and integrators"
TITLE = "Webhooks are jobs: signed, retried, and never silently lost"
DESC = ("Webhook delivery: audit events and explicit publish() calls reach WebhookService, which matches "
        "them against subscriptions and queues one webhook.deliver job per match; a worker re-checks the "
        "destination, signs the request (Standard Webhooks HMAC-SHA256 over id, timestamp and body) and "
        "POSTs it; a non-2xx answer is retried with backoff using the same message id, and a receiver that "
        "keeps failing leaves the job dead and visible to administrators.")
W, H = 960, 488


def body():
    b = [
        zone(24, 40, 432, 208, "IN THE API"),
        path("M 192,108 H 238"),
        path("M 192,196 H 238"),
        path("M 432,152 H 542"),
        path("M 736,152 H 822", "link"),
        path("M 640,192 V 318"),
        label_above(214, 108, "EVENT"),
        label_above(488, 152, "ENQUEUE"),
        label_above(779, 152, "SIGNED POST", "link"),
        label_side(640, 256, "NON-2XX x5"),
        node(48, 80, 144, 56, "Audit log", "every security event", "SRC"),
        node(48, 168, 144, 56, "Your service", "publish(event)", "SRC"),
        node(240, 88, 192, 128, "WebhookService", "match user.* · rbac.* · *", "SVC"),
        node(544, 112, 192, 80, "webhook.deliver job", "retry · backoff · same id", "JOB", "focal"),
        node(824, 112, 112, 80, "Receiver", "verify · dedupe", "EXT", "external"),
        node(544, 320, 192, 72, "Dead job", "/admin/jobs?status=dead", "DLQ", "store"),
    ]
    b.append(f'<text x="48" y="436" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'Destinations: https only, never private or loopback addresses (checked again before each delivery); no redirects.</text>')
    b.append(legend(448, W, [("muted", "in-process"), ("link", "HTTPS"), ("focal", "retried unit"),
                             ("store", "visible failure"), ("external", "your other system")]))
    return "".join(b)
