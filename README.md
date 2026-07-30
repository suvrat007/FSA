# FinSight OS

Financial statement analysis and 3-statement modeling terminal, built with Streamlit.

FinSight OS ingests company financials from yfinance, Screener.in exports, or arbitrary
spreadsheets, normalizes divergent Ind AS and US GAAP nomenclature into a single internal model,
and then interprets them: common-size and growth analytics, twenty-three ratios, a rule-based
forensic review, a graded verdict on liquidity and solvency and profitability, a driver-linked
forward model, multi-company comparison, industry positioning, and formatted exports.

The platform does not just display ratios. The assessment engine scores each dimension against
benchmark bands and states, in prose, what the numbers mean and which constraint binds.

## Documentation

[DOCUMENTATION.md](DOCUMENTATION.md) is the full technical and financial reference: every feature,
the data format it receives and produces, the financial formula behind it, and the actual code
that implements it, with worked examples using real output from the bundled datasets.

## Architecture

The project separates calculation from presentation. Every function lives in `functions/`.
Everything in `pages/` and `app.py` is presentation only, which keeps the analytics importable
and testable without a running Streamlit session.

```
FSA/
├── app.py                      Entry point: data source controls and module index
├── functions/                  All calculation, formatting, and rendering helpers
│   ├── config.py               Line item names, currency scales, theme palette
│   ├── datamodel.py            FinancialDataModel, LoadResult, provenance tags
│   ├── formatting.py           Currency, percent, ratio formatting and guarded division
│   ├── state.py                Session state keys, company library, cohort store
│   ├── theme.py                Page configuration and stylesheet
│   ├── caching.py              Cached loader entry points and cache invalidation
│   ├── sectors.py              Business model classification and industry universe
│   ├── mock_data.py            Bundled offline datasets
│   ├── loader_yfinance.py      Yahoo Finance ingestion
│   ├── loader_screener.py      Screener.in export parser
│   ├── loader_upload.py        Generic CSV and XLSX parser
│   ├── statements.py           Common-size statements, growth rates, CAGR
│   ├── ratios.py               Ratio definitions, groups, and applicability rules
│   ├── quality.py              Seven forensic accounting rules
│   ├── assessment.py           Benchmark bands, dimension scoring, verdict text
│   ├── comparison.py           Multi-company matrix, ranking, percentile positioning
│   ├── assumptions.py          ForecastAssumptions driver container
│   ├── forecast.py             Linked 3-statement projection engine
│   ├── scenarios.py            Base, bull, and bear cases
│   ├── sensitivity.py          Two-dimensional sensitivity grid
│   ├── narrative.py            Executive narrative generation
│   ├── methodology.py          Finance and implementation reference entries
│   ├── charts.py               Plotly figure builders
│   ├── components.py           Small reusable Streamlit widgets
│   ├── panels.py               Composed page sections such as the library builder
│   ├── export_excel.py         Multi-tab openpyxl workbook writer
│   └── export_html.py          Self-contained HTML memo writer
├── pages/                      Streamlit interface, one file per module
│   ├── 1_Overview.py
│   ├── 2_Statements.py
│   ├── 3_Ratios.py
│   ├── 4_Quality_Checks.py
│   ├── 5_Assessment.py
│   ├── 6_Forecast.py
│   ├── 7_Comparison.py
│   ├── 8_Industry.py
│   ├── 9_Report.py
│   └── 10_Methodology.py
└── requirements.txt
```

Each module holds one responsibility and pages contain presentation only. Anything longer than a
screen of layout code is lifted into `functions/panels.py` so the page scripts stay readable.

`pages/` keeps its name because Streamlit's multi-page router requires that exact directory.

## Modules

| Module | Purpose |
| --- | --- |
| Overview | Company profile, market metadata, headline metrics, price history, data quality |
| Statements | Income statement, balance sheet, and cash flow in reported, common-size, and growth views |
| Ratios | Twenty-three ratios across profitability, liquidity, solvency, efficiency, and cash flow quality |
| Quality Checks | Seven forensic rules covering earnings quality, working capital, leverage, and the balance sheet identity |
| Assessment | Graded verdict per dimension with the reasoning stated in prose |
| Forecast | Driver-based projection with a balancing plug, three scenarios, and a sensitivity grid |
| Comparison | Any set of companies pulled by ticker, uploaded, or taken from bundled data |
| Industry | Position against the full industry cohort and against mapped direct competitors |
| Report | Executive memo with Excel, HTML, and CSV export |
| Methodology | Finance concept and code implementation for every documented metric |

## Assessment engine

`functions/assessment.py` turns ratios into a judgement. Each ratio is scored from 0 to 100 by
interpolating its observed value across strong, adequate, and weak benchmark thresholds; metric
scores average into a dimension score; dimensions combine using fixed weights.

| Dimension | Weight | Question answered |
| --- | --- | --- |
| Liquidity | 18% | Can obligations falling due within twelve months be met? |
| Solvency and Leverage | 24% | Is the capital structure sustainable and debt comfortably serviced? |
| Profitability | 26% | Does the business earn an adequate return on sales and on capital? |
| Operating Efficiency | 12% | How quickly is capital cycled through operations back into cash? |
| Cash Flow Quality | 20% | Do reported profits convert into actual cash? |

Critical forensic findings subtract six points each and advisory findings two, capped at eighteen.
Scores above 75 are strong, above 55 adequate, above 35 weak, below that critical. Trend compares
the dimension score in the earliest of the last three periods against the latest, so a company can
read adequate today while deteriorating.

Thresholds are general corporate norms and are not adjusted by sector, which the interface states
alongside every verdict.

## Data integrity

Three rules govern how the platform treats its inputs.

**Failures are reported, never substituted.** Loaders return a `LoadResult` carrying a status and
a message. A failed fetch surfaces as an error; it never silently falls back to demonstration data
under another company's name.

**Every line item carries its origin.** Each of the 31 standard line items is tagged `Reported`,
`Derived`, or `Not available`, and derived values state how they were computed. A dataset that
supplies eight items reads as 26% complete rather than pretending to be whole, and ratios that
depend on absent inputs read as not available instead of as zero.

**Sector-inappropriate ratios are suppressed.** Banks and financial institutions are detected from
metadata, and working capital, inventory, and EBITDA-based ratios are withheld rather than
computed into meaningless numbers. Liquidity and efficiency are left unscored for them, and the
leverage caveat is stated explicitly.

## Caching

Market fetches are cached for one hour and parsed uploads for thirty minutes, keyed on ticker or
on file bytes. Cohort fetches on the industry page reuse the same cache, so loading a nine-member
industry a second time is instant. The sidebar carries a manual cache clear.

## Units

Statements are held in a base unit of ten million currency units, that is one crore. The bundled
datasets and Screener.in exports are already denominated this way; the Yahoo Finance loader
divides incoming absolute figures by the same factor on ingest. The reporting scale selector in
the sidebar converts that base unit into crore, lakh, million, or billion for display only, so
every stored figure remains directly comparable across data sources.

## Forecast engine

`functions/forecast.py` projects each period in sequence: income statement lines from the driver
assumptions, working capital from DSO, DIO, and DPO, the PP&E schedule from capex less
depreciation, retained earnings from net income less dividends, and then the cash flow statement.
Any residual funding gap is absorbed into short-term debt, so total assets equal total
liabilities plus equity by construction rather than by coincidence. The projection inherits the
opening balance from the final historical period, which means the identity holds for the whole
timeline provided the historical data balances.

## Setup

Requires Python 3.9 or later.

```bash
pip install -r requirements.txt
streamlit run app.py
```

The application opens at `http://localhost:8501` and loads a bundled offline dataset on first
run, so no network access is required to explore it.

## Deployment

1. Push the repository to GitHub.
2. Create an app at [share.streamlit.io](https://share.streamlit.io/).
3. Select the repository and set the main file path to `app.py`.

## Data sources

| Source | Notes |
| --- | --- |
| Bundled dataset | Reliance Industries and Tata Consultancy Services, balanced five-year models with deterministic synthetic price history |
| Yahoo Finance | Live statements and quote metadata via yfinance; reports an error when a symbol returns nothing |
| Screener.in export | Parses the `Data Sheet` tab of a standard `.xlsx` export |
| Custom spreadsheet | Generic CSV or XLSX parser matching line items by keyword against roughly forty label variants |

For a custom spreadsheet, put line item labels in the first column and one column per reporting
period. Recognised labels include Revenue, Sales, EBITDA, Operating Profit, EBIT, Interest,
Profit Before Tax, Net Profit, Total Assets, Total Debt, Borrowings, Total Equity, Net Worth,
Receivables, Inventory, Payables, and Operating Cash Flow. Unmatched rows are listed back as a
caveat rather than dropped silently.

## Not in scope

Valuation is deliberately absent. There is no DCF, no WACC, no multiples-based fair value, and no
price target. The forecast produces statements, not a valuation, and the assessment grades
financial condition rather than whether the shares are cheap.
