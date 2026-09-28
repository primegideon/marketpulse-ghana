import duckdb

con = duckdb.connect('agri_ghana.duckdb')

# Check actual column types in the fact tables
print("=== fact_monthly_prices columns ===")
print(con.execute("DESCRIBE fact_monthly_prices").df())

print("\n=== fact_gbvi_index columns ===")
print(con.execute("DESCRIBE fact_gbvi_index").df())

print("\n=== fact_market_spreads columns ===")
print(con.execute("DESCRIBE fact_market_spreads").df())

print("\n=== fact_price_forecasts columns ===")
print(con.execute("DESCRIBE fact_price_forecasts").df())

print("\n=== List of views ===")
print(con.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema='main'").df())
