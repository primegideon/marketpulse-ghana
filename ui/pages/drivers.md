---
title: Drivers & Seasons
---

> **Price shocks combine macroeconomic exposure (GHS depreciation) with recurring seasonal patterns. Response should vary by commodity: import-dependent staples need macro hedging; domestic staples need seasonal stocking strategies.**

---

```sql commodity_list_seasonal
select distinct commodity_name
from fact_seasonal_outlook
order by commodity_name
```

<Dropdown
  name=season_commodity
  data={commodity_list_seasonal}
  value=commodity_name
  title="Commodity (for Seasonal Patterns tab)"
  defaultValue="rice (imported)"
/>

```sql mom_by_commodity
select
    commodity_name,
    round(avg(mom_inflation_pct), 1)      as avg_mom,
    round(avg(abs(mom_inflation_pct)), 1) as avg_abs_mom
from fact_monthly_prices
where price_type = 'retail'
  and mom_inflation_pct is not null
  and month_start >= '2021-01-01'
group by commodity_name
order by avg_mom desc
```

```sql price_trend_all
select
    month_start,
    commodity_name,
    round(rolling_3m_avg, 2) as rolling_3m
from fact_monthly_prices
where price_type = 'retail'
  and commodity_name in ('rice (imported)', 'rice (local)', 'maize', 'cassava', 'tomatoes (local)')
  and region = 'greater accra'
  and rolling_3m_avg is not null
order by commodity_name, month_start
```

```sql seasonal_heatmap
select
    commodity_name,
    month_num,
    month_name,
    round(avg_mom_pct, 1)  as avg_mom,
    round(pct_years_up, 0) as years_up,
    direction_signal
from fact_seasonal_outlook
where commodity_name = coalesce(nullif('${inputs.season_commodity}', ''), 'rice (imported)')
order by month_num
```

---

<Tabs>
  <Tab label="Post-2021 Price Growth">

## Average Monthly Price Change — Jan 2021 to Jul 2023

<BarChart
  data={mom_by_commodity}
  x=commodity_name
  y=avg_mom
  swapXY=true
  title="Average Monthly Price Change by Commodity (%, Jan 2021–Jul 2023)"
  subtitle="Import-dependent staples (rice imported, plantains) show strongest upward pressure. Domestic staples comparatively contained."
  colorPalette={["#2563a8"]}
  labels=true
/>

> **FX contribution:** An estimated ~60% of the post-2021 price increase in import-dependent staples is attributable to GHS/USD depreciation. Domestic staples remain exposed through input costs, fuel, and substitution channels.

  </Tab>
  <Tab label="Rolling Price Trend">

## 3-Month Rolling Average Retail Price (GHS/kg) — Greater Accra

<LineChart
  data={price_trend_all}
  x=month_start
  y=rolling_3m
  series=commodity_name
  title="3-Month Rolling Average Retail Price (GHS/kg) — Greater Accra"
  subtitle="Smoothed trend removes month-to-month noise. Sharp upward divergence in rice (imported) visible from mid-2021."
/>

  </Tab>
  <Tab label="Seasonal Patterns">

## Seasonal Price Patterns by Commodity

Select a commodity using the dropdown above to filter the table and chart below.

<DataTable
  data={seasonal_heatmap}
  rows=all
  search=false
/>

<BarChart
  data={seasonal_heatmap}
  x=month_name
  y=avg_mom
  title="Average Monthly Price Change by Calendar Month (%)"
  subtitle="Positive = price typically rises that month. Negative = typically falls. Based on 4 years of data (2019–2023)."
  colorPalette={["#2563a8"]}
  labels=true
/>

> **Example:** Rice (imported) tends to rise Jan–Mar (lean season) and fall Sep–Nov (harvest). Cassava shows near-opposite timing.
>
> **Caveat:** Signals are based on 4 annual cycles only. Treat as probabilistic guidance, not prediction.

  </Tab>
</Tabs>

---

> **Data scope:** Seasonal signals based on Aug 2019–Jul 2023 retail price cycles (4 years). FX contribution estimated via shock decomposition using World Bank GHS/USD monthly rates (PA.NUS.FCRF). Causal identification is not claimed.
