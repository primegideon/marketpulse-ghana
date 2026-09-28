import duckdb

# 1. Connect to (or create) local DuckDB database file
db_path = "agri_ghana.duckdb"
con = duckdb.connect(db_path)

print("Connecting to DuckDB...")

# 2. Direct download URL for WFP Ghana Food Prices on HDX
wfp_url = "https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320/resource/e877350b-146f-4fa7-8690-db9605eea78c/download/wfp_food_prices_gha.csv"

# 3. Create raw staging table
con.execute(
    f"""
    CREATE OR REPLACE TABLE raw_wfp_prices AS 
    SELECT * FROM read_csv_auto('{wfp_url}');
"""
)

# 4. Verify record count
row_count = con.execute("SELECT COUNT(*) FROM raw_wfp_prices").fetchone()[0]
print(
    f"Successfully ingested WFP Ghana dataset! Total records in raw_wfp_prices: {row_count:,}"
)

# Close connection
con.close()