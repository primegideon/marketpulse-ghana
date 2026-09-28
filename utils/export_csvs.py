import duckdb

con = duckdb.connect('agri_ghana.duckdb')

tables = [
    'fact_monthly_prices',
    'fact_gbvi_index',
    'fact_market_spreads',
    'fact_price_forecasts'
]

import os
os.makedirs('ui/sources/agri_ghana', exist_ok=True)

for table in tables:
    print(f"Exporting {table} to CSV...")
    try:
        con.execute(f"COPY {table} TO 'ui/sources/agri_ghana/{table}.csv' (HEADER, DELIMITER ',')")
    except Exception as e:
        print(f"Failed exporting {table}: {e}")

print("Export complete.")
