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

def compute_mape(y_true, y_pred):
    """Calculate Mean Absolute Percentage Error."""
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def main():
    db_path = "agri_ghana.duckdb"
    
    # Connect in read-write mode to export results back to the database
    con = duckdb.connect(db_path, read_only=False)
    
    print("Extracting historical monthly prices...")
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
    df['ds'] = pd.to_datetime(df['ds'])
    
    # ---------------------------------------------------------
    # Split Data (Pre-2022 Train, 2022+ Test)
    # ---------------------------------------------------------
    split_date = pd.to_datetime("2022-01-01")
    train_df = df[df['ds'] < split_date].copy()
    test_df = df[df['ds'] >= split_date].copy()
    
    # Calculate Naive Baseline predictions for the test set
    test_df['y_pred_naive'] = test_df.groupby('commodity_name')['y'].shift(1)
    last_train_vals = train_df.groupby('commodity_name').last().reset_index()[['commodity_name', 'y']]
    last_train_vals = last_train_vals.rename(columns={'y': 'last_train_y'})
    test_df = test_df.merge(last_train_vals, on='commodity_name', how='left')
    test_df['y_pred_naive'] = test_df['y_pred_naive'].fillna(test_df['last_train_y'])
    
    # Store Naive MAPE per commodity
    naive_mapes = {}
    for crop in test_df['commodity_name'].unique():
        crop_test = test_df[test_df['commodity_name'] == crop]
        naive_mapes[crop] = compute_mape(crop_test['y'].values, crop_test['y_pred_naive'].values)
    
    # ---------------------------------------------------------
    # Train Prophet, Evaluate, and Forecast
    # ---------------------------------------------------------
    all_forecasts = []
    performance_records = []
    
    commodities = train_df['commodity_name'].unique()
    
    for crop in commodities:
        crop_train = train_df[train_df['commodity_name'] == crop][['ds', 'y']]
        crop_test = test_df[test_df['commodity_name'] == crop][['ds', 'y']]
        
        # Fit model on training data ONLY
        m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        m.fit(crop_train)
        
        # Evaluate on out-of-sample test data
        if len(crop_test) > 0:
            test_forecast = m.predict(crop_test[['ds']])
            prophet_mape = compute_mape(crop_test['y'].values, test_forecast['yhat'].values)
        else:
            prophet_mape = None
            
        naive_mape = naive_mapes.get(crop, None)
        
        # Record performance comparison
        performance_records.append({
            'Commodity': crop,
            'Naive MAPE (%)': round(naive_mape, 2) if naive_mape else None,
            'Prophet MAPE (%)': round(prophet_mape, 2) if prophet_mape else None,
            'Prophet Wins?': "YES" if (prophet_mape and naive_mape and prophet_mape < naive_mape) else "NO"
        })
        
        # Generate full historical timeline + 30-Day Future Forecast (1 Month Ahead)
        # Using freq='MS' (Month Start) to align with our DATE_TRUNC monthly data
        future = m.make_future_dataframe(periods=1, freq='MS')
        forecast = m.predict(future)
        
        forecast['commodity_name'] = crop
        forecast['mape_score'] = prophet_mape
        forecast['baseline_mape_score'] = naive_mape
        
        # Tag whether the row is a future prediction or a historical backcast
        max_historical_date = df[df['commodity_name'] == crop]['ds'].max()
        forecast['is_forecast'] = forecast['ds'] > max_historical_date
        
        # Subset to final schema columns
        keep_cols = ['commodity_name', 'ds', 'yhat', 'yhat_lower', 'yhat_upper', 'mape_score', 'baseline_mape_score', 'is_forecast']
        all_forecasts.append(forecast[keep_cols])
        
    # Combine everything into one giant DataFrame
    final_forecast_df = pd.concat(all_forecasts, ignore_index=True)
    
    # Rename columns to match exact DuckDB schema requirements
    final_forecast_df = final_forecast_df.rename(columns={
        'ds': 'record_date',
        'yhat': 'predicted_price_ghs',
        'yhat_lower': 'lower_bound_ghs',
        'yhat_upper': 'upper_bound_ghs'
    })
    
    # Enforce non-negative floor (clip at 0.01) to observe real-world economic bounds
    final_forecast_df['predicted_price_ghs'] = final_forecast_df['predicted_price_ghs'].clip(lower=0.01)
    final_forecast_df['lower_bound_ghs'] = final_forecast_df['lower_bound_ghs'].clip(lower=0.01)
    final_forecast_df['upper_bound_ghs'] = final_forecast_df['upper_bound_ghs'].clip(lower=0.01)
    
    # ---------------------------------------------------------
    # Terminal Output & Database Backwrite
    # ---------------------------------------------------------
    print("\n--- Out-of-Sample Performance Comparison (MAPE) ---")
    perf_df = pd.DataFrame(performance_records)
    print(perf_df.to_string(index=False))
    
    print("\nWriting forecasts to DuckDB (fact_price_forecasts)...")
    con.execute("DROP TABLE IF EXISTS fact_price_forecasts")
    
    # Create strict schema
    con.execute("""
    CREATE TABLE fact_price_forecasts (
        commodity_name VARCHAR,
        record_date DATE,
        predicted_price_ghs DOUBLE,
        lower_bound_ghs DOUBLE,
        upper_bound_ghs DOUBLE,
        mape_score DOUBLE,
        baseline_mape_score DOUBLE,
        is_forecast BOOLEAN
    )
    """)
    
    # Bulk insert
    con.execute("INSERT INTO fact_price_forecasts SELECT * FROM final_forecast_df")
    print("Export successful!")
    
    print("\nPreview of fact_price_forecasts (5 most recent future predictions):")
    preview = con.execute("""
        SELECT * 
        FROM fact_price_forecasts 
        WHERE is_forecast = TRUE 
        ORDER BY record_date DESC 
        LIMIT 5
    """).fetchdf()
    print(preview.to_string(index=False))
    
    con.close()

if __name__ == "__main__":
    main()
