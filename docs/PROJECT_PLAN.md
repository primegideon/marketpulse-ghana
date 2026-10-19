# MarketPulse Ghana: Analytics Engineering Implementation Plan

## 1. Executive Summary & Architecture Vision

MarketPulse Ghana is structured around a modern, local-first analytics engineering architecture:

$$\text{WFP Ghana Food Prices (HDX)} \longrightarrow \text{DuckDB Data Store} \longrightarrow \text{SQL Modeling Marts} \longrightarrow \text{Evidence.dev Web UI} \longrightarrow \text{Vercel Deployment}$$

This document outlines the end-to-end technical plan, data governance requirements, modeling specifications, and frontend design to ensure complete project alignment and future reproducibility.

---

## 2. End-to-End Pipeline Architecture

```
[HDX WFP Public Data]
   │
   ├── wfp_food_prices_gha.csv (39,038+ rows)
   └── wfp_markets_gha.csv (93 rows)
   │
   ▼ [Phase 1: Ingestion & Observability]
scripts/ingest_hdx.py
   │
   ├── data/raw/ (local cached downloads, gitignored)
   ├── agri_ghana.duckdb
   │     ├── raw_wfp_prices
   │     ├── raw_wfp_markets
   │     └── meta_pipeline_runs (operational audit & execution log)
   │
   ▼ [Phase 2: SQL Transformation & Modeling Layer]
scripts/build_marts.py (or sql/ migrations)
   │
   ├── Staging Layer:
   │     ├── stg_food_prices (unit normalization, price cleaning, typed columns)
   │     └── stg_markets (verified coordinate bounds, normalized administrative names)
   ├── Dimension Layer:
   │     ├── dim_markets (market_id, market, admin1, admin2, latitude, longitude)
   │     ├── dim_commodities (commodity_id, commodity, category, standardized_unit)
   │     └── dim_date (date, year, month, quarter, season_phase)
   └── Analytical Marts:
         ├── mart_commodity_monthly (monthly medians, MoM % change, YoY % change)
         ├── mart_regional_spreads (price differentials between production & consumer hubs)
         ├── mart_wholesale_retail_margins (spread and markup percentage)
         └── mart_pipeline_health (data freshness and pipeline audit records)
   │
   ▼ [Phase 3: Evidence.dev Web UI]
ui/ (Evidence project directory)
   │
   ├── evidence.settings.json (configured with duckdb connector to agri_ghana.duckdb)
   ├── pages/
   │     ├── index.md (Executive overview, inflation KPI cards, pipeline health card)
   │     ├── commodities.md (Time-series explorer, seasonality analysis, unit prices)
   │     ├── markets.md (Geographic map of Ghana with regional price spread overlays)
   │     ├── margins.md (Wholesale vs retail price analysis)
   │     └── governance.md (Audit log from meta_pipeline_runs, data source metadata)
   │
   ▼ [Phase 4: Production Deployment]
Vercel Cloud Hosting
   │
   └── vercel.json (configured with root directory: ui, static build execution)
```

---

## 3. Detailed Phase Breakdown

### Phase 1: Ingestion & Operational Audit Logging

* **Objective**: Automate data retrieval from HDX, preserve source idempotency, and capture full operational audit logs inside the database.
* **Key Components**:
  1. `scripts/ingest_hdx.py`:
     * HTTP stream download with checksum/size validation and network retry handling.
     * Table recreation with pre-existing snapshot retention (`raw_wfp_prices_previous`).
  2. `meta_pipeline_runs` Table in DuckDB:
     * Schema:
       * `run_id` (`VARCHAR`): Unique UUID or timestamp string for the execution batch.
       * `started_at` (`TIMESTAMP`): Run start timestamp in UTC.
       * `completed_at` (`TIMESTAMP`): Run completion timestamp in UTC.
       * `pipeline_step` (`VARCHAR`): Identifier (e.g., `hdx_ingestion`, `build_marts`).
       * `status` (`VARCHAR`): `SUCCESS`, `WARNING`, or `FAILED`.
       * `records_affected` (`BIGINT`): Count of rows ingested or updated.
       * `execution_time_s` (`DOUBLE`): Run duration in seconds.
       * `error_details` (`VARCHAR`): Detailed stack trace or exception text (NULL on success).

### Phase 2: Transformation & Dimensional Modeling Layer

* **Objective**: Convert raw, heterogeneous transaction rows into clean, standardized, business-ready analytical marts.
* **Core Modeling Logic**:
  1. **Unit Standardization**:
     * Detect and parse volume units (`100 KG`, `50 KG`, `91 KG`, `KG`, `Tubers`, `Bunch`).
     * Calculate `normalized_price_per_kg` for commodities measured by weight.
  2. **Temporal Aggregation**:
     * Calculate monthly medians per commodity, unit, price type, and market.
     * Derive national monthly benchmarks.
  3. **Growth Metrics**:
     * Calculate Month-over-Month (MoM) growth using `LAG(median_price, 1) OVER (...)`.
     * Calculate Year-over-Year (YoY) inflation using `LAG(median_price, 12) OVER (...)`.
  4. **Regional Spread Analysis**:
     * Benchmark secondary markets against primary consumption centers (e.g., Accra, Kumasi).
  5. **Data Quality & Anomaly Quarantine**:
     * Establish `audit_data_anomalies` view capturing impossible coordinate records, negative prices, or currency conversion breaks.

### Phase 3: Evidence.dev Application Development (`ui/`)

* **Objective**: Build an interactive, fast, serverless web reporting product deployable on Vercel.
* **Core Views & Deliverables**:
  1. **Executive Dashboard (`index.md`)**:
     * Top-level KPI cards: Latest Reporting Period, Monitored Staples Count, Highest 12M Inflation Riser, Most Stable / Lowest YoY Staple, Pipeline Audit Status.
     * Interactive Tabbed Visualizations: Standardized Per-KG Trends, Commercial Packaging Units (bags/crates), Top YoY Inflation Gainers ranking, and Recent Market Benchmarks data table.
  2. **Commodity Price Tracker (`commodities.md`)**:
     * Standardized Wholesale Benchmark (0 – 15 GHS / KG) tracking normalized trajectories across monitored staples.
     * Cereal Wholesale Price per KG comparing Maize vs. Imported Rice vs. Indigenous Grains.
     * Comprehensive Latest Month Price Matrix and complete Monitored Staples Directory.
  3. **Geographic Market Intelligence (`markets.md`)**:
     * Wholesale Maize Price Disparities (% above or below national median benchmark) across monitoring hubs.
     * Regional Price Level per Kilogram comparing all 10 administrative regions.
     * Market Classification Breakdown across Tiers (Major National Hub, Regional Center, Local Market) and complete Market Directory with geographic coordinates.
  4. **Wholesale vs. Retail Spreads (`margins.md`)**:
     * Multi-year Maize Price Breakdown comparing commercial acquisition vs. retail checkout per kilogram.
     * Representative Retail Markup Ranking across commodities.
     * Market-Level Spread Observations table filtered through the data quality verification rule.
  5. **Data Governance & Observability (`governance.md`)**:
     * Operational Pipeline Audit Log (`meta_pipeline_runs`) tracking execution timestamps, durations, and record volumes.
     * Data Quality & Anomaly Quarantine (`audit_data_anomalies`) detailing survey discrepancies and quarantined outlier records.
     * Comprehensive presentation of methodology and HDX source provenance.

### Phase 4: Production Build & Vercel Deployment

* **Objective**: Configure deterministic static builds and connect Vercel for continuous deployment.
* **Key Tasks**:
  1. Validate Evidence build locally using `npm run build`.
  2. Create `vercel.json` defining build commands, static data route mapping, and strict client-side anti-caching headers.
  3. Verify static SQL query extraction without database connection timeouts.

### Future Phase: Predictive Model Reintegration

* **Context**: Machine learning components (Phase 2 & Phase 3) are safely consolidated in `archive/ml/`.
* **Reintegration Path**:
  1. Preprocessing script reads directly from DuckDB `stg_food_prices`.
  2. Inference outputs are written to DuckDB as `mart_maize_forecasts`.
  3. Evidence.dev page displays actual historical prices seamlessly stitched to model projections.

---

## 4. Immediate Next Step Checklist

- [x] **Step 1**: Update `scripts/ingest_hdx.py` to record execution metrics into `meta_pipeline_runs`.
- [x] **Step 2**: Create `scripts/build_marts.py` containing modular SQL definitions for staging views, marts, and data quality anomaly quarantine.
- [x] **Step 3**: Validate marts in DuckDB (`stg_food_prices`, `dim_markets`, `dim_commodities`, `dim_calendar`, `mart_commodity_monthly`, `mart_regional_spreads`, `mart_wholesale_retail_margins`, `audit_data_anomalies`).
- [x] **Step 4**: Scaffold the Evidence.dev application inside `ui/` and connect to `agri_ghana.duckdb`.
- [x] **Step 5**: Develop initial Evidence.dev dashboard pages and test local build.
- [x] **Step 6**: Configure `vercel.json` with route rewrites and deploy to production on Vercel.
