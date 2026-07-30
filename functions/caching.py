from typing import Dict, List

import streamlit as st

from functions.datamodel import LoadResult
from functions.loader_screener import load_screener_excel
from functions.loader_upload import load_uploaded_statement
from functions.loader_yfinance import load_yfinance_data
from functions.mock_data import get_mock_company_model

MARKET_TTL_SECONDS = 3600
FILE_TTL_SECONDS = 1800
MAX_CACHE_ENTRIES = 128


@st.cache_data(ttl=MARKET_TTL_SECONDS, max_entries=MAX_CACHE_ENTRIES, show_spinner=False)
def fetch_market_model(ticker: str) -> LoadResult:
    return load_yfinance_data(ticker)


@st.cache_data(ttl=FILE_TTL_SECONDS, max_entries=32, show_spinner=False)
def fetch_screener_model(payload: bytes, filename: str) -> LoadResult:
    import io

    return load_screener_excel(io.BytesIO(payload), filename.rsplit(".", 1)[0])


@st.cache_data(ttl=FILE_TTL_SECONDS, max_entries=32, show_spinner=False)
def fetch_uploaded_model(payload: bytes, filename: str) -> LoadResult:
    import io

    return load_uploaded_statement(io.BytesIO(payload), filename)


@st.cache_data(ttl=MARKET_TTL_SECONDS, max_entries=8, show_spinner=False)
def fetch_demo_model(ticker: str):
    return get_mock_company_model(ticker)


def fetch_market_models(tickers: List[str]) -> Dict[str, LoadResult]:
    results: Dict[str, LoadResult] = {}
    unique = list(dict.fromkeys(ticker.strip().upper() for ticker in tickers if ticker.strip()))

    if not unique:
        return results

    progress = st.progress(0.0, text="Fetching company data")

    for index, ticker in enumerate(unique, start=1):
        progress.progress(index / len(unique), text=f"Fetching {ticker} ({index} of {len(unique)})")
        results[ticker] = fetch_market_model(ticker)

    progress.empty()

    return results


def clear_cache() -> None:
    st.cache_data.clear()
