"""Tiny emitter for diagram-design SVG. Write SVG with {role} / {role@0.40} placeholders;
render() resolves them per skin, so light and dark come from one spec."""
from __future__ import annotations

import math
import re
from html import escape as _esc

SANS = "'Geist', system-ui, sans-serif"
MONO = "'Geist Mono', ui-monospace, monospace"
SERIF = "'Instrument Serif', 'Noto Serif', serif"

SKINS = {
    "light": dict(paper="#f5f5f5", paper2="#ececec", ink="#2d3142", muted="#4f5d75", soft="#5a6580",
                  accent="#bf4520", link="#2e5aa8", white="#ffffff",
                  ink_rgb="45,49,66", muted_rgb="79,93,117", soft_rgb="90,101,128", accent_rgb="191,69,32",
                  link_rgb="46,90,168"),
    "dark": dict(paper="#2d3142", paper2="#393e53", ink="#f5f5f5", muted="#bfc0c0", soft="#949eb2",
                 accent="#f08a59", link="#739fdf", white="#393e53",
                 ink_rgb="245,245,245", muted_rgb="191,192,192", soft_rgb="148,158,178", accent_rgb="240,138,89",
                 link_rgb="115,159,223"),
}

TOKEN = re.compile(r"\{(paper2|paper|ink|muted|soft|accent|link|white)(?:@([0-9.]+))?\}")


def resolve(text: str, skin: str) -> str:
    s = SKINS[skin]

    def sub(m):
        role, alpha = m.group(1), m.group(2)
        if alpha is None:
            return s[role]
        return f"rgba({s[role + '_rgb']},{alpha})"

    return TOKEN.sub(sub, text)


def e(t: str) -> str:
    return _esc(t, quote=True)


def g4(v: float) -> int:
    return int(math.ceil(v / 4) * 4)


def mono_w(text: str, size: float, track: float = 0.06) -> float:
    return len(text) * size * (0.62 + track)


# ---- connectors -------------------------------------------------------------------
STYLE = {
    "muted": ('{muted}', "arrow", "1.2", None),
    "accent": ('{accent}', "arrow-accent", "1.4", None),
    "link": ('{link}', "arrow-link", "1.2", None),
    "dashed": ('{muted}', "arrow", "1", "4,3"),
    "dashed-accent": ('{accent}', "arrow-accent", "1.2", "4,3"),
    "dashed-link": ('{link}', "arrow-link", "1", "4,3"),
}
LABEL_COLOR = {"muted": "{muted}", "dashed": "{muted}", "accent": "{accent}", "dashed-accent": "{accent}",
               "link": "{link}", "dashed-link": "{link}"}


def path(d: str, style: str = "muted", arrow: bool = True) -> str:
    stroke, marker, width, dash = STYLE[style]
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    mk = f' marker-end="url(#{marker})"' if arrow else ""
    return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}"{dash_attr}{mk}/>'


def hv(x1, y1, x2, y2, r=8):
    """Horizontal then vertical, one rounded bend."""
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    return f"M {x1},{y1} H {x2 - sx * r} Q {x2},{y1} {x2},{y1 + sy * r} V {y2}"


def vh(x1, y1, x2, y2, r=8):
    """Vertical then horizontal, one rounded bend."""
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    return f"M {x1},{y1} V {y2 - sy * r} Q {x1},{y2} {x1 + sx * r},{y2} H {x2}"


def hvh(x1, y1, x2, y2, mid=None, r=8):
    """Horizontal, vertical at mid, horizontal: two rounded bends."""
    mid = (x1 + x2) // 2 if mid is None else mid
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    return (f"M {x1},{y1} H {mid - sx * r} Q {mid},{y1} {mid},{y1 + sy * r} "
            f"V {y2 - sy * r} Q {mid},{y2} {mid + sx * r},{y2} H {x2}")


def vhv(x1, y1, x2, y2, mid=None, r=8):
    """Vertical, horizontal at mid, vertical: two rounded bends."""
    mid = (y1 + y2) // 2 if mid is None else mid
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    return (f"M {x1},{y1} V {mid - sy * r} Q {x1},{mid} {x1 + sx * r},{mid} "
            f"H {x2 - sx * r} Q {x2},{mid} {x2},{mid + sy * r} V {y2}")


def label_above(cx, y_line, text, style="muted", gap=6):
    """Mask + label centered on cx, mask bottom `gap` px above a horizontal stroke."""
    w = g4(mono_w(text, 8) + 10)
    top = y_line - gap - 12
    return (f'<rect x="{cx - w / 2:g}" y="{top}" width="{w}" height="12" rx="2" fill="{{paper}}"/>'
            f'<text x="{cx}" y="{top + 9}" fill="{LABEL_COLOR[style]}" font-size="8" font-family="{MONO}" '
            f'text-anchor="middle" letter-spacing="0.06em">{e(text)}</text>')


def label_below(cx, y_line, text, style="muted", gap=6):
    w = g4(mono_w(text, 8) + 10)
    top = y_line + gap
    return (f'<rect x="{cx - w / 2:g}" y="{top}" width="{w}" height="12" rx="2" fill="{{paper}}"/>'
            f'<text x="{cx}" y="{top + 9}" fill="{LABEL_COLOR[style]}" font-size="8" font-family="{MONO}" '
            f'text-anchor="middle" letter-spacing="0.06em">{e(text)}</text>')


def label_side(x_line, cy, text, style="muted", side="right", gap=8):
    """Mask + label beside a vertical stroke."""
    w = g4(mono_w(text, 8) + 10)
    x = x_line + gap if side == "right" else x_line - gap - w
    return (f'<rect x="{x}" y="{cy - 6}" width="{w}" height="12" rx="2" fill="{{paper}}"/>'
            f'<text x="{x + w / 2:g}" y="{cy + 3}" fill="{LABEL_COLOR[style]}" font-size="8" font-family="{MONO}" '
            f'text-anchor="middle" letter-spacing="0.06em">{e(text)}</text>')


# ---- nodes --------------------------------------------------------------------------
KIND = {
    "focal": ("{accent@0.08}", "{accent}", None, "{accent@0.50}", "{accent}"),
    "backend": ("{white}", "{ink}", None, "{ink@0.40}", "{ink}"),
    "store": ("{ink@0.05}", "{muted}", None, "{muted@0.50}", "{muted}"),
    "external": ("{ink@0.03}", "{ink@0.30}", None, "{ink@0.22}", "{soft}"),
    "input": ("{muted@0.10}", "{soft}", None, "{soft@0.40}", "{soft}"),
    "optional": ("{ink@0.02}", "{ink@0.30}", "4,3", "{ink@0.22}", "{soft}"),
    "security": ("{accent@0.05}", "{accent@0.50}", "4,4", "{accent@0.40}", "{accent}"),
}


def node(x, y, w, h, name, sub=None, tag=None, kind="backend", rx=6, name_size=12):
    fill, stroke, dash, tag_stroke, tag_fill = KIND[kind]
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{{paper}}"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1"{dash_attr}/>']
    cx = x + w / 2
    if tag:
        tw = g4(mono_w(tag, 7, 0.08) + 8)
        out.append(f'<rect x="{x + 8}" y="{y + 6}" width="{tw}" height="12" rx="2" fill="transparent" stroke="{tag_stroke}" stroke-width="0.8"/>'
                   f'<text x="{x + 8 + tw / 2:g}" y="{y + 15}" fill="{tag_fill}" font-size="7" font-family="{MONO}" text-anchor="middle" letter-spacing="0.08em">{e(tag)}</text>')
    has_sub = sub is not None
    cy = y + h / 2 + (6 if tag else 0)
    ny = cy + (-2 if has_sub else 4)
    out.append(f'<text x="{cx:g}" y="{ny:g}" fill="{{ink}}" font-size="{name_size}" font-weight="600" font-family="{SANS}" text-anchor="middle">{e(name)}</text>')
    if has_sub:
        out.append(f'<text x="{cx:g}" y="{ny + 14:g}" fill="{{muted}}" font-size="9" font-family="{MONO}" text-anchor="middle">{e(sub)}</text>')
    return "".join(out)


def zone(x, y, w, h, label, dashed=False):
    dash = ' stroke-dasharray="4,4"' if dashed else ""
    stroke = "{ink@0.20}" if dashed else "{ink@0.10}"
    lw = g4(mono_w(label, 7, 0.14) + 12)
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{{ink@0.02}}" stroke="{stroke}" stroke-width="0.8"{dash}/>'
            f'<rect x="{x + 12}" y="{y - 6}" width="{lw}" height="12" rx="2" fill="{{paper}}"/>'
            f'<text x="{x + 12 + lw / 2:g}" y="{y + 3}" fill="{{soft}}" font-size="7" font-family="{MONO}" text-anchor="middle" letter-spacing="0.14em">{e(label)}</text>')


def text(x, y, t, role="sub", anchor="start", color="{muted}", size=None, weight=None, italic=False):
    fam = {"sub": MONO, "name": SANS, "serif": SERIF, "eyebrow": MONO}[role]
    size = size or {"sub": 9, "name": 12, "serif": 14, "eyebrow": 8}[role]
    extra = ' letter-spacing="0.14em"' if role == "eyebrow" else ""
    w = f' font-weight="{weight}"' if weight else (' font-weight="600"' if role == "name" else "")
    it = ' font-style="italic"' if italic else ""
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-family="{fam}" text-anchor="{anchor}"{w}{it}{extra}>{e(t)}</text>'


def legend(y, vb_w, items):
    """items: list of (kind, label) where kind in arrow styles or node kinds."""
    out = [f'<line x1="32" y1="{y - 8}" x2="{vb_w - 32}" y2="{y - 8}" stroke="{{ink@0.10}}" stroke-width="0.8"/>',
           f'<text x="32" y="{y + 10}" fill="{{muted}}" font-size="8" font-family="{MONO}" letter-spacing="0.14em">LEGEND</text>']
    x = 112
    for kind, lab in items:
        if kind in STYLE:
            stroke, marker, width, dash = STYLE[kind]
            d = f' stroke-dasharray="{dash}"' if dash else ""
            out.append(f'<line x1="{x}" y1="{y + 7}" x2="{x + 28}" y2="{y + 7}" stroke="{stroke}" stroke-width="{width}"{d} marker-end="url(#{marker})"/>')
        else:
            fill, stroke, dash, *_ = KIND[kind]
            d = f' stroke-dasharray="{dash}"' if dash else ""
            out.append(f'<rect x="{x}" y="{y}" width="28" height="14" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1"{d}/>')
        out.append(f'<text x="{x + 36}" y="{y + 10}" fill="{{muted}}" font-size="9" font-family="{MONO}">{e(lab)}</text>')
        x += 36 + g4(len(lab) * 9 * 0.62) + 28
    return "".join(out)


DEFS = """<defs>
<marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{muted}"/></marker>
<marker id="arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{accent}"/></marker>
<marker id="arrow-link" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{link}"/></marker>
<marker id="arrow-open" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polyline points="0 0, 8 3, 0 6" fill="none" stroke="{muted}" stroke-width="1.2"/></marker>
</defs>"""

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&amp;family=Geist:wght@400;500;600'
         '&amp;family=Geist+Mono:wght@400;500;600&amp;display=swap" rel="stylesheet">')


def page(slug, eyebrow, title, desc, body, vb_w, vb_h, skin, svg_attrs=""):
    s = SKINS[skin]
    sid = slug if skin == "light" else f"{slug}-dark"
    svg = (f'<svg viewBox="0 0 {vb_w} {vb_h}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-labelledby="{sid}-title {sid}-desc"{svg_attrs}>'
           f'<title id="{sid}-title">{e(title)}</title><desc id="{sid}-desc">{e(desc)}</desc>'
           f'{DEFS}<rect width="100%" height="100%" fill="{{paper}}"/>{body}</svg>')
    svg = resolve(svg, skin)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
{FONTS}
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: {SANS}; background: {s['paper']}; color: {s['ink']}; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 3rem 2rem; }}
.frame {{ max-width: {max(vb_w, 960)}px; width: 100%; }}
.diagram-container {{ width: 100%; overflow-x: auto; }}
.eyebrow {{ font-family: {MONO}; font-size: 0.66rem; font-weight: 500; letter-spacing: 0.18em; text-transform: uppercase; color: {s['muted']}; margin-bottom: 0.5rem; }}
h1 {{ font-family: {SERIF}; font-size: clamp(1.5rem, 2.4vw + 0.75rem, 2rem); font-weight: 400; letter-spacing: -0.02em; line-height: 1.15; color: {s['ink']}; margin-bottom: 1.5rem; }}
svg {{ width: 100%; min-width: {vb_w}px; display: block; }}
@media print {{ .diagram-container {{ overflow-x: visible; }} svg {{ min-width: 0; }} }}
</style>
</head>
<body>
<div class="frame">
<p class="eyebrow">{e(eyebrow)}</p>
<h1>{e(title)}</h1>
<div class="diagram-container">
{svg}
</div>
</div>
</body>
</html>
"""


def layer_stack(layers, top_word, bottom_word, x=144, w=728, top=56, h=64, arrow_up=True):
    """layers: (idx, name, sub, note, focal) from top to bottom."""
    b = []
    for i, (idx, name, sub, note, focal) in enumerate(layers):
        y = top + i * h
        fill = "{accent@0.08}" if focal else ("{paper}" if i % 2 else "{paper2}")
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>')
        if i:
            b.append(f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" stroke="{{ink@0.12}}" stroke-width="1"/>')
        color = "{accent}" if focal else "{muted}"
        b.append(f'<text x="{x + 20}" y="{y + 36}" fill="{color}" font-size="9" font-family="{MONO}" letter-spacing="0.18em">L{idx}</text>'
                 f'<text x="{x + 88}" y="{y + 30}" fill="{{ink}}" font-size="15" font-weight="600" font-family="{SANS}">{e(name)}</text>'
                 f'<text x="{x + 88}" y="{y + 46}" fill="{{muted}}" font-size="9" font-family="{MONO}">{e(sub)}</text>'
                 f'<text x="{x + w - 20}" y="{y + 36}" fill="{{soft}}" font-size="9" font-family="{MONO}" text-anchor="end">{e(note)}</text>')
    bottom = top + len(layers) * h
    b.append(f'<rect x="{x}" y="{top}" width="{w}" height="{bottom - top}" fill="none" stroke="{{muted}}" stroke-width="1"/>')
    for i, (*_, focal) in enumerate(layers):
        if focal:
            y = top + i * h
            b.append(f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{w - 1}" height="{h - 1}" fill="none" stroke="{{accent}}" stroke-width="1.2"/>')
    y1, y2 = (bottom - 8, top + 8) if arrow_up else (top + 8, bottom - 8)
    b.append(f'<path d="M 96,{y1} V {y2}" fill="none" stroke="{{muted}}" stroke-width="1.2" marker-end="url(#arrow)"/>'
             f'<text x="84" y="{top + 12}" fill="{{muted}}" font-size="8" font-family="{MONO}" text-anchor="end" letter-spacing="0.14em">{top_word}</text>'
             f'<text x="84" y="{bottom - 4}" fill="{{muted}}" font-size="8" font-family="{MONO}" text-anchor="end" letter-spacing="0.14em">{bottom_word}</text>')
    return "".join(b), bottom


def diamond(cx, cy, hw, hh, name, focal=False):
    stroke = "{accent}" if focal else "{ink}"
    fill = "{accent@0.08}" if focal else "{white}"
    pts = f"{cx},{cy - hh} {cx + hw},{cy} {cx},{cy + hh} {cx - hw},{cy}"
    return (f'<polygon points="{pts}" fill="{{paper}}"/><polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            f'<text x="{cx}" y="{cy + 4}" fill="{{ink}}" font-size="12" font-weight="600" font-family="{SANS}" text-anchor="middle">{e(name)}</text>')
