import duckdb
import pandas as pd

def main():
    db_path = "agri_ghana.duckdb"
    print(f"Connecting to {db_path}...")
    
    # Establish read-write connection to execute DDL statements
    con = duckdb.connect(db_path)
    
    print("Building analytics_monthly_prices view...")
    con.execute("""
    CREATE OR REPLACE VIEW analytics_monthly_prices AS
    SELECT 
        DATE_TRUNC('month', record_date) AS month_start,
        commodity_name,
        ROUND(AVG(price_per_kg_ghs), 2) AS avg_price_per_kg_ghs,
        COUNT(*) AS observation_count
    FROM stg_wfp_prices
    WHERE commodity_name LIKE '%maize%'
       OR commodity_name LIKE '%rice%'
       OR commodity_name LIKE '%cassava%'
       OR commodity_name LIKE '%plantain%'
       OR commodity_name LIKE '%tomato%'
    GROUP BY DATE_TRUNC('month', record_date), commodity_name;
    """)
    
    print("Building analytics_gbvi_metrics view...")
    con.execute("""
    CREATE OR REPLACE VIEW analytics_gbvi_metrics AS
    SELECT 
        month_start,
        commodity_name,
        avg_price_per_kg_ghs,
        ROUND(avg_price_per_kg_ghs - LAG(avg_price_per_kg_ghs) OVER (PARTITION BY commodity_name ORDER BY month_start), 2) AS mom_price_change_ghs,
        ROUND(((avg_price_per_kg_ghs - LAG(avg_price_per_kg_ghs) OVER (PARTITION BY commodity_name ORDER BY month_start)) / 
            NULLIF(LAG(avg_price_per_kg_ghs) OVER (PARTITION BY commodity_name ORDER BY month_start), 0)) * 100, 2) AS mom_pct_change
    FROM analytics_monthly_prices;
    """)

    print("\nViews successfully created.")
    
    # Output row count for verification
    row_count = con.execute("SELECT COUNT(*) FROM analytics_gbvi_metrics").fetchone()[0]
    print(f"Total rows in analytics_gbvi_metrics: {row_count:,}")
    
    # Output 5-row preview ordered by most recent date
    print("\nGBVI Metrics Preview (5 most recent rows):")
    preview_df = con.execute("""
        SELECT * 
        FROM analytics_gbvi_metrics 
        ORDER BY month_start DESC 
        LIMIT 5
    """).fetchdf()
    
    print(preview_df.to_string(index=False))
    
    con.close()

if __name__ == "__main__":
    main()
