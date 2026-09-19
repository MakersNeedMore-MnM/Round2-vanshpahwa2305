"""Safe, reusable Plotly visualizations for QueryPeek result sets."""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

MAX_PLOT_ROWS = 5_000
_MEASURE_HINTS = (
    "amount", "average", "avg", "count", "frequency", "number", "quantity",
    "rate", "revenue", "sales", "share", "sum", "total", "value", "volume",
    "percent", "percentage", "proportion", "distribution", "ratio",
)
_PIE_HINTS = (
    "count", "frequency", "percent", "percentage", "proportion", "distribution",
    "ratio", "share",
)


def _column_text(column: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(column).lower()).strip("_")


def _column_tokens(column: object) -> set[str]:
    return set(_column_text(column).split("_"))


def _unique_columns(columns: Iterable[object]) -> list[str]:
    """Return stable, unique labels without changing the caller's DataFrame."""

    used: dict[str, int] = {}
    result: list[str] = []
    for column in columns:
        base = str(column) or "column"
        occurrence = used.get(base, 0) + 1
        used[base] = occurrence
        result.append(base if occurrence == 1 else f"{base}_{occurrence}")
    return result


def _numeric_values(series: pd.Series) -> pd.Series | None:
    values = pd.to_numeric(series, errors="coerce")
    non_null = series.notna().sum()
    if non_null == 0 or values.notna().sum() < max(1, int(non_null * 0.8)):
        return None
    return values


def _datetime_values(series: pd.Series) -> pd.Series | None:
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")
    if pd.api.types.is_numeric_dtype(series):
        return None
    values = pd.to_datetime(series, errors="coerce", format="mixed")
    non_null = series.notna().sum()
    if non_null < 2 or values.notna().sum() < max(2, int(non_null * 0.8)):
        return None
    return values


def _is_numeric(series: pd.Series) -> bool:
    return _numeric_values(series) is not None


def _is_datetime(series: pd.Series) -> bool:
    return _datetime_values(series) is not None


def _score_column(column: object, *, measure: bool) -> int:
    tokens = _column_tokens(column)
    score = len(tokens & set(_MEASURE_HINTS)) if measure else 0
    if "id" in tokens or _column_text(column).endswith("_id"):
        score -= 4
    return score


def _choose_column(columns: list[str], *, measure: bool) -> str:
    return max(
        enumerate(columns),
        key=lambda item: (_score_column(item[1], measure=measure), -item[0]),
    )[1]


def _is_pie_suitable(category: str, value: str, frame: pd.DataFrame) -> bool:
    categories = frame[category].nunique(dropna=True)
    if not 2 <= categories <= 6:
        return False
    values = pd.to_numeric(frame[value], errors="coerce").dropna()
    if values.empty or (values < 0).any() or values.sum() <= 0:
        return False
    name_suggests_distribution = bool(_column_tokens(value) & set(_PIE_HINTS))
    total = float(values.sum())
    represents_share = abs(total - 1) < 0.01 or abs(total - 100) < 0.01
    return name_suggests_distribution or represents_share


def _prepared_frame(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy(deep=True)
    frame.columns = _unique_columns(frame.columns)
    return frame.head(MAX_PLOT_ROWS)


def create_visualization(data: pd.DataFrame) -> Figure | None:
    """Create a conservative chart for results, or return ``None``.

    The input is copied before type coercion or row bounding. This function
    only visualizes supplied results and never connects to or executes SQL.
    """

    if not isinstance(data, pd.DataFrame) or data.empty or len(data.columns) < 2:
        return None

    frame = _prepared_frame(data)
    numeric_columns = [column for column in frame.columns if _is_numeric(frame[column])]
    datetime_columns = [column for column in frame.columns if _is_datetime(frame[column])]

    if datetime_columns and numeric_columns and len(frame) >= 2:
        x_column = datetime_columns[0]
        y_column = _choose_column(numeric_columns, measure=True)
        frame[x_column] = _datetime_values(frame[x_column])
        frame[y_column] = _numeric_values(frame[y_column])
        chart_data = frame[[x_column, y_column]].dropna()
        if chart_data.empty:
            return None
        return px.line(chart_data, x=x_column, y=y_column, markers=True)

    if len(numeric_columns) >= 2 and len(frame) >= 2:
        x_column, y_column = numeric_columns[:2]
        frame[x_column] = _numeric_values(frame[x_column])
        frame[y_column] = _numeric_values(frame[y_column])
        chart_data = frame[[x_column, y_column]].dropna()
        if chart_data.empty:
            return None
        return px.scatter(chart_data, x=x_column, y=y_column)

    categorical_columns = [
        column
        for column in frame.columns
        if column not in numeric_columns and column not in datetime_columns
    ]
    if categorical_columns and numeric_columns and len(frame) >= 2:
        category_column = min(
            categorical_columns,
            key=lambda column: frame[column].nunique(dropna=True),
        )
        value_column = _choose_column(numeric_columns, measure=True)
        frame[value_column] = _numeric_values(frame[value_column])
        chart_data = frame[[category_column, value_column]].dropna()
        if chart_data.empty:
            return None
        if _is_pie_suitable(category_column, value_column, chart_data):
            return px.pie(chart_data, names=category_column, values=value_column, hole=0.45)
        return px.bar(chart_data, x=category_column, y=value_column)

    return None


__all__ = ["create_visualization"]
