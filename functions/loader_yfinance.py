import logging
from typing import Dict, List, Set, Tuple

import pandas as pd
import yfinance as yf

from functions.config import (
    BS_CASH,
    BS_EQUITY_CAPITAL,
    BS_INVENTORY,
    BS_LT_DEBT,
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
from functions.datamodel import (
    DERIVED,
    MISSING,
    REPORTED,
    STANDARD_BS_ITEMS,
    STANDARD_CF_ITEMS,
    STANDARD_IS_ITEMS,
    STATUS_EMPTY,
    STATUS_ERROR,
    FinancialDataModel,
    LoadResult,
    build_provenance,
    create_empty_statement,
)

logger = logging.getLogger(__name__)

SOURCE_LABEL = "Yahoo Finance"
EBITDA_FALLBACK_MULTIPLE = 1.15
BASE_UNIT_DIVISOR = 1e7

INCOME_STATEMENT_MAP: Dict[str, str] = {
    "Total Revenue": IS_REVENUE,
    "Operating Revenue": IS_REVENUE,
    "EBITDA": IS_EBITDA,
    "Normalized EBITDA": IS_EBITDA,
    "EBIT": IS_EBIT,
    "Operating Income": IS_EBIT,
    "Interest Expense": IS_INTEREST,
    "Interest Expense Non Operating": IS_INTEREST,
    "Pretax Income": IS_PBT,
    "Tax Provision": IS_TAX,
    "Net Income": IS_NET_INCOME,
    "Net Income Common Stockholders": IS_NET_INCOME,
}

BALANCE_SHEET_MAP: Dict[str, str] = {
    "Cash And Cash Equivalents": BS_CASH,
    "Receivables": BS_RECEIVABLES,
    "Accounts Receivable": BS_RECEIVABLES,
    "Inventory": BS_INVENTORY,
    "Current Assets": BS_TOTAL_CA,
    "Net PPE": BS_PPE,
    "Total Assets": BS_TOTAL_ASSETS,
    "Accounts Payable": BS_PAYABLES,
    "Current Debt": BS_ST_DEBT,
    "Current Liabilities": BS_TOTAL_CL,
    "Long Term Debt": BS_LT_DEBT,
    "Total Debt": BS_TOTAL_DEBT,
    "Total Liabilities Net Minority Interest": BS_TOTAL_LIABILITIES,
    "Stockholders Equity": BS_TOTAL_EQUITY,
    "Capital Stock": BS_EQUITY_CAPITAL,
    "Retained Earnings": BS_RESERVES,
}

CASH_FLOW_MAP: Dict[str, str] = {
    "Operating Cash Flow": CF_OPERATING,
    "Investing Cash Flow": CF_INVESTING,
    "Financing Cash Flow": CF_FINANCING,
    "Capital Expenditure": CF_CAPEX,
    "Free Cash Flow": CF_FREE_CASH_FLOW,
}


def load_yfinance_data(ticker_symbol: str) -> LoadResult:
    ticker_clean = ticker_symbol.strip().upper()

    if not ticker_clean:
        return LoadResult.failure(STATUS_EMPTY, "No ticker symbol was supplied.", SOURCE_LABEL)

    try:
        ticker = yf.Ticker(ticker_clean)
        info = ticker.info or {}

        income_raw = ticker.financials
        balance_raw = ticker.balance_sheet
        cash_raw = ticker.cashflow

        if _is_unusable(income_raw) or _is_unusable(balance_raw):
            return LoadResult.failure(
                STATUS_EMPTY,
                f"Yahoo Finance returned no financial statements for {ticker_clean}. "
                f"The symbol may be delisted, unsupported, or misspelled.",
                SOURCE_LABEL,
            )

        income_raw, balance_raw, cash_raw, years = _align_periods(income_raw, balance_raw, cash_raw)

        income, income_reported = _map_income_statement(income_raw, years)
        balance, balance_reported = _map_balance_sheet(balance_raw, years)
        cash, cash_reported = _map_cash_flow(cash_raw, years)

        derived = _collect_derived(income, balance, cash, income_reported, balance_reported, cash_reported)
        reported = income_reported | balance_reported | cash_reported

        provenance = _build_provenance(income, balance, cash, reported, derived)
        caveats = _build_caveats(ticker_clean, derived, provenance)

        model = FinancialDataModel(
            company_name=info.get("longName") or info.get("shortName") or ticker_clean,
            ticker=ticker_clean,
            currency=info.get("currency", "INR"),
            years=years,
            income_statement=income,
            balance_sheet=balance,
            cash_flow=cash,
            market_data=_extract_market_data(info, ticker),
            metadata=_extract_metadata(info),
            provenance=provenance,
            caveats=caveats,
        )

        return LoadResult.success(model, SOURCE_LABEL)

    except Exception as error:
        logger.warning("yfinance fetch failed for %s (%s).", ticker_clean, error)
        return LoadResult.failure(
            STATUS_ERROR,
            f"The request for {ticker_clean} failed: {error}",
            SOURCE_LABEL,
        )


def _is_unusable(df: pd.DataFrame) -> bool:
    return df is None or df.empty


def _align_periods(
    income_raw: pd.DataFrame,
    balance_raw: pd.DataFrame,
    cash_raw: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    ordered_columns = sorted(income_raw.columns, key=pd.to_datetime)
    years = [f"FY{pd.to_datetime(column).year % 100:02d}" for column in ordered_columns]

    income_raw = income_raw.reindex(columns=ordered_columns)
    balance_raw = balance_raw.reindex(columns=ordered_columns)
    cash_raw = (
        cash_raw.reindex(columns=ordered_columns)
        if not _is_unusable(cash_raw)
        else pd.DataFrame(columns=ordered_columns)
    )

    return income_raw, balance_raw, cash_raw, years


def _apply_mapping(
    raw_df: pd.DataFrame,
    mapping: Dict[str, str],
    standard_items: List[str],
    years: List[str],
) -> Tuple[pd.DataFrame, Set[str]]:
    target = create_empty_statement(standard_items, years)
    reported: Set[str] = set()

    if _is_unusable(raw_df):
        return target, reported

    raw_df = raw_df.copy()
    raw_df.index = [str(index).strip() for index in raw_df.index]

    for source_key, standard_key in mapping.items():
        if source_key not in raw_df.index or standard_key in reported:
            continue

        values = pd.to_numeric(raw_df.loc[source_key], errors="coerce").fillna(0.0).values

        if len(values) == len(years) and target.loc[standard_key].abs().sum() == 0:
            target.loc[standard_key] = values / BASE_UNIT_DIVISOR
            reported.add(standard_key)

    return target, reported


def _map_income_statement(raw_df: pd.DataFrame, years: List[str]) -> Tuple[pd.DataFrame, Set[str]]:
    income, reported = _apply_mapping(raw_df, INCOME_STATEMENT_MAP, STANDARD_IS_ITEMS, years)

    if IS_EBITDA not in reported and income.loc[IS_EBIT].abs().sum() > 0:
        income.loc[IS_EBITDA] = income.loc[IS_EBIT] * EBITDA_FALLBACK_MULTIPLE

    return income, reported


def _map_balance_sheet(raw_df: pd.DataFrame, years: List[str]) -> Tuple[pd.DataFrame, Set[str]]:
    balance, reported = _apply_mapping(raw_df, BALANCE_SHEET_MAP, STANDARD_BS_ITEMS, years)

    if BS_TOTAL_DEBT not in reported:
        balance.loc[BS_TOTAL_DEBT] = balance.loc[BS_ST_DEBT] + balance.loc[BS_LT_DEBT]

    if BS_TOTAL_EQUITY not in reported:
        balance.loc[BS_TOTAL_EQUITY] = (
            balance.loc[BS_TOTAL_ASSETS] - balance.loc[BS_TOTAL_LIABILITIES]
        )

    if BS_TOTAL_LIABILITIES not in reported:
        balance.loc[BS_TOTAL_LIABILITIES] = (
            balance.loc[BS_TOTAL_ASSETS] - balance.loc[BS_TOTAL_EQUITY]
        )

    return balance, reported


def _map_cash_flow(raw_df: pd.DataFrame, years: List[str]) -> Tuple[pd.DataFrame, Set[str]]:
    cash, reported = _apply_mapping(raw_df, CASH_FLOW_MAP, STANDARD_CF_ITEMS, years)

    if CF_FREE_CASH_FLOW not in reported:
        cash.loc[CF_FREE_CASH_FLOW] = cash.loc[CF_OPERATING] - cash.loc[CF_CAPEX].abs()

    return cash, reported


def _collect_derived(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cash: pd.DataFrame,
    income_reported: Set[str],
    balance_reported: Set[str],
    cash_reported: Set[str],
) -> Dict[str, str]:
    derived: Dict[str, str] = {}

    if IS_EBITDA not in income_reported and income.loc[IS_EBITDA].abs().sum() > 0:
        derived[IS_EBITDA] = f"estimated as EBIT multiplied by {EBITDA_FALLBACK_MULTIPLE}"

    if BS_TOTAL_DEBT not in balance_reported and balance.loc[BS_TOTAL_DEBT].abs().sum() > 0:
        derived[BS_TOTAL_DEBT] = "summed from short-term and long-term debt"

    if BS_TOTAL_EQUITY not in balance_reported and balance.loc[BS_TOTAL_EQUITY].abs().sum() > 0:
        derived[BS_TOTAL_EQUITY] = "back-solved as total assets less total liabilities"

    if BS_TOTAL_LIABILITIES not in balance_reported and balance.loc[BS_TOTAL_LIABILITIES].abs().sum() > 0:
        derived[BS_TOTAL_LIABILITIES] = "back-solved as total assets less total equity"

    if CF_FREE_CASH_FLOW not in cash_reported and cash.loc[CF_FREE_CASH_FLOW].abs().sum() > 0:
        derived[CF_FREE_CASH_FLOW] = "computed as operating cash flow less capital expenditure"

    return derived


def _build_provenance(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cash: pd.DataFrame,
    reported: Set[str],
    derived: Dict[str, str],
) -> Dict[str, str]:
    populated: Dict[str, str] = {}

    for statement in (income, balance, cash):
        for item in statement.index:
            if item in derived:
                populated[item] = DERIVED
            elif item in reported:
                populated[item] = REPORTED
            elif float(statement.loc[item].abs().sum()) > 0:
                populated[item] = DERIVED
            else:
                populated[item] = MISSING

    return build_provenance(populated)


def _build_caveats(ticker: str, derived: Dict[str, str], provenance: Dict[str, str]) -> List[str]:
    caveats = [
        f"Statements were retrieved from Yahoo Finance for {ticker} and converted from absolute "
        f"currency units into the platform base unit by dividing by {BASE_UNIT_DIVISOR:,.0f}."
    ]

    for item, explanation in derived.items():
        caveats.append(f"{item} was not reported by the source and was {explanation}.")

    absent = [item for item, status in provenance.items() if status == MISSING]

    if absent:
        caveats.append(
            f"{len(absent)} standard line items were unavailable from this source and are held "
            f"at zero: {', '.join(absent[:6])}"
            + (" and others." if len(absent) > 6 else ".")
        )

    return caveats


def _extract_market_data(info: dict, ticker) -> dict:
    try:
        history = ticker.history(period="1y")
    except Exception:
        history = pd.DataFrame()

    return {
        "share_price": info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
        "shares_outstanding": info.get("sharesOutstanding") or 0,
        "market_cap": (info.get("marketCap") or 0) / BASE_UNIT_DIVISOR,
        "pe_ratio": info.get("trailingPE") or 0.0,
        "pb_ratio": info.get("priceToBook") or 0.0,
        "ev_ebitda": info.get("enterpriseToEbitda") or 0.0,
        "beta": info.get("beta") or 1.0,
        "52w_high": info.get("fiftyTwoWeekHigh") or 0.0,
        "52w_low": info.get("fiftyTwoWeekLow") or 0.0,
        "price_history": history if history is not None else pd.DataFrame(),
    }


def _extract_metadata(info: dict) -> Dict[str, str]:
    city = info.get("city", "")
    country = info.get("country", "")
    location = ", ".join(part for part in (city, country) if part) or "N/A"

    return {
        "Sector": info.get("sector", "N/A"),
        "Industry": info.get("industry", "N/A"),
        "Exchange": info.get("exchange", "N/A"),
        "Headquarters": location,
        "Description": info.get("longBusinessSummary", "N/A"),
        "Source": SOURCE_LABEL,
    }
