---
title: Trade Margins
---

# Wholesale vs. Retail Trade Margins

> **Evaluating the price spread between wholesale commercial acquisition and retail consumer checkout to measure trade markups and intermediary costs.**

---

```sql margin_overview
SELECT
    commodity,
    ROUND(MEDIAN(margin_per_kg_ghs), 2) AS median_margin_per_kg,
    ROUND(MEDIAN(retail_markup_pct) / 100.0, 4) AS median_retail_markup_pct,
    COUNT(*) AS paired_observations
FROM agri_ghana.mart_wholesale_retail_margins
WHERE retail_markup_pct BETWEEN -30 AND 200
GROUP BY commodity
ORDER BY median_retail_markup_pct DESC
```

```sql margin_trend_maize
SELECT
    date,
    year_month,
    ROUND(AVG(wholesale_price_per_kg), 2) AS avg_wholesale_per_kg,
    ROUND(AVG(retail_price_per_kg), 2) AS avg_retail_per_kg,
    ROUND(AVG(margin_per_kg_ghs), 2) AS avg_margin_per_kg
FROM agri_ghana.mart_wholesale_retail_margins
WHERE commodity = 'Maize'
GROUP BY date, year_month
ORDER BY date
```

```sql recent_margins_table
SELECT
    year_month,
    market,
    region,
    commodity,
    wholesale_price_per_kg,
    retail_price_per_kg,
    margin_per_kg_ghs,
    ROUND(retail_markup_pct / 100.0, 4) AS retail_markup_pct
FROM agri_ghana.mart_wholesale_retail_margins
WHERE date = (SELECT MAX(date) FROM agri_ghana.mart_wholesale_retail_margins)
  AND retail_markup_pct BETWEEN -30 AND 200
ORDER BY commodity, market
```

## National Maize Price Breakdown: Wholesale vs. Retail (GHS / KG)

<LineChart
  data={margin_trend_maize}
  x=date
  y={["avg_wholesale_per_kg", "avg_retail_per_kg"]}
  yFmt="#,##0.00"
  title="Wholesale vs. Retail Price per KG (Maize)"
  subtitle="The vertical spread represents the intermediary commercial trade and transport markup"
/>

---

<Tabs>
  <Tab label="Representative Markup by Crop">

### Median Retail Markup Across Commodities

> Calculated using median markup across paired market-level observations, excluding reporting anomalies to provide reliable commercial margins.

<BarChart
  data={margin_overview}
  x=commodity
  y=median_retail_markup_pct
  yFmt="pct"
  swapXY=true
  title="Median Retail Markup (%) Above Wholesale Price"
  subtitle="Standard trade spread between wholesale acquisition and retail checkout"
  labels=true
/>

  </Tab>

  <Tab label="Latest Market Margins">

### Current Market-Level Spread Observations

> Displaying verified market-level paired observations. Source unit-reporting discrepancies have been filtered out.

<DataTable data={recent_margins_table} search=true pagination=true>
  <Column id="year_month" title="Period" />
  <Column id="market" title="Market" />
  <Column id="region" title="Region" />
  <Column id="commodity" title="Commodity" />
  <Column id="wholesale_price_per_kg" title="Wholesale / KG (GHS)" fmt="#,##0.00" />
  <Column id="retail_price_per_kg" title="Retail / KG (GHS)" fmt="#,##0.00" />
  <Column id="margin_per_kg_ghs" title="Margin / KG (GHS)" fmt="#,##0.00" />
  <Column id="retail_markup_pct" title="Markup" fmt="+0.0%;-0.0%;0.0%" />
</DataTable>

  </Tab>
</Tabs>
