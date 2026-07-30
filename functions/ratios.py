from typing import Dict, List

import numpy as np
import pandas as pd

from functions.config import (
    BS_CASH,
    BS_INVENTORY,
    BS_PAYABLES,
    BS_RECEIVABLES,
    BS_TOTAL_ASSETS,
    BS_TOTAL_CA,
    BS_TOTAL_CL,
    BS_TOTAL_DEBT,
    BS_TOTAL_EQUITY,
    CF_CAPEX,
    CF_FREE_CASH_FLOW,
    CF_OPERATING,
    IS_EBIT,
    IS_EBITDA,
    IS_INTEREST,
    IS_NET_INCOME,
    IS_REVENUE,
)
from functions.datamodel import FinancialDataModel, read_item
from functions.formatting import safe_divide
from functions.sectors import MODEL_FINANCIAL, classify_business_model

ASSUMED_COGS_RATIO = 0.70
DAYS_IN_YEAR = 365.0

COGS_ASSUMPTION_NOTE = (
    f"Cost of goods sold is not carried as a separate line by the supported data sources, so "
    f"inventory and payables day counts assume COGS equals {ASSUMED_COGS_RATIO:.0%} of revenue. "
    f"Days inventory outstanding, days payables outstanding, the cash conversion cycle, and "
    f"inventory turnover are therefore approximations rather than reported figures."
)

EBITDA_MARGIN = "EBITDA Margin (%)"
EBIT_MARGIN = "EBIT Margin (%)"
NET_MARGIN = "Net Profit Margin (%)"
ROA = "Return on Assets - ROA (%)"
ROE = "Return on Equity - ROE (%)"
ROCE = "Return on Capital Employed - ROCE (%)"

CURRENT_RATIO = "Current Ratio (x)"
QUICK_RATIO = "Quick Ratio (x)"
CASH_RATIO = "Cash Ratio (x)"

DEBT_TO_EQUITY = "Debt-to-Equity (x)"
DEBT_TO_ASSETS = "Debt-to-Assets (x)"
INTEREST_COVERAGE = "Interest Coverage (x)"
NET_DEBT_TO_EBITDA = "Net Debt / EBITDA (x)"

ASSET_TURNOVER = "Asset Turnover (x)"
INVENTORY_TURNOVER = "Inventory Turnover (x)"
RECEIVABLES_TURNOVER = "Receivables Turnover (x)"
DSO = "Days Sales Outstanding - DSO (days)"
DIO = "Days Inventory Outstanding - DIO (days)"
DPO = "Days Payables Outstanding - DPO (days)"
CCC = "Cash Conversion Cycle - CCC (days)"

CFO_TO_NET_INCOME = "CFO / Net Income (x)"
FCF_TO_REVENUE = "FCF / Revenue (%)"
CAPEX_INTENSITY = "Capex Intensity (%)"

RATIO_GROUPS: Dict[str, List[str]] = {
    "Profitability and Returns": [EBITDA_MARGIN, EBIT_MARGIN, NET_MARGIN, ROA, ROE, ROCE],
    "Liquidity": [CURRENT_RATIO, QUICK_RATIO, CASH_RATIO],
    "Solvency and Capital Structure": [
        DEBT_TO_EQUITY,
        DEBT_TO_ASSETS,
        INTEREST_COVERAGE,
        NET_DEBT_TO_EBITDA,
    ],
    "Efficiency and Working Capital": [
        ASSET_TURNOVER,
        INVENTORY_TURNOVER,
        RECEIVABLES_TURNOVER,
        DSO,
        DIO,
        DPO,
        CCC,
    ],
    "Cash Flow Quality": [CFO_TO_NET_INCOME, FCF_TO_REVENUE, CAPEX_INTENSITY],
}

RATIO_GROUPS_FLAT = [name for group in RATIO_GROUPS.values() for name in group]

APPROXIMATED_RATIOS = {INVENTORY_TURNOVER, DIO, DPO, CCC}

NOT_MEANINGFUL_FOR_FINANCIALS = {
    CURRENT_RATIO,
    QUICK_RATIO,
    CASH_RATIO,
    INVENTORY_TURNOVER,
    RECEIVABLES_TURNOVER,
    DSO,
    DIO,
    DPO,
    CCC,
    EBITDA_MARGIN,
    NET_DEBT_TO_EBITDA,
}

FINANCIAL_SUPPRESSION_NOTE = (
    "Working capital, inventory, and EBITDA-based ratios are suppressed for banks and financial "
    "institutions. A lender has no operating cycle in the manufacturing sense, and interest is "
    "revenue rather than a financing cost, so these measures would be arithmetically valid but "
    "economically meaningless."
)


def compute_all_ratios(model: FinancialDataModel) -> pd.DataFrame:
    if not model.years:
        return pd.DataFrame()

    columns = {
        year: _compute_year_ratios(
            model.income_statement, model.balance_sheet, model.cash_flow, year
        )
        for year in model.years
    }

    ratios = pd.DataFrame(columns, columns=model.years).round(2)

    if classify_business_model(model) == MODEL_FINANCIAL:
        suppressed = [name for name in NOT_MEANINGFUL_FOR_FINANCIALS if name in ratios.index]
        ratios.loc[suppressed] = np.nan

    return ratios


def suppressed_ratios(model: FinancialDataModel) -> List[str]:
    if classify_business_model(model) != MODEL_FINANCIAL:
        return []

    return [name for name in RATIO_GROUPS_FLAT if name in NOT_MEANINGFUL_FOR_FINANCIALS]


def _compute_year_ratios(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cash: pd.DataFrame,
    year: str,
) -> Dict[str, float]:
    revenue = read_item(income, IS_REVENUE, year)
    ebitda = read_item(income, IS_EBITDA, year)
    ebit = read_item(income, IS_EBIT, year)
    interest = read_item(income, IS_INTEREST, year)
    net_income = read_item(income, IS_NET_INCOME, year)

    cash_balance = read_item(balance, BS_CASH, year)
    receivables = read_item(balance, BS_RECEIVABLES, year)
    inventory = read_item(balance, BS_INVENTORY, year)
    current_assets = read_item(balance, BS_TOTAL_CA, year)
    total_assets = read_item(balance, BS_TOTAL_ASSETS, year)
    payables = read_item(balance, BS_PAYABLES, year)
    current_liabilities = read_item(balance, BS_TOTAL_CL, year)
    total_debt = read_item(balance, BS_TOTAL_DEBT, year)
    total_equity = read_item(balance, BS_TOTAL_EQUITY, year)

    cfo = read_item(cash, CF_OPERATING, year)
    capex = read_item(cash, CF_CAPEX, year)
    free_cash_flow = read_item(cash, CF_FREE_CASH_FLOW, year, default=cfo - capex)

    capital_employed = total_assets - current_liabilities
    if capital_employed <= 0:
        capital_employed = total_debt + total_equity

    cost_of_goods = revenue * ASSUMED_COGS_RATIO

    days_sales = safe_divide(receivables, revenue) * DAYS_IN_YEAR
    days_inventory = safe_divide(inventory, cost_of_goods) * DAYS_IN_YEAR
    days_payables = safe_divide(payables, cost_of_goods) * DAYS_IN_YEAR
    conversion_cycle = days_inventory + days_sales - days_payables

    return {
        EBITDA_MARGIN: safe_divide(ebitda, revenue) * 100.0,
        EBIT_MARGIN: safe_divide(ebit, revenue) * 100.0,
        NET_MARGIN: safe_divide(net_income, revenue) * 100.0,
        ROA: safe_divide(net_income, total_assets) * 100.0,
        ROE: safe_divide(net_income, total_equity) * 100.0,
        ROCE: safe_divide(ebit, capital_employed) * 100.0,
        CURRENT_RATIO: safe_divide(current_assets, current_liabilities),
        QUICK_RATIO: safe_divide(current_assets - inventory, current_liabilities),
        CASH_RATIO: safe_divide(cash_balance, current_liabilities),
        DEBT_TO_EQUITY: safe_divide(total_debt, total_equity),
        DEBT_TO_ASSETS: safe_divide(total_debt, total_assets),
        INTEREST_COVERAGE: safe_divide(ebit, interest),
        NET_DEBT_TO_EBITDA: safe_divide(total_debt - cash_balance, ebitda),
        ASSET_TURNOVER: safe_divide(revenue, total_assets),
        INVENTORY_TURNOVER: safe_divide(cost_of_goods, inventory),
        RECEIVABLES_TURNOVER: safe_divide(revenue, receivables),
        DSO: days_sales,
        DIO: days_inventory,
        DPO: days_payables,
        CCC: conversion_cycle,
        CFO_TO_NET_INCOME: safe_divide(cfo, net_income),
        FCF_TO_REVENUE: safe_divide(free_cash_flow, revenue) * 100.0,
        CAPEX_INTENSITY: safe_divide(abs(capex), revenue) * 100.0,
    }


def read_ratio(ratios: pd.DataFrame, ratio_name: str, year: str) -> float:
    if ratios.empty or ratio_name not in ratios.index or year not in ratios.columns:
        return np.nan

    return float(ratios.loc[ratio_name, year])
