import streamlit as st

from functions.assessment import assess_company
from functions.components import render_finding, render_grade_badge
from functions.export_excel import export_model_to_excel
from functions.export_html import export_report_to_html
from functions.narrative import SECTION_ORDER, generate_executive_narrative
from functions.quality import evaluate_red_flags
from functions.state import FORECAST_KEY, active_assumptions, initialize_state, require_model
from functions.theme import configure_page, render_page_header

EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

configure_page("Report")
initialize_state()

model = require_model()
forecast = st.session_state.get(FORECAST_KEY)
assumptions = active_assumptions()

narratives = generate_executive_narrative(model)
findings = evaluate_red_flags(model)
assessment = assess_company(model)

render_page_header(
    "Investment Memo",
    f"{model.company_name} ({model.ticker}) · sourced from {model.source}",
)

badge_column, _ = st.columns([1, 2])

with badge_column:
    render_grade_badge(assessment.grade, assessment.score, caption="Overall assessment")

if forecast is None:
    st.info("Open the forecast module first to include projected statements in the exports.")

for section in SECTION_ORDER:
    if section not in narratives:
        continue

    st.subheader(section)
    st.write(narratives[section])

if findings:
    st.subheader("Findings in detail")

    for finding in findings:
        render_finding(finding)

with st.expander("Data quality and assumptions carried into this memo", expanded=False):
    for caveat in assessment.caveats:
        st.markdown(f"- {caveat}")

st.divider()
st.subheader("Exports")

excel_column, html_column, csv_column = st.columns(3)

with excel_column:
    st.markdown("**Excel workbook**")
    st.caption("Summary, assessment, data quality, statements, ratios, findings, and scenarios.")
    st.download_button(
        "Download .xlsx",
        data=export_model_to_excel(model, forecast, assumptions),
        file_name=f"{model.ticker}_financial_model.xlsx",
        mime=EXCEL_MIME,
        width="stretch",
    )

with html_column:
    st.markdown("**HTML memo**")
    st.caption("Printable memo carrying the verdict, dimension grades, tables, and caveats.")
    st.download_button(
        "Download .html",
        data=export_report_to_html(model, forecast).encode("utf-8"),
        file_name=f"{model.ticker}_research_memo.html",
        mime="text/html",
        width="stretch",
    )

with csv_column:
    st.markdown("**Income statement**")
    st.caption("Normalized income statement in the platform base unit.")
    st.download_button(
        "Download .csv",
        data=model.income_statement.to_csv().encode("utf-8"),
        file_name=f"{model.ticker}_income_statement.csv",
        mime="text/csv",
        width="stretch",
    )
