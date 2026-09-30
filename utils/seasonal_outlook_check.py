"""
Compute seasonal outlook statistics from retail price data.
Used to validate what the new forecasts page SQL will return.
"""
import duckdb
import pandas as pd

con = duckdb.connect("agri_ghana.duckdb")

# Seasonal MoM stats by commodity and calendar month
print("=== Seasonal MoM stats (retail, last 5 years of data = 2018-2023) ===")
df = con.execute("""
    WITH monthly AS (
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS month_start,
            commodity_name,
            AVG(price_per_kg_ghs) AS avg_price
        FROM stg_wfp_prices
        WHERE price_type = 'retail'
          AND price_per_kg_ghs BETWEEN 0.05 AND 500.0
          AND commodity_name IN (
              'maize','cassava','rice (local)','rice (imported)',
              'plantains (apentu)','tomatoes (local)'
          )
          AND record_date >= '2018-01-01'
        GROUP BY 1, 2
        HAVING COUNT(*) >= 3
    ),
    with_mom AS (
        SELECT
            month_start,
            commodity_name,
            avg_price,
            EXTRACT(month FROM month_start)::INTEGER AS month_num,
            ROUND(
                (avg_price - LAG(avg_price) OVER (PARTITION BY commodity_name ORDER BY month_start))
                / NULLIF(LAG(avg_price) OVER (PARTITION BY commodity_name ORDER BY month_start), 0)
                * 100, 2
            ) AS mom_pct
        FROM monthly
    )
    SELECT
        commodity_name,
        month_num,
        COUNT(*)                             AS years_observed,
        ROUND(AVG(mom_pct), 1)               AS avg_mom_pct,
        ROUND(MIN(mom_pct), 1)               AS min_mom_pct,
        ROUND(MAX(mom_pct), 1)               AS max_mom_pct,
        ROUND(STDDEV(mom_pct), 1)            AS stddev_mom_pct,
        SUM(CASE WHEN mom_pct > 1  THEN 1 ELSE 0 END) AS count_up,
        SUM(CASE WHEN mom_pct < -1 THEN 1 ELSE 0 END) AS count_down,
        SUM(CASE WHEN mom_pct BETWEEN -1 AND 1 THEN 1 ELSE 0 END) AS count_flat
    FROM with_mom
    WHERE mom_pct IS NOT NULL
      AND mom_pct BETWEEN -60 AND 200
    GROUP BY 1, 2
    ORDER BY 1, 2
""").fetchdf()
print(df.to_string())

print()
print("=== Trailing 3-month trend per commodity (most recent 3 months) ===")
trend = con.execute("""
    WITH monthly AS (
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS month_start,
            commodity_name,
            ROUND(AVG(price_per_kg_ghs), 2) AS avg_price
        FROM stg_wfp_prices
        WHERE price_type = 'retail'
          AND price_per_kg_ghs BETWEEN 0.05 AND 500.0
          AND commodity_name IN (
              'maize','cassava','rice (local)','rice (imported)',
              'plantains (apentu)','tomatoes (local)'
          )
        GROUP BY 1, 2
        HAVING COUNT(*) >= 3
    ),
    ranked AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY commodity_name ORDER BY month_start DESC) AS rn
        FROM monthly
    ),
    latest3 AS (
        SELECT commodity_name, month_start, avg_price
        FROM ranked WHERE rn <= 3
    ),
    bounds AS (
        SELECT
            commodity_name,
            MAX(CASE WHEN rn_asc = 1 THEN avg_price END) AS price_3mo_ago,
            MAX(CASE WHEN rn_asc = 3 THEN avg_price END) AS price_latest
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY commodity_name ORDER BY month_start ASC) AS rn_asc
            FROM latest3
        ) t
        GROUP BY commodity_name
    )
    SELECT
        commodity_name,
        price_3mo_ago,
        price_latest,
        ROUND((price_latest - price_3mo_ago) / NULLIF(price_3mo_ago, 0) * 100, 1) AS trailing_3m_pct
    FROM bounds
    ORDER BY commodity_name
""").fetchdf()
print(trend.to_string())

con.close()
