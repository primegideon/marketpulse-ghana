import duckdb
import pandas as pd

# ============================================================
# MarketPulse Ghana — Analytics Views Builder
# Builds 3 DuckDB views from stg_wfp_prices:
#   1. fact_monthly_prices  — MoM%, rolling averages
#   2. fact_market_spreads  — producing vs. urban price gap
#   3. fact_gbvi_index      — Ghana Basket Volatility Index (0-100)
# ============================================================

CORE_STAPLES = ("maize", "maize (yellow)", "rice (local)", "rice (imported)",
                "cassava", "plantains (apem)", "plantains (apentu)", "tomatoes (local)", "tomatoes (navrongo)")

# Regions classified by agricultural role (Ghana geography)
PRODUCING_REGIONS = ("brong ahafo", "northern", "upper east", "upper west", "volta")
URBAN_REGIONS     = ("greater accra", "ashanti")

def main():
    db_path = "agri_ghana.duckdb"
    con = duckdb.connect(db_path)
    print(f"Connected to {db_path}.\n")

    # ----------------------------------------------------------
    # VIEW 1: fact_monthly_prices
    # Groups stg_wfp_prices into one monthly average per
    # (commodity, region), then computes:
    #   - MoM% change compared to previous month
    #   - 3-month rolling average (smoothed trend)
    #   - 6-month rolling average (longer-term trend)
    # Applies outlier guard: only prices 0.05–500 GHS/kg included.
    # ----------------------------------------------------------
    print("Building fact_monthly_prices...")
    con.execute("""
    CREATE OR REPLACE VIEW fact_monthly_prices AS
    WITH monthly AS (
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS month_start,
            commodity_name,
            region,
            ROUND(AVG(price_per_kg_ghs), 4) AS avg_price_per_kg_ghs,
            COUNT(*) AS observation_count
        FROM stg_wfp_prices
        WHERE price_per_kg_ghs BETWEEN 0.05 AND 500.0
        GROUP BY DATE_TRUNC('month', record_date)::DATE, commodity_name, region
        HAVING COUNT(*) >= 2   -- require at least 2 records per month to avoid single-point artifacts
    )
    SELECT
        month_start,
        commodity_name,
        region,
        avg_price_per_kg_ghs,
        observation_count,
        ROUND(AVG(avg_price_per_kg_ghs) OVER (
            PARTITION BY commodity_name, region
            ORDER BY month_start
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 4) AS rolling_3m_avg,
        ROUND(AVG(avg_price_per_kg_ghs) OVER (
            PARTITION BY commodity_name, region
            ORDER BY month_start
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ), 4) AS rolling_6m_avg,
        ROUND(
            (avg_price_per_kg_ghs
                - LAG(avg_price_per_kg_ghs) OVER (PARTITION BY commodity_name, region ORDER BY month_start)
            )
            / NULLIF(LAG(avg_price_per_kg_ghs) OVER (PARTITION BY commodity_name, region ORDER BY month_start), 0)
            * 100,
        2) AS mom_inflation_pct
    FROM monthly;
    """)
    n = con.execute("SELECT COUNT(*) FROM fact_monthly_prices").fetchone()[0]
    print(f"  fact_monthly_prices: {n:,} rows")
    df = con.execute("""
        SELECT * FROM fact_monthly_prices
        WHERE commodity_name = 'maize' AND region = 'brong ahafo'
        ORDER BY month_start LIMIT 6
    """).fetchdf()
    print("  Sample (maize, Brong Ahafo):")
    print(df[["month_start","avg_price_per_kg_ghs","rolling_3m_avg","mom_inflation_pct"]].to_string(index=False))

    # ----------------------------------------------------------
    # VIEW 2: fact_market_spreads
    # Measures the price gap between urban consumer regions
    # and rural producing regions for each commodity each month.
    #
    # Ghana agricultural geography:
    #   PRODUCING: Brong Ahafo, Northern, Upper East, Upper West, Volta
    #   URBAN:     Greater Accra, Ashanti (Kumasi)
    #
    # A positive spread_margin_pct means urban consumers pay
    # more than farm-gate prices — this is normal and captures
    # transport/storage markup. A very high spread signals
    # supply chain inefficiency.
    # ----------------------------------------------------------
    print("\nBuilding fact_market_spreads...")
    con.execute(f"""
    CREATE OR REPLACE VIEW fact_market_spreads AS
    WITH monthly AS (
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS month_start,
            commodity_name,
            region,
            ROUND(AVG(price_per_kg_ghs), 4) AS avg_price
        FROM stg_wfp_prices
        WHERE price_per_kg_ghs BETWEEN 0.05 AND 500.0
        GROUP BY DATE_TRUNC('month', record_date)::DATE, commodity_name, region
        HAVING COUNT(*) >= 2   -- require at least 2 records to avoid single-market noise
    ),
    urban AS (
        SELECT month_start, commodity_name, ROUND(AVG(avg_price), 4) AS urban_avg_price
        FROM monthly
        WHERE region IN {URBAN_REGIONS}
        GROUP BY month_start, commodity_name
    ),
    producing AS (
        SELECT month_start, commodity_name, ROUND(AVG(avg_price), 4) AS producing_avg_price
        FROM monthly
        WHERE region IN {PRODUCING_REGIONS}
        GROUP BY month_start, commodity_name
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
        2) AS spread_margin_pct
    FROM urban u
    JOIN producing p
        ON u.month_start = p.month_start
       AND u.commodity_name = p.commodity_name
    ORDER BY u.month_start, u.commodity_name;
    """)
    n = con.execute("SELECT COUNT(*) FROM fact_market_spreads").fetchone()[0]
    print(f"  fact_market_spreads: {n:,} rows")
    df = con.execute("""
        SELECT * FROM fact_market_spreads
        WHERE commodity_name = 'maize'
        ORDER BY month_start DESC LIMIT 6
    """).fetchdf()
    print("  Sample (maize, latest 6 months):")
    print(df.to_string(index=False))

    # ----------------------------------------------------------
    # VIEW 3: fact_gbvi_index
    # Ghana Basket Volatility Index — a single 0-100 score
    # measuring food price stability each month across the
    # 5 core staple crop groups defined in the project plan:
    #   Maize | Rice | Cassava | Plantain | Tomatoes
    #
    # Formula (composite):
    #   60% weight: average absolute MoM% change across staples
    #               (how much prices moved on average)
    #   40% weight: STDDEV of MoM% across staples
    #               (how differently each crop behaved)
    #
    # Each component is scaled to [0,100] before weighting:
    #   avg_abs_mom  / 30.0 * 100  (30% avg move = score 100)
    #   stddev_mom   / 25.0 * 100  (25% stddev   = score 100)
    #
    # Risk bands (matching project plan):
    #   0–30   → Stable Price Environment
    #   31–70  → Moderate Inflationary Pressure
    #   71–100 → High Food Volatility Alert
    # ----------------------------------------------------------
    print("\nBuilding fact_gbvi_index...")
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
        GROUP BY DATE_TRUNC('month', record_date)::DATE, commodity_name
        HAVING COUNT(*) >= 2   -- require at least 2 observations nationally per month
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
        HAVING COUNT(commodity_name) >= 2  -- need at least 2 commodities for meaningful score
    )
    SELECT
        month_start,
        staple_count,
        avg_abs_mom_pct,
        stddev_mom_pct,
        avg_mom_pct,
        -- Composite GBVI: 60% magnitude + 40% spread, bounded [0,100]
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
    print(f"  fact_gbvi_index: {n:,} rows")

    df = con.execute("SELECT * FROM fact_gbvi_index ORDER BY month_start DESC LIMIT 12").fetchdf()
    print("  Latest 12 months:")
    print(df.to_string(index=False))

    print("\n--- GBVI Score Distribution ---")
    dist = con.execute("""
        SELECT risk_band, COUNT(*) as months,
               ROUND(MIN(gbvi_score),1) as min_score,
               ROUND(MAX(gbvi_score),1) as max_score,
               ROUND(AVG(gbvi_score),1) as avg_score
        FROM fact_gbvi_index
        GROUP BY risk_band
        ORDER BY avg_score
    """).fetchdf()
    print(dist.to_string(index=False))

    print("\n--- fact_market_spreads: MoM inflation across ALL commodities ---")
    mom_check = con.execute("""
        SELECT MIN(mom_inflation_pct), MAX(mom_inflation_pct), 
               COUNT(CASE WHEN ABS(mom_inflation_pct) > 100 THEN 1 END) as extreme_count
        FROM fact_monthly_prices WHERE mom_inflation_pct IS NOT NULL
    """).fetchdf()
    print(mom_check.to_string(index=False))

    print("\nAll views rebuilt successfully.")
    con.close()

if __name__ == "__main__":
    main()
