---
title: "Supply Chain Price Spreads"
---

# Supply Chain Price Spreads

Analysis of the price gap between producing regions (farm-gate) and urban consumer markets. A high spread margin indicates significant supply chain friction — transport costs, middlemen markups, or market access barriers that drive up the cost of food for urban households.

**Producing regions:** Brong Ahafo, Northern, Upper East, Upper West, Volta

**Urban consumer regions:** Greater Accra, Ashanti

```sql latest_spread
SELECT
    commodity_name,
    ROUND(producing_avg_price, 2)           AS producing_avg_price,
    ROUND(urban_avg_price, 2)               AS urban_avg_price,
    ROUND(absolute_spread_ghs, 2)           AS absolute_spread_ghs,
    ROUND(spread_margin_pct / 100.0, 4)     AS spread_margin_pct_dec
FROM agri_ghana.fact_market_spreads
WHERE month_start = (SELECT MAX(month_start) FROM agri_ghana.fact_market_spreads)
ORDER BY spread_margin_pct DESC
```

```sql spread_kpis
SELECT
    ROUND(AVG(spread_margin_pct), 1)        AS avg_spread_pct,
    ROUND(MAX(spread_margin_pct), 1)        AS max_spread_pct,
    COUNT(DISTINCT commodity_name)          AS commodities_monitored,
    COUNT(DISTINCT month_start)             AS months_on_record
FROM agri_ghana.fact_market_spreads
```

```sql spread_trends
SELECT
    month_start,
    commodity_name,
    ROUND(spread_margin_pct / 100.0, 4) AS spread_margin_pct_dec
FROM agri_ghana.fact_market_spreads
WHERE month_start >= '2020-01-01'
  AND spread_margin_pct > 0
ORDER BY month_start, commodity_name
```

```sql top_spread_commodities
SELECT
    commodity_name,
    ROUND(AVG(spread_margin_pct), 1)    AS avg_spread_pct,
    ROUND(MAX(spread_margin_pct), 1)    AS peak_spread_pct
FROM agri_ghana.fact_market_spreads
WHERE spread_margin_pct > 0
GROUP BY commodity_name
ORDER BY avg_spread_pct DESC
LIMIT 10
```

---

## Overview

<Grid cols=4>
    <BigValue
        data={spread_kpis}
        value="avg_spread_pct"
        title="Average Urban Markup (%)"
        fmt="num1"
        downIsGood=true
    />
    <BigValue
        data={spread_kpis}
        value="max_spread_pct"
        title="Highest Recorded Markup (%)"
        fmt="num1"
        downIsGood=true
    />
    <BigValue
        data={spread_kpis}
        value="commodities_monitored"
        title="Commodities Monitored"
    />
    <BigValue
        data={spread_kpis}
        value="months_on_record"
        title="Months on Record"
    />
</Grid>

---

## Urban Markup by Commodity — Latest Month

How much more expensive is each commodity in urban consumer markets compared to the farm-gate price in producing regions? A 100% markup means the urban price is double the producer price.

<BarChart
    data={latest_spread}
    x="commodity_name"
    y="spread_margin_pct_dec"
    title="Urban Price Premium over Farm-Gate — Latest Month"
    yAxisTitle="Urban Markup (%)"
    swapXY=true
    sort="spread_margin_pct_dec"
    fmt="pct1"
    colorPalette={['#1d4ed8']}
/>

---

## Average Urban Markup by Commodity — Full Period

Which commodities have sustained the highest urban price premiums over the full observation period?

<BarChart
    data={top_spread_commodities}
    x="commodity_name"
    y="avg_spread_pct"
    title="Top 10 Commodities by Average Urban Markup — Full Observation Period (%)"
    yAxisTitle="Average Urban Markup (%)"
    swapXY=true
    colorPalette={['#1d4ed8']}
/>

---

## Spread Margin Trend (2020 – 2023)

<LineChart
    data={spread_trends}
    x="month_start"
    y="spread_margin_pct_dec"
    series="commodity_name"
    title="Urban vs Farm-Gate Price Spread by Commodity (% Margin)"
    yAxisTitle="Urban Markup (%)"
    fmt="pct1"
    legend=true
/>

> **What drives spread widening?** Spreads typically widen during the dry season (November – March) when poor road conditions in the Northern and Upper regions raise transport costs. Tomatoes and plantains show the most volatile spreads due to their perishability — any supply disruption rapidly inflates urban prices while farm-gate prices collapse.

---

## Price Gap — Latest Month

<DataTable data={latest_spread} search=true>
    <Column id="commodity_name" title="Commodity" />
    <Column id="producing_avg_price" title="Farm-Gate Avg (GHS/KG)" fmt="num2" />
    <Column id="urban_avg_price" title="Urban Avg (GHS/KG)" fmt="num2" />
    <Column id="absolute_spread_ghs" title="Absolute Gap (GHS/KG)" fmt="num2" />
    <Column id="spread_margin_pct_dec" title="Urban Markup" fmt="pct1" />
</DataTable>
