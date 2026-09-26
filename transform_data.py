import duckdb
import pandas as pd

def main():
    db_path = "agri_ghana.duckdb"
    print(f"Connecting to {db_path}...")
    con = duckdb.connect(db_path)

    print("Running transformation and creating stg_wfp_prices...")

    sql_query = """
    CREATE OR REPLACE TABLE stg_wfp_prices AS
    WITH cleaned_data AS (
        SELECT 
            CAST(date AS DATE) AS record_date,
            TRIM(LOWER(admin1)) AS region,
            TRIM(LOWER(admin2)) AS district,
            TRIM(LOWER(market)) AS market_name,
            TRIM(LOWER(commodity)) AS commodity_name,
            TRIM(LOWER(unit)) AS raw_unit,
            TRIM(LOWER(pricetype)) AS price_type,
            CAST(price AS DOUBLE) AS raw_price_ghs
        FROM raw_wfp_prices
        WHERE price IS NOT NULL AND CAST(price AS DOUBLE) > 0
    ),
    converted_data AS (
        SELECT 
            *,
            CASE 
                WHEN raw_unit = 'kg' THEN 1.0
                WHEN raw_unit LIKE '%kg%' 
                    THEN CAST(regexp_extract(raw_unit, '[0-9]+') AS DOUBLE)
                WHEN raw_unit LIKE '100 tuber%' THEN 350.0
                WHEN raw_unit LIKE '%bunch%' THEN 20.0
                WHEN raw_unit LIKE '%pcs%' OR raw_unit LIKE '%pieces%' THEN 15.0
                ELSE 1.0
            END AS kg_conversion_factor,

            CASE 
                WHEN raw_unit = 'kg' THEN 'exact'
                WHEN raw_unit LIKE '%kg%' THEN 'exact'
                WHEN raw_unit LIKE '100 tuber%' OR raw_unit LIKE '%bunch%' OR raw_unit LIKE '%pcs%' OR raw_unit LIKE '%pieces%' 
                    THEN 'estimated'
                ELSE 'unrecognized_fallback'
            END AS conversion_confidence
        FROM cleaned_data
    )
    SELECT 
        *,
        ROUND(raw_price_ghs / kg_conversion_factor, 4) AS price_per_kg_ghs
    FROM converted_data;
    """

    con.execute(sql_query)

    row_count = con.execute("SELECT COUNT(*) FROM stg_wfp_prices").fetchone()[0]
    print(f"\nTransformation complete. Total records in stg_wfp_prices: {row_count:,}")

    confidence_breakdown = con.execute("""
        SELECT conversion_confidence, COUNT(*) AS row_count 
        FROM stg_wfp_prices 
        GROUP BY conversion_confidence
    """).fetchdf()
    print("\nConversion confidence breakdown:")
    print(confidence_breakdown.to_string(index=False))

    print("\nData Preview (5 rows):")
    sample_df = con.execute("SELECT * FROM stg_wfp_prices LIMIT 5").fetchdf()
    print(sample_df.to_string(index=False))

    con.close()

if __name__ == "__main__":
    main()