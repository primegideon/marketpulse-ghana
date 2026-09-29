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
    avg_mom_pct,
    avg_abs_mom_pct,
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

```sql gbvi_sparkline
SELECT
    month_start,
    gbvi_score
FROM agri_ghana.fact_gbvi_index
ORDER BY month_start DESC
LIMIT 12
```

```sql mom_sparkline
SELECT
    month_start,
    avg_mom_pct
FROM agri_ghana.fact_gbvi_index
ORDER BY month_start DESC
LIMIT 12
```

```sql swing_sparkline
SELECT
    month_start,
    avg_abs_mom_pct
FROM agri_ghana.fact_gbvi_index
ORDER BY month_start DESC
LIMIT 12
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
    ROUND(AVG(mom_inflation_pct), 2) AS avg_mom_pct,
    CASE
        WHEN EXTRACT(month FROM month_start)::INTEGER IN (2, 4) THEN 'Lean Season'
        WHEN EXTRACT(month FROM month_start)::INTEGER IN (9, 10) THEN 'Harvest Relief'
        ELSE 'Normal'
    END AS season_group
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

<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:8px">

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #b91c1c">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fee2e2;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="7" width="2.5" height="6" rx="1" fill="#b91c1c"/><rect x="5.5" y="4" width="2.5" height="9" rx="1" fill="#b91c1c"/><rect x="10" y="1" width="2.5" height="12" rx="1" fill="#b91c1c"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">GBVI Score</span>
</div>
<BigValue data={latest_gbvi} value="gbvi_score" fmt="#,##0.0" downIsGood=true comparison="gbvi_score" comparisonData={prev_gbvi} comparisonTitle="vs prior month"/>
<Sparkline data={gbvi_sparkline} dateCol="month_start" valueCol="gbvi_score" type="area" color="#b91c1c" height=28 width=160/>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #b91c1c">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fee2e2;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M6.2 1.8L1 11h12.1L7.8 1.8a.9.9 0 0 0-1.6 0Z" stroke="#b91c1c" stroke-width="1.3" fill="none"/><line x1="7" y1="5.5" x2="7" y2="8.5" stroke="#b91c1c" stroke-width="1.3" stroke-linecap="round"/><circle cx="7" cy="10.2" r="0.6" fill="#b91c1c"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Risk Band</span>
</div>
<BigValue data={latest_gbvi} value="risk_band"/>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #d97706">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fef3c7;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,11 4.5,6.5 8,8.5 13,2.5" stroke="#d97706" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9.5,2.5 13,2.5 13,6" stroke="#d97706" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Avg MoM Inflation</span>
</div>
<BigValue data={latest_gbvi} value="avg_mom_pct_dec" fmt="pct1" downIsGood=true/>
<Sparkline data={mom_sparkline} dateCol="month_start" valueCol="avg_mom_pct" type="area" color="#d97706" height=28 width=160/>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #1e3a5f">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#e8f0fa;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,7 3,7 4.8,2.5 6.8,11.5 8.5,5.5 10.5,7 13,7" stroke="#1e3a5f" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Avg Price Swing</span>
</div>
<BigValue data={latest_gbvi} value="avg_abs_mom_pct_dec" fmt="pct1" downIsGood=true/>
<Sparkline data={swing_sparkline} dateCol="month_start" valueCol="avg_abs_mom_pct" type="area" color="#1e3a5f" height=28 width=160/>
</div>

</div>

<Alert status="info">
    <b>What is the GBVI?</b> The Ghana Basket Volatility Index is a composite score from 0 to 100 measuring month-over-month price instability across Ghana's 9-commodity staple basket: Maize, Maize (Yellow), Rice (Local), Rice (Imported), Cassava, Plantains (Apem), Plantains (Apentu), Tomatoes (Local), and Tomatoes (Navrongo). Scores of 0–30 indicate a stable price environment. 31–70 signals moderate inflationary pressure. Above 70 is a high food volatility alert.
</Alert>

---

## GBVI Trend (2006 – 2023)

<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px;align-items:center">
<span style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#57606a;margin-right:4px">9-commodity basket:</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Maize</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Maize (Yellow)</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Rice (Local)</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Rice (Imported)</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Cassava</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Plantains (Apem)</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Plantains (Apentu)</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Tomatoes (Local)</span>
<span style="font-size:11px;padding:2px 9px;border-radius:20px;background:#f0f4f9;border:1px solid #d0daea;color:#1e3a5f;font-weight:600">Tomatoes (Navrongo)</span>
</div>

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
        {y: 70, label: 'High Alert (70)', color: '#b91c1c', lineType: 'dashed'},
        {y: 30, label: 'Stable (30)', color: '#15803d', lineType: 'dashed'}
    ]}
    echartsOptions={{
        visualMap: {
            show: false,
            type: 'piecewise',
            dimension: 1,
            seriesIndex: 0,
            pieces: [
                {gt: 70, lte: 100, color: '#b91c1c'},
                {gt: 30, lte: 70,  color: '#d97706'},
                {gt: 0,  lte: 30,  color: '#1e3a5f'}
            ]
        }
    }}
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
    series="season_group"
    title="Average MoM Retail Inflation by Calendar Month — Primary Staples"
    subtitle="Retail prices only · Observations capped at ±100% to exclude data entry anomalies"
    yAxisTitle="Avg MoM Change (%)"
    colorPalette={['#d97706', '#15803d', '#4a90c4']}
    fmt="num1"
    sort=false
    labels=true
    labelFmt="num1"
/>

<Alert status="info">
    <b>Seasonal pattern:</b> April consistently records the highest average retail inflation across the staple basket (lean season peak). February also sees elevated pressure as reserves run low. September and October mark the arrival of the main harvest, bringing the only months of average price relief across the basket.
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
    labels=true
    labelFmt="num2"
    colorPalette={['#1e3a5f']}
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
    fmt="num1"
    labels=true
    labelFmt="num1"
    colorPalette={['#2563a8']}
/>

    </Tab>
</Tabs>
