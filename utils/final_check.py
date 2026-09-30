import duckdb
con = duckdb.connect("agri_ghana.duckdb")

print("=== fact_gbvi_index (last 5) ===")
print(con.execute(
    "SELECT month_start, gbvi_score, risk_band, avg_mom_pct, avg_abs_mom_pct "
    "FROM fact_gbvi_index ORDER BY month_start DESC LIMIT 5"
).fetchdf().to_string())

print("\n=== fact_monthly_prices (retail maize last 5) ===")
print(con.execute(
    "SELECT month_start, region, avg_price_per_kg_ghs, price_type "
    "FROM fact_monthly_prices "
    "WHERE commodity_name = 'maize' AND price_type = 'retail' "
    "ORDER BY month_start DESC LIMIT 5"
).fetchdf().to_string())

print("\n=== fact_market_spreads (last 5) ===")
print(con.execute(
    "SELECT month_start, commodity_name, spread_margin_pct, price_type "
    "FROM fact_market_spreads ORDER BY month_start DESC LIMIT 5"
).fetchdf().to_string())

print("\n=== fact_price_forecasts ===")
print(con.execute(
    "SELECT commodity_name, record_date, predicted_price_ghs, mape_score, directional_accuracy "
    "FROM fact_price_forecasts ORDER BY commodity_name, record_date"
).fetchdf().to_string())

con.close()
