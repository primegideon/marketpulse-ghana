---
title: "Supply Chain Price Spreads"
---

# Supply Chain Price Spreads

Analysis of the retail price gap between agricultural producing regions and urban consumer markets. A high spread margin indicates supply chain friction — transport costs, intermediary markups, or market access barriers that raise the cost of food for urban households above farm-gate levels.

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
    ROUND(AVG(spread_margin_pct), 1)            AS avg_spread_pct,
    ROUND(MAX(spread_margin_pct), 1)            AS max_spread_pct,
    COUNT(DISTINCT commodity_name)              AS commodities_monitored,
    COUNT(DISTINCT month_start)                 AS months_on_record
FROM agri_ghana.fact_market_spreads
WHERE spread_margin_pct IS NOT NULL
  AND spread_margin_pct > 0
```

```sql spread_trends
SELECT
    month_start,
    commodity_name,
    ROUND(spread_margin_pct, 1) AS spread_margin_pct
FROM agri_ghana.fact_market_spreads
WHERE month_start >= '2020-01-01'
  AND spread_margin_pct > 0
ORDER BY month_start, commodity_name
```

```sql top_spread_commodities
SELECT
    commodity_name,
    ROUND(AVG(spread_margin_pct), 1) AS avg_spread_pct,
    ROUND(MAX(spread_margin_pct), 1) AS peak_spread_pct,
    COUNT(*)                         AS months_observed
FROM agri_ghana.fact_market_spreads
WHERE spread_margin_pct > 0
GROUP BY commodity_name
ORDER BY avg_spread_pct DESC
LIMIT 10
```

```sql spread_commodities_list
SELECT DISTINCT commodity_name
FROM agri_ghana.fact_market_spreads
WHERE spread_margin_pct > 0
ORDER BY commodity_name
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

<Tabs>
    <Tab label="Latest Month">

## Urban Markup by Commodity — Latest Month

How much more expensive is each commodity in urban consumer markets relative to farm-gate prices in producing regions? A markup of 100% means the urban price is double the producing-region price.

<BarChart
    data={latest_spread}
    x="commodity_name"
    y="spread_margin_pct_dec"
    title="Urban Price Premium over Farm-Gate — Latest Month"
    subtitle="Positive values indicate urban prices exceed producing-region prices"
    yAxisTitle="Urban Markup (%)"
    swapXY=true
    sort="spread_margin_pct_dec"
    fmt="pct1"
    colorPalette={['#2563a8']}
/>

---

## Price Gap Detail — Latest Month

<DataTable data={latest_spread} search=true rowNumbers=false>
    <Column id="commodity_name" title="Commodity" />
    <Column id="producing_avg_price" title="Farm-Gate Avg (GHS/KG)" fmt="num2" />
    <Column id="urban_avg_price" title="Urban Avg (GHS/KG)" fmt="num2" />
    <Column id="absolute_spread_ghs" title="Absolute Gap (GHS/KG)" fmt="num2" />
    <Column id="spread_margin_pct_dec" title="Urban Markup" fmt="pct1" contentType="colorscale" scaleColor="blue" />
</DataTable>

    </Tab>
    <Tab label="Trend">

## Spread Margin Trend (2020 – 2023)

Monthly urban markup percentage by commodity since January 2020. Spread widening during specific periods can be traced to dry-season road deterioration, fuel price increases, or perishability-driven farm-gate price collapses. Use the filter to focus on one commodity at a time.

<Dropdown
    name="trend_commodity"
    data={spread_commodities_list}
    value="commodity_name"
    title="Commodity"
    defaultValue="maize"
/>

```sql spread_trend_filtered
SELECT
    month_start,
    ROUND(spread_margin_pct, 1) AS spread_margin_pct
FROM agri_ghana.fact_market_spreads
WHERE month_start >= '2020-01-01'
  AND spread_margin_pct > 0
  AND commodity_name = '${inputs.trend_commodity.value}'
ORDER BY month_start
```

<AreaChart
    data={spread_trend_filtered}
    x="month_start"
    y="spread_margin_pct"
    title="Urban vs Farm-Gate Price Spread — Monthly Markup (%)"
    subtitle="Positive values only · 2020–2023"
    yAxisTitle="Urban Markup (%)"
    colorPalette={['#1e3a5f']}
/>

<Alert status="info">
    <b>Spread drivers:</b> Spreads typically widen during the dry season (November–March) when road conditions in the Northern and Upper regions raise transport costs. Tomatoes and plantains show the most volatile spreads because any supply disruption rapidly inflates urban prices while farm-gate prices simultaneously collapse, amplifying the margin.
</Alert>

    </Tab>
    <Tab label="All Commodities">

## Average Urban Markup by Commodity — Full Period

Which commodities have sustained the highest urban price premiums over the full observation period? High sustained markups indicate persistent supply chain inefficiencies rather than one-off events.

<BarChart
    data={top_spread_commodities}
    x="commodity_name"
    y="avg_spread_pct"
    title="Top 10 Commodities by Average Urban Markup — Full Observation Period (%)"
    subtitle="Higher values indicate greater and more persistent supply chain friction"
    yAxisTitle="Average Urban Markup (%)"
    swapXY=true
    colorPalette={['#1e3a5f']}
/>

    </Tab>
</Tabs>
