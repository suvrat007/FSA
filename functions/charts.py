from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from functions.config import (
    BS_CASH,
    BS_INVENTORY,
    BS_PPE,
    BS_RECEIVABLES,
    CHART_SERIES_COLORS,
    IS_NET_INCOME,
    IS_REVENUE,
    THEME_COLORS,
)
from functions.datamodel import FinancialDataModel, read_item

_AXIS_STYLE = {
    "gridcolor": THEME_COLORS["chart_grid"],
    "showline": True,
    "linecolor": THEME_COLORS["border_strong"],
    "zeroline": False,
}


def plot_revenue_profit_trend(model: FinancialDataModel) -> go.Figure:
    years = model.years
    income = model.income_statement

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=years,
            y=[read_item(income, IS_REVENUE, year) for year in years],
            name="Revenue",
            marker_color=THEME_COLORS["accent_secondary"],
        )
    )
    figure.add_trace(
        go.Bar(
            x=years,
            y=[read_item(income, IS_NET_INCOME, year) for year in years],
            name="Net income",
            marker_color=THEME_COLORS["accent_primary"],
        )
    )
    figure.update_layout(barmode="group")

    return _apply_theme(figure, "Revenue and net income by period")


def plot_balance_sheet_stack(model: FinancialDataModel) -> go.Figure:
    years = model.years
    balance = model.balance_sheet

    components = [
        (BS_CASH, "Cash and equivalents", THEME_COLORS["accent_primary"]),
        (BS_RECEIVABLES, "Receivables", THEME_COLORS["accent_secondary"]),
        (BS_INVENTORY, "Inventory", THEME_COLORS["warning"]),
        (BS_PPE, "Net PP&E", THEME_COLORS["accent_tertiary"]),
    ]

    figure = go.Figure()

    for item, label, color in components:
        figure.add_trace(
            go.Bar(
                x=years,
                y=[read_item(balance, item, year) for year in years],
                name=label,
                marker_color=color,
            )
        )

    figure.update_layout(barmode="stack")

    return _apply_theme(figure, "Asset composition by period")


def plot_ratio_trend(ratios: pd.DataFrame, ratio_names: List[str], title: str) -> go.Figure:
    figure = go.Figure()

    for index, name in enumerate(ratio_names):
        if name not in ratios.index:
            continue

        figure.add_trace(
            go.Scatter(
                x=list(ratios.columns),
                y=ratios.loc[name],
                mode="lines+markers",
                name=name,
                line={"width": 2.5, "color": CHART_SERIES_COLORS[index % len(CHART_SERIES_COLORS)]},
                marker={"size": 7},
            )
        )

    return _apply_theme(figure, title)


def plot_peer_radar(
    comparison: pd.DataFrame,
    metric_columns: List[str],
    target_label: str = "",
    label_column: str = "Company",
) -> go.Figure:
    figure = go.Figure()

    if comparison.empty or len(comparison) < 2:
        return figure

    available = [
        column
        for column in metric_columns
        if column in comparison.columns and comparison[column].notna().any()
    ]

    if not available:
        return figure

    matches = comparison.index[comparison[label_column] == target_label].tolist()
    target_index = matches[0] if matches else comparison.index[0]

    target = comparison.loc[target_index]
    peer_average = comparison.drop(index=target_index)[available].mean()

    figure.add_trace(
        go.Scatterpolar(
            r=[target[column] for column in available],
            theta=available,
            fill="toself",
            name=str(target["Company"]),
            line_color=THEME_COLORS["accent_primary"],
        )
    )
    figure.add_trace(
        go.Scatterpolar(
            r=[peer_average[column] for column in available],
            theta=available,
            fill="toself",
            name="Peer average",
            line_color=THEME_COLORS["accent_secondary"],
        )
    )
    figure.update_layout(
        polar={
            "bgcolor": "rgba(0,0,0,0)",
            "radialaxis": {"visible": True, "gridcolor": THEME_COLORS["chart_grid"]},
            "angularaxis": {"gridcolor": THEME_COLORS["chart_grid"]},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": THEME_COLORS["text_muted"], "size": 12},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.15},
        margin={"l": 60, "r": 60, "t": 40, "b": 60},
    )

    return figure


def plot_sensitivity_heatmap(matrix: pd.DataFrame, title: str) -> go.Figure:
    figure = px.imshow(
        matrix.values,
        labels={"x": "EBITDA margin", "y": "Revenue growth", "color": "Terminal value"},
        x=list(matrix.columns),
        y=list(matrix.index),
        color_continuous_scale="Viridis",
        aspect="auto",
    )
    figure.update_traces(texttemplate="%{z:,.0f}", textfont={"size": 11})

    return _apply_theme(figure, title)


def plot_stock_price_history(price_history: pd.DataFrame, company_name: str) -> go.Figure:
    if price_history is None or price_history.empty or "Close" not in price_history.columns:
        return go.Figure()

    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25])
    figure.add_trace(
        go.Scatter(
            x=price_history.index,
            y=price_history["Close"],
            name="Close",
            line={"color": THEME_COLORS["accent_primary"], "width": 2},
        ),
        row=1,
        col=1,
    )

    if "Volume" in price_history.columns:
        figure.add_trace(
            go.Bar(
                x=price_history.index,
                y=price_history["Volume"],
                name="Volume",
                marker_color=THEME_COLORS["accent_secondary"],
                opacity=0.5,
            ),
            row=2,
            col=1,
        )

    return _apply_theme(figure, f"{company_name} share price and volume, trailing year")


def plot_metric_comparison(
    comparison: pd.DataFrame,
    metric_column: str,
    label_column: str = "Company",
    highlight: str = "",
) -> go.Figure:
    if comparison.empty or metric_column not in comparison.columns:
        return go.Figure()

    frame = comparison[[label_column, metric_column]].dropna().sort_values(metric_column)

    if frame.empty:
        return go.Figure()

    colors = [
        THEME_COLORS["accent_primary"] if str(label) == highlight else THEME_COLORS["border_strong"]
        for label in frame[label_column]
    ]

    figure = go.Figure(
        go.Bar(
            x=frame[metric_column],
            y=frame[label_column],
            orientation="h",
            marker_color=colors,
            text=[f"{value:,.2f}" for value in frame[metric_column]],
            textposition="auto",
        )
    )
    figure.update_layout(showlegend=False)

    return _apply_theme(figure, metric_column, unified_hover=False)


def plot_multi_company_trend(series: pd.DataFrame, title: str) -> go.Figure:
    figure = go.Figure()

    if series.empty:
        return figure

    for index, column in enumerate(series.columns):
        figure.add_trace(
            go.Scatter(
                x=list(series.index),
                y=series[column],
                mode="lines+markers",
                name=str(column),
                line={"width": 2.5, "color": CHART_SERIES_COLORS[index % len(CHART_SERIES_COLORS)]},
                marker={"size": 6},
            )
        )

    return _apply_theme(figure, title)


def plot_percentile_position(position: pd.DataFrame, title: str) -> go.Figure:
    if position.empty or "Percentile" not in position.columns:
        return go.Figure()

    frame = position.dropna(subset=["Percentile"]).sort_values("Percentile")

    colors = [
        THEME_COLORS["success"]
        if value >= 66
        else THEME_COLORS["warning"]
        if value >= 33
        else THEME_COLORS["danger"]
        for value in frame["Percentile"]
    ]

    figure = go.Figure(
        go.Bar(
            x=frame["Percentile"],
            y=frame["Metric"],
            orientation="h",
            marker_color=colors,
            text=[f"{value:.0f}" for value in frame["Percentile"]],
            textposition="auto",
        )
    )
    figure.add_vline(
        x=50,
        line_dash="dash",
        line_color=THEME_COLORS["text_muted"],
        annotation_text="peer median",
        annotation_position="top",
    )
    figure.update_layout(showlegend=False, xaxis={"range": [0, 100]})

    return _apply_theme(figure, title, unified_hover=False)


def plot_dimension_scores(labels: List[str], scores: List[float], title: str) -> go.Figure:
    colors = [
        THEME_COLORS["success"]
        if score >= 75
        else THEME_COLORS["accent_secondary"]
        if score >= 55
        else THEME_COLORS["warning"]
        if score >= 35
        else THEME_COLORS["danger"]
        for score in scores
    ]

    figure = go.Figure(
        go.Bar(
            x=scores,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{score:.0f}" for score in scores],
            textposition="auto",
        )
    )
    figure.update_layout(showlegend=False, xaxis={"range": [0, 100]})

    return _apply_theme(figure, title, unified_hover=False)


def _apply_theme(figure: go.Figure, title: str, unified_hover: bool = True) -> go.Figure:
    figure.update_layout(
        title={
            "text": title,
            "x": 0.0,
            "xanchor": "left",
            "font": {"size": 15, "color": THEME_COLORS["text_main"]},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": THEME_COLORS["text_muted"], "size": 12},
        margin={"l": 50, "r": 40, "t": 60, "b": 45},
        hovermode="x unified" if unified_hover else "closest",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1.0,
            "font": {"size": 11},
        },
    )
    figure.update_xaxes(**_AXIS_STYLE)
    figure.update_yaxes(**_AXIS_STYLE)

    return figure
