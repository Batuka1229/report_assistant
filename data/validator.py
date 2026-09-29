"""Non-mutating data quality checks."""

from __future__ import annotations

from typing import Any

import pandas as pd


class DataValidator:
    def validate(self, df: pd.DataFrame) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        missing_columns = [str(column) for column in df.columns if str(column).strip() == ""]
        if df.empty:
            errors.append("Өгөгдлийн хуудас хоосон байна.")
        if len(df.columns) == 0:
            errors.append("Файлд багана олдсонгүй.")
        if missing_columns:
            warnings.append(f"Нэргүй багана илэрлээ: {len(missing_columns)}.")

        completely_empty = [str(column) for column in df.columns if df[column].isna().all()]
        if completely_empty:
            warnings.append("Бүрэн хоосон багана: " + ", ".join(completely_empty))
        missing_values = {
            str(column): int(count)
            for column, count in df.isna().sum().items()
            if count > 0
        }
        if missing_values:
            warnings.append("Дутуу утга илэрсэн; эх өгөгдлийг өөрчлөөгүй.")
        duplicate_rows = int(df.duplicated().sum())
        if duplicate_rows:
            warnings.append(f"Давхардсан мөр: {duplicate_rows}.")

        numeric_strings: list[str] = []
        invalid_dates: list[str] = []
        invalid_types: list[str] = []
        for column in df.select_dtypes(include=["object", "string"]).columns:
            values = df[column].dropna()
            if values.empty:
                continue
            as_text = values.astype(str).str.strip()
            numeric_candidate = pd.to_numeric(as_text.str.replace(",", "", regex=False), errors="coerce")
            if numeric_candidate.notna().mean() >= 0.8:
                numeric_strings.append(str(column))
            name_hint = any(token in str(column).lower() for token in ("date", "time", "огноо", "сар", "өдөр"))
            if name_hint and pd.to_datetime(values, errors="coerce").isna().mean() > 0:
                invalid_dates.append(str(column))
            mixed_types = values.map(lambda value: type(value).__name__).nunique() > 1
            if mixed_types or any(value == "" for value in as_text):
                invalid_types.append(str(column))
        if numeric_strings:
            warnings.append("Тоон утга текст хэлбэрээр хадгалагдсан байж болзошгүй багана: " + ", ".join(numeric_strings))
        if invalid_dates:
            warnings.append("Огнооны баганад хөрвөхгүй утга байна: " + ", ".join(invalid_dates))
        if invalid_types:
            warnings.append("Хоосон текстэн утга байна: " + ", ".join(invalid_types))

        return {
            "is_valid": not errors,
            "warnings": warnings,
            "errors": errors,
            "missing_values": missing_values,
            "duplicate_rows": duplicate_rows,
            "empty_columns": completely_empty,
            "numeric_strings": numeric_strings,
            "invalid_dates": invalid_dates,
            "missing_column_names": missing_columns,
        }


def validate_data(df: pd.DataFrame) -> dict[str, Any]:
    return DataValidator().validate(df)