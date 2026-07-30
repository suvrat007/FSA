from typing import List

import pandas as pd

from functions.assumptions import ForecastAssumptions
from functions.config import CF_FREE_CASH_FLOW, IS_NET_INCOME
from functions.datamodel import FinancialDataModel, read_item
from functions.forecast import build_3_statement_forecast

METRIC_NET_INCOME = "Net Income"
METRIC_FREE_CASH_FLOW = "Free Cash Flow"

SENSITIVITY_METRICS: List[str] = [METRIC_NET_INCOME, METRIC_FREE_CASH_FLOW]


def generate_2d_sensitivity_matrix(
    model: FinancialDataModel,
    base_assumptions: ForecastAssumptions,
    rev_growth_steps: List[float],
    ebitda_margin_steps: List[float],
    target_metric: str = METRIC_NET_INCOME,
) -> pd.DataFrame:
    matrix = [
        [
            _terminal_value(model, base_assumptions, growth, margin, target_metric)
            for margin in ebitda_margin_steps
        ]
        for growth in rev_growth_steps
    ]

    return pd.DataFrame(
        matrix,
        index=[f"Growth {growth:+.1f}%" for growth in rev_growth_steps],
        columns=[f"Margin {margin:.1f}%" for margin in ebitda_margin_steps],
    ).round(2)


def _terminal_value(
    model: FinancialDataModel,
    base_assumptions: ForecastAssumptions,
    growth: float,
    margin: float,
    target_metric: str,
) -> float:
    assumptions = base_assumptions.derive(
        rev_growth_rates=[growth] * base_assumptions.n_years,
        ebitda_margin=margin,
    )
    forecast = build_3_statement_forecast(model, assumptions)
    terminal_year = forecast.years[-1]

    if target_metric == METRIC_FREE_CASH_FLOW:
        return read_item(forecast.cash_flow, CF_FREE_CASH_FLOW, terminal_year)

    return read_item(forecast.income_statement, IS_NET_INCOME, terminal_year)
