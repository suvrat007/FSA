import streamlit as st

from functions.charts import plot_metric_comparison, plot_percentile_position
from functions.comparison import (
    METRIC_COLUMNS,
    NUMBER_FORMATS,
    SCORE_COLUMN,
    build_comparison_table,
    build_position_table,
    cohort_statistics,
    summarise_position,
)
from functions.config import get_scale
from functions.panels import fetch_cohort, render_load_failures
from functions.sectors import (
    INDUSTRY_UNIVERSE,
    detect_industry,
    direct_competitors,
    industry_members,
)
from functions.state import active_scale, cohort, initialize_state, require_model, set_cohort
from functions.theme import configure_page, render_page_header

DEFAULT_METRIC = "ROCE (%)"

configure_page("Industry")
initialize_state()

model = require_model()
scale = get_scale(active_scale())
detected = detect_industry(model)

render_page_header(
    "Industry Position",
    f"{model.company_name} ({model.ticker}) measured against its industry cohort and its "
    f"closest competitors",
)

industries = list(INDUSTRY_UNIVERSE.keys())
default_index = industries.index(detected) if detected in industries else 0

if detected:
    st.caption(f"Industry detected from company metadata: {detected}. Override below if needed.")
else:
    st.caption(
        "The industry could not be detected from this company's metadata, which is common for "
        "uploaded spreadsheets and Screener exports. Select one manually."
    )

industry = st.selectbox("Industry", industries, index=default_index)

cohort_tickers = industry_members(industry, model.ticker)
competitor_tickers = direct_competitors(model.ticker, industry)

selection_column, action_column = st.columns([3, 1])

with selection_column:
    chosen = st.multiselect(
        f"Cohort members ({len(cohort_tickers)} in {industry})",
        options=cohort_tickers,
        default=cohort_tickers,
    )

with action_column:
    st.write("")
    run = st.button("Fetch cohort", type="primary", width="stretch")

if run:
    if not chosen:
        st.warning("Select at least one cohort member.")
    else:
        loaded, failures = fetch_cohort(chosen)
        set_cohort(loaded)

        if loaded:
            st.success(f"Loaded {len(loaded)} of {len(chosen)} cohort members.")

        render_load_failures(failures, "cohort member(s)")

loaded_cohort = cohort()

if not loaded_cohort:
    st.info(
        "No cohort data has been loaded yet. Choose the members above and select Fetch cohort. "
        "This requires network access to Yahoo Finance and is cached for one hour."
    )
    st.stop()

peer_models = list(loaded_cohort.values())

comparison = build_comparison_table([model] + peer_models)
comparison["Revenue"] = comparison["Revenue"] * scale["factor"]
position = build_position_table(model, peer_models)

st.divider()
st.subheader("Where this company sits")
st.write(summarise_position(position, model.company_name))

if not position.empty:
    st.plotly_chart(
        plot_percentile_position(position, f"Percentile against the {industry} cohort"),
        width="stretch",
    )
    st.caption(
        "A percentile of 50 means the company matches the cohort median on that metric. The "
        "scale is oriented so that higher is always better, including for metrics such as debt "
        "to equity and the cash conversion cycle where a lower raw value is preferable."
    )

st.divider()
st.subheader("Position against cohort medians")

if position.empty:
    st.info("Not enough overlapping data to build a position table.")
else:
    st.dataframe(
        position.style.format(
            {
                model.ticker: "{:,.2f}",
                "Peer median": "{:,.2f}",
                "Peer best": "{:,.2f}",
                "Peer worst": "{:,.2f}",
                "Gap to median": "{:+,.2f}",
                "Percentile": "{:.0f}",
            },
            na_rep="n/a",
        ),
        width="stretch",
        hide_index=True,
    )

st.divider()

competitor_tab, cohort_tab, distribution_tab = st.tabs(
    ["Direct competitors", "Full cohort", "Cohort distribution"]
)

with competitor_tab:
    available = [ticker for ticker in competitor_tickers if ticker in loaded_cohort]

    if not available:
        st.info(
            f"None of the mapped direct competitors for {model.ticker} "
            f"({', '.join(competitor_tickers) or 'none mapped'}) are in the loaded cohort. "
            f"Add them to the selection above and fetch again."
        )
    else:
        head_to_head = build_comparison_table([model] + [loaded_cohort[t] for t in available])
        head_to_head["Revenue"] = head_to_head["Revenue"] * scale["factor"]

        st.dataframe(
            head_to_head.style.format(
                dict(NUMBER_FORMATS, **{SCORE_COLUMN: "{:.0f}"}), na_rep="n/a"
            ),
            width="stretch",
            hide_index=True,
        )
        st.caption(
            f"Closest competitors to {model.ticker} by business mix rather than by size alone."
        )

with cohort_tab:
    st.dataframe(
        comparison.style.format(
            dict(NUMBER_FORMATS, **{SCORE_COLUMN: "{:.0f}"}), na_rep="n/a"
        ),
        width="stretch",
        hide_index=True,
    )

    metric_choice = st.selectbox(
        "Chart a metric", METRIC_COLUMNS, index=METRIC_COLUMNS.index(DEFAULT_METRIC)
    )
    st.plotly_chart(
        plot_metric_comparison(comparison, metric_choice, highlight=model.company_name),
        width="stretch",
    )

with distribution_tab:
    statistics = cohort_statistics(comparison)

    if statistics.empty:
        st.info("Not enough data to describe the cohort distribution.")
    else:
        st.dataframe(statistics, width="stretch")
        st.caption(
            "Quartiles across every loaded cohort member including the target company. Count "
            "shows how many companies carried usable data for each metric."
        )
