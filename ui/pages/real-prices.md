---
title: Real (CPI-Adjusted) Prices
---

# Inflation-Adjusted Food Prices

> **What you're seeing**: All prices deflated to 2015 Ghana Cedis using Ghana Statistical Service CPI estimates. This separates *real food supply/demand dynamics* from *monetary inflation effects*.

Over Ghana's 17-year monitoring window, headline inflation (peaking above 54% YoY in late 2022) dramatically distorts nominal price signals. CPI-adjusted "real" prices reveal whether food has actually become more or less affordable in constant-purchasing-power terms.

---

```sql real_vs_nominal
SELECT
    year_month,
    date,
    commodity,
    price_type,
    median_price_ghs_per_kg AS nominal_price_ghs_per_kg,
    real_price_ghs_per_kg
FROM agri_ghana.mart_commodity_monthly_real
WHERE commodity = 'Maize'
  AND price_type = 'Wholesale'
  AND raw_unit = '100 KG'
ORDER BY date
```

```sql latest_real_prices
SELECT
    commodity,
    price_type,
    year_month,
    ROUND(median_price_ghs_per_kg, 2) AS nominal_price_ghs_per_kg,
    ROUND(real_price_ghs_per_kg, 2) AS real_price_ghs_per_kg,
    cpi_index,
    ROUND(((median_price_ghs_per_kg - real_price_ghs_per_kg) / NULLIF(real_price_ghs_per_kg, 0)) * 100, 1) AS inflation_premium_pct
FROM agri_ghana.mart_commodity_monthly_real
WHERE date = (SELECT MAX(date) FROM agri_ghana.mart_commodity_monthly_real)
  AND real_price_ghs_per_kg IS NOT NULL
ORDER BY commodity, price_type
```

```sql cpi_series
SELECT
    year,
    cpi_index,
    base_year
FROM agri_ghana.dim_cpi_ghana
ORDER BY year
```

<Tabs>
  <Tab label="Nominal Prices">

### Maize Wholesale — Nominal GHS/KG (Current Cedis)

Nominal prices show the actual market-quoted value in Ghanaian Cedis at the time of survey. These include both real supply/demand changes **and** monetary inflation effects.

<LineChart
  data={real_vs_nominal}
  x=date
  y=nominal_price_ghs_per_kg
  yFmt="#,##0.00"
  title="Maize Wholesale — Nominal Price (GHS/KG)"
  subtitle="Raw survey prices in current Ghanaian Cedis — includes inflation component"
  xAxisTitle="Date"
  yAxisTitle="GHS per KG"
/>

  </Tab>

  <Tab label="Real (CPI-Adjusted) Prices">

### Maize Wholesale — Real GHS/KG (2015 Constant Cedis)

After deflating by the Ghana CPI (base year 2015 = 100), real prices show the **purchasing-power-adjusted** food cost trajectory — isolating genuine supply/demand dynamics from monetary expansion.

<LineChart
  data={real_vs_nominal}
  x=date
  y=real_price_ghs_per_kg
  yFmt="#,##0.00"
  title="Maize Wholesale — Real Price (2015 GHS/KG)"
  subtitle="CPI-deflated prices in constant 2015 Ghana Cedis — reflects true purchasing power dynamics"
  xAxisTitle="Date"
  yAxisTitle="Real GHS per KG (2015 base)"
/>

  </Tab>

  <Tab label="Nominal vs Real Overlay">

### Nominal vs Real Price Comparison — Maize Wholesale

<LineChart
  data={real_vs_nominal}
  x=date
  y={["nominal_price_ghs_per_kg", "real_price_ghs_per_kg"]}
  yFmt="#,##0.00"
  title="Maize — Nominal vs Real Price (GHS/KG)"
  subtitle="Gap between lines represents the cumulative inflation premium embedded in nominal prices"
  labels=true
  xAxisTitle="Date"
  yAxisTitle="GHS per KG"
/>

The divergence between the two series represents the **inflation premium** — the portion of nominal price growth attributable purely to monetary depreciation rather than changes in the physical supply/demand balance.

  </Tab>

  <Tab label="Ghana CPI History">

### Ghana Consumer Price Index (2015 = 100)

<LineChart
  data={cpi_series}
  x=year
  y=cpi_index
  yFmt="#,##0.0"
  title="Ghana CPI Index (Base Year 2015 = 100)"
  subtitle="Annual average CPI estimates — Source: World Bank / Ghana Statistical Service"
  xAxisTitle="Year"
  yAxisTitle="CPI Index (2015 = 100)"
/>

  </Tab>
</Tabs>

---

## Latest Real Prices by Commodity

Prices deflated to **2015 Ghana Cedis** (base CPI = 100). The *Inflation Premium %* column shows how much of the current nominal price is attributable to cumulative monetary inflation since 2015.

<DataTable data={latest_real_prices} search=true>
  <Column id="commodity" title="Commodity" />
  <Column id="price_type" title="Price Type" />
  <Column id="year_month" title="Period" />
  <Column id="nominal_price_ghs_per_kg" title="Nominal GHS/KG" fmt="#,##0.00" />
  <Column id="real_price_ghs_per_kg" title="Real GHS/KG (2015)" fmt="#,##0.00" />
  <Column id="cpi_index" title="CPI Index" fmt="#,##0.0" />
  <Column id="inflation_premium_pct" title="Inflation Premium %" fmt="0.0" />
</DataTable>

---

> **CPI Methodology Note**: The CPI index used here is `dim_cpi_ghana` — annual average estimates anchored to 2015 = 100, based on World Bank / Ghana Statistical Service published series. For the most current official CPI data, refer to the [Ghana Statistical Service](https://statsghana.gov.gh/). Monthly interpolation is not applied; all deflation uses the annual average CPI for the survey year.
