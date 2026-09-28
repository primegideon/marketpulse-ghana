"""
Machine Learning Forecasting Pipeline
=====================================
Integrates Meta's Prophet algorithm to generate robust 30-day forward price
trajectories for core staple crops. Employs chronological splits and naive
baseline evaluation mechanisms to strictly validate out-of-sample performance
before persisting projections to the data warehouse.
"""

import duckdb
import pandas as pd
import numpy as np
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import logging
import warnings

# Suppress Prophet non-critical runtime warnings
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------
DB_PATH = "agri_ghana.duckdb"

STAPLES = [
    "maize",
    "cassava",
    "rice (local)",
    "rice (imported)",
    "plantains (apentu)",
    "tomatoes (local)",
]

FORECAST_MONTHS = 3

# Guardrails from plan
PRICE_FLOOR_GHS  = 0.01   # Non-negativity floor
PRICE_CEIL_GHS   = 500.0  # Macro outlier ceiling

# Minimum months of data required to train a model
MIN_TRAINING_MONTHS = 18

def get_national_monthly(con: duckdb.DuckDBPyConnection, commodity: str) -> pd.DataFrame:
    """Retrieves aggregated monthly retail data for time-series modeling."""
    df = con.execute(f"""
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS ds,
            ROUND(AVG(price_per_kg_ghs), 4) AS y
        FROM stg_wfp_prices
        WHERE commodity_name = '{commodity}'
          AND price_per_kg_ghs BETWEEN 0.05 AND {PRICE_CEIL_GHS}
          AND price_type = 'retail'
        GROUP BY DATE_TRUNC('month', record_date)::DATE
        HAVING COUNT(*) >= 3
        ORDER BY ds
    """).fetchdf()
    df["ds"] = pd.to_datetime(df["ds"])
    return df

def naive_mape(series: pd.Series) -> float:
    """Calculates a naive lag-1 baseline MAPE over the final 20% validation window."""
    n = len(series)
    test_size = max(3, int(n * 0.2))
    test = series.iloc[-test_size:]
    baseline = series.iloc[-(test_size + 1):-1].values  # shift by 1

    if len(baseline) == 0:
        return np.nan

    errors = np.abs((test.values - baseline) / np.where(baseline == 0, np.nan, baseline))
    return float(np.nanmean(errors) * 100)

def fit_and_forecast(commodity: str, df: pd.DataFrame) -> pd.DataFrame:
    """Instantiates and fits the Prophet engine to derive future price boundaries."""
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.15,
        seasonality_mode="multiplicative",
    )
    model.fit(df)

    future = model.make_future_dataframe(
        periods=FORECAST_MONTHS,
        freq="MS",          # Month Start: aligns with monthly training data
        include_history=False,  # Return ONLY future dates, no historical rows
    )
    forecast = model.predict(future)

    result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    result["is_forecast"] = True

    for col in ["yhat", "yhat_lower", "yhat_upper"]:
        result[col] = result[col].clip(lower=PRICE_FLOOR_GHS, upper=PRICE_CEIL_GHS)

    result["commodity_name"] = commodity
    result["market_name"]    = "national"

    result = result.rename(columns={
        "ds":          "record_date",
        "yhat":        "predicted_price_ghs",
        "yhat_lower":  "lower_bound_ghs",
        "yhat_upper":  "upper_bound_ghs",
    })

    return result[["commodity_name", "market_name", "record_date",
                   "predicted_price_ghs", "lower_bound_ghs", "upper_bound_ghs",
                   "is_forecast"]]

def evaluate_mape(commodity: str, df: pd.DataFrame) -> tuple[float, float]:
    """Executes walk-forward cross-validation for rigorous accuracy tracking."""
    baseline = naive_mape(df["y"])
    n_months = len(df)
    
    if n_months < MIN_TRAINING_MONTHS:
        logging.warning(f"[{commodity}] Insufficient epochs for cross-validation ({n_months} months).")
        return np.nan, baseline

    try:
        # Use last 20% as test horizon, 60% as initial training window
        initial_months = max(12, int(n_months * 0.6))
        horizon_months = max(3, int(n_months * 0.2))

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.15,
            seasonality_mode="multiplicative",
        )
        model.fit(df)

        cv_df = cross_validation(
            model,
            initial=f"{initial_months * 30} days",
            period="30 days",
            horizon=f"{horizon_months * 30} days",
            disable_tqdm=True,
        )
        pm = performance_metrics(cv_df)
        model_mape = float(pm["mape"].mean() * 100)
    except Exception as e:
        logging.warning(f"[{commodity}] Cross-validation failed: {e}. Defaulting to standard chronological split.")
        split = int(len(df) * 0.8)
        train, test = df.iloc[:split], df.iloc[split:]
        model2 = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                         daily_seasonality=False, changepoint_prior_scale=0.15,
                         seasonality_mode="multiplicative")
        model2.fit(train)
        pred = model2.predict(test[["ds"]])
        pred["yhat"] = pred["yhat"].clip(lower=PRICE_FLOOR_GHS)
        actual = test["y"].values
        predicted = pred["yhat"].values
        errors = np.abs((actual - predicted) / np.where(actual == 0, np.nan, actual))
        model_mape = float(np.nanmean(errors) * 100)

    return model_mape, baseline

def main():
    con = duckdb.connect(DB_PATH)
    logging.info(f"Database connection initialized: {DB_PATH}")

    all_forecasts = []

    for commodity in STAPLES:
        df = get_national_monthly(con, commodity)

        if len(df) < MIN_TRAINING_MONTHS:
            logging.warning(f"Skipping {commodity}: Insufficient historical data.")
            continue

        model_mape, base_mape = evaluate_mape(commodity, df)
        logging.info(f"Evaluated {commodity}: Model MAPE = {model_mape:.1f}% | Baseline = {base_mape:.1f}%")

        forecast_df = fit_and_forecast(commodity, df)
        forecast_df["mape_score"] = model_mape
        forecast_df["baseline_mape_score"] = base_mape
        all_forecasts.append(forecast_df)

    if not all_forecasts:
        logging.error("Pipeline failure: No commodities met minimum data thresholds.")
        con.close()
        return

    combined = pd.concat(all_forecasts, ignore_index=True)

    logging.info("Persisting forecast matrix to data warehouse (fact_price_forecasts)...")
    con.execute("DROP TABLE IF EXISTS fact_price_forecasts")
    con.execute("""
        CREATE TABLE fact_price_forecasts (
            commodity_name       VARCHAR,
            market_name          VARCHAR,
            record_date          DATE,
            predicted_price_ghs  DOUBLE,
            lower_bound_ghs      DOUBLE,
            upper_bound_ghs      DOUBLE,
            mape_score           DOUBLE,
            baseline_mape_score  DOUBLE,
            is_forecast          BOOLEAN
        )
    """)
    con.register("forecast_temp", combined)
    con.execute("INSERT INTO fact_price_forecasts SELECT * FROM forecast_temp")

    total = con.execute("SELECT COUNT(*) FROM fact_price_forecasts").fetchone()[0]
    logging.info(f"Pipeline executed successfully. Forecast table populated with {total:,} records.")

    con.close()

if __name__ == "__main__":
    main()
