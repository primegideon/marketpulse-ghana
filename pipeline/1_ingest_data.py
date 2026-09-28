"""
Data Ingestion Module
=====================
This module establishes a connection to the local DuckDB data warehouse and 
ingests the raw agricultural pricing dataset from the UN World Food Programme 
(Humanitarian Data Exchange) directly into a staging table.
"""

import duckdb
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    db_path = "agri_ghana.duckdb"
    wfp_url = "https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320/resource/e877350b-146f-4fa7-8690-db9605eea78c/download/wfp_food_prices_gha.csv"

    logging.info(f"Establishing connection to data warehouse: {db_path}")
    con = duckdb.connect(db_path)

    logging.info(f"Ingesting raw dataset from remote source: {wfp_url}")
    
    con.execute(f"""
        CREATE OR REPLACE TABLE raw_wfp_prices AS 
        SELECT * FROM read_csv_auto('{wfp_url}');
    """)

    row_count = con.execute("SELECT COUNT(*) FROM raw_wfp_prices").fetchone()[0]
    logging.info(f"Ingestion successful. Total records inserted into 'raw_wfp_prices': {row_count:,}")

    con.close()
    logging.info("Database connection closed.")

if __name__ == "__main__":
    main()