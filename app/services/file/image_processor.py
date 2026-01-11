"""Image processing service for thumbnails and resizing."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from PIL import Image

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.core.interfaces.storage_interface import StorageInterface
    from app.services.logger import Logger
    from config import Config


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

        self.logger.info(
            "ImageProcessor initialized", extra={"service": "ImageProcessor"}
        )

    def _generate_thumbnail_path(
        self: ImageProcessor, original_path: str, size: int
    ) -> str:
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

    async def process_image(
        self: ImageProcessor,
        storage_path: str,
        image_content: bytes,
        thumbnail_sizes: list[int],
    ) -> dict[str, str]:
        """Process image and generate thumbnails.

        Args:
        ----
            storage_path: Original file storage path.
            image_content: Original image content as bytes.
            thumbnail_sizes: List of thumbnail sizes to generate.

        Returns:
        -------
            Dictionary mapping size to thumbnail storage path.

        """
        thumbnail_paths = {}

        try:
            image = Image.open(io.BytesIO(image_content))
            image_format = image.format or "JPEG"

            for size in thumbnail_sizes:
                try:
                    thumbnail = self._create_thumbnail(image, size)
                    thumb_path = self._generate_thumbnail_path(storage_path, size)

                    thumb_bytes = await self._image_to_bytes(thumbnail, image_format)
                    await self.storage_backend.save(thumb_path, thumb_bytes, overwrite=True)

                    thumbnail_paths[str(size)] = thumb_path

                    self.logger.debug(
                        f"Generated thumbnail {size}px for {storage_path}",
                        extra={"service": "ImageProcessor"},
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Failed to generate thumbnail {size}px: {e}",
                        extra={"service": "ImageProcessor"},
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to process image {storage_path}: {e}",
                extra={"service": "ImageProcessor"},
            )

        return thumbnail_paths

    def _create_thumbnail(
        self: ImageProcessor, image: Image.Image, size: int
    ) -> Image.Image:
        """Create thumbnail from image.

        Args:
        ----
            image: PIL Image object.
            size: Target size (width/height).

        Returns:
        -------
            Thumbnail Image object.

        """
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        return image.copy()

    async def _image_to_bytes(
        self: ImageProcessor, image: Image.Image, format: str
    ) -> bytes:
        """Convert PIL Image to bytes.

        Args:
        ----
            image: PIL Image object.
            format: Image format (JPEG, PNG, etc.).

        Returns:
        -------
            Image content as bytes.

        """
        buffer = io.BytesIO()

        if format == "JPEG":
            if image.mode in ("RGBA", "LA", "P"):
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                image = rgb_image
            image.save(buffer, format="JPEG", quality=85, optimize=True)
        else:
            image.save(buffer, format=format, optimize=True)

        return buffer.getvalue()

    async def resize_image(
        self: ImageProcessor,
        storage_path: str,
        image_content: bytes,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> bytes | None:
        """Resize image to specified dimensions.

        Args:
        ----
            storage_path: Original file storage path.
            image_content: Original image content as bytes.
            max_width: Maximum width (maintains aspect ratio).
            max_height: Maximum height (maintains aspect ratio).

        Returns:
        -------
            Resized image content as bytes, or None if failed.

        """
        try:
            image = Image.open(io.BytesIO(image_content))
            image_format = image.format or "JPEG"

            if max_width or max_height:
                original_width, original_height = image.size
                new_width = max_width or original_width
                new_height = max_height or original_height

                if max_width and max_height:
                    ratio = min(new_width / original_width, new_height / original_height)
                    new_width = int(original_width * ratio)
                    new_height = int(original_height * ratio)
                elif max_width:
                    ratio = new_width / original_width
                    new_height = int(original_height * ratio)
                else:
                    ratio = new_height / original_height
                    new_width = int(original_width * ratio)

                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            return await self._image_to_bytes(image, image_format)

        except Exception as e:
            self.logger.error(
                f"Failed to resize image {storage_path}: {e}",
                extra={"service": "ImageProcessor"},
            )
            return None


__all__ = ["ImageProcessor"]

