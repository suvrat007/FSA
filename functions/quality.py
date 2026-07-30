from typing import Any, Dict, List

import numpy as np

from functions.config import (
    BS_INVENTORY,
    BS_RECEIVABLES,
    BS_TOTAL_DEBT,
    CF_FREE_CASH_FLOW,
    CF_OPERATING,
    IS_NET_INCOME,
    IS_REVENUE,
)
from functions.datamodel import FinancialDataModel, read_item
from functions.ratios import (
    CFO_TO_NET_INCOME,
    EBITDA_MARGIN,
    INTEREST_COVERAGE,
    compute_all_ratios,
    read_ratio,
)
from functions.statements import compute_yoy_growth

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARNING = "WARNING"

RULE_COUNT = 7

CFO_QUALITY_THRESHOLD = 0.8
CFO_CRITICAL_THRESHOLD = 0.5
GROWTH_SPREAD_THRESHOLD = 10.0
GROWTH_SPREAD_CRITICAL = 20.0
DEBT_SPIKE_THRESHOLD = 20.0
INTEREST_COVER_THRESHOLD = 3.0
INTEREST_COVER_CRITICAL = 1.5


def evaluate_red_flags(model: FinancialDataModel) -> List[Dict[str, Any]]:
    if len(model.years) < 2:
        return []

    income = model.income_statement
    balance = model.balance_sheet
    cash = model.cash_flow

    latest_year = model.years[-1]
    income_growth = compute_yoy_growth(income)
    balance_growth = compute_yoy_growth(balance)
    ratios = compute_all_ratios(model)

    flags: List[Dict[str, Any]] = []

    flags.extend(_check_earnings_quality(income, cash, ratios, latest_year))
    flags.extend(
        _check_growth_divergence(
            income_growth,
            balance_growth,
            latest_year,
            BS_RECEIVABLES,
            "RF-02",
            "Accounts receivable overgrowth",
            "Receivables expanding faster than sales can indicate channel stuffing, relaxed "
            "credit terms, or difficulty collecting payment from customers.",
        )
    )
    flags.extend(
        _check_growth_divergence(
            income_growth,
            balance_growth,
            latest_year,
            BS_INVENTORY,
            "RF-03",
            "Inventory accumulation risk",
            "Inventory building faster than sales points to slowing demand, obsolescence risk, "
            "or future write-downs.",
        )
    )
    flags.extend(_check_leverage(balance_growth, ratios, latest_year))
    flags.extend(_check_free_cash_flow(cash, model.years))
    flags.extend(_check_margin_trend(ratios, model.years))
    flags.extend(_check_balance_integrity(model))

    return flags


def _build_flag(
    rule_id: str,
    rule_name: str,
    severity: str,
    observation: str,
    finance_reason: str,
) -> Dict[str, Any]:
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "severity": severity,
        "observation": observation,
        "finance_reason": finance_reason,
    }


def _check_earnings_quality(income, cash, ratios, year: str) -> List[Dict[str, Any]]:
    net_income = read_item(income, IS_NET_INCOME, year)
    cfo = read_item(cash, CF_OPERATING, year)
    cfo_ratio = read_ratio(ratios, CFO_TO_NET_INCOME, year)

    if net_income <= 0 or np.isnan(cfo_ratio) or cfo_ratio >= CFO_QUALITY_THRESHOLD:
        return []

    severity = SEVERITY_CRITICAL if cfo_ratio < CFO_CRITICAL_THRESHOLD else SEVERITY_WARNING

    return [
        _build_flag(
            "RF-01",
            "Low earnings quality (CFO below net income)",
            severity,
            f"In {year} net income was {net_income:,.1f} while operating cash flow was "
            f"{cfo:,.1f}, a CFO to net income ratio of {cfo_ratio:.2f}x.",
            "Strong reported profit with weak operating cash flow suggests aggressive revenue "
            "recognition, uncollected accruals, or earnings that are not converting into cash.",
        )
    ]


def _check_growth_divergence(
    income_growth,
    balance_growth,
    year: str,
    balance_item: str,
    rule_id: str,
    rule_name: str,
    finance_reason: str,
) -> List[Dict[str, Any]]:
    if IS_REVENUE not in income_growth.index or balance_item not in balance_growth.index:
        return []

    revenue_growth = income_growth.loc[IS_REVENUE, year]
    item_growth = balance_growth.loc[balance_item, year]

    if np.isnan(revenue_growth) or np.isnan(item_growth):
        return []

    spread = item_growth - revenue_growth

    if spread <= GROWTH_SPREAD_THRESHOLD or item_growth <= GROWTH_SPREAD_THRESHOLD:
        return []

    severity = SEVERITY_CRITICAL if spread > GROWTH_SPREAD_CRITICAL else SEVERITY_WARNING

    return [
        _build_flag(
            rule_id,
            rule_name,
            severity,
            f"In {year} {balance_item.lower()} grew {item_growth:+.1f}% year on year against "
            f"revenue growth of {revenue_growth:+.1f}%, a spread of {spread:+.1f} percentage points.",
            finance_reason,
        )
    ]


def _check_leverage(balance_growth, ratios, year: str) -> List[Dict[str, Any]]:
    if BS_TOTAL_DEBT not in balance_growth.index:
        return []

    debt_growth = balance_growth.loc[BS_TOTAL_DEBT, year]
    coverage = read_ratio(ratios, INTEREST_COVERAGE, year)

    if np.isnan(debt_growth) or np.isnan(coverage):
        return []

    if debt_growth <= DEBT_SPIKE_THRESHOLD or coverage >= INTEREST_COVER_THRESHOLD:
        return []

    severity = SEVERITY_CRITICAL if coverage < INTEREST_COVER_CRITICAL else SEVERITY_WARNING

    return [
        _build_flag(
            "RF-04",
            "Leverage spike with weak debt coverage",
            severity,
            f"Total debt rose {debt_growth:+.1f}% in {year} while interest coverage fell to "
            f"{coverage:.2f}x.",
            "Rapid debt expansion combined with weak interest coverage raises solvency risk and "
            "exposure to rising interest rates.",
        )
    ]


def _check_free_cash_flow(cash, years: List[str]) -> List[Dict[str, Any]]:
    if CF_FREE_CASH_FLOW not in cash.index:
        return []

    recent_years = years[-3:]
    deficit_years = [year for year in recent_years if read_item(cash, CF_FREE_CASH_FLOW, year) < 0]

    if len(deficit_years) < 2:
        return []

    return [
        _build_flag(
            "RF-05",
            "Persistent free cash flow deficit",
            SEVERITY_CRITICAL,
            f"Free cash flow was negative in {len(deficit_years)} of the last "
            f"{len(recent_years)} periods ({', '.join(deficit_years)}).",
            "Sustained negative free cash flow forces reliance on external debt or equity "
            "issuance to fund operations and capital expenditure.",
        )
    ]


def _check_margin_trend(ratios, years: List[str]) -> List[Dict[str, Any]]:
    if EBITDA_MARGIN not in ratios.index or len(years) < 3:
        return []

    margins = [read_ratio(ratios, EBITDA_MARGIN, year) for year in years[-3:]]

    if any(np.isnan(margin) for margin in margins):
        return []

    if not margins[0] > margins[1] > margins[2]:
        return []

    return [
        _build_flag(
            "RF-06",
            "Consecutive margin compression",
            SEVERITY_WARNING,
            f"EBITDA margin contracted across three consecutive periods: {margins[0]:.1f}%, "
            f"{margins[1]:.1f}%, {margins[2]:.1f}%.",
            "Sustained margin erosion indicates pricing pressure, cost inflation, or an eroding "
            "competitive position.",
        )
    ]


def _check_balance_integrity(model: FinancialDataModel) -> List[Dict[str, Any]]:
    return [
        _build_flag(
            "RF-07",
            "Balance sheet imbalance",
            SEVERITY_CRITICAL,
            warning,
            "The accounting identity requires total assets to equal total liabilities plus total "
            "equity. An imbalance points to a parsing error or unrecorded line items.",
        )
        for warning in model.validate_integrity()
    ]
