# MarketPulse Ghana

[![Data: WFP HDX](https://img.shields.io/badge/Data-WFP_HDX-blue.svg)](https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320)
[![Database: DuckDB](https://img.shields.io/badge/Database-DuckDB-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![UI: Evidence.dev](https://img.shields.io/badge/UI-Evidence.dev-FF6B6B)](https://evidence.dev/)
[![Deployment: Vercel](https://img.shields.io/badge/Deployment-Vercel-000000?logo=vercel&logoColor=white)](https://vercel.com/)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org/)

MarketPulse Ghana is an analytics engineering project that transforms over 17 years of historical food price records in Ghana into high-fidelity market intelligence. Built for small and medium-sized enterprises (SMEs), agricultural traders, food processors, and policy analysts, the platform illuminates price volatility, seasonal trends, regional spreads, and market dynamics across key food staples.

---

## Architecture

The project implements a modern, local-first analytics engineering pipeline designed for fast analytical query execution and web-based reporting:

```
┌─────────────────────────────────┐
│  WFP Ghana Food Prices (HDX)    │  Raw source data (CSV)
└────────────────┬────────────────┘
                 │
                 ▼ Ingestion & SQL Transformations
┌─────────────────────────────────┐
│     DuckDB Analytical Engine    │  Embedded analytical data store
│       (agri_ghana.duckdb)       │  • raw_wfp_prices (37,765 rows)
└────────────────┬────────────────┘
                 │
                 ▼ SQL Queries & Reactive Markdown
┌─────────────────────────────────┐
│       Evidence.dev Web UI       │  Interactive reports, charts, and metrics
│       (Hosted on Vercel)        │  Fast, serverless static analytical app
└─────────────────────────────────┘
```

1. **Ingestion & Storage**: Granular market records collected by the United Nations World Food Programme (WFP) are loaded directly into an embedded [DuckDB](https://duckdb.org/) database (`agri_ghana.duckdb`), eliminating heavyweight database overhead while providing columnar analytical speed.
2. **Exploration & Quality Assurance**: In-depth profiling, data auditing, anomaly detection, and seasonality analysis are maintained in [`notebooks/exploratory_data_analysis.ipynb`](notebooks/exploratory_data_analysis.ipynb).
3. **Semantic Reporting & Visualization**: Dashboards and business intelligence products are authored with [Evidence.dev](https://evidence.dev/) markdown-based reports, rendered statically and deployed via Vercel.

---

## Dataset Overview

The dataset is sourced from the [WFP Ghana Food Prices dataset on HDX](https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320):

* **Local Table**: `raw_wfp_prices` in `agri_ghana.duckdb`
* **Total Observations**: 37,765 records
* **Temporal Coverage**: January 2006 – July 2023 (210 consecutive months)
* **Geographical Coverage**: 44 commercial and rural markets spanning all major regions in Ghana
* **Commodity Scope**: 26 primary staple crops and food commodities (including Maize, Rice, Cassava, Yam, Plantains, Cowpeas, and Tomatoes)
* **Price Classifications**: Wholesale and Retail price levels denominated in Ghanaian Cedis (GHS) and USD equivalents

> **Note on Interpretation**: Prices reflect observed market transactions and serve as macroeconomic market context. They do not incorporate individual firm transport logistics, inventory carrying costs, or retail margins.

---

## Repository Structure

```
marketpulse-ghana/
├── agri_ghana.duckdb       # DuckDB analytical database (table: raw_wfp_prices)
├── notebooks/
│   └── exploratory_data_analysis.ipynb  # Core data profiling, audit, and market analysis
├── archive/
│   └── ml/                 # Consolidated Machine Learning pipeline (Phases 2 & 3)
│       ├── data/           # Engineered feature matrices, train/test splits, predictions
│       ├── models/         # Serialized XGBoost model binary and metadata JSON
│       ├── notebooks/      # Preprocessing, feature engineering, and CV training notebooks
│       └── README.md       # ML archive overview and reactivation runbook
├── .gitignore              # Repository exclusions (build files, credentials, local roadmaps)
└── README.md               # Main project documentation
```

---

## Exploratory Data Analysis & Quality Auditing

The active analysis notebook [`notebooks/exploratory_data_analysis.ipynb`](notebooks/exploratory_data_analysis.ipynb) establishes data health across the entire historical snapshot:

* **Integrity Audits**: Verified zero unhandled null values, zero duplicate observation keys (`date, market_id, commodity_id, unit, pricetype`), and validated geographic coordinate bounds within Ghana.
* **Price Distribution & Seasonality**: Identified cyclical harvest patterns and documented structural price breaks coinciding with global food commodity inflation and local currency devaluations.
* **Exchange Rate Verification**: Flagged implied historical exchange rate variations between local GHS and recorded USD prices for analytical awareness.

---

## Getting Started

### Prerequisites

* Python 3.10+ (Python 3.12 recommended)
* Node.js 18+ (for Evidence.dev UI development)

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/primegideon/marketpulse-ghana.git
   cd marketpulse-ghana
   ```

2. **Configure Python Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install duckdb pandas numpy matplotlib seaborn jupyter nbconvert ipykernel
   ```

3. **Query DuckDB Directly**:
   You can query the DuckDB store using Python or the DuckDB CLI:
   ```python
   import duckdb

   con = duckdb.connect("agri_ghana.duckdb", read_only=True)
   print(con.execute("SELECT commodity, pricetype, COUNT(*) FROM raw_wfp_prices GROUP BY ALL LIMIT 10").df())
   con.close()
   ```

4. **Run the Analysis Notebook**:
   ```powershell
   jupyter lab notebooks/exploratory_data_analysis.ipynb
   ```

---

## Machine Learning Archive

Earlier predictive modeling experiments targeting 1-month-ahead wholesale maize price forecasting with XGBoost and walk-forward cross-validation have been consolidated in [`archive/ml/`](archive/ml/). When analytical reporting is established, predictive models can be reintroduced as a downstream forecast mart. Refer to [`archive/ml/README.md`](archive/ml/README.md) for complete details.

---

## License & Acknowledgements

* Data courtesy of the **United Nations World Food Programme (WFP)** via the **Humanitarian Data Exchange (HDX)**.
* Project developed as part of the **AmaliTech Data Analytics / Data Engineering Capstone**.
