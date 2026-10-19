---
title: Governance & Observability
---

# Data Architecture & Pipeline Observability

> **Production audit trail, automated ingestion metrics, and source data provenance for MarketPulse Ghana.**

---

```sql pipeline_runs
SELECT
    run_id,
    started_at,
    completed_at,
    pipeline_step,
    status,
    records_affected,
    execution_time_s,
    COALESCE(error_details, 'None') AS error_details
FROM agri_ghana.mart_pipeline_health
ORDER BY started_at DESC
```

```sql run_summary
SELECT
    COUNT(*) AS total_recorded_runs,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful_runs,
    ROUND(AVG(execution_time_s), 2) AS avg_duration_seconds,
    MAX(completed_at) AS last_execution_timestamp
FROM agri_ghana.mart_pipeline_health
```

<BigValue
  data={run_summary}
  value=total_recorded_runs
  title="Total Pipeline Executions"
/>

<BigValue
  data={run_summary}
  value=successful_runs
  title="Successful Runs"
/>

<BigValue
  data={run_summary}
  value=avg_duration_seconds
  title="Avg Run Duration"
  subtitle="Seconds"
/>

<BigValue
  data={run_summary}
  value=last_execution_timestamp
  title="Last Execution"
/>

---

## Operational Pipeline Audit Log (`meta_pipeline_runs`)

Every execution of the automated HDX download, DuckDB ingestion, and analytical mart transformation writes an audit record into DuckDB to guarantee system observability.

```sql anomaly_log
SELECT
    date,
    market,
    region,
    commodity,
    anomaly_type,
    anomaly_details,
    resolution_status
FROM agri_ghana.audit_data_anomalies
ORDER BY date DESC, commodity
LIMIT 50
```

<DataTable data={pipeline_runs} search=true pagination=true>
  <Column id="run_id" title="Run ID" />
  <Column id="started_at" title="Started At" />
  <Column id="pipeline_step" title="Pipeline Step" />
  <Column id="status" title="Status" />
  <Column id="records_affected" title="Records" fmt="#,##0" />
  <Column id="execution_time_s" title="Duration (s)" fmt="0.00" />
  <Column id="error_details" title="Errors" />
</DataTable>

---

## Data Quality & Anomaly Quarantine (`audit_data_anomalies`)

Statistical anomalies, survey discrepancies, and unit inversions are quarantined from commercial reporting marts and logged here for transparent data governance:

<DataTable data={anomaly_log} search=true pagination=true>
  <Column id="date" title="Survey Date" />
  <Column id="market" title="Market" />
  <Column id="region" title="Region" />
  <Column id="commodity" title="Commodity" />
  <Column id="anomaly_type" title="Anomaly Type" />
  <Column id="anomaly_details" title="Audit Description" />
  <Column id="resolution_status" title="Governance Status" />
</DataTable>

---

## Analytical Methodology & Macroeconomic Context

### 1. Nominal vs. Real Pricing (Monetary Inflation)
All prices presented across MarketPulse Ghana are denominated in **Nominal Ghanaian Cedis (GHS)** and USD equivalents at prevailing historical exchange rates. Over the 17-year monitoring period (2006–2023), Ghana experienced significant macroeconomic currency depreciation and periods of high headline inflation (exceeding 54% Year-over-Year in late 2022). Analysts evaluating multi-year secular growth curves must note that price increases reflect national monetary expansion and exchange-rate pressures alongside physical agricultural supply dynamics.

### 2. Administrative Boundaries (10 Legacy vs. 16 Modern Regions)
The WFP monitoring program anchors spatial observations to Ghana's **10 historical administrative regions** established prior to the 2018 national referenda:
* **Brong Ahafo**: Encompasses modern *Bono*, *Bono East*, and *Ahafo* regions.
* **Northern**: Encompasses modern *Northern*, *Savannah*, and *North East* regions.
* **Volta**: Encompasses modern *Volta* and *Oti* regions.
* **Western**: Encompasses modern *Western* and *Western North* regions.

Standardizing to the 10 legacy regions preserves longitudinal spatial continuity across all 17 years without statistical breaks.

### 3. Agro-Ecological Seasonality & Crop Cycles
Price dynamics across Ghana are governed by distinct agro-climatic rainfall regimes:
* **Bimodal Rainfall (Southern & Middle Belts)**: Features two distinct harvests—the **Major Season harvest** (August–September) and the **Minor Season harvest** (November–December).
* **Unimodal Rainfall (Northern Grain Belt)**: A single concentrated rainy season yields a single major harvest between October and November.
* **The "Lean Season" (Hunger Gap)**: Occurs annually between **May and July** across northern markets as household granaries deplete ahead of the new harvest, creating predictable cyclical price surges for grains (Maize, Millet, Sorghum).

---

## Data Provenance & Technical Architecture

1. **Source Registry**:
   * Published by: **United Nations World Food Programme (WFP)**
   * Hosted on: [Humanitarian Data Exchange (HDX)](https://data.humdata.org/dataset/wfp-food-prices-for-ghana)
   * National Partners: **Ministry of Food and Agriculture (MoFA, Ghana)** and **FAO GIEWS**
2. **Analytical Engine**:
   * [DuckDB](https://duckdb.org/) embedded columnar database powering zero-copy local analytics.
   * Automated SQL marts generate normalized pricing per kilogram, calendar-aware temporal lags, spatial spreads, and quarantined anomaly layers.
3. **Data Quality & Testing**:
   * Automated regression test suite (`scripts/test_marts.py`) verifying 27 data contracts, composite primary keys, price non-negativity, and margin validity before each CI/CD deployment.
   * Complete schema catalog documented in the [Data Dictionary](file:///docs/DATA_DICTIONARY.md).
4. **Presentation Layer**:
   * Built with [Evidence.dev](https://evidence.dev/) compiled statically into WebAssembly and client-side Parquet for sub-second page loads on Vercel.
