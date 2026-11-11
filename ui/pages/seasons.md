---
title: Agricultural Seasons
---

# Agricultural Seasons & Price Cycles

> **Ghana's food commodity prices follow predictable seasonal rhythms tied to four distinct agricultural seasons. Understanding these cycles is essential for food security planning, procurement timing, and market interventions.**
>
> - **Lean Season** (May – Jul): Pre-harvest period with low supply and peak prices
> - **Major Harvest** (Aug – Nov): Primary harvest period with peak supply and lowest prices
> - **Post-Harvest** (Dec – Jan): Storage and distribution phase with moderate, stable prices
> - **Minor Season** (Feb – Apr): Second planting season with partial harvest in southern Ghana

---

```sql seasonal_avg
SELECT
    c.agricultural_season,
    m.commodity,
    ROUND(AVG(m.median_price_ghs_per_kg), 2) AS avg_price_per_kg,
    COUNT(*) AS data_points
FROM agri_ghana.mart_commodity_monthly m
JOIN agri_ghana.dim_calendar c ON m.date = c.date
WHERE m.price_type = 'Wholesale'
  AND m.median_price_ghs_per_kg IS NOT NULL
  AND m.commodity IN ('Maize', 'Rice (imported)', 'Cassava', 'Millet', 'Sorghum')
GROUP BY c.agricultural_season, m.commodity
ORDER BY m.commodity, avg_price_per_kg DESC
```

```sql season_order
-- For ordering seasons correctly: Lean Season, Major Harvest, Post-Harvest, Minor Season
SELECT
    CASE agricultural_season
        WHEN 'Lean Season' THEN 1
        WHEN 'Major Harvest' THEN 2
        WHEN 'Post-Harvest' THEN 3
        WHEN 'Minor Season' THEN 4
    END AS season_order,
    agricultural_season,
    commodity,
    ROUND(AVG(median_price_ghs_per_kg), 2) AS avg_price_per_kg
FROM agri_ghana.mart_commodity_monthly m
JOIN agri_ghana.dim_calendar c ON m.date = c.date
WHERE m.price_type = 'Wholesale'
  AND m.median_price_ghs_per_kg IS NOT NULL
  AND m.commodity IN ('Maize', 'Rice (imported)', 'Cassava', 'Millet', 'Sorghum')
GROUP BY agricultural_season, commodity
ORDER BY season_order, commodity
```

```sql maize_by_season_year
SELECT
    c.year,
    c.agricultural_season,
    ROUND(AVG(m.median_price_ghs_per_kg), 2) AS avg_price_per_kg
FROM agri_ghana.mart_commodity_monthly m
JOIN agri_ghana.dim_calendar c ON m.date = c.date
WHERE m.commodity = 'Maize'
  AND m.price_type = 'Wholesale'
  AND m.raw_unit = '100 KG'
  AND m.median_price_ghs_per_kg IS NOT NULL
GROUP BY c.year, c.agricultural_season
ORDER BY c.year, c.agricultural_season
```

```sql lean_season_premium
SELECT
    commodity,
    MAX(CASE WHEN agricultural_season = 'Lean Season' THEN avg_price_per_kg END) AS lean_price,
    MAX(CASE WHEN agricultural_season = 'Major Harvest' THEN avg_price_per_kg END) AS harvest_price,
    ROUND(
        (MAX(CASE WHEN agricultural_season = 'Lean Season' THEN avg_price_per_kg END) -
         MAX(CASE WHEN agricultural_season = 'Major Harvest' THEN avg_price_per_kg END)) /
        NULLIF(MAX(CASE WHEN agricultural_season = 'Major Harvest' THEN avg_price_per_kg END), 0) * 100.0,
        1
    ) AS lean_premium_pct
FROM (
    SELECT
        c.agricultural_season,
        m.commodity,
        ROUND(AVG(m.median_price_ghs_per_kg), 2) AS avg_price_per_kg
    FROM agri_ghana.mart_commodity_monthly m
    JOIN agri_ghana.dim_calendar c ON m.date = c.date
    WHERE m.price_type = 'Wholesale'
      AND m.median_price_ghs_per_kg IS NOT NULL
      AND m.commodity IN ('Maize', 'Rice (imported)', 'Cassava', 'Millet', 'Sorghum')
    GROUP BY c.agricultural_season, m.commodity
)
GROUP BY commodity
ORDER BY lean_premium_pct DESC
```

## Lean Season Price Premium (Key Staples)

<BigValue
  data={lean_season_premium}
  value=lean_premium_pct
  title="Maize Lean Season Premium (%)"
  fmt="0.0"
  row=0
/>

<BigValue
  data={lean_season_premium}
  value=lean_price
  title="Maize Lean Season Price (GHS/KG)"
  fmt="#,##0.00"
  row=0
/>

<BigValue
  data={lean_season_premium}
  value=harvest_price
  title="Maize Harvest Price (GHS/KG)"
  fmt="#,##0.00"
  row=0
/>

> **Lean Season Premium**: The percentage by which Lean Season prices exceed Major Harvest prices. Higher premiums indicate greater food security risk and opportunity for strategic grain reserves.

---

<Tabs>
  <Tab label="Seasonal Price Averages">

### Average Price by Agricultural Season & Commodity

<BarChart
  data={season_order}
  x=agricultural_season
  y=avg_price_per_kg
  series=commodity
  yFmt="#,##0.00"
  title="Average Wholesale Price by Season (GHS / KG)"
  subtitle="Grouped bar chart showing how each agricultural season affects commodity prices — Lean Season consistently yields the highest prices"
  xLabelRotation=15
/>

  </Tab>

  <Tab label="Maize Multi-Year Trends">

### Maize Wholesale Price: Seasonal Pattern by Year

<LineChart
  data={maize_by_season_year}
  x=year
  y=avg_price_per_kg
  series=agricultural_season
  yFmt="#,##0.00"
  title="Maize Annual Seasonal Price Trends (GHS / KG)"
  subtitle="Tracking how seasonal price differentials have evolved over the years — the growing gap between Lean and Harvest prices signals increasing food system volatility"
/>

  </Tab>

  <Tab label="Lean Season Premium Table">

### Lean-to-Harvest Price Premium by Commodity

<DataTable data={lean_season_premium}>
  <Column id="commodity" title="Commodity" />
  <Column id="lean_price" title="Lean Season Price (GHS/KG)" fmt="#,##0.00" />
  <Column id="harvest_price" title="Harvest Price (GHS/KG)" fmt="#,##0.00" />
  <Column id="lean_premium_pct" title="Lean Premium (%)" fmt="0.0" />
</DataTable>

> **Interpretation**: The lean premium (%) measures the additional cost consumers face during the pre-harvest period compared to harvest time. High premiums indicate strong seasonality that may cause food insecurity for vulnerable households.

  </Tab>

  <Tab label="All Season Data">

### Full Seasonal Commodity Data

<DataTable data={seasonal_avg} search=true>
  <Column id="agricultural_season" title="Season" />
  <Column id="commodity" title="Commodity" />
  <Column id="avg_price_per_kg" title="Avg Price (GHS/KG)" fmt="#,##0.00" />
  <Column id="data_points" title="Observations" fmt="#,##0" />
</DataTable>

  </Tab>
</Tabs>
