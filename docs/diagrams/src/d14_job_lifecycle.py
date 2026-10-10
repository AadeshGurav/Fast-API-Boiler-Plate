from lib import MONO, SANS, e, label_above, label_below, label_side, legend, path

SLUG = "job-lifecycle"
EYEBROW = "State machine · for developers and operators"
TITLE = "A background job either finishes, or waits where you can see it"
DESC = ("Background job states: enqueue creates a queued job; a worker claims it with a conditional update "
        "that exactly one worker wins and runs it under a lease; success marks it done; a failure re-queues "
        "it with exponential backoff and jitter until jobs_max_attempts, then marks it dead; a lease that "
        "expires because the worker stopped re-queues it; an administrator can retry a dead job.")
W, H = 960, 528


def state(x, y, w, h, name, lines, focal=False, kind="backend"):
    fill, stroke = {"focal": ("{accent@0.08}", "{accent}"), "backend": ("{white}", "{ink}"),
                    "store": ("{ink@0.05}", "{muted}")}["focal" if focal else kind]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{{paper}}"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
           f'<text x="{x + 16}" y="{y + 26}" fill="{{ink}}" font-size="12" font-weight="600" font-family="{SANS}">{e(name)}</text>']
    for i, line in enumerate(lines):
        out.append(f'<text x="{x + 16}" y="{y + 46 + i * 15}" fill="{{muted}}" font-size="9" font-family="{MONO}">{e(line)}</text>')
    return "".join(out)


def body():
    b = [
        # enqueue -> queued
        path("M 62,224 H 96"),
        # queued -> running (claim)
        path("M 288,208 H 384"),
        # running -> queued (retry), below the claim arrow
        path("M 384,248 H 290", "dashed"),
        # running -> done
        path("M 608,192 H 752 Q 760,192 760,184 V 138"),
        # running -> dead
        path("M 608,264 H 752 Q 760,264 760,272 V 334", "accent"),
        # lease expired: running -> queued, below everything
        path("M 496,296 V 432 Q 496,440 488,440 H 200 Q 192,440 192,432 V 298", "dashed"),
        # admin retry: dead -> queued, along the top
        path("M 884,376 H 900 Q 908,376 908,368 V 56 Q 908,48 900,48 H 200 Q 192,48 192,56 V 158", "link"),
        label_above(336, 208, "CLAIM · WIN"),
        label_below(336, 248, "RETRY"),
        label_side(760, 160, "SUCCESS", side="right"),
        label_side(760, 300, "MAX ATTEMPTS", "accent", side="right"),
        label_below(344, 440, "LEASE EXPIRED"),
        label_above(524, 48, "ADMIN RETRY", "link"),
        '<circle cx="56" cy="224" r="6" fill="{ink}"/>',
        state(96, 160, 192, 136, "Queued", ["run_at <= now", "backoff with jitter", "idempotency_key"]),
        state(384, 160, 224, 136, "Running", ["one worker holds it", "lease = 2 x timeout", "handler must be", "idempotent"]),
        state(708, 72, 176, 64, "Done", ["kept 14 days"], kind="store"),
        state(708, 336, 176, 80, "Dead", ["last_error kept", "/admin/jobs?status=dead"], focal=True),
    ]
    b.append(f'<text x="96" y="476" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'Workers run inside the API (jobs_run_in_api) or alone (python -m app.jobs); claiming works on any backend.</text>')
    b.append(legend(496, W, [("muted", "transition"), ("dashed", "back to the queue"),
                                     ("accent", "gives up"), ("link", "administrator")]))
    return "".join(b)
