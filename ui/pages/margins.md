---
title: Trade Margins
---

# Wholesale vs. Retail Trade Margins

> **Evaluating the price spread between wholesale commercial acquisition and retail consumer checkout to measure trade markups and intermediary costs.**

---

```sql margin_overview
SELECT
    commodity,
    ROUND(AVG(margin_per_kg_ghs), 2) AS avg_margin_per_kg,
    ROUND(AVG(retail_markup_pct), 1) AS avg_retail_markup_pct,
    COUNT(*) AS paired_observations
FROM agri_ghana.mart_wholesale_retail_margins
GROUP BY commodity
ORDER BY avg_retail_markup_pct DESC
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
    retail_markup_pct
FROM agri_ghana.mart_wholesale_retail_margins
WHERE date = (SELECT MAX(date) FROM agri_ghana.mart_wholesale_retail_margins)
ORDER BY retail_markup_pct DESC
```

## National Maize Price Breakdown: Wholesale vs. Retail (GHS / KG)

<LineChart
  data={margin_trend_maize}
  x=date
  y={["avg_wholesale_per_kg", "avg_retail_per_kg"]}
  title="Wholesale vs. Retail Price per KG (Maize)"
  subtitle="The vertical gap represents the intermediary trade and distribution margin"
/>

---

<Tabs>
  <Tab label="Average Markup by Crop">

### Retail Markup Percentage Across Commodities

<BarChart
  data={margin_overview}
  x=commodity
  y=avg_retail_markup_pct
  swapXY=true
  title="Average Retail Markup (%) Above Wholesale Price"
  subtitle="Higher percentages reflect higher spoilage risks, handling fees, or retailer pricing power"
  labels=true
/>

  </Tab>

  <Tab label="Latest Market Margins">

### Current Market-Level Spread Observations

<DataTable data={recent_margins_table} search=true pagination=true>
  <Column id="year_month" title="Period" />
  <Column id="market" title="Market" />
  <Column id="region" title="Region" />
  <Column id="commodity" title="Commodity" />
  <Column id="wholesale_price_per_kg" title="Wholesale / KG (GHS)" fmt="#,##0.00" />
  <Column id="retail_price_per_kg" title="Retail / KG (GHS)" fmt="#,##0.00" />
  <Column id="margin_per_kg_ghs" title="Margin / KG (GHS)" fmt="#,##0.00" />
  <Column id="retail_markup_pct" title="Markup (%)" fmt="+0.0;-0.0;0.0" />
</DataTable>

  </Tab>
</Tabs>
