# MarketPulse Ghana
### Data Pipeline and Dashboard for Agricultural Price Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Database: DuckDB](https://img.shields.io/badge/Database-DuckDB-yellow.svg)](#)
[![UI: Evidence.dev](https://img.shields.io/badge/UI-Evidence.dev-blueviolet.svg)](#)
[![CI: GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-black.svg)](#)

MarketPulse Ghana is an end-to-end open-source data pipeline and business intelligence platform that tracks and analyses agricultural commodity prices across Ghana's major markets. It translates raw UN food price data into inflation signals, supply chain insights, a composite volatility index, and a data-driven seasonal price outlook — for policymakers, agricultural economists, and food security analysts.

---

## Executive Summary

### The Business Problem

Ghana's food price landscape is fragmented across dozens of regional markets with no unified analytical layer. Raw price data published by the UN World Food Programme exists as flat CSV exports containing inconsistent units, 25 commodity types, and 10 administrative regions. Without a structured pipeline, identifying which commodities are driving inflation, which regions are absorbing the highest food cost pressures, and where supply chain inefficiencies are widening the gap between farm-gate and urban retail prices requires hours of manual spreadsheet work — and still produces no forward-looking signal.

### The Value Delivered

MarketPulse Ghana closes that gap with a fully automated, code-driven analytics stack that runs from raw CSV to a live web dashboard.

- **Unified price intelligence:** Normalises 18 different local market units into a single standardised GHS/KG metric, making cross-commodity and cross-region comparison analytically valid.
- **Supply chain transparency:** Quantifies the exact urban markup over farm-gate prices for every monitored commodity, isolating where supply chain friction is adding cost for urban households.
- **Seasonal price outlook:** Provides a data-driven seasonal signal per commodity — what the price has historically done in the coming calendar month, based on five years of retail observations — grounded in fact rather than model extrapolation.
- **Composite volatility index:** Produces the Ghana Basket Volatility Index (GBVI), a single 0–100 composite score summarising price stability across Ghana's five primary staples.

---

## System Architecture

The project follows a unified code-driven ELT architecture. A local DuckDB database acts as the single analytical hub between the ingestion layer and the web interface. No external cloud services or paid infrastructure are required.

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
  stg_wfp_prices (cleaned, unit-normalised to GHS/KG)
        |
        v
  [ 3_build_analytics_views.py ]
  fact_monthly_prices  /  fact_market_spreads  /  fact_gbvi_index
        |
        v
  [ 5_build_seasonal_outlook.py ]
  fact_seasonal_outlook (historical seasonal MoM statistics)
        |
        v
  [ Evidence.dev UI ]  -->  Vercel (production deployment)
```

### Technology Matrix

| Layer | Tool | Purpose |
| :--- | :--- | :--- |
| Data Source | WFP HDX Ghana Food Prices CSV | Raw commodity price observations across Ghana's markets |
| Storage and Warehouse | DuckDB | In-process OLAP database; single source of truth for all layers |
| Ingestion and Transformation | Python, Pandas | Unit normalisation, deduplication, and analytical view construction |
| BI Dashboard | Evidence.dev | SQL-first markdown dashboard framework; queries DuckDB directly |
| Deployment | Vercel, GitHub Actions | Static site hosting and automated pipeline validation CI |

---

## Database Schema

### Schema Objects

| Object | Type | Layer | Description |
| :--- | :--- | :--- | :--- |
| `raw_wfp_prices` | Table | Staging | Unmodified source records loaded directly from the WFP CSV |
| `stg_wfp_prices` | Table | Staging | Cleaned dataset with all units normalised to GHS per KG |
| `fact_monthly_prices` | View | Analytics | Monthly average prices by commodity and region, with MoM inflation %, 3-month and 6-month rolling averages, and price type |
| `fact_market_spreads` | View | Analytics | Farm-gate vs urban price gap by commodity, with absolute spread (GHS) and percentage margin |
| `fact_gbvi_index` | View | Analytics | Monthly GBVI composite score, risk band classification, and constituent statistics |
| `fact_seasonal_outlook` | Table | Analytics | Historical MoM statistics by commodity and calendar month: average change, range, direction frequency, and directional signal |

### Core Metric — The Ghana Basket Volatility Index (GBVI)

The GBVI is a composite 0–100 score computed monthly across Ghana's five primary consumer staples: Maize, Rice, Cassava, Plantain, and Tomatoes. It is derived from the average absolute month-over-month price change (60% weight) and its cross-commodity standard deviation (40% weight), normalised against calibrated thresholds derived from the stable-year distribution in the 2006–2023 dataset.

| Score Range | Risk Band | Interpretation |
| :--- | :--- | :--- |
| 0 – 30 | Stable | Price environment is within normal seasonal variation |
| 31 – 70 | Moderate | Inflationary pressure is present; monitoring recommended |
| 71 – 100 | High Alert | Significant price instability; intervention consideration warranted |

### Unit Conversion Reference

All source prices are normalised to GHS per kilogram. Key conversion factors are empirically derived from the WFP Ghana dataset (38,917 rows, 2006–2023):

| Unit | Commodity | Factor | Basis |
| :--- | :--- | :--- | :--- |
| bunch | plantains (apem) | 9 kg | WFP VAAM field standard for large cooking variety |
| bunch | plantains (apentu) | 6 kg | WFP VAAM field standard for small dessert variety |
| 100 tubers | cassava | 50 kg | 0.5 kg per tuber; standard small cassava tuber weight |
| 100 tubers | yam | 100 kg | 1.0 kg per tuber; yam tubers substantially heavier than cassava |
| N kg bag | all | N kg | Numeric prefix extracted via regex |

### Analytical Questions Addressed

1. **Volatility Ranking:** Which staple crops have experienced the highest retail price fluctuation over the full observation period?
2. **Geographic Price Spread:** What is the percentage price gap between farm-gate prices in producing regions and urban consumer market prices?
3. **Seasonality Patterns:** Which calendar months consistently register peak price pressure across the primary staple basket?
4. **Regional Inflation:** Which Ghanaian region has recorded the highest average food inflation rate during the recent shock period?
5. **Seasonal Signal:** What does a given commodity typically do in the coming calendar month, and how consistent is that pattern?

---

## Repository Structure

```text
marketpulse-ghana/
├── .github/
│   └── workflows/
│       └── pipeline-validation.yml   # CI: validates DuckDB row counts and GBVI range
├── pipeline/
│   ├── 1_ingest_data.py              # Loads raw WFP CSV into DuckDB staging table
│   ├── 2_transform_data.py           # Cleans data and normalises units to GHS/KG
│   ├── 3_build_analytics_views.py    # Constructs fact views: monthly prices, spreads, GBVI
│   ├── 5_build_seasonal_outlook.py   # Builds fact_seasonal_outlook: historical MoM stats
│   └── requirements.txt             # Python dependencies: duckdb, pandas, scipy
├── ui/
│   ├── pages/
│   │   ├── index.md                  # Executive Overview — GBVI, volatility ranking, seasonality
│   │   ├── commodities.md            # Commodity Price Intelligence — per-commodity drill-down
│   │   ├── forecasts.md              # Seasonal Price Outlook — historical seasonal signals
│   │   └── market_spreads.md         # Supply Chain Price Spreads — farm-gate vs urban analysis
│   ├── sources/
│   │   └── agri_ghana/               # DuckDB source connection and SQL query definitions
│   ├── theme.yaml                    # Dashboard colour palette and chart defaults
│   └── evidence.config.yaml          # Evidence project configuration
├── utils/
│   ├── validate_sql.py               # Validates all SQL blocks in MD pages against DuckDB
│   └── ...                           # Audit and diagnostic scripts
├── agri_ghana.duckdb                 # Analytical warehouse (committed build artefact)
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

Execute the pipeline scripts in sequence to build the database from scratch:

```bash
python pipeline/1_ingest_data.py
python pipeline/2_transform_data.py
python pipeline/3_build_analytics_views.py
python pipeline/5_build_seasonal_outlook.py
```

Each script logs its progress to the console. On completion, `agri_ghana.duckdb` will contain all staging tables, analytical views, and the seasonal outlook table.

### 4. Validate SQL Queries

Run the SQL validator to confirm all dashboard queries resolve against the database before deploying:

```bash
python utils/validate_sql.py
```

Expected output: `21/21 queries passed.`

### 5. Launch the Dashboard

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

- **Row count validation:** Confirms all fact tables meet minimum row thresholds, guarding against empty or corrupt pipeline runs.
- **Seasonal outlook check:** Confirms `fact_seasonal_outlook` contains entries for all 12 months for the core staple commodities.
- **GBVI range check:** Confirms all GBVI scores are within the mathematically valid 0–100 range.

### Data Quality Rules

- **Unit standardisation:** All source records are normalised from 18 distinct local market units to a single GHS/KG standard during the transformation step.
- **Non-negativity enforcement:** Prices below GHS 0.05/KG or above GHS 500/KG are excluded from analytical views as physically implausible.
- **Price type segregation:** All consumer-facing KPIs and charts use retail prices only. Wholesale prices are retained in the database but filtered at query level.
- **SQL validation:** The `utils/validate_sql.py` script validates every SQL block in every dashboard page against the live DuckDB file. Must pass before any deployment.

---

## Data Source

**UN World Food Programme — Ghana Food Prices**
Published via the Humanitarian Data Exchange (HDX). Licensed under Creative Commons Attribution for International Development (CC BY-IGO).
Coverage: January 2006 – July 2023. 38,917 price observations across 25 commodities and 10 administrative regions.
URL: [https://data.humdata.org/dataset/wfp-food-prices-for-ghana](https://data.humdata.org/dataset/wfp-food-prices-for-ghana)

---

## License

This project is licensed under the MIT License.
