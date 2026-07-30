import streamlit as st

from functions.components import render_methodology
from functions.methodology import METHODOLOGY_REGISTRY
from functions.state import initialize_state
from functions.theme import configure_page, render_page_header

PIPELINE = """
Data sources            yfinance  |  Screener.in export  |  CSV or XLSX upload
                                        |
Ingestion               functions/loader_yfinance.py
                        functions/loader_screener.py
                        functions/loader_upload.py
                                        |
Normalized model        functions/datamodel.py
                        FinancialDataModel: income statement, balance sheet, cash flow
                                        |
        +---------------+---------------+---------------+
        |               |               |               |
Ratios          Accounting        3-statement       Peer
functions/      quality           forecast          benchmarking
ratios.py       functions/        functions/        functions/
                quality.py        forecast.py       peers.py
        |               |               |               |
        +---------------+-------+-------+---------------+
                                |
Presentation            app.py and pages/
Exports                 functions/export_excel.py, functions/export_html.py
"""

DESIGN_NOTES = [
    (
        "Guarded arithmetic",
        "safe_divide returns NaN instead of raising when a denominator is zero or missing, and "
        "read_item returns a caller-supplied default when a line item is absent from a source.",
    ),
    (
        "Balancing plug",
        "Each projected period absorbs any funding shortfall into short-term debt, so total "
        "assets equal total liabilities plus equity by construction rather than by coincidence.",
    ),
    (
        "Single source of truth",
        "Line item names, ratio names, and theme colours are defined once in functions/config.py "
        "and functions/ratios.py, so renaming a metric changes it everywhere at once.",
    ),
    (
        "Separated layers",
        "Every calculation lives in functions/. The pages/ directory contains presentation only, "
        "which keeps the analytics testable without a running Streamlit session.",
    ),
    (
        "Vectorised computation",
        "Common-size statements and growth rates use column-wise pandas operations rather than "
        "explicit row loops.",
    ),
    (
        "Deterministic demo data",
        "The bundled datasets use a fixed random seed for the synthetic price history, so charts "
        "and exports reproduce exactly between runs.",
    ),
]

configure_page("Methodology")
initialize_state()

render_page_header(
    "Methodology",
    "Each metric documented from both the finance and the implementation side",
)

st.subheader("Pipeline")
st.code(PIPELINE, language="text")

st.divider()
st.subheader("Metric reference")

topic = st.selectbox("Topic", list(METHODOLOGY_REGISTRY.keys()))
render_methodology(topic, expanded=True)

st.divider()
st.subheader("Design notes")

for index in range(0, len(DESIGN_NOTES), 2):
    for column, (heading, detail) in zip(st.columns(2), DESIGN_NOTES[index : index + 2]):
        with column:
            st.markdown(f"**{heading}**")
            st.caption(detail)
