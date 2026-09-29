# MarketPulse Ghana
### Modern Data Stack Pipeline for Agricultural Price Volatility and Inflation Forecasting

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Database: DuckDB](https://img.shields.io/badge/Database-DuckDB-yellow.svg)](#)
[![ML: Prophet](https://img.shields.io/badge/ML-Meta%20Prophet-blue.svg)](#)
[![UI: Evidence.dev](https://img.shields.io/badge/UI-Evidence.dev-blueviolet.svg)](#)
[![CI: GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-black.svg)](#)

MarketPulse Ghana is an end-to-end open-source data pipeline and business intelligence platform that tracks, analyses, and forecasts agricultural commodity prices across Ghana's major markets, translating raw UN food price data into inflation signals, supply chain insights, and 30-day price projections for policymakers, agricultural economists, and food security analysts.

---

## Executive Summary

### The Business Problem

Ghana's food price landscape is fragmented across dozens of regional markets with no unified analytical layer. Raw price data published by the UN World Food Programme exists as flat CSV exports containing inconsistent units, 25 commodity types, and 10 administrative regions. Without a structured pipeline, identifying which commodities are driving inflation, which regions are absorbing the highest food cost pressures, and where supply chain inefficiencies are widening the gap between farm-gate and urban retail prices requires hours of manual spreadsheet work — and still produces no forward-looking signal.

### The Value Delivered

MarketPulse Ghana closes that gap with a fully automated, code-driven analytics stack that runs from raw CSV to a live web dashboard.

- **Unified price intelligence:** Normalises 18 different local market units into a single standardized GHS/KG metric, making cross-commodity and cross-region comparison analytically valid for the first time.
- **Supply chain transparency:** Quantifies the exact urban markup over farm-gate prices for every monitored commodity, isolating where supply chain friction is adding cost for urban households.
- **Forward price signal:** Generates 30-day price projections using Meta's Prophet time-series model, benchmarked against a naive baseline to provide honest model reliability reporting.
- **Composite volatility index:** Produces the Ghana Basket Volatility Index (GBVI), a single 0–100 composite score summarising price stability across Ghana's five primary staples — a metric designed for executive-level briefings and policy dashboards.

---

## System Architecture

The project follows a unified code-driven ELT architecture. A local DuckDB database acts as the single analytical hub between the ingestion layer, the machine learning engine, and the web interface. No external cloud services or paid infrastructure are required.

### Pipeline Dataflow

```text
WFP Ghana Food Prices CSV (HDX)
        |
        v
  [ 1_ingest_data.py ]
  raw_wfp_prices (DuckDB staging table)
        |
        v
  [ 2_transform_data.py ]
  stg_wfp_prices (cleaned, unit-normalized to GHS/KG)
        |
        v
  [ 3_build_analytics_views.py ]
  fact_monthly_prices  /  fact_market_spreads  /  fact_gbvi_index
        |
        v
  [ 4_run_forecasting.py ]
  fact_price_forecasts (Prophet ML output)
        |
        v
  [ Evidence.dev UI ]  -->  Vercel (production deployment)
```

### Technology Matrix

| Layer | Tool | License | Purpose |
| :--- | :--- | :--- | :--- |
| Data Source | WFP HDX Ghana Food Prices CSV | Open Data | Raw commodity price observations across Ghana's markets |
| Storage and Warehouse | DuckDB 0.10 | MIT | In-process OLAP database; serves as the single source of truth for all layers |
| Ingestion and Transformation | Python, Pandas | Open Source | Unit normalisation, deduplication, and analytical view construction |
| ML Forecasting | Meta Prophet, scikit-learn | Open Source | Time-series price projection with confidence intervals and MAPE evaluation |
| BI Dashboard | Evidence.dev v35 | MIT | SQL-first markdown dashboard framework; queries DuckDB directly |
| Deployment | Vercel (Hobby), GitHub Actions | Free Tier | Static site hosting and automated pipeline validation CI |

---

## Database Schema

### Schema Objects

| Object | Type | Layer | Description |
| :--- | :--- | :--- | :--- |
| `raw_wfp_prices` | Table | Staging | Unmodified source records loaded directly from the WFP CSV |
| `stg_wfp_prices` | Table | Staging | Cleaned dataset with all units normalised to GHS per KG |
| `fact_monthly_prices` | View | Analytics | Monthly average prices by commodity and region, with MoM inflation %, 3-month rolling average, and 6-month rolling average |
| `fact_market_spreads` | View | Analytics | Farm-gate vs urban price gap by commodity, with absolute spread (GHS) and percentage margin |
| `fact_gbvi_index` | View | Analytics | Monthly GBVI composite score, risk band classification, and constituent statistics |
| `fact_price_forecasts` | Table | Inference | 30-day Prophet model predictions with upper/lower 80% confidence bounds, model MAPE, and naive baseline MAPE |

### Core Metric — The Ghana Basket Volatility Index (GBVI)

The GBVI is a composite 0–100 score computed monthly across Ghana's five primary consumer staples: Maize, Rice, Cassava, Plantain, and Tomatoes. It is derived from the average absolute month-over-month price change and its standard deviation across the basket, then normalised to a bounded scale. The score maps to three operational risk bands:

| Score Range | Risk Band | Interpretation |
| :--- | :--- | :--- |
| 0 – 30 | Stable | Price environment is within normal seasonal variation |
| 31 – 70 | Moderate | Inflationary pressure is present; monitoring recommended |
| 71 – 100 | High Volatility Alert | Significant price instability; intervention consideration warranted |

### Analytical Questions Addressed

1. **Volatility Ranking:** Which staple crops experienced the highest price fluctuation over the last three years, measured by standard deviation of monthly price?
2. **Geographic Price Spread:** What is the average percentage price gap between producing-region farm-gate prices and urban consumer market prices for key staples?
3. **Seasonality Patterns:** Which calendar months consistently register peak price pressure across the primary staple basket?
4. **Regional Inflation Acceleration:** Which Ghanaian region recorded the highest average food inflation rate over the trailing 12-month period?

### ML Model Guardrails

The forecasting pipeline enforces four data integrity rules to prevent unrealistic outputs during macroeconomic volatility:

- **Non-Negativity Floor:** Enforces a hard minimum of GHS 0.01/KG. Prophet can produce negative price extrapolations; this constraint prevents physically impossible outputs.
- **Outlier Capping:** Price observations are bounded between GHS 0.05 and GHS 150.0/KG. Localised hyper-inflation spikes in thin markets are treated as outliers that would otherwise distort long-run trend fitting.
- **Naive Baseline Benchmarking:** Every Prophet forecast is evaluated against a naive baseline (last known value repeated). Both MAPE scores are recorded and surfaced on the dashboard for transparent model reliability reporting.
- **Bounded Projection Horizon:** Forward projections are capped at 30 days with explicit 80% confidence intervals. Longer horizons in agricultural markets carry uncertainty that exceeds the model's reliable extrapolation range.

---

## Repository Structure

```text
marketpulse-ghana/
├── .github/
│   └── workflows/
│       └── pipeline-validation.yml   # CI: validates DuckDB row counts, forecast output, and GBVI range
├── pipeline/
│   ├── 1_ingest_data.py              # Loads raw WFP CSV into DuckDB staging table
│   ├── 2_transform_data.py           # Cleans data and normalises units to GHS/KG
│   ├── 3_build_analytics_views.py    # Constructs fact views: monthly prices, spreads, GBVI
│   ├── 4_run_forecasting.py          # Trains Prophet model and writes forecasts to DuckDB
│   └── requirements.txt             # Python dependencies for the pipeline
├── ui/
│   ├── pages/
│   │   ├── index.md                  # Executive Overview — GBVI, volatility ranking, seasonality
│   │   ├── commodities.md            # Commodity Price Intelligence — per-commodity drill-down
│   │   ├── forecasts.md              # 30-Day Price Projections — Prophet forecasts with CI
│   │   └── market_spreads.md         # Supply Chain Price Spreads — farm-gate vs urban analysis
│   ├── sources/
│   │   └── agri_ghana/               # DuckDB source connection and SQL query definitions
│   └── evidence.plugins.yaml         # Evidence plugin registry
├── agri_ghana.duckdb                 # Root analytical warehouse (pipeline output)
└── README.md
```

---

## Local Setup

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher

### 1. Clone the Repository

```bash
git clone https://github.com/primegideon/marketpulse-ghana.git
cd marketpulse-ghana
```

### 2. Python Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r pipeline/requirements.txt
```

### 3. Run the Data Pipeline

Execute the four pipeline scripts in sequence to build the database from scratch:

```bash
python pipeline/1_ingest_data.py
python pipeline/2_transform_data.py
python pipeline/3_build_analytics_views.py
python pipeline/4_run_forecasting.py
```

Each script logs its progress to the console. On completion, `agri_ghana.duckdb` will contain all staging tables, analytical views, and forecast output.

### 4. Launch the Dashboard

```bash
cd ui
npm install
npm run dev
```

The local development server starts at `http://localhost:3000`.

---

## CI/CD and Quality Assurance

### Pipeline Validation (GitHub Actions)

A validation workflow runs automatically on every push or pull request to `main` that touches the `pipeline/` directory or the DuckDB file. It performs three checks:

- **Row count validation:** Confirms all four fact tables meet minimum row thresholds, guarding against empty or corrupt pipeline runs being merged.
- **Forecast output check:** Confirms that `fact_price_forecasts` contains future projections for at least three commodities.
- **GBVI range check:** Confirms all GBVI scores are within the mathematically valid 0–100 range.

### Data Quality Rules

- **Unit standardisation:** All source records are normalised from 18 distinct local market units to a single GHS/KG standard during the transformation step.
- **Deduplication:** The staging layer deduplicates on the compound key of date, market, and commodity before any downstream aggregation.
- **Non-negativity enforcement:** Negative or zero prices are treated as data entry errors and excluded from analytical views and ML training data.

---

## Data Source

**UN World Food Programme — Ghana Food Prices**
Published via the Humanitarian Data Exchange (HDX). Licensed under Creative Commons Attribution for International Development (CC BY-IGO).
URL: [https://data.humdata.org/dataset/wfp-food-prices-for-ghana](https://data.humdata.org/dataset/wfp-food-prices-for-ghana)

---

## License

This project is licensed under the MIT License.
