from lib import SERIF, layer_stack, legend

SLUG = "config-layers"
EYEBROW = "Layer stack · for operators and developers"
TITLE = "Six places a setting can come from, one winner"
DESC = ("Configuration precedence from lowest to highest: defaults in app/settings.py, config.toml, "
        "config.local.toml, config.secrets.toml, the .env file and FABP_ environment variables; the merged "
        "result is validated once at startup.")
W, H = 960, 560

LAYERS = [  # top (wins) to bottom
    ("06", "Environment variables", "FABP_<NAME>=value · JSON for lists", "containers · CI", True),
    ("05", ".env file", "FABP_ lines · git-ignored", "written by make setup", False),
    ("04", "config.secrets.toml", "generated JWT key · mode 0600", "never committed", False),
    ("03", "config.local.toml", "your machine's overrides", "git-ignored", False),
    ("02", "config.toml", "project defaults · roles · groups", "committed", False),
    ("01", "app/settings.py", "every setting: type · default · description", "source of truth", False),
]


def body():
    b, bottom = layer_stack(LAYERS, "WINS", "BASE")
    b = [b, f'<text x="144" y="{bottom + 36}" fill="{{muted}}" font-size="14" font-style="italic" font-family="{SERIF}">'
         "Merged bottom-up, validated once: a typo stops startup and names the key and the file it came from.</text>",
         legend(500, W, [("focal", "what production sets")])]
    return "".join(b)
