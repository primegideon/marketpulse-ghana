---
title: "Commodity Price Intelligence"
---

# Commodity Price Intelligence

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

## Price Summary

<Grid cols=4>
    <BigValue
        data={commodity_kpis}
        value="national_avg_price"
        title="National Retail Average (GHS/KG)"
        fmt="num2"
    />
    <BigValue
        data={commodity_kpis}
        value="all_time_high"
        title="Historical Peak (GHS/KG)"
        fmt="num2"
        downIsGood=true
    />
    <BigValue
        data={commodity_kpis}
        value="all_time_low"
        title="Historical Floor (GHS/KG)"
        fmt="num2"
    />
    <BigValue
        data={commodity_kpis}
        value="avg_mom_inflation"
        title="Avg MoM Inflation (%)"
        fmt="num2"
        downIsGood=true
    />
</Grid>

---

<Tabs>
    <Tab label="Price Trend">

## National Retail Price Series with Rolling Averages

The raw monthly national average is plotted alongside a 3-month and 6-month rolling average. The rolling averages smooth short-term supply shocks and reveal the underlying price trend direction.

<AreaChart
    data={commodity_national}
    x="month_start"
    y="national_avg"
    title="National Average Retail Price — Monthly (GHS/KG)"
    subtitle="Retail prices only"
    yAxisTitle="Price (GHS/KG)"
    colorPalette={['#1e3a5f']}
/>

<LineChart
    data={commodity_national}
    x="month_start"
    y={['rolling_3m', 'rolling_6m']}
    title="3-Month and 6-Month Rolling Average (GHS/KG)"
    subtitle="Smoothed trend lines — useful for identifying sustained price direction"
    yAxisTitle="Price (GHS/KG)"
    legend=true
    colorPalette={['#4a90c4', '#7fb3d3']}
/>

    </Tab>
    <Tab label="Regional Breakdown">

## Regional Retail Price Dispersion

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
    <Tab label="Statistics">

## Regional Statistics — Full Observation Period

<DataTable data={regional_summary} search=true rowNumbers=false>
    <Column id="region" title="Region" />
    <Column id="historical_avg" title="Historical Avg (GHS/KG)" fmt="num2" contentType="colorscale" scaleColor="blue" />
    <Column id="all_time_low" title="Floor Price (GHS/KG)" fmt="num2" />
    <Column id="all_time_high" title="Peak Price (GHS/KG)" fmt="num2" />
    <Column id="price_volatility" title="Std Dev (GHS/KG)" fmt="num2" />
    <Column id="months_observed" title="Months on Record" />
</DataTable>

    </Tab>
</Tabs>
