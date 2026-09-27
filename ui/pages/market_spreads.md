---
title: "Market Spreads"
---

# Geographic Market Spreads

Supply chain efficiency analysis: comparing "Farm-gate" prices in Producing Regions vs "Retail" prices in Urban Consumer Regions.

Producing Regions: **Brong Ahafo, Northern, Upper East, Upper West, Volta**
Urban Regions: **Greater Accra, Ashanti**

```sql spread_trends
SELECT 
    month_start,
    commodity_name,
    urban_avg_price,
    producing_avg_price,
    absolute_spread_ghs,
    spread_margin_pct / 100.0 as spread_margin_pct_dec
FROM agri_ghana.fact_market_spreads
WHERE month_start >= '2020-01-01'
ORDER BY month_start, commodity_name
```

```sql latest_spread
SELECT 
    commodity_name,
    urban_avg_price,
    producing_avg_price,
    spread_margin_pct / 100.0 as spread_margin_pct_dec
FROM agri_ghana.fact_market_spreads
WHERE month_start = (SELECT max(month_start) FROM agri_ghana.fact_market_spreads)
ORDER BY spread_margin_pct DESC
```

## Current Spread Margins (Latest Month)

<BarChart 
    data={latest_spread}
    x="commodity_name"
    y="spread_margin_pct_dec"
    title="Urban Markup vs Farm-Gate (Percentage)"
    yAxisTitle="Spread %"
    fmt="pct1"
    swapXY={true}
    sort="spread_margin_pct_dec"
/>

## Historical Spread Trends

<LineChart 
    data={spread_trends} 
    x="month_start" 
    y="spread_margin_pct_dec" 
    series="commodity_name"
    title="Markup % Over Time (Urban vs Producing)"
    yAxisTitle="Markup %"
    fmt="pct1"
    legend={true}
/>

<DataTable data={latest_spread} title="Latest Market Gaps by Commodity">
    <Column id="commodity_name" title="Commodity" />
    <Column id="producing_avg_price" title="Producing Avg (GHS/KG)" fmt="num2" />
    <Column id="urban_avg_price" title="Urban Avg (GHS/KG)" fmt="num2" />
    <Column id="spread_margin_pct_dec" title="Markup Margin" fmt="pct1" />
</DataTable>
