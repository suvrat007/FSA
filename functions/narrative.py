from typing import Dict, List

import numpy as np

from functions.assessment import assess_company
from functions.config import IS_NET_INCOME, IS_REVENUE
from functions.datamodel import FinancialDataModel, read_item
from functions.quality import SEVERITY_CRITICAL, evaluate_red_flags
from functions.ratios import (
    CURRENT_RATIO,
    DEBT_TO_EQUITY,
    EBITDA_MARGIN,
    INTEREST_COVERAGE,
    ROCE,
    ROE,
    compute_all_ratios,
    read_ratio,
)
from functions.statements import compute_cagr

SECTION_SUMMARY = "Executive Summary"
SECTION_PROFITABILITY = "Profitability and Returns"
SECTION_SOLVENCY = "Solvency and Liquidity"
SECTION_FORENSIC = "Accounting Quality"
SECTION_VERDICT = "Verdict"
SECTION_CONCLUSION = "Conclusion"

SECTION_ORDER: List[str] = [
    SECTION_SUMMARY,
    SECTION_PROFITABILITY,
    SECTION_SOLVENCY,
    SECTION_FORENSIC,
    SECTION_VERDICT,
    SECTION_CONCLUSION,
]

STRONG_ROE_THRESHOLD = 15.0
CONSERVATIVE_LEVERAGE_THRESHOLD = 1.0
COMFORTABLE_COVERAGE_THRESHOLD = 3.0


def generate_executive_narrative(model: FinancialDataModel) -> Dict[str, str]:
    if not model.years:
        return {SECTION_SUMMARY: "Insufficient data is available to generate a narrative."}

    latest_year = model.years[-1]
    income = model.income_statement
    ratios = compute_all_ratios(model)
    red_flags = evaluate_red_flags(model)

    assessment = assess_company(model)

    return {
        SECTION_SUMMARY: _summary_section(model, income, latest_year),
        SECTION_PROFITABILITY: _profitability_section(ratios, latest_year),
        SECTION_SOLVENCY: _solvency_section(ratios, latest_year),
        SECTION_FORENSIC: _forensic_section(red_flags),
        SECTION_VERDICT: _verdict_section(assessment),
        SECTION_CONCLUSION: _conclusion_section(model, ratios, latest_year),
    }


def _verdict_section(assessment) -> str:
    dimension_text = "; ".join(
        f"{dimension.name.lower()} {dimension.grade.lower()}"
        for dimension in assessment.dimensions
        if dimension.applicable
    )

    if not dimension_text:
        return assessment.verdict

    return f"{assessment.verdict} By dimension: {dimension_text}."


def _summary_section(model: FinancialDataModel, income, latest_year: str) -> str:
    revenue = read_item(income, IS_REVENUE, latest_year)
    net_income = read_item(income, IS_NET_INCOME, latest_year)

    revenue_cagr = np.nan
    if IS_REVENUE in income.index and len(model.years) >= 3:
        revenue_cagr = compute_cagr(income.loc[IS_REVENUE])

    trajectory = (
        f"a compound annual revenue growth rate of {revenue_cagr:+.1f}% across the historical window"
        if not np.isnan(revenue_cagr)
        else "a revenue trajectory measured across the available historical periods"
    )

    return (
        f"{model.company_name} ({model.ticker}) reported revenue of {revenue:,.1f} and net income "
        f"of {net_income:,.1f} in {latest_year}. The company operates in the "
        f"{model.metadata.get('Sector', 'unclassified')} sector "
        f"({model.metadata.get('Industry', 'unclassified')}), and the historical record shows "
        f"{trajectory}."
    )


def _profitability_section(ratios, latest_year: str) -> str:
    ebitda_margin = read_ratio(ratios, EBITDA_MARGIN, latest_year)
    roe = read_ratio(ratios, ROE, latest_year)
    roce = read_ratio(ratios, ROCE, latest_year)

    return (
        f"Operating profitability in {latest_year} stands at an EBITDA margin of "
        f"{_value_text(ebitda_margin, '%')}. Shareholder returns are reflected in a return on "
        f"equity of {_value_text(roe, '%')} and a return on capital employed of "
        f"{_value_text(roce, '%')}. Return on capital employed indicates how efficiently the "
        f"business converts total invested capital into operating profit."
    )


def _solvency_section(ratios, latest_year: str) -> str:
    current_ratio = read_ratio(ratios, CURRENT_RATIO, latest_year)
    debt_to_equity = read_ratio(ratios, DEBT_TO_EQUITY, latest_year)
    coverage = read_ratio(ratios, INTEREST_COVERAGE, latest_year)

    coverage_comment = (
        "Interest coverage provides a comfortable debt service cushion."
        if not np.isnan(coverage) and coverage > COMFORTABLE_COVERAGE_THRESHOLD
        else "Interest coverage warrants continued monitoring."
    )

    return (
        f"Short-term liquidity is supported by a current ratio of {_value_text(current_ratio, 'x')}. "
        f"The capital structure carries a debt-to-equity ratio of "
        f"{_value_text(debt_to_equity, 'x')}, with operating earnings covering interest "
        f"{_value_text(coverage, 'x')} over. {coverage_comment}"
    )


def _forensic_section(red_flags: List[Dict[str, str]]) -> str:
    if not red_flags:
        return (
            "The forensic rule set produced no findings. Reported earnings, working capital "
            "movements, leverage, and the balance sheet identity are all within expected bounds."
        )

    critical = sum(1 for flag in red_flags if flag["severity"] == SEVERITY_CRITICAL)
    warnings = len(red_flags) - critical

    return (
        f"The forensic rule set produced {len(red_flags)} finding(s): {critical} critical and "
        f"{warnings} advisory. Each finding is listed in full with its accounting rationale in "
        f"the accounting quality section of the report."
    )


def _conclusion_section(model: FinancialDataModel, ratios, latest_year: str) -> str:
    roe = read_ratio(ratios, ROE, latest_year)
    debt_to_equity = read_ratio(ratios, DEBT_TO_EQUITY, latest_year)

    is_robust = (
        not np.isnan(roe)
        and not np.isnan(debt_to_equity)
        and roe > STRONG_ROE_THRESHOLD
        and debt_to_equity < CONSERVATIVE_LEVERAGE_THRESHOLD
    )

    return (
        f"On the evidence above, {model.company_name} presents a "
        f"{'robust' if is_robust else 'moderate'} financial risk profile. Working capital trends "
        f"and cash conversion remain the primary items to track in subsequent reporting periods."
    )


def _value_text(value: float, suffix: str) -> str:
    if value is None or np.isnan(value):
        return "not available"

    return f"{value:.2f}{suffix}"
