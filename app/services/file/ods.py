"""OpenDocument spreadsheet (ods) reading and writing with ``odfpy`` alone.

Replaces a pandas round trip that cost ~110 MB of dependencies for this one format.
ODS compresses runs of identical rows and cells into ``number-*-repeated`` attributes, so a
tiny file can describe a million cells. The reader therefore tracks positions arithmetically,
materialises only cells that hold a value, and checks the expanded size against the cap
before building the grid: a hostile file cannot allocate past ``max_cells``.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any

from odf import teletype
from odf.namespaces import TABLENS
from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableCell, TableRow
from odf.text import P

Rows = list[list[Any]]
CELL_TAGS = {(TABLENS, "table-cell"), (TABLENS, "covered-table-cell")}
NUMERIC_TYPES = {"float", "percentage", "currency"}


def _repeat(element: Any, attribute: str) -> int:
    return max(1, int(element.getAttribute(attribute) or 1))


def _value(cell: Any) -> Any:
    kind = cell.getAttribute("valuetype")
    if kind in NUMERIC_TYPES:
        number = float(cell.getAttribute("value"))
        return int(number) if number.is_integer() else number
    if kind == "boolean":
        return cell.getAttribute("booleanvalue") == "true"
    if kind == "date":
        return datetime.fromisoformat(cell.getAttribute("datevalue"))
    paragraphs = [teletype.extractText(p) for p in cell.getElementsByType(P)]
    return "\n".join(paragraphs) if paragraphs else None


def _too_big(max_cells: int) -> ValueError:
    return ValueError(f"Spreadsheet exceeds the limit of {max_cells} cells")


def _read_table(table: Any, max_cells: int) -> Rows:
    # (first row index, sparse {column: value}, how many times the row repeats)
    runs: list[tuple[int, dict[int, Any], int]] = []
    height = width = row_index = 0
    for row in table.getElementsByType(TableRow):
        row_repeat = _repeat(row, "numberrowsrepeated")
        cells: dict[int, Any] = {}
        column = 0
        for cell in row.childNodes:
            if cell.qname not in CELL_TAGS:
                continue
            col_repeat = _repeat(cell, "numbercolumnsrepeated")
            value = _value(cell)
            if value is not None:
                if column + col_repeat > max_cells:
                    raise _too_big(max_cells)
                for offset in range(col_repeat):
                    cells[column + offset] = value
            column += col_repeat
        if cells:
            runs.append((row_index, cells, row_repeat))
            height = row_index + row_repeat
            width = max(width, max(cells) + 1)
        row_index += row_repeat
        if height * width > max_cells:
            raise _too_big(max_cells)

    grid: Rows = [[None] * width for _ in range(height)]
    for start, cells, repeat in runs:
        for r in range(start, start + repeat):
            for c, value in cells.items():
                grid[r][c] = value
    return grid


def read(content: bytes, max_cells: int) -> dict[str, Rows]:
    """Every sheet as a padded grid of values; trailing empty rows and columns are dropped."""
    document = load(io.BytesIO(content))
    sheets: dict[str, Rows] = {}
    budget = max_cells
    for table in document.spreadsheet.getElementsByType(Table):
        grid = _read_table(table, budget)
        budget -= sum(len(row) for row in grid)
        sheets[table.getAttribute("name")] = grid
    return sheets


def _cell(value: Any) -> Any:
    if value is None:
        return TableCell()
    if isinstance(value, bool):  # before int: bool is an int subclass
        cell = TableCell(valuetype="boolean", booleanvalue=str(value).lower())
        text = "TRUE" if value else "FALSE"
    elif isinstance(value, int | float):
        cell = TableCell(valuetype="float", value=value)
        text = str(value)
    elif isinstance(value, date):
        cell = TableCell(valuetype="date", datevalue=value.isoformat())
        text = value.isoformat()
    else:
        cell = TableCell(valuetype="string")
        text = str(value)
    cell.addElement(P(text=text))
    return cell


def write(data: dict[str, Rows]) -> bytes:
    """Serialise sheets of values (already neutralised by the caller) to ods bytes."""
    document = OpenDocumentSpreadsheet()
    for name, rows in data.items():
        table = Table(name=name)
        for row in rows:
            table_row = TableRow()
            for value in row:
                table_row.addElement(_cell(value))
            table.addElement(table_row)
        document.spreadsheet.addElement(table)
    output = io.BytesIO()
    document.write(output)
    return output.getvalue()
