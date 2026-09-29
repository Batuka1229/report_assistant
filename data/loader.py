"""In-memory loading utilities for supported tabular files."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from zipfile import BadZipFile

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException
from xlrd.biffh import XLRDError


class DataLoader:
    """Load tabular files without persisting uploaded content to disk."""

    @staticmethod
    def _bytes(source: bytes | bytearray | BinaryIO) -> bytes:
        if isinstance(source, (bytes, bytearray)):
            return bytes(source)
        getvalue = getattr(source, "getvalue", None)
        if callable(getvalue):
            payload = getvalue()
            if isinstance(payload, bytes):
                return payload
        position = source.tell() if source.seekable() else None
        payload = source.read()
        if position is not None:
            source.seek(position)
        return payload

    @staticmethod
    def _suffix(source: object, filename: str | None = None) -> str:
        name = filename or getattr(source, "name", "")
        return Path(str(name)).suffix.lower()

    def get_sheets(self, source: bytes | bytearray | BinaryIO, filename: str | None = None) -> list[str]:
        suffix = self._suffix(source, filename)
        if suffix == ".csv":
            return ["CSV"]
        if suffix not in {".xlsx", ".xls"}:
            raise ValueError("Зөвхөн .xlsx, .xls эсвэл .csv файл дэмжинэ.")
        try:
            with pd.ExcelFile(BytesIO(self._bytes(source))) as workbook:
                return [str(sheet_name) for sheet_name in workbook.sheet_names]
        except (ValueError, OSError, ImportError, BadZipFile) as exc:
            raise ValueError("Excel файлыг унших боломжгүй байна.") from exc
        except (InvalidFileException, XLRDError) as exc:
            raise ValueError("Excel файлыг унших боломжгүй байна.") from exc

    def load_excel(
        self,
        source: bytes | bytearray | BinaryIO,
        sheet_name: str | int = 0,
        filename: str | None = None,
    ) -> pd.DataFrame:
        if self._suffix(source, filename) not in {".xlsx", ".xls"}:
            raise ValueError("Excel файлын өргөтгөл .xlsx эсвэл .xls байх ёстой.")
        try:
            return pd.read_excel(BytesIO(self._bytes(source)), sheet_name=sheet_name)
        except (ValueError, OSError, ImportError, IndexError, BadZipFile, InvalidFileException, XLRDError) as exc:
            raise ValueError("Сонгосон Excel хуудсыг унших боломжгүй байна.") from exc

    def load_csv(
        self,
        source: bytes | bytearray | BinaryIO,
        filename: str | None = None,
    ) -> pd.DataFrame:
        if self._suffix(source, filename) not in {".csv", ""}:
            raise ValueError("CSV файлын өргөтгөл .csv байх ёстой.")
        payload = self._bytes(source)
        if not payload:
            raise ValueError("Файл хоосон байна.")
        errors: list[UnicodeDecodeError] = []
        for encoding in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                return pd.read_csv(BytesIO(payload), encoding=encoding)
            except UnicodeDecodeError as exc:
                errors.append(exc)
        raise ValueError("CSV файлын кодчиллыг таних боломжгүй байна.") from errors[-1]

    def load_sheet(
        self,
        source: bytes | bytearray | BinaryIO,
        sheet_name: str | int = 0,
        filename: str | None = None,
    ) -> pd.DataFrame:
        suffix = self._suffix(source, filename)
        if suffix == ".csv":
            return self.load_csv(source, filename)
        if suffix in {".xlsx", ".xls"}:
            return self.load_excel(source, sheet_name, filename)
        raise ValueError("Зөвхөн .xlsx, .xls эсвэл .csv файл дэмжинэ.")