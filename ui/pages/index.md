---
title: National Pulse
---

# MarketPulse Ghana
### Agricultural Price Intelligence for Food Security

> **Ghana's staple-food basket moved from relative stability into a High Alert volatility phase in 2022 — driven by a cedi depreciation of over 55% between January and October 2022.**

---

```sql gbvi_latest
select
    month_start,
    round(gbvi_score, 1)   as gbvi_score,
    risk_band,
    round(avg_abs_mom_pct, 1) as avg_abs_mom_pct
from agri_ghana.fact_gbvi_index
order by month_start desc
limit 1
```

```sql gbvi_peak
select
    month_start,
    round(gbvi_score, 1) as gbvi_score,
    risk_band
from agri_ghana.fact_gbvi_index
order by gbvi_score desc
limit 1
```

```sql commodity_volatility
select
    commodity_name,
    round(avg(abs(mom_inflation_pct)), 1) as avg_abs_mom_pct
from agri_ghana.fact_monthly_prices
where price_type = 'retail'
  and mom_inflation_pct is not null
group by commodity_name
order by avg_abs_mom_pct desc
```

```sql gbvi_trend
select
    month_start,
    round(gbvi_score, 1)  as gbvi_score,
    risk_band,
    round(avg_mom_pct, 1) as avg_mom_pct
from agri_ghana.fact_gbvi_index
order by month_start
```

```sql price_index
select
    p.month_start,
    p.commodity_name,
    round(
        p.avg_price_per_kg_ghs
        / first_value(p.avg_price_per_kg_ghs) over (
            partition by p.commodity_name
            order by p.month_start
            rows between unbounded preceding and unbounded following
        ) * 100,
    1) as price_index
from agri_ghana.fact_monthly_prices p
where p.price_type = 'retail'
  and p.commodity_name in ('rice (imported)', 'maize', 'tomatoes (local)', 'cassava', 'plantains (apentu)', 'millet')
  and p.region = 'greater accra'
order by p.commodity_name, p.month_start
```

<BigValue
  data={gbvi_latest}
  value=gbvi_score
  title="Latest GBVI Score — Jul 2023"
  subtitle={gbvi_latest[0].risk_band}
/>

<BigValue
  data={gbvi_peak}
  value=gbvi_score
  title="Peak GBVI Score"
  subtitle={"Reached " + gbvi_peak[0].month_start}
/>

<BigValue
  data={commodity_volatility}
  value=commodity_name
  title="Most Volatile Commodity"
  subtitle={"Avg ±" + commodity_volatility[0].avg_abs_mom_pct + "% MoM"}
/>

<BigValue
  data={commodity_volatility}
  rows=2
  value=commodity_name
  title="Most Stable Staples"
  subtitle="Lowest average monthly price movement"
/>

---

## Ghana Basket Volatility Index — Aug 2019 to Jul 2023

<LineChart
  data={gbvi_trend}
  x=month_start
  y=gbvi_score
  yMin=0
  yMax=100
  title="GBVI Score — Monthly Food Price Volatility"
  subtitle="Shaded bands: Stable (0–30) · Moderate (31–70) · High Alert (71–100)"
  labels=true
  colorPalette={["#2563a8"]}
/>

> **2022 peak:** Broad food-price instability coincided with cedi depreciation exceeding 55% (Jan–Oct 2022), raising import costs across rice, plantains, and processed staples.

---

## Commodity Volatility Ranking

<BarChart
  data={commodity_volatility}
  x=commodity_name
  y=avg_abs_mom_pct
  swapXY=true
  title="Average Absolute Month-on-Month Price Change by Commodity (Retail)"
  subtitle="Higher = more volatile. Tomatoes, peppers, and onions show greatest short-term instability."
  colorPalette={["#2563a8"]}
  labels=true
/>

---

## Price Index by Commodity — Indexed to Aug 2019 = 100

<LineChart
  data={price_index}
  x=month_start
  y=price_index
  series=commodity_name
  title="Retail Price Index (Aug 2019 = 100) — Greater Accra"
  subtitle="Shows relative price growth since the start of the retail observation window."
  labels=false
/>

> **Reading this chart:** A value of 150 means prices are 50% higher than August 2019. Rice (imported) rose sharply in 2022 alongside the cedi depreciation; maize and cassava showed comparatively stable trajectories.

---

> **Data scope:** Monthly retail prices across 44 georeferenced markets in 10 Ghanaian regions, Aug 2019–Jul 2023. Source: WFP VAM Ghana via HDX. Prices in nominal GHS/kg.
