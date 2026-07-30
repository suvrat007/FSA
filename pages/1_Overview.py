import pandas as pd
import streamlit as st

from functions.charts import plot_revenue_profit_trend, plot_stock_price_history
from functions.components import render_data_quality, render_kpi_card
from functions.config import IS_NET_INCOME, IS_REVENUE, currency_symbol
from functions.datamodel import read_item
from functions.formatting import format_currency, format_ratio
from functions.sectors import MODEL_FINANCIAL, classify_business_model, detect_industry
from functions.state import active_scale, initialize_state, require_model
from functions.theme import configure_page, render_page_header

configure_page("Overview")
initialize_state()

model = require_model()
scale_key = active_scale()
metadata = model.metadata
market = model.market_data
latest_year = model.years[-1]
symbol = currency_symbol(model.currency)

render_page_header(
    f"{model.company_name} ({model.ticker})",
    f"{metadata.get('Sector', 'Unclassified')} · {metadata.get('Industry', 'Unclassified')} · "
    f"{metadata.get('Exchange', 'N/A')} · sourced from {model.source}",
)

if classify_business_model(model) == MODEL_FINANCIAL:
    st.warning(
        "This company is classified as a bank or financial institution. Working capital, "
        "inventory, and EBITDA-based ratios are suppressed throughout the platform because they "
        "carry no economic meaning for a lender."
    )

first_row = st.columns(4)

with first_row[0]:
    render_kpi_card(
        f"Revenue {latest_year}",
        format_currency(
            read_item(model.income_statement, IS_REVENUE, latest_year), scale_key, model.currency
        ),
    )

with first_row[1]:
    render_kpi_card(
        f"Net income {latest_year}",
        format_currency(
            read_item(model.income_statement, IS_NET_INCOME, latest_year), scale_key, model.currency
        ),
    )

with first_row[2]:
    market_cap = market.get("market_cap", 0)
    render_kpi_card(
        "Market capitalisation",
        format_currency(market_cap, scale_key, model.currency) if market_cap else "N/A",
    )

with first_row[3]:
    share_price = market.get("share_price", 0)
    render_kpi_card("Share price", f"{symbol} {share_price:,.2f}" if share_price else "N/A")

st.write("")

second_row = st.columns(4)

with second_row[0]:
    render_kpi_card("Price / earnings", format_ratio(market.get("pe_ratio")))

with second_row[1]:
    render_kpi_card("Price / book", format_ratio(market.get("pb_ratio")))

with second_row[2]:
    render_kpi_card("Beta", format_ratio(market.get("beta")))

with second_row[3]:
    high = market.get("52w_high", 0)
    low = market.get("52w_low", 0)
    render_kpi_card(
        "52-week range",
        f"{symbol}{low:,.0f} - {symbol}{high:,.0f}" if high else "N/A",
    )

st.divider()

chart_column, profile_column = st.columns([3, 2])

with chart_column:
    st.plotly_chart(plot_revenue_profit_trend(model), width="stretch")

with profile_column:
    st.subheader("Business profile")
    st.write(metadata.get("Description", "No description is available for this company."))
    st.markdown(
        f"- Headquarters: {metadata.get('Headquarters', 'N/A')}\n"
        f"- Reporting periods: {', '.join(model.years)}\n"
        f"- Reporting currency: {model.currency}\n"
        f"- Industry classification: {detect_industry(model) or 'not detected'}"
    )

render_data_quality(model)

price_history = market.get("price_history")

if isinstance(price_history, pd.DataFrame) and not price_history.empty:
    st.divider()
    st.plotly_chart(
        plot_stock_price_history(price_history, model.company_name),
        width="stretch",
    )
