from lib import MONO, label_above, label_side, legend, node, path, zone

SLUG = "audit-trail"
EYEBROW = "Data flow · for operators, auditors and security reviewers"
TITLE = "Who changed what, and from where, without passing it around"
DESC = ("Audit trail: RBACMiddleware puts the caller's IP address, user agent and user id in a request "
        "context; when a service completes a security change (roles, grants, account status, passwords, "
        "sessions, two-factor, API tokens) it calls AuditService.record, which adds the request id and writes "
        "an append-only event to audit_events; administrators search it at GET /admin/audit-events, and "
        "events expire after audit_retention_days.")
W, H = 960, 504


def body():
    b = [
        zone(24, 40, 912, 208, "ONE REQUEST"),
        path("M 168,140 H 238", "link"),
        path("M 416,140 H 486"),
        path("M 664,140 H 734"),
        path("M 828,176 V 318"),
        path("M 384,356 H 454", "link"),
        path("M 664,356 H 734"),
        label_above(203, 140, "REQUEST", "link"),
        label_above(451, 140, "CHANGE"),
        label_above(699, 140, "RECORD"),
        label_side(828, 284, "APPEND"),
        label_above(419, 356, "SEARCH", "link"),
        label_above(699, 356, "READ"),
        node(40, 112, 128, 56, "Caller", "app · token", "IN", "input"),
        node(240, 104, 176, 72, "RBACMiddleware", "actor · IP · agent", "CTX"),
        node(488, 104, 176, 72, "A service", "RBAC · auth · tokens", "SVC"),
        node(736, 104, 184, 72, "AuditService", "+ request id", "SVC", "focal"),
        node(736, 320, 184, 72, "audit_events", "append-only · TTL", "DB", "store"),
        node(456, 320, 208, 72, "GET /admin/audit-events", "filters · paged", "API"),
        node(240, 328, 144, 56, "Administrator", "needs *", "IN", "input"),
    ]
    b.append(f'<text x="48" y="216" fill="{{soft}}" font-size="8" font-family="{MONO}" letter-spacing="0.04em">'
             'A failed audit write is logged and never fails the change; refused changes are not recorded.</text>')
    b.append(legend(456, W, [("link", "HTTP"), ("muted", "in-process"), ("focal", "the one writer"),
                             ("store", "collection")]))
    return "".join(b)
