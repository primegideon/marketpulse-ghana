"""
MarketPulse Ghana — ML Forecasting Pipeline
============================================
Uses Meta Prophet to generate 30-day forward price predictions
for Ghana's core staple crops from stg_wfp_prices.

Fixes applied vs. previous version:
  - Trains on data through 2023-07 (the actual last month in dataset)
  - Generates real future forecasts (is_forecast=True rows)
  - Forecasts at national level (aggregated across all regions)
  - Uses correct stg_wfp_prices with fixed KG conversions
  - Writes market_name='national' to align with plan schema
  - Evaluates with walk-forward cross-validation, not static split
  - Records both model MAPE and naive baseline MAPE for transparency
"""

import duckdb
import pandas as pd
import numpy as np
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import warnings
warnings.filterwarnings("ignore")

# ----------------------------------------------------------------
# Config
# ----------------------------------------------------------------
DB_PATH = "agri_ghana.duckdb"

# Staple commodities to forecast (plan specifies 5 groups)
STAPLES = [
    "maize",
    "cassava",
    "rice (local)",
    "rice (imported)",
    "plantains (apentu)",
    "tomatoes (local)",
]

# Forecast horizon: 3 months ahead at monthly resolution
# (Monthly data → monthly forecasts. "30-day" in the plan = 1 month ahead;
# we do 3 months to give the dashboard a visible trend window.)
FORECAST_MONTHS = 3

# Guardrails from plan
PRICE_FLOOR_GHS  = 0.01   # Non-negativity floor
PRICE_CEIL_GHS   = 500.0  # Macro outlier ceiling

# Minimum months of data required to train a model
MIN_TRAINING_MONTHS = 18


def get_national_monthly(con: duckdb.DuckDBPyConnection, commodity: str) -> pd.DataFrame:
    """
    Returns a monthly time series of national average price per KG for
    the given commodity, across all regions and markets.
    Only includes months with >= 3 observations for reliability.
    """
    df = con.execute(f"""
        SELECT
            DATE_TRUNC('month', record_date)::DATE AS ds,
            ROUND(AVG(price_per_kg_ghs), 4) AS y
        FROM stg_wfp_prices
        WHERE commodity_name = '{commodity}'
          AND price_per_kg_ghs BETWEEN 0.05 AND {PRICE_CEIL_GHS}
        GROUP BY DATE_TRUNC('month', record_date)::DATE
        HAVING COUNT(*) >= 3
        ORDER BY ds
    """).fetchdf()
    df["ds"] = pd.to_datetime(df["ds"])
    return df


def naive_mape(series: pd.Series) -> float:
    """
    Naive baseline: predict that next month = this month (last-value carry-forward).
    Calculates MAPE over the last 20% of the series.
    Returns MAPE as a percentage.
    """
    n = len(series)
    test_size = max(3, int(n * 0.2))
    test = series.iloc[-test_size:]
    baseline = series.iloc[-(test_size + 1):-1].values  # shift by 1

    if len(baseline) == 0:
        return np.nan

    errors = np.abs((test.values - baseline) / np.where(baseline == 0, np.nan, baseline))
    return float(np.nanmean(errors) * 100)


def fit_and_forecast(commodity: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Trains Prophet on monthly data, generates 3-month forward forecasts.
    Returns ONLY the future rows (is_forecast=True).

    Key design decisions:
    - freq='MS' (month start): we train on monthly data, so we must
      forecast at monthly resolution. Using daily freq with monthly
      training data causes Prophet to apply yearly seasonality at daily
      granularity, creating unrealistic intra-month swings.
    - include_history=False: ensures ALL returned rows are future dates,
      making is_forecast=True universally correct and unambiguous.
    - periods=FORECAST_MONTHS: 3 months ahead gives a visible forecast
      window on the dashboard while staying within reliable model range.
    """
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.15,
        seasonality_mode="multiplicative",
    )
    model.fit(df)

    # Forecast at monthly resolution — only future rows
    future = model.make_future_dataframe(
        periods=FORECAST_MONTHS,
        freq="MS",          # Month Start: aligns with monthly training data
        include_history=False,  # Return ONLY future dates, no historical rows
    )
    forecast = model.predict(future)

    result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    result["is_forecast"] = True  # All rows are guaranteed future dates

    # Apply price guardrails
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
    """
    Walk-forward MAPE evaluation using Prophet's cross_validation.
    Falls back to a simple 80/20 split if insufficient data.
    Returns (model_mape, baseline_mape).
    """
    baseline = naive_mape(df["y"])

    n_months = len(df)
    if n_months < MIN_TRAINING_MONTHS:
        print(f"    [{commodity}] Too few months ({n_months}) for cross-validation. Skipping MAPE.")
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
        print(f"    [{commodity}] Cross-validation failed: {e}. Using simple split.")
        # Fallback: fit on 80%, test on 20%
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
    print(f"Connected to {DB_PATH}.\n")
    print(f"Staples to forecast: {STAPLES}\n")

    all_forecasts = []
    mape_records  = []

    for commodity in STAPLES:
        print(f"Processing: {commodity}")
        df = get_national_monthly(con, commodity)

        if len(df) < MIN_TRAINING_MONTHS:
            print(f"  Skipping — only {len(df)} months of data (need {MIN_TRAINING_MONTHS})")
            continue

        print(f"  Training data: {df['ds'].min().date()} to {df['ds'].max().date()} ({len(df)} months)")

        # 1. Evaluate accuracy
        model_mape, base_mape = evaluate_mape(commodity, df)
        print(f"  MAPE: model={model_mape:.1f}%  naive_baseline={base_mape:.1f}%")
        mape_records.append({
            "commodity_name":    commodity,
            "mape_score":        model_mape,
            "baseline_mape_score": base_mape,
        })

        # 2. Fit final model on ALL data and forecast 30 days ahead
        forecast_df = fit_and_forecast(commodity, df)
        n_future = forecast_df["is_forecast"].sum()
        print(f"  Generated {len(forecast_df)} total rows ({n_future} future forecast rows)")

        # Attach MAPE scores
        forecast_df["mape_score"]         = model_mape
        forecast_df["baseline_mape_score"] = base_mape
        all_forecasts.append(forecast_df)

    if not all_forecasts:
        print("No commodities had enough data. Exiting.")
        con.close()
        return

    combined = pd.concat(all_forecasts, ignore_index=True)

    # Show summary of future forecasts
    future_rows = combined[combined["is_forecast"] == True]
    print(f"\n=== Summary: {len(future_rows)} actual future forecast rows ===")
    print(future_rows[["commodity_name","record_date","predicted_price_ghs",
                        "lower_bound_ghs","upper_bound_ghs"]].to_string(index=False))

    # Write to DuckDB — DROP and recreate fact_price_forecasts
    print("\nWriting fact_price_forecasts to DuckDB...")
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
    future_total = con.execute("SELECT COUNT(*) FROM fact_price_forecasts WHERE is_forecast=TRUE").fetchone()[0]
    print(f"fact_price_forecasts written: {total:,} rows total, {future_total} future forecasts")

    # Verify latest forecasted prices make sense
    print("\n=== Latest predicted prices per commodity ===")
    check = con.execute("""
        SELECT commodity_name, record_date,
               ROUND(predicted_price_ghs, 2) as predicted_ghs,
               ROUND(lower_bound_ghs, 2) as lower,
               ROUND(upper_bound_ghs, 2) as upper,
               is_forecast
        FROM fact_price_forecasts
        WHERE is_forecast = TRUE
        ORDER BY commodity_name, record_date
        LIMIT 30
    """).fetchdf()
    print(check.to_string(index=False))

    con.close()
    print("\nML pipeline complete.")


if __name__ == "__main__":
    main()
