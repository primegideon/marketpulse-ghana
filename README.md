# MarketPulse Ghana

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![DuckDB](https://img.shields.io/badge/DuckDB-In--Process-yellow.svg)
![Evidence](https://img.shields.io/badge/Evidence.dev-BI_Dashboard-blueviolet)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**An intelligent agricultural commodity price volatility and inflation forecasting engine.**

MarketPulse Ghana is an end-to-end data engineering and machine learning pipeline built to ingest, analyze, and forecast the prices of primary agricultural staples across Ghanaian markets. By leveraging open UN World Food Programme data, in-process analytical databases, and time-series forecasting, this platform provides actionable insights into regional food security and inflationary pressures.

---

## Table of Contents
- [Core Features](#core-features)
- [The Ghana Basket Volatility Index (GBVI)](#the-ghana-basket-volatility-index-gbvi)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)

---

## Core Features
- **Automated Data Ingestion:** Pulls and normalizes raw agricultural pricing data from the UN Humanitarian Data Exchange (HDX).
- **Standardized Metric Engineering:** Converts all 18 distinct local market units (tubers, bunches, diverse bag sizes from 10–250 KG) into standardized 1 KG equivalents using regex-based extraction for accurate comparative analysis.
- **Geographic Price Spread Analysis:** Compares farm-gate prices in producing regions (Brong Ahafo, Northern, Upper East, Upper West, Volta) against urban consumer prices (Greater Accra, Ashanti) to measure supply chain markup.
- **Advanced Time-Series Forecasting:** Uses Meta's `Prophet` library to predict 30-day future price trajectories with confidence intervals, trained on data through July 2023.
- **SQL-First BI Dashboard:** Powered by Evidence.dev to render dynamic, code-driven analytics, interactive charts, and data tables directly from the local DuckDB warehouse.

---

## The Ghana Basket Volatility Index (GBVI)
A proprietary crown metric developed for this project. The GBVI is a composite score (0–100) that tracks month-over-month price stability across Ghana's five most critical staple crop groups (Maize, Rice, Cassava, Plantain, Tomatoes).

**Formula (composite):**
- 60% weight: average absolute MoM% change across the 5 staple groups (magnitude of movement)
- 40% weight: standard deviation of MoM% across staples (how differently each crop behaved)
- Both components scaled to [0, 100] and bounded with `LEAST(100, GREATEST(0, ...))`

**Risk bands:**
- **0–30:** Stable Price Environment
- **31–70:** Moderate Inflationary Pressure
- **71–100:** High Food Volatility Alert

---

## System Architecture
```
WFP Ghana CSV (HDX) → DuckDB (agri_ghana.duckdb) → Prophet ML → Evidence.dev UI → Vercel
```

| Layer | Technology |
|---|---|
| Data Source | UN WFP HDX (CSV, 37,765 records, 2006–2023) |
| Staging & Warehouse | DuckDB (in-process OLAP) |
| Analytics | Python + DuckDB SQL Views |
| ML Forecasting | Python + Meta Prophet |
| Dashboard | Evidence.dev (SQL-to-Markdown BI) |
| Deployment | Vercel / Netlify (free tier) |

**Database objects:**
| Object | Type | Description |
|---|---|---|
| `raw_wfp_prices` | Table | Unmodified WFP CSV dump |
| `stg_wfp_prices` | Table | Cleaned, unit-normalized staging table |
| `fact_monthly_prices` | View | Monthly avg prices, MoM%, rolling 3m/6m averages |
| `fact_market_spreads` | View | Producing vs. urban price gap per commodity/month |
| `fact_gbvi_index` | View | GBVI composite score (0–100) per month |
| `fact_price_forecasts` | Table | Prophet 30-day forecasts with MAPE scores |

---

## Prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) (Required for Evidence.dev)
- Git

---

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/primegideon/marketpulse-ghana.git
cd marketpulse-ghana
```

### 2. Set Up the Python Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install duckdb pandas prophet scikit-learn
```

### 3. Run the Full Data Pipeline (in order)
```bash
# Step 1: Download and ingest raw WFP data into DuckDB
python ingest_data.py

# Step 2: Clean, normalize all 18 unit types, build stg_wfp_prices
python transform_data.py

# Step 3: Build the 3 analytics views (market spreads, GBVI, monthly prices)
python build_analytics_views.py

# Step 4: Run Prophet ML forecasting pipeline (may take 3-5 minutes)
python run_forecasting.py
```

### 4. Launch the Dashboard
```bash
cd ui
npm install
npm run dev
```
Navigate to `http://localhost:3000` to view the interactive Evidence dashboard.
