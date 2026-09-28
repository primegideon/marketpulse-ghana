import duckdb
import pandas as pd
import numpy as np
from prophet import Prophet
import logging
import warnings

# Suppress prophet logging noise
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").disabled = True
warnings.filterwarnings("ignore")

def main():
    db_path = "agri_ghana.duckdb"
    con = duckdb.connect(db_path, read_only=True)
    
    print("Extracting historical monthly prices for core staples...")
    
    # Extract national average per commodity per month
    query = """
    SELECT 
        CAST(month_start AS DATE) AS ds,
        commodity_name,
        ROUND(AVG(avg_price_per_kg_ghs), 2) AS y
    FROM fact_monthly_prices
    WHERE commodity_name LIKE '%maize%'
       OR commodity_name LIKE '%rice%'
       OR commodity_name LIKE '%cassava%'
       OR commodity_name LIKE '%plantain%'
       OR commodity_name LIKE '%tomato%'
    GROUP BY month_start, commodity_name
    ORDER BY commodity_name, ds
    """
    
    df = con.execute(query).fetchdf()
    con.close()
    
    df['ds'] = pd.to_datetime(df['ds'])
    
    print(f"Total dataset records: {len(df)}")
    
    # ---------------------------------------------------------
    # Prevent Data Leakage (Chronological Split)
    # ---------------------------------------------------------
    split_date = pd.to_datetime("2022-01-01")
    train_df = df[df['ds'] < split_date].copy()
    test_df = df[df['ds'] >= split_date].copy()
    
    print(f"\n[Split] Train data (before {split_date.date()}): {len(train_df)} records")
    print(f"[Split] Test data (from {split_date.date()}): {len(test_df)} records")
    print(f"Train date range: {train_df['ds'].min().date()} to {train_df['ds'].max().date()}")
    print(f"Test date range: {test_df['ds'].min().date()} to {test_df['ds'].max().date()}")
    
    # ---------------------------------------------------------
    # Naive Baseline Benchmark
    # ---------------------------------------------------------
    print("\nComputing Naive Baseline Benchmark on Out-of-Sample Test Set...")
    # Predict next month = previous month's price
    test_df['y_pred_naive'] = test_df.groupby('commodity_name')['y'].shift(1)
    
    # Backfill the first test row with the last known train row
    last_train_vals = train_df.groupby('commodity_name').last().reset_index()[['commodity_name', 'y']]
    last_train_vals = last_train_vals.rename(columns={'y': 'last_train_y'})
    test_df = test_df.merge(last_train_vals, on='commodity_name', how='left')
    test_df['y_pred_naive'] = test_df['y_pred_naive'].fillna(test_df['last_train_y'])
    test_df = test_df.drop(columns=['last_train_y'])
    
    # Compute MAE for Naive Baseline
    test_df['naive_error'] = np.abs(test_df['y'] - test_df['y_pred_naive'])
    naive_mae = test_df.groupby('commodity_name')['naive_error'].mean()
    
    print("Naive Baseline Mean Absolute Error (MAE) by commodity:")
    print(naive_mae.round(2).to_string())
    
    # ---------------------------------------------------------
    # Fit Meta Prophet Models
    # ---------------------------------------------------------
    print("\nTraining Prophet models exclusively on train_df (Zero Data Leakage)...")
    models = {}
    
    commodities = train_df['commodity_name'].unique()
    for crop in commodities:
        print(f"  -> Fitting model for: {crop}")
        crop_train = train_df[train_df['commodity_name'] == crop][['ds', 'y']]
        
        m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        m.fit(crop_train)
        models[crop] = m
        
    print("\nVerification: All Prophet models successfully trained on isolated historical data.")

if __name__ == "__main__":
    main()
