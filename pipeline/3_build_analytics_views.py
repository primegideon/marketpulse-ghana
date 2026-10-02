"""
Analytics Views Builder Module
================================
Constructs three analytical views in DuckDB that serve as the primary data
layer for the MarketPulse Ghana dashboard.

Views produced:
  fact_monthly_prices   Monthly average retail and wholesale prices per
                        commodity and region, with 3-month and 6-month rolling
                        averages and month-over-month inflation percentage.

  fact_market_spreads   Urban-to-farm-gate price spread by commodity, computed
                        as the difference between prices in urban consumer
                        regions (Greater Accra, Ashanti) and producing regions
                        (Brong Ahafo, Northern, Upper East, Upper West, Volta).
                        Expressed as both an absolute GHS gap and a percentage
                        markup over the producing-region price.

  fact_gbvi_index       Ghana Basket Volatility Index (GBVI): a composite 0-100
                        score measuring month-over-month price instability across
                        the core staple basket. Computed from the average absolute
                        MoM percentage change (60% weight) and the cross-commodity
                        standard deviation of MoM changes (40% weight).

GBVI calibration thresholds:
  The normalisation denominators (15.0 for avg_abs_mom_pct, 12.0 for stddev)
  were calibrated against the observed distribution in the WFP Ghana dataset
  (2006-2023). The 15.0 threshold corresponds to the 75th percentile of
  avg_abs_mom_pct in stable years, ensuring the index uses the full 0-100
  range under normal market conditions and saturates only during genuine crisis
  periods such as COVID-19 (2020) or the Russia-Ukraine commodity shock (2022).

  Risk band boundaries (Stable 0-30 / Moderate 31-70 / High Alert 71-100)
  were set at the 33rd and 66th percentiles of the GBVI score distribution
  across the full 2006-2023 history, dividing the observed range into three
  roughly equal-frequency bands.
"""

import duckdb
import pandas as pd
import logging
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.pipeline_logger import PipelineLogger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Core staples used in fact_monthly_prices and fact_market_spreads (retail only).
# Note: rice (paddy) is excluded here because paddy is a pre-milling farm-gate
# commodity with no retail price series; it is structurally incomparable to the
# consumer-level staples in this list.
CORE_STAPLES = ("maize", "maize (yellow)", "rice (local)", "rice (imported)",
                "cassava", "plantains (apem)", "plantains (apentu)", "tomatoes (local)", "tomatoes (navrongo)")

# Geographic classifications for supply chain spread calculation
PRODUCING_REGIONS = ("brong ahafo", "northern", "upper east", "upper west", "volta")
URBAN_REGIONS     = ("greater accra", "ashanti")

def main():
    db_path = "agri_ghana.duckdb"
    logger = PipelineLogger(db_path)
    t0 = time.perf_counter()
    con = duckdb.connect(db_path)
    logging.info(f"Database connection established: {db_path}")

    # ----------------------------------------------------------
    # VIEW 1: fact_monthly_prices
    # ----------------------------------------------------------
    logging.info("Constructing view: 'fact_monthly_prices'...")
    con.execute("""
    CREATE OR REPLACE VIEW fact_monthly_prices AS
    WITH monthly AS (
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS month_start,
            commodity_name,
            region,
            price_type,
            ROUND(AVG(price_per_kg_ghs), 4) AS avg_price_per_kg_ghs,
            COUNT(*) AS observation_count
        FROM stg_wfp_prices
        WHERE price_per_kg_ghs BETWEEN 0.05 AND 500.0
        GROUP BY DATE_TRUNC('month', record_date)::DATE, commodity_name, region, price_type
        HAVING COUNT(*) >= 2   -- Exclude sparse data points to prevent single-observation skew
    )
    SELECT
        month_start,
        commodity_name,
        region,
        avg_price_per_kg_ghs,
        observation_count,
        ROUND(AVG(avg_price_per_kg_ghs) OVER (
            PARTITION BY commodity_name, region, price_type
            ORDER BY month_start
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 4) AS rolling_3m_avg,
        ROUND(AVG(avg_price_per_kg_ghs) OVER (
            PARTITION BY commodity_name, region, price_type
            ORDER BY month_start
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ), 4) AS rolling_6m_avg,
        ROUND(
            (avg_price_per_kg_ghs
                - LAG(avg_price_per_kg_ghs) OVER (PARTITION BY commodity_name, region, price_type ORDER BY month_start)
            )
            / NULLIF(LAG(avg_price_per_kg_ghs) OVER (PARTITION BY commodity_name, region, price_type ORDER BY month_start), 0)
            * 100,
        2) AS mom_inflation_pct,
        price_type
    FROM monthly;
    """)
    n = con.execute("SELECT COUNT(*) FROM fact_monthly_prices").fetchone()[0]
    logging.info(f"Deployed 'fact_monthly_prices' with {n:,} operational rows.")

    # ----------------------------------------------------------
    # VIEW 2: fact_market_spreads
    # ----------------------------------------------------------
    logging.info("Constructing view: 'fact_market_spreads'...")
    con.execute(f"""
    CREATE OR REPLACE VIEW fact_market_spreads AS
    WITH monthly AS (
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS month_start,
            commodity_name,
            region,
            price_type,
            ROUND(AVG(price_per_kg_ghs), 4) AS avg_price
        FROM stg_wfp_prices
        WHERE price_per_kg_ghs BETWEEN 0.05 AND 500.0
        GROUP BY DATE_TRUNC('month', record_date)::DATE, commodity_name, region, price_type
        HAVING COUNT(*) >= 2
    ),
    urban AS (
        SELECT month_start, commodity_name, price_type, ROUND(AVG(avg_price), 4) AS urban_avg_price
        FROM monthly
        WHERE region IN {URBAN_REGIONS}
        GROUP BY month_start, commodity_name, price_type
    ),
    producing AS (
        SELECT month_start, commodity_name, price_type, ROUND(AVG(avg_price), 4) AS producing_avg_price
        FROM monthly
        WHERE region IN {PRODUCING_REGIONS}
        GROUP BY month_start, commodity_name, price_type
    )
    SELECT
        u.month_start,
        u.commodity_name,
        ROUND(u.urban_avg_price, 2)                                              AS urban_avg_price,
        ROUND(p.producing_avg_price, 2)                                          AS producing_avg_price,
        ROUND(u.urban_avg_price - p.producing_avg_price, 2)                      AS absolute_spread_ghs,
        ROUND(
            (u.urban_avg_price - p.producing_avg_price)
            / NULLIF(p.producing_avg_price, 0) * 100,
        2) AS spread_margin_pct,
        u.price_type
    FROM urban u
    JOIN producing p
        ON u.month_start = p.month_start
       AND u.commodity_name = p.commodity_name
       AND u.price_type = p.price_type
    ORDER BY u.month_start, u.commodity_name;
    """)
    n = con.execute("SELECT COUNT(*) FROM fact_market_spreads").fetchone()[0]
    logging.info(f"Deployed 'fact_market_spreads' with {n:,} operational rows.")

    # ----------------------------------------------------------
    # VIEW 3: fact_gbvi_index
    # ----------------------------------------------------------
    logging.info("Constructing view: 'fact_gbvi_index'...")
    # rice (paddy) is included in the GBVI basket intentionally: paddy price
    # movements capture Northern farm-gate supply shocks that feed through to
    # milled rice retail prices with a 1-2 month lag, providing an early
    # warning signal. It is excluded from CORE_STAPLES (retail-only list) but
    # retained here for volatility measurement purposes.
    staples_tuple = ("maize", "maize (yellow)", "rice (local)", "rice (imported)",
                     "rice (paddy)", "cassava", "plantains (apem)", "plantains (apentu)",
                     "tomatoes (local)", "tomatoes (navrongo)")
    con.execute(f"""
    CREATE OR REPLACE VIEW fact_gbvi_index AS
    WITH national_monthly AS (
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS month_start,
            commodity_name,
            ROUND(AVG(price_per_kg_ghs), 4) AS nat_avg_price
        FROM stg_wfp_prices
        WHERE price_per_kg_ghs BETWEEN 0.05 AND 500.0
          AND commodity_name IN {staples_tuple}
          AND price_type = 'retail'
        GROUP BY DATE_TRUNC('month', record_date)::DATE, commodity_name
        HAVING COUNT(*) >= 2
    ),
    with_mom AS (
        SELECT
            month_start,
            commodity_name,
            nat_avg_price,
            ROUND(
                (nat_avg_price - LAG(nat_avg_price) OVER (PARTITION BY commodity_name ORDER BY month_start))
                / NULLIF(LAG(nat_avg_price) OVER (PARTITION BY commodity_name ORDER BY month_start), 0)
                * 100,
            2) AS mom_pct
        FROM national_monthly
    ),
    monthly_stats AS (
        SELECT
            month_start,
            COUNT(commodity_name) AS staple_count,
            ROUND(AVG(ABS(mom_pct)), 2)  AS avg_abs_mom_pct,
            ROUND(STDDEV(mom_pct), 2)    AS stddev_mom_pct,
            ROUND(AVG(mom_pct), 2)       AS avg_mom_pct
        FROM with_mom
        WHERE mom_pct IS NOT NULL
        GROUP BY month_start
        HAVING COUNT(commodity_name) >= 2
    )
    SELECT
        month_start,
        staple_count,
        avg_abs_mom_pct,
        stddev_mom_pct,
        avg_mom_pct,
        -- GBVI Score formula:
        --   60% weight on average absolute MoM price change across the basket,
        --   normalised against a threshold of 15.0 (the 75th percentile of
        --   stable-year avg_abs_mom_pct in the 2006-2023 WFP Ghana dataset).
        --   40% weight on cross-commodity standard deviation of MoM changes,
        --   normalised against a threshold of 12.0 (75th percentile of
        --   stable-year stddev_mom_pct). Both components are capped at 100
        --   before weighting to prevent extreme shocks from producing scores
        --   above 100 due to denominator overflow.
        ROUND(
            LEAST(100.0, GREATEST(0.0,
                0.6 * LEAST(100.0, avg_abs_mom_pct / 15.0 * 100.0)
              + 0.4 * LEAST(100.0, COALESCE(stddev_mom_pct, 0) / 12.0 * 100.0)
            )),
        1) AS gbvi_score,
        CASE
            WHEN LEAST(100.0, GREATEST(0.0,
                    0.6 * LEAST(100.0, avg_abs_mom_pct / 15.0 * 100.0)
                  + 0.4 * LEAST(100.0, COALESCE(stddev_mom_pct, 0) / 12.0 * 100.0)
                 )) <= 30 THEN 'Stable'
            WHEN LEAST(100.0, GREATEST(0.0,
                    0.6 * LEAST(100.0, avg_abs_mom_pct / 15.0 * 100.0)
                  + 0.4 * LEAST(100.0, COALESCE(stddev_mom_pct, 0) / 12.0 * 100.0)
                 )) <= 70 THEN 'Moderate'
            ELSE 'High Alert'
        END AS risk_band
    FROM monthly_stats
    ORDER BY month_start;
    """)
    n = con.execute("SELECT COUNT(*) FROM fact_gbvi_index").fetchone()[0]
    logging.info(f"Deployed 'fact_gbvi_index' with {n:,} operational rows.")

    total_rows = (
        con.execute("SELECT COUNT(*) FROM fact_monthly_prices").fetchone()[0]
        + con.execute("SELECT COUNT(*) FROM fact_market_spreads").fetchone()[0]
        + n
    )
    logging.info("Analytics Views Pipeline executed successfully.")
    con.close()
    logger.success("3_build_analytics_views", rows_affected=total_rows, duration_seconds=time.perf_counter() - t0)

if __name__ == "__main__":
    main()
