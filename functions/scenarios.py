from typing import Any, Dict

import pandas as pd

from functions.assumptions import ForecastAssumptions
from functions.config import CF_FREE_CASH_FLOW, IS_NET_INCOME, IS_REVENUE
from functions.datamodel import FinancialDataModel, read_item
from functions.forecast import build_3_statement_forecast

BASE_CASE = "Base case"
BULL_CASE = "Bull case"
BEAR_CASE = "Bear case"

BULL_GROWTH_UPLIFT = 3.0
BULL_MARGIN_UPLIFT = 2.0

BEAR_GROWTH_HAIRCUT = 4.0
BEAR_MARGIN_HAIRCUT = 3.0
BEAR_RATE_PREMIUM = 1.0
BEAR_MIN_GROWTH = 1.0
BEAR_MIN_MARGIN = 5.0


def build_scenario_models(
    model: FinancialDataModel,
    base_assumptions: ForecastAssumptions,
) -> Dict[str, Dict[str, Any]]:
    bull_assumptions = base_assumptions.derive(
        rev_growth_rates=[rate + BULL_GROWTH_UPLIFT for rate in base_assumptions.rev_growth_rates],
        ebitda_margin=base_assumptions.ebitda_margin + BULL_MARGIN_UPLIFT,
    )

    bear_assumptions = base_assumptions.derive(
        rev_growth_rates=[
            max(BEAR_MIN_GROWTH, rate - BEAR_GROWTH_HAIRCUT)
            for rate in base_assumptions.rev_growth_rates
        ],
        ebitda_margin=max(BEAR_MIN_MARGIN, base_assumptions.ebitda_margin - BEAR_MARGIN_HAIRCUT),
        interest_rate=base_assumptions.interest_rate + BEAR_RATE_PREMIUM,
    )

    return {
        BASE_CASE: _build_scenario(model, base_assumptions),
        BULL_CASE: _build_scenario(model, bull_assumptions),
        BEAR_CASE: _build_scenario(model, bear_assumptions),
    }


def compile_scenario_summary_table(scenarios: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    rows = []

    for name, payload in scenarios.items():
        forecast = payload["model"]
        terminal_year = forecast.years[-1]

        rows.append(
            {
                "Scenario": name,
                "Terminal Year": terminal_year,
                "Revenue": read_item(forecast.income_statement, IS_REVENUE, terminal_year),
                "Net Income": read_item(forecast.income_statement, IS_NET_INCOME, terminal_year),
                "Free Cash Flow": read_item(forecast.cash_flow, CF_FREE_CASH_FLOW, terminal_year),
            }
        )

    return pd.DataFrame(rows).round(2)


def _build_scenario(
    model: FinancialDataModel,
    assumptions: ForecastAssumptions,
) -> Dict[str, Any]:
    return {
        "model": build_3_statement_forecast(model, assumptions),
        "assumptions": assumptions,
    }
