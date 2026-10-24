# MarketPulse Ghana

[![Production](https://img.shields.io/badge/Production-Live%20on%20Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://marketpulse-ghana.vercel.app)
[![Pipeline Sync](https://img.shields.io/badge/Pipeline%20Sync-Automated%20CI%2FCD-238636?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/primegideon/marketpulse-ghana/actions/workflows/data_pipeline_sync.yml)
[![Data HDX](https://img.shields.io/badge/Data-WFP%20HDX-0072BC?style=flat-square&logo=unhcr&logoColor=white)](https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320)
[![Database DuckDB](https://img.shields.io/badge/Database-DuckDB-FFF000?style=flat-square&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![UI Evidence.dev](https://img.shields.io/badge/UI-Evidence.dev-FF4F64?style=flat-square&logo=framework7&logoColor=white)](https://evidence.dev/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)

MarketPulse Ghana is an analytics engineering platform that transforms over 17 years of historical and contemporary food commodity price records across Ghana into actionable market intelligence. Built for agricultural aggregators, food processors, retail distributors, and economic analysts, the platform illuminates price inflation trajectories, standardized per-kilogram valuations, spatial market spreads, and wholesale-to-retail trade margins.

* **Live Web Application**: [marketpulse-ghana.vercel.app](https://marketpulse-ghana.vercel.app)

---

## Modern Data Stack Architecture

The platform implements an automated, local-first analytics engineering pipeline:

```
┌─────────────────────────────────┐
│   UN WFP Ghana Datasets (HDX)   │  Raw Food Prices & Market Reference CSVs
└────────────────┬────────────────┘
                 │
                 ▼ scripts/ingest_hdx.py
┌─────────────────────────────────┐
│     DuckDB Ingestion Layer      │  raw_wfp_prices (39,038 records)
│      (agri_ghana.duckdb)        │  raw_wfp_markets (93 market reference rows)
└────────────────┬────────────────┘  raw_wfp_prices_previous (snapshot)
                 │                   meta_pipeline_runs (Operational audit trail, TIMESTAMPTZ)
                 ▼ scripts/build_marts.py
┌─────────────────────────────────┐
│     Staging Views               │  stg_food_prices (unit normalization, per-kg, unit_family)
│      (Data Hygiene & Typing)    │  stg_markets (Title Case regions, coordinate casting)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Dimensional Models          │  dim_commodities (26-crop catalog, packaging units)
│                                 │  dim_markets (44 nodes, market_tier taxonomy, activity stats)
└────────────────┬────────────────┘  dim_calendar (211 months, agricultural_season encoding)
                 │
                 ▼
┌─────────────────────────────────┐
│     DuckDB Analytical Marts     │  • mart_commodity_monthly (YoY / MoM / per-KG / moving avg)
│      (SQL Transformation)       │  • mart_regional_spreads (per-kg spatial price differentials)
└────────────────┬────────────────┘  • mart_wholesale_retail_margins (MEDIAN-aggregated, verified)
                 │                   • mart_pipeline_health (Evidence.dev pipeline observability)
                 │                   • audit_data_anomalies (quarantined irregular records)
                 ▼ ui/ (Evidence.dev)
┌─────────────────────────────────┐
│      Evidence.dev Dashboard     │  Static serverless analytical web app — 5 pages
│        (Hosted on Vercel)       │  Sub-second query execution, zero cloud database costs
└─────────────────────────────────┘
```

1. **Automated Ingestion (`scripts/ingest_hdx.py`)**: Retrieves the latest food prices and market reference CSVs directly from the Humanitarian Data Exchange (HDX). Features exponential-backoff retry logic (3 attempts), a minimum row integrity floor to catch truncated downloads, idempotent snapshot preservation (`raw_wfp_prices_previous`), and UTC TIMESTAMPTZ operational audit logging into `meta_pipeline_runs`.
2. **Staging Layer (`scripts/build_marts.py`)**: Builds two staging views — `stg_food_prices` (unit parsing, `unit_family` canonical classification, per-KG normalization, Title Case region mapping) and `stg_markets` (coordinate casting, administrative normalization).
3. **Dimensional Modeling (`scripts/build_marts.py`)**: Three dimensional views — `dim_commodities` (26-crop catalog with packaging unit inventories), `dim_markets` (44 market nodes with `market_tier` taxonomy and activity statistics), and `dim_calendar` (211 months with `agricultural_season` encoding: Lean Season, Major Harvest, Post-Harvest, Minor Season).
4. **Analytical Mart Modeling (`scripts/build_marts.py`)**: Four analytical marts — `mart_commodity_monthly` (DATEDIFF-validated MoM/YoY growth, moving averages, per-KG medians), `mart_regional_spreads` (per-KG spatial price differentials), `mart_wholesale_retail_margins` (MEDIAN-aggregated trade markups with `is_verified_margin` quality flag), `mart_pipeline_health` (Evidence.dev-facing audit view). Plus `audit_data_anomalies` quarantine governance view.
5. **Exploration & Quality Assurance**: In-depth profiling, data auditing, anomaly detection, and seasonality analysis maintained in [`notebooks/exploratory_data_analysis.ipynb`](notebooks/exploratory_data_analysis.ipynb).
6. **Presentation Layer (`ui/`)**: A multi-page [Evidence.dev](https://evidence.dev/) web application with five pages (index, commodities, markets, margins, governance) compiled statically into client-side Arrow/Parquet bundles and deployed globally on Vercel.
7. **Automated Continuous Ingestion (`.github/workflows/data_pipeline_sync.yml`)**: A monthly GitHub Actions workflow that detects new HDX data releases, recalculates all analytical marts, runs the 28-check data quality assertion suite, and **opens an automated Pull Request with a Vercel preview deployment** for human review before merging to `main`.

---

## Executive Market Intelligence & Key Findings

Over 17 years (2006–2023) of standardized commodity monitoring across Ghana's primary agro-ecological markets reveal three critical structural insights:

1. **Macroeconomic Currency Shock (2022–2023)**:
   * Prior to 2022, staple food prices exhibited moderate secular growth (5–8% CAGR) punctuated by seasonal harvest cycles.
   * In 2022–2023, rapid Cedi depreciation coupled with global fuel inflation precipitated unprecedented price surges exceeding **65% YoY** across core staples (Maize, Rice, Cassava). Because price series are denominated in **Nominal GHS**, analysts should note that monetary depreciation explains the bulk of post-2021 upward momentum rather than sudden harvest failures.

2. **Spatial Transit Friction & Asymmetric Spreads**:
   * Bulky, perishable commodities with high weight-to-value ratios (Yam, Cassava) exhibit the widest regional spreads (up to **+40% in coastal sink markets like Accra** relative to surplus production hubs in Brong-Ahafo and Northern regions), driven directly by diesel and transit logistics costs.
   * Grains with high storability (Maize, Millet) exhibit tighter spatial integration across secondary regional markets.
   * The `mart_regional_spreads` mart provides per-kilogram spread metrics (`spread_to_national_per_kg`, `spread_to_national_per_kg_pct`) for any commodity, market, and time period.

3. **Agro-Ecological Seasonality & Procurement Windows**:
   * **Bimodal South**: Major harvest in August–September reliably depresses prices (`agricultural_season = 'Major Harvest'`); minor harvest in November provides a secondary cushion.
   * **Unimodal North**: Single harvest in October–November. The annual **"Lean Season" (May–July)** (`agricultural_season = 'Lean Season'`) represents the annual peak in grain prices as farm granaries deplete ahead of new crops.
   * Commercial aggregators optimizing procurement achieve 20–35% lower cost bases by purchasing during September–October harvest gluts.
   * Ghana's agro-ecological season phases are encoded directly into `dim_calendar.agricultural_season` for queryable, domain-aware analysis.

---

## Dataset Overview

The dataset is sourced from the [WFP Ghana Food Prices dataset on HDX](https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320):

* **Database Engine**: [DuckDB](https://duckdb.org/) (`agri_ghana.duckdb`)
* **Total Ingested Observations**: 39,038 food price records across 93 market nodes
* **Temporal Coverage**: January 2006 – July 2023 (211 consecutive months)
* **Geographical Coverage**: 44 monitored commercial and rural markets spanning all 10 administrative regions. The WFP monitoring program uses Ghana's **10 legacy regional boundaries** (pre-2018 referenda) to preserve 17-year longitudinal spatial continuity. Modern Ghana has 16 regions (the 2018 referenda split Brong Ahafo, Northern, Volta, and Western each into sub-regions), but standardizing to the 10 historical boundaries avoids statistical breaks in the time series.
* **Commodity Scope**: 26 primary staple crops and food commodities (Cereals, Tubers, Pulses, Vegetables, Animal Proteins)
* **Price Classifications**: Wholesale commercial bulk containers and Retail consumer checkout levels denominated in Ghanaian Cedis (GHS) and USD equivalents

---

## Repository Structure

```
marketpulse-ghana/
├── .github/
│   └── workflows/
│       └── data_pipeline_sync.yml       # Monthly automated HDX ingestion, test assertions & PR workflow
├── agri_ghana.duckdb                    # Embedded DuckDB analytical database
├── data/
│   └── raw/                             # Downloaded source CSVs from HDX
├── docs/
│   ├── PROJECT_PLAN.md                  # Comprehensive analytics engineering roadmap
│   ├── DATA_DICTIONARY.md               # Complete column-level data dictionary & schema catalog
│   └── images/                          # Visual dashboard artifacts and platform screenshots
├── scripts/
│   ├── ingest_hdx.py                    # Automated HDX downloader & DuckDB ingestor
│   ├── build_marts.py                   # Dimensional models and analytical marts builder
│   └── test_marts.py                    # Automated 28-check data contract & quality assertion suite
├── notebooks/
│   └── exploratory_data_analysis.ipynb  # Core data profiling, audit, and market analysis
├── ui/                                  # Evidence.dev analytical web application
│   ├── pages/
│   │   ├── index.md                     # National Food Price Pulse & KPIs
│   │   ├── commodities.md               # Commodity Explorer & Normalized Per-KG Affordability
│   │   ├── markets.md                   # Market Geography & Regional Disparities
│   │   ├── margins.md                   # Wholesale vs. Retail Trade Markups
│   │   └── governance.md                # Pipeline Observability & Audit Log
│   ├── sources/agri_ghana/              # DuckDB source queries and connection configs
│   ├── package.json                     # Node.js dependencies and build scripts
│   └── vercel.json                      # Vercel deployment and cache revalidation configuration
├── archive/
│   └── ml/                              # Consolidated ML forecasting pipeline (Phases 2 & 3)
│       ├── data/                        # Engineered feature matrices and train/test splits
│       ├── models/                      # Serialized XGBoost model binary
│       ├── notebooks/                   # Preprocessing, feature engineering, and CV training
│       ├── INFERENCE_PROTOCOL.md        # Downstream ML inference and reintegration specification
│       └── README.md                    # ML archive runbook
├── requirements.txt                     # Pinned Python dependencies for reproducible environments
├── .gitignore                           # Repository exclusions
└── README.md                            # Main project documentation
```

---

## Getting Started

### Prerequisites

* Python 3.10+ (Python 3.12 recommended)
* Node.js 18+ and npm (for Evidence.dev web UI)

### 1. Ingest Data & Build Marts

Clone the repository and set up the Python environment:

```powershell
git clone https://github.com/primegideon/marketpulse-ghana.git
cd marketpulse-ghana

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Execute the end-to-end ingestion, transformation, and test validation pipeline:

```powershell
# 1. Download latest data from HDX and ingest to DuckDB
python scripts/ingest_hdx.py

# 2. Build dimensional tables and analytical marts
python scripts/build_marts.py

# 3. Run automated 28-check data quality assertion suite
python scripts/test_marts.py
```

> **Note**: The 28-check assertion suite exits with code `1` on any failure, blocking bad data from the CI/CD pipeline.

### 2. Run the Evidence Web Dashboard Locally

Navigate to the `ui/` directory, synchronize sources, and start the development server:

```powershell
cd ui
npm install
npm run sync:sources
npm run sources
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to explore the dashboard.

---

## Troubleshooting & Client-Side Caching

MarketPulse Ghana executes analytical queries in the browser using **DuckDB-WASM** and client Web Workers:

* **Issue (`TProtocolException: Invalid data`)**:
  * **Cause**: Following new dataset deployments, Chromium-based browsers (Google Chrome, Microsoft Edge, Brave) may retain active Web Workers or cached binary Parquet byte ranges in persistent storage, resulting in an Apache Thrift deserialization mismatch.
  * **Resolution**:
    * **Incognito Window**: Open the dashboard in an Incognito / Private window for a clean, un-cached DuckDB-WASM session.
    * **Clear Site Storage**: In Chrome/Edge, open DevTools (`F12`), go to **Application > Storage**, click **Clear site data**, and reload the page.

---

## Machine Learning Archive

Earlier predictive modeling experiments targeting 1-month-ahead wholesale maize price forecasting with XGBoost and 9-fold walk-forward cross-validation have been preserved in [`archive/ml/`](archive/ml/). Wholesale maize was selected as the pilot commodity for its 209-month continuous coverage — the longest unbroken time series in the dataset. The holdout test period (January 2022 – June 2023) was deliberately set during the peak currency depreciation window to stress-test the model under maximum out-of-sample volatility. A formal [`archive/ml/INFERENCE_PROTOCOL.md`](archive/ml/INFERENCE_PROTOCOL.md) defines the full downstream contract for reading from `mart_commodity_monthly`, generating predictions with 95% confidence intervals, and writing results back to DuckDB for Evidence.dev visualization. Refer to [`archive/ml/README.md`](archive/ml/README.md) for the complete modeling runbook.

---

## License & Acknowledgements

* Data published by the **United Nations World Food Programme (WFP)** via the **Humanitarian Data Exchange (HDX)** in partnership with the **Ministry of Food and Agriculture (MoFA, Ghana)** and **FAO GIEWS**.
* Developed as part of the **AmaliTech Data Analytics & Engineering Capstone**.
