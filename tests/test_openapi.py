"""The OpenAPI document is the API's contract: committed, reviewed, and stable for clients."""

import collections

from app.api.openapi import SNAPSHOT, build_schema, render


def operations(schema):
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            yield path, method, operation


def test_committed_snapshot_matches_the_application():
    current = render(build_schema())

    assert SNAPSHOT.read_text(encoding="utf-8") == current, (
        "The API contract changed. Run `make openapi`, review the diff in "
        "docs/reference/openapi.json, and commit it with the change."
    )


def test_operation_ids_are_unique_and_readable():
    ids = [op["operationId"] for _, _, op in operations(build_schema())]

    assert [i for i, n in collections.Counter(ids).items() if n > 1] == []
    assert all(i.isidentifier() for i in ids)
