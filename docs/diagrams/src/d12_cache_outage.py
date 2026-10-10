from lib import MONO, SANS, e, label_above, label_below, legend, path

SLUG = "cache-outage"
EYEBROW = "State machine · for operators and SREs"
TITLE = "Losing Redis slows the service down, it does not take it down"
DESC = ("Cache circuit states: while healthy the cache is used normally; any cache error opens the circuit "
        "for cache_failure_cooldown_seconds, during which reads fall through to the database, writes are "
        "skipped, rate limiting fails open and idempotent requests answer 503; after the cool-down one call "
        "tries the cache again and either closes or reopens the circuit.")
W, H = 960, 464


def state(x, y, w, h, name, lines, focal=False):
    fill, stroke = ("{accent@0.08}", "{accent}") if focal else ("{white}", "{ink}")
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{{paper}}"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
           f'<text x="{x + 16}" y="{y + 28}" fill="{{ink}}" font-size="12" font-weight="600" font-family="{SANS}">{e(name)}</text>']
    for i, line in enumerate(lines):
        out.append(f'<text x="{x + 16}" y="{y + 50 + i * 16}" fill="{{muted}}" font-size="9" font-family="{MONO}">{e(line)}</text>')
    return "".join(out)


def body():
    b = [
        path("M 62,200 H 96"),
        path("M 288,184 H 384"),
        path("M 608,184 H 704"),
        path("M 704,216 H 608", "accent"),
        path("M 800,264 V 352 Q 800,360 792,360 H 200 Q 192,360 192,352 V 264"),
        label_above(336, 184, "ANY ERROR"),
        label_above(656, 184, "10 S PASS"),
        label_below(656, 216, "FAILS", "accent"),
        label_below(496, 360, "SUCCEEDS"),
        '<circle cx="56" cy="200" r="6" fill="{ink}"/>',
        state(96, 136, 192, 128, "Healthy", ["cache read and written", "sessions · permissions", "rate counters · claims"]),
        state(384, 136, 224, 128, "Cooling down", ["reads → database answers", "writes skipped, TTL cleans", "rate limit fails open",
                                                   "idempotency → 503"], focal=True),
        state(704, 136, 192, 128, "Trial call", ["next request tries Redis", "1 s timeout, 1 retry"]),
    ]
    b.append(legend(424, W, [("muted", "transition"), ("accent", "outage continues"), ("focal", "degraded but serving")]))
    return "".join(b)
