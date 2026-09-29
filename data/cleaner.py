"""Optional, explicit data conversions that preserve the caller's DataFrame."""

from __future__ import annotations

import pandas as pd


def create_cleaned_copy(
    df: pd.DataFrame,
    numeric_columns: list[str] | None = None,
    date_columns: list[str] | None = None,
) -> pd.DataFrame:
    cleaned = df.copy(deep=True)
    for column in numeric_columns or []:
        if column in cleaned:
            values = cleaned[column].astype("string").str.replace(",", "", regex=False)
            cleaned[column] = pd.to_numeric(values, errors="coerce")
    for column in date_columns or []:
        if column in cleaned:
            cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
    return cleaned