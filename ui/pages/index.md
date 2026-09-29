---
title: "Executive Overview"
---

# MarketPulse Ghana

**Agricultural price volatility and food inflation monitor for Ghana's core staple commodities.**

Data source: UN World Food Programme (WFP) &nbsp;·&nbsp; Seasonal outlook: 2018–2023 retail baseline &nbsp;·&nbsp; Coverage: 2006 – 2023

---

```sql latest_gbvi
SELECT
    gbvi_score,
    risk_band,
    avg_mom_pct / 100.0     AS avg_mom_pct_dec,
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
  AND price_type = 'retail'
  AND commodity_name IN (
      'maize', 'maize (yellow)', 'rice (local)', 'rice (imported)',
      'cassava', 'plantains (apem)', 'plantains (apentu)',
      'tomatoes (local)', 'tomatoes (navrongo)', 'sorghum', 'millet', 'yam'
  )
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
  AND price_type = 'retail'
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
  AND price_type = 'retail'
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
        title="Current Risk Band"
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
        title="Avg Absolute Price Swing"
        fmt="pct1"
        downIsGood=true
    />
</Grid>

<Alert status="info">
    <b>What is the GBVI?</b> The Ghana Basket Volatility Index is a composite score from 0 to 100 measuring month-over-month price instability across Ghana's five primary staples: Maize, Rice, Cassava, Plantain, and Tomatoes. Scores of 0–30 indicate a stable price environment. 31–70 signals moderate inflationary pressure. Above 70 is a high food volatility alert. The index is calibrated so that a score below 30 reflects normal seasonal variation and a score of 100 corresponds to a genuine supply crisis or macroeconomic shock.
</Alert>

---

## GBVI Trend (2006 – 2023)

<AreaChart
    data={gbvi_history}
    x="month_start"
    y="gbvi_score"
    title="Ghana Basket Volatility Index — Monthly Score"
    subtitle="Composite 0–100 measure of staple basket price instability"
    yAxisTitle="GBVI Score"
    yMin=0
    yMax=100
    labels=false
    colorPalette={['#1e3a5f']}
    referenceLines={[
        {y: 70, label: 'High Alert threshold', color: '#b91c1c', lineType: 'dashed'},
        {y: 30, label: 'Stable threshold', color: '#15803d', lineType: 'dashed'}
    ]}
/>

<Details title="Reading this chart">
    The GBVI peaks during two recurring conditions: the pre-harvest lean season (February–April) when grain reserves from the prior harvest are depleted, and during documented macroeconomic shocks. The spikes to 100 in early 2020 reflect COVID-19 market disruptions; those in early 2022 reflect the Russia-Ukraine global commodity price shock and the onset of the Ghana cedi depreciation crisis.
</Details>

---

<Tabs>
    <Tab label="Overview">

## Seasonal Price Pressure

Average month-over-month retail price change by calendar month across the five primary staples. Months above zero indicate prices tend to rise; below zero indicates they tend to fall. Based on retail prices only.

<BarChart
    data={seasonality}
    x="month_name"
    y="avg_mom_pct"
    title="Average MoM Retail Inflation by Calendar Month — Primary Staples"
    subtitle="Retail prices only · Observations capped at ±100% to exclude data entry anomalies"
    yAxisTitle="Avg MoM Change (%)"
/>

<Alert status="info">
    <b>Seasonal pattern:</b> April consistently records the highest average retail inflation across the staple basket. This aligns with the pre-harvest lean season when grain reserves from the previous harvest are running low and new-season supply has not yet reached markets. September shows price relief as the main harvest arrives.
</Alert>

    </Tab>
    <Tab label="Deep Dive">

## Staple Commodity Volatility Ranking

Which staple crops have shown the highest absolute retail price variation over the full observation period? Standard deviation of monthly price measures the spread of price observations around the commodity's long-run average.

<BarChart
    data={volatility_ranking}
    x="commodity_name"
    y="price_stddev"
    title="Price Volatility by Staple Commodity — Standard Deviation of Monthly Retail Price (GHS/KG)"
    subtitle="Retail prices only · Full observation period 2006–2023"
    yAxisTitle="Price Std Dev (GHS/KG)"
    swapXY=true
/>

---

## Regional Retail Inflation — July 2022 to July 2023

Average month-over-month retail price change by administrative region over the trailing 18-month period. This period captures the Ghana cedi depreciation crisis and its uneven regional impact on food prices.

<BarChart
    data={regional_inflation}
    x="region"
    y="avg_mom_pct"
    title="Average MoM Retail Inflation by Region — July 2022 to July 2023"
    subtitle="Retail prices only · Staple and non-staple commodities included"
    yAxisTitle="Avg MoM Inflation (%)"
    swapXY=true
/>

    </Tab>
</Tabs>
