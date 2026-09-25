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
- **Automated Data Ingestion:** Seamlessly pulls and normalizes raw agricultural pricing data from the UN Humanitarian Data Exchange (HDX).
- **Standardized Metric Engineering:** Converts diverse, local market units (tubers, crates, diverse bag sizes) into standardized 1 KG equivalents for accurate comparative analysis.
- **Advanced Time-Series Forecasting:** Utilizes Meta's `Prophet` library to predict 30-day future price trajectories with calculated confidence intervals.
- **SQL-First BI Dashboard:** Powered by Evidence.dev to render dynamic, code-driven analytics, interactive charts, and data tables directly from the local DuckDB warehouse.

---

## The Ghana Basket Volatility Index (GBVI)
A proprietary crown metric developed for this project. The GBVI is a composite score (0–100) that tracks month-over-month price stability across Ghana's five most critical staples (Maize, Rice, Cassava, Plantain, Tomatoes).

*   **0–30:** Stable Price Environment
*   **31–70:** Moderate Inflationary Pressure
*   **71–100:** High Food Volatility Alert

---

## System Architecture
MarketPulse relies on a modern, zero-infrastructure, locally executable data stack.

1. **Data Source:** UN WFP HDX (CSV)
2. **Staging & Warehouse:** DuckDB
3. **Analytics & ML:** Python, Pandas, Prophet
4. **Presentation Layer:** Evidence.dev (SQL-to-Markdown)
5. **Deployment:** Vercel / Netlify

---

## Prerequisites
Ensure you have the following installed on your local machine:
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) (Required for Evidence.dev)
- Git

---

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/marketpulse-ghana.git
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

### 3. Run the Data Pipeline
Execute the Python scripts sequentially to build your local DuckDB data warehouse:
```bash
# Download and ingest raw WFP data
python ingest_data.py

# Clean, normalize units, and build the staging tables
python transform_data.py
```

### 4. Launch the Dashboard
```bash
cd ui
npm install
npm run dev
```
Navigate to `http://localhost:3000` to view the interactive Evidence dashboard.
