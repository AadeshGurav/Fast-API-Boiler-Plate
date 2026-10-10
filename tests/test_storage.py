"""Local storage must never leave its base directory."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.file.storage.local import LocalStorage
from tests.conftest import run


@pytest.fixture
def storage(tmp_path):
    (tmp_path / "uploads").mkdir()
    (tmp_path / "uploads_evil").mkdir()  # shares a string prefix with the base
    return LocalStorage({}, MagicMock(), base_path=str(tmp_path / "uploads"))


@pytest.mark.parametrize("hostile", ["../uploads_evil/x", "a/../../x", "..\\x", "a/b/../../../x"])
def test_traversal_is_refused(storage, hostile):
    with pytest.raises(ValueError, match="traversal"):
        storage._get_full_path(hostile)


def test_absolute_paths_are_confined_to_the_base(storage):
    assert storage._get_full_path("/etc/passwd").is_relative_to(storage.base_path.resolve())


def test_symlink_escape_is_refused(storage, tmp_path):
    (storage.base_path / "link").symlink_to(tmp_path / "uploads_evil")
    with pytest.raises(ValueError, match="traversal"):
        storage._get_full_path("link/secret.txt")


def test_save_read_delete_round_trip(storage):
    assert run(storage.save("u/f/1/a.txt", b"hi"))
    assert run(storage.read("u/f/1/a.txt")) == b"hi"
    assert not run(storage.save("u/f/1/a.txt", b"again"))  # no silent overwrite
    assert run(storage.delete("u/f/1/a.txt"))
    assert run(storage.read("u/f/1/a.txt")) is None


# ---- streaming ----------------------------------------------------------------------


async def chunked(*pieces: bytes):
    for piece in pieces:
        yield piece


async def failing_after(piece: bytes):
    yield piece
    raise ValueError("client went away")


async def collect(stream) -> bytes:
    return b"".join([piece async for piece in stream])


def test_save_stream_writes_atomically_and_reads_back_in_pieces(storage):
    assert run(storage.save_stream("u/f/1/a.bin", chunked(b"abc", b"def", b"g")))
    assert run(storage.read("u/f/1/a.bin")) == b"abcdefg"
    pieces = [p for p in run(_pieces(storage, "u/f/1/a.bin", 3))]
    assert pieces == [b"abc", b"def", b"g"]
    assert not run(storage.save_stream("u/f/1/a.bin", chunked(b"x")))  # no silent overwrite


async def _pieces(storage, path, size):
    return [p async for p in await storage.open_stream(path, chunk_size=size)]


def test_a_failing_stream_leaves_nothing_behind(storage):
    with pytest.raises(ValueError, match="went away"):
        run(storage.save_stream("u/f/1/a.bin", failing_after(b"partial")))
    assert run(storage.exists("u/f/1/a.bin")) is False
    assert run(storage.list("u/f/1", recursive=True)) == []  # no .partial file either


def test_open_stream_of_a_missing_file_is_none(storage):
    assert run(storage.open_stream("nope")) is None


def test_purge_removes_only_stale_files_and_empty_folders(storage):
    import os
    import time

    run(storage.save("_uploads/u/old/000001", b"x"))
    run(storage.save("_uploads/u/new/000001", b"y"))
    stale = storage._get_full_path("_uploads/u/old/000001")
    os.utime(stale, (time.time() - 7200, time.time() - 7200))

    assert run(storage.purge_older_than("_uploads", 3600)) == 1
    assert run(storage.exists("_uploads/u/new/000001"))
    assert not storage._get_full_path("_uploads/u/old").exists()  # emptied folder pruned


# ---- S3 (boto3 against moto's in-process fake) -------------------------------------


@pytest.fixture
def s3(monkeypatch):
    pytest.importorskip("moto")
    import boto3
    from moto import mock_aws

    from app.services.file.storage.s3 import S3Storage

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="files")
        config = {
            "s3_bucket": "files",
            "s3_key_prefix": "fabp",
            "s3_part_size": 5 * 1024 * 1024,
            "file_download_url_ttl": 60,
        }
        yield S3Storage(config, MagicMock(), client=client), client


def test_s3_round_trip_honours_the_key_prefix(s3):
    storage, client = s3
    assert run(storage.save("u/f/1/a.txt", b"hi"))
    assert not run(storage.save("u/f/1/a.txt", b"again"))
    assert run(storage.read("u/f/1/a.txt")) == b"hi"
    assert run(storage.get_size("u/f/1/a.txt")) == 2
    assert client.get_object(Bucket="files", Key="fabp/u/f/1/a.txt")["Body"].read() == b"hi"
    assert run(storage.list("u/f", recursive=True)) == ["u/f/1/a.txt"]
    assert run(storage.delete("u/f/1/a.txt")) and not run(storage.delete("u/f/1/a.txt"))
    assert run(storage.read("u/f/1/a.txt")) is None


def test_s3_traversal_is_refused(s3):
    storage, _ = s3
    with pytest.raises(ValueError, match="traversal"):
        run(storage.exists("../other-tenant/x"))


def test_s3_large_stream_goes_up_as_multipart_and_reads_back_identical(s3):
    storage, client = s3
    part = 5 * 1024 * 1024
    payload = bytes(range(256)) * (part // 256) * 2 + b"tail"  # 10 MiB + 4 -> 3 parts

    assert run(storage.save_stream("big.bin", chunked(payload[:3_000_000], payload[3_000_000:])))
    assert run(storage.get_size("big.bin")) == len(payload)
    assert run(collect_from(storage, "big.bin")) == payload
    assert client.list_multipart_uploads(Bucket="files").get("Uploads", []) == []


async def collect_from(storage, path) -> bytes:
    return await collect(await storage.open_stream(path, chunk_size=1_000_000))


def test_s3_failed_multipart_upload_is_aborted(s3):
    storage, client = s3

    async def big_then_fail():
        yield b"x" * (6 * 1024 * 1024)  # enough to start a multipart upload
        raise ValueError("client went away")

    with pytest.raises(ValueError, match="went away"):
        run(storage.save_stream("big.bin", big_then_fail()))
    assert client.list_multipart_uploads(Bucket="files").get("Uploads", []) == []
    assert run(storage.exists("big.bin")) is False


def test_s3_small_stream_is_a_single_put_and_missing_streams_are_none(s3):
    storage, _ = s3
    assert run(storage.save_stream("small.txt", chunked(b"a", b"b")))
    assert run(storage.read("small.txt")) == b"ab"
    assert run(storage.open_stream("missing")) is None


def test_s3_download_url_is_presigned_with_response_headers(s3):
    storage, _ = s3
    url = run(
        storage.download_url(
            "u/a.txt",
            content_type="text/plain",
            content_disposition='attachment; filename="a.txt"',
            expires_in=60,
        )
    )
    assert "fabp/u/a.txt" in url and "response-content-disposition" in url and "Signature" in url


def test_s3_purge_deletes_stale_objects_under_the_prefix(s3):
    storage, _ = s3
    run(storage.save("_uploads/u/1", b"x"))
    run(storage.save("keep/1", b"y"))
    assert run(storage.purge_older_than("_uploads", 0)) == 1
    assert run(storage.exists("keep/1")) and not run(storage.exists("_uploads/u/1"))
