"""
Seasonal Outlook View Builder
==============================
Constructs fact_seasonal_outlook — a pre-aggregated table of historical
month-over-month price statistics for each core staple commodity, grouped
by calendar month.

This replaces the Prophet forecasting model as the forward-looking component
of the MarketPulse Ghana dashboard. Rather than generating point forecasts,
it answers the question: given the current calendar month, what has this
commodity's price historically done in the next one to three months?

Statistics are computed over a rolling 5-year window (2018-2023) of retail
prices only, providing a recent and relevant seasonal baseline that reflects
post-2017 price dynamics including the cedi depreciation trend.

Columns produced:
    commodity_name      Commodity identifier
    month_num           Calendar month number (1=Jan, 12=Dec)
    month_name          Abbreviated month name
    years_observed      Number of years contributing to the average
    avg_mom_pct         Average month-over-month price change (%)
    min_mom_pct         Minimum observed MoM change in this month (%)
    max_mom_pct         Maximum observed MoM change in this month (%)
    stddev_mom_pct      Standard deviation of MoM changes (%)
    count_up            Number of years prices rose (MoM > +1%)
    count_down          Number of years prices fell (MoM < -1%)
    count_flat          Number of years prices were flat (MoM within ±1%)
    pct_years_up        Percentage of years prices rose
    pct_years_down      Percentage of years prices fell
    direction_signal    Dominant direction: 'Typically rises', 'Typically falls',
                        'Mixed' based on majority of observed years
"""

import duckdb
import logging
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.pipeline_logger import PipelineLogger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DB_PATH = "agri_ghana.duckdb"

OUTLOOK_STAPLES = (
    "maize", "cassava", "rice (local)", "rice (imported)",
    "plantains (apentu)", "tomatoes (local)"
)

# Rolling window: use 2018 onwards to reflect post-cedi-depreciation price dynamics
WINDOW_START = "2018-01-01"


def main():
    logger = PipelineLogger(DB_PATH)
    t0 = time.perf_counter()
    con = duckdb.connect(DB_PATH)
    logging.info(f"Database connection established: {DB_PATH}")

    staples_sql = str(OUTLOOK_STAPLES)

    logging.info("Building fact_seasonal_outlook...")
    con.execute(f"""
    CREATE OR REPLACE TABLE fact_seasonal_outlook AS
    WITH monthly AS (
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS month_start,
            commodity_name,
            AVG(price_per_kg_ghs) AS avg_price
        FROM stg_wfp_prices
        WHERE price_type = 'retail'
          AND price_per_kg_ghs BETWEEN 0.05 AND 500.0
          AND commodity_name IN {staples_sql}
          AND record_date >= '{WINDOW_START}'
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
    ),
    aggregated AS (
        SELECT
            commodity_name,
            month_num,
            CASE month_num
                WHEN 1  THEN 'Jan' WHEN 2  THEN 'Feb' WHEN 3  THEN 'Mar'
                WHEN 4  THEN 'Apr' WHEN 5  THEN 'May' WHEN 6  THEN 'Jun'
                WHEN 7  THEN 'Jul' WHEN 8  THEN 'Aug' WHEN 9  THEN 'Sep'
                WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dec'
            END AS month_name,
            COUNT(*)                                                    AS years_observed,
            ROUND(AVG(mom_pct), 1)                                      AS avg_mom_pct,
            ROUND(MIN(mom_pct), 1)                                      AS min_mom_pct,
            ROUND(MAX(mom_pct), 1)                                      AS max_mom_pct,
            ROUND(STDDEV(mom_pct), 1)                                   AS stddev_mom_pct,
            SUM(CASE WHEN mom_pct >  1 THEN 1 ELSE 0 END)              AS count_up,
            SUM(CASE WHEN mom_pct < -1 THEN 1 ELSE 0 END)              AS count_down,
            SUM(CASE WHEN mom_pct BETWEEN -1 AND 1 THEN 1 ELSE 0 END)  AS count_flat
        FROM with_mom
        WHERE mom_pct IS NOT NULL
          AND mom_pct BETWEEN -60 AND 200
        GROUP BY 1, 2, 3
    )
    SELECT
        commodity_name,
        month_num,
        month_name,
        years_observed,
        avg_mom_pct,
        min_mom_pct,
        max_mom_pct,
        stddev_mom_pct,
        count_up,
        count_down,
        count_flat,
        ROUND(count_up   * 100.0 / NULLIF(years_observed, 0), 0) AS pct_years_up,
        ROUND(count_down * 100.0 / NULLIF(years_observed, 0), 0) AS pct_years_down,
        CASE
            WHEN count_up   > count_down AND count_up   > count_flat THEN 'Typically rises'
            WHEN count_down > count_up   AND count_down > count_flat THEN 'Typically falls'
            ELSE 'Mixed'
        END AS direction_signal
    FROM aggregated
    ORDER BY commodity_name, month_num
    """)

    n = con.execute("SELECT COUNT(*) FROM fact_seasonal_outlook").fetchone()[0]
    logging.info(f"fact_seasonal_outlook populated with {n} rows.")

    # Spot-check
    sample = con.execute("""
        SELECT commodity_name, month_name, avg_mom_pct, direction_signal, years_observed
        FROM fact_seasonal_outlook
        WHERE commodity_name IN ('maize', 'tomatoes (local)')
        ORDER BY commodity_name, month_num
    """).fetchdf()
    print(sample.to_string())

    con.close()
    logging.info("Done.")
    logger.success("5_build_seasonal_outlook", rows_affected=n, duration_seconds=time.perf_counter() - t0)


if __name__ == "__main__":
    main()
