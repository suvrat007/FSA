import streamlit as st

from functions.charts import plot_ratio_trend
from functions.components import render_finding, render_methodology
from functions.quality import RULE_COUNT, SEVERITY_CRITICAL, SEVERITY_WARNING, evaluate_red_flags
from functions.ratios import CFO_TO_NET_INCOME, compute_all_ratios
from functions.state import initialize_state, require_model
from functions.theme import configure_page, render_page_header

configure_page("Quality Checks")
initialize_state()

model = require_model()
findings = evaluate_red_flags(model)
ratios = compute_all_ratios(model)

critical_count = sum(1 for finding in findings if finding["severity"] == SEVERITY_CRITICAL)
warning_count = sum(1 for finding in findings if finding["severity"] == SEVERITY_WARNING)

render_page_header(
    "Accounting Quality",
    f"{model.company_name} · rule-based forensic review of the reported statements",
)

summary_columns = st.columns(3)
summary_columns[0].metric("Rules evaluated", RULE_COUNT)
summary_columns[1].metric("Critical findings", critical_count)
summary_columns[2].metric("Advisory findings", warning_count)

st.divider()

findings_column, context_column = st.columns([1.3, 0.7])

with findings_column:
    st.subheader("Findings")

    if not findings:
        st.success("No findings were raised. All seven rules passed for every reporting period.")
    else:
        for finding in findings:
            render_finding(finding)

with context_column:
    st.subheader("Earnings quality")

    if CFO_TO_NET_INCOME in ratios.index:
        st.plotly_chart(
            plot_ratio_trend(ratios, [CFO_TO_NET_INCOME], "Operating cash flow to net income"),
            width="stretch",
        )

    st.caption(
        "A ratio persistently below 0.8x suggests reported earnings are driven by non-cash "
        "accruals, delayed collections, or inventory build rather than cash generation."
    )

    render_methodology(CFO_TO_NET_INCOME)
