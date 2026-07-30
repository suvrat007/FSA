from typing import Dict, List

import numpy as np
import pandas as pd

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
from functions.datamodel import (
    ALL_STANDARD_ITEMS,
    DERIVED,
    MISSING,
    REPORTED,
    FinancialDataModel,
)

DEMO_YEARS: List[str] = ["FY20", "FY21", "FY22", "FY23", "FY24"]

SOURCE_LABEL = "Bundled offline dataset"

_PRICE_SERIES_SEED = 20240331
_TRADING_DAYS = 250

_DERIVED_ITEMS = {
    BS_TOTAL_CA,
    BS_TOTAL_CL,
    BS_TOTAL_DEBT,
    BS_TOTAL_EQUITY,
    BS_TOTAL_LIABILITIES,
    CF_FREE_CASH_FLOW,
}

_CAVEATS = [
    "This is a bundled offline dataset compiled for demonstration. Figures approximate published "
    "annual reports but are not audited source data and should not be used for real decisions.",
    "Subtotals are recomputed from their components rather than transcribed, so the balance sheet "
    "identity holds exactly in every period.",
    "The share price series is synthetic and generated from a fixed random seed.",
]


def get_mock_company_model(ticker_key: str = "RELIANCE.NS") -> FinancialDataModel:
    if "TCS" in ticker_key.upper():
        return _build_tcs_model()

    return _build_reliance_model()


def _build_statement(data: Dict[str, List[float]], years: List[str]) -> pd.DataFrame:
    return pd.DataFrame(data, index=years).T[years]


def _demo_provenance() -> Dict[str, str]:
    return {
        item: DERIVED if item in _DERIVED_ITEMS else REPORTED
        for item in ALL_STANDARD_ITEMS
    }


def _derive_balance_sheet_totals(bs_df: pd.DataFrame) -> pd.DataFrame:
    bs_df.loc[BS_TOTAL_CA] = bs_df.loc[[BS_CASH, BS_RECEIVABLES, BS_INVENTORY, BS_OTHER_CA]].sum()
    bs_df.loc[BS_TOTAL_CL] = bs_df.loc[[BS_PAYABLES, BS_ST_DEBT, BS_OTHER_CL]].sum()
    bs_df.loc[BS_TOTAL_DEBT] = bs_df.loc[[BS_ST_DEBT, BS_LT_DEBT]].sum()
    bs_df.loc[BS_TOTAL_EQUITY] = bs_df.loc[[BS_EQUITY_CAPITAL, BS_RESERVES]].sum()
    bs_df.loc[BS_TOTAL_LIABILITIES] = (
        bs_df.loc[BS_TOTAL_CL] + bs_df.loc[BS_LT_DEBT] + bs_df.loc[BS_OTHER_NCL]
    )

    return bs_df


def _build_price_history(start_price: float, end_price: float, volume_range: tuple) -> pd.DataFrame:
    rng = np.random.default_rng(_PRICE_SERIES_SEED)
    dates = pd.date_range(end="2024-03-31", periods=_TRADING_DAYS, freq="B")
    closes = np.linspace(start_price, end_price, _TRADING_DAYS) + rng.normal(0, 30, _TRADING_DAYS)
    volumes = rng.integers(volume_range[0], volume_range[1], _TRADING_DAYS)

    return pd.DataFrame({"Close": closes, "Volume": volumes}, index=dates)


def _build_reliance_model() -> FinancialDataModel:
    years = DEMO_YEARS

    is_df = _build_statement(
        {
            IS_REVENUE: [596679, 466924, 699962, 879468, 900122],
            IS_EBITDA: [88217, 80737, 110460, 142138, 161688],
            IS_EBIT: [67258, 59798, 86047, 111833, 126938],
            IS_INTEREST: [22027, 21189, 14584, 19571, 22627],
            IS_PBT: [45231, 38609, 71463, 92262, 104311],
            IS_TAX: [8530, 2045, 12624, 25211, 24688],
            IS_NET_INCOME: [36701, 36564, 58839, 67051, 79623],
        },
        years,
    )

    bs_df = _build_statement(
        {
            BS_CASH: [45465, 87456, 36245, 68450, 92140],
            BS_RECEIVABLES: [19654, 18945, 23650, 29840, 34500],
            BS_INVENTORY: [73904, 81672, 107778, 141254, 148900],
            BS_OTHER_CA: [85430, 92450, 112450, 125400, 138500],
            BS_PPE: [634560, 645120, 712450, 812400, 895400],
            BS_OTHER_NCA: [265430, 314560, 345670, 384500, 421400],
            BS_TOTAL_ASSETS: [1124443, 1240203, 1338243, 1561844, 1730840],
            BS_PAYABLES: [96450, 108450, 125400, 145600, 158400],
            BS_ST_DEBT: [85400, 72500, 68400, 79500, 84200],
            BS_OTHER_CL: [78400, 84200, 92500, 104500, 115600],
            BS_LT_DEBT: [221400, 184500, 198500, 234500, 252400],
            BS_OTHER_NCL: [92400, 98400, 104500, 114200, 125400],
            BS_EQUITY_CAPITAL: [6339, 6445, 6765, 6765, 6765],
            BS_RESERVES: [544054, 685708, 742178, 876779, 988075],
        },
        years,
    )
    bs_df = _derive_balance_sheet_totals(bs_df)

    cf_df = _build_statement(
        {
            CF_OPERATING: [94876, 56186, 110654, 115240, 142850],
            CF_INVESTING: [-74500, -92400, -104500, -125400, -132000],
            CF_FINANCING: [-12400, 48205, -57365, 13355, 12840],
            CF_CAPEX: [76500, 84200, 95400, 112000, 121000],
        },
        years,
    )
    cf_df.loc[CF_FREE_CASH_FLOW] = cf_df.loc[CF_OPERATING] - cf_df.loc[CF_CAPEX]

    market_data = {
        "share_price": 2980.50,
        "shares_outstanding": 6.765e9,
        "market_cap": 2016300.0,
        "pe_ratio": 25.3,
        "pb_ratio": 2.26,
        "ev_ebitda": 14.2,
        "beta": 0.95,
        "52w_high": 3024.90,
        "52w_low": 2220.30,
        "price_history": _build_price_history(2200, 2950, (1_000_000, 5_000_000)),
    }

    metadata = {
        "Source": SOURCE_LABEL,
        "Sector": "Energy and Retail Conglomerate",
        "Industry": "Integrated Oil, Gas and Retail",
        "Exchange": "NSE",
        "Headquarters": "Mumbai, Maharashtra, India",
        "Description": (
            "Reliance Industries Limited is an Indian multinational conglomerate operating in "
            "energy, petrochemicals, retail, telecommunications, and media."
        ),
    }

    return FinancialDataModel(
        company_name="Reliance Industries Ltd",
        ticker="RELIANCE.NS",
        currency="INR",
        years=years,
        income_statement=is_df,
        balance_sheet=bs_df,
        cash_flow=cf_df,
        market_data=market_data,
        metadata=metadata,
        provenance=_demo_provenance(),
        caveats=list(_CAVEATS),
    )


def _build_tcs_model() -> FinancialDataModel:
    years = DEMO_YEARS

    is_df = _build_statement(
        {
            IS_REVENUE: [156949, 164177, 191754, 225458, 240893],
            IS_EBITDA: [42110, 46546, 53057, 59258, 64280],
            IS_EBIT: [38580, 42481, 48453, 54237, 59120],
            IS_INTEREST: [920, 637, 784, 880, 950],
            IS_PBT: [42248, 43760, 51687, 56890, 61500],
            IS_TAX: [9880, 11155, 13339, 14593, 15600],
            IS_NET_INCOME: [32368, 32605, 38348, 42297, 45900],
        },
        years,
    )

    bs_df = _build_statement(
        {
            BS_CASH: [8640, 6850, 12450, 11200, 14500],
            BS_RECEIVABLES: [30650, 32400, 36800, 41200, 44500],
            BS_INVENTORY: [120, 110, 90, 105, 115],
            BS_OTHER_CA: [38400, 42100, 45600, 48900, 52100],
            BS_PPE: [11800, 12100, 12800, 13400, 14200],
            BS_OTHER_NCA: [31500, 34500, 38400, 41500, 44800],
            BS_TOTAL_ASSETS: [121110, 128060, 146140, 156305, 170215],
            BS_PAYABLES: [8400, 9200, 10500, 11400, 12200],
            BS_ST_DEBT: [0, 0, 0, 0, 0],
            BS_OTHER_CL: [24500, 26800, 29400, 31200, 33500],
            BS_LT_DEBT: [0, 0, 0, 0, 0],
            BS_OTHER_NCL: [4100, 4500, 4900, 5200, 5600],
            BS_EQUITY_CAPITAL: [375, 370, 366, 366, 366],
            BS_RESERVES: [83735, 87190, 100974, 108139, 118549],
        },
        years,
    )
    bs_df = _derive_balance_sheet_totals(bs_df)

    cf_df = _build_statement(
        {
            CF_OPERATING: [32360, 38802, 39949, 41991, 46800],
            CF_INVESTING: [-8500, -7400, -9200, -8900, -9500],
            CF_FINANCING: [-24500, -32500, -31500, -33500, -34000],
            CF_CAPEX: [3150, 2850, 3200, 3400, 3600],
        },
        years,
    )
    cf_df.loc[CF_FREE_CASH_FLOW] = cf_df.loc[CF_OPERATING] - cf_df.loc[CF_CAPEX]

    market_data = {
        "share_price": 3850.00,
        "shares_outstanding": 3.66e9,
        "market_cap": 1409100.0,
        "pe_ratio": 30.7,
        "pb_ratio": 11.8,
        "ev_ebitda": 21.5,
        "beta": 0.62,
        "52w_high": 4254.75,
        "52w_low": 3056.00,
        "price_history": _build_price_history(3100, 3950, (500_000, 2_500_000)),
    }

    metadata = {
        "Source": SOURCE_LABEL,
        "Sector": "Information Technology",
        "Industry": "IT Services and Consulting",
        "Exchange": "NSE",
        "Headquarters": "Mumbai, Maharashtra, India",
        "Description": (
            "Tata Consultancy Services is an Indian multinational information technology "
            "services and consulting company, part of the Tata Group."
        ),
    }

    return FinancialDataModel(
        company_name="Tata Consultancy Services Ltd",
        ticker="TCS.NS",
        currency="INR",
        years=years,
        income_statement=is_df,
        balance_sheet=bs_df,
        cash_flow=cf_df,
        market_data=market_data,
        metadata=metadata,
        provenance=_demo_provenance(),
        caveats=list(_CAVEATS),
    )
