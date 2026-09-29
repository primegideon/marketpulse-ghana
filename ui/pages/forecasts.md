---
title: "Seasonal Price Outlook"
---

# Seasonal Price Outlook

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
SELECT
    month_start,
    ROUND(AVG(avg_price_per_kg_ghs), 2) AS national_avg
FROM (
    SELECT month_start, avg_price_per_kg_ghs
    FROM agri_ghana.fact_monthly_prices
    WHERE commodity_name = '${inputs.selected_commodity.value}'
      AND price_type = 'retail'
    ORDER BY month_start DESC
    LIMIT 6
) t
GROUP BY month_start
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

<Grid cols=3>
    <BigValue
        data={latest_price}
        value="current_price"
        title="Latest Observed Retail Price (GHS/KG)"
        fmt="num2"
    />
    <BigValue
        data={trailing_3m_change}
        value="trailing_3m_pct"
        title="Trailing 3-Month Price Change (%)"
        fmt="num1"
        downIsGood=true
    />
    <BigValue
        data={gbvi_latest}
        value="gbvi_score"
        title="Current GBVI Score"
        fmt="num1"
        downIsGood=true
    />
</Grid>

<Grid cols=2>
    <BigValue
        data={gbvi_latest}
        value="risk_band"
        title="Market Risk Band"
    />
    <BigValue
        data={next_month_outlook}
        value="direction_signal"
        title="Next Month Seasonal Signal"
    />
</Grid>

<Alert status="info">
    <b>How to read this:</b> The GBVI score measures current market stress (0–30 Stable, 31–70 Moderate, 71–100 High Alert). The seasonal signal tells you what this commodity has historically done in the coming calendar month over the last five years. A High Alert GBVI combined with a "Typically rises" signal indicates compounded upward price pressure. A Stable GBVI with "Typically falls" suggests price relief is likely.
</Alert>

---

<Tabs>
    <Tab label="Next Month">

## Next Month Seasonal Signal

<Grid cols=4>
    <BigValue
        data={next_month_outlook}
        value="avg_mom_pct"
        title="Historical Avg MoM Change (%)"
        fmt="num1"
        downIsGood=true
    />
    <BigValue
        data={next_month_outlook}
        value="pct_years_up"
        title="% of Years Prices Rose"
        fmt="num0"
    />
    <BigValue
        data={next_month_outlook}
        value="pct_years_down"
        title="% of Years Prices Fell"
        fmt="num0"
    />
    <BigValue
        data={next_month_outlook}
        value="years_observed"
        title="Years on Record"
        fmt="num0"
    />
</Grid>

---

## Trailing 6-Month Price History

<AreaChart
    data={trailing_trend}
    x="month_start"
    y="national_avg"
    title="National Average Retail Price — Last 6 Months (GHS/KG)"
    subtitle="Retail prices only · Most recent observed data"
    yAxisTitle="Price (GHS/KG)"
    yMin=0
    colorPalette={['#1e3a5f']}
/>

    </Tab>
    <Tab label="Full Year Profile">

## Full Seasonal Profile — All 12 Months

Average month-over-month retail price change for each calendar month, based on the last five years of observations. Months above zero typically see prices rise; months below zero typically see prices fall. The range bar shows the minimum and maximum observed change across all years.

<BarChart
    data={seasonal_profile}
    x="month_name"
    y="avg_mom_pct"
    title="Average MoM Retail Price Change by Calendar Month (%)"
    subtitle="Retail prices · 2018–2023 · Positive = prices typically rise that month"
    yAxisTitle="Avg MoM Change (%)"
    colorPalette={['#2563a8']}
    labels=false
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
