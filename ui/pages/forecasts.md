---
title: "Seasonal Price Outlook"
---

Historical price behaviour for Ghana's core staple commodities, by calendar month. Based on retail price data from 2018–2023 — the five most recent years of consistent WFP retail coverage.

Use this to answer: **given the current month, what has this commodity's price typically done?**

```sql outlook_commodities
SELECT DISTINCT commodity_name
FROM agri_ghana.fact_seasonal_outlook
ORDER BY commodity_name
```

<Dropdown
    name="selected_commodity"
    data={outlook_commodities}
    value="commodity_name"
    title="Commodity"
    defaultValue="maize"
/>

```sql seasonal_profile
SELECT
    month_name,
    month_num,
    avg_mom_pct,
    min_mom_pct,
    max_mom_pct,
    stddev_mom_pct,
    pct_years_up,
    pct_years_down,
    direction_signal,
    years_observed
FROM agri_ghana.fact_seasonal_outlook
WHERE commodity_name = '${inputs.selected_commodity.value}'
ORDER BY month_num
```

```sql trailing_trend
SELECT month_start, national_avg
FROM (
    SELECT
        month_start,
        ROUND(AVG(avg_price_per_kg_ghs), 2) AS national_avg
    FROM agri_ghana.fact_monthly_prices
    WHERE commodity_name = '${inputs.selected_commodity.value}'
      AND price_type = 'retail'
    GROUP BY month_start
    ORDER BY month_start DESC
    LIMIT 6
) t
ORDER BY month_start ASC
```

```sql price_sparkline
SELECT month_start, national_avg
FROM (
    SELECT
        month_start,
        ROUND(AVG(avg_price_per_kg_ghs), 2) AS national_avg
    FROM agri_ghana.fact_monthly_prices
    WHERE commodity_name = '${inputs.selected_commodity.value}'
      AND price_type = 'retail'
    GROUP BY month_start
    ORDER BY month_start DESC
    LIMIT 24
) t
ORDER BY month_start ASC
```

```sql latest_price
SELECT
    ROUND(AVG(avg_price_per_kg_ghs), 2) AS current_price
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND price_type = 'retail'
  AND month_start = (
      SELECT MAX(month_start)
      FROM agri_ghana.fact_monthly_prices
      WHERE commodity_name = '${inputs.selected_commodity.value}'
        AND price_type = 'retail'
  )
```

```sql price_3m_ago
SELECT
    ROUND(AVG(avg_price_per_kg_ghs), 2) AS price_3m_ago
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND price_type = 'retail'
  AND month_start = (
      SELECT DISTINCT month_start
      FROM agri_ghana.fact_monthly_prices
      WHERE commodity_name = '${inputs.selected_commodity.value}'
        AND price_type = 'retail'
      ORDER BY month_start DESC
      LIMIT 1 OFFSET 3
  )
```

```sql trailing_3m_change
SELECT
    ROUND(
        (${latest_price[0].current_price} - ${price_3m_ago[0].price_3m_ago})
        / NULLIF(${price_3m_ago[0].price_3m_ago}, 0) * 100
    , 1) AS trailing_3m_pct
```

```sql gbvi_latest
SELECT
    gbvi_score,
    risk_band,
    month_start
FROM agri_ghana.fact_gbvi_index
ORDER BY month_start DESC
LIMIT 1
```

```sql next_month_num
SELECT
    ((EXTRACT(month FROM MAX(month_start))::INTEGER % 12) + 1) AS next_month
FROM agri_ghana.fact_monthly_prices
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND price_type = 'retail'
```

```sql next_month_outlook
SELECT
    month_name,
    avg_mom_pct,
    min_mom_pct,
    max_mom_pct,
    pct_years_up,
    pct_years_down,
    direction_signal,
    years_observed
FROM agri_ghana.fact_seasonal_outlook
WHERE commodity_name = '${inputs.selected_commodity.value}'
  AND month_num = ${next_month_num[0].next_month}
```

---

## Market Context

<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:12px">

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #1e3a5f">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#e8f0fa;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="#1e3a5f" stroke-width="1.3"/><line x1="7" y1="4" x2="7" y2="7.5" stroke="#1e3a5f" stroke-width="1.4" stroke-linecap="round"/><circle cx="7" cy="9.5" r="0.7" fill="#1e3a5f"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Latest Retail Price</span>
</div>
<BigValue data={latest_price} value="current_price" fmt="num2"/>
<div style="font-size:10px;color:#57606a;margin-top:4px">GHS per KG · Most recent month</div>
<Sparkline data={price_sparkline} dateCol="month_start" valueCol="national_avg" type="area" color="#1e3a5f" height=28 width=160/>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #d97706">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fef3c7;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,11 4.5,6.5 8,8.5 13,2.5" stroke="#d97706" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9.5,2.5 13,2.5 13,6" stroke="#d97706" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">3-Month Price Change</span>
</div>
<BigValue data={trailing_3m_change} value="trailing_3m_pct" fmt="num1" downIsGood=true/>
<div style="font-size:10px;color:#57606a;margin-top:4px">% change · Latest vs 3 months prior</div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #b91c1c">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fee2e2;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1" y="7" width="2.5" height="6" rx="1" fill="#b91c1c"/><rect x="5.5" y="4" width="2.5" height="9" rx="1" fill="#b91c1c"/><rect x="10" y="1" width="2.5" height="12" rx="1" fill="#b91c1c"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Current GBVI Score</span>
</div>
<BigValue data={gbvi_latest} value="gbvi_score" fmt="num1" downIsGood=true/>
<div style="font-size:10px;color:#57606a;margin-top:4px">Basket volatility index · 0–100</div>
</div>

</div>

<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:8px">

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #1e3a5f">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#e8f0fa;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M6.2 1.8L1 11h12.1L7.8 1.8a.9.9 0 0 0-1.6 0Z" stroke="#1e3a5f" stroke-width="1.3" fill="none"/><line x1="7" y1="5.5" x2="7" y2="8.5" stroke="#1e3a5f" stroke-width="1.3" stroke-linecap="round"/><circle cx="7" cy="10.2" r="0.6" fill="#1e3a5f"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Market Risk Band</span>
</div>
<BigValue data={gbvi_latest} value="risk_band"/>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #15803d">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#dcfce7;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="5.5" stroke="#15803d" stroke-width="1.3"/><polyline points="4.5,7 6.5,9 9.5,5" stroke="#15803d" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Next Month Seasonal Signal</span>
</div>
<BigValue data={next_month_outlook} value="direction_signal"/>
</div>

</div>

<Alert status="info">
    <b>How to read this:</b> The GBVI score measures current market stress (0–30 Stable, 31–70 Moderate, 71–100 High Alert). The seasonal signal tells you what this commodity has historically done in the coming calendar month over the last five years. A High Alert GBVI combined with a "Typically rises" signal indicates compounded upward price pressure. A Stable GBVI with "Typically falls" suggests price relief is likely.
</Alert>

---

<Tabs>
    <Tab label="Next Month">

## Next Month Seasonal Signal

<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:8px">

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #d97706">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fef3c7;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,7 3,7 4.8,2.5 6.8,11.5 8.5,5.5 10.5,7 13,7" stroke="#d97706" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Avg MoM Change</span>
</div>
<BigValue data={next_month_outlook} value="avg_mom_pct" fmt="num1" downIsGood=true/>
<div style="font-size:10px;color:#57606a;margin-top:4px">% · Historical average</div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #b91c1c">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#fee2e2;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,11 4.5,6.5 8,8.5 13,2.5" stroke="#b91c1c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9.5,2.5 13,2.5 13,6" stroke="#b91c1c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Years Prices Rose</span>
</div>
<BigValue data={next_month_outlook} value="pct_years_up" fmt="num0"/>
<div style="font-size:10px;color:#57606a;margin-top:4px">% of observed years</div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #15803d">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#dcfce7;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><polyline points="1,3 4.5,7.5 8,5.5 13,11.5" stroke="#15803d" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9.5,11.5 13,11.5 13,8" stroke="#15803d" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Years Prices Fell</span>
</div>
<BigValue data={next_month_outlook} value="pct_years_down" fmt="num0"/>
<div style="font-size:10px;color:#57606a;margin-top:4px">% of observed years</div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;border-top:3px solid #1e3a5f">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
<div style="width:28px;height:28px;background:#e8f0fa;border-radius:6px;display:flex;align-items:center;justify-content:center">
<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="1.5" y="2" width="11" height="10" rx="1.5" stroke="#1e3a5f" stroke-width="1.3" fill="none"/><line x1="1.5" y1="5.5" x2="12.5" y2="5.5" stroke="#1e3a5f" stroke-width="1"/><line x1="5" y1="2" x2="5" y2="1" stroke="#1e3a5f" stroke-width="1.3" stroke-linecap="round"/><line x1="9" y1="2" x2="9" y2="1" stroke="#1e3a5f" stroke-width="1.3" stroke-linecap="round"/></svg>
</div>
<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#57606a">Years on Record</span>
</div>
<BigValue data={next_month_outlook} value="years_observed" fmt="num0"/>
<div style="font-size:10px;color:#57606a;margin-top:4px">Observation window</div>
</div>

</div>

---

## Trailing 6-Month Price History

<AreaChart
    data={trailing_trend}
    x="month_start"
    y="national_avg"
    title="National Average Retail Price — Last 6 Months (GHS/KG)"
    subtitle="Retail prices only · Most recent 6 observed months"
    yAxisTitle="Price (GHS/KG)"
    yMin=0
    colorPalette={['#1e3a5f']}
    markers=true
/>

    </Tab>
    <Tab label="Full Year Profile">

## Full Seasonal Profile — All 12 Months

Average month-over-month retail price change for each calendar month, based on the last five years of observations. Months above zero typically see prices rise; months below zero typically see prices fall.

<BarChart
    data={seasonal_profile}
    x="month_name"
    y="avg_mom_pct"
    title="Average MoM Retail Price Change by Calendar Month (%)"
    subtitle="Retail prices · 2018–2023 · Positive = prices typically rise that month"
    yAxisTitle="Avg MoM Change (%)"
    colorPalette={['#2563a8']}
    fmt="num1"
    sort=false
    labels=true
    labelFmt="num1"
/>

<Alert status="info">
    <b>Seasonal drivers:</b> Price rises in the lean season (January–April) reflect depleted reserves from the prior harvest before new-season supply arrives. Price falls in September–October align with the main harvest. Tomatoes and plantains show the most extreme swings due to perishability and thin market depth — a supply disruption can double urban prices within a single month.
</Alert>

---

## Seasonal Detail Table

<DataTable data={seasonal_profile} rowNumbers=false>
    <Column id="month_name" title="Month" />
    <Column id="avg_mom_pct" title="Avg MoM Change (%)" fmt="num1" contentType="colorscale" scaleColor="blue" />
    <Column id="min_mom_pct" title="Worst Case (%)" fmt="num1" />
    <Column id="max_mom_pct" title="Best Case (%)" fmt="num1" />
    <Column id="pct_years_up" title="Years Up (%)" fmt="num0" />
    <Column id="pct_years_down" title="Years Down (%)" fmt="num0" />
    <Column id="direction_signal" title="Signal" />
    <Column id="years_observed" title="Years on Record" />
</DataTable>

    </Tab>
</Tabs>
