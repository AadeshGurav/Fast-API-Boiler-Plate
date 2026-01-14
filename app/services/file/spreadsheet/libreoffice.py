"""LibreOffice headless implementation for Linux spreadsheet processing."""

from __future__ import annotations

import asyncio
import csv
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import BaseSpreadsheetProcessor

if TYPE_CHECKING:
    from app.core.interfaces.storage_interface import StorageInterface
    from app.services.logger import Logger
    from config import Config


class LibreOfficeProcessor(BaseSpreadsheetProcessor):
    """LibreOffice headless processor for Linux."""

    def __init__(
        self: LibreOfficeProcessor,
        logger: Logger,
        config: Config,
        storage_backend: StorageInterface,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize LibreOffice processor.

        Args:
        ----
            logger: Logger instance.
            config: Configuration instance.
            storage_backend: Storage backend instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        super().__init__(logger, config, storage_backend, *args, **kwargs)
        self.libreoffice_path = config.get("file_libreoffice_path", "libreoffice")
        self._available = None

        self.logger.info(
            "LibreOfficeProcessor initialized",
            extra={"service": "LibreOfficeProcessor"},
        )

    async def _check_availability(self: LibreOfficeProcessor) -> bool:
        """Check if LibreOffice is available.

        Returns:
        -------
            True if LibreOffice is available, False otherwise.

        """
        if self._available is not None:
            return self._available

        try:
            process = await asyncio.create_subprocess_exec(
                self.libreoffice_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

            if process.returncode == 0:
                self._available = True
                self.logger.info(
                    f"LibreOffice available: {stdout.decode().strip()}",
                    extra={"service": "LibreOfficeProcessor"},
                )
                return True

            self._available = False
            self.logger.warning(
                f"LibreOffice not available: {stderr.decode().strip()}",
                extra={"service": "LibreOfficeProcessor"},
            )
            return False

        except (FileNotFoundError, asyncio.TimeoutError, Exception) as e:
            self._available = False
            self.logger.error(
                f"LibreOffice availability check failed: {e}",
                extra={"service": "LibreOfficeProcessor"},
            )
            return False

    async def _run_libreoffice_command(
        self: LibreOfficeProcessor,
        command: list[str],
        timeout: float | None = None,
    ) -> tuple[int, bytes, bytes]:
        """Run LibreOffice command via subprocess.

        Args:
        ----
            command: Command and arguments list.
            timeout: Optional timeout in seconds.

        Returns:
        -------
            Tuple of (returncode, stdout, stderr).

        Raises:
        ------
            RuntimeError: If LibreOffice is not available.

        """
        if not await self._check_availability():
            raise RuntimeError("LibreOffice is not available on this system")

        timeout = timeout or self.timeout

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return process.returncode, stdout, stderr

        except asyncio.TimeoutError as e:
            self.logger.error(
                f"LibreOffice command timed out after {timeout}s: {command}",
                extra={"service": "LibreOfficeProcessor"},
            )
            raise RuntimeError(f"LibreOffice command timed out: {e}") from e

        except Exception as e:
            self.logger.error(
                f"LibreOffice command failed: {e}",
                extra={"service": "LibreOfficeProcessor"},
            )
            raise RuntimeError(f"LibreOffice command failed: {e}") from e

    async def read_spreadsheet(
        self: LibreOfficeProcessor,
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
            RuntimeError: If reading fails.

        """
        content = await self.storage_backend.read(file_path)
        if not content:
            raise RuntimeError(f"File not found: {file_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / f"input_{uuid.uuid4().hex}.xlsx"

            input_file.write_bytes(content)

            output_dir = temp_path / "output"
            output_dir.mkdir()

            command = [
                self.libreoffice_path,
                "--headless",
                "--convert-to",
                "csv",
                "--outdir",
                str(output_dir),
                str(input_file),
            ]

            returncode, stdout, stderr = await self._run_libreoffice_command(command)

            if returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"LibreOffice conversion failed: {error_msg}")

            result: dict[str, list[list[Any]]] = {}

            csv_files = list(output_dir.glob("*.csv"))
            if not csv_files:
                self.logger.warning(
                    f"No CSV files generated from {file_path}",
                    extra={"service": "LibreOfficeProcessor"},
                )
                return result

            for csv_file in csv_files:
                sheet_name_from_file = csv_file.stem

                if sheet_name and sheet_name_from_file != sheet_name:
                    continue

                with open(csv_file, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = [row for row in reader]
                    result[sheet_name_from_file] = rows

            if sheet_name and sheet_name not in result:
                raise RuntimeError(f"Sheet '{sheet_name}' not found in workbook")

            return result

    async def create_spreadsheet(
        self: LibreOfficeProcessor,
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

        """
        if format == "csv" and len(data) > 1:
            self.logger.warning(
                "CSV format only supports single sheet, using first sheet",
                extra={"service": "LibreOfficeProcessor"},
            )
            data = {list(data.keys())[0]: list(data.values())[0]}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_dir = temp_path / "csv_input"
            csv_dir.mkdir()

            csv_files = []

            for sheet_name, rows in data.items():
                csv_file = csv_dir / f"{sheet_name}.csv"
                csv_files.append(csv_file)

                with open(csv_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)

                    if headers and sheet_name in headers:
                        writer.writerow(headers[sheet_name])

                    for row in rows:
                        writer.writerow(row)

            if format == "csv" and csv_files:
                output_file = temp_path / "output.csv"
                shutil.copy(csv_files[0], output_file)
            else:
                output_dir = temp_path / "output"
                output_dir.mkdir()

                for csv_file in csv_files:
                    command = [
                        self.libreoffice_path,
                        "--headless",
                        "--convert-to",
                        format,
                        "--outdir",
                        str(output_dir),
                        str(csv_file),
                    ]

                    returncode, stdout, stderr = await self._run_libreoffice_command(
                        command
                    )

                    if returncode != 0:
                        error_msg = stderr.decode() if stderr else "Unknown error"
                        self.logger.error(
                            f"Failed to convert {csv_file} to {format}: {error_msg}",
                            extra={"service": "LibreOfficeProcessor"},
                        )
                        return False

                if format == "ods":
                    output_file = self._merge_ods_sheets(output_dir, temp_path)
                else:
                    converted_files = list(output_dir.glob(f"*.{format}"))
                    if not converted_files:
                        self.logger.error(
                            f"No {format} files generated",
                            extra={"service": "LibreOfficeProcessor"},
                        )
                        return False
                    output_file = converted_files[0]

            output_content = output_file.read_bytes()
            saved = await self.storage_backend.save(
                file_path, output_content, overwrite=True
            )

            if saved:
                self.logger.info(
                    f"Created spreadsheet: {file_path}",
                    extra={"service": "LibreOfficeProcessor"},
                )

            return saved

    def _merge_ods_sheets(
        self: LibreOfficeProcessor, source_dir: Path, temp_dir: Path
    ) -> Path:
        """Merge multiple ODS files into single workbook.

        Args:
        ----
            source_dir: Directory containing ODS files.
            temp_dir: Temporary directory for output.

        Returns:
        -------
            Path to merged ODS file.

        """
        ods_files = list(source_dir.glob("*.ods"))
        if not ods_files:
            raise RuntimeError("No ODS files to merge")

        if len(ods_files) == 1:
            return ods_files[0]

        merged_ods = temp_dir / "merged.ods"

        with zipfile.ZipFile(merged_ods, "w", zipfile.ZIP_DEFLATED) as merged:
            content_xml_parts = []

            for ods_file in ods_files:
                with zipfile.ZipFile(ods_file, "r") as source:
                    for item in source.namelist():
                        if item == "content.xml":
                            content_xml_parts.append(source.read(item))
                        elif item not in merged.namelist():
                            merged.writestr(item, source.read(item))

            if content_xml_parts:
                merged_content = b"".join(content_xml_parts)
                merged.writestr("content.xml", merged_content)

        return merged_ods

    async def update_spreadsheet(
        self: LibreOfficeProcessor,
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

        """
        existing_data = await self.read_spreadsheet(file_path)

        if sheet_name:
            if sheet_name not in existing_data:
                raise RuntimeError(f"Sheet '{sheet_name}' not found")
            existing_data[sheet_name] = data.get(sheet_name, existing_data[sheet_name])
        else:
            existing_data.update(data)

        content = await self.storage_backend.read(file_path)
        if not content:
            return False

        file_ext = Path(file_path).suffix.lower()
        format_map = {".xlsx": "xlsx", ".ods": "ods", ".csv": "csv"}
        format_type = format_map.get(file_ext, "xlsx")

        return await self.create_spreadsheet(
            file_path, existing_data, format=format_type
        )

    async def delete_sheet(
        self: LibreOfficeProcessor,
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

        """
        existing_data = await self.read_spreadsheet(file_path)

        if sheet_name not in existing_data:
            raise RuntimeError(f"Sheet '{sheet_name}' not found")

        del existing_data[sheet_name]

        if not existing_data:
            raise RuntimeError("Cannot delete last sheet from workbook")

        content = await self.storage_backend.read(file_path)
        if not content:
            return False

        file_ext = Path(file_path).suffix.lower()
        format_map = {".xlsx": "xlsx", ".ods": "ods", ".csv": "csv"}
        format_type = format_map.get(file_ext, "xlsx")

        return await self.create_spreadsheet(
            file_path, existing_data, format=format_type
        )

    async def get_sheet_info(
        self: LibreOfficeProcessor,
        file_path: str,
    ) -> dict[str, Any]:
        """Get workbook/sheet metadata.

        Args:
        ----
            file_path: Path to spreadsheet file.

        Returns:
        -------
            Dictionary with workbook info (sheet names, row/column counts, etc.).

        """
        data = await self.read_spreadsheet(file_path)

        sheet_info: dict[str, dict[str, int]] = {}
        for sheet_name, rows in data.items():
            row_count = len(rows)
            col_count = max((len(row) for row in rows), default=0)
            sheet_info[sheet_name] = {
                "row_count": row_count,
                "column_count": col_count,
            }

        file_ext = Path(file_path).suffix.lower()
        format_map = {".xlsx": "xlsx", ".ods": "ods", ".csv": "csv"}
        format_type = format_map.get(file_ext, "xlsx")

        return {
            "sheet_names": list(data.keys()),
            "sheet_info": sheet_info,
            "format": format_type,
            "total_sheets": len(data),
        }


__all__ = ["LibreOfficeProcessor"]
