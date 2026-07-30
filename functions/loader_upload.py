import logging
from typing import Any, Dict, List, Set, Tuple

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
    STATUS_ERROR,
    STATUS_UNSUPPORTED,
    FinancialDataModel,
    LoadResult,
    build_provenance,
    create_empty_statement,
)
from functions.mock_data import DEMO_YEARS

logger = logging.getLogger(__name__)

SOURCE_LABEL = "Custom spreadsheet"
MAX_PERIODS = 6

LABEL_KEYWORDS: List[Tuple[Tuple[str, ...], str, str]] = [
    (("revenue", "sales", "turnover", "total income"), "income", IS_REVENUE),
    (("ebitda", "operating profit"), "income", IS_EBITDA),
    (("ebit", "operating income"), "income", IS_EBIT),
    (("interest", "finance cost"), "income", IS_INTEREST),
    (("profit before tax", "pbt"), "income", IS_PBT),
    (("tax expense", "tax provision"), "income", IS_TAX),
    (("net profit", "net income", "profit after tax", "pat"), "income", IS_NET_INCOME),
    (("cash and", "cash equivalents"), "balance", BS_CASH),
    (("receivable", "debtors"), "balance", BS_RECEIVABLES),
    (("inventor", "stock in trade"), "balance", BS_INVENTORY),
    (("payable", "creditors"), "balance", BS_PAYABLES),
    (("current assets",), "balance", BS_TOTAL_CA),
    (("current liabilities",), "balance", BS_TOTAL_CL),
    (("total assets",), "balance", BS_TOTAL_ASSETS),
    (("total debt", "borrowings"), "balance", BS_TOTAL_DEBT),
    (("total equity", "net worth", "shareholders equity"), "balance", BS_TOTAL_EQUITY),
    (("operating cash", "cash from operations", "cfo"), "cash", CF_OPERATING),
    (("capital expenditure", "capex"), "cash", CF_CAPEX),
    (("free cash flow",), "cash", CF_FREE_CASH_FLOW),
]


def load_uploaded_statement(file_obj: Any, filename: str) -> LoadResult:
    try:
        df = _read_tabular_file(file_obj, filename)
    except Exception as error:
        logger.warning("Unable to read the uploaded file %s (%s).", filename, error)
        return LoadResult.failure(STATUS_ERROR, f"The file could not be read: {error}", SOURCE_LABEL)

    if df is None:
        return LoadResult.failure(
            STATUS_UNSUPPORTED,
            f"{filename} is not a supported format. Upload a .csv, .xlsx, or .xls file.",
            SOURCE_LABEL,
        )

    df = df.dropna(how="all").dropna(how="all", axis=1)

    if df.empty or len(df.columns) < 2:
        return LoadResult.failure(
            STATUS_UNSUPPORTED,
            "The file has no usable rows. Expected line item labels in the first column and one "
            "column per reporting period.",
            SOURCE_LABEL,
        )

    label_column = df.columns[0]
    period_columns = _detect_period_columns(df)
    periods_detected = bool(period_columns)
    years = [str(column).strip() for column in period_columns] or list(DEMO_YEARS)

    statements = {
        "income": create_empty_statement(STANDARD_IS_ITEMS, years),
        "balance": create_empty_statement(STANDARD_BS_ITEMS, years),
        "cash": create_empty_statement(STANDARD_CF_ITEMS, years),
    }
    reported: Set[str] = set()
    unmatched: List[str] = []

    for _, row in df.iterrows():
        raw_label = str(row[label_column]).strip()
        label = raw_label.lower()

        if not label or label in {"nan", "none"}:
            continue

        matched = False

        for keywords, statement_key, standard_item in LABEL_KEYWORDS:
            if any(keyword in label for keyword in keywords) and standard_item not in reported:
                statements[statement_key].loc[standard_item] = _row_values(
                    row, period_columns, len(years)
                )
                reported.add(standard_item)
                matched = True
                break

        if not matched:
            unmatched.append(raw_label)

    if not reported:
        return LoadResult.failure(
            STATUS_UNSUPPORTED,
            "No recognisable line items were matched. Label rows with terms such as Revenue, "
            "EBITDA, Net Profit, Total Assets, Total Equity, or Operating Cash Flow.",
            SOURCE_LABEL,
        )

    derived = _derive_missing(statements, reported)
    provenance = _build_provenance(statements, reported, derived)
    caveats = _build_caveats(filename, derived, provenance, unmatched, periods_detected)

    model = FinancialDataModel(
        company_name=filename.rsplit(".", 1)[0].replace("_", " ").strip().title(),
        ticker="UPLOAD",
        currency="INR",
        years=years,
        income_statement=statements["income"],
        balance_sheet=statements["balance"],
        cash_flow=statements["cash"],
        metadata={"Source": f"{SOURCE_LABEL} ({filename})", "Sector": "N/A", "Industry": "N/A"},
        provenance=provenance,
        caveats=caveats,
    )

    return LoadResult.success(model, SOURCE_LABEL)


def _read_tabular_file(file_obj: Any, filename: str):
    lowered = filename.lower()

    if lowered.endswith(".csv"):
        return pd.read_csv(file_obj)

    if lowered.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_obj)

    return None


def _detect_period_columns(df: pd.DataFrame) -> List[Any]:
    candidates = [
        column
        for column in df.columns[1:]
        if any(char.isdigit() for char in str(column))
    ]

    return candidates[-MAX_PERIODS:] if len(candidates) >= 2 else []


def _row_values(row: pd.Series, period_columns: List[Any], period_count: int) -> np.ndarray:
    if not period_columns:
        return np.zeros(period_count)

    values = pd.to_numeric(row[period_columns], errors="coerce").fillna(0.0).values

    if len(values) < period_count:
        values = np.pad(values, (0, period_count - len(values)), "constant")

    return values[:period_count]


def _derive_missing(statements: Dict[str, pd.DataFrame], reported: Set[str]) -> Dict[str, str]:
    income = statements["income"]
    cash = statements["cash"]
    derived: Dict[str, str] = {}

    if IS_EBIT not in reported and IS_PBT in reported and IS_INTEREST in reported:
        income.loc[IS_EBIT] = income.loc[IS_PBT] + income.loc[IS_INTEREST]
        derived[IS_EBIT] = "computed as profit before tax plus interest expense"

    if IS_EBITDA not in reported and income.loc[IS_EBIT].abs().sum() > 0:
        income.loc[IS_EBITDA] = income.loc[IS_EBIT]
        derived[IS_EBITDA] = "set equal to EBIT because no depreciation line was supplied"

    if CF_FREE_CASH_FLOW not in reported and CF_OPERATING in reported:
        cash.loc[CF_FREE_CASH_FLOW] = cash.loc[CF_OPERATING] - cash.loc[CF_CAPEX].abs()
        derived[CF_FREE_CASH_FLOW] = "computed as operating cash flow less capital expenditure"

    return derived


def _build_provenance(
    statements: Dict[str, pd.DataFrame],
    reported: Set[str],
    derived: Dict[str, str],
) -> Dict[str, str]:
    populated: Dict[str, str] = {}

    for statement in statements.values():
        for item in statement.index:
            if item in derived:
                populated[item] = DERIVED
            elif item in reported:
                populated[item] = REPORTED
            else:
                populated[item] = MISSING

    return build_provenance(populated)


def _build_caveats(
    filename: str,
    derived: Dict[str, str],
    provenance: Dict[str, str],
    unmatched: List[str],
    periods_detected: bool,
) -> List[str]:
    caveats = [
        f"Values were taken from {filename} exactly as supplied. The platform assumes they are "
        f"denominated in crore; rescale the file before upload if they are not."
    ]

    if not periods_detected:
        caveats.append(
            "No period columns containing digits were found, so placeholder labels FY20 to FY24 "
            "were applied and all values read as zero."
        )

    for item, explanation in derived.items():
        caveats.append(f"{item} was not supplied and was {explanation}.")

    if unmatched:
        caveats.append(
            f"{len(unmatched)} row label(s) could not be matched to a standard line item and were "
            f"ignored: {', '.join(unmatched[:5])}"
            + (" and others." if len(unmatched) > 5 else ".")
        )

    absent = [item for item, status in provenance.items() if status == MISSING]

    if absent:
        caveats.append(
            f"{len(absent)} standard line items were not supplied. Any ratio depending on them "
            f"will read as not available rather than being estimated."
        )

    return caveats
