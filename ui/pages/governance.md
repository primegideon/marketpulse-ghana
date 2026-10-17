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

## Data Provenance & Methodology

1. **Source Registry**:
   * Published by: **United Nations World Food Programme (WFP)**
   * Hosted on: [Humanitarian Data Exchange (HDX)](https://data.humdata.org/dataset/wfp-food-prices-for-ghana)
   * National Partners: **Ministry of Food and Agriculture (MoFA, Ghana)** and **FAO GIEWS**
2. **Analytical Engine**:
   * [DuckDB](https://duckdb.org/) embedded columnar database powering zero-copy local analytics.
   * Automated SQL marts generate normalized pricing per kilogram, temporal lags, and regional spreads.
3. **Presentation Layer**:
   * Built with [Evidence.dev](https://evidence.dev/) compiled statically for sub-second page loads and zero server maintenance on Vercel.
