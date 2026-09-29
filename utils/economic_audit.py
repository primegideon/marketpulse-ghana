"""
Economic Context and Model Accuracy Audit
==========================================
Examines the historical price trajectory of Ghana's core staple commodities
against known macroeconomic shock periods and evaluates whether the Prophet
model MAPE scores stored in the database are plausible given observed volatility.

Shock periods documented in this dataset (2006-2023):
  March-April 2020  : COVID-19 border closures and market disruptions.
                      GBVI reached 100.0 in February, March, and April 2020.
  June-July 2021    : Global shipping crisis and fuel cost increases.
                      GBVI reached 100.0 in June and July 2021.
  February-March 2022: Russia-Ukraine war. Ghana imports approximately 40%
                      of its wheat requirements. Global grain and fuel prices
                      spiked. GBVI reached 100.0 in March 2022.
  July 2022 onwards : Ghana cedi depreciation crisis. The GHS lost approximately
                      55% of its value against the USD between 2021 and 2023,
                      driving sustained food price inflation independent of
                      seasonal supply-side factors. Ghana entered an IMF
                      extended credit facility programme in May 2023.

Price level changes (retail, 2019 to 2023):
  Maize:            GHS 1.63/kg -> GHS 6.43/kg  (+294%)
  Rice (local):     GHS 4.92/kg -> GHS 12.68/kg (+158%)
  Cassava:          GHS 2.40/kg -> GHS 5.92/kg  (+147%)
  Plantains:        GHS 1.27/kg -> GHS 5.13/kg  (+304%)
  Tomatoes (local): GHS 3.33/kg -> GHS 8.63/kg  (+159%)

These structural price level increases mean that a forecasting model trained
on 2019-2023 data must account for both seasonal variation and a strong
non-stationary trend. Prophet's multiplicative seasonality mode and explicit
changepoint configuration are intended to address this requirement.
"""

import duckdb

con = duckdb.connect("agri_ghana.duckdb")
SEP = "\n" + "=" * 60 + "\n"


# -------------------------------------------------------------------
# 1. Maize price trajectory (retail, national average)
# -------------------------------------------------------------------
print(SEP + "1. MAIZE RETAIL PRICE TRAJECTORY — national monthly average")
print(con.execute("""
    SELECT month_start,
           ROUND(AVG(avg_price_per_kg_ghs), 2) AS nat_avg_ghs,
           ROUND(AVG(mom_inflation_pct), 2)     AS mom_pct
    FROM fact_monthly_prices
    WHERE commodity_name = 'maize'
      AND price_type = 'retail'
      AND mom_inflation_pct IS NOT NULL
    GROUP BY month_start
    ORDER BY month_start
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 2. Rice (local) price trajectory (retail, national average)
# -------------------------------------------------------------------
print(SEP + "2. RICE (LOCAL) RETAIL PRICE TRAJECTORY — national monthly average")
print(con.execute("""
    SELECT month_start,
           ROUND(AVG(avg_price_per_kg_ghs), 2) AS nat_avg_ghs,
           ROUND(AVG(mom_inflation_pct), 2)     AS mom_pct
    FROM fact_monthly_prices
    WHERE commodity_name = 'rice (local)'
      AND price_type = 'retail'
      AND mom_inflation_pct IS NOT NULL
    GROUP BY month_start
    ORDER BY month_start
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 3. GBVI scores over the full period
# Identifies shock periods by GBVI score and risk band.
# -------------------------------------------------------------------
print(SEP + "3. GBVI MONTHLY SCORES — full period with shock annotation")
print(con.execute("""
    SELECT month_start, gbvi_score, risk_band,
           avg_abs_mom_pct, stddev_mom_pct, avg_mom_pct
    FROM fact_gbvi_index
    ORDER BY month_start
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 4. Extreme MoM observations
# Lists the 20 largest absolute MoM changes in the dataset to
# identify which commodity-region-period combinations produced
# extreme values that influence model training.
# -------------------------------------------------------------------
print(SEP + "4. TOP 20 EXTREME MONTH-ON-MONTH OBSERVATIONS")
print(con.execute("""
    SELECT month_start, commodity_name, region, price_type,
           ROUND(avg_price_per_kg_ghs, 2) AS price_ghs,
           ROUND(mom_inflation_pct, 2)    AS mom_pct
    FROM fact_monthly_prices
    WHERE mom_inflation_pct IS NOT NULL
    ORDER BY ABS(mom_inflation_pct) DESC
    LIMIT 20
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 5. Price level comparison by year for core staples
# Quantifies the cumulative inflation experienced since 2019.
# -------------------------------------------------------------------
print(SEP + "5. ANNUAL AVERAGE RETAIL PRICES — core staples (GHS/KG)")
print(con.execute("""
    SELECT commodity_name,
           ROUND(AVG(CASE WHEN YEAR(month_start) = 2019 THEN avg_price_per_kg_ghs END), 2) AS avg_2019,
           ROUND(AVG(CASE WHEN YEAR(month_start) = 2020 THEN avg_price_per_kg_ghs END), 2) AS avg_2020,
           ROUND(AVG(CASE WHEN YEAR(month_start) = 2021 THEN avg_price_per_kg_ghs END), 2) AS avg_2021,
           ROUND(AVG(CASE WHEN YEAR(month_start) = 2022 THEN avg_price_per_kg_ghs END), 2) AS avg_2022,
           ROUND(AVG(CASE WHEN YEAR(month_start) = 2023 THEN avg_price_per_kg_ghs END), 2) AS avg_2023
    FROM fact_monthly_prices
    WHERE commodity_name IN (
        'maize', 'rice (local)', 'cassava', 'plantains (apentu)', 'tomatoes (local)'
    )
      AND price_type = 'retail'
    GROUP BY commodity_name
    ORDER BY commodity_name
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 6. MAPE plausibility check
# Compares stored model MAPE against the naive baseline and assesses
# whether the skill ratio is consistent with academic benchmarks.
#
# Reference: Published food price forecasting studies using Prophet
# or SARIMA on WFP datasets typically achieve MAPE of 8-20% on
# monthly data and a skill ratio of 1.2-2.0 over naive baselines.
# A skill ratio above 10 should be treated as a signal of a
# computation error rather than genuine model performance.
# -------------------------------------------------------------------
print(SEP + "6. PROPHET MAPE PLAUSIBILITY — skill ratio vs academic benchmarks")
print(con.execute("""
    SELECT commodity_name,
           ROUND(mape_score, 2)              AS model_mape_pct,
           ROUND(baseline_mape_score, 2)     AS baseline_mape_pct,
           ROUND(baseline_mape_score / NULLIF(mape_score, 0), 1) AS skill_ratio
    FROM fact_price_forecasts
    GROUP BY commodity_name, mape_score, baseline_mape_score
    ORDER BY commodity_name
""").fetchdf().to_string(index=False))
print("""
Expected skill ratio for a well-calibrated food price forecasting model:
  1.2 - 2.0  : Reasonable improvement over naive baseline
  2.0 - 5.0  : Strong performance, uncommon in high-volatility settings
  Above 10   : Likely indicates a scale or computation error in MAPE storage

The baseline MAPE values (25-51%) are consistent with the observed price
volatility in the 2019-2023 training period. A model MAPE of exactly 1.0%
across all commodities is not plausible given this volatility level and
indicates the cross-validation output was not converted to percentage scale
correctly before being stored. The pipeline has been corrected; re-run
4_run_forecasting.py to update the stored MAPE values.
""")


# -------------------------------------------------------------------
# 7. Training data available per commodity
# -------------------------------------------------------------------
print(SEP + "7. TRAINING DATA AVAILABILITY — months per commodity")
print(con.execute("""
    SELECT commodity_name,
           COUNT(*) AS training_months,
           MIN(ds)  AS first_month,
           MAX(ds)  AS last_month
    FROM (
        SELECT DATE_TRUNC('month', record_date)::DATE AS ds,
               commodity_name
        FROM stg_wfp_prices
        WHERE price_type = 'retail'
          AND price_per_kg_ghs BETWEEN 0.05 AND 500
          AND commodity_name IN (
              'maize', 'cassava', 'rice (local)', 'rice (imported)',
              'plantains (apentu)', 'tomatoes (local)'
          )
        GROUP BY ds, commodity_name
        HAVING COUNT(*) >= 3
    )
    GROUP BY commodity_name
    ORDER BY training_months DESC
""").fetchdf().to_string(index=False))

con.close()
print(SEP + "ECONOMIC CONTEXT AUDIT COMPLETE")
