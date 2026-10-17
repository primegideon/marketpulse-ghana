---
title: Commodity Explorer
---

# Commodity Price Intelligence

> **Detailed time-series trajectories, normalized price-per-kilogram metrics, and inflation indicators across 26 Ghanaian food commodities.**

---

```sql commodity_inventory
SELECT
    commodity,
    category,
    reported_units,
    total_observations,
    first_recorded_date,
    last_recorded_date
FROM agri_ghana.dim_commodities
ORDER BY category, commodity
```

```sql normalized_per_kg_trends
SELECT
    date,
    year_month,
    commodity,
    price_type,
    median_price_ghs_per_kg
FROM agri_ghana.mart_commodity_monthly
WHERE median_price_ghs_per_kg IS NOT NULL
  AND price_type = 'Wholesale'
  AND commodity IN ('Maize', 'Rice (imported)', 'Rice (local)', 'Cassava', 'Cowpeas', 'Millet', 'Sorghum')
ORDER BY date, commodity
```

```sql cereal_comparison
SELECT
    date,
    commodity,
    median_price_ghs_per_kg
FROM agri_ghana.mart_commodity_monthly
WHERE category = 'cereals and tubers'
  AND price_type = 'Wholesale'
  AND median_price_ghs_per_kg IS NOT NULL
  AND commodity IN ('Maize', 'Rice (imported)', 'Millet', 'Sorghum')
ORDER BY date
```

```sql latest_prices_table
SELECT
    commodity,
    category,
    raw_unit,
    price_type,
    median_price_ghs_per_kg,
    median_price_ghs,
    ROUND(mom_pct_change / 100.0, 4) AS mom_pct,
    ROUND(yoy_pct_change / 100.0, 4) AS yoy_pct,
    markets_reporting
FROM agri_ghana.mart_commodity_monthly
WHERE date = (SELECT MAX(date) FROM agri_ghana.mart_commodity_monthly)
ORDER BY category, commodity, price_type
```

## Normalized Wholesale Prices (GHS per Kilogram)

<LineChart
  data={normalized_per_kg_trends}
  x=date
  y=median_price_ghs_per_kg
  series=commodity
  yFmt="#,##0.00"
  title="Standardized Commodity Comparison (GHS / KG)"
  subtitle="Normalized to per-kilogram price across wholesale packaging units (0 – 15 GHS / KG)"
/>

---

<Tabs>
  <Tab label="Cereal Staples">

### Major Cereal Price Dynamics

<LineChart
  data={cereal_comparison}
  x=date
  y=median_price_ghs_per_kg
  series=commodity
  yFmt="#,##0.00"
  title="Cereal Wholesale Price per KG (2006 – 2023)"
  subtitle="Maize vs. Imported Rice vs. Indigenous Grains"
/>

  </Tab>

  <Tab label="Latest Commodity Prices">

### Latest Month Commodity Price Matrix

<DataTable data={latest_prices_table} search=true pagination=true>
  <Column id="commodity" title="Commodity" />
  <Column id="category" title="Food Category" />
  <Column id="raw_unit" title="Unit" />
  <Column id="price_type" title="Type" />
  <Column id="median_price_ghs_per_kg" title="Per KG (GHS)" fmt="#,##0.00" />
  <Column id="median_price_ghs" title="Commercial Unit (GHS)" fmt="#,##0.00" />
  <Column id="mom_pct" title="MoM" fmt="+0.0%;-0.0%;0.0%" />
  <Column id="yoy_pct" title="YoY" fmt="+0.0%;-0.0%;0.0%" />
  <Column id="markets_reporting" title="Markets" />
</DataTable>

  </Tab>

  <Tab label="Commodity Catalog">

### Complete Monitored Staples Directory

<DataTable data={commodity_inventory} search=true pagination=true>
  <Column id="commodity" title="Commodity" />
  <Column id="category" title="Category" />
  <Column id="reported_units" title="Units Traded" />
  <Column id="total_observations" title="Observations" fmt="#,##0" />
  <Column id="first_recorded_date" title="First Record" />
  <Column id="last_recorded_date" title="Latest Record" />
</DataTable>

  </Tab>
</Tabs>
