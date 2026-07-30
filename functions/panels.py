from typing import Dict, List, Tuple

import streamlit as st

from functions.caching import fetch_demo_model, fetch_market_models, fetch_uploaded_model
from functions.config import OFFLINE_DEMO_COMPANIES
from functions.datamodel import FinancialDataModel
from functions.state import add_to_library, clear_library, library, remove_from_library

UPLOAD_HINT = (
    "Label rows with terms such as Revenue, EBITDA, Net Profit, Total Assets, Total Equity, or "
    "Operating Cash Flow, with one column per reporting period."
)


def render_library_builder(key_prefix: str = "library") -> None:
    ticker_tab, upload_tab, demo_tab = st.tabs(
        ["Pull by ticker", "Add a spreadsheet", "Bundled data"]
    )

    with ticker_tab:
        _render_ticker_input(key_prefix)

    with upload_tab:
        _render_upload_input(key_prefix)

    with demo_tab:
        _render_demo_input(key_prefix)


def render_library_selector(key_prefix: str = "library") -> List[FinancialDataModel]:
    current = library()

    if not current:
        st.info("The comparison set is empty. Add at least one company above.")
        return []

    selection_column, action_column = st.columns([4, 1])

    with selection_column:
        selected_labels = st.multiselect(
            "Companies in the comparison",
            options=list(current.keys()),
            default=list(current.keys()),
            key=f"{key_prefix}_selection",
        )

    with action_column:
        st.write("")

        if st.button("Clear set", width="stretch", key=f"{key_prefix}_clear"):
            clear_library()
            st.rerun()

    removal = st.selectbox(
        "Remove one company", ["None"] + list(current.keys()), key=f"{key_prefix}_removal"
    )

    if removal != "None" and st.button(f"Remove {removal}", key=f"{key_prefix}_remove_button"):
        remove_from_library(removal)
        st.rerun()

    return [current[label] for label in selected_labels if label in current]


def fetch_cohort(tickers: List[str]) -> Tuple[Dict[str, FinancialDataModel], List[str]]:
    loaded: Dict[str, FinancialDataModel] = {}
    failures: List[str] = []

    for ticker, result in fetch_market_models(tickers).items():
        if result.ok:
            loaded[ticker] = result.model
        else:
            failures.append(f"{ticker}: {result.message}")

    return loaded, failures


def render_load_failures(failures: List[str], scope: str) -> None:
    if not failures:
        return

    with st.expander(f"{len(failures)} {scope} could not be loaded", expanded=True):
        for message in failures:
            st.error(message)

    st.warning(
        "Statistics below are computed only from the companies that loaded successfully, so they "
        "describe a smaller set than requested."
    )


def _render_ticker_input(key_prefix: str) -> None:
    ticker_input = st.text_input(
        "Tickers to add, comma separated",
        placeholder="INFY.NS, WIPRO.NS, HCLTECH.NS",
        key=f"{key_prefix}_tickers",
    )

    if not st.button("Fetch and add", type="primary", key=f"{key_prefix}_fetch"):
        return

    requested = [value.strip() for value in ticker_input.split(",") if value.strip()]

    if not requested:
        st.warning("Enter at least one ticker symbol.")
        return

    loaded, failures = fetch_cohort(requested)
    added = [add_to_library(model) for model in loaded.values()]

    if added:
        st.success(f"Added {len(added)} company model(s): {', '.join(added)}.")

    for message in failures:
        st.error(message)


def _render_upload_input(key_prefix: str) -> None:
    st.caption(UPLOAD_HINT)

    uploads = st.file_uploader(
        "Statement files",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        key=f"{key_prefix}_uploads",
    )

    if not uploads or not st.button("Parse and add", type="primary", key=f"{key_prefix}_parse"):
        return

    for upload in uploads:
        result = fetch_uploaded_model(upload.getvalue(), upload.name)

        if result.ok:
            st.success(f"Added {add_to_library(result.model)}.")
        else:
            st.error(f"{upload.name}: {result.message}")


def _render_demo_input(key_prefix: str) -> None:
    choice = st.selectbox(
        "Bundled dataset", list(OFFLINE_DEMO_COMPANIES.keys()), key=f"{key_prefix}_demo"
    )

    if st.button("Add dataset", key=f"{key_prefix}_add_demo"):
        model = fetch_demo_model(OFFLINE_DEMO_COMPANIES[choice])
        st.success(f"Added {add_to_library(model)}.")
