---
title: "Price Forecasts"
---

# 3-Month Price Forecasts

Powered by Meta's Prophet algorithm, MarketPulse projects future commodity prices over a 3-month horizon based on historical volatility and seasonal trends.

```sql future_forecasts
SELECT 
    commodity_name,
    record_date,
    predicted_price_ghs,
    lower_bound_ghs,
    upper_bound_ghs
FROM agri_ghana.fact_price_forecasts
WHERE is_forecast = TRUE
ORDER BY commodity_name, record_date
```

```sql historical_plus_forecast
SELECT 
    f.commodity_name,
    f.record_date,
    f.predicted_price_ghs,
    f.lower_bound_ghs,
    f.upper_bound_ghs,
    f.is_forecast
FROM agri_ghana.fact_price_forecasts f
WHERE f.record_date >= '2022-01-01'
ORDER BY f.commodity_name, f.record_date
```

<Tabs>
    <Tab label="Visual Forecasts">
        ## Future Price Projections (With Confidence Intervals)
        
        The shaded regions represent the 80% confidence interval for each prediction. 
        
        <LineChart 
            data={historical_plus_forecast} 
            x="record_date" 
            y="predicted_price_ghs" 
            y2="upper_bound_ghs"
            y3="lower_bound_ghs"
            series="commodity_name"
            title="Forecasts (Since 2022)"
            yAxisTitle="Price per KG (GHS)"
            legend={true}
        />
    </Tab>
    
    <Tab label="Raw Forecast Data">
        ## Forecast Output Table
        
        <DataTable data={future_forecasts} search={true}>
            <Column id="commodity_name" title="Commodity" />
            <Column id="record_date" title="Forecast Date" fmt="date" />
            <Column id="predicted_price_ghs" title="Predicted (GHS/KG)" fmt="num2" />
            <Column id="lower_bound_ghs" title="Lower Bound" fmt="num2" />
            <Column id="upper_bound_ghs" title="Upper Bound" fmt="num2" />
        </DataTable>
    </Tab>
</Tabs>
