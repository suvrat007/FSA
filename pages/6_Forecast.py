import streamlit as st

from functions.assumptions import DEFAULT_FORECAST_YEARS, ForecastAssumptions
from functions.charts import plot_sensitivity_heatmap
from functions.components import render_methodology
from functions.config import get_scale
from functions.forecast import build_3_statement_forecast
from functions.formatting import scale_frame
from functions.methodology import FORECAST_MODEL_TOPIC
from functions.scenarios import build_scenario_models, compile_scenario_summary_table
from functions.sensitivity import SENSITIVITY_METRICS, generate_2d_sensitivity_matrix
from functions.state import ASSUMPTIONS_KEY, FORECAST_KEY, active_scale, initialize_state, require_model
from functions.theme import configure_page, render_page_header

GROWTH_OFFSETS = [-4.0, -2.0, 0.0, 2.0, 4.0]
MARGIN_OFFSETS = [-3.0, -1.5, 0.0, 1.5, 3.0]

configure_page("Forecast")
initialize_state()

model = require_model()
scale_key = active_scale()
scale = get_scale(scale_key)

render_page_header(
    "3-Statement Forecast",
    f"{model.company_name} · {DEFAULT_FORECAST_YEARS}-year driver-based projection, "
    f"values in {scale['label'].lower()}",
)

with st.expander("Forecast drivers", expanded=True):
    growth_column, working_capital_column, capital_column = st.columns(3)

    with growth_column:
        revenue_growth = st.slider("Revenue growth (% per year)", 1.0, 30.0, 10.0, step=0.5)
        ebitda_margin = st.slider("EBITDA margin (%)", 5.0, 45.0, 18.0, step=0.5)
        tax_rate = st.slider("Effective tax rate (%)", 10.0, 35.0, 25.0, step=1.0)

    with working_capital_column:
        dso = st.slider("Days sales outstanding", 10, 120, 40, step=5)
        dio = st.slider("Days inventory outstanding", 10, 150, 55, step=5)
        dpo = st.slider("Days payables outstanding", 10, 120, 45, step=5)

    with capital_column:
        capex_percent = st.slider("Capex (% of revenue)", 1.0, 25.0, 8.0, step=0.5)
        depreciation_percent = st.slider("Depreciation (% of PP&E)", 3.0, 20.0, 10.0, step=0.5)
        interest_rate = st.slider("Interest rate on debt (%)", 3.0, 15.0, 7.5, step=0.5)
        payout_ratio = st.slider("Dividend payout (% of net income)", 0.0, 80.0, 25.0, step=5.0)

assumptions = ForecastAssumptions(
    rev_growth_rates=[revenue_growth] * DEFAULT_FORECAST_YEARS,
    ebitda_margin=ebitda_margin,
    tax_rate=tax_rate,
    dso=dso,
    dio=dio,
    dpo=dpo,
    capex_percent_rev=capex_percent,
    depr_percent_ppe=depreciation_percent,
    interest_rate=interest_rate,
    dividend_payout_ratio=payout_ratio,
    n_years=DEFAULT_FORECAST_YEARS,
)

forecast = build_3_statement_forecast(model, assumptions)

st.session_state[ASSUMPTIONS_KEY] = assumptions
st.session_state[FORECAST_KEY] = forecast

integrity_warnings = forecast.validate_integrity()

if integrity_warnings:
    st.error(f"Balance sheet does not balance. {integrity_warnings[0]}")
else:
    st.success("Balance sheet identity holds across every historical and projected period.")

st.divider()

income_tab, balance_tab, cash_tab, scenario_tab, sensitivity_tab = st.tabs(
    ["Income statement", "Balance sheet", "Cash flow", "Scenarios", "Sensitivity"]
)

with income_tab:
    st.dataframe(
        scale_frame(forecast.income_statement, scale_key).style.format("{:,.2f}"),
        width="stretch",
    )

with balance_tab:
    st.dataframe(
        scale_frame(forecast.balance_sheet, scale_key).style.format("{:,.2f}"),
        width="stretch",
    )

with cash_tab:
    st.dataframe(
        scale_frame(forecast.cash_flow, scale_key).style.format("{:,.2f}"),
        width="stretch",
    )

with scenario_tab:
    scenarios = build_scenario_models(model, assumptions)
    summary = compile_scenario_summary_table(scenarios)
    numeric_columns = ["Revenue", "Net Income", "Free Cash Flow"]
    summary[numeric_columns] = summary[numeric_columns] * scale["factor"]

    st.dataframe(
        summary.style.format({column: "{:,.2f}" for column in numeric_columns}),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "The bull case adds 3 percentage points to revenue growth and 2 to the EBITDA margin. "
        "The bear case removes 4 and 3 respectively and adds 1 point to the borrowing rate."
    )

with sensitivity_tab:
    target_metric = st.radio("Target metric", SENSITIVITY_METRICS, horizontal=True)

    matrix = generate_2d_sensitivity_matrix(
        model,
        assumptions,
        [revenue_growth + offset for offset in GROWTH_OFFSETS],
        [ebitda_margin + offset for offset in MARGIN_OFFSETS],
        target_metric=target_metric,
    )

    st.plotly_chart(
        plot_sensitivity_heatmap(
            matrix * scale["factor"],
            f"Terminal year {target_metric.lower()} in {scale['label'].lower()}",
        ),
        width="stretch",
    )

st.divider()
render_methodology(FORECAST_MODEL_TOPIC)
