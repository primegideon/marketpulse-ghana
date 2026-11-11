---
title: Commodity Explorer
---

# Commodity Price Intelligence

> **Detailed time-series trajectories, normalized price-per-kilogram metrics, and inflation indicators across 26 Ghanaian food commodities.**

---

```sql category_options
SELECT DISTINCT category AS value, category AS label
FROM agri_ghana.dim_commodities
ORDER BY category
```

```sql commodity_inventory
SELECT
    commodity,
    category,
    wholesale_units,
    retail_units,
    total_observations,
    first_recorded_date,
    last_recorded_date
FROM agri_ghana.dim_commodities
ORDER BY category, commodity
```

```sql normalized_per_kg_trends
SELECT
    m.date,
    m.year_month,
    m.commodity,
    m.price_type,
    ROUND(MEDIAN(m.median_price_ghs_per_kg), 2) AS median_price_ghs_per_kg
FROM agri_ghana.mart_commodity_monthly m
JOIN agri_ghana.dim_commodities c ON m.commodity = c.commodity
WHERE m.median_price_ghs_per_kg IS NOT NULL
  AND m.price_type = 'Wholesale'
  AND m.commodity IN ('Maize', 'Rice (imported)', 'Rice (local)', 'Cassava', 'Cowpeas', 'Millet', 'Sorghum')
  AND ('{selected_category}' = 'All' OR c.category = '{selected_category}')
GROUP BY m.date, m.year_month, m.commodity, m.price_type
ORDER BY m.date, m.commodity
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
    m.commodity,
    m.category,
    m.raw_unit,
    m.price_type,
    m.median_price_ghs_per_kg,
    m.median_price_ghs,
    ROUND(m.mom_pct_change / 100.0, 4) AS mom_pct,
    ROUND(m.yoy_pct_change / 100.0, 4) AS yoy_pct,
    m.markets_reporting
FROM agri_ghana.mart_commodity_monthly m
JOIN agri_ghana.dim_commodities c ON m.commodity = c.commodity
WHERE m.date = (SELECT MAX(date) FROM agri_ghana.mart_commodity_monthly)
  AND ('{selected_category}' = 'All' OR c.category = '{selected_category}')
ORDER BY m.category, m.commodity, m.price_type
```

<Dropdown data={category_options} name=selected_category defaultValue="All" title="Filter by Food Category">
    <DropdownOption value="All" valueLabel="All Categories" />
</Dropdown>

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
  <Column id="wholesale_units" title="Wholesale Packaging" />
  <Column id="retail_units" title="Retail Unit" />
  <Column id="total_observations" title="Observations" fmt="#,##0" />
  <Column id="first_recorded_date" title="First Record" />
  <Column id="last_recorded_date" title="Latest Record" />
</DataTable>

  </Tab>
</Tabs>
