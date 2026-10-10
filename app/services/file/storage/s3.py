"""S3-compatible object storage (AWS S3, MinIO, Cloudflare R2, Ceph, ...).

Shared by every app instance, so any number of workers and hosts can serve the same files.
Uploads and downloads stream (multipart upload; ranged-free chunked reads), and the backend
can hand clients presigned URLs so file bytes bypass the API entirely.

Needs ``boto3`` (``pip install -r requirements-s3.txt``). boto3 is blocking, so every call
runs in a worker thread. Abandoned multipart uploads and the ``_uploads/`` staging prefix
are best expired with a bucket lifecycle rule as well; ``purge_older_than`` covers stores
without one.
"""

from __future__ import annotations

import asyncio
import posixpath
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.core.interfaces.storage_interface import STREAM_CHUNK_SIZE, StorageInterface

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.services.logger import Logger
    from config import Config

MISSING_CODES = {"404", "NoSuchKey", "NotFound"}
DELETE_BATCH = 1000  # S3's per-request limit for DeleteObjects


def _is_missing(error: Exception) -> bool:
    code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
    return str(code) in MISSING_CODES


class S3Storage(StorageInterface):
    """Files as objects under ``s3_key_prefix`` in ``s3_bucket``."""

    def __init__(self, config: Config, logger: Logger, client: Any | None = None) -> None:
        super().__init__(config, logger)
        self.bucket: str = config["s3_bucket"]
        self.key_prefix: str = config["s3_key_prefix"].strip("/")
        self.part_size: int = config["s3_part_size"]
        self.client = client or self._create_client(config)

    @staticmethod
    def _create_client(config: Config) -> Any:
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as e:
            raise RuntimeError(
                "file_storage_backend = 's3' needs boto3: pip install -r requirements-s3.txt"
            ) from e
        return boto3.client(
            "s3",
            region_name=config["s3_region"],
            endpoint_url=config["s3_endpoint_url"],
            aws_access_key_id=config["s3_access_key_id"],
            aws_secret_access_key=config["s3_secret_access_key"],
            config=BotoConfig(
                retries={"max_attempts": 5, "mode": "adaptive"},
                connect_timeout=5,
                read_timeout=30,
                max_pool_connections=config["s3_max_connections"],
            ),
        )

    # ---- keys -------------------------------------------------------------------------
    def _key(self, file_path: str) -> str:
        relative = posixpath.normpath(file_path.replace("\\", "/").lstrip("/"))
        if relative.startswith("..") or relative == ".":
            raise ValueError("Path traversal detected")
        return f"{self.key_prefix}/{relative}" if self.key_prefix else relative

    def _relative(self, key: str) -> str:
        return key.removeprefix(f"{self.key_prefix}/") if self.key_prefix else key

    async def _call(self, operation: str, **arguments: Any) -> Any:
        return await asyncio.to_thread(
            getattr(self.client, operation), Bucket=self.bucket, **arguments
        )

    # ---- StorageInterface ---------------------------------------------------------------
    async def exists(self, file_path: str) -> bool:
        try:
            await self._call("head_object", Key=self._key(file_path))
        except Exception as e:
            if _is_missing(e):
                return False
            raise
        return True

    async def get_size(self, file_path: str) -> int:
        try:
            head = await self._call("head_object", Key=self._key(file_path))
        except Exception as e:
            if _is_missing(e):
                return 0
            raise
        return head["ContentLength"]

    async def save(self, file_path: str, content: bytes, *, overwrite: bool = False) -> bool:
        if not overwrite and await self.exists(file_path):
            return False
        try:
            await self._call("put_object", Key=self._key(file_path), Body=content)
        except Exception as e:
            self.logger.error(f"Failed to save {file_path}: {e}", extra={"service": "S3Storage"})
            return False
        return True

    async def read(self, file_path: str) -> bytes | None:
        try:
            response = await self._call("get_object", Key=self._key(file_path))
        except Exception as e:
            if _is_missing(e):
                return None
            raise
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, file_path: str) -> bool:
        if not await self.exists(file_path):
            return False
        await self._call("delete_object", Key=self._key(file_path))
        return True

    async def get_url(self, file_path: str, *, expires_in: int | None = None) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self._key(file_path)},
            ExpiresIn=expires_in or self.config["file_download_url_ttl"],
        )

    async def list(self, prefix: str, *, recursive: bool = False) -> list[str]:
        key_prefix = self._key(prefix).rstrip("/") + "/"
        options = {"Prefix": key_prefix} | ({} if recursive else {"Delimiter": "/"})

        def collect() -> list[str]:
            paginator = self.client.get_paginator("list_objects_v2")
            return [
                self._relative(item["Key"])
                for page in paginator.paginate(Bucket=self.bucket, **options)
                for item in page.get("Contents", [])
            ]

        return await asyncio.to_thread(collect)

    # ---- streaming ----------------------------------------------------------------------
    async def save_stream(
        self, file_path: str, chunks: AsyncIterator[bytes], *, overwrite: bool = False
    ) -> bool:
        """Single PUT for small files; multipart (``s3_part_size`` parts) beyond that. A
        failing ``chunks`` aborts the multipart upload so no orphaned parts are billed."""
        if not overwrite and await self.exists(file_path):
            return False
        key, buffer = self._key(file_path), bytearray()
        upload_id: str | None = None
        parts: list[dict[str, Any]] = []

        async def send_part(data: bytes) -> None:
            nonlocal upload_id
            if upload_id is None:
                upload_id = (await self._call("create_multipart_upload", Key=key))["UploadId"]
            number = len(parts) + 1
            part = await self._call(
                "upload_part", Key=key, UploadId=upload_id, PartNumber=number, Body=data
            )
            parts.append({"ETag": part["ETag"], "PartNumber": number})

        try:
            async for chunk in chunks:
                buffer.extend(chunk)
                while len(buffer) >= self.part_size:
                    await send_part(bytes(buffer[: self.part_size]))
                    del buffer[: self.part_size]
            if upload_id is None:
                await self._call("put_object", Key=key, Body=bytes(buffer))
                return True
            if buffer:
                await send_part(bytes(buffer))
            await self._call(
                "complete_multipart_upload",
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
        except BaseException:
            if upload_id is not None:
                await asyncio.shield(
                    self._call("abort_multipart_upload", Key=key, UploadId=upload_id)
                )
            raise
        return True

    async def open_stream(
        self, file_path: str, *, chunk_size: int = STREAM_CHUNK_SIZE
    ) -> AsyncIterator[bytes] | None:
        try:
            response = await self._call("get_object", Key=self._key(file_path))
        except Exception as e:
            if _is_missing(e):
                return None
            raise
        body = response["Body"]

        async def pieces() -> AsyncIterator[bytes]:
            try:
                while piece := await asyncio.to_thread(body.read, chunk_size):
                    yield piece
            finally:
                body.close()

        return pieces()

    async def download_url(
        self, file_path: str, *, content_type: str, content_disposition: str, expires_in: int
    ) -> str | None:
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": self._key(file_path),
                "ResponseContentType": content_type,
                "ResponseContentDisposition": content_disposition,
            },
            ExpiresIn=expires_in,
        )

    async def purge_older_than(self, prefix: str, max_age_seconds: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=max_age_seconds)
        key_prefix = self._key(prefix).rstrip("/") + "/"

        def purge() -> int:
            paginator = self.client.get_paginator("list_objects_v2")
            stale = [
                {"Key": item["Key"]}
                for page in paginator.paginate(Bucket=self.bucket, Prefix=key_prefix)
                for item in page.get("Contents", [])
                if item["LastModified"] < cutoff
            ]
            for start in range(0, len(stale), DELETE_BATCH):
                self.client.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": stale[start : start + DELETE_BATCH], "Quiet": True},
                )
            return len(stale)

        return await asyncio.to_thread(purge)


__all__ = ["S3Storage"]
