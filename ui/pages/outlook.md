---
title: Six-Month Outlook
---

> **The forecast converts historical price patterns and FX dynamics into a commodity-specific food-security watchlist. All projections are model estimates, not observed prices.**

---

```sql forecast_commodities
select distinct commodity_name
from fact_price_forecasts
order by commodity_name
```

<Dropdown
  name=forecast_commodity
  data={forecast_commodities}
  value=commodity_name
  title="Commodity"
  defaultValue="maize"
/>

```sql forecast_selected
select
    record_date,
    round(predicted_price_ghs, 2)  as projected_price,
    round(lower_bound_ghs, 2)      as lower_bound,
    round(upper_bound_ghs, 2)      as upper_bound,
    round(mape_score, 1)           as mape,
    round(directional_accuracy, 1) as dir_accuracy
from fact_price_forecasts
where commodity_name = coalesce(nullif('${inputs.forecast_commodity}', ''), 'maize')
order by record_date
```

```sql historical_for_forecast
select
    month_start                    as record_date,
    round(avg_price_per_kg_ghs, 2) as actual_price
from fact_monthly_prices
where commodity_name = coalesce(nullif('${inputs.forecast_commodity}', ''), 'maize')
  and price_type = 'retail'
  and region = 'greater accra'
  and month_start >= '2022-01-01'
order by month_start
```

```sql watchlist
select
    f.commodity_name,
    round(f.predicted_price_ghs, 2)  as projected_price,
    round(f.lower_bound_ghs, 2)      as lower_bound,
    round(f.upper_bound_ghs, 2)      as upper_bound,
    round(f.mape_score, 1)           as mape,
    round(f.directional_accuracy, 1) as dir_accuracy,
    s.direction_signal               as seasonal_signal
from fact_price_forecasts f
left join fact_seasonal_outlook s
    on lower(f.commodity_name) = lower(s.commodity_name)
    and s.month_num = 8
where f.record_date = (select max(record_date) from fact_price_forecasts)
order by f.mape_score asc
```

```sql model_comparison
select * from (
    values
        ('XGBoost', 61.1, 21.5),
        ('Prophet', 47.2, 42.4),
        ('ARIMAX',  38.9, 23.8)
) t(model, dir_accuracy, avg_mape)
order by dir_accuracy desc
```

---

<BigValue
  data={forecast_selected}
  value=projected_price
  title="Projected Price (GHS/kg)"
  subtitle="Latest forecast month"
/>

<BigValue
  data={forecast_selected}
  value=mape
  title="Model MAPE (%)"
  subtitle="Avg forecast error on Jan–Jul 2023 test set"
/>

<BigValue
  data={forecast_selected}
  value=dir_accuracy
  title="Directional Accuracy (%)"
  subtitle="% months model predicted correct direction"
/>

---

<Tabs>
  <Tab label="Forecast Chart">

## Historical Price + 3-Month Forecast

<LineChart
  data={historical_for_forecast}
  x=record_date
  y=actual_price
  title="Actual Retail Price (GHS/kg) — Greater Accra (Jan 2022–Jul 2023)"
  subtitle="Historical prices leading into the forecast window."
  colorPalette={["#1e3a5f"]}
/>

<LineChart
  data={forecast_selected}
  x=record_date
  y={["projected_price", "lower_bound", "upper_bound"]}
  title="Six-Month Projected Price (GHS/kg)"
  subtitle="Projected price with lower and upper confidence bounds. Forecast period: Aug–Oct 2023."
  colorPalette={["#7c5cd8", "#c5dce8", "#c5dce8"]}
/>

> All values are model estimates. Use as directional signals — not exact price predictions.

  </Tab>
  <Tab label="Watchlist">

## Six-Month Watchlist — All Commodities

<DataTable
  data={watchlist}
  rows=all
  search=false
/>

> `mape` = average forecast error on Jan–Jul 2023 test set (lower = more reliable). `seasonal_signal` = historical Aug pattern. `dir_accuracy` = % months model correctly predicted direction.

  </Tab>
  <Tab label="Model Comparison">

## XGBoost vs Prophet vs ARIMAX — Holdout Validation

<BarChart
  data={model_comparison}
  x=model
  y=dir_accuracy
  title="Directional Accuracy on Holdout Data (%)"
  subtitle="XGBoost selected: highest directional accuracy — the key metric for food security planning."
  colorPalette={["#2563a8"]}
  labels=true
/>

<BarChart
  data={model_comparison}
  x=model
  y=avg_mape
  title="Average MAPE on Holdout Data (%)"
  subtitle="Lower is better. XGBoost achieved the lowest average forecast error."
  colorPalette={["#d97706"]}
  labels=true
/>

  </Tab>
</Tabs>

---

> **Forecast scope:** Aug–Oct 2023 (3 months). Train: Aug 2019–Dec 2022. Test: Jan–Jul 2023. Model: XGBoost with lag features (price lags 1/2/3, MoM momentum, month-of-year, GHS/USD FX). Forecasts are model estimates; actual prices may differ.
