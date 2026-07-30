import streamlit as st

from functions.charts import plot_metric_comparison, plot_multi_company_trend, plot_peer_radar
from functions.comparison import (
    METRIC_BY_COLUMN,
    METRIC_COLUMNS,
    NUMBER_FORMATS,
    RADAR_METRICS,
    SCORE_COLUMN,
    build_comparison_table,
    build_metric_series,
    build_rank_table,
)
from functions.config import get_scale
from functions.panels import render_library_builder, render_library_selector
from functions.ratios import RATIO_GROUPS_FLAT, ROE
from functions.state import active_scale, add_to_library, initialize_state, library, require_model
from functions.theme import configure_page, render_page_header

DEFAULT_METRIC = "ROCE (%)"

configure_page("Comparison")
initialize_state()

model = require_model()
scale = get_scale(active_scale())

render_page_header(
    "Company Comparison",
    "Build a comparison set from live tickers, uploaded statements, or bundled datasets",
)

if not library():
    add_to_library(model)

render_library_builder("comparison")

st.divider()

selected_models = render_library_selector("comparison")

if not selected_models:
    st.stop()

comparison = build_comparison_table(selected_models)
comparison["Revenue"] = comparison["Revenue"] * scale["factor"]
table_formats = dict(NUMBER_FORMATS, **{SCORE_COLUMN: "{:.0f}"})

st.subheader(f"Comparison matrix (revenue in {scale['label'].lower()})")
st.dataframe(
    comparison.style.format(table_formats, na_rep="n/a"),
    width="stretch",
    hide_index=True,
)
st.caption(
    "Overall score and grade come from the assessment engine, so a company that leads on a "
    "single ratio can still rank lower once leverage, cash conversion, and forensic findings are "
    "weighed together. Companies drawn from different sources may not be strictly like for like."
)

st.divider()

metric_column, rank_column = st.columns(2)

with metric_column:
    st.subheader("Single metric")
    metric_choice = st.selectbox(
        "Metric", METRIC_COLUMNS, index=METRIC_COLUMNS.index(DEFAULT_METRIC)
    )
    st.plotly_chart(
        plot_metric_comparison(comparison, metric_choice, highlight=model.company_name),
        width="stretch",
    )
    st.caption(
        "Higher is better for this metric."
        if METRIC_BY_COLUMN[metric_choice].higher_is_better
        else "Lower is better for this metric."
    )

with rank_column:
    st.subheader("Rank by metric")
    ranks = build_rank_table(comparison)
    rank_columns = [column for column in METRIC_COLUMNS if column in ranks.columns]
    st.dataframe(
        ranks.style.format("{:.0f}", subset=rank_columns, na_rep="n/a"),
        width="stretch",
        hide_index=True,
    )
    st.caption("Rank 1 is the best performer on that metric within the selected set.")

if len(selected_models) > 1:
    st.divider()
    st.subheader("Profile against the set average")
    st.plotly_chart(
        plot_peer_radar(comparison, RADAR_METRICS, target_label=model.company_name),
        width="stretch",
    )
    st.caption(
        f"{model.company_name} against the average of the other companies in the set. Axes share "
        f"one scale, so a metric expressed in percent will dominate one expressed as a multiple."
    )

st.divider()
st.subheader("Trend across companies")

trend_ratio = st.selectbox("Ratio", RATIO_GROUPS_FLAT, index=RATIO_GROUPS_FLAT.index(ROE))
series = build_metric_series(selected_models, trend_ratio)

if series.empty:
    st.info("None of the selected companies carry this ratio across their reporting periods.")
else:
    st.plotly_chart(plot_multi_company_trend(series, trend_ratio), width="stretch")
    st.caption(
        "Periods are aligned by label. Companies with different financial year ends or different "
        "period counts will not line up exactly."
    )
