---
title: "Commodity Price Intelligence"
---

# Commodity Price Intelligence

Select a commodity to examine its historical price series, regional dispersion, rolling trend averages, and volatility profile across all monitored markets in Ghana.

```sql all_commodities
SELECT DISTINCT commodity_name
FROM agri_ghana.fact_monthly_prices
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
ORDER BY month_start, region
```

```sql commodity_kpis
SELECT
    ROUND(AVG(avg_price_per_kg_ghs), 2)  AS national_avg_price,
    ROUND(MAX(avg_price_per_kg_ghs), 2)  AS all_time_high,
    ROUND(MIN(avg_price_per_kg_ghs), 2)  AS all_time_low,
    ROUND(AVG(mom_inflation_pct), 2)     AS avg_mom_inflation
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
```

```sql regional_summary
SELECT
    region,
    ROUND(AVG(avg_price_per_kg_ghs), 2)    AS historical_avg,
    ROUND(MIN(avg_price_per_kg_ghs), 2)    AS all_time_low,
    ROUND(MAX(avg_price_per_kg_ghs), 2)    AS all_time_high,
    ROUND(STDDEV(avg_price_per_kg_ghs), 2) AS price_volatility,
    COUNT(*) AS months_observed
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
GROUP BY region
ORDER BY historical_avg DESC
```

---

## Price Summary

<Grid cols=4>
    <BigValue
        data={commodity_kpis}
        value="national_avg_price"
        title="National Average (GHS/KG)"
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

## National Price Series with Rolling Averages

The raw monthly national average is plotted alongside a 3-month and 6-month rolling average. The rolling lines smooth short-term supply shocks and reveal the underlying price trend.

<LineChart
    data={commodity_national}
    x="month_start"
    y={['national_avg', 'rolling_3m', 'rolling_6m']}
    title="National Average Price — Raw Monthly vs 3M and 6M Rolling Average (GHS/KG)"
    yAxisTitle="Price (GHS/KG)"
    legend=true
/>

---

## Regional Price Dispersion

Price dispersion across regions reflects transport costs, market access, and local supply-demand imbalances.

<LineChart
    data={commodity_by_region}
    x="month_start"
    y="avg_price_per_kg_ghs"
    series="region"
    title="Average Monthly Price by Region (GHS/KG)"
    yAxisTitle="Price (GHS/KG)"
    legend=true
/>

---

## Regional Statistics

<DataTable data={regional_summary} search=true>
    <Column id="region" title="Region" />
    <Column id="historical_avg" title="Historical Average (GHS/KG)" fmt="num2" />
    <Column id="all_time_low" title="Floor Price (GHS/KG)" fmt="num2" />
    <Column id="all_time_high" title="Peak Price (GHS/KG)" fmt="num2" />
    <Column id="price_volatility" title="Volatility — Std Dev" fmt="num2" />
    <Column id="months_observed" title="Months on Record" />
</DataTable>
