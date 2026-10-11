"""Cursor pagination: stable pages at any depth, even while records are added."""

from __future__ import annotations

from tests.test_features import admin_client, signed_in
from tests.test_files import upload


def test_following_cursors_visits_every_file_once_newest_first(env):
    client = signed_in(env)
    created = [
        upload(client, name=f"f{i}.pdf", content=f"%PDF-1.4 {i}".encode()).json()["file_id"]
        for i in range(5)
    ]

    seen, cursor = [], None
    while True:
        page = client.get(
            "/api/v1/files/", params={"page_size": 2, **({"cursor": cursor} if cursor else {})}
        ).json()
        seen += [f["file_id"] for f in page["files"]]
        assert page["total"] == 5
        if not page["has_next"]:
            break
        cursor = page["next_cursor"]

    assert seen == list(reversed(created))


def test_a_file_added_while_paging_does_not_shift_later_pages(env):
    client = signed_in(env)
    for i in range(4):
        upload(client, name=f"f{i}.pdf", content=f"%PDF-1.4 {i}".encode())
    first = client.get("/api/v1/files/", params={"page_size": 2}).json()

    upload(client, name="new.pdf", content=b"%PDF-1.4 new")
    second = client.get(
        "/api/v1/files/", params={"page_size": 2, "cursor": first["next_cursor"]}
    ).json()

    first_ids = [f["file_id"] for f in first["files"]]
    second_ids = [f["file_id"] for f in second["files"]]
    assert len(second_ids) == 2 and not set(first_ids) & set(second_ids)


def test_page_numbers_still_work_and_point_to_the_cursor(env):
    client = signed_in(env)
    for i in range(3):
        upload(client, name=f"f{i}.pdf", content=f"%PDF-1.4 {i}".encode())

    page_two = client.get("/api/v1/files/", params={"page": 2, "page_size": 2}).json()

    assert len(page_two["files"]) == 1 and page_two["has_next"] is False
    assert page_two["next_cursor"] is None


def test_forged_cursors_are_a_client_error(env):
    client = signed_in(env)
    admin = admin_client(env)

    for url, session in (
        ("/api/v1/files/", client),
        ("/api/v1/admin/audit-events", admin),
        ("/api/v1/admin/jobs", admin),
    ):
        response = session.get(url, params={"cursor": "not-a-cursor"})
        assert response.status_code == 400, url
        assert response.json()["detail"] == "Invalid cursor"


def test_audit_events_page_by_cursor(env):
    for i in range(3):
        signed_in(env, username=f"user{i}", email=f"user{i}@example.com")
    admin = admin_client(env)

    first = admin.get("/api/v1/admin/audit-events", params={"page_size": 3}).json()
    rest = admin.get(
        "/api/v1/admin/audit-events", params={"page_size": 3, "cursor": first["next_cursor"]}
    ).json()

    ids = [e["id"] for e in first["events"] + rest["events"]]
    assert len(ids) == len(set(ids)) == first["total"] == 4
