from lib import MONO, SANS, e, hv, vhv

SLUG = "before-after"
EYEBROW = "Architecture delta · for decision makers"
TITLE = "What the polish changed"
DESC = ("Before and after the hardening rewrite: the demo UI and its page traffic were removed, the "
        "dependency-injection container became plain wiring, and the API, cache and file storage changed "
        "behaviour while the client and MongoDB stayed the same.")
W, H = 1200, 680
SVG_ATTRS = ' data-diagram="architecture-delta"'

MARK = {"unchanged": "=", "changed": "~", "removed": "−", "added": "+"}

# id: (x, y, w, h, name, sub_before, sub_after, sig_before, sig_after, status)
COMPONENTS = {
    "client": (104, 0, 128, 64, "Client", "browser", "browser · app", "client", "client", "unchanged"),
    "ui": (256, 96, 80, 64, "Demo UI", "Jinja · JS", None, "ui:jinja", None, "removed"),
    "api": (104, 96, 128, 64, "API", "HTML + JSON", "JSON · RFC 9457", "api:html+json;basehttp", "api:json;pure-asgi", "changed"),
    "wiring": (104, 192, 128, 64, "Wiring", "DI container", "build_services()", "wiring:container;globals", "wiring:explicit", "changed"),
    "mongo": (0, 304, 96, 64, "MongoDB", "records", "records", "mongodb", "mongodb", "unchanged"),
    "cache": (120, 304, 96, 64, "Cache", "Redis as DB", "Redis · memory", "cache:redis-as-db", "cache:pluggable;degrades", "changed"),
    "storage": (240, 304, 96, 64, "Storage", "local · in RAM", "local · S3", "storage:local;buffered", "storage:local|s3;streamed", "changed"),
}
# id: (from, to, d, status, signature)
RELATIONS = {
    "r-request": ("client", "api", "M 168 64 V 96", "unchanged", "https:api"),
    "r-pages": ("client", "ui", hv(232, 32, 296, 96), "removed", "https:html"),
    "r-services": ("api", "wiring", "M 168 160 V 192", "unchanged", "uses"),
    "r-records": ("wiring", "mongo", vhv(136, 256, 48, 304, mid=280), "unchanged", "query"),
    "r-cache": ("wiring", "cache", "M 168 256 V 304", "unchanged", "get-set"),
    "r-bytes": ("wiring", "storage", vhv(200, 256, 288, 304, mid=280), "unchanged", "read-write"),
}
LEDGER = [
    ("REMOVED", "ui", "Demo pages, templates and JS: API-only"),
    ("REMOVED", "r-pages", "Browsers no longer fetch HTML pages"),
    ("CHANGED", "api", "Pure-ASGI middleware, problem+json errors"),
    ("CHANGED", "wiring", "DI container → plain build_services()"),
    ("CHANGED", "cache", "Pluggable; slows down, never fails, when lost"),
    ("CHANGED", "storage", "Streamed end to end; local disk or S3"),
]


def component(cid, snap):
    x, y, w, h, name, sb, sa, sigb, siga, status = COMPONENTS[cid]
    sub, sig = (sb, sigb) if snap == "before" else (sa, siga)
    focal = cid == "api"
    fill = "{accent@0.08}" if focal else "{white}"
    stroke = "{accent}" if focal else "{muted}"
    dash = ' stroke-dasharray="4 4"' if status == "removed" else ""
    out = [f'<g data-kind="component" data-object-id="{cid}" data-status="{status}" data-signature="{e(sig)}">',
           f'<rect data-role="bounds" x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.2"{dash}/>']
    if status == "changed":
        out.append(f'<path d="M {x + 1} {y + 12} V {y + h - 12}" fill="none" stroke="{stroke}" stroke-width="3"/>')
    out += [f'<text x="{x + 10}" y="{y + 15}" fill="{{muted}}" font-size="7.5" font-family="{MONO}">{MARK[status]} {cid}</text>',
            f'<text x="{x + 10}" y="{y + 36}" fill="{{ink}}" font-size="12" font-family="{SANS}" font-weight="600">{e(name)}</text>',
            f'<text x="{x + 10}" y="{y + 53}" fill="{{muted}}" font-size="9" font-family="{MONO}">{e(sub)}</text>',
            "</g>"]
    return "".join(out)


def relation(rid):
    src, dst, d, status, sig = RELATIONS[rid]
    dash = ' stroke-dasharray="4 4"' if status == "removed" else ""
    return (f'<path data-kind="relationship" data-object-id="{rid}" data-status="{status}" data-signature="{sig}" '
            f'data-from="{src}" data-to="{dst}" d="{d}" fill="none" stroke="{{muted}}" stroke-width="1.2"{dash} marker-end="url(#arrow)"/>')


def snapshot(snap, tx):
    keep = lambda status: not (snap == "after" and status == "removed")  # noqa: E731
    out = [f'<g data-snapshot="{snap}" transform="translate({tx} 96)" data-grid="336 480 4">']
    out += [relation(r) for r, v in RELATIONS.items() if keep(v[3])]
    out += [component(c, snap) for c, v in COMPONENTS.items() if keep(v[9])]
    out.append("</g>")
    return "".join(out)


def heading(x, title, sub):
    return (f'<text x="{x}" y="28" fill="{{ink}}" font-size="14" font-family="{SANS}" font-weight="600">{e(title)}</text>'
            f'<text x="{x}" y="52" fill="{{muted}}" font-size="10" font-family="{SANS}">{e(sub)}</text>')


def body():
    b = [heading(24, "Before", "develop @ c544392 · demo UI + DI container"),
         heading(424, "Changes", "2 removals · 4 behaviour changes"),
         heading(840, "After", "arch/polished-boilerplate · API-only"),
         '<path d="M 392 8 V 576 M 808 8 V 576" stroke="{ink@0.12}" stroke-width="1"/>',
         snapshot("before", 24)]
    y = 108
    for i, (change, target, line) in enumerate(LEDGER, 1):
        b.append(f'<text x="424" y="{y + 2}" fill="{{muted}}" font-size="9" font-family="{MONO}">{i:02d}</text>'
                 f'<text x="456" y="{y}" data-change="{change}" data-target="{target}" fill="{{muted}}" font-size="8" '
                 f'font-family="{MONO}" letter-spacing="0.06em">{change} · {target}'
                 f'<tspan x="456" y="{y + 23}" fill="{{ink}}" font-size="12" font-family="{SANS}" letter-spacing="0">{e(line)}</tspan></text>')
        if i < len(LEDGER):
            b.append(f'<path d="M 456 {y + 40} H 776" stroke="{{ink@0.12}}" stroke-width="0.8"/>')
        y += 60
    b.append(f'<text x="424" y="{y + 20}" fill="{{muted}}" font-size="8" font-family="{MONO}" letter-spacing="0.14em">PRESERVED</text>'
             f'<text x="424" y="{y + 40}" fill="{{muted}}" font-size="11" font-family="{SANS}">client · MongoDB · every data path</text>')
    b.append(snapshot("after", 840))
    b.append('<path d="M 24 608 H 1176" stroke="{ink@0.12}" stroke-width="1"/>')
    items = [(24, "= Unchanged", ""), (220, "− Removed", ' stroke-dasharray="4 4"'), (416, "~ Changed", "")]
    for x, lab, dash in items:
        b.append(f'<rect x="{x}" y="624" width="20" height="16" rx="3" fill="none" stroke="{{muted}}" stroke-width="1"{dash}/>')
        if lab.startswith("~"):
            b.append(f'<path d="M {x + 1} 628 V 636" stroke="{{muted}}" stroke-width="3"/>')
        b.append(f'<text x="{x + 32}" y="636" fill="{{muted}}" font-size="11" font-family="{SANS}">{lab}</text>')
    b.append(f'<rect x="612" y="624" width="20" height="16" rx="3" fill="{{accent@0.08}}" stroke="{{accent}}" stroke-width="1"/>'
             f'<text x="644" y="636" fill="{{muted}}" font-size="11" font-family="{SANS}">Focus: the API surface</text>')
    b.append(f'<text x="24" y="660" fill="{{muted}}" font-size="9" font-family="{SANS}">IDs persist across snapshots. '
             f'Dashed strokes mark removal, the left bar a behaviour change.</text>'
             f'<text x="1176" y="660" fill="{{muted}}" font-size="9" font-family="{MONO}" text-anchor="end">7 components · 6 relationships · 6 changes</text>')
    return "".join(b)
