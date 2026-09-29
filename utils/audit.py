"""
Database Audit Script
======================
Performs a comprehensive validation of all analytical layers in the
MarketPulse Ghana DuckDB warehouse. Checks are organised by concern:
GBVI key indicators, regional inflation, seasonality, volatility ranking,
Prophet MAPE scores, forecast data availability, GBVI formula calibration,
market spread distributions, commodity KPI accuracy, and data date range.

Run this script after any pipeline execution to verify that outputs are
within expected ranges and that display-layer queries return correct values.
"""

import duckdb

con = duckdb.connect("agri_ghana.duckdb")
SEP = "\n" + "=" * 60 + "\n"


# -------------------------------------------------------------------
# 1. GBVI Key Indicators
# Verify raw database values against what the index.md dashboard
# query computes (avg_mom_pct / 100.0 fed to Evidence pct1 formatter).
# pct1 multiplies by 100 before rendering, so net display = raw value.
# -------------------------------------------------------------------
print(SEP + "1. GBVI KEY INDICATORS — raw database values")
print(con.execute("""
    SELECT month_start, gbvi_score, risk_band,
           avg_mom_pct, avg_abs_mom_pct
    FROM fact_gbvi_index
    ORDER BY month_start DESC
    LIMIT 2
""").fetchdf().to_string(index=False))
print("""
index.md computes avg_mom_pct / 100.0 then applies fmt='pct1'.
Evidence pct1 multiplies by 100 before rendering, so the net
display value equals the original raw percentage. This is correct.
""")


# -------------------------------------------------------------------
# 2. Regional Inflation
# Confirms the raw values produced by the regional_inflation query.
# The BarChart uses no fmt prop, so values are rendered as plain numbers.
# Retail price_type filter is required to avoid wholesale dilution.
# -------------------------------------------------------------------
print(SEP + "2. REGIONAL INFLATION — retail-only values (last 18 months)")
print(con.execute("""
    SELECT region, ROUND(AVG(mom_inflation_pct), 2) AS avg_mom_pct
    FROM fact_monthly_prices
    WHERE month_start >= CAST('2022-07-01' AS DATE)
      AND price_type = 'retail'
      AND mom_inflation_pct IS NOT NULL
      AND mom_inflation_pct BETWEEN -100 AND 500
    GROUP BY region
    ORDER BY avg_mom_pct DESC
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 3. Seasonality — retail only vs retail + wholesale (mixed)
# Quantifies the distortion introduced by including wholesale prices
# in the seasonality calculation. The difference column shows how
# much the mixed result understates the retail consumer signal.
# -------------------------------------------------------------------
print(SEP + "3. SEASONALITY — retail-only vs mixed (retail + wholesale)")
mixed = con.execute("""
    SELECT EXTRACT(month FROM month_start)::INTEGER AS m,
           ROUND(AVG(mom_inflation_pct), 2) AS mixed_avg
    FROM fact_monthly_prices
    WHERE commodity_name IN (
        'maize', 'rice (local)', 'cassava', 'tomatoes (local)', 'plantains (apentu)'
    )
      AND mom_inflation_pct IS NOT NULL
      AND mom_inflation_pct BETWEEN -100 AND 500
    GROUP BY m ORDER BY m
""").fetchdf()
retail = con.execute("""
    SELECT EXTRACT(month FROM month_start)::INTEGER AS m,
           ROUND(AVG(mom_inflation_pct), 2) AS retail_avg
    FROM fact_monthly_prices
    WHERE commodity_name IN (
        'maize', 'rice (local)', 'cassava', 'tomatoes (local)', 'plantains (apentu)'
    )
      AND price_type = 'retail'
      AND mom_inflation_pct IS NOT NULL
      AND mom_inflation_pct BETWEEN -100 AND 500
    GROUP BY m ORDER BY m
""").fetchdf()
merged = mixed.merge(retail, on="m")
merged["difference_pp"] = (merged["retail_avg"] - merged["mixed_avg"]).round(2)
print(merged.to_string(index=False))
print("\nApril retail vs mixed difference illustrates the magnitude of distortion.")


# -------------------------------------------------------------------
# 4. Volatility Ranking
# Confirms top-8 most volatile commodities when restricted to the
# staple basket and retail price type. Non-staples (meat, eggs, fish)
# are excluded to ensure the chart is relevant to food security context.
# -------------------------------------------------------------------
print(SEP + "4. VOLATILITY RANKING — staple basket, retail only")
print(con.execute("""
    SELECT commodity_name,
           ROUND(STDDEV_POP(avg_price_per_kg_ghs), 2) AS price_stddev,
           ROUND(AVG(avg_price_per_kg_ghs), 2) AS avg_price_ghs
    FROM fact_monthly_prices
    WHERE avg_price_per_kg_ghs IS NOT NULL
      AND price_type = 'retail'
      AND commodity_name IN (
          'maize', 'maize (yellow)', 'rice (local)', 'rice (imported)',
          'cassava', 'plantains (apem)', 'plantains (apentu)',
          'tomatoes (local)', 'tomatoes (navrongo)', 'sorghum', 'millet', 'yam'
      )
    GROUP BY commodity_name
    ORDER BY price_stddev DESC
    LIMIT 8
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 5. Prophet MAPE Scores
# All mape_score values should reflect genuine cross-validation results
# expressed as whole-number percentages (e.g. 12.4 = 12.4% error).
# A value of exactly 1.0 across all commodities indicates a scale error
# where the proportion was not converted to percentage correctly.
# -------------------------------------------------------------------
print(SEP + "5. PROPHET MAPE SCORES — stored values vs baseline")
print(con.execute("""
    SELECT commodity_name, mape_score, baseline_mape_score,
           ROUND(baseline_mape_score / NULLIF(mape_score, 0), 1) AS skill_ratio
    FROM fact_price_forecasts
    GROUP BY commodity_name, mape_score, baseline_mape_score
    ORDER BY commodity_name
""").fetchdf().to_string(index=False))
print("""
Skill ratio = baseline_mape / model_mape.
A ratio above 1 confirms the model improves on the naive baseline.
Academic food price forecasting benchmarks typically achieve a ratio
of 1.2 to 2.0. A ratio of 25 or above suggests a data quality issue.
""")


# -------------------------------------------------------------------
# 6. Forecast Data Availability
# Confirms the number of forecast records per commodity and their
# date range. Only 3 records per commodity (one per forecast month)
# is expected given FORECAST_MONTHS = 3 in the pipeline configuration.
# -------------------------------------------------------------------
print(SEP + "6. FORECAST DATA AVAILABILITY — records per commodity")
print(con.execute("""
    SELECT commodity_name, record_date,
           ROUND(predicted_price_ghs, 2) AS predicted,
           ROUND(lower_bound_ghs, 2)     AS lower,
           ROUND(upper_bound_ghs, 2)     AS upper,
           is_forecast
    FROM fact_price_forecasts
    WHERE commodity_name = 'maize'
    ORDER BY record_date
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 7. GBVI Formula Calibration
# Checks the distribution of raw inputs (avg_abs_mom_pct, stddev_mom_pct)
# against the normalisation thresholds (15.0 and 12.0) used in the formula.
# The thresholds should sit near the 75th percentile of stable-year values
# so the index uses its full range without saturating prematurely.
# -------------------------------------------------------------------
print(SEP + "7. GBVI FORMULA CALIBRATION — input distribution vs thresholds")
print(con.execute("""
    SELECT
        ROUND(MIN(avg_abs_mom_pct), 2)    AS abs_mom_min,
        ROUND(MAX(avg_abs_mom_pct), 2)    AS abs_mom_max,
        ROUND(AVG(avg_abs_mom_pct), 2)    AS abs_mom_avg,
        ROUND(MIN(stddev_mom_pct), 2)     AS stddev_min,
        ROUND(MAX(stddev_mom_pct), 2)     AS stddev_max,
        ROUND(AVG(stddev_mom_pct), 2)     AS stddev_avg
    FROM fact_gbvi_index
""").fetchdf().to_string(index=False))
print(con.execute("""
    SELECT month_start, gbvi_score, avg_abs_mom_pct, stddev_mom_pct
    FROM fact_gbvi_index
    ORDER BY gbvi_score DESC
    LIMIT 10
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 8. Market Spread Distribution
# Validates the spread_margin_pct range and confirms how many rows
# fall above the KPI cap value of 600 used in spread_kpis query.
# -------------------------------------------------------------------
print(SEP + "8. MARKET SPREAD DISTRIBUTION — range and cap analysis")
print(con.execute("""
    SELECT
        ROUND(MIN(spread_margin_pct), 2)  AS min_pct,
        ROUND(MAX(spread_margin_pct), 2)  AS max_pct,
        ROUND(AVG(spread_margin_pct), 2)  AS avg_pct,
        COUNT(*)                          AS total_rows,
        COUNT(CASE WHEN spread_margin_pct > 600 THEN 1 END) AS rows_above_600
    FROM fact_market_spreads
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 9. Commodities Page KPIs — retail vs mixed comparison
# Demonstrates the improvement in KPI accuracy when wholesale records
# are excluded. The retail average is the consumer-relevant figure.
# -------------------------------------------------------------------
print(SEP + "9. COMMODITIES PAGE KPIs — retail only vs mixed for maize")
print("Mixed (retail + wholesale):")
print(con.execute("""
    SELECT
        ROUND(AVG(avg_price_per_kg_ghs), 2)  AS national_avg_price,
        ROUND(MAX(avg_price_per_kg_ghs), 2)  AS all_time_high,
        ROUND(MIN(avg_price_per_kg_ghs), 2)  AS all_time_low,
        ROUND(AVG(CASE WHEN mom_inflation_pct BETWEEN -100 AND 500
                       THEN mom_inflation_pct END), 2) AS avg_mom_inflation
    FROM fact_monthly_prices
    WHERE commodity_name = 'maize'
      AND avg_price_per_kg_ghs IS NOT NULL
""").fetchdf().to_string(index=False))
print("Retail only:")
print(con.execute("""
    SELECT
        ROUND(AVG(avg_price_per_kg_ghs), 2)  AS national_avg_price,
        ROUND(MAX(avg_price_per_kg_ghs), 2)  AS all_time_high,
        ROUND(MIN(avg_price_per_kg_ghs), 2)  AS all_time_low,
        ROUND(AVG(CASE WHEN mom_inflation_pct BETWEEN -100 AND 500
                       THEN mom_inflation_pct END), 2) AS avg_mom_inflation
    FROM fact_monthly_prices
    WHERE commodity_name = 'maize'
      AND price_type = 'retail'
      AND avg_price_per_kg_ghs IS NOT NULL
""").fetchdf().to_string(index=False))


# -------------------------------------------------------------------
# 10. Data Date Range
# Confirms the actual coverage period in fact_monthly_prices against
# the dataset metadata published on the WFP HDX platform.
# -------------------------------------------------------------------
print(SEP + "10. DATA DATE RANGE — actual coverage in fact_monthly_prices")
print(con.execute("""
    SELECT MIN(month_start) AS earliest,
           MAX(month_start) AS latest,
           COUNT(DISTINCT month_start) AS distinct_months
    FROM fact_monthly_prices
""").fetchdf().to_string(index=False))

con.close()
print(SEP + "AUDIT COMPLETE")
