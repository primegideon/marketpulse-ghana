"""
Analytics Views Builder Module
==============================
Constructs foundational analytical views in DuckDB for downstream BI reporting.
1. `fact_monthly_prices`: Generates aggregated monthly averages, tracking rolling trends and MoM%.
2. `fact_market_spreads`: Isolates the markup spread between agricultural producing regions and urban demand centers.
3. `fact_gbvi_index`: Computes the Ghana Basket Volatility Index, a proprietary 0-100 composite volatility metric.
"""

import duckdb
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CORE_STAPLES = ("maize", "maize (yellow)", "rice (local)", "rice (imported)",
                "cassava", "plantains (apem)", "plantains (apentu)", "tomatoes (local)", "tomatoes (navrongo)")

# Geographic classifications for supply chain spread calculation
PRODUCING_REGIONS = ("brong ahafo", "northern", "upper east", "upper west", "volta")
URBAN_REGIONS     = ("greater accra", "ashanti")

def main():
    db_path = "agri_ghana.duckdb"
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
        ROUND(
            LEAST(100.0, GREATEST(0.0,
                0.6 * LEAST(100.0, avg_abs_mom_pct / 30.0 * 100.0)
              + 0.4 * LEAST(100.0, COALESCE(stddev_mom_pct, 0) / 25.0 * 100.0)
            )),
        1) AS gbvi_score,
        CASE
            WHEN LEAST(100.0, GREATEST(0.0,
                    0.6 * LEAST(100.0, avg_abs_mom_pct / 30.0 * 100.0)
                  + 0.4 * LEAST(100.0, COALESCE(stddev_mom_pct, 0) / 25.0 * 100.0)
                 )) <= 30 THEN 'Stable'
            WHEN LEAST(100.0, GREATEST(0.0,
                    0.6 * LEAST(100.0, avg_abs_mom_pct / 30.0 * 100.0)
                  + 0.4 * LEAST(100.0, COALESCE(stddev_mom_pct, 0) / 25.0 * 100.0)
                 )) <= 70 THEN 'Moderate'
            ELSE 'High Alert'
        END AS risk_band
    FROM monthly_stats
    ORDER BY month_start;
    """)
    n = con.execute("SELECT COUNT(*) FROM fact_gbvi_index").fetchone()[0]
    logging.info(f"Deployed 'fact_gbvi_index' with {n:,} operational rows.")

    logging.info("Analytics Views Pipeline executed successfully.")
    con.close()

if __name__ == "__main__":
    main()
