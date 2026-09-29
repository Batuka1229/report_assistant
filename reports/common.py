"""Shared in-memory report data and chart rendering helpers."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from models.schemas import ReportContent
from utils.formatter import build_report_content


def report_data(
    analysis: dict[str, Any],
    insights: dict[str, Any],
    report: ReportContent | None = None,
) -> ReportContent:
    return build_report_content(analysis, insights, report)


def report_chart_images(df: pd.DataFrame | None, profile: dict[str, Any] | None) -> list[tuple[str, BytesIO]]:
    if df is None or profile is None:
        return []
    images: list[tuple[str, BytesIO]] = []
    numeric = profile.get("numeric_columns", [])
    categories = profile.get("categorical_columns", [])
    dates = profile.get("date_columns", [])
    columns_by_name = {str(column): column for column in df.columns}

    def save_figure(figure: Figure, title: str) -> None:
        buffer = BytesIO()
        FigureCanvasAgg(figure).print_png(buffer)
        buffer.seek(0)
        images.append((title, buffer))
        figure.clear()

    if dates and numeric:
        date_column, metric = dates[0], numeric[0]
        working = pd.DataFrame({
            "date": pd.to_datetime(df[columns_by_name[date_column]], errors="coerce"),
            "value": pd.to_numeric(df[columns_by_name[metric]], errors="coerce"),
        }).dropna().sort_values("date")
        if not working.empty:
            figure = Figure(figsize=(8, 3.6), tight_layout=True)
            axis = figure.subplots()
            axis.plot(working["date"], working["value"], marker="o", markersize=2)
            axis.set_title(f"{metric} — хугацааны өөрчлөлт")
            axis.set_xlabel("Огноо")
            axis.set_ylabel(metric)
            axis.grid(alpha=0.25)
            figure.autofmt_xdate()
            save_figure(figure, "Хугацааны өөрчлөлт")

    if categories and numeric:
        category, metric = categories[0], numeric[0]
        grouped = pd.DataFrame({
            "category": df[columns_by_name[category]].fillna("(хоосон)").astype(str),
            "value": pd.to_numeric(df[columns_by_name[metric]], errors="coerce"),
        }).groupby("category")["value"].sum().nlargest(20).sort_values()
        if not grouped.empty:
            figure = Figure(figsize=(8, max(3.2, len(grouped) * 0.24)), tight_layout=True)
            axis = figure.subplots()
            axis.barh(
                np.asarray(grouped.index.astype(str).tolist(), dtype=str),
                np.asarray(grouped.to_numpy(), dtype=float),
            )
            axis.set_title(f"{category} — {metric}")
            axis.set_xlabel(metric)
            axis.grid(axis="x", alpha=0.25)
            save_figure(figure, "Ангиллын харьцуулалт")

    if numeric:
        metric = numeric[0]
        values = pd.to_numeric(df[columns_by_name[metric]], errors="coerce").dropna().to_numpy(dtype=float)
        if values.size:
            figure = Figure(figsize=(8, 3.4), tight_layout=True)
            axis = figure.subplots()
            axis.hist(values, bins=min(30, max(5, int(np.sqrt(values.size)))), color="#2878A0")
            axis.set_title(f"{metric} — утгын тархалт")
            axis.set_xlabel(metric)
            axis.set_ylabel("Давтамж")
            axis.grid(axis="y", alpha=0.25)
            save_figure(figure, "Утгын тархалт")
    return images