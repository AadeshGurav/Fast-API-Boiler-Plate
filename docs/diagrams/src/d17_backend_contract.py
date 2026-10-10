from lib import MONO, label_side, legend, node, path, zone

SLUG = "backend-contract"
EYEBROW = "Architecture · for developers and decision makers"
TITLE = "One contract suite decides which engines may run the app"
DESC = ("Backend contract: the same tests in tests/contract (database rules, cache rules and a whole-"
        "application smoke test) run against the in-memory stand-ins on every make test, against real "
        "MongoDB 8, PostgreSQL 17 and Redis 7 in CI, and against your own backend class when you name it.")
W, H = 960, 448

TARGETS = [  # x, w, name, sub, tag, kind, label, style
    (56, 128, "FakeDatabase", "in-memory", "DB", "store", "EVERY RUN", "muted"),
    (200, 128, "MongoDB 8", "default", "DB", "store", "CI", "muted"),
    (344, 128, "PostgreSQL 17", "JSONB tables", "DB", "store", "CI", "muted"),
    (488, 128, "Your backend", "module:Class", "DB", "optional", "YOU", "dashed"),
    (664, 112, "MemoryCache", "one process", "KV", "store", "EVERY RUN", "muted"),
    (792, 112, "Redis 7", "default", "KV", "store", "CI", "muted"),
]


def body():
    b = [zone(40, 196, 592, 120, "DATABASES"), zone(648, 196, 272, 120, "CACHES")]
    for x, w, *_rest in TARGETS:
        label, style = _rest[-2], _rest[-1]
        cx = x + w // 2
        b.append(path(f"M {cx},136 V 222", style))
        b.append(label_side(cx, 168, label, style))
    b.append(node(48, 48, 864, 88, "Contract suite", "tests/contract · database rules · cache rules · the whole app on each real database",
                  "TESTS", "focal"))
    for x, w, name, sub, tag, kind, *_ in TARGETS:
        b.append(node(x, 224, w, 72, name, sub, tag, kind))
    b.append(f'<text x="48" y="352" fill="{{muted}}" font-size="9" font-family="{MONO}">'
             'CONTRACT_DATABASES=fake,mongodb,postgres,package.module:Class  CONTRACT_CACHES=memory,redis</text>')
    b.append(f'<text x="48" y="372" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'A backend is finished when the suite is green against it: no application code changes.</text>')
    b.append(legend(408, W, [("muted", "runs against"), ("dashed", "when you name it"), ("focal", "the definition"),
                             ("store", "built in"), ("optional", "bring your own")]))
    return "".join(b)
