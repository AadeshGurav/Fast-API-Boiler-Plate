from lib import diamond, label_above, label_side, legend, node, path

SLUG = "file-upload"
EYEBROW = "Flowchart · for developers"
TITLE = "An upload, from first byte to new version"
DESC = ("File upload flow: the type and name are validated, bytes stream to storage while being counted and "
        "hashed, size and quota are enforced, identical bytes return the caller's existing file, otherwise "
        "thumbnails and sheet info are derived and a new version is recorded; rejections answer 400.")
W, H = 960, 808


def body():
    b = [
        path("M 360,64 V 88"),
        path("M 360,160 V 192"),
        path("M 456,124 H 640", "dashed"),
        path("M 360,248 V 280"),
        path("M 456,316 H 732 Q 740,316 740,308 V 152", "dashed"),
        path("M 360,352 V 400"),
        path("M 360,472 V 504"),
        path("M 264,436 H 168 Q 160,436 160,444 V 696 Q 160,704 168,704 H 260"),
        path("M 360,560 V 592"),
        path("M 360,648 V 680", "accent"),
        label_side(360, 176, "YES"),
        label_above(548, 124, "NO", "dashed"),
        label_side(360, 376, "YES"),
        label_above(600, 316, "NO", "dashed"),
        label_side(360, 488, "NO"),
        label_side(160, 570, "YES · EXISTING", side="left"),
        node(260, 24, 200, 40, "Upload", "multipart or chunks", kind="input", rx=20),
        diamond(360, 124, 96, 36, "Type & name OK?"),
        node(240, 192, 240, 56, "Stream to storage", "count · SHA-256 · size cap", "STEP"),
        diamond(360, 316, 96, 36, "Size & quota OK?"),
        diamond(360, 436, 96, 36, "Duplicate of yours?"),
        node(240, 504, 240, 56, "Derive extras", "thumbnails · sheet info", "STEP"),
        node(240, 592, 240, 56, "Record version", "v+1 · is_latest · quota", "STEP"),
        node(260, 680, 200, 48, "201 · file response", "download + thumbnail URLs", kind="focal", rx=20),
        node(640, 96, 200, 56, "400 problem", "stored bytes removed", kind="external", rx=20),
    ]
    b.append(legend(768, W, [("muted", "flow"), ("dashed", "rejected"), ("accent", "accepted"),
                             ("focal", "success"), ("external", "early answer")]))
    return "".join(b)
