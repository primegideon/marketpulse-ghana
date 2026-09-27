---
title: "Macro Overview"
---

# MarketPulse Ghana: Executive Overview

A real-time monitor for Ghana's core agricultural staples, highlighting inflation, food security risks, and price volatility.

```sql latest_gbvi
SELECT 
    month_start, 
    gbvi_score, 
    risk_band,
    avg_mom_pct / 100.0 as avg_mom_pct_dec,
    gbvi_score - lag(gbvi_score) over (order by month_start) as gbvi_change
FROM agri_ghana.fact_gbvi_index 
ORDER BY month_start DESC 
LIMIT 2
```

```sql gbvi_history
SELECT 
    month_start, 
    gbvi_score,
    risk_band,
    avg_mom_pct / 100.0 as avg_mom_pct_dec
FROM agri_ghana.fact_gbvi_index 
WHERE month_start >= '2019-01-01'
ORDER BY month_start
```

<Grid cols={3}>
    <BigValue 
        data={latest_gbvi} 
        value="gbvi_score" 
        title="GBVI Score (Latest)" 
        fmt="#,##0.0"
        downIsGood={true}
    />
    <BigValue 
        data={latest_gbvi} 
        value="risk_band" 
        title="Current Risk Level" 
    />
    <BigValue 
        data={latest_gbvi} 
        value="avg_mom_pct_dec" 
        title="Avg MoM Inflation" 
        fmt="pct1"
        downIsGood={true}
    />
</Grid>

## GBVI Trend (2019 - Present)

The Ghana Basket Volatility Index (GBVI) is a composite score from 0-100 measuring price instability across Maize, Rice, Cassava, Plantain, and Tomatoes.

<LineChart 
    data={gbvi_history} 
    x="month_start" 
    y="gbvi_score" 
    title="GBVI Score Over Time"
    yAxisTitle="GBVI Score"
    yMin={0}
    yMax={100}
    seriesColors={{ gbvi_score: '#1E3A8A' }}
    yAxisLabels={true}
/>

## Inflation Trends by Staple

```sql inflation_by_staple
SELECT 
    month_start,
    commodity_name,
    AVG(mom_inflation_pct) / 100.0 as avg_mom_pct_dec
FROM agri_ghana.fact_monthly_prices
WHERE month_start >= '2022-01-01'
GROUP BY month_start, commodity_name
ORDER BY month_start, commodity_name
```

<LineChart 
    data={inflation_by_staple} 
    x="month_start" 
    y="avg_mom_pct_dec" 
    series="commodity_name"
    title="MoM Inflation by Commodity (Since 2022)"
    yAxisTitle="MoM % Change"
    fmt="pct1"
    legend={true}
/>
