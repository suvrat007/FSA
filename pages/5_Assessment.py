import streamlit as st

from functions.assessment import DIMENSION_ORDER, GRADE_UNAVAILABLE, assess_company
from functions.charts import plot_dimension_scores
from functions.components import (
    render_assessment_caveats,
    render_data_quality,
    render_dimension,
    render_grade_badge,
)
from functions.sectors import MODEL_FINANCIAL, classify_business_model
from functions.state import initialize_state, require_model
from functions.theme import configure_page, render_page_header

configure_page("Assessment")
initialize_state()

model = require_model()
assessment = assess_company(model)

render_page_header(
    "Assessment and Verdict",
    f"{model.company_name} ({model.ticker}) · interpreted from {len(model.years)} reporting "
    f"periods ending {assessment.period}",
)

if classify_business_model(model) == MODEL_FINANCIAL:
    st.warning(
        "This company was identified as a bank or financial institution. Liquidity and operating "
        "efficiency are not scored, and leverage thresholds calibrated for non-financial "
        "corporates do not apply cleanly to a lender's balance sheet."
    )

verdict_column, score_column = st.columns([2, 1])

with verdict_column:
    st.subheader("Overall verdict")
    st.write(assessment.verdict)

with score_column:
    render_grade_badge(
        assessment.grade,
        assessment.score,
        caption=f"{assessment.critical_findings} critical and "
        f"{assessment.advisory_findings} advisory forensic finding(s)",
    )

scored = [
    dimension
    for dimension in assessment.dimensions
    if dimension.applicable and dimension.grade != GRADE_UNAVAILABLE
]

if scored:
    st.plotly_chart(
        plot_dimension_scores(
            [dimension.name for dimension in scored],
            [dimension.score for dimension in scored],
            "Score by dimension",
        ),
        width="stretch",
    )

st.divider()
st.subheader("Dimension by dimension")

for name in DIMENSION_ORDER:
    dimension = assessment.dimension(name)

    if dimension is not None:
        render_dimension(dimension)

st.divider()

summary_column, caveat_column = st.columns([1, 1])

with summary_column:
    st.subheader("Scorecard")
    st.dataframe(
        assessment.summary_frame().style.format({"Score": "{:.0f}"}, na_rep="not scored"),
        width="stretch",
        hide_index=True,
    )

with caveat_column:
    st.subheader("Reading the verdict")
    st.caption(
        "Each dimension is scored from its ratios against general corporate benchmark bands, "
        "then combined using fixed weights. Forensic findings subtract from the total. Scores "
        "above 75 are strong, above 55 adequate, above 35 weak, and below that critical."
    )
    render_assessment_caveats(assessment)

render_data_quality(model)
