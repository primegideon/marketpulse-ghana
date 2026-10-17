---
title: Market Geography
---

# Market Geography & Regional Spreads

> **Geographic price differentials, regional trading disparities, and transportation premiums across 44 Ghanaian monitoring markets.**

---

```sql market_summary
SELECT
    market,
    region,
    district,
    market_tier,
    commodities_monitored,
    total_observations,
    first_observation_date,
    last_observation_date,
    latitude,
    longitude
FROM agri_ghana.dim_markets
WHERE total_observations > 0
ORDER BY total_observations DESC
```

```sql maize_regional_spreads
WITH latest_period AS (
    SELECT MAX(date) AS max_date FROM agri_ghana.mart_regional_spreads
)
SELECT
    region,
    market,
    market_median_ghs,
    national_median_ghs,
    spread_to_national_ghs,
    ROUND(spread_to_national_pct / 100.0, 4) AS spread_to_national_pct,
    ROUND(market_median_ghs / 100.0, 2) AS market_median_ghs_per_kg,
    ROUND(national_median_ghs / 100.0, 2) AS national_median_ghs_per_kg,
    ROUND(spread_to_national_ghs / 100.0, 2) AS spread_to_national_per_kg
FROM agri_ghana.mart_regional_spreads
WHERE date = (SELECT max_date FROM latest_period)
  AND commodity = 'Maize'
  AND raw_unit = '100 KG'
  AND price_type = 'Wholesale'
ORDER BY spread_to_national_pct DESC
```

```sql regional_price_comparison
WITH latest_period AS (
    SELECT MAX(date) AS max_date FROM agri_ghana.mart_regional_spreads
)
SELECT
    region,
    ROUND(AVG(market_median_ghs_per_kg), 2) AS regional_avg_price_per_kg,
    COUNT(DISTINCT market) AS active_markets
FROM agri_ghana.mart_regional_spreads
WHERE date = (SELECT max_date FROM latest_period)
  AND commodity = 'Maize'
  AND price_type = 'Wholesale'
GROUP BY region
ORDER BY regional_avg_price_per_kg DESC
```

```sql tier_stats
SELECT
    market_tier,
    COUNT(DISTINCT market_id) AS market_count,
    SUM(total_observations) AS total_observations
FROM agri_ghana.dim_markets
WHERE total_observations > 0
GROUP BY market_tier
ORDER BY total_observations DESC
```

## Wholesale Maize Price Disparities vs National Median

<BarChart
  data={maize_regional_spreads}
  x=market
  y=spread_to_national_pct
  yFmt="pct"
  swapXY=true
  title="Maize Price Spread (% Above or Below National Benchmark)"
  subtitle="Markets with positive spreads indicate consumer import premiums; negative spreads indicate producing surplus hubs"
  labels=true
/>

---

<Tabs>
  <Tab label="Regional Averages">

### Average Wholesale Maize Price by Region (GHS / KG)

<BarChart
  data={regional_price_comparison}
  x=region
  y=regional_avg_price_per_kg
  yFmt="#,##0.00"
  title="Regional Price Level per Kilogram (GHS / KG)"
  subtitle="Cost variations driven by transport costs, regional rainfall, and localized supply conditions"
  labels=true
/>

  </Tab>

  <Tab label="Market Tier Breakdown">

### Distribution Across Market Tiers

<DataTable data={tier_stats}>
  <Column id="market_tier" title="Market Classification" />
  <Column id="market_count" title="Number of Markets" />
  <Column id="total_observations" title="Recorded Observations" fmt="#,##0" />
</DataTable>

  </Tab>

  <Tab label="All Monitoring Markets">

### Complete Market Directory & Geographic Coordinates

<DataTable data={market_summary} search=true pagination=true>
  <Column id="market" title="Market Name" />
  <Column id="region" title="Region" />
  <Column id="district" title="District" />
  <Column id="market_tier" title="Classification" />
  <Column id="commodities_monitored" title="Commodities" />
  <Column id="total_observations" title="Observations" fmt="#,##0" />
  <Column id="latitude" title="Latitude" fmt="0.00" />
  <Column id="longitude" title="Longitude" fmt="0.00" />
</DataTable>

  </Tab>
</Tabs>
