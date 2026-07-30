import logging
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd

from functions.config import (
    BS_EQUITY_CAPITAL,
    BS_OTHER_CA,
    BS_OTHER_CL,
    BS_PPE,
    BS_RESERVES,
    BS_TOTAL_ASSETS,
    BS_TOTAL_DEBT,
    BS_TOTAL_EQUITY,
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
)
from functions.datamodel import (
    DERIVED,
    MISSING,
    REPORTED,
    STANDARD_BS_ITEMS,
    STANDARD_CF_ITEMS,
    STANDARD_IS_ITEMS,
    STATUS_ERROR,
    STATUS_UNSUPPORTED,
    FinancialDataModel,
    LoadResult,
    build_provenance,
    create_empty_statement,
)
from functions.mock_data import DEMO_YEARS

logger = logging.getLogger(__name__)

SOURCE_LABEL = "Screener.in export"
MAX_PERIODS = 5

INCOME_LABEL_MAP: Dict[str, str] = {
    "sales": IS_REVENUE,
    "revenue": IS_REVENUE,
    "operating profit": IS_EBITDA,
    "ebitda": IS_EBITDA,
    "interest": IS_INTEREST,
    "profit before tax": IS_PBT,
    "net profit": IS_NET_INCOME,
}

BALANCE_LABEL_MAP: Dict[str, str] = {
    "equity capital": BS_EQUITY_CAPITAL,
    "reserves": BS_RESERVES,
    "borrowings": BS_TOTAL_DEBT,
    "other liabilities": BS_OTHER_CL,
    "fixed assets": BS_PPE,
    "other assets": BS_OTHER_CA,
    "total assets": BS_TOTAL_ASSETS,
    "total liabilities": BS_TOTAL_ASSETS,
}

CASH_LABEL_MAP: Dict[str, str] = {
    "cash from operating activity": CF_OPERATING,
    "cash from investing activity": CF_INVESTING,
    "cash from financing activity": CF_FINANCING,
}


def load_screener_excel(source: Any, company_name: str = "Screener Export") -> LoadResult:
    try:
        workbook = pd.ExcelFile(source)
    except Exception as error:
        logger.warning("Unable to open the Screener export (%s).", error)
        return LoadResult.failure(
            STATUS_ERROR,
            f"The workbook could not be opened: {error}",
            SOURCE_LABEL,
        )

    if "Data Sheet" not in workbook.sheet_names:
        return LoadResult.failure(
            STATUS_UNSUPPORTED,
            "This workbook has no 'Data Sheet' tab, so it is not a standard Screener.in export. "
            f"Sheets found: {', '.join(workbook.sheet_names)}. "
            "Use the custom spreadsheet loader instead.",
            SOURCE_LABEL,
        )

    try:
        return _parse_data_sheet(workbook.parse("Data Sheet"), company_name)
    except Exception as error:
        logger.warning("Unable to parse the Screener export (%s).", error)
        return LoadResult.failure(
            STATUS_ERROR,
            f"The 'Data Sheet' tab could not be parsed: {error}",
            SOURCE_LABEL,
        )


def _parse_data_sheet(df: pd.DataFrame, fallback_name: str) -> LoadResult:
    df = df.dropna(how="all").dropna(how="all", axis=1)

    if df.empty:
        return LoadResult.failure(
            STATUS_UNSUPPORTED, "The 'Data Sheet' tab is empty.", SOURCE_LABEL
        )

    company = _detect_company_name(df, fallback_name)
    years, years_detected = _detect_periods(df)

    income = create_empty_statement(STANDARD_IS_ITEMS, years)
    balance = create_empty_statement(STANDARD_BS_ITEMS, years)
    cash = create_empty_statement(STANDARD_CF_ITEMS, years)
    reported: Set[str] = set()

    for _, row in df.iterrows():
        label = str(row.iloc[0]).strip().lower()
        values = _row_values(row, len(years))

        _assign_if_empty(income, INCOME_LABEL_MAP, label, values, reported)
        _assign_if_empty(balance, BALANCE_LABEL_MAP, label, values, reported)
        _assign_if_empty(cash, CASH_LABEL_MAP, label, values, reported)

    if not reported:
        return LoadResult.failure(
            STATUS_UNSUPPORTED,
            "No recognisable financial line items were found in the 'Data Sheet' tab.",
            SOURCE_LABEL,
        )

    derived: Dict[str, str] = {}

    if IS_EBIT not in reported:
        income.loc[IS_EBIT] = income.loc[IS_PBT] + income.loc[IS_INTEREST]
        derived[IS_EBIT] = "computed as profit before tax plus interest expense"

    if BS_TOTAL_EQUITY not in reported:
        balance.loc[BS_TOTAL_EQUITY] = balance.loc[BS_EQUITY_CAPITAL] + balance.loc[BS_RESERVES]
        derived[BS_TOTAL_EQUITY] = "summed from equity share capital and reserves"

    if CF_FREE_CASH_FLOW not in reported:
        cash.loc[CF_FREE_CASH_FLOW] = cash.loc[CF_OPERATING]
        derived[CF_FREE_CASH_FLOW] = (
            "set equal to operating cash flow because Screener exports do not isolate capital "
            "expenditure"
        )

    provenance = _build_provenance(income, balance, cash, reported, derived)
    caveats = _build_caveats(derived, provenance, years_detected)

    model = FinancialDataModel(
        company_name=company,
        ticker="SCREENER_EXPORT",
        currency="INR",
        years=years,
        income_statement=income,
        balance_sheet=balance,
        cash_flow=cash,
        metadata={"Source": SOURCE_LABEL, "Sector": "N/A", "Industry": "N/A"},
        provenance=provenance,
        caveats=caveats,
    )

    return LoadResult.success(model, SOURCE_LABEL)


def _detect_company_name(df: pd.DataFrame, fallback_name: str) -> str:
    first_cell = str(df.iloc[0, 0]).strip()

    if not first_cell or first_cell.lower() in {"nan", "none"} or len(first_cell) < 3:
        return fallback_name

    return first_cell.replace("Company:", "").strip() or fallback_name


def _detect_periods(df: pd.DataFrame) -> Tuple[List[str], bool]:
    for _, row in df.iterrows():
        candidates = [str(value) for value in row.values if _looks_like_period(str(value))]

        if len(candidates) >= 3:
            return [f"FY{value.strip()[-2:]}" for value in candidates[-MAX_PERIODS:]], True

    return list(DEMO_YEARS), False


def _looks_like_period(value: str) -> bool:
    return any(marker in value for marker in ("201", "202"))


def _row_values(row: pd.Series, period_count: int) -> np.ndarray:
    values = pd.to_numeric(row.iloc[1 : period_count + 1], errors="coerce").fillna(0.0).values

    if len(values) < period_count:
        values = np.pad(values, (0, period_count - len(values)), "constant")

    return values[:period_count]


def _assign_if_empty(
    statement: pd.DataFrame,
    label_map: Dict[str, str],
    label: str,
    values: np.ndarray,
    reported: Set[str],
) -> None:
    for keyword, standard_item in label_map.items():
        if keyword in label and standard_item not in reported:
            statement.loc[standard_item] = values
            reported.add(standard_item)


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
            else:
                populated[item] = MISSING

    return build_provenance(populated)


def _build_caveats(
    derived: Dict[str, str],
    provenance: Dict[str, str],
    years_detected: bool,
) -> List[str]:
    caveats = [
        "Screener.in exports are already denominated in crore, so no unit conversion was applied."
    ]

    if not years_detected:
        caveats.append(
            "Reporting periods could not be detected in the workbook, so placeholder labels "
            "FY20 to FY24 were applied. Period labels may not match the underlying data."
        )

    for item, explanation in derived.items():
        caveats.append(f"{item} was not present in the export and was {explanation}.")

    absent = [item for item, status in provenance.items() if status == MISSING]

    if absent:
        caveats.append(
            f"Screener exports do not carry {len(absent)} of the standard line items used by this "
            f"platform. Ratios that depend on them will read as not available."
        )

    return caveats
