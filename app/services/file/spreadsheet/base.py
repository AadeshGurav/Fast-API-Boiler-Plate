"""Base spreadsheet processor with platform detection and common utilities."""

from __future__ import annotations

import platform
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.interfaces.storage_interface import StorageInterface
    from app.services.logger import Logger
    from config import Config


class BaseSpreadsheetProcessor(ABC):
    """Abstract base class for platform-specific spreadsheet processors."""

    def __init__(
        self: BaseSpreadsheetProcessor,
        logger: Logger,
        config: Config,
        storage_backend: StorageInterface,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize base spreadsheet processor.

        Args:
        ----
            logger: Logger instance.
            config: Configuration instance.
            storage_backend: Storage backend instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        self.logger = logger
        self.config = config
        self.storage_backend = storage_backend
        self.temp_dir = config.get("file_spreadsheet_temp_dir") or None
        self.timeout = config.get("file_spreadsheet_timeout", 300)

    @staticmethod
    def detect_platform() -> str:
        """Detect the current platform.

        Returns:
        -------
            Platform identifier: 'linux', 'windows', or 'unknown'.

        """
        system = platform.system().lower()
        if system == "linux":
            return "linux"
        if system == "windows":
            return "windows"
        return "unknown"

    @staticmethod
    def create_processor(
        logger: Logger,
        config: Config,
        storage_backend: StorageInterface,
    ) -> BaseSpreadsheetProcessor:
        """Factory method to create platform-specific processor.

        Args:
        ----
            logger: Logger instance.
            config: Configuration instance.
            storage_backend: Storage backend instance.

        Returns:
        -------
            Platform-specific processor instance.

        Raises:
        ------
            NotImplementedError: If platform is not supported.

        """
        platform_name = BaseSpreadsheetProcessor.detect_platform()

        if platform_name == "linux":
            from .libreoffice import LibreOfficeProcessor

            return LibreOfficeProcessor(logger, config, storage_backend)

        if platform_name == "windows":
            from .excel import ExcelProcessor

            return ExcelProcessor(logger, config, storage_backend)

        raise NotImplementedError(f"Platform {platform_name} is not supported")

    def _get_temp_directory(self: BaseSpreadsheetProcessor) -> Path:
        """Get temporary directory for file operations.

        Returns:
        -------
            Path to temporary directory.

        """
        if self.temp_dir:
            temp_path = Path(self.temp_dir)
            temp_path.mkdir(parents=True, exist_ok=True)
            return temp_path

        return Path(tempfile.gettempdir())

    def _is_spreadsheet_mime_type(
        self: BaseSpreadsheetProcessor, mime_type: str
    ) -> bool:
        """Check if MIME type is a spreadsheet type.

        Args:
        ----
            mime_type: MIME type string.

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
        return mime_type in spreadsheet_types

    @abstractmethod
    async def read_spreadsheet(
        self: BaseSpreadsheetProcessor,
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
            NotImplementedError: If not implemented by subclass.

        """
        raise NotImplementedError

    @abstractmethod
    async def create_spreadsheet(
        self: BaseSpreadsheetProcessor,
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
            NotImplementedError: If not implemented by subclass.

        """
        raise NotImplementedError

    @abstractmethod
    async def update_spreadsheet(
        self: BaseSpreadsheetProcessor,
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
            NotImplementedError: If not implemented by subclass.

        """
        raise NotImplementedError

    @abstractmethod
    async def delete_sheet(
        self: BaseSpreadsheetProcessor,
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
            NotImplementedError: If not implemented by subclass.

        """
        raise NotImplementedError

    @abstractmethod
    async def get_sheet_info(
        self: BaseSpreadsheetProcessor,
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
            NotImplementedError: If not implemented by subclass.

        """
        raise NotImplementedError


__all__ = ["BaseSpreadsheetProcessor"]
