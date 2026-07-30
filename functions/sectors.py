from typing import Dict, List, Optional

from functions.datamodel import FinancialDataModel

MODEL_GENERAL = "General corporate"
MODEL_FINANCIAL = "Bank or financial institution"

FINANCIAL_KEYWORDS = (
    "bank",
    "financial service",
    "financial institution",
    "insurance",
    "capital market",
    "asset management",
    "nbfc",
    "lending",
    "credit service",
    "brokerage",
    "mortgage",
)

INDUSTRY_UNIVERSE: Dict[str, List[str]] = {
    "IT Services": [
        "TCS.NS",
        "INFY.NS",
        "WIPRO.NS",
        "HCLTECH.NS",
        "TECHM.NS",
        "LTIM.NS",
        "PERSISTENT.NS",
        "MPHASIS.NS",
        "COFORGE.NS",
    ],
    "Oil, Gas and Energy": [
        "RELIANCE.NS",
        "ONGC.NS",
        "BPCL.NS",
        "IOC.NS",
        "HINDPETRO.NS",
        "GAIL.NS",
        "OIL.NS",
    ],
    "Automobiles": [
        "TATAMOTORS.NS",
        "MARUTI.NS",
        "M&M.NS",
        "BAJAJ-AUTO.NS",
        "HEROMOTOCO.NS",
        "EICHERMOT.NS",
        "TVSMOTOR.NS",
        "ASHOKLEY.NS",
    ],
    "Banks and Financials": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "KOTAKBANK.NS",
        "AXISBANK.NS",
        "INDUSINDBK.NS",
        "BANKBARODA.NS",
        "BAJFINANCE.NS",
    ],
    "Pharmaceuticals": [
        "SUNPHARMA.NS",
        "DRREDDY.NS",
        "CIPLA.NS",
        "DIVISLAB.NS",
        "LUPIN.NS",
        "AUROPHARMA.NS",
        "TORNTPHARM.NS",
        "ALKEM.NS",
    ],
    "Consumer Staples": [
        "HINDUNILVR.NS",
        "ITC.NS",
        "NESTLEIND.NS",
        "BRITANNIA.NS",
        "DABUR.NS",
        "MARICO.NS",
        "GODREJCP.NS",
        "COLPAL.NS",
    ],
    "Metals and Mining": [
        "TATASTEEL.NS",
        "JSWSTEEL.NS",
        "HINDALCO.NS",
        "VEDL.NS",
        "JINDALSTEL.NS",
        "SAIL.NS",
        "NMDC.NS",
        "NATIONALUM.NS",
    ],
    "Cement and Construction": [
        "ULTRACEMCO.NS",
        "SHREECEM.NS",
        "AMBUJACEM.NS",
        "ACC.NS",
        "DALBHARAT.NS",
        "JKCEMENT.NS",
        "LT.NS",
    ],
    "Telecom": [
        "BHARTIARTL.NS",
        "IDEA.NS",
        "TATACOMM.NS",
        "INDUSTOWER.NS",
    ],
    "Power and Utilities": [
        "NTPC.NS",
        "POWERGRID.NS",
        "TATAPOWER.NS",
        "ADANIPOWER.NS",
        "JSWENERGY.NS",
        "NHPC.NS",
        "SJVN.NS",
    ],
    "Chemicals": [
        "PIDILITIND.NS",
        "SRF.NS",
        "UPL.NS",
        "AARTIIND.NS",
        "DEEPAKNTR.NS",
        "TATACHEM.NS",
        "NAVINFLUOR.NS",
    ],
    "Consumer Durables": [
        "TITAN.NS",
        "HAVELLS.NS",
        "VOLTAS.NS",
        "CROMPTON.NS",
        "BLUESTARCO.NS",
        "DIXON.NS",
    ],
    "Industrials and Conglomerates": [
        "ADANIENT.NS",
        "SIEMENS.NS",
        "ABB.NS",
        "BHEL.NS",
        "CUMMINSIND.NS",
        "THERMAX.NS",
    ],
}

DIRECT_COMPETITORS: Dict[str, List[str]] = {
    "TCS.NS": ["INFY.NS", "WIPRO.NS", "HCLTECH.NS"],
    "INFY.NS": ["TCS.NS", "WIPRO.NS", "HCLTECH.NS"],
    "WIPRO.NS": ["TCS.NS", "INFY.NS", "TECHM.NS"],
    "HCLTECH.NS": ["TCS.NS", "INFY.NS", "WIPRO.NS"],
    "RELIANCE.NS": ["ONGC.NS", "BPCL.NS", "IOC.NS"],
    "ONGC.NS": ["RELIANCE.NS", "OIL.NS", "GAIL.NS"],
    "TATAMOTORS.NS": ["MARUTI.NS", "M&M.NS", "ASHOKLEY.NS"],
    "MARUTI.NS": ["TATAMOTORS.NS", "M&M.NS", "HYUNDAI.NS"],
    "HDFCBANK.NS": ["ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
    "ICICIBANK.NS": ["HDFCBANK.NS", "AXISBANK.NS", "SBIN.NS"],
    "SUNPHARMA.NS": ["DRREDDY.NS", "CIPLA.NS", "LUPIN.NS"],
    "HINDUNILVR.NS": ["ITC.NS", "NESTLEIND.NS", "DABUR.NS"],
    "ITC.NS": ["HINDUNILVR.NS", "BRITANNIA.NS", "NESTLEIND.NS"],
    "TATASTEEL.NS": ["JSWSTEEL.NS", "SAIL.NS", "JINDALSTEL.NS"],
    "ULTRACEMCO.NS": ["SHREECEM.NS", "AMBUJACEM.NS", "ACC.NS"],
    "BHARTIARTL.NS": ["IDEA.NS", "TATACOMM.NS"],
    "NTPC.NS": ["POWERGRID.NS", "TATAPOWER.NS", "JSWENERGY.NS"],
    "TITAN.NS": ["HAVELLS.NS", "VOLTAS.NS", "DIXON.NS"],
}

INDUSTRY_KEYWORDS: Dict[str, tuple] = {
    "IT Services": ("information technology", "software", "it services", "consulting"),
    "Oil, Gas and Energy": ("oil", "gas", "petroleum", "refin", "energy"),
    "Automobiles": ("auto", "vehicle", "motor"),
    "Banks and Financials": FINANCIAL_KEYWORDS,
    "Pharmaceuticals": ("pharma", "drug", "biotech", "healthcare"),
    "Consumer Staples": ("consumer", "household", "personal product", "food", "beverage", "tobacco"),
    "Metals and Mining": ("steel", "metal", "mining", "aluminium", "aluminum", "copper"),
    "Cement and Construction": ("cement", "construction", "building material", "engineering"),
    "Telecom": ("telecom", "communication service", "wireless"),
    "Power and Utilities": ("utility", "utilities", "power", "electric"),
    "Chemicals": ("chemical", "specialty chemical", "fertiliz", "agrochem"),
    "Consumer Durables": ("durable", "appliance", "electronic equipment", "luxury"),
    "Industrials and Conglomerates": ("industrial", "conglomerate", "machinery", "capital good"),
}


def classify_business_model(model: FinancialDataModel) -> str:
    haystack = " ".join(
        [
            model.metadata.get("Sector", ""),
            model.metadata.get("Industry", ""),
            model.company_name,
        ]
    ).lower()

    if any(keyword in haystack for keyword in FINANCIAL_KEYWORDS):
        return MODEL_FINANCIAL

    if model.ticker in INDUSTRY_UNIVERSE.get("Banks and Financials", []):
        return MODEL_FINANCIAL

    return MODEL_GENERAL


def is_financial(model: FinancialDataModel) -> bool:
    return classify_business_model(model) == MODEL_FINANCIAL


def detect_industry(model: FinancialDataModel) -> Optional[str]:
    for industry, tickers in INDUSTRY_UNIVERSE.items():
        if model.ticker in tickers:
            return industry

    haystack = " ".join(
        [model.metadata.get("Industry", ""), model.metadata.get("Sector", "")]
    ).lower()

    if not haystack.strip():
        return None

    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return industry

    return None


def industry_members(industry: str, exclude_ticker: str = "") -> List[str]:
    return [
        ticker
        for ticker in INDUSTRY_UNIVERSE.get(industry, [])
        if ticker != exclude_ticker.upper()
    ]


def direct_competitors(ticker: str, industry: Optional[str] = None) -> List[str]:
    known = DIRECT_COMPETITORS.get(ticker.upper())

    if known:
        return known

    if industry:
        return industry_members(industry, ticker)[:3]

    return []
