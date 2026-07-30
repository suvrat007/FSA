from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from functions.assessment import assess_company
from functions.config import IS_REVENUE
from functions.datamodel import FinancialDataModel, read_item
from functions.ratios import (
    ASSET_TURNOVER,
    CCC,
    CFO_TO_NET_INCOME,
    CURRENT_RATIO,
    DEBT_TO_EQUITY,
    EBITDA_MARGIN,
    FCF_TO_REVENUE,
    INTEREST_COVERAGE,
    NET_MARGIN,
    ROCE,
    ROE,
    compute_all_ratios,
    read_ratio,
)
from functions.statements import compute_cagr

COMPANY_COLUMN = "Company"
TICKER_COLUMN = "Ticker"
PERIOD_COLUMN = "Period"
REVENUE_COLUMN = "Revenue"
REVENUE_CAGR_COLUMN = "Revenue CAGR (%)"
GRADE_COLUMN = "Overall grade"
SCORE_COLUMN = "Overall score"

IDENTITY_COLUMNS = [COMPANY_COLUMN, TICKER_COLUMN, PERIOD_COLUMN]


@dataclass(frozen=True)
class ComparisonMetric:
    column: str
    ratio: Optional[str]
    higher_is_better: bool
    number_format: str


COMPARISON_METRICS: List[ComparisonMetric] = [
    ComparisonMetric(REVENUE_COLUMN, None, True, "{:,.0f}"),
    ComparisonMetric(REVENUE_CAGR_COLUMN, None, True, "{:+.1f}"),
    ComparisonMetric("EBITDA margin (%)", EBITDA_MARGIN, True, "{:.1f}"),
    ComparisonMetric("Net margin (%)", NET_MARGIN, True, "{:.1f}"),
    ComparisonMetric("ROE (%)", ROE, True, "{:.1f}"),
    ComparisonMetric("ROCE (%)", ROCE, True, "{:.1f}"),
    ComparisonMetric("Asset turnover (x)", ASSET_TURNOVER, True, "{:.2f}"),
    ComparisonMetric("Current ratio (x)", CURRENT_RATIO, True, "{:.2f}"),
    ComparisonMetric("Debt to equity (x)", DEBT_TO_EQUITY, False, "{:.2f}"),
    ComparisonMetric("Interest coverage (x)", INTEREST_COVERAGE, True, "{:.2f}"),
    ComparisonMetric("CFO to net income (x)", CFO_TO_NET_INCOME, True, "{:.2f}"),
    ComparisonMetric("FCF to revenue (%)", FCF_TO_REVENUE, True, "{:.1f}"),
    ComparisonMetric("Cash conversion cycle (days)", CCC, False, "{:.0f}"),
]

METRIC_COLUMNS = [metric.column for metric in COMPARISON_METRICS]

RADAR_METRICS: List[str] = [
    "EBITDA margin (%)",
    "Net margin (%)",
    "ROE (%)",
    "ROCE (%)",
]

METRIC_BY_COLUMN = {metric.column: metric for metric in COMPARISON_METRICS}

NUMBER_FORMATS = {metric.column: metric.number_format for metric in COMPARISON_METRICS}


def build_comparison_table(
    models: List[FinancialDataModel],
    include_assessment: bool = True,
) -> pd.DataFrame:
    rows = []

    for model in models:
        if not model.years:
            continue

        ratios = compute_all_ratios(model)
        latest_year = model.years[-1]
        income = model.income_statement

        revenue_cagr = np.nan
        if IS_REVENUE in income.index and len(model.years) >= 3:
            revenue_cagr = compute_cagr(income.loc[IS_REVENUE])

        row = {
            COMPANY_COLUMN: model.company_name,
            TICKER_COLUMN: model.ticker,
            PERIOD_COLUMN: latest_year,
            REVENUE_COLUMN: read_item(income, IS_REVENUE, latest_year, default=np.nan),
            REVENUE_CAGR_COLUMN: revenue_cagr,
        }

        for metric in COMPARISON_METRICS:
            if metric.ratio is not None:
                row[metric.column] = read_ratio(ratios, metric.ratio, latest_year)

        if include_assessment:
            assessment = assess_company(model)
            row[GRADE_COLUMN] = assessment.grade
            row[SCORE_COLUMN] = assessment.score

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    columns = IDENTITY_COLUMNS + METRIC_COLUMNS
    if include_assessment:
        columns += [SCORE_COLUMN, GRADE_COLUMN]

    return pd.DataFrame(rows).reindex(columns=columns)


def build_rank_table(comparison: pd.DataFrame) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()

    ranks = comparison[IDENTITY_COLUMNS].copy()

    for column in METRIC_COLUMNS:
        if column not in comparison.columns:
            continue

        metric = METRIC_BY_COLUMN[column]
        ranks[column] = comparison[column].rank(
            ascending=not metric.higher_is_better,
            method="min",
            na_option="keep",
        )

    return ranks


def build_metric_series(
    models: List[FinancialDataModel],
    ratio_name: str,
) -> pd.DataFrame:
    series: Dict[str, pd.Series] = {}

    for model in models:
        ratios = compute_all_ratios(model)

        if ratios.empty or ratio_name not in ratios.index:
            continue

        series[f"{model.company_name}"] = ratios.loc[ratio_name]

    if not series:
        return pd.DataFrame()

    return pd.DataFrame(series)


def percentile_rank(value: float, population: List[float], higher_is_better: bool) -> float:
    values = [item for item in population if item is not None and not np.isnan(item)]

    if np.isnan(value) or len(values) < 2:
        return np.nan

    below = sum(1 for item in values if item < value)
    equal = sum(1 for item in values if item == value)
    percentile = 100.0 * (below + 0.5 * equal) / len(values)

    return round(percentile if higher_is_better else 100.0 - percentile, 1)


def build_position_table(
    target: FinancialDataModel,
    cohort: List[FinancialDataModel],
) -> pd.DataFrame:
    comparison = build_comparison_table([target] + list(cohort), include_assessment=False)

    if comparison.empty or len(comparison) < 2:
        return pd.DataFrame()

    target_row = comparison.iloc[0]
    peer_frame = comparison.iloc[1:]
    rows = []

    for column in METRIC_COLUMNS:
        if column not in comparison.columns:
            continue

        metric = METRIC_BY_COLUMN[column]
        peer_values = peer_frame[column].dropna().tolist()
        target_value = target_row[column]

        if not peer_values or pd.isna(target_value):
            continue

        median = float(np.median(peer_values))
        rows.append(
            {
                "Metric": column,
                target.ticker: round(float(target_value), 2),
                "Peer median": round(median, 2),
                "Peer best": round(
                    float(max(peer_values) if metric.higher_is_better else min(peer_values)), 2
                ),
                "Peer worst": round(
                    float(min(peer_values) if metric.higher_is_better else max(peer_values)), 2
                ),
                "Gap to median": round(float(target_value) - median, 2),
                "Percentile": percentile_rank(
                    float(target_value),
                    peer_values + [float(target_value)],
                    metric.higher_is_better,
                ),
                "Standing": _standing(
                    float(target_value), median, metric.higher_is_better
                ),
            }
        )

    return pd.DataFrame(rows)


def summarise_position(position: pd.DataFrame, target_name: str) -> str:
    if position.empty:
        return f"No comparable peer data was available to position {target_name}."

    leading = position[position["Standing"] == "Ahead"]["Metric"].tolist()
    lagging = position[position["Standing"] == "Behind"]["Metric"].tolist()
    average_percentile = position["Percentile"].mean()

    parts = [
        f"{target_name} sits at the {average_percentile:.0f}th percentile of its comparison set "
        f"on average across {len(position)} metrics."
    ]

    if leading:
        parts.append(f"It leads the peer median on {_join_lower(leading)}.")

    if lagging:
        parts.append(f"It trails the peer median on {_join_lower(lagging)}.")

    if not leading and not lagging:
        parts.append("It tracks the peer median closely on every measured dimension.")

    return " ".join(parts)


def cohort_statistics(comparison: pd.DataFrame) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()

    available = [column for column in METRIC_COLUMNS if column in comparison.columns]
    described = comparison[available].describe(percentiles=[0.25, 0.5, 0.75]).T

    return described[["count", "min", "25%", "50%", "75%", "max"]].round(2)


def _standing(value: float, median: float, higher_is_better: bool) -> str:
    if median == 0:
        return "Level"

    relative = (value - median) / abs(median)

    if abs(relative) < 0.05:
        return "Level"

    ahead = relative > 0 if higher_is_better else relative < 0

    return "Ahead" if ahead else "Behind"


def _join_lower(values: List[str]) -> str:
    lowered = [value.lower() for value in values]

    if len(lowered) == 1:
        return lowered[0]

    return f"{', '.join(lowered[:-1])} and {lowered[-1]}"
