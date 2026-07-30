from typing import Dict

from functions.ratios import (
    CCC,
    CFO_TO_NET_INCOME,
    CURRENT_RATIO,
    DEBT_TO_EQUITY,
    EBITDA_MARGIN,
    INTEREST_COVERAGE,
    ROCE,
    ROE,
)

FORECAST_MODEL_TOPIC = "3-Statement Forecast Model"
ASSESSMENT_TOPIC = "Assessment and Verdict Engine"
PROVENANCE_TOPIC = "Data Provenance and Assumptions"
COMPARISON_TOPIC = "Comparison and Industry Positioning"

METHODOLOGY_REGISTRY: Dict[str, Dict[str, str]] = {
    EBITDA_MARGIN: {
        "title": "EBITDA Margin",
        "category": "Profitability",
        "formula": "EBITDA Margin = (EBITDA / Revenue) * 100",
        "finance_concept": (
            "EBITDA margin measures core operating profitability before interest, tax, and "
            "non-cash charges. It shows how efficiently revenue is converted into operating "
            "earnings, independent of capital structure and depreciation policy."
        ),
        "interpretation": (
            "A higher margin signals pricing power and operational efficiency. Tracking the "
            "margin over time reveals whether operating leverage or cost inflation dominates."
        ),
        "implementation": (
            "Computed in functions/ratios.py from the EBITDA and Revenue rows of the normalized "
            "income statement using safe_divide, which returns NaN rather than raising when "
            "revenue is zero or missing."
        ),
        "data_source": (
            "yfinance financials or a Screener.in export, normalized into "
            "FinancialDataModel.income_statement."
        ),
    },
    ROE: {
        "title": "Return on Equity",
        "category": "Profitability",
        "formula": "ROE = (Net Income / Total Shareholders Equity) * 100",
        "finance_concept": (
            "Return on equity measures how effectively management generates profit from "
            "shareholder capital. It is the headline measure of shareholder value creation."
        ),
        "interpretation": (
            "An ROE above 15 to 20 percent is generally strong for Indian corporates. DuPont "
            "analysis decomposes it into net margin, asset turnover, and financial leverage."
        ),
        "implementation": (
            "Computed in functions/ratios.py from Net Income on the income statement and Total "
            "Shareholders Equity on the balance sheet."
        ),
        "data_source": (
            "Income statement net profit after tax and balance sheet share capital plus reserves."
        ),
    },
    ROCE: {
        "title": "Return on Capital Employed",
        "category": "Profitability",
        "formula": "ROCE = (EBIT / Capital Employed) * 100, Capital Employed = Total Assets - Current Liabilities",
        "finance_concept": (
            "ROCE measures the operating return generated for all capital providers, both debt "
            "and equity. Unlike ROE it is neutral to capital structure."
        ),
        "interpretation": (
            "ROCE must exceed the weighted average cost of capital for the business to create "
            "economic value."
        ),
        "implementation": (
            "Computed in functions/ratios.py. Capital employed falls back to total debt plus "
            "total equity when assets less current liabilities is not positive."
        ),
        "data_source": "Balance sheet total assets and current liabilities, income statement EBIT.",
    },
    CURRENT_RATIO: {
        "title": "Current Ratio",
        "category": "Liquidity",
        "formula": "Current Ratio = Total Current Assets / Total Current Liabilities",
        "finance_concept": (
            "The current ratio measures the ability to meet obligations due within twelve months "
            "using short-term assets."
        ),
        "interpretation": (
            "Above 1.5x indicates healthy short-term liquidity. Below 1.0x indicates potential "
            "distress, while a very high ratio may signal idle capital."
        ),
        "implementation": (
            "Computed in functions/ratios.py using safe_divide over the balance sheet current "
            "asset and current liability totals."
        ),
        "data_source": "FinancialDataModel.balance_sheet current asset and liability subtotals.",
    },
    DEBT_TO_EQUITY: {
        "title": "Debt-to-Equity Ratio",
        "category": "Solvency and Leverage",
        "formula": "Debt-to-Equity = Total Debt / Total Shareholders Equity",
        "finance_concept": (
            "Debt-to-equity evaluates financial leverage by comparing interest-bearing debt to "
            "shareholder capital."
        ),
        "interpretation": (
            "Leverage amplifies returns in expansions and losses in downturns. Capital-intensive "
            "sectors sustain higher ratios than asset-light services businesses."
        ),
        "implementation": (
            "Computed in functions/ratios.py. Total debt is short-term plus long-term debt, "
            "derived in the loaders when the source data does not report it directly."
        ),
        "data_source": "Balance sheet debt lines, share capital, and reserves.",
    },
    INTEREST_COVERAGE: {
        "title": "Interest Coverage Ratio",
        "category": "Solvency and Leverage",
        "formula": "Interest Coverage = EBIT / Interest Expense",
        "finance_concept": (
            "Interest coverage assesses how comfortably operating earnings service the interest "
            "charge on outstanding debt."
        ),
        "interpretation": (
            "Above 3.0x is comfortable. Below 1.5x signals vulnerability and downgrade risk."
        ),
        "implementation": (
            "Computed in functions/ratios.py and consumed by rule RF-04 in functions/quality.py."
        ),
        "data_source": "Income statement EBIT and interest expense.",
    },
    CCC: {
        "title": "Cash Conversion Cycle",
        "category": "Efficiency and Working Capital",
        "formula": "CCC = DIO + DSO - DPO",
        "finance_concept": (
            "The cash conversion cycle measures the days between paying suppliers for inventory "
            "and collecting cash from customers."
        ),
        "interpretation": (
            "A short or negative cycle means suppliers finance operations and little capital is "
            "locked in working capital."
        ),
        "implementation": (
            "Computed in functions/ratios.py. DSO uses receivables over revenue; DIO and DPO use "
            "an assumed cost of goods ratio of 0.70 applied to revenue, since a separate COGS "
            "line is not always available in the source data."
        ),
        "data_source": "Income statement revenue with balance sheet receivables, inventory, and payables.",
    },
    CFO_TO_NET_INCOME: {
        "title": "Operating Cash Flow to Net Income",
        "category": "Cash Flow Quality",
        "formula": "CFO / Net Income = Cash Flow from Operations / Net Income",
        "finance_concept": (
            "This quality-of-earnings measure tests whether reported accounting profit is backed "
            "by cash generated from core operations."
        ),
        "interpretation": (
            "Above 1.0x indicates cash-generative earnings. Persistently below 0.8x warns of "
            "aggressive revenue recognition or working capital absorption."
        ),
        "implementation": (
            "Computed in functions/ratios.py and used by rule RF-01 in functions/quality.py."
        ),
        "data_source": "Cash flow statement operating cash flow and income statement net income.",
    },
    FORECAST_MODEL_TOPIC: {
        "title": "Linked 3-Statement Forecast and Balancing Plug",
        "category": "Financial Modeling",
        "formula": "Total Assets = Total Liabilities + Total Shareholders Equity",
        "finance_concept": (
            "A 3-statement model projects the income statement, balance sheet, and cash flow "
            "statement forward from a shared set of operating drivers so that every projected "
            "period remains internally consistent."
        ),
        "interpretation": (
            "The output supports valuation, debt capacity assessment, dividend sustainability "
            "testing, and scenario analysis."
        ),
        "implementation": (
            "Implemented in functions/forecast.py. Each period projects income statement lines "
            "from the drivers, working capital from DSO, DIO, and DPO, the PP&E schedule from "
            "capex and depreciation, retained earnings from net income less dividends, and then "
            "the cash flow statement. Any residual funding gap is absorbed by short-term debt so "
            "the balance sheet identity holds exactly."
        ),
        "data_source": (
            "The final historical period of FinancialDataModel acts as the opening balance, "
            "combined with the driver values in ForecastAssumptions."
        ),
    },
    ASSESSMENT_TOPIC: {
        "title": "Assessment and Verdict Engine",
        "category": "Interpretation",
        "formula": "Dimension score = mean(metric scores); Overall = weighted mean less findings penalty",
        "finance_concept": (
            "Ratios on their own do not answer whether a company is sound. The assessment engine "
            "scores each ratio against a benchmark band, averages the scores within a dimension, "
            "then combines the dimensions using fixed weights: solvency and profitability carry "
            "the most weight, cash flow quality next, then liquidity and efficiency."
        ),
        "interpretation": (
            "Scores above 75 are strong, above 55 adequate, above 35 weak, and below that "
            "critical. Trend compares the dimension score in the earliest of the last three "
            "periods against the latest, so a company can be adequate today yet deteriorating."
        ),
        "implementation": (
            "Implemented in functions/assessment.py. Each Benchmark carries strong, adequate, and "
            "weak thresholds plus a direction flag, and scoring interpolates the observed value "
            "across those breakpoints onto a 0 to 100 scale. Critical forensic findings subtract "
            "6 points each and advisory findings 2, capped at 18."
        ),
        "data_source": (
            "The ratio table produced by functions/ratios.py plus the findings produced by "
            "functions/quality.py, both derived from the active FinancialDataModel."
        ),
    },
    PROVENANCE_TOPIC: {
        "title": "Data Provenance and Assumptions",
        "category": "Data Integrity",
        "formula": "Every standard line item is tagged Reported, Derived, or Not available",
        "finance_concept": (
            "An analysis is only as trustworthy as the data beneath it. Sources differ in what "
            "they report: Yahoo Finance omits EBITDA for many companies, Screener exports do not "
            "isolate capital expenditure, and uploaded spreadsheets carry whatever the author "
            "chose to include."
        ),
        "interpretation": (
            "Reported means the source supplied the figure directly. Derived means the platform "
            "computed it from other lines and states how. Not available means no value exists and "
            "the item is held at zero, which makes any dependent ratio read as not available "
            "rather than as a misleading number."
        ),
        "implementation": (
            "Each loader records a provenance map and a list of caveats on the FinancialDataModel. "
            "Loaders return a LoadResult and never substitute demonstration data when a source "
            "fails, so a failed fetch surfaces as an error rather than as another company's "
            "figures."
        ),
        "data_source": (
            "Populated by functions/loader_yfinance.py, functions/loader_screener.py, "
            "functions/loader_upload.py, and functions/mock_data.py."
        ),
    },
    COMPARISON_TOPIC: {
        "title": "Comparison and Industry Positioning",
        "category": "Benchmarking",
        "formula": "Percentile = 100 x (count below + 0.5 x count equal) / cohort size",
        "finance_concept": (
            "A ratio is only meaningful against a reference. The comparison module measures a "
            "company against a set the user assembles; the industry module measures it against a "
            "curated cohort of listed peers and against its closest direct competitors."
        ),
        "interpretation": (
            "Percentiles are oriented so higher is always better, including for metrics such as "
            "debt to equity and the cash conversion cycle where a lower raw value is preferable. "
            "A percentile of 50 means the company matches the cohort median."
        ),
        "implementation": (
            "Implemented in functions/comparison.py with the cohort definitions in "
            "functions/sectors.py. Fetches are cached for one hour by functions/caching.py, and "
            "cohort members that fail to load are excluded from the median with a warning rather "
            "than silently replaced."
        ),
        "data_source": (
            "Any mix of Yahoo Finance tickers, uploaded spreadsheets, and bundled datasets held "
            "in the session company library."
        ),
    },
}
