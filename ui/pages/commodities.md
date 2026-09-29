---
title: "Commodity Price Intelligence"
---

Select a commodity to examine its retail price series, regional dispersion, rolling trend averages, and price volatility profile across Ghana's monitored markets. All prices are retail unless otherwise stated.

```sql all_commodities
SELECT DISTINCT commodity_name
FROM agri_ghana.fact_monthly_prices
WHERE price_type = 'retail'
ORDER BY commodity_name
```

<Dropdown
    name="selected_commodity"
    data={all_commodities}
    value="commodity_name"
    title="Commodity"
    defaultValue="maize"
/>

```sql commodity_national
SELECT
    month_start,
    ROUND(AVG(avg_price_per_kg_ghs), 2) AS national_avg,
    ROUND(AVG(rolling_3m_avg), 2)       AS rolling_3m,
    ROUND(AVG(rolling_6m_avg), 2)       AS rolling_6m
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND price_type = 'retail'
GROUP BY month_start
ORDER BY month_start
```

```sql commodity_by_region
SELECT
    month_start,
    region,
    ROUND(avg_price_per_kg_ghs, 2) AS avg_price_per_kg_ghs
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND price_type = 'retail'
ORDER BY month_start, region
```

```sql commodity_kpis
SELECT
    ROUND(AVG(avg_price_per_kg_ghs), 2)  AS national_avg_price,
    ROUND(MAX(avg_price_per_kg_ghs), 2)  AS all_time_high,
    ROUND(MIN(avg_price_per_kg_ghs), 2)  AS all_time_low,
    ROUND(AVG(CASE WHEN mom_inflation_pct BETWEEN -100 AND 500 THEN mom_inflation_pct END), 2) AS avg_mom_inflation
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND price_type = 'retail'
  AND avg_price_per_kg_ghs IS NOT NULL
```

```sql price_sparkline
SELECT
    month_start,
    ROUND(AVG(avg_price_per_kg_ghs), 2) AS national_avg
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND price_type = 'retail'
GROUP BY month_start
ORDER BY month_start DESC
LIMIT 24
```

```sql regional_summary
SELECT
    region,
    ROUND(AVG(avg_price_per_kg_ghs), 2)        AS historical_avg,
    ROUND(MIN(avg_price_per_kg_ghs), 2)        AS all_time_low,
    ROUND(MAX(avg_price_per_kg_ghs), 2)        AS all_time_high,
    ROUND(STDDEV_POP(avg_price_per_kg_ghs), 2) AS price_volatility,
    COUNT(*) AS months_observed
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND price_type = 'retail'
  AND avg_price_per_kg_ghs IS NOT NULL
GROUP BY region
ORDER BY historical_avg DESC
```

---

## Market Snapshot

<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:8px">

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #1e3a5f">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#e8f0fa;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="#1e3a5f" stroke-width="1.3"/><line x1="7" y1="4" x2="7" y2="7.5" stroke="#1e3a5f" stroke-width="1.4" stroke-linecap="round"/><circle cx="7" cy="9.5" r="0.7" fill="#1e3a5f"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Long-Run Avg Price</span>
</div>
<BigValue data={commodity_kpis} value="national_avg_price" fmt="num2"/>
<div style="font-size:10px;color:#57606a;margin-top:4px">GHS per KG · Full period</div>
<Sparkline data={price_sparkline} dateCol="month_start" valueCol="national_avg" type="area" color="#1e3a5f" height=28 width=160/>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #b91c1c">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fee2e2;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,11 4.5,6.5 8,8.5 13,2.5" stroke="#b91c1c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9.5,2.5 13,2.5 13,6" stroke="#b91c1c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">All-Time Peak</span>
</div>
<BigValue data={commodity_kpis} value="all_time_high" fmt="num2" downIsGood=true/>
<div style="font-size:10px;color:#57606a;margin-top:4px">GHS per KG · Highest observed</div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #15803d">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#dcfce7;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,3 4.5,7.5 8,5.5 13,11.5" stroke="#15803d" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9.5,11.5 13,11.5 13,8" stroke="#15803d" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Historic Floor</span>
</div>
<BigValue data={commodity_kpis} value="all_time_low" fmt="num2"/>
<div style="font-size:10px;color:#57606a;margin-top:4px">GHS per KG · Lowest observed</div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #d97706">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fef3c7;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,7 3,7 4.8,2.5 6.8,11.5 8.5,5.5 10.5,7 13,7" stroke="#d97706" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Avg MoM Inflation</span>
</div>
<BigValue data={commodity_kpis} value="avg_mom_inflation" fmt="num2" downIsGood=true/>
<div style="font-size:10px;color:#57606a;margin-top:4px">% · Monthly retail average</div>
</div>

</div>

---

<Tabs>
    <Tab label="Price History">

## National Retail Price Series with Rolling Averages

The raw monthly national average is plotted alongside a 3-month and 6-month rolling average. The rolling averages smooth short-term supply shocks and reveal the underlying price trend direction.

<AreaChart
    data={commodity_national}
    x="month_start"
    y="national_avg"
    title="National Average Retail Price — Monthly (GHS/KG)"
    subtitle="Retail prices only · Aug 2019 – Jul 2023 · WFP retail coverage begins Aug 2019"
    yAxisTitle="Price (GHS/KG)"
    colorPalette={['#1e3a5f']}
    markers=true
    referenceLines={[
        {x: '2022-11-01', label: 'Cedi depreciation crisis', color: '#d97706', lineType: 'dashed'}
    ]}
/>

<LineChart
    data={commodity_national}
    x="month_start"
    y={['rolling_3m', 'rolling_6m']}
    title="3-Month and 6-Month Rolling Average (GHS/KG)"
    subtitle="3m reacts faster to price moves · 6m reflects structural trend direction · Aug 2019 – Jul 2023"
    yAxisTitle="Price (GHS/KG)"
    legend=true
    colorPalette={['#1e3a5f', '#7fb3d3']}
    seriesOptions={[
        {name: 'rolling_3m', lineWidth: 2.5},
        {name: 'rolling_6m', lineWidth: 1.5}
    ]}
/>

    </Tab>
    <Tab label="Regional Dispersion">

## Retail Price Dispersion by Region

Price variation across regions reflects transport costs, market access constraints, and local supply-demand imbalances. Producing regions typically record lower prices than urban consumer centres.

<LineChart
    data={commodity_by_region}
    x="month_start"
    y="avg_price_per_kg_ghs"
    series="region"
    title="Average Monthly Retail Price by Region (GHS/KG)"
    subtitle="Retail prices only"
    yAxisTitle="Price (GHS/KG)"
    legend=true
/>

    </Tab>
    <Tab label="Market Statistics">

## Regional Market Statistics — Full Observation Period

Per-region summary of retail price range, average, and volatility over the full observation window. Standard deviation measures how widely prices have fluctuated around the regional average.

<DataTable data={regional_summary} search=true rowNumbers=false>
    <Column id="region" title="Region" />
    <Column id="historical_avg" title="Historical Avg (GHS/KG)" fmt="num2" contentType="colorscale" scaleColor="blue" />
    <Column id="all_time_low" title="Floor Price (GHS/KG)" fmt="num2" />
    <Column id="all_time_high" title="Peak Price (GHS/KG)" fmt="num2" />
    <Column id="price_volatility" title="Volatility (Std Dev)" fmt="num2" />
    <Column id="months_observed" title="Months on Record" />
</DataTable>

    </Tab>
</Tabs>
