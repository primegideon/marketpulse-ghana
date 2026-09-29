---
title: "Executive Overview"
---

# MarketPulse Ghana

**Agricultural price volatility and food inflation monitor for Ghana's core staple commodities.**

Data source: UN World Food Programme (WFP) · Forecast engine: Meta Prophet · Coverage: 2019 – 2023

---

```sql latest_gbvi
SELECT
    gbvi_score,
    risk_band,
    avg_mom_pct / 100.0  AS avg_mom_pct_dec,
    avg_abs_mom_pct / 100.0 AS avg_abs_mom_pct_dec,
    month_start
FROM agri_ghana.fact_gbvi_index
ORDER BY month_start DESC
LIMIT 1
```

```sql prev_gbvi
SELECT gbvi_score
FROM agri_ghana.fact_gbvi_index
ORDER BY month_start DESC
LIMIT 1 OFFSET 1
```

```sql gbvi_history
SELECT
    month_start,
    gbvi_score,
    risk_band
FROM agri_ghana.fact_gbvi_index
ORDER BY month_start
```

```sql volatility_ranking
SELECT
    commodity_name,
    ROUND(STDDEV_POP(avg_price_per_kg_ghs), 2) AS price_stddev,
    ROUND(AVG(avg_price_per_kg_ghs), 2)        AS avg_price_ghs
FROM agri_ghana.fact_monthly_prices
WHERE avg_price_per_kg_ghs IS NOT NULL
GROUP BY commodity_name
ORDER BY price_stddev DESC
LIMIT 8
```

```sql seasonality
SELECT
    CASE EXTRACT(month FROM month_start)::INTEGER
        WHEN 1  THEN 'Jan' WHEN 2  THEN 'Feb' WHEN 3  THEN 'Mar'
        WHEN 4  THEN 'Apr' WHEN 5  THEN 'May' WHEN 6  THEN 'Jun'
        WHEN 7  THEN 'Jul' WHEN 8  THEN 'Aug' WHEN 9  THEN 'Sep'
        WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
    END AS month_name,
    EXTRACT(month FROM month_start)::INTEGER AS month_num,
    ROUND(AVG(mom_inflation_pct), 2) AS avg_mom_pct
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name IN ('maize', 'rice (local)', 'cassava', 'tomatoes (local)', 'plantains (apentu)')
  AND mom_inflation_pct IS NOT NULL
  AND mom_inflation_pct BETWEEN -100 AND 500
GROUP BY month_name, month_num
ORDER BY month_num
```

```sql regional_inflation
SELECT
    region,
    ROUND(AVG(mom_inflation_pct), 2) AS avg_mom_pct
FROM agri_ghana.fact_monthly_prices
WHERE month_start >= '2022-07-01'
  AND mom_inflation_pct IS NOT NULL
  AND mom_inflation_pct BETWEEN -100 AND 500
GROUP BY region
ORDER BY avg_mom_pct DESC
```

---

## Key Indicators

<Grid cols=4>
    <BigValue
        data={latest_gbvi}
        value="gbvi_score"
        title="GBVI Score"
        fmt="#,##0.0"
        downIsGood=true
        comparison="gbvi_score"
        comparisonData={prev_gbvi}
        comparisonTitle="vs prior month"
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
        downIsGood=true
    />
    <BigValue
        data={latest_gbvi}
        value="avg_abs_mom_pct_dec"
        title="Avg Price Swing"
        fmt="pct1"
        downIsGood=true
    />
</Grid>

> **What is the GBVI?** The Ghana Basket Volatility Index is a composite score from 0–100 measuring month-over-month price instability across Ghana's five primary staples: Maize, Rice, Cassava, Plantain, and Tomatoes. A score of 0–30 indicates a stable price environment. 31–70 signals moderate inflationary pressure. Above 70 is a high food volatility alert.

---

## GBVI Trend (2019 – 2023)

<LineChart
    data={gbvi_history}
    x="month_start"
    y="gbvi_score"
    title="Ghana Basket Volatility Index — Monthly Score"
    yAxisTitle="GBVI Score (0–100)"
    yMin=0
    yMax=100
    labels=true
    colorPalette={['#1d4ed8']}
/>

<Details title="How to read this chart">
    The GBVI spikes during planting season (Feb–May) when existing stocks are depleted before the new harvest arrives, and again during flooding events in the Northern region which disrupt supply routes. The relatively stable period from mid-2021 to early-2022 reflects improved supply-chain conditions before global commodity price shocks resumed.
</Details>

---

## Price Volatility Ranking

Which commodities have shown the highest absolute price swings over the full observation period?

<BarChart
    data={volatility_ranking}
    x="commodity_name"
    y="price_stddev"
    title="Top 8 Most Volatile Commodities — Standard Deviation of Monthly Price (GHS/KG)"
    yAxisTitle="Price Std Dev (GHS/KG)"
    swapXY=true
    colorPalette={['#1d4ed8']}
/>

---

## Seasonal Price Pressure

Average month-over-month inflation by calendar month across the five primary staples. Months above zero mean prices tend to rise; below zero means they tend to fall.

<BarChart
    data={seasonality}
    x="month_name"
    y="avg_mom_pct"
    title="Average MoM Inflation by Calendar Month — Primary Staples"
    yAxisTitle="Avg MoM % Change"
    colorPalette={['#1d4ed8']}
/>

> **Key pattern:** February and April consistently record the highest average inflation. This aligns with the pre-harvest lean season when grain reserves from the previous harvest are running low. July and September show price relief as the main harvest comes to market.

---

## Regional Inflation Pressure (Last 12 Months)

<BarChart
    data={regional_inflation}
    x="region"
    y="avg_mom_pct"
    title="Average MoM Inflation by Region — July 2022 to July 2023"
    yAxisTitle="Avg MoM Inflation %"
    swapXY=true
    colorPalette={['#1d4ed8']}
/>
