"""Data-driven Plotly visualizations."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px


def create_charts(df: pd.DataFrame, profile: dict[str, Any]) -> list[tuple[str, Any]]:
    charts: list[tuple[str, Any]] = []
    numeric = profile.get("numeric_columns", [])
    dates = profile.get("date_columns", [])
    categories = profile.get("categorical_columns", [])
    columns_by_name = {str(column): column for column in df.columns}

    if dates and numeric:
        date_column, value_column = dates[0], numeric[0]
        dates_parsed = pd.to_datetime(df[columns_by_name[date_column]], errors="coerce")
        actual_value_column = columns_by_name[value_column]
        trend_df = pd.DataFrame({"Огноо": dates_parsed, value_column: pd.to_numeric(df[actual_value_column], errors="coerce")})
        trend_df = trend_df.dropna().sort_values("Огноо")
        if not trend_df.empty:
            charts.append(("Хугацааны өөрчлөлт", px.line(
                trend_df, x="Огноо", y=value_column, title=f"{value_column} хугацааны өөрчлөлт"
            )))

    if categories and numeric:
        category, metric = categories[0], numeric[0]
        grouped = pd.DataFrame({
            "Ангилал": df[columns_by_name[category]].fillna("(хоосон)").astype(str),
            metric: pd.to_numeric(df[columns_by_name[metric]], errors="coerce"),
        }).groupby("Ангилал", as_index=False)[metric].sum().nlargest(20, metric)
        if not grouped.empty:
            charts.append(("Ангиллын харьцуулалт", px.bar(
                grouped, x="Ангилал", y=metric, title=f"{category} — {metric}"
            )))
            charts.append(("Ангиллын бүтэц", px.pie(
                grouped, names="Ангилал", values=metric, title=f"{metric}-ийн ангиллын бүтэц"
            )))

    if numeric:
        metric = numeric[0]
        values = pd.to_numeric(df[columns_by_name[metric]], errors="coerce").dropna()
        if not values.empty:
            charts.append(("Утгын тархалт", px.histogram(
                x=values, nbins=30, title=f"{metric} утгын тархалт", labels={"x": metric}
            )))
            charts.append(("Хайрцган график", px.box(
                y=values, title=f"{metric} — утгын тархалт", labels={"y": metric}
            )))
    return charts