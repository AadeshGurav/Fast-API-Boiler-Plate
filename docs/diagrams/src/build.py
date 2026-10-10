"""Rebuild every diagram: ``python3 docs/diagrams/src/build.py`` (writes docs/diagrams/).

Needs the diagram-design skill (https://github.com/cathrynlavery/diagram-design) for its
checks and SVG export. Set DIAGRAM_DESIGN_SKILL to its skills/diagram-design folder and,
optionally, DIAGRAM_DESIGN_REPO to a clone of the repository for the geometry check.
Pass spec prefixes (``d06 d07``) to rebuild only those.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

from lib import page

HERE = Path(__file__).parent
OUT = HERE.parent
SKILL = Path(os.environ.get("DIAGRAM_DESIGN_SKILL",
                            Path.home() / ".claude/plugins/marketplaces/diagram-design/skills/diagram-design"))
REPO = os.environ.get("DIAGRAM_DESIGN_REPO")
only = sys.argv[1:]

checks = [[str(SKILL / "scripts/self_check.py")]]
if REPO:
    checks.append([str(Path(REPO) / "scripts/verify-geometry.py")])

failed = False
for spec in sorted(HERE.glob("d[0-9][0-9]_*.py")):
    if only and not any(spec.stem.startswith(p) for p in only):
        continue
    mod = importlib.import_module(spec.stem)
    for skin in ("light", "dark"):
        name = mod.SLUG if skin == "light" else f"{mod.SLUG}-dark"
        html = OUT / f"{name}.html"
        html.write_text(page(mod.SLUG, mod.EYEBROW, mod.TITLE, mod.DESC, mod.body(), mod.W, mod.H, skin,
                             getattr(mod, "SVG_ATTRS", "")))
        for check in checks:
            result = subprocess.run(["python3", *check, str(html)], capture_output=True, text=True)
            if result.returncode:
                failed = True
                print(f"FAIL {html.name}\n{result.stdout}{result.stderr}")
        subprocess.run(["python3", str(SKILL / "scripts/export_svg.py"), "--system-fonts", str(html),
                        str(OUT / f"{name}.svg")], check=True, capture_output=True)
    print("built", mod.SLUG)
sys.exit(1 if failed else 0)
