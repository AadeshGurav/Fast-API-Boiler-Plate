"""The ods reader and writer: value types, repeated runs, and the cell cap against hostile files."""

import io
from datetime import datetime

import pytest
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableCell, TableRow
from odf.text import P

from app.services.file import ods


def build(rows_spec):
    """rows_spec: list of (row_repeat, [(col_repeat, value or None), ...])."""
    document = OpenDocumentSpreadsheet()
    table = Table(name="S")
    for row_repeat, cells in rows_spec:
        row = TableRow(numberrowsrepeated=row_repeat) if row_repeat > 1 else TableRow()
        for col_repeat, value in cells:
            attrs = {"numbercolumnsrepeated": col_repeat} if col_repeat > 1 else {}
            if value is None:
                row.addElement(TableCell(**attrs))
            else:
                cell = TableCell(valuetype="float", value=value, **attrs)
                cell.addElement(P(text=str(value)))
                row.addElement(cell)
        table.addElement(row)
    document.spreadsheet.addElement(table)
    out = io.BytesIO()
    document.write(out)
    return out.getvalue()


def test_round_trip_keeps_types_and_sheets():
    when = datetime(2026, 10, 10, 9, 30)
    data = {
        "A": [["text", 1, 2.5, True, False], [when, None, "multi\nline"]],
        "B": [["only"]],
    }

    sheets = ods.read(ods.write(data), max_cells=1000)

    assert sheets["A"] == [["text", 1, 2.5, True, False], [when, None, "multi\nline", None, None]]
    assert sheets["B"] == [["only"]]


def test_repeated_rows_and_columns_expand():
    content = build([(2, [(3, 7)]), (1, [(1, None), (1, 9)])])

    assert ods.read(content, max_cells=100) == {"S": [[7, 7, 7], [7, 7, 7], [None, 9, None]]}


def test_trailing_empty_runs_are_dropped_without_allocating():
    # What office suites write: one real cell, then the rest of the sheet as empty repeats.
    content = build([(1, [(1, 1), (16383, None)]), (1_048_575, [(16384, None)])])

    assert ods.read(content, max_cells=10) == {"S": [[1]]}


@pytest.mark.parametrize(
    "spec",
    [
        [(1_000_000, [(1, 1)])],  # one value, a million rows
        [(1, [(1_000_000, 1)])],  # one value, a million columns
        [(1, [(1, 1)]), (1_000_000, [(1, None)]), (1, [(1, 1)])],  # far-apart values
    ],
)
def test_expansion_past_the_cap_is_refused(spec):
    with pytest.raises(ValueError, match="limit"):
        ods.read(build(spec), max_cells=1000)


def test_cap_is_shared_across_sheets():
    data = {"A": [[1] * 6], "B": [[1] * 6]}

    with pytest.raises(ValueError, match="limit"):
        ods.read(ods.write(data), max_cells=10)
