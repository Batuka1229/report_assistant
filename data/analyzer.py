"""Deterministic analysis using Pandas and NumPy as the source of truth."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config.settings import MAX_CATEGORIES
from data.profiler import DataProfiler

_KPI_TERMS = (
    "amount", "total", "revenue", "income", "expense", "cost", "budget",
    "quantity", "count", "price", "balance", "profit", "sales", "үнэ",
    "дүн", "орлого", "зарлага", "тоо", "ашиг",
)
_FREQUENCIES = {"daily": "D", "weekly": "W", "monthly": "M", "quarterly": "Q", "yearly": "Y"}


def _number(value: Any) -> int | float | None:
    if value is None or pd.isna(value):
        return None
    result = float(value)
    if not np.isfinite(result):
        return None
    return int(result) if result.is_integer() else result


class DataAnalyzer:
    def __init__(self, df: pd.DataFrame, profile: dict[str, Any] | None = None):
        self.df = df
        self.profile = profile or DataProfiler().profile(df)
        self._column_by_name = {str(column): column for column in df.columns}
        self.numeric = df.select_dtypes(include=np.number).copy()
        for column in self.profile.get("numeric_string_columns", []):
            source_column = self._column_by_name[column]
            values = pd.to_numeric(
                df[source_column].astype("string").str.replace(",", "", regex=False), errors="coerce"
            )
            if values.notna().any():
                self.numeric[column] = values
        self.dates: dict[str, pd.Series] = {}
        for column in self.profile.get("date_columns", []):
            parsed = pd.to_datetime(df[self._column_by_name[column]], errors="coerce")
            if parsed.notna().sum() >= 2:
                self.dates[column] = parsed

    def basic_summary(self) -> dict[str, Any]:
        numeric_summary: dict[str, dict[str, Any]] = {}
        if not self.numeric.empty:
            describe = self.numeric.describe(percentiles=[0.25, 0.5, 0.75]).T
            for column, row in describe.iterrows():
                values = self.numeric[column].dropna().to_numpy(dtype=float)
                numeric_summary[str(column)] = {
                    "count": int(row["count"]),
                    "sum": _number(self.numeric[column].sum()),
                    "mean": _number(np.mean(values)) if len(values) else None,
                    "median": _number(np.median(values)) if len(values) else None,
                    "min": _number(row["min"]),
                    "max": _number(row["max"]),
                    "std": _number(np.std(values, ddof=1)) if len(values) > 1 else None,
                    "variance": _number(np.var(values, ddof=1)) if len(values) > 1 else None,
                    "25th_percentile": _number(row["25%"]),
                    "50th_percentile": _number(row["50%"]),
                    "75th_percentile": _number(row["75%"]),
                }
        date_range = {
            column: {
                "start": dates.min().date().isoformat(),
                "end": dates.max().date().isoformat(),
                "valid_dates": int(dates.notna().sum()),
            }
            for column, dates in self.dates.items()
        }
        return {
            "dataset": {
                "rows": int(len(self.df)),
                "columns": int(len(self.df.columns)),
                "column_names": [str(column) for column in self.df.columns],
                "date_range": date_range,
            },
            "statistics": numeric_summary,
            "data_quality": self.analyze_missing_values() | self.analyze_duplicates(),
            "profile": self.profile,
        }

    def calculate_kpis(self) -> list[dict[str, Any]]:
        kpis: list[dict[str, Any]] = []
        for column in self.numeric.columns:
            values = self.numeric[column].dropna()
            if values.empty:
                continue
            name_match = any(term in str(column).lower() for term in _KPI_TERMS)
            varied = values.nunique() > 1
            if not name_match and (len(self.numeric.columns) > 4 or not varied):
                continue
            kpis.append({
                "column": str(column),
                "sum": _number(values.sum()),
                "average": _number(np.mean(values.to_numpy(dtype=float))),
                "median": _number(np.median(values.to_numpy(dtype=float))),
                "minimum": _number(values.min()),
                "maximum": _number(values.max()),
                "count": int(values.count()),
            })
        return kpis

    def analyze_missing_values(self) -> dict[str, Any]:
        counts = self.df.isna().sum()
        return {
            "missing_values": {str(key): int(value) for key, value in counts.items() if value},
            "total_missing_values": int(counts.sum()),
            "missing_value_percent": _number(counts.sum() / max(self.df.size, 1) * 100),
        }

    def analyze_duplicates(self) -> dict[str, Any]:
        return {"duplicate_rows": int(self.df.duplicated().sum())}

    def analyze_numeric_columns(self) -> dict[str, Any]:
        return self.basic_summary()["statistics"]

    def analyze_categories(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for column in self.profile.get("categorical_columns", []):
            counts = self.df[self._column_by_name[column]].value_counts(dropna=False).head(MAX_CATEGORIES)
            result[column] = [
                {
                    "category": "(хоосон)" if (
                        value is None or value is pd.NA
                        or (isinstance(value, (float, np.floating)) and np.isnan(value))
                    ) else str(value),
                    "count": int(count),
                }
                for value, count in counts.items()
            ]
        return result

    def analyze_trends(self) -> list[dict[str, Any]]:
        trends: list[dict[str, Any]] = []
        for date_column, dates in self.dates.items():
            for value_column in self.numeric.columns:
                frame = pd.DataFrame({"date": dates, "value": self.numeric[value_column]})
                frame = frame.dropna(subset=["date"])
                if frame["date"].nunique() < 2:
                    continue
                for frequency_name, frequency in _FREQUENCIES.items():
                    period_values = frame.groupby(frame["date"].dt.to_period(frequency))["value"]
                    grouped = period_values.agg(["sum", "mean", "count"]).dropna(how="all")
                    if len(grouped) < 2:
                        continue
                    totals = grouped["sum"]
                    change = totals.pct_change().replace([np.inf, -np.inf], np.nan)
                    periods: list[dict[str, Any]] = []
                    grouped_records = grouped.reset_index(names="period").to_dict(orient="records")
                    for position, row in enumerate(grouped_records):
                        pct = change.iloc[position]
                        periods.append({
                            "period": str(row["period"]),
                            "total": _number(row["sum"]),
                            "average": _number(row["mean"]),
                            "count": int(row["count"]),
                            "change_percent": _number(pct * 100) if pd.notna(pct) else None,
                        })
                    valid_totals = totals.dropna()
                    trends.append({
                        "date_column": str(date_column),
                        "value_column": str(value_column),
                        "frequency": frequency_name,
                        "periods": periods[-MAX_CATEGORIES:],
                        "period_count": int(len(grouped)),
                        "highest_period": str(valid_totals.idxmax()),
                        "lowest_period": str(valid_totals.idxmin()),
                        "total_change_percent": _number(
                            (valid_totals.iloc[-1] / valid_totals.iloc[0] - 1) * 100
                        ) if valid_totals.iloc[0] != 0 else None,
                        "mom_change_percent": _number(change.iloc[-1] * 100)
                        if frequency_name == "monthly" and pd.notna(change.iloc[-1]) else None,
                        "yoy_change_percent": _number(
                            (totals.iloc[-1] / totals.iloc[-13] - 1) * 100
                        ) if frequency_name == "monthly" and len(totals) > 12 and totals.iloc[-13] != 0 else None,
                    })
        return trends

    def compare_categories(self) -> list[dict[str, Any]]:
        comparisons: list[dict[str, Any]] = []
        for category in self.profile.get("categorical_columns", []):
            source_category = self._column_by_name[category]
            if self.df[source_category].nunique(dropna=True) > MAX_CATEGORIES:
                continue
            for metric in self.numeric.columns:
                values = self.numeric[metric]
                working = pd.DataFrame({
                    "category": self.df[source_category].astype("string").fillna("(хоосон)"),
                    "value": values,
                })
                grouped = working.groupby("category", as_index=False)["value"].agg(
                    count="count", sum="sum", mean="mean", min="min", max="max"
                )
                total = float(values.sum())
                rows = []
                records: list[list[Any]] = grouped.to_numpy(dtype=object).tolist()
                records.sort(key=lambda row: float(row[2]), reverse=True)
                for key, count, total_value, average, minimum, maximum in records[:MAX_CATEGORIES]:
                    rows.append({
                        "category": str(key),
                        "count": int(count),
                        "sum": _number(total_value),
                        "average": _number(average),
                        "minimum": _number(minimum),
                        "maximum": _number(maximum),
                        "percentage_of_total": _number(float(total_value) / total * 100) if total else None,
                    })
                comparisons.append({
                    "category_column": str(category),
                    "metric_column": str(metric),
                    "categories": rows,
                })
        return comparisons

    def detect_outliers(self, method: str = "iqr") -> list[dict[str, Any]]:
        outliers: list[dict[str, Any]] = []
        for column in self.numeric.columns:
            values = self.numeric[column].dropna()
            if len(values) < 4:
                continue
            if method == "std":
                mean = float(np.mean(values.to_numpy(dtype=float)))
                std = float(np.std(values.to_numpy(dtype=float)))
                lower, upper = mean - 3 * std, mean + 3 * std
            else:
                q1, q3 = values.quantile([0.25, 0.75])
                spread = float(q3 - q1)
                lower, upper = float(q1 - 1.5 * spread), float(q3 + 1.5 * spread)
            mask = (values < lower) | (values > upper)
            for index, value in values.loc[mask].head(100).items():
                outliers.append({
                    "column": str(column),
                    "row_index": str(index),
                    "value": _number(value),
                    "lower_bound": _number(lower),
                    "upper_bound": _number(upper),
                    "deviation": _number(value - upper if value > upper else value - lower),
                    "method": method,
                })
                if len(outliers) >= 500:
                    return outliers
        return outliers

    def calculate_correlations(self) -> list[dict[str, Any]]:
        if self.numeric.shape[1] < 2:
            return []
        correlation_values = self.numeric.corr().to_numpy(dtype=float)
        columns = [str(column) for column in self.numeric.columns]
        relationships: list[dict[str, Any]] = []
        for left_index, left in enumerate(columns):
            for right_index in range(left_index + 1, len(columns)):
                right = columns[right_index]
                value = float(correlation_values[left_index, right_index])
                if not np.isfinite(value):
                    continue
                relationships.append({
                    "column_a": str(left),
                    "column_b": str(right),
                    "correlation": _number(value),
                    "strength": "strong" if abs(value) >= 0.7 else "moderate" if abs(value) >= 0.4 else "weak",
                    "direction": "positive" if value > 0 else "negative" if value < 0 else "none",
                })
        return sorted(relationships, key=lambda item: abs(item["correlation"] or 0), reverse=True)

    def generate_analysis(self) -> dict[str, Any]:
        summary = self.basic_summary()
        summary.update({
            "kpis": self.calculate_kpis(),
            "categories": self.analyze_categories(),
            "trends": self.analyze_trends(),
            "category_comparisons": self.compare_categories(),
            "outliers": self.detect_outliers(),
            "correlations": self.calculate_correlations(),
        })
        return summary