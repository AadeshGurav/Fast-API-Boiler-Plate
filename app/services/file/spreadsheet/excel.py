"""MS Excel processor for Windows (empty stubs for future implementation)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import BaseSpreadsheetProcessor

if TYPE_CHECKING:
    from app.core.interfaces.storage_interface import StorageInterface
    from app.services.logger import Logger
    from config import Config


class ExcelProcessor(BaseSpreadsheetProcessor):
    """MS Excel processor for Windows (not implemented)."""

    def __init__(
        self: ExcelProcessor,
        logger: Logger,
        config: Config,
        storage_backend: StorageInterface,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize Excel processor.

        Args:
        ----
            logger: Logger instance.
            config: Configuration instance.
            storage_backend: Storage backend instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(logger, config, storage_backend, *args, **kwargs)

        self.logger.info(
            "ExcelProcessor initialized (stub implementation)",
            extra={"service": "ExcelProcessor"},
        )

    async def read_spreadsheet(
        self: ExcelProcessor,
        file_path: str,
        sheet_name: str | None = None,
    ) -> dict[str, list[list[Any]]]:
        """Read and parse spreadsheet data.

        Args:
        ----
            file_path: Path to spreadsheet file.
            sheet_name: Optional specific sheet to read.

        Returns:
        -------
            Dictionary mapping sheet names to data (list of lists).

        Raises:
        ------
            NotImplementedError: Windows implementation not available.

        """
        raise NotImplementedError("Excel processor not implemented for Windows")

    async def create_spreadsheet(
        self: ExcelProcessor,
        file_path: str,
        data: dict[str, list[list[Any]]],
        format: str = "xlsx",
        headers: dict[str, list[str]] | None = None,
    ) -> bool:
        """Create new spreadsheet from data.

        Args:
        ----
            file_path: Output file path.
            data: Dictionary mapping sheet names to data (list of lists).
            format: Output format (xlsx, ods, csv).
            headers: Optional headers per sheet.

        Returns:
        -------
            True if successful, False otherwise.

        Raises:
        ------
            NotImplementedError: Windows implementation not available.

        """
        raise NotImplementedError("Excel processor not implemented for Windows")

    async def update_spreadsheet(
        self: ExcelProcessor,
        file_path: str,
        data: dict[str, list[list[Any]]],
        sheet_name: str | None = None,
    ) -> bool:
        """Update existing spreadsheet.

        Args:
        ----
            file_path: Path to spreadsheet file.
            data: Dictionary mapping sheet names to data (list of lists).
            sheet_name: Optional specific sheet to update.

        Returns:
        -------
            True if successful, False otherwise.

        Raises:
        ------
            NotImplementedError: Windows implementation not available.

        """
        raise NotImplementedError("Excel processor not implemented for Windows")

    async def delete_sheet(
        self: ExcelProcessor,
        file_path: str,
        sheet_name: str,
    ) -> bool:
        """Delete a sheet from workbook.

        Args:
        ----
            file_path: Path to spreadsheet file.
            sheet_name: Name of sheet to delete.

        Returns:
        -------
            True if successful, False otherwise.

        Raises:
        ------
            NotImplementedError: Windows implementation not available.

        """
        raise NotImplementedError("Excel processor not implemented for Windows")

    async def get_sheet_info(
        self: ExcelProcessor,
        file_path: str,
    ) -> dict[str, Any]:
        """Get workbook/sheet metadata.

        Args:
        ----
            file_path: Path to spreadsheet file.

        Returns:
        -------
            Dictionary with workbook info (sheet names, row/column counts, etc.).

        Raises:
        ------
            NotImplementedError: Windows implementation not available.

        """
        raise NotImplementedError("Excel processor not implemented for Windows")


__all__ = ["ExcelProcessor"]

