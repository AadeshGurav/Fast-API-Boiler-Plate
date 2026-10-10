from lib import SERIF, layer_stack, legend

SLUG = "code-layers"
EYEBROW = "Layer stack · for developers"
TITLE = "Five layers, each calling only the one below"
DESC = ("Code layers from top to bottom: HTTP routes, business services, the cache-aware data layer with "
        "per-collection ops, the backend services that pick and guard an engine, and the swappable engines "
        "for MongoDB, Redis or memory, and local disk or S3.")
W, H = 960, 496

LAYERS = [
    ("5", "Routes", "app/api/routes/ · parse, call a service, shape the reply", "no business logic", False),
    ("4", "Services", "auth · rbac · file · oauth · password", "never touch Mongo or Redis", False),
    ("3", "Data layer", "DataService + services/data/*_ops.py · cache keys", "where queries live", True),
    ("2", "Backend services", "DatabaseService · CacheService · create_storage", "pick, namespace, degrade", False),
    ("1", "Engines", "MongoDB · Redis | memory · local | S3", "package.module:Class", False),
]


def body():
    b, bottom = layer_stack(LAYERS, "CALLS", "ENGINE", arrow_up=False)
    return "".join([b, f'<text x="144" y="{bottom + 36}" fill="{{muted}}" font-size="14" font-style="italic" font-family="{SERIF}">'
                    "Middleware wraps the top layer; build_services() wires all five once per app.</text>",
                    legend(436, W, [("focal", "add your resource's queries here")])])
