from typing import List

import pandas as pd

from functions.assumptions import ForecastAssumptions
from functions.config import (
    BS_CASH,
    BS_EQUITY_CAPITAL,
    BS_INVENTORY,
    BS_LT_DEBT,
    BS_OTHER_CA,
    BS_OTHER_CL,
    BS_OTHER_NCA,
    BS_OTHER_NCL,
    BS_PAYABLES,
    BS_PPE,
    BS_RECEIVABLES,
    BS_RESERVES,
    BS_ST_DEBT,
    BS_TOTAL_ASSETS,
    BS_TOTAL_CA,
    BS_TOTAL_CL,
    BS_TOTAL_DEBT,
    BS_TOTAL_EQUITY,
    BS_TOTAL_LIABILITIES,
    CF_CAPEX,
    CF_FINANCING,
    CF_FREE_CASH_FLOW,
    CF_INVESTING,
    CF_OPERATING,
    IS_EBIT,
    IS_EBITDA,
    IS_INTEREST,
    IS_NET_INCOME,
    IS_PBT,
    IS_REVENUE,
    IS_TAX,
)
from functions.datamodel import FinancialDataModel, read_item

DAYS_IN_YEAR = 365.0
FALLBACK_BASE_YEAR = 24


def build_3_statement_forecast(
    model: FinancialDataModel,
    assumptions: ForecastAssumptions,
) -> FinancialDataModel:
    if not model.years:
        return model

    forecast_years = _build_forecast_years(model.years[-1], assumptions.n_years)
    timeline = list(model.years) + forecast_years

    income = model.income_statement.copy()
    balance = model.balance_sheet.copy()
    cash = model.cash_flow.copy()

    for year in forecast_years:
        income[year] = 0.0
        balance[year] = 0.0
        cash[year] = 0.0

    for index, year in enumerate(forecast_years):
        previous_year = timeline[timeline.index(year) - 1]
        _project_year(income, balance, cash, assumptions, index, year, previous_year)

    return FinancialDataModel(
        company_name=f"{model.company_name} (forecast)",
        ticker=model.ticker,
        currency=model.currency,
        years=timeline,
        income_statement=income.round(2),
        balance_sheet=balance.round(2),
        cash_flow=cash.round(2),
        market_data=model.market_data,
        metadata=model.metadata,
    )


def _build_forecast_years(last_historical_year: str, count: int) -> List[str]:
    digits = "".join(char for char in last_historical_year if char.isdigit())
    base_year = int(digits) if digits else FALLBACK_BASE_YEAR

    return [f"FY{(base_year + offset) % 100:02d}" for offset in range(1, count + 1)]


def _project_year(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cash: pd.DataFrame,
    assumptions: ForecastAssumptions,
    index: int,
    year: str,
    previous_year: str,
) -> None:
    growth_rate = assumptions.growth_for(index)

    opening_ppe = read_item(balance, BS_PPE, previous_year)
    opening_debt = read_item(balance, BS_TOTAL_DEBT, previous_year)

    revenue = read_item(income, IS_REVENUE, previous_year) * (1.0 + growth_rate / 100.0)
    ebitda = revenue * (assumptions.ebitda_margin / 100.0)
    depreciation = opening_ppe * (assumptions.depr_percent_ppe / 100.0)
    ebit = ebitda - depreciation
    interest = opening_debt * (assumptions.interest_rate / 100.0)
    profit_before_tax = ebit - interest
    tax = max(0.0, profit_before_tax * (assumptions.tax_rate / 100.0))
    net_income = profit_before_tax - tax

    income.loc[IS_REVENUE, year] = revenue
    income.loc[IS_EBITDA, year] = ebitda
    income.loc[IS_EBIT, year] = ebit
    income.loc[IS_INTEREST, year] = interest
    income.loc[IS_PBT, year] = profit_before_tax
    income.loc[IS_TAX, year] = tax
    income.loc[IS_NET_INCOME, year] = net_income

    receivables = (assumptions.dso / DAYS_IN_YEAR) * revenue
    inventory = (assumptions.dio / DAYS_IN_YEAR) * revenue
    payables = (assumptions.dpo / DAYS_IN_YEAR) * revenue

    other_current_assets = read_item(balance, BS_OTHER_CA, previous_year)
    other_non_current_assets = read_item(balance, BS_OTHER_NCA, previous_year)
    other_current_liabilities = read_item(balance, BS_OTHER_CL, previous_year)
    other_non_current_liabilities = read_item(balance, BS_OTHER_NCL, previous_year)
    short_term_debt = read_item(balance, BS_ST_DEBT, previous_year)
    long_term_debt = read_item(balance, BS_LT_DEBT, previous_year)
    equity_capital = read_item(balance, BS_EQUITY_CAPITAL, previous_year)

    capex = revenue * (assumptions.capex_percent_rev / 100.0)
    net_ppe = opening_ppe + capex - depreciation

    dividends = max(0.0, net_income * (assumptions.dividend_payout_ratio / 100.0))
    reserves = read_item(balance, BS_RESERVES, previous_year) + net_income - dividends
    total_equity = equity_capital + reserves

    change_in_receivables = receivables - read_item(balance, BS_RECEIVABLES, previous_year)
    change_in_inventory = inventory - read_item(balance, BS_INVENTORY, previous_year)
    change_in_payables = payables - read_item(balance, BS_PAYABLES, previous_year)

    operating_cash_flow = (
        net_income
        + depreciation
        - change_in_receivables
        - change_in_inventory
        + change_in_payables
    )
    investing_cash_flow = -capex
    financing_cash_flow = -dividends
    net_cash_flow = operating_cash_flow + investing_cash_flow + financing_cash_flow

    unplugged_cash = read_item(balance, BS_CASH, previous_year) + net_cash_flow

    if unplugged_cash < 0:
        short_term_debt += abs(unplugged_cash)
        cash_balance = 0.0
    else:
        cash_balance = unplugged_cash

    total_current_assets = cash_balance + receivables + inventory + other_current_assets
    total_assets = total_current_assets + net_ppe + other_non_current_assets
    total_current_liabilities = payables + short_term_debt + other_current_liabilities
    total_liabilities = (
        total_current_liabilities + long_term_debt + other_non_current_liabilities
    )

    balance.loc[BS_CASH, year] = cash_balance
    balance.loc[BS_RECEIVABLES, year] = receivables
    balance.loc[BS_INVENTORY, year] = inventory
    balance.loc[BS_OTHER_CA, year] = other_current_assets
    balance.loc[BS_TOTAL_CA, year] = total_current_assets
    balance.loc[BS_PPE, year] = net_ppe
    balance.loc[BS_OTHER_NCA, year] = other_non_current_assets
    balance.loc[BS_TOTAL_ASSETS, year] = total_assets
    balance.loc[BS_PAYABLES, year] = payables
    balance.loc[BS_ST_DEBT, year] = short_term_debt
    balance.loc[BS_OTHER_CL, year] = other_current_liabilities
    balance.loc[BS_TOTAL_CL, year] = total_current_liabilities
    balance.loc[BS_LT_DEBT, year] = long_term_debt
    balance.loc[BS_TOTAL_DEBT, year] = short_term_debt + long_term_debt
    balance.loc[BS_OTHER_NCL, year] = other_non_current_liabilities
    balance.loc[BS_TOTAL_LIABILITIES, year] = total_liabilities
    balance.loc[BS_EQUITY_CAPITAL, year] = equity_capital
    balance.loc[BS_RESERVES, year] = reserves
    balance.loc[BS_TOTAL_EQUITY, year] = total_equity

    cash.loc[CF_OPERATING, year] = operating_cash_flow
    cash.loc[CF_INVESTING, year] = investing_cash_flow
    cash.loc[CF_FINANCING, year] = financing_cash_flow
    cash.loc[CF_CAPEX, year] = capex
    cash.loc[CF_FREE_CASH_FLOW, year] = operating_cash_flow - capex
