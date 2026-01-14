"""Spreadsheet processing service for reading and manipulating spreadsheets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.core.interfaces.storage_interface import StorageInterface
    from app.services.logger import Logger
    from config import Config


class SpreadsheetProcessor(BaseService):
    """Service for processing spreadsheets (read, create, update, delete)."""

    def __init__(
        self: SpreadsheetProcessor,
        logger: Logger,
        config: Config,
        storage_backend: StorageInterface,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize SpreadsheetProcessor.

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

        from app.services.file.spreadsheet.base import BaseSpreadsheetProcessor

        self.platform_processor = BaseSpreadsheetProcessor.create_processor(
            logger, config, storage_backend
        )

        self.logger.info(
            "SpreadsheetProcessor initialized",
            extra={"service": "SpreadsheetProcessor"},
        )

    def _is_spreadsheet_type(self: SpreadsheetProcessor, content_type: str) -> bool:
        """Check if content type is a spreadsheet type.

        Args:
        ----
            content_type: MIME type string.

        Returns:
        -------
            True if spreadsheet type, False otherwise.

        """
        spreadsheet_types = [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.oasis.opendocument.spreadsheet",
            "text/csv",
        ]
        return content_type in spreadsheet_types

    async def read_spreadsheet(
        self: SpreadsheetProcessor,
        storage_path: str,
        sheet_name: str | None = None,
    ) -> dict[str, list[list[Any]]]:
        """Read spreadsheet data.

        Args:
        ----
            storage_path: Storage path to spreadsheet file.
            sheet_name: Optional specific sheet to read.

        Returns:
        -------
            Dictionary mapping sheet names to data (list of lists).

        Raises:
        ------
            RuntimeError: If reading fails.

        """
        return await self.platform_processor.read_spreadsheet(storage_path, sheet_name)

    async def create_spreadsheet(
        self: SpreadsheetProcessor,
        storage_path: str,
        data: dict[str, list[list[Any]]],
        format: str = "xlsx",
        headers: dict[str, list[str]] | None = None,
    ) -> bool:
        """Create new spreadsheet.

        Args:
        ----
            storage_path: Storage path for output file.
            data: Dictionary mapping sheet names to data (list of lists).
            format: Output format (xlsx, ods, csv).
            headers: Optional headers per sheet.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.platform_processor.create_spreadsheet(
            storage_path, data, format, headers
        )

    async def update_spreadsheet(
        self: SpreadsheetProcessor,
        storage_path: str,
        data: dict[str, list[list[Any]]],
        sheet_name: str | None = None,
    ) -> bool:
        """Update existing spreadsheet.

        Args:
        ----
            storage_path: Storage path to spreadsheet file.
            data: Dictionary mapping sheet names to data (list of lists).
            sheet_name: Optional specific sheet to update.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.platform_processor.update_spreadsheet(
            storage_path, data, sheet_name
        )

    async def delete_sheet(
        self: SpreadsheetProcessor,
        storage_path: str,
        sheet_name: str,
    ) -> bool:
        """Delete a sheet from workbook.

        Args:
        ----
            storage_path: Storage path to spreadsheet file.
            sheet_name: Name of sheet to delete.

        Returns:
        -------
            True if successful, False otherwise.

        """
        return await self.platform_processor.delete_sheet(storage_path, sheet_name)

    async def get_sheet_info(
        self: SpreadsheetProcessor,
        storage_path: str,
    ) -> dict[str, Any]:
        """Get workbook/sheet metadata.

        Args:
        ----
            storage_path: Storage path to spreadsheet file.

        Returns:
        -------
            Dictionary with workbook info (sheet names, row/column counts, etc.).

        """
        return await self.platform_processor.get_sheet_info(storage_path)


__all__ = ["SpreadsheetProcessor"]
