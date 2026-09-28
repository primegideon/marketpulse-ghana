"""
Data Transformation Module
==========================
This module sanitizes the raw pricing dataset. It executes unit normalization 
algorithms to convert diverse local market units (e.g., specific bag weights, 
bunches, tubers) into a standardized Price-per-Kilogram (GHS/KG) metric, 
ensuring accurate comparative analysis downstream.
"""

import duckdb
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    db_path = "agri_ghana.duckdb"
    logging.info(f"Connecting to database: {db_path}")
    con = duckdb.connect(db_path)

    logging.info("Executing normalization transformations to build 'stg_wfp_prices'...")
    
    sql_query = r"""
    CREATE OR REPLACE TABLE stg_wfp_prices AS
    WITH cleaned_data AS (
        SELECT 
            CAST(date AS DATE) AS record_date,
            TRIM(LOWER(admin1)) AS region,
            TRIM(LOWER(admin2)) AS district,
            TRIM(LOWER(market)) AS market_name,
            TRIM(LOWER(commodity)) AS commodity_name,
            CAST(latitude AS DOUBLE) AS latitude,
            CAST(longitude AS DOUBLE) AS longitude,
            TRIM(LOWER(unit)) AS raw_unit,
            TRIM(LOWER(pricetype)) AS price_type,
            CAST(price AS DOUBLE) AS raw_price_ghs
        FROM raw_wfp_prices
        WHERE price IS NOT NULL AND CAST(price AS DOUBLE) > 0
    ),
    converted_data AS (
        SELECT 
            *,
            -- ----------------------------------------------------------------
            -- KG Conversion Factor Logic
            -- Purpose: normalise every price to a per-1-kg basis.
            --
            -- Unit reference (from WFP Ghana dataset audit):
            --   'kg'           -> 1 kg  (retail, already per kg)
            --   'N kg'         -> N kg  (wholesale bag of N kg)
            --   'bunch'        -> 12 kg (standard WFP plantain bunch weight)
            --   '100 tubers'   -> 50 kg (cassava: ~0.5 kg avg per tuber)
            --   '30 pcs'       -> 30    (eggs: price per tray / 30 eggs)
            --                    NOTE: eggs not in staple scope (won't affect GBVI)
            -- ----------------------------------------------------------------
            CASE 
                WHEN raw_unit = 'kg' THEN 1.0
                WHEN raw_unit LIKE '%bunch%' THEN 12.0
                WHEN raw_unit LIKE '%tuber%' THEN 50.0
                WHEN raw_unit = '30 pcs' THEN 30.0
                WHEN REGEXP_MATCHES(raw_unit, '^\d+\s*kg$')
                    THEN TRY_CAST(REGEXP_EXTRACT(raw_unit, '^(\d+)', 1) AS DOUBLE)
                ELSE 1.0
            END AS kg_conversion_factor
        FROM cleaned_data
    )
    SELECT 
        record_date,
        region,
        district,
        market_name,
        latitude,
        longitude,
        commodity_name,
        raw_unit,
        price_type,
        raw_price_ghs,
        kg_conversion_factor,
        -- Apply hard boundaries to exclude macroeconomic outliers
        GREATEST(0.01, LEAST(500.0, ROUND(raw_price_ghs / NULLIF(kg_conversion_factor, 0), 2))) AS price_per_kg_ghs
    FROM converted_data
    WHERE raw_price_ghs > 0 AND kg_conversion_factor > 0;
    """
    
    con.execute(sql_query)

    row_count = con.execute("SELECT COUNT(*) FROM stg_wfp_prices").fetchone()[0]
    logging.info(f"Transformation complete. Total records in 'stg_wfp_prices': {row_count:,}")

    logging.info("Unit Conversion Factor Distribution Mapping:")
    mapping_df = con.execute("""
        SELECT raw_unit, kg_conversion_factor, COUNT(*) as observation_count
        FROM stg_wfp_prices
        GROUP BY raw_unit, kg_conversion_factor
        ORDER BY observation_count DESC
    """).fetchdf()
    print(mapping_df.to_string(index=False))

    logging.info("Normalized Price per KG ranges by commodity (Validation Check):")
    sample_df = con.execute("""
        SELECT 
            commodity_name,
            ROUND(MIN(price_per_kg_ghs), 2) AS min_ghs,
            ROUND(MAX(price_per_kg_ghs), 2) AS max_ghs,
            ROUND(AVG(price_per_kg_ghs), 2) AS avg_ghs,
            COUNT(*) AS observation_count
        FROM stg_wfp_prices
        GROUP BY commodity_name
        ORDER BY avg_ghs DESC
    """).fetchdf()
    print(sample_df.to_string(index=False))
    
    con.close()
    logging.info("Database connection closed.")

if __name__ == "__main__":
    main()