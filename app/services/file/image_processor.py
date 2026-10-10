"""Image processing service for thumbnails and resizing."""

from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageOps

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.core.interfaces.storage_interface import StorageInterface
    from app.services.logger import Logger
    from config import Config

# Refuse images that decode to more than ~50 megapixels (decompression bombs): a tiny
# upload can otherwise expand to gigabytes of RAM. Pillow itself only *warns* up to twice
# this value, so ``_render_thumbnails`` checks the declared size before decoding.
MAX_IMAGE_PIXELS = 50_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class ImageProcessor(BaseService):
    """Service for processing images (thumbnails, resizing)."""

    def __init__(
        self: ImageProcessor,
        logger: Logger,
        config: Config,
        storage_backend: StorageInterface,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize ImageProcessor.

        Args:
        ----
            logger: Logger instance.
            config: Configuration instance.
            storage_backend: Storage backend instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(config, logger, *args, **kwargs)
        self.storage_backend = storage_backend

        self.logger.info("ImageProcessor initialized", extra={"service": "ImageProcessor"})

    def _generate_thumbnail_path(self: ImageProcessor, original_path: str, size: int) -> str:
        """Generate thumbnail storage path.

        Args:
        ----
            original_path: Original file path.
            size: Thumbnail size (width/height).

        Returns:
        -------
            Thumbnail storage path.

        """
        path_parts = original_path.rsplit(".", 1)
        if len(path_parts) == 2:
            base, ext = path_parts
            return f"{base}_thumb_{size}.{ext}"
        return f"{original_path}_thumb_{size}"

    @staticmethod
    def _render_thumbnails(image_content: bytes, thumbnail_sizes: list[int]) -> dict[int, bytes]:
        """Decode once, then render every size from a *fresh copy* of the original.

        (``Image.thumbnail`` shrinks in place, so reusing one image made every
        thumbnail after the smallest come out at the smallest size.) CPU-bound: call
        from a worker thread.
        """
        with Image.open(io.BytesIO(image_content)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:  # header only, nothing decoded yet
                raise Image.DecompressionBombError(
                    f"image has {image.width * image.height} pixels (limit {MAX_IMAGE_PIXELS})"
                )
            image_format = image.format or "JPEG"
            oriented = ImageOps.exif_transpose(image)  # honour camera rotation
            rendered: dict[int, bytes] = {}
            for size in thumbnail_sizes:
                thumb = oriented.copy()
                thumb.thumbnail((size, size), Image.Resampling.LANCZOS)
                rendered[size] = ImageProcessor._encode(thumb, image_format)
            return rendered

    async def process_image(
        self: ImageProcessor,
        storage_path: str,
        image_content: bytes,
        thumbnail_sizes: list[int],
    ) -> dict[str, str]:
        """Generate and store thumbnails; returns {size: storage path}.

        Failure to process an image (corrupt data, decompression bomb) is logged and
        yields no thumbnails; the upload itself still succeeds.
        """
        try:
            rendered = await asyncio.to_thread(
                self._render_thumbnails, image_content, thumbnail_sizes
            )
        except (OSError, ValueError, Image.DecompressionBombError) as e:
            self.logger.warning(
                f"Could not process image {storage_path}: {e}",
                extra={"service": "ImageProcessor"},
            )
            return {}

        thumbnail_paths: dict[str, str] = {}
        for size, thumb_bytes in rendered.items():
            thumb_path = self._generate_thumbnail_path(storage_path, size)
            if await self.storage_backend.save(thumb_path, thumb_bytes, overwrite=True):
                thumbnail_paths[str(size)] = thumb_path
        return thumbnail_paths

    @staticmethod
    def _encode(image: Image.Image, format: str) -> bytes:
        """Encode ``image``; JPEG cannot hold transparency, so flatten onto white."""
        buffer = io.BytesIO()
        if format == "JPEG":
            if image.mode in ("RGBA", "LA", "P"):
                rgba = image.convert("RGBA")
                flat = Image.new("RGB", rgba.size, (255, 255, 255))
                flat.paste(rgba, mask=rgba.split()[-1])
                image = flat
            elif image.mode != "RGB":
                image = image.convert("RGB")
            image.save(buffer, format="JPEG", quality=85, optimize=True)
        else:
            image.save(buffer, format=format, optimize=True)
        return buffer.getvalue()


__all__ = ["ImageProcessor"]
