import duckdb
import pandas as pd

def main():
    db_path = "agri_ghana.duckdb"
    
    # Opening in read_only mode ensures this script won't clash with the IDE extension
    con = duckdb.connect(db_path, read_only=True)
    
    print("--- Staging Table Verification ---\n")
    
    # 1. Verify zero nulls in price_per_kg_ghs
    null_count = con.execute("""
        SELECT COUNT(*) 
        FROM stg_wfp_prices 
        WHERE price_per_kg_ghs IS NULL
    """).fetchone()[0]
    print(f"Null values in price_per_kg_ghs: {null_count}")
    
    # 2. Display distinct commodities
    commodities_df = con.execute("""
        SELECT DISTINCT commodity_name 
        FROM stg_wfp_prices 
        ORDER BY commodity_name
    """).fetchdf()
    print(f"\nDistinct commodities ({len(commodities_df)} total):")
    print(", ".join(commodities_df['commodity_name'].tolist()))
    
    # 3. Average 1 KG price per commodity for the year 2023
    avg_prices_2023 = con.execute("""
        SELECT 
            commodity_name, 
            ROUND(AVG(price_per_kg_ghs), 2) AS avg_price_per_kg_2023
        FROM stg_wfp_prices 
        WHERE EXTRACT(YEAR FROM record_date) = 2023
        GROUP BY commodity_name
        ORDER BY avg_price_per_kg_2023 DESC
    """).fetchdf()
    
    print("\nAverage 1 KG Price per Commodity (Year 2023):")
    if not avg_prices_2023.empty:
        print(avg_prices_2023.to_string(index=False))
    else:
        print("No records found for the year 2023.")
    
    con.close()

if __name__ == "__main__":
    main()
