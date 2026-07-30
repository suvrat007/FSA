import streamlit as st

from functions.charts import plot_ratio_trend
from functions.components import render_methodology, render_provenance_legend
from functions.methodology import METHODOLOGY_REGISTRY
from functions.ratios import (
    APPROXIMATED_RATIOS,
    COGS_ASSUMPTION_NOTE,
    FINANCIAL_SUPPRESSION_NOTE,
    RATIO_GROUPS,
    compute_all_ratios,
    suppressed_ratios,
)
from functions.state import initialize_state, require_model
from functions.theme import configure_page, render_page_header

configure_page("Ratios")
initialize_state()

model = require_model()
ratios = compute_all_ratios(model)
suppressed = suppressed_ratios(model)

render_page_header(
    "Financial Ratios",
    f"{model.company_name} · {len(model.years)} reporting periods · sourced from {model.source}",
)

if suppressed:
    st.warning(FINANCIAL_SUPPRESSION_NOTE)

group_name = st.selectbox("Ratio group", list(RATIO_GROUPS.keys()))
group_items = [name for name in RATIO_GROUPS[group_name] if name in ratios.index]
group_available = [name for name in group_items if not ratios.loc[name].isna().all()]

if not group_available:
    st.info(
        f"No ratio in this group can be computed for {model.company_name}. "
        + (
            FINANCIAL_SUPPRESSION_NOTE
            if suppressed
            else "The source data does not carry the required line items."
        )
    )
    st.stop()

table_column, chart_column = st.columns(2)

with table_column:
    st.dataframe(
        ratios.loc[group_items].style.format("{:,.2f}", na_rep="n/a"),
        width="stretch",
    )

with chart_column:
    st.plotly_chart(
        plot_ratio_trend(ratios, group_available, group_name),
        width="stretch",
    )

unavailable = [name for name in group_items if name not in group_available]

if unavailable:
    st.caption(f"Shown as not available for this company: {', '.join(unavailable)}.")

approximated = [name for name in group_available if name in APPROXIMATED_RATIOS]

if approximated:
    st.info(COGS_ASSUMPTION_NOTE)

render_provenance_legend(model)

documented = [name for name in group_available if name in METHODOLOGY_REGISTRY]

if documented:
    st.divider()
    st.subheader("Methodology")

    for name in documented:
        render_methodology(name)
