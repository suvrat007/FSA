from typing import Any, Dict, List

APP_NAME = "FinSight OS"
APP_TAGLINE = "Financial Statement Analysis and 3-Statement Modeling Terminal"
APP_VERSION = "1.0.0"

BASE_UNIT_LABEL = "crore"
DEFAULT_SCALE = "CRORE"

CURRENCY_SCALES: Dict[str, Dict[str, Any]] = {
    "CRORE": {"label": "Crore", "factor": 1.0, "suffix": " Cr"},
    "LAKH": {"label": "Lakh", "factor": 100.0, "suffix": " Lakh"},
    "MILLION": {"label": "Million", "factor": 10.0, "suffix": " Mn"},
    "BILLION": {"label": "Billion", "factor": 0.01, "suffix": " Bn"},
}

CURRENCY_SYMBOLS: Dict[str, str] = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}

THEME_COLORS: Dict[str, str] = {
    "bg_dark": "#0F172A",
    "bg_card": "#1E293B",
    "bg_sidebar": "#090D16",
    "border": "#334155",
    "border_strong": "#475569",
    "text_main": "#F8FAFC",
    "text_muted": "#94A3B8",
    "accent_primary": "#10B981",
    "accent_secondary": "#06B6D4",
    "accent_tertiary": "#8B5CF6",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "success": "#22C55E",
    "chart_grid": "#334155",
}

CHART_SERIES_COLORS: List[str] = [
    THEME_COLORS["accent_primary"],
    THEME_COLORS["accent_secondary"],
    THEME_COLORS["warning"],
    THEME_COLORS["accent_tertiary"],
    THEME_COLORS["danger"],
]

IS_REVENUE = "Revenue"
IS_EBITDA = "EBITDA"
IS_EBIT = "EBIT"
IS_INTEREST = "Interest Expense"
IS_PBT = "Profit Before Tax"
IS_TAX = "Tax Expense"
IS_NET_INCOME = "Net Income"

BS_CASH = "Cash & Cash Equivalents"
BS_RECEIVABLES = "Accounts Receivable"
BS_INVENTORY = "Inventory"
BS_OTHER_CA = "Other Current Assets"
BS_TOTAL_CA = "Total Current Assets"
BS_PPE = "Net PP&E / Fixed Assets"
BS_OTHER_NCA = "Other Non-Current Assets"
BS_TOTAL_ASSETS = "Total Assets"

BS_PAYABLES = "Accounts Payable"
BS_ST_DEBT = "Short-Term Debt"
BS_OTHER_CL = "Other Current Liabilities"
BS_TOTAL_CL = "Total Current Liabilities"
BS_LT_DEBT = "Long-Term Debt"
BS_TOTAL_DEBT = "Total Debt"
BS_OTHER_NCL = "Other Non-Current Liabilities"
BS_TOTAL_LIABILITIES = "Total Liabilities"

BS_EQUITY_CAPITAL = "Equity Share Capital"
BS_RESERVES = "Reserves & Surplus"
BS_TOTAL_EQUITY = "Total Shareholders Equity"

CF_OPERATING = "Cash Flow from Operations (CFO)"
CF_INVESTING = "Cash Flow from Investing (CFI)"
CF_FINANCING = "Cash Flow from Financing (CFF)"
CF_CAPEX = "Capital Expenditures (Capex)"
CF_FREE_CASH_FLOW = "Free Cash Flow (FCF)"

BALANCE_TOLERANCE = 1.0

OFFLINE_DEMO_COMPANIES: Dict[str, str] = {
    "Reliance Industries Ltd": "RELIANCE.NS",
    "Tata Consultancy Services Ltd": "TCS.NS",
}

PEER_GROUPS: Dict[str, List[str]] = {
    "IT Services": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "Conglomerates & Energy": ["RELIANCE.NS", "ADANIENT.NS", "ONGC.NS", "BPCL.NS"],
    "Automotive": ["TATAMOTORS.NS", "MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS"],
    "Banking & Finance": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS"],
}


def get_scale(scale_key: str) -> Dict[str, Any]:
    return CURRENCY_SCALES.get(scale_key, CURRENCY_SCALES[DEFAULT_SCALE])


def currency_symbol(currency: str) -> str:
    return CURRENCY_SYMBOLS.get((currency or "").upper(), "")
