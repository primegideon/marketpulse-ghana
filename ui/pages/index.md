---
title: National Food Price Pulse
---

# MarketPulse Ghana: Food Price Intelligence

> **Comprehensive food commodity market intelligence across Ghana, derived from the UN World Food Programme (WFP) Humanitarian Data Exchange database.**

---

```sql pipeline_status
SELECT
    started_at,
    status,
    records_affected,
    execution_time_s
FROM agri_ghana.mart_pipeline_health
ORDER BY started_at DESC
LIMIT 1
```

```sql headline_kpis
WITH latest_month AS (
    SELECT MAX(date) AS max_date FROM agri_ghana.mart_commodity_monthly
),
active_stats AS (
    SELECT
        COUNT(DISTINCT commodity) AS tracked_commodities,
        COUNT(DISTINCT raw_unit) AS tracked_units
    FROM agri_ghana.mart_commodity_monthly
    WHERE date = (SELECT max_date FROM latest_month)
),
top_riser AS (
    SELECT
        commodity,
        raw_unit,
        price_type,
        yoy_pct_change
    FROM agri_ghana.mart_commodity_monthly
    WHERE date = (SELECT max_date FROM latest_month)
      AND yoy_pct_change IS NOT NULL
    ORDER BY yoy_pct_change DESC
    LIMIT 1
)
SELECT
    strftime((SELECT max_date FROM latest_month), '%B %Y') AS latest_period,
    (SELECT tracked_commodities FROM active_stats) AS total_commodities,
    (SELECT commodity || ' (' || price_type || ')' FROM top_riser) AS top_riser_name,
    (SELECT yoy_pct_change FROM top_riser) AS top_riser_yoy
```

```sql staple_trends
SELECT
    date,
    year_month,
    commodity,
    raw_unit,
    price_type,
    median_price_ghs,
    median_price_ghs_per_kg,
    mom_pct_change,
    yoy_pct_change
FROM agri_ghana.mart_commodity_monthly
WHERE commodity IN ('Maize', 'Rice (imported)', 'Rice (local)', 'Cassava', 'Plantains', 'Yam')
  AND price_type = 'Wholesale'
ORDER BY date, commodity
```

```sql yoy_inflation_ranking
WITH latest_month AS (
    SELECT MAX(date) AS max_date FROM agri_ghana.mart_commodity_monthly
)
SELECT
    commodity || ' [' || raw_unit || ' - ' || price_type || ']' AS series_label,
    yoy_pct_change,
    median_price_ghs
FROM agri_ghana.mart_commodity_monthly
WHERE date = (SELECT max_date FROM latest_month)
  AND yoy_pct_change IS NOT NULL
ORDER BY yoy_pct_change DESC
LIMIT 10
```

```sql monthly_table_preview
SELECT
    year_month,
    commodity,
    price_type,
    raw_unit,
    median_price_ghs,
    mom_pct_change,
    yoy_pct_change,
    markets_reporting
FROM agri_ghana.mart_commodity_monthly
WHERE commodity IN ('Maize', 'Rice (imported)', 'Cassava', 'Yam', 'Tomatoes')
ORDER BY date DESC, commodity
LIMIT 15
```

<BigValue
  data={headline_kpis}
  value=latest_period
  title="Latest Reporting Period"
/>

<BigValue
  data={headline_kpis}
  value=total_commodities
  title="Monitored Food Staples"
/>

<BigValue
  data={headline_kpis}
  value=top_riser_name
  title="Highest 12M Inflation"
  subtitle={"+" + headline_kpis[0].top_riser_yoy + "% YoY"}
/>

<BigValue
  data={pipeline_status}
  value=status
  title="Pipeline Status"
  subtitle={"Last Audit: " + pipeline_status[0].records_affected + " records (" + pipeline_status[0].execution_time_s + "s)"}
/>

---

<Tabs>
  <Tab label="Staple Price Trajectories">

## Primary Staple Trends (Wholesale, GHS)

<LineChart
  data={staple_trends}
  x=date
  y=median_price_ghs
  series=commodity
  title="National Monthly Median Wholesale Prices"
  subtitle="Observed across 44 Ghanaian wholesale markets (2006 – 2023)"
/>

  </Tab>

  <Tab label="YoY Inflation Rankings">

## Highest Year-over-Year Price Growth

<BarChart
  data={yoy_inflation_ranking}
  x=series_label
  y=yoy_pct_change
  swapXY=true
  title="Top Food Price Inflation Gainers (% Year-over-Year)"
  subtitle="Relative price change compared to the exact same calendar month in the previous year"
  labels=true
/>

  </Tab>

  <Tab label="Recent Monthly Data">

## Recent Monthly Market Benchmarks

<DataTable data={monthly_table_preview} search=true pagination=true>
  <Column id="year_month" title="Period" />
  <Column id="commodity" title="Commodity" />
  <Column id="price_type" title="Type" />
  <Column id="raw_unit" title="Unit" />
  <Column id="median_price_ghs" title="Median (GHS)" fmt="#,##0.00" />
  <Column id="mom_pct_change" title="MoM (%)" fmt="+0.0;-0.0;0.0" />
  <Column id="yoy_pct_change" title="YoY (%)" fmt="+0.0;-0.0;0.0" />
  <Column id="markets_reporting" title="Markets" />
</DataTable>

  </Tab>
</Tabs>

---

> **Source**: World Food Programme (WFP) Humanitarian Data Exchange (HDX). Data processed through DuckDB analytical marts.
