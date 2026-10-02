---
title: Six-Month Outlook
---

# Six-Month Outlook
### Which commodities require attention over the next six months?

> **The forecast converts historical price patterns and FX dynamics into a commodity-specific food-security watchlist. All projections are model estimates, not observed prices.**

---

```sql forecast_commodities
select distinct commodity_name
from fact_price_forecasts
order by commodity_name
```

```sql forecast_selected
select
    record_date,
    round(predicted_price_ghs, 2)        as projected_price,
    round(lower_bound_ghs, 2)            as lower_bound,
    round(upper_bound_ghs, 2)            as upper_bound,
    round(mape_score, 1)                 as mape_score,
    round(directional_accuracy * 100, 1) as dir_acc_pct,
    is_forecast
from fact_price_forecasts
where commodity_name = '${inputs.forecast_commodity}'
order by record_date
```

```sql historical_for_forecast
select
    month_start                    as record_date,
    round(avg_price_per_kg_ghs, 2) as actual_price
from fact_monthly_prices
where commodity_name = '${inputs.forecast_commodity}'
  and price_type = 'retail'
  and region = 'greater accra'
  and month_start >= '2022-01-01'
order by month_start
```

```sql watchlist
select
    f.commodity_name,
    round(f.predicted_price_ghs, 2)        as projected_price,
    round(f.lower_bound_ghs, 2)            as lower_bound,
    round(f.upper_bound_ghs, 2)            as upper_bound,
    round(f.mape_score, 1)                 as mape_pct,
    round(f.directional_accuracy * 100, 1) as dir_acc_pct,
    s.direction_signal                     as seasonal_signal
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
        ('XGBoost',  61.1, 21.5),
        ('Prophet',  47.2, 42.4),
        ('ARIMAX',   38.9, 23.8)
) t(model, directional_accuracy_pct, avg_mape_pct)
order by directional_accuracy_pct desc
```

<Dropdown
  name=forecast_commodity
  data={forecast_commodities}
  value=commodity_name
  title="Select Commodity"
  defaultValue="maize"
/>

---

<BigValue
  data={forecast_selected}
  value=projected_price
  title="Latest Projected Price (GHS/kg)"
  subtitle="Six-month model forecast from Jul 2023"
/>

<BigValue
  data={forecast_selected}
  value=mape_score
  title="Forecast Error (MAPE %)"
  subtitle="Average % deviation from actual on test data"
/>

<BigValue
  data={forecast_selected}
  value=dir_acc_pct
  title="XGBoost Directional Accuracy"
  subtitle="% of months model predicted correct direction"
/>

---

## Historical Actual Prices — Recent 18 Months

<LineChart
  data={historical_for_forecast}
  x=record_date
  y=actual_price
  title="Actual Retail Price (GHS/kg) — Greater Accra"
  subtitle="Historical context before the forecast window begins (Aug 2023)."
  colorPalette={["#1e3a5f"]}
/>

## Six-Month Model Forecast with Confidence Band

<LineChart
  data={forecast_selected}
  x=record_date
  y={["projected_price", "lower_bound", "upper_bound"]}
  title="Six-Month Projected Price (GHS/kg)"
  subtitle="Projected price with lower and upper confidence bounds. Uncertainty widens for more volatile commodities."
  colorPalette={["#7c5cd8", "#c5dce8", "#c5dce8"]}
/>

> **Forecast language:** All values are model estimates. Use as directional signals for procurement or monitoring decisions, not as exact price predictions.

---

## Six-Month Watchlist — All Forecast Commodities

<DataTable
  data={watchlist}
  rows=all
  search=false
/>

> **How to read:** `mape_pct` = average forecast error on the Jan–Jul 2023 test set (lower = more reliable). `seasonal_signal` = historical pattern for August. `dir_acc_pct` = how often the model predicted the correct price direction on holdout data.

---

## Model Validation — XGBoost vs Prophet vs ARIMAX

<BarChart
  data={model_comparison}
  x=model
  y=directional_accuracy_pct
  title="Directional Accuracy on Holdout Data (Jan–Jul 2023)"
  subtitle="XGBoost selected: highest directional accuracy — the operationally relevant metric for food security planning."
  colorPalette={["#2563a8"]}
  labels=true
/>

<BarChart
  data={model_comparison}
  x=model
  y=avg_mape_pct
  title="Average MAPE on Holdout Data"
  subtitle="Lower is better. XGBoost achieved the lowest average percentage error across all tested commodities."
  colorPalette={["#d97706"]}
  labels=true
/>

---

> **Forecast scope:** Aug–Oct 2023 (3 months available). Train: Aug 2019–Dec 2022. Test: Jan–Jul 2023. Model: XGBoost with lag features (price lags 1/2/3, MoM momentum, month-of-year, GHS/USD FX rate). Forecasts are model estimates; actual prices may differ.
