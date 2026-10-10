from lib import SERIF, layer_stack, legend

SLUG = "what-you-get"
EYEBROW = "Layer stack · for decision makers"
TITLE = "You build the top layer; the rest ships ready"
DESC = ("What the boilerplate provides: your product sits on top of included accounts and access control, "
        "files and data, and safety nets, all running on open-source FastAPI, MongoDB, Redis and Docker.")
W, H = 960, 496

LAYERS = [
    ("5", "Your product", "your resources · business rules · screens", "you build this", True),
    ("4", "Accounts and access", "sign-up · sessions · roles · groups · Google sign-in", "included", False),
    ("3", "Files and data", "versioned files · spreadsheets · S3 · migrations", "included", False),
    ("2", "Safety nets", "rate limits · safe retries · CSRF · timeouts · errors", "included", False),
    ("1", "Platform", "FastAPI · MongoDB · Redis · Docker", "open source, no licences", False),
]


def body():
    b, bottom = layer_stack(LAYERS, "YOURS", "READY", arrow_up=True)
    return "".join([b, f'<text x="144" y="{bottom + 36}" fill="{{muted}}" font-size="14" font-style="italic" font-family="{SERIF}">'
                    "Day one starts at layer 5: the first sprint ships product, not plumbing.</text>",
                    legend(436, W, [("focal", "where your team's time goes")])])
