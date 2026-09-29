---
title: "Supply Chain Price Spreads"
---

Analysis of the retail price gap between agricultural producing regions and urban consumer markets. A high spread margin indicates supply chain friction — transport costs, intermediary markups, or market access barriers that raise the cost of food for urban households above farm-gate levels.

**Producing regions:** Brong Ahafo, Northern, Upper East, Upper West, Volta &nbsp;·&nbsp; **Urban consumer regions:** Greater Accra, Ashanti

```sql latest_spread
SELECT
    commodity_name,
    ROUND(AVG(producing_avg_price), 2)       AS producing_avg_price,
    ROUND(AVG(urban_avg_price), 2)           AS urban_avg_price,
    ROUND(AVG(absolute_spread_ghs), 2)       AS absolute_spread_ghs,
    ROUND(AVG(spread_margin_pct), 1)         AS spread_margin_pct,
    ROUND(AVG(spread_margin_pct / 100.0), 4) AS spread_margin_pct_dec
FROM agri_ghana.fact_market_spreads
WHERE month_start = (SELECT MAX(month_start) FROM agri_ghana.fact_market_spreads)
  AND spread_margin_pct > 0
GROUP BY commodity_name
ORDER BY spread_margin_pct DESC
```

```sql spread_kpis
SELECT
    ROUND(AVG(spread_margin_pct), 1)         AS avg_spread_pct,
    ROUND(MAX(spread_margin_pct), 1)         AS max_spread_pct,
    COUNT(DISTINCT commodity_name)           AS commodities_monitored,
    COUNT(DISTINCT month_start)              AS months_on_record
FROM agri_ghana.fact_market_spreads
WHERE spread_margin_pct IS NOT NULL
  AND spread_margin_pct > 0
```

```sql spread_kpis_sparkline
SELECT
    month_start,
    ROUND(AVG(spread_margin_pct), 1) AS avg_spread_pct
FROM agri_ghana.fact_market_spreads
WHERE spread_margin_pct > 0
GROUP BY month_start
ORDER BY month_start DESC
LIMIT 24
```

```sql top_spread_commodities
SELECT
    commodity_name,
    ROUND(AVG(spread_margin_pct), 1) AS avg_spread_pct,
    ROUND(MAX(spread_margin_pct), 1) AS peak_spread_pct,
    COUNT(DISTINCT month_start)      AS months_observed
FROM agri_ghana.fact_market_spreads
WHERE spread_margin_pct > 0
GROUP BY commodity_name
ORDER BY avg_spread_pct DESC
LIMIT 10
```

```sql spread_commodities_list
SELECT DISTINCT commodity_name
FROM agri_ghana.fact_market_spreads
WHERE spread_margin_pct > 0
ORDER BY commodity_name
```

---

## Supply Chain Overview

<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:8px">

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #d97706">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fef3c7;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,7 3,7 4.8,2.5 6.8,11.5 8.5,5.5 10.5,7 13,7" stroke="#d97706" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Avg Urban Markup</span>
</div>
<BigValue data={spread_kpis} value="avg_spread_pct" fmt="num1" downIsGood=true/>
<div style="font-size:10px;color:#57606a;margin-top:4px">% above farm-gate · All commodities</div>
<Sparkline data={spread_kpis_sparkline} dateCol="month_start" valueCol="avg_spread_pct" type="area" color="#d97706" height=28 width=160/>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #b91c1c">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fee2e2;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,11 4.5,6.5 8,8.5 13,2.5" stroke="#b91c1c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9.5,2.5 13,2.5 13,6" stroke="#b91c1c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Peak Recorded Markup</span>
</div>
<BigValue data={spread_kpis} value="max_spread_pct" fmt="num1" downIsGood=true/>
<div style="font-size:10px;color:#57606a;margin-top:4px">% · Fresh peppers, Aug 2021</div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #1e3a5f">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#e8f0fa;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="7" width="2.5" height="6" rx="1" fill="#1e3a5f"/><rect x="5.5" y="4" width="2.5" height="9" rx="1" fill="#1e3a5f"/><rect x="10" y="1" width="2.5" height="12" rx="1" fill="#1e3a5f"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Commodities Tracked</span>
</div>
<BigValue data={spread_kpis} value="commodities_monitored"/>
<div style="font-size:10px;color:#57606a;margin-top:4px">Across all markets</div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #1e3a5f">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#e8f0fa;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1.5" y="2" width="11" height="10" rx="1.5" stroke="#1e3a5f" stroke-width="1.3" fill="none"/><line x1="1.5" y1="5.5" x2="12.5" y2="5.5" stroke="#1e3a5f" stroke-width="1"/><line x1="5" y1="2" x2="5" y2="1" stroke="#1e3a5f" stroke-width="1.3" stroke-linecap="round"/><line x1="9" y1="2" x2="9" y2="1" stroke="#1e3a5f" stroke-width="1.3" stroke-linecap="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Months on Record</span>
</div>
<BigValue data={spread_kpis} value="months_on_record"/>
<div style="font-size:10px;color:#57606a;margin-top:4px">Jan 2008 – Jul 2023</div>
</div>

</div>

---

<Tabs>
    <Tab label="Latest Month">

## Urban Markup by Commodity — Latest Month

How much more expensive is each commodity in urban consumer markets relative to farm-gate prices in producing regions? A markup of 100% means the urban price is double the producing-region price.

<BarChart
    data={latest_spread}
    x="commodity_name"
    y="spread_margin_pct_dec"
    title="Urban Price Premium over Farm-Gate — Latest Month"
    subtitle="Retail prices only · Sorted highest to lowest · Values are % above farm-gate price"
    yAxisTitle="Urban Markup (%)"
    swapXY=true
    fmt="pct1"
    labels=true
    labelFmt="pct0"
    colorPalette={['#2563a8']}
/>

---

## Price Gap Detail — Latest Month

<DataTable data={latest_spread} search=true rowNumbers=false>
    <Column id="commodity_name" title="Commodity" />
    <Column id="producing_avg_price" title="Farm-Gate (GHS/KG)" fmt="num2" />
    <Column id="urban_avg_price" title="Urban Price (GHS/KG)" fmt="num2" />
    <Column id="absolute_spread_ghs" title="Absolute Gap (GHS/KG)" fmt="num2" />
    <Column id="spread_margin_pct_dec" title="Urban Markup" fmt="pct1" contentType="colorscale" scaleColor="blue" />
</DataTable>

    </Tab>
    <Tab label="Spread Trend">

## Urban Markup Trend (2020 – 2023)

Monthly urban markup for a single commodity since January 2020. Spread widening can be traced to dry-season road deterioration, fuel price increases, or perishability-driven farm-gate price collapses. Select a commodity to examine its spread history.

<Dropdown
    name="trend_commodity"
    data={spread_commodities_list}
    value="commodity_name"
    title="Commodity"
    defaultValue="maize"
/>

```sql spread_trend_filtered
SELECT
    month_start,
    ROUND(AVG(spread_margin_pct), 1) AS spread_margin_pct
FROM agri_ghana.fact_market_spreads
WHERE month_start >= '2020-01-01'
  AND spread_margin_pct > 0
  AND commodity_name = '${inputs.trend_commodity.value}'
GROUP BY month_start
ORDER BY month_start ASC
```

<AreaChart
    data={spread_trend_filtered}
    x="month_start"
    y="spread_margin_pct"
    title="Urban vs Farm-Gate Price Spread — Monthly Markup (%)"
    subtitle="Values are percentage points above farm-gate price · 2020–2023"
    yAxisTitle="Urban Markup (%)"
    fmt="num1"
    markers=true
    colorPalette={['#1e3a5f']}
    referenceLines={[
        {x: '2022-11-01', label: 'Cedi depreciation crisis', color: '#d97706', lineType: 'dashed'}
    ]}
/>

<Alert status="info">
    <b>Spread drivers:</b> Spreads typically widen during the dry season (November–March) when road conditions in the Northern and Upper regions raise transport costs. Tomatoes and plantains show the most volatile spreads because any supply disruption rapidly inflates urban prices while farm-gate prices simultaneously collapse, amplifying the margin.
</Alert>

    </Tab>
    <Tab label="All Commodities">

## Average Urban Markup by Commodity — Full Period

Which commodities have sustained the highest urban price premiums over the full observation period? High sustained markups indicate persistent supply chain inefficiencies rather than one-off events.

<BarChart
    data={top_spread_commodities}
    x="commodity_name"
    y="avg_spread_pct"
    title="Top 10 Commodities by Average Urban Markup — Full Observation Period"
    subtitle="Values are % above farm-gate price · Higher = more persistent supply chain friction"
    yAxisTitle="Avg Urban Markup (%)"
    swapXY=true
    fmt="num1"
    labels=true
    labelFmt="num1"
    colorPalette={['#1e3a5f']}
/>

    </Tab>
</Tabs>
