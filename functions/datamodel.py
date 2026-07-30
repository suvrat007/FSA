from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

import pandas as pd

from functions.config import (
    BALANCE_TOLERANCE,
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

REPORTED = "Reported"
DERIVED = "Derived"
ASSUMED = "Assumed"
MISSING = "Not available"

PROVENANCE_ORDER = [REPORTED, DERIVED, ASSUMED, MISSING]

STATUS_OK = "ok"
STATUS_EMPTY = "empty"
STATUS_ERROR = "error"
STATUS_UNSUPPORTED = "unsupported"

STANDARD_IS_ITEMS: List[str] = [
    IS_REVENUE,
    IS_EBITDA,
    IS_EBIT,
    IS_INTEREST,
    IS_PBT,
    IS_TAX,
    IS_NET_INCOME,
]

STANDARD_BS_ITEMS: List[str] = [
    BS_CASH,
    BS_RECEIVABLES,
    BS_INVENTORY,
    BS_OTHER_CA,
    BS_TOTAL_CA,
    BS_PPE,
    BS_OTHER_NCA,
    BS_TOTAL_ASSETS,
    BS_PAYABLES,
    BS_ST_DEBT,
    BS_OTHER_CL,
    BS_TOTAL_CL,
    BS_LT_DEBT,
    BS_TOTAL_DEBT,
    BS_OTHER_NCL,
    BS_TOTAL_LIABILITIES,
    BS_EQUITY_CAPITAL,
    BS_RESERVES,
    BS_TOTAL_EQUITY,
]

STANDARD_CF_ITEMS: List[str] = [
    CF_OPERATING,
    CF_INVESTING,
    CF_FINANCING,
    CF_CAPEX,
    CF_FREE_CASH_FLOW,
]

ALL_STANDARD_ITEMS: List[str] = STANDARD_IS_ITEMS + STANDARD_BS_ITEMS + STANDARD_CF_ITEMS


@dataclass
class FinancialDataModel:
    company_name: str
    ticker: str
    currency: str = "INR"
    years: List[str] = field(default_factory=list)
    income_statement: pd.DataFrame = field(default_factory=pd.DataFrame)
    balance_sheet: pd.DataFrame = field(default_factory=pd.DataFrame)
    cash_flow: pd.DataFrame = field(default_factory=pd.DataFrame)
    market_data: Dict[str, Union[float, int, str, pd.DataFrame]] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)
    provenance: Dict[str, str] = field(default_factory=dict)
    caveats: List[str] = field(default_factory=list)

    @property
    def source(self) -> str:
        return self.metadata.get("Source", "Unknown")

    def provenance_of(self, item: str) -> str:
        return self.provenance.get(item, MISSING)

    def items_by_provenance(self, status: str) -> List[str]:
        return [item for item in ALL_STANDARD_ITEMS if self.provenance_of(item) == status]

    def provenance_frame(self) -> pd.DataFrame:
        rows = [
            {"Line item": item, "Origin": self.provenance_of(item)}
            for item in ALL_STANDARD_ITEMS
        ]

        return pd.DataFrame(rows)

    def completeness(self) -> float:
        if not ALL_STANDARD_ITEMS:
            return 0.0

        populated = sum(
            1 for item in ALL_STANDARD_ITEMS if self.provenance_of(item) != MISSING
        )

        return round(100.0 * populated / len(ALL_STANDARD_ITEMS), 1)

    def validate_integrity(self) -> List[str]:
        if self.balance_sheet.empty:
            return ["Balance sheet is empty."]

        warnings: List[str] = []

        for year in self.years:
            if year not in self.balance_sheet.columns:
                continue

            assets = read_item(self.balance_sheet, BS_TOTAL_ASSETS, year)
            liabilities = read_item(self.balance_sheet, BS_TOTAL_LIABILITIES, year)
            equity = read_item(self.balance_sheet, BS_TOTAL_EQUITY, year)
            difference = abs(assets - (liabilities + equity))

            if difference > BALANCE_TOLERANCE:
                warnings.append(
                    f"Balance sheet mismatch in {year}: assets ({assets:,.1f}) does not equal "
                    f"liabilities ({liabilities:,.1f}) plus equity ({equity:,.1f}); "
                    f"difference of {difference:,.1f}."
                )

        return warnings


@dataclass
class LoadResult:
    model: Optional[FinancialDataModel] = None
    status: str = STATUS_OK
    message: str = ""
    source_label: str = ""

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK and self.model is not None

    @classmethod
    def success(cls, model: FinancialDataModel, source_label: str = "") -> "LoadResult":
        return cls(model=model, status=STATUS_OK, source_label=source_label)

    @classmethod
    def failure(cls, status: str, message: str, source_label: str = "") -> "LoadResult":
        return cls(model=None, status=status, message=message, source_label=source_label)


def create_empty_statement(line_items: List[str], years: List[str]) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=line_items, columns=years).astype(float)


def read_item(df: pd.DataFrame, item: str, year: str, default: float = 0.0) -> float:
    if df.empty or item not in df.index or year not in df.columns:
        return default

    value = df.loc[item, year]

    return default if pd.isna(value) else float(value)


def build_provenance(
    populated_items: Dict[str, str],
    default_status: str = MISSING,
) -> Dict[str, str]:
    return {item: populated_items.get(item, default_status) for item in ALL_STANDARD_ITEMS}


def infer_provenance(
    statements: Dict[str, pd.DataFrame],
    reported_items: set,
    derived_items: Dict[str, str],
) -> Dict[str, str]:
    provenance: Dict[str, str] = {}

    for statement in statements.values():
        if statement is None or statement.empty:
            continue

        for item in statement.index:
            if item in derived_items:
                provenance[item] = DERIVED
            elif item in reported_items:
                provenance[item] = REPORTED
            elif float(statement.loc[item].abs().sum()) > 0:
                provenance[item] = DERIVED
            else:
                provenance[item] = MISSING

    return build_provenance(provenance)
