---
title: "Commodity Deep Dive"
---

# Regional Commodity Price Tracker

Analyze historical price trends for specific agricultural staples across all regions in Ghana.

```sql all_commodities
SELECT DISTINCT commodity_name 
FROM agri_ghana.fact_monthly_prices 
ORDER BY commodity_name
```

<Dropdown 
    name="selected_commodity" 
    data={all_commodities} 
    value="commodity_name" 
    defaultValue="maize"
/>

```sql commodity_data
SELECT 
    month_start, 
    region,
    avg_price_per_kg_ghs 
FROM agri_ghana.fact_monthly_prices 
WHERE commodity_name = '${inputs.selected_commodity}'
ORDER BY month_start, region
```

## Historical Price Trends (By Region)

<LineChart 
    data={commodity_data} 
    x="month_start" 
    y="avg_price_per_kg_ghs" 
    series="region"
    title="Average Price per KG (GHS)"
    yAxisTitle="Price (GHS)"
    legend={true}
/>

```sql summary_stats
SELECT 
    region,
    MIN(avg_price_per_kg_ghs) as all_time_low,
    MAX(avg_price_per_kg_ghs) as all_time_high,
    AVG(avg_price_per_kg_ghs) as average_price
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity}'
GROUP BY region
ORDER BY average_price DESC
```

## Regional Summary Statistics

<DataTable data={summary_stats}>
    <Column id="region" title="Region" />
    <Column id="all_time_low" title="All-Time Low (GHS)" fmt="num2" />
    <Column id="all_time_high" title="All-Time High (GHS)" fmt="num2" />
    <Column id="average_price" title="Historical Average (GHS)" fmt="num2" />
</DataTable>
