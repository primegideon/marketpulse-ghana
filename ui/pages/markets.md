---
title: Market Geography
---

# Market Geography & Regional Spreads

> **Geographic price differentials, regional trading disparities, and transportation premiums across 44 Ghanaian monitoring markets.**

---

```sql tier_options
SELECT DISTINCT market_tier AS value, market_tier AS label
FROM agri_ghana.dim_markets
WHERE total_observations > 0
ORDER BY market_tier
```

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

```sql map_data
WITH latest_period AS (
    SELECT MAX(date) AS max_date FROM agri_ghana.mart_regional_spreads
)
SELECT
    r.market,
    r.region,
    m.latitude,
    m.longitude,
    r.spread_to_national_pct,
    r.market_median_ghs_per_kg,
    m.market_tier
FROM agri_ghana.mart_regional_spreads r
JOIN agri_ghana.dim_markets m ON r.market = m.market
WHERE r.date = (SELECT max_date FROM latest_period)
  AND r.commodity = 'Maize'
  AND r.raw_unit = '100 KG'
  AND r.price_type = 'Wholesale'
  AND m.latitude IS NOT NULL
  AND m.longitude IS NOT NULL
  AND ('${inputs.selected_tier.value}' = 'All' OR m.market_tier = '${inputs.selected_tier.value}')
ORDER BY r.market_median_ghs_per_kg DESC
```

```sql maize_regional_spreads
WITH latest_period AS (
    SELECT MAX(date) AS max_date FROM agri_ghana.mart_regional_spreads
)
SELECT
    r.region,
    r.market,
    r.market_median_ghs,
    r.national_median_ghs,
    r.spread_to_national_ghs,
    ROUND(r.spread_to_national_pct / 100.0, 4) AS spread_to_national_pct,
    r.market_median_ghs_per_kg,
    m.market_tier
FROM agri_ghana.mart_regional_spreads r
JOIN agri_ghana.dim_markets m ON r.market = m.market
WHERE r.date = (SELECT max_date FROM latest_period)
  AND r.commodity = 'Maize'
  AND r.raw_unit = '100 KG'
  AND r.price_type = 'Wholesale'
  AND ('${inputs.selected_tier.value}' = 'All' OR m.market_tier = '${inputs.selected_tier.value}')
ORDER BY r.spread_to_national_pct DESC
```

```sql regional_price_comparison
WITH latest_period AS (
    SELECT MAX(date) AS max_date FROM agri_ghana.mart_regional_spreads
)
SELECT
    r.region,
    ROUND(AVG(r.market_median_ghs_per_kg), 2) AS regional_avg_price_per_kg,
    COUNT(DISTINCT r.market) AS active_markets
FROM agri_ghana.mart_regional_spreads r
JOIN agri_ghana.dim_markets m ON r.market = m.market
WHERE r.date = (SELECT max_date FROM latest_period)
  AND r.commodity = 'Maize'
  AND r.price_type = 'Wholesale'
  AND ('${inputs.selected_tier.value}' = 'All' OR m.market_tier = '${inputs.selected_tier.value}')
GROUP BY r.region
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

<Dropdown data={tier_options} name=selected_tier defaultValue="All" title="Filter by Market Tier">
    <DropdownOption value="All" valueLabel="All Tiers" />
</Dropdown>

## Maize Price Spread Across Ghana Markets

<BubbleMap
  data={map_data}
  lat=latitude
  long=longitude
  size=market_median_ghs_per_kg
  value=market_median_ghs_per_kg
  pointName=market
  startingLat=7.95
  startingLong=-1.02
  startingZoom=6
  title="Maize Price Spread Across Ghana Markets"
  subtitle="Bubble size reflects wholesale maize price per kilogram (GHS/KG) across monitoring markets"
/>

> **Reading the map**: Larger bubbles indicate markets that deviate most from the national benchmark price. Markets above the national median (positive spread) typically reflect higher transport costs or supply constraints. Markets with negative spreads are often major production surplus zones.

---

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
  xLabelRotation=45
  title="Regional Price Level per Kilogram (GHS / KG)"
  subtitle="Cost variations driven by transport costs, regional rainfall, and localized supply conditions across all 10 regions"
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
