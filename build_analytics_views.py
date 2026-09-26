import duckdb
import pandas as pd

def main():
    db_path = "agri_ghana.duckdb"
    
    # Establish read-write connection to execute DDL statements
    con = duckdb.connect(db_path)
    print(f"Connected to {db_path}.")
    
    print("Building fact_monthly_prices view...")
    con.execute("""
    CREATE OR REPLACE VIEW fact_monthly_prices AS
    WITH monthly_aggs AS (
        SELECT 
            DATE_TRUNC('month', record_date) AS month_start,
            commodity_name,
            region,
            ROUND(AVG(price_per_kg_ghs), 2) AS avg_price_per_kg_ghs,
            COUNT(*) AS observation_count
        FROM stg_wfp_prices
        WHERE price_per_kg_ghs BETWEEN 0.05 AND 150.0
        GROUP BY DATE_TRUNC('month', record_date), commodity_name, region
    )
    SELECT 
        *,
        ROUND(AVG(avg_price_per_kg_ghs) OVER (
            PARTITION BY region, commodity_name 
            ORDER BY month_start 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2) AS rolling_3m_avg,
        ROUND(AVG(avg_price_per_kg_ghs) OVER (
            PARTITION BY region, commodity_name 
            ORDER BY month_start 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ), 2) AS rolling_6m_avg,
        ROUND(((avg_price_per_kg_ghs - LAG(avg_price_per_kg_ghs) OVER (
            PARTITION BY region, commodity_name 
            ORDER BY month_start
        )) / NULLIF(LAG(avg_price_per_kg_ghs) OVER (
            PARTITION BY region, commodity_name 
            ORDER BY month_start
        ), 0)) * 100, 2) AS mom_inflation_pct
    FROM monthly_aggs;
    """)
    
    print("Building fact_market_spreads view...")
    con.execute("""
    CREATE OR REPLACE VIEW fact_market_spreads AS
    WITH region_types AS (
        SELECT 
            month_start,
            commodity_name,
            region,
            avg_price_per_kg_ghs,
            CASE 
                WHEN region IN ('greater accra', 'ashanti') THEN 'Urban'
                ELSE 'Producing'
            END AS region_type
        FROM fact_monthly_prices
    ),
    producing AS (
        SELECT month_start, commodity_name, ROUND(AVG(avg_price_per_kg_ghs), 2) AS producing_avg_price
        FROM region_types WHERE region_type = 'Producing'
        GROUP BY 1, 2
    ),
    urban AS (
        SELECT month_start, commodity_name, ROUND(AVG(avg_price_per_kg_ghs), 2) AS urban_avg_price
        FROM region_types WHERE region_type = 'Urban'
        GROUP BY 1, 2
    ),
    spreads AS (
        SELECT 
            u.month_start,
            u.commodity_name,
            u.urban_avg_price,
            p.producing_avg_price,
            ROUND(u.urban_avg_price - p.producing_avg_price, 2) AS absolute_spread_ghs,
            ROUND(((u.urban_avg_price - p.producing_avg_price) / NULLIF(p.producing_avg_price, 0)) * 100, 2) AS spread_margin_pct
        FROM urban u
        JOIN producing p ON u.month_start = p.month_start AND u.commodity_name = p.commodity_name
    )
    SELECT * FROM spreads
    WHERE spread_margin_pct BETWEEN -100.0 AND 300.0;
    """)

    print("Building fact_gbvi_index view...")
    con.execute("""
    CREATE OR REPLACE VIEW fact_gbvi_index AS
    WITH core_staples AS (
        SELECT 
            DATE_TRUNC('month', record_date) AS month_start,
            commodity_name,
            ROUND(AVG(price_per_kg_ghs), 2) AS nat_avg_price
        FROM stg_wfp_prices
        WHERE price_per_kg_ghs BETWEEN 0.05 AND 150.0
          AND (commodity_name LIKE '%maize%'
           OR commodity_name LIKE '%rice%'
           OR commodity_name LIKE '%cassava%'
           OR commodity_name LIKE '%plantain%'
           OR commodity_name LIKE '%tomato%')
        GROUP BY DATE_TRUNC('month', record_date), commodity_name
    ),
    staple_mom AS (
        SELECT 
            month_start,
            commodity_name,
            ROUND(((nat_avg_price - LAG(nat_avg_price) OVER (PARTITION BY commodity_name ORDER BY month_start)) / 
                NULLIF(LAG(nat_avg_price) OVER (PARTITION BY commodity_name ORDER BY month_start), 0)) * 100, 2) AS mom_pct
        FROM core_staples
    ),
    monthly_volatility AS (
        SELECT 
            month_start,
            ROUND(STDDEV(mom_pct), 2) AS mom_volatility,
            ROUND(AVG(mom_pct), 2) AS avg_mom_pct
        FROM staple_mom
        WHERE mom_pct IS NOT NULL
        GROUP BY month_start
    ),
    gbvi_scaled AS (
        SELECT 
            month_start,
            mom_volatility,
            avg_mom_pct,
            -- Bounded scaling: Caps volatility scaling smoothly up to 100
            ROUND(LEAST(100.0, GREATEST(0.0, COALESCE(mom_volatility * 2.0, 0))), 2) AS gbvi_score
        FROM monthly_volatility
    )
    SELECT 
        *,
        CASE 
            WHEN gbvi_score <= 30 THEN '0-30: Stable'
            WHEN gbvi_score <= 70 THEN '31-70: Moderate'
            ELSE '71-100: High Alert'
        END AS risk_band
    FROM gbvi_scaled;
    """)

    print("\nAnalytics views successfully built with robust safeguards.\n")
    
    # ---------------------------------------------------------
    # Verification Outputs
    # ---------------------------------------------------------
    
    # 1. fact_monthly_prices
    row_count = con.execute("SELECT COUNT(*) FROM fact_monthly_prices").fetchone()[0]
    print(f"Total rows in fact_monthly_prices: {row_count:,}")
    print("Preview (5 most recent rows):")
    df = con.execute("SELECT * FROM fact_monthly_prices ORDER BY month_start DESC LIMIT 5").fetchdf()
    print(df.to_string(index=False) + "\n")
    
    # 2. fact_market_spreads
    row_count = con.execute("SELECT COUNT(*) FROM fact_market_spreads").fetchone()[0]
    print(f"Total rows in fact_market_spreads: {row_count:,}")
    print("Preview (5 most recent rows):")
    df = con.execute("SELECT * FROM fact_market_spreads ORDER BY month_start DESC LIMIT 5").fetchdf()
    print(df.to_string(index=False) + "\n")
    
    # 3. fact_gbvi_index
    row_count = con.execute("SELECT COUNT(*) FROM fact_gbvi_index").fetchone()[0]
    print(f"Total rows in fact_gbvi_index: {row_count:,}")
    print("Preview (5 most recent rows):")
    df = con.execute("SELECT * FROM fact_gbvi_index ORDER BY month_start DESC LIMIT 5").fetchdf()
    print(df.to_string(index=False) + "\n")
    
    con.close()

if __name__ == "__main__":
    main()
