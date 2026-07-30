import streamlit as st

from functions.charts import plot_balance_sheet_stack
from functions.components import render_data_quality, render_provenance_legend
from functions.config import BASE_UNIT_LABEL, get_scale
from functions.formatting import scale_frame
from functions.state import active_scale, initialize_state, require_model
from functions.statements import (
    compute_common_size_balance_sheet,
    compute_common_size_income_statement,
    compute_yoy_growth,
)
from functions.theme import configure_page, render_page_header

VIEW_ABSOLUTE = "Reported"
VIEW_GROWTH = "Year-on-year growth"
VIEW_COMMON_SIZE_REVENUE = "Common size (% of revenue)"
VIEW_COMMON_SIZE_ASSETS = "Common size (% of total assets)"

configure_page("Statements")
initialize_state()

model = require_model()
scale_key = active_scale()
scale = get_scale(scale_key)

render_page_header(
    "Financial Statements",
    f"{model.company_name} · values reported in {scale['label'].lower()} "
    f"(source data denominated in {BASE_UNIT_LABEL})",
)


def render_statement(statement, view, common_size_builder, key) -> None:
    selected = st.radio("View", view, horizontal=True, key=key)

    if selected == VIEW_ABSOLUTE:
        st.dataframe(
            scale_frame(statement, scale_key).style.format("{:,.2f}"),
            width="stretch",
        )
    elif selected == VIEW_GROWTH:
        st.dataframe(
            compute_yoy_growth(statement).style.format("{:+.2f}%", na_rep="n/a"),
            width="stretch",
        )
    else:
        st.dataframe(
            common_size_builder().style.format("{:.2f}%", na_rep="n/a"),
            width="stretch",
        )


income_tab, balance_tab, cash_tab = st.tabs(["Income statement", "Balance sheet", "Cash flow"])

with income_tab:
    render_statement(
        model.income_statement,
        [VIEW_ABSOLUTE, VIEW_COMMON_SIZE_REVENUE, VIEW_GROWTH],
        lambda: compute_common_size_income_statement(model),
        "income_view",
    )

with balance_tab:
    render_statement(
        model.balance_sheet,
        [VIEW_ABSOLUTE, VIEW_COMMON_SIZE_ASSETS, VIEW_GROWTH],
        lambda: compute_common_size_balance_sheet(model),
        "balance_view",
    )

    st.divider()
    st.plotly_chart(plot_balance_sheet_stack(model), width="stretch")

with cash_tab:
    render_statement(
        model.cash_flow,
        [VIEW_ABSOLUTE, VIEW_GROWTH],
        lambda: model.cash_flow,
        "cash_view",
    )

st.divider()
render_provenance_legend(model)
render_data_quality(model)
