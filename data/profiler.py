"""Infer useful column roles without modifying source data."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class DataProfiler:
    def profile(self, df: pd.DataFrame) -> dict[str, Any]:
        numeric = df.select_dtypes(include=np.number).columns.tolist()
        booleans = df.select_dtypes(include=["bool", "boolean"]).columns.tolist()
        date_columns: list[str] = []
        numeric_strings: list[str] = []
        for column in df.columns:
            if column in numeric or column in booleans:
                continue
            series = df[column]
            values = series.dropna()
            if values.empty:
                continue
            lower_name = str(column).lower()
            date_hint = any(token in lower_name for token in ("date", "time", "огноо", "сар", "өдөр"))
            if pd.api.types.is_datetime64_any_dtype(series):
                date_columns.append(str(column))
            elif pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
                parsed_numbers = pd.to_numeric(values.astype(str).str.replace(",", "", regex=False), errors="coerce")
                if parsed_numbers.notna().mean() >= 0.8:
                    numeric_strings.append(str(column))
                else:
                    parsed_dates = pd.to_datetime(values, errors="coerce", format="mixed")
                    if parsed_dates.notna().mean() >= (0.7 if date_hint else 0.9):
                        date_columns.append(str(column))

        id_columns: list[str] = []
        categorical: list[str] = []
        text: list[str] = []
        for column in df.columns:
            if column in numeric or column in booleans or column in date_columns:
                continue
            series = df[column]
            nunique = int(series.nunique(dropna=True))
            ratio = nunique / max(len(df), 1)
            name = str(column).lower()
            id_hint = any(token in name for token in ("id", "код", "дугаар", "number", "uuid"))
            if id_hint or (len(df) > 1 and ratio >= 0.98 and nunique > 10):
                id_columns.append(str(column))
            elif nunique <= min(100, max(20, int(np.sqrt(max(len(df), 1)) * 2))):
                categorical.append(str(column))
            else:
                text.append(str(column))

        return {
            "numeric_columns": [str(item) for item in numeric],
            "date_columns": date_columns,
            "categorical_columns": categorical,
            "boolean_columns": [str(item) for item in booleans],
            "text_columns": text,
            "id_columns": id_columns,
            "numeric_string_columns": numeric_strings,
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "column_types": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
            "missing_values": {str(key): int(value) for key, value in df.isna().sum().items() if value},
        }


def profile_data(df: pd.DataFrame) -> dict[str, Any]:
    return DataProfiler().profile(df)