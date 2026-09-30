"""
Model performance diagnosis: shows exactly what the test window looks like
and why a time-series model cannot beat a naive baseline on it.
"""
import duckdb
import pandas as pd

con = duckdb.connect("agri_ghana.duckdb")

print("=== GHS/USD exchange rate during training vs test window ===")
print(con.execute("""
    SELECT
        DATE_TRUNC('year', record_date)::DATE AS year,
        ROUND(AVG(price_per_kg_ghs), 2) AS avg_maize_retail_ghs
    FROM stg_wfp_prices
    WHERE commodity_name = 'maize' AND price_type = 'retail'
    GROUP BY 1 ORDER BY 1
""").fetchdf().to_string())

print()
print("=== Training/test split for maize ===")
df = con.execute("""
    SELECT
        DATE_TRUNC('month', record_date)::DATE AS ds,
        ROUND(AVG(price_per_kg_ghs), 4) AS y
    FROM stg_wfp_prices
    WHERE commodity_name = 'maize'
      AND price_per_kg_ghs BETWEEN 0.05 AND 500.0
      AND price_type = 'retail'
    GROUP BY 1 HAVING COUNT(*) >= 3
    ORDER BY 1
""").fetchdf()
n = len(df)
split = int(n * 0.8)
print(f"Total months: {n}")
print(f"Train: {df['ds'].iloc[0].date()} to {df['ds'].iloc[split-1].date()} ({split} months)")
print(f"Test:  {df['ds'].iloc[split].date()} to {df['ds'].iloc[-1].date()} ({n - split} months)")
print()
print("Test period prices (the shock window the model is evaluated on):")
print(df.iloc[split:].to_string())

con.close()
