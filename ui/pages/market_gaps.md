---
title: Market Gaps
---

# Market Gaps
### Where are the price pressure points across Ghana's markets?

> **The 2022 shock widened the urban–rural price gap, creating uneven exposure across Ghana's markets and regions.**

---

```sql inputs
select
    '${inputs.commodity}' as selected_commodity
```

```sql spread_latest
select
    commodity_name,
    round(urban_avg_price, 2)    as urban_price,
    round(producing_avg_price, 2) as rural_price,
    round(absolute_spread_ghs, 2) as spread_ghs,
    round(spread_margin_pct, 1)   as spread_pct
from agri_ghana.fact_market_spreads
where price_type = 'retail'
  and commodity_name = '${inputs.commodity.value}'
order by month_start desc
limit 1
```

```sql spread_trend
select
    month_start,
    commodity_name,
    round(urban_avg_price, 2)     as urban_price,
    round(producing_avg_price, 2) as rural_price,
    round(absolute_spread_ghs, 2) as spread_ghs,
    round(spread_margin_pct, 1)   as spread_pct
from agri_ghana.fact_market_spreads
where price_type = 'retail'
  and commodity_name = '${inputs.commodity.value}'
order by month_start
```

```sql spread_ranking
select
    commodity_name,
    round(avg(spread_margin_pct), 1) as avg_spread_pct,
    round(avg(absolute_spread_ghs), 2) as avg_spread_ghs,
    round(avg(urban_avg_price), 2) as avg_urban_price
from agri_ghana.fact_market_spreads
where price_type = 'retail'
  and month_start >= '2022-01-01'
group by commodity_name
order by avg_spread_pct desc
```

```sql market_prices
select
    p.region,
    p.commodity_name,
    round(avg(p.avg_price_per_kg_ghs), 2) as avg_price,
    round(avg(p.mom_inflation_pct), 1)    as avg_mom_pct,
    count(distinct p.month_start)         as months_observed
from agri_ghana.fact_monthly_prices p
where p.price_type = 'retail'
  and p.commodity_name = '${inputs.commodity.value}'
group by p.region, p.commodity_name
order by avg_price desc
```

```sql commodity_list
select distinct commodity_name
from agri_ghana.fact_market_spreads
where price_type = 'retail'
order by commodity_name
```

<Dropdown
  name=commodity
  data={commodity_list}
  value=commodity_name
  title="Select Commodity"
  defaultValue="maize"
/>

---

<BigValue
  data={spread_latest}
  value=urban_price
  title="Latest Urban Price (GHS/kg)"
  subtitle="Greater Accra / Ashanti average"
/>

<BigValue
  data={spread_latest}
  value=rural_price
  title="Latest Rural Price (GHS/kg)"
  subtitle="Producing region average"
/>

<BigValue
  data={spread_latest}
  value=spread_ghs
  title="Urban–Rural Spread (GHS/kg)"
  subtitle="Absolute price gap"
/>

<BigValue
  data={spread_latest}
  value=spread_pct
  title="Spread Margin (%)"
  subtitle="Urban premium over rural"
/>

---

## Urban vs Rural Retail Price — Over Time

<LineChart
  data={spread_trend}
  x=month_start
  y={["urban_price", "rural_price"]}
  title="Urban vs Rural Average Retail Price (GHS/kg)"
  subtitle="Urban = Greater Accra + Ashanti. Rural = Northern, Upper East, Upper West, Brong Ahafo, Volta."
  labels=false
/>

---

## Urban–Rural Spread Margin Over Time

<AreaChart
  data={spread_trend}
  x=month_start
  y=spread_pct
  title="Urban–Rural Spread Margin (%)"
  subtitle="Positive = urban consumers pay more than rural. Widening gap signals logistics/supply chain stress."
  colorPalette={["#d97706"]}
/>

---

## Price Gap by Commodity — 2022 Onwards

<BarChart
  data={spread_ranking}
  x=commodity_name
  y=avg_spread_pct
  swapXY=true
  title="Average Urban–Rural Spread Margin by Commodity (Jan 2022–Jul 2023)"
  subtitle="Shows which commodities carry the largest geographic price burden."
  colorPalette={["#b45309"]}
  labels=true
/>

---

## Regional Average Price Comparison

<BarChart
  data={market_prices}
  x=region
  y=avg_price
  swapXY=true
  title="Average Retail Price by Region (GHS/kg)"
  subtitle="Based on all available retail observations. Select a commodity above to update."
  colorPalette={["#2563a8"]}
  labels=true
/>

> **44 markets monitored** across 10 Ghanaian regions. Urban markets (Greater Accra, Ashanti) consistently show higher consumer prices than producing regions (Northern, Upper East/West, Brong Ahafo).

---

> **Data scope:** Monthly retail prices across 44 georeferenced markets in 10 Ghanaian regions, Aug 2019–Jul 2023. Source: WFP VAM Ghana via HDX. Urban/rural classification based on administrative region: urban = Greater Accra + Ashanti; producing/rural = Northern, Upper East, Upper West, Brong Ahafo, Volta.
