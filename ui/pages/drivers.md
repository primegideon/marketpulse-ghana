---
title: Drivers & Seasons
---

# Drivers & Seasons
### Why are prices moving — and when does it happen every year?

> **Price shocks combine macroeconomic exposure (GHS depreciation) with recurring seasonal patterns. The response should vary by commodity: import-dependent staples need macro hedging; domestically grown staples need seasonal stocking strategies.**

---

```sql commodity_list_seasonal
select distinct commodity_name
from fact_seasonal_outlook
order by commodity_name
```

```sql mom_by_commodity
select
    commodity_name,
    round(avg(mom_inflation_pct), 1)      as avg_mom_pct,
    round(avg(abs(mom_inflation_pct)), 1) as avg_abs_mom_pct,
    count(*) as months
from fact_monthly_prices
where price_type = 'retail'
  and mom_inflation_pct is not null
  and month_start >= '2021-01-01'
group by commodity_name
order by avg_mom_pct desc
```

```sql price_trend_all
select
    month_start,
    commodity_name,
    round(avg_price_per_kg_ghs, 2) as avg_price,
    round(mom_inflation_pct, 1)    as mom_pct,
    round(rolling_3m_avg, 2)       as rolling_3m
from fact_monthly_prices
where price_type = 'retail'
  and commodity_name in ('rice (imported)', 'rice (local)', 'maize', 'cassava', 'tomatoes (local)')
  and region = 'greater accra'
order by commodity_name, month_start
```

```sql seasonal_heatmap
select
    commodity_name,
    month_num,
    month_name,
    round(avg_mom_pct, 1)  as avg_mom_pct,
    round(pct_years_up, 0) as pct_years_up,
    direction_signal,
    years_observed
from fact_seasonal_outlook
order by commodity_name, month_num
```

```sql seasonal_commodity
select
    month_num,
    month_name,
    round(avg_mom_pct, 1)  as avg_mom_pct,
    round(pct_years_up, 0) as pct_years_up,
    direction_signal
from fact_seasonal_outlook
where commodity_name = '${inputs.season_commodity}'
order by month_num
```

---

## Price Growth Since 2021 — Import-Dependent vs Domestic Staples

<BarChart
  data={mom_by_commodity}
  x=commodity_name
  y=avg_mom_pct
  swapXY=true
  title="Average Monthly Price Change by Commodity (Jan 2021–Jul 2023)"
  subtitle="Import-dependent staples (rice imported, plantains) show strongest upward pressure post-2021. Domestic staples (maize, millet, sorghum) comparatively contained."
  colorPalette={["#2563a8"]}
  labels=true
/>

> **FX contribution:** An estimated ~60% of the post-2021 price increase in import-dependent staples is attributable to GHS/USD depreciation, based on the project's shock-decomposition model. Domestic staples remain exposed through input costs, fuel, and substitution channels.

---

## Monthly Price Trend with 3-Month Rolling Average

<LineChart
  data={price_trend_all}
  x=month_start
  y=rolling_3m
  series=commodity_name
  title="3-Month Rolling Average Retail Price (GHS/kg) — Greater Accra"
  subtitle="Smoothed trend removes month-to-month noise. Sharp upward divergence in rice (imported) visible from mid-2021."
/>

---

## Seasonal Price Patterns — Commodity × Month

<DataTable
  data={seasonal_heatmap}
  rows=all
  search=false
/>

> **How to read:** `avg_mom_pct` = average price change in that calendar month across observed years. `pct_years_up` = how often prices rose historically in that month. `direction_signal` = dominant seasonal pattern.
>
> **Example:** Rice tends to rise Jan–Mar (lean season) and fall Sep–Nov (harvest). Cassava shows near-opposite timing.
>
> **Caveat:** Signals are based on 4 annual cycles (2019–2023). Treat as probabilistic guidance, not prediction.

---

## Seasonal Detail — Single Commodity

<Dropdown
  name=season_commodity
  data={commodity_list_seasonal}
  value=commodity_name
  title="Select Commodity for Seasonal Detail"
  defaultValue="rice (imported)"
/>

<BarChart
  data={seasonal_commodity}
  x=month_name
  y=avg_mom_pct
  title="Average Monthly Price Change by Calendar Month"
  subtitle="Positive bars = price typically rises in that month. Negative = typically falls."
  colorPalette={["#2563a8"]}
  labels=true
/>

---

> **Data scope:** Seasonal signals based on Aug 2019–Jul 2023 retail price cycles (4 years). FX contribution estimated via shock decomposition using World Bank GHS/USD monthly rates (PA.NUS.FCRF). Findings describe correlation patterns within the WFP sample; causal identification is not claimed.
