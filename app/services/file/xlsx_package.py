"""Edit an .xlsx zip package: patch sheets, add or delete sheets, copy the rest untouched.

Every part of the zip that is not edited is written back byte-for-byte, which is what keeps
charts, images, drawings and pivot tables alive. Sheet content is patched by ``xlsx_patch``.
Pure and blocking (bytes in, bytes out): run it in a worker thread.
"""

from __future__ import annotations

import io
import posixpath
import re
import zipfile
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from app.services.file.xlsx_patch import (
    MAIN_NS,
    Edits,
    Rows,
    UnsupportedWorkbookError,
    new_sheet_xml,
    patch_sheet_xml,
    reject_unsafe_markup,
)

REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WORKSHEET_REL_TYPE = f"{REL_NS}/worksheet"
WORKSHEET_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"

WORKBOOK = "xl/workbook.xml"
WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
CONTENT_TYPES = "[Content_Types].xml"
CALC_CHAIN = "xl/calcChain.xml"


def _parse_xml(data: bytes) -> ElementTree.Element:
    """Parse a package part. Real workbooks never carry a DTD, and stdlib ElementTree
    expands entities, so a document type declaration is refused outright."""
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError("Not a valid .xlsx file: unexpected DTD")
    return ElementTree.fromstring(data)  # noqa: S314 - DTDs rejected above


class _Package:
    """The zip's parts in memory, in their original order."""

    def __init__(self, content: bytes, max_unpacked_bytes: int) -> None:
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as e:
            raise ValueError("Not a valid .xlsx file") from e
        with archive:
            if sum(info.file_size for info in archive.infolist()) > max_unpacked_bytes:
                raise ValueError("Workbook expands to more than the allowed size")
            self.parts: dict[str, bytes] = {n: archive.read(n) for n in archive.namelist()}
        for required in (WORKBOOK, WORKBOOK_RELS, CONTENT_TYPES):
            if required not in self.parts:
                raise ValueError(f"Not a valid .xlsx file: missing {required}")

    def text(self, name: str) -> str:
        text = self.parts[name].decode("utf-8")
        reject_unsafe_markup(text)
        return text

    def put(self, name: str, text: str) -> None:
        self.parts[name] = text.encode("utf-8")

    def serialize(self) -> bytes:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in self.parts.items():
                archive.writestr(name, data)
        return output.getvalue()


def _sheet_parts(package: _Package) -> list[tuple[str, str, str]]:
    """``[(sheet name, relationship id, part path)]`` in workbook order."""
    relationships = {
        rel.get("Id"): rel.get("Target", "") for rel in _parse_xml(package.parts[WORKBOOK_RELS])
    }
    sheets = _parse_xml(package.parts[WORKBOOK]).find(f"{{{MAIN_NS}}}sheets")
    found = []
    for sheet in sheets if sheets is not None else []:
        rel_id = sheet.get(f"{{{REL_NS}}}id", "")
        target = relationships.get(rel_id, "")
        path = target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target)
        found.append((sheet.get("name", ""), rel_id, posixpath.normpath(path)))
    return found


def _insert_before(text: str, closing_tag: str, addition: str) -> str:
    if closing_tag not in text:
        raise UnsupportedWorkbookError(f"no {closing_tag} to extend")
    return text.replace(closing_tag, addition + closing_tag, 1)


def _drop_calculation_state(package: _Package) -> None:
    """Edits invalidate cached results and the calc chain; make Excel rebuild both."""
    if CALC_CHAIN in package.parts:
        del package.parts[CALC_CHAIN]
        package.put(
            CONTENT_TYPES,
            re.sub(r'<Override\b[^>]*"/xl/calcChain\.xml"[^>]*/>', "", package.text(CONTENT_TYPES)),
        )
        package.put(
            WORKBOOK_RELS,
            re.sub(r"<Relationship\b[^>]*calcChain[^>]*/>", "", package.text(WORKBOOK_RELS)),
        )

    workbook = package.text(WORKBOOK)
    if "<calcPr" in workbook:
        workbook = re.sub(r'(<calcPr\b[^>]*?)\sfullCalcOnLoad="[^"]*"', r"\1", workbook)
        workbook = workbook.replace("<calcPr", '<calcPr fullCalcOnLoad="1"', 1)
    else:  # schema order: ... sheets, functionGroups, externalReferences, definedNames, calcPr
        for anchor in (
            "</definedNames>",
            "</externalReferences>",
            "</functionGroups>",
            "</sheets>",
        ):
            if anchor in workbook:
                workbook = workbook.replace(anchor, f'{anchor}<calcPr fullCalcOnLoad="1"/>', 1)
                break
    package.put(WORKBOOK, workbook)


def _add_sheet(package: _Package, name: str, rows: Rows) -> None:
    workbook, rels = package.text(WORKBOOK), package.text(WORKBOOK_RELS)
    sheets = _parse_xml(package.parts[WORKBOOK]).find(f"{{{MAIN_NS}}}sheets")
    sheet_id = 1 + max((int(s.get("sheetId", 0)) for s in sheets), default=0)
    used_ids = {int(n) for n in re.findall(r'\bId="rId(\d+)"', rels)}
    rel_id = f"rId{1 + max(used_ids, default=0)}"
    number = next(
        n for n in range(1, 100_000) if f"xl/worksheets/sheet{n}.xml" not in package.parts
    )
    part = f"xl/worksheets/sheet{number}.xml"

    package.put(part, new_sheet_xml(rows))
    package.put(
        WORKBOOK,
        _insert_before(
            workbook,
            "</sheets>",
            f'<sheet name="{escape(name, {chr(34): "&quot;"})}" sheetId="{sheet_id}" '
            f'xmlns:r="{REL_NS}" r:id="{rel_id}"/>',
        ),
    )
    package.put(
        WORKBOOK_RELS,
        _insert_before(
            rels,
            "</Relationships>",
            f'<Relationship Id="{rel_id}" Type="{WORKSHEET_REL_TYPE}" '
            f'Target="worksheets/sheet{number}.xml"/>',
        ),
    )
    package.put(
        CONTENT_TYPES,
        _insert_before(
            package.text(CONTENT_TYPES),
            "</Types>",
            f'<Override PartName="/{part}" ContentType="{WORKSHEET_CONTENT_TYPE}"/>',
        ),
    )


def _delete_sheet(package: _Package, name: str) -> None:
    sheets = _sheet_parts(package)
    position = next(i for i, (n, _, _) in enumerate(sheets) if n == name)
    _, rel_id, part = sheets[position]
    rel_id_pattern = re.escape(rel_id)

    workbook = re.sub(
        rf'<sheet\b(?=[^>]*:id="{rel_id_pattern}")[^>]*/>', "", package.text(WORKBOOK), count=1
    )

    def renumber(match: re.Match[str]) -> str:
        scope = re.search(r'\blocalSheetId="(\d+)"', match.group(0))
        if scope is None or int(scope.group(1)) < position:
            return match.group(0)
        if int(scope.group(1)) == position:
            return ""  # a name scoped to the deleted sheet
        return match.group(0).replace(
            scope.group(0), f'localSheetId="{int(scope.group(1)) - 1}"', 1
        )

    workbook = re.sub(r"<definedName\b[^>]*>.*?</definedName>", renumber, workbook, flags=re.S)
    workbook = re.sub(r'\s(?:activeTab|firstSheet)="\d+"', "", workbook)
    package.put(WORKBOOK, workbook)

    package.put(
        WORKBOOK_RELS,
        re.sub(
            rf'<Relationship\b(?=[^>]*\bId="{rel_id_pattern}")[^>]*/>',
            "",
            package.text(WORKBOOK_RELS),
        ),
    )
    package.put(
        CONTENT_TYPES,
        re.sub(rf'<Override\b[^>]*"/{re.escape(part)}"[^>]*/>', "", package.text(CONTENT_TYPES)),
    )
    package.parts.pop(part, None)
    package.parts.pop(
        posixpath.join(posixpath.dirname(part), "_rels", f"{posixpath.basename(part)}.rels"), None
    )


def edit_xlsx(
    content: bytes,
    *,
    edits: dict[str, Edits] | None = None,
    new_sheets: dict[str, Rows] | None = None,
    delete: str | None = None,
    max_unpacked_bytes: int = 512 * 1024 * 1024,
) -> bytes:
    """Return ``content`` with cell ``edits`` applied, ``new_sheets`` added, ``delete`` removed.

    Raises:
    ------
        ValueError: The file is not a workbook, a named sheet is missing, or an edit would
            corrupt it (``UnsupportedWorkbookError`` for layouts this module will not patch).

    """
    package = _Package(content, max_unpacked_bytes)
    paths = {name: part for name, _, part in _sheet_parts(package)}
    for name, sheet_edits in (edits or {}).items():
        if name not in paths:
            raise ValueError(f"Sheet '{name}' not found")
        package.put(paths[name], patch_sheet_xml(package.text(paths[name]), sheet_edits))
    for name, rows in (new_sheets or {}).items():
        _add_sheet(package, name, rows)
    if delete is not None:
        if delete not in paths:
            raise ValueError(f"Sheet '{delete}' not found")
        _delete_sheet(package, delete)
    _drop_calculation_state(package)
    return package.serialize()


__all__ = ["UnsupportedWorkbookError", "edit_xlsx"]
