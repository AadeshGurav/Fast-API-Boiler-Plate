"""Edit an .xlsx package at the XML level, leaving everything not edited byte-identical.

openpyxl rebuilds a workbook from its object model, which drops what it does not model:
charts, images, pivot tables, drawings, conditional-format extensions. This module instead
patches only the parts that must change (the edited sheets' ``<sheetData>`` and, for
structural changes, the workbook/relationship/content-type lists) and copies every other
part of the zip untouched. Untouched cells keep their original XML, so formulas, styles and
cached values survive too.

This module patches one worksheet part; ``xlsx_package`` applies it across the zip.
Pure and blocking (strings in, strings out): run it in a worker thread.
"""

from __future__ import annotations

import math
import re
from typing import Any
from xml.sax.saxutils import escape

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

# Cell coordinates are (row, column), both 1-based.
Edits = dict[tuple[int, int], Any]
Rows = list[list[Any]]

_SHEET_DATA = re.compile(r"<sheetData\s*/>|<sheetData>(.*?)</sheetData>", re.S)
_ROW = re.compile(r"<row\b([^>]*?)(?:/>|>(.*?)</row>)", re.S)
_CELL = re.compile(r"<c\b([^>]*?)(?:/>|>(.*?)</c>)", re.S)
_CELL_REF = re.compile(r'\br="([A-Z]+)(\d+)"')
_ROW_NUMBER = re.compile(r'\br="(\d+)"')
_STYLE = re.compile(r'\bs="\d+"')
_MULTI_CELL_FORMULA = re.compile(r'<f\b[^>]*\bref="')
_XML_FORBIDDEN = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


class UnsupportedWorkbookError(ValueError):
    """The package uses a layout this module does not patch (it refuses rather than guess)."""


def reject_unsafe_markup(xml: str) -> None:
    """Refuse comments, CDATA and processing instructions in a part we patch with regexes.

    Real workbooks never carry them, and they are the one place raw ``<row``/``<c`` text can
    hide from the XML parser while still sending the lazy patterns below quadratic.
    """
    body = xml.lstrip("\ufeff")
    if body.startswith("<?xml"):
        body = body[body.find("?>") + 2 :]
    if "<!--" in body or "<![CDATA[" in body or "<?" in body:
        raise UnsupportedWorkbookError("comments, CDATA and processing instructions are refused")


# ---- cells ---------------------------------------------------------------------------
def column_letters(index: int) -> str:
    """1 -> A, 27 -> AA."""
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def column_index(letters: str) -> int:
    """A -> 1, AA -> 27."""
    result = 0
    for char in letters:
        result = result * 26 + ord(char) - 64
    return result


def _cell_xml(row: int, column: int, style: str, value: Any) -> str:
    """One ``<c>`` element holding a plain value (text goes inline: no shared-string table)."""
    ref = f'r="{column_letters(column)}{row}"'
    if value is None:
        return f"<c {ref}{style}/>"
    if isinstance(value, bool):
        return f'<c {ref}{style} t="b"><v>{int(value)}</v></c>'
    if isinstance(value, int | float) and math.isfinite(value):
        return f"<c {ref}{style}><v>{value!r}</v></c>"
    text = escape(_XML_FORBIDDEN.sub("", str(value)))
    return f'<c {ref}{style} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


# ---- sheet data ----------------------------------------------------------------------
def _parse_rows(sheet_data: str) -> dict[int, tuple[str, dict[int, str], str]]:
    """``row number -> (row attributes, {column: cell xml}, row xml)``; all kept verbatim."""
    rows: dict[int, tuple[str, dict[int, str], str]] = {}
    for row_match in _ROW.finditer(sheet_data):
        attributes, body = row_match.group(1), row_match.group(2) or ""
        number = _ROW_NUMBER.search(attributes)
        if number is None:
            raise UnsupportedWorkbookError("a row without a row number")
        cells: dict[int, str] = {}
        for cell_match in _CELL.finditer(body):
            reference = _CELL_REF.search(cell_match.group(1))
            if reference is None:
                raise UnsupportedWorkbookError("a cell without a cell reference")
            cells[column_index(reference.group(1))] = cell_match.group(0)
        rows[int(number.group(1))] = (attributes, cells, row_match.group(0))
    return rows


def _replace_cell(row: int, column: int, existing: str | None, value: Any) -> str | None:
    """New XML for the cell (None = nothing to write), keeping the existing cell's style."""
    style = ""
    if existing is not None:
        if _MULTI_CELL_FORMULA.search(existing):
            raise ValueError(
                f"Cell {column_letters(column)}{row} anchors a shared or array formula; "
                "overwriting it would corrupt the cells that depend on it"
            )
        found = _STYLE.search(existing.partition(">")[0])
        style = f" {found.group(0)}" if found else ""
    if value is None and existing is None:
        return None
    return _cell_xml(row, column, style, value)


def patch_sheet_xml(xml: str, edits: Edits) -> str:
    """Apply ``edits`` to one worksheet part; everything outside the touched cells is kept."""
    reject_unsafe_markup(xml)
    match = _SHEET_DATA.search(xml)
    if match is None:
        raise UnsupportedWorkbookError("worksheet without an unprefixed <sheetData>")
    rows = _parse_rows(match.group(1) or "")
    touched: set[int] = set()
    for (row, column), value in sorted(edits.items()):
        _, cells, _ = rows.setdefault(row, (f' r="{row}"', {}, ""))
        replacement = _replace_cell(row, column, cells.get(column), value)
        if replacement is not None:
            cells[column] = replacement
            touched.add(row)

    parts: list[str] = []
    for number in sorted(rows):
        attributes, cells, original = rows[number]
        if number not in touched:
            parts.append(original)
            continue
        attributes = re.sub(r'\sspans="[^"]*"', "", attributes)  # the hint is now stale
        body = "".join(cells[c] for c in sorted(cells))
        parts.append(f"<row{attributes}>{body}</row>" if body else f"<row{attributes}/>")
    return f"{xml[: match.start()]}<sheetData>{''.join(parts)}</sheetData>{xml[match.end() :]}"


def new_sheet_xml(rows: Rows) -> str:
    """A minimal worksheet part holding ``rows``."""
    cells = {
        (r, c): value
        for r, row in enumerate(rows, 1)
        for c, value in enumerate(row, 1)
        if value is not None
    }
    empty = f'<worksheet xmlns="{MAIN_NS}"><sheetData/></worksheet>'
    body = patch_sheet_xml(empty, cells)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n{body}'


__all__ = [
    "Edits",
    "Rows",
    "UnsupportedWorkbookError",
    "new_sheet_xml",
    "patch_sheet_xml",
    "reject_unsafe_markup",
]
