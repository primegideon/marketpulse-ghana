# marketpulse-ghana

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![DuckDB](https://img.shields.io/badge/DuckDB-In--Process-yellow.svg)
![Evidence](https://img.shields.io/badge/Evidence.dev-BI_Dashboard-blueviolet)

**MarketPulse – Agri-Commodity Price Volatility & Inflation Forecaster**

MarketPulse Ghana is an open-source data pipeline and business intelligence dashboard designed to track, analyze, and forecast food prices across Ghana. It ingests raw agricultural pricing data from the UN World Food Programme and transforms it into actionable insights regarding inflation, supply chain efficiency, and regional food security.



---

## Core Features

*   **Automated Data Standardization:** The raw UN dataset contains 18 different local market units (from 100kg bags to "bunches" of plantains). The pipeline algorithmically converts all commodities into a standardized price-per-kg metric for accurate comparative analysis.
*   **Geographic Market Spread Analysis:** Compares farm-gate prices in major producing regions (Brong Ahafo, Northern, Upper East, Upper West, Volta) against retail prices in major urban centers (Greater Accra, Ashanti). This isolates the exact markup added by the supply chain.
*   **The GBVI Score:** The Ghana Basket Volatility Index is a proprietary 0–100 composite metric tracking price stability for 5 core consumer staples (Maize, Rice, Cassava, Plantain, Tomatoes). It measures both the magnitude and standard deviation of month-over-month retail inflation.
*   **Machine Learning Forecasting:** Integrates Meta's `Prophet` time-series forecasting model to project retail price trajectories for key staples up to 3 months into the future, trained on nearly 4 years of historical retail data (2019-2023).
*   **Code-Driven BI Dashboard:** The entire visualization layer is built using Evidence.dev, generating interactive markdown-based analytics by querying the local DuckDB warehouse directly.

---

## System Architecture

The project follows a unified code-driven architecture where a local database acts as the single bridge between data engineering, machine learning, and the web interface.

**Pipeline Flow:**
`WFP Ghana CSV (HDX) → DuckDB → Python (Pandas/Prophet) → Evidence.dev`

**Database Objects (DuckDB):**
| Object | Type | Description |
|---|---|---|
| `raw_wfp_prices` | Table | Unmodified raw CSV dataset |
| `stg_wfp_prices` | Table | Cleaned dataset normalized to GHS/kg with latitude/longitude |
| `fact_monthly_prices` | View | Monthly retail & wholesale averages, rolling trends, and MoM% |
| `fact_market_spreads` | View | Producing vs. Urban price gaps by commodity |
| `fact_gbvi_index` | View | The 0–100 retail volatility score |
| `fact_price_forecasts` | Table | 3-month future retail predictions from the Prophet ML model |

---

## Local Setup & Installation

### Prerequisites
*   Python 3.10+
*   Node.js 18+

### 1. Repository Setup
```bash
git clone https://github.com/primegideon/marketpulse-ghana.git
cd marketpulse-ghana
```

### 2. Python Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install duckdb pandas prophet scikit-learn
```

### 3. Run the Data Engine
The pipeline is segmented into sequential steps. Run them in order to construct the database from scratch:

```bash
# Step 1: Download raw data and load into DuckDB
python pipeline/1_ingest_data.py

# Step 2: Clean data and normalize units
python pipeline/2_transform_data.py

# Step 3: Build analytics views (Spreads, GBVI, Monthly trends)
python pipeline/3_build_analytics_views.py

# Step 4: Train Prophet ML model and generate forecasts
python pipeline/4_run_forecasting.py
```

### 4. Launch the Dashboard
```bash
cd ui
npm install
npm run dev
```
Navigate to `http://localhost:3000` to view the interactive dashboard.
