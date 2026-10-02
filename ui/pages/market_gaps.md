---
title: Market Gaps
---

> **The 2022 shock widened the urban–rural price gap, creating uneven exposure across Ghana's markets and regions.**

---

```sql commodity_list
select distinct commodity_name
from fact_market_spreads
where price_type = 'retail'
order by commodity_name
```

<Dropdown
  name=commodity
  data={commodity_list}
  value=commodity_name
  title="Commodity"
  defaultValue="maize"
/>

```sql spread_latest
select
    round(urban_avg_price, 2)     as urban_price,
    round(producing_avg_price, 2) as rural_price,
    round(absolute_spread_ghs, 2) as spread_ghs,
    round(spread_margin_pct, 1)   as spread_pct
from fact_market_spreads
where price_type = 'retail'
  and commodity_name = '${inputs.commodity}'
order by month_start desc
limit 1
```

```sql spread_trend
select
    month_start,
    round(urban_avg_price, 2)     as urban_price,
    round(producing_avg_price, 2) as rural_price,
    round(spread_margin_pct, 1)   as spread_pct
from fact_market_spreads
where price_type = 'retail'
  and commodity_name = '${inputs.commodity}'
order by month_start
```

```sql spread_ranking
select
    commodity_name,
    round(avg(spread_margin_pct), 1)   as avg_spread_pct,
    round(avg(absolute_spread_ghs), 2) as avg_spread_ghs
from fact_market_spreads
where price_type = 'retail'
  and month_start >= '2022-01-01'
group by commodity_name
order by avg_spread_pct desc
```

```sql market_prices
select
    p.region,
    round(avg(p.avg_price_per_kg_ghs), 2) as avg_price
from fact_monthly_prices p
where p.price_type = 'retail'
  and p.commodity_name = '${inputs.commodity}'
group by p.region
order by avg_price desc
```

---

<BigValue
  data={spread_latest}
  value=urban_price
  title="Urban Price (GHS/kg)"
  subtitle="Greater Accra / Ashanti — latest month"
/>

<BigValue
  data={spread_latest}
  value=rural_price
  title="Rural Price (GHS/kg)"
  subtitle="Producing region — latest month"
/>

<BigValue
  data={spread_latest}
  value=spread_ghs
  title="Spread (GHS/kg)"
  subtitle="Urban minus rural"
/>

<BigValue
  data={spread_latest}
  value=spread_pct
  title="Spread Margin (%)"
  subtitle="Urban premium over rural"
/>

---

<Tabs>
  <Tab label="Price Lines">

## Urban vs Rural Retail Price — Over Time

<LineChart
  data={spread_trend}
  x=month_start
  y={["urban_price", "rural_price"]}
  title="Urban vs Rural Average Retail Price (GHS/kg)"
  subtitle="Urban = Greater Accra + Ashanti. Rural = Northern, Upper East, Upper West, Brong Ahafo, Volta."
/>

  </Tab>
  <Tab label="Spread Over Time">

## Urban–Rural Spread Margin Over Time

<AreaChart
  data={spread_trend}
  x=month_start
  y=spread_pct
  title="Urban–Rural Spread Margin (%)"
  subtitle="Widening gap signals logistics/supply chain cost pressure."
  colorPalette={["#d97706"]}
/>

  </Tab>
  <Tab label="By Commodity (2022+)">

## Price Gap by Commodity — 2022 Onwards

<BarChart
  data={spread_ranking}
  x=commodity_name
  y=avg_spread_pct
  swapXY=true
  title="Average Urban–Rural Spread Margin by Commodity (%)"
  subtitle="Jan 2022–Jul 2023. Which commodities carry the largest geographic price burden."
  colorPalette={["#b45309"]}
  labels=true
/>

  </Tab>
  <Tab label="By Region">

## Regional Average Price Comparison

<BarChart
  data={market_prices}
  x=region
  y=avg_price
  swapXY=true
  title="Average Retail Price by Region (GHS/kg)"
  subtitle="All available retail observations for selected commodity."
  colorPalette={["#2563a8"]}
  labels=true
/>

  </Tab>
</Tabs>

---

> **Data scope:** Monthly retail prices, Aug 2019–Jul 2023. Urban = Greater Accra + Ashanti; Rural = Northern, Upper East, Upper West, Brong Ahafo, Volta. Source: WFP VAM Ghana via HDX.
