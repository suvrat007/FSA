import streamlit as st

from functions.caching import (
    clear_cache,
    fetch_demo_model,
    fetch_market_model,
    fetch_screener_model,
    fetch_uploaded_model,
)
from functions.components import render_module_card
from functions.config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    CURRENCY_SCALES,
    OFFLINE_DEMO_COMPANIES,
    get_scale,
)
from functions.state import SCALE_KEY, initialize_state, require_model, set_active_model
from functions.theme import configure_page, render_page_header

SOURCE_DEMO = "Bundled dataset"
SOURCE_YAHOO = "Yahoo Finance"
SOURCE_SCREENER = "Screener.in export"
SOURCE_UPLOAD = "Custom spreadsheet"

MODULES = [
    ("Overview", "Company profile, market metadata, price history, and data quality."),
    ("Statements", "Income statement, balance sheet, and cash flow with common-size and growth views."),
    ("Ratios", "Ratios across profitability, liquidity, solvency, efficiency, and cash quality."),
    ("Quality Checks", "Seven forensic accounting rules covering earnings quality and the balance sheet identity."),
    ("Assessment", "Graded verdict on liquidity, solvency, profitability, efficiency, and cash conversion."),
    ("Forecast", "Driver-based 3-statement projection with scenarios and a sensitivity grid."),
    ("Comparison", "Compare any set of companies pulled by ticker or added from a spreadsheet."),
    ("Industry", "Position the company against its full industry cohort and its direct competitors."),
    ("Report", "Executive memo with Excel, HTML, and CSV export."),
    ("Methodology", "Finance concept and code implementation for every metric in the platform."),
]

configure_page("Home")
initialize_state()

st.sidebar.markdown(f"### {APP_NAME}")
st.sidebar.caption(f"Version {APP_VERSION}")
st.sidebar.divider()

data_source = st.sidebar.radio(
    "Data source",
    [SOURCE_DEMO, SOURCE_YAHOO, SOURCE_SCREENER, SOURCE_UPLOAD],
)

if data_source == SOURCE_DEMO:
    selected_company = st.sidebar.selectbox("Company", list(OFFLINE_DEMO_COMPANIES.keys()))

    if st.sidebar.button("Load dataset", type="primary", width="stretch"):
        with st.spinner(f"Loading {selected_company}"):
            set_active_model(fetch_demo_model(OFFLINE_DEMO_COMPANIES[selected_company]))
        st.sidebar.success(f"Loaded {selected_company}.")

elif data_source == SOURCE_YAHOO:
    ticker = st.sidebar.text_input("Ticker symbol", "TCS.NS")

    if st.sidebar.button("Fetch data", type="primary", width="stretch"):
        with st.spinner(f"Fetching {ticker}"):
            result = fetch_market_model(ticker)

        if result.ok:
            set_active_model(result.model)
            st.sidebar.success(f"Loaded {result.model.company_name}.")
        else:
            st.sidebar.error(result.message)

elif data_source == SOURCE_SCREENER:
    screener_file = st.sidebar.file_uploader("Screener.in export", type=["xlsx"])

    if screener_file and st.sidebar.button("Parse export", type="primary", width="stretch"):
        with st.spinner("Parsing export"):
            result = fetch_screener_model(screener_file.getvalue(), screener_file.name)

        if result.ok:
            set_active_model(result.model)
            st.sidebar.success(f"Loaded {result.model.company_name}.")
        else:
            st.sidebar.error(result.message)

else:
    custom_file = st.sidebar.file_uploader("Statement file", type=["csv", "xlsx", "xls"])

    if custom_file and st.sidebar.button("Parse file", type="primary", width="stretch"):
        with st.spinner("Parsing file"):
            result = fetch_uploaded_model(custom_file.getvalue(), custom_file.name)

        if result.ok:
            set_active_model(result.model)
            st.sidebar.success(f"Loaded {result.model.company_name}.")
        else:
            st.sidebar.error(result.message)

st.sidebar.divider()

st.session_state[SCALE_KEY] = st.sidebar.selectbox(
    "Reporting scale",
    options=list(CURRENCY_SCALES.keys()),
    format_func=lambda key: CURRENCY_SCALES[key]["label"],
)

if st.sidebar.button("Clear cached data", width="stretch"):
    clear_cache()
    st.sidebar.success("Cache cleared. The next fetch will hit the source directly.")

model = require_model()

render_page_header(APP_NAME, APP_TAGLINE)

st.info(
    f"Active model: {model.company_name} ({model.ticker}). "
    f"Source: {model.source}. "
    f"Periods: {', '.join(model.years)}. "
    f"Reporting scale: {get_scale(st.session_state[SCALE_KEY])['label']}. "
    f"Line item completeness: {model.completeness():.0f}%."
)

st.subheader("Modules")

for row_start in range(0, len(MODULES), 5):
    for column, (name, detail) in zip(st.columns(5), MODULES[row_start : row_start + 5]):
        with column:
            render_module_card(name, detail)

st.caption(
    "Market data is cached for one hour and uploaded files for thirty minutes. Loaders never "
    "substitute demonstration data when a source fails; a failed fetch is reported as an error."
)
