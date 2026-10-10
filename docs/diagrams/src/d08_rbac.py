from lib import hvh, label_side, legend, node, path

SLUG = "rbac-resolution"
EYEBROW = "Architecture · for developers"
TITLE = "How a request earns its permission"
DESC = ("RBAC resolution: role definitions from config.toml, the user's roles and groups, and active "
        "temporary grants are merged into one permission set, cached per user, and checked against the "
        "resource:action the middleware derives from the request method and path.")
W, H = 960, 432


def body():
    b = [
        path(hvh(208, 104, 272, 192, mid=240)),
        path("M 208,208 H 272"),
        path(hvh(208, 312, 272, 224, mid=240)),
        path("M 448,208 H 512"),
        path("M 688,208 H 752"),
        path("M 840,240 V 280", "accent"),
        path("M 840,104 V 176", "link"),
        label_side(840, 140, "REQUIRES", "link"),
        node(32, 72, 176, 64, "Role definitions", "config.toml · inherits", "CONFIG", "external"),
        node(32, 176, 176, 64, "User record", "roles · groups", "DB", "store"),
        node(32, 280, 176, 64, "Temporary grants", "start · end · revoked", "DB", "store"),
        node(272, 176, 176, 64, "Resolve permissions", "union · cycles cut", "RBAC"),
        node(512, 176, 176, 64, "Cached set", "TTL 300 s · dropped on change", "KV", "store"),
        node(752, 176, 176, 64, "Check permission", "* · files:* · files:delete", "CHECK", "focal"),
        node(752, 40, 176, 64, "DELETE /api/v1/files/7", "method + first segment", "HTTP", "input"),
    ]
    b.append(node(752, 280, 176, 64, "Allowed → route runs", "otherwise 403 problem", "RESULT", "optional"))
    b.append(legend(392, W, [("muted", "feeds"), ("accent", "decision path"), ("link", "from the request"),
                             ("focal", "the check"), ("store", "stored state")]))
    return "".join(b)
