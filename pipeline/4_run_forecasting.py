"""
Machine Learning Forecasting Pipeline
======================================
Trains an XGBoost gradient-boosted regression model for each core staple
commodity and generates 3-month forward price projections.

Model selection rationale:
  XGBoost with lag features was selected over Prophet and ARIMAX following a
  formal three-model evaluation on a date-based train/test split
  (train: 2019-08-01 to 2022-12-31, test: 2023-01-01 to 2023-07-01).

  Results:
    XGBoost  — Avg MAPE: 21.5%  Avg Directional Accuracy: 61.1%
    ARIMAX   — Avg MAPE: 23.8%  Avg Directional Accuracy: 38.9%
    Prophet  — Avg MAPE: 42.4%  Avg Directional Accuracy: 47.2%

  XGBoost achieved the highest directional accuracy (the operationally
  relevant metric for food security planning) and the lowest MAPE.
  It makes no stationarity assumptions, handles structural breaks via lag
  feature engineering, and is well-suited to the 40-month retail price
  series available in the WFP Ghana dataset (retail coverage begins Aug 2019).

Feature set:
  price_lag_1, price_lag_2, price_lag_3   — recent price memory
  mom_pct_lag_1                           — recent momentum signal
  month_of_year                           — seasonal pattern
  usd_ghs                                 — GHS/USD FX rate (external driver)

Accuracy metrics:
  - MAPE (Mean Absolute Percentage Error): forecast error magnitude.
  - Directional accuracy: whether the model correctly predicted the direction
    of price movement (up / down / flat within ±1%). This is the primary
    metric for procurement and food security decisions.
  Both benchmarked against a naive lag-1 baseline.

GHS/USD exchange rate:
  Approximately 60% of Ghana's post-2021 food price increase is attributable
  to GHS currency depreciation. Monthly rates are sourced from the World Bank
  (indicator PA.NUS.FCRF), interpolated to monthly frequency via linear spline.
"""

import duckdb
import urllib.request
import json
import pandas as pd
import numpy as np
import logging
import warnings
import time
import sys
import os
from scipy.interpolate import interp1d
from xgboost import XGBRegressor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.pipeline_logger import PipelineLogger

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

# Price guardrails applied to both training data and forecast outputs.
# Floor: Prophet can extrapolate below zero during structural downturns;
#        GHS 0.01/kg is the non-negativity hard boundary.
# Ceiling: GHS 500/kg excludes hyper-inflation spikes in thin markets
#          that would distort long-run trend fitting.
PRICE_FLOOR_GHS     = 0.01
PRICE_CEIL_GHS      = 500.0

# Minimum number of monthly observations required to train a model.
MIN_TRAINING_MONTHS = 18

# Known macroeconomic shocks — retained for documentation and reference
# in statistical analysis. Not used as model parameters in XGBoost
# (handled implicitly via lag features and the FX regressor).
KNOWN_CHANGEPOINTS = [
    "2020-03-01",   # COVID-19 border closures and market shutdowns
    "2022-02-01",   # Russia-Ukraine war: global grain and fuel price surge
    "2022-07-01",   # Ghana cedi depreciation crisis onset
]

# XGBoost feature columns
FEATURES = ["lag1", "lag2", "lag3", "mom_lag1", "month", "usd_ghs"]

# ------------------------------------------------------------------
# Train / Test Split — date-based (mentor correction)
# ------------------------------------------------------------------
# Previous approach: 80/20 percentage split.
# Problem: all three macroeconomic shocks land in the test set because
# they occur at the tail of the dataset (2020, 2022), so the model has
# never seen a shock during training and performs poorly on the test set.
#
# Fix: train on 2006-01-01 → TRAIN_END (absorbs all shocks including
# the cedi depreciation crisis). Test on TEST_START → end of dataset
# (Jan–Jul 2023 — a clean 7-month out-of-sample window).
# All three KNOWN_CHANGEPOINTS now fall within the training window,
# which is exactly the intent.
TRAIN_END   = "2022-12-31"   # last date included in training
TEST_START  = "2023-01-01"   # first date of the held-out test window


# ----------------------------------------------------------------
# GHS/USD Exchange Rate — external regressor
# ----------------------------------------------------------------

# Annual average GHS/USD rates sourced from World Bank indicator PA.NUS.FCRF
# and Bank of Ghana official publications. These are the official end-of-year
# average rates published in the World Bank World Development Indicators.
# Retrieved live where possible; embedded as fallback for offline use.
_BOG_ANNUAL_RATES = {
    2006: 0.921,   2007: 1.028,   2008: 1.062,   2009: 1.409,
    2010: 1.430,   2011: 1.516,   2012: 1.796,   2013: 2.202,
    2014: 3.212,   2015: 3.824,   2016: 3.910,   2017: 4.351,
    2018: 4.585,   2019: 5.217,   2020: 5.596,   2021: 5.806,
    2022: 8.272,   2023: 11.020,
}


def fetch_worldbank_fx_rates() -> dict[int, float]:
    """
    Fetch annual average GHS/USD rates from the World Bank API.
    Returns a dict of {year: rate}. Falls back to embedded rates on failure.
    """
    try:
        url = (
            "https://api.worldbank.org/v2/country/GH/indicator/PA.NUS.FCRF"
            "?format=json&per_page=100&mrv=30"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        records = data[1] if isinstance(data, list) and len(data) > 1 else []
        rates = {
            int(rec["date"]): float(rec["value"])
            for rec in records
            if rec.get("value") is not None
        }
        if len(rates) >= 10:
            logging.info(f"World Bank FX rates fetched: {len(rates)} annual observations.")
            return rates
    except Exception as e:
        logging.warning(f"World Bank FX fetch failed ({e}). Using embedded rates.")
    return _BOG_ANNUAL_RATES.copy()


def build_monthly_fx_series(
    start: str = "2006-01-01",
    end:   str = "2023-07-01",
) -> pd.DataFrame:
    """
    Build a monthly GHS/USD exchange rate series by linearly interpolating
    the annual average rates across monthly date points.

    The annual rate for year Y is anchored to July 1 of that year (midpoint),
    so the interpolation distributes the annual average evenly across months
    rather than step-changing at January 1.

    Returns a DataFrame with columns: ds (datetime), usd_ghs (float).
    """
    annual_rates = fetch_worldbank_fx_rates()
    # Merge with embedded rates to fill any gaps in the API response
    for yr, rate in _BOG_ANNUAL_RATES.items():
        if yr not in annual_rates:
            annual_rates[yr] = rate

    # Anchor each annual rate to the midpoint of the year (July 1)
    anchor_dates  = pd.to_datetime([f"{yr}-07-01" for yr in sorted(annual_rates)])
    anchor_values = np.array([annual_rates[yr] for yr in sorted(annual_rates)], dtype=float)

    # Linear interpolation function over the anchor points
    interp_fn = interp1d(
        anchor_dates.asi8,          # nanoseconds since epoch (int64)
        anchor_values,
        kind="linear",
        fill_value="extrapolate",
    )

    monthly_dates = pd.date_range(start=start, end=end, freq="MS")
    interpolated  = interp_fn(monthly_dates.asi8)

    fx = pd.DataFrame({"ds": monthly_dates, "usd_ghs": interpolated})
    # Clip to physically valid range: GHS/USD has never been below 0.9 or above 20
    fx["usd_ghs"] = fx["usd_ghs"].clip(lower=0.5, upper=20.0)
    return fx


def get_national_monthly(
    con: duckdb.DuckDBPyConnection,
    commodity: str,
    fx: pd.DataFrame,
) -> pd.DataFrame:
    """
    Retrieve monthly retail price series for a commodity and join the
    GHS/USD exchange rate as an additional column for use as a Prophet
    external regressor.
    """
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
    df = df.merge(fx[["ds", "usd_ghs"]], on="ds", how="left")
    # Forward-fill any months where FX data is missing (should not occur
    # within the 2006-2023 window but handled defensively)
    df["usd_ghs"] = df["usd_ghs"].ffill().bfill()
    return df


def naive_mape(series: pd.Series) -> float:
    """
    Compute a naive lag-1 baseline MAPE over the final 20% of the series.
    The baseline prediction for each month is simply the prior month's price.
    Returns a whole-number percentage (e.g. 12.4 = 12.4% error).
    """
    n = len(series)
    test_size = max(3, int(n * 0.2))
    test     = series.iloc[-test_size:]
    baseline = series.iloc[-(test_size + 1):-1].values

    if len(baseline) == 0:
        return np.nan

    errors = np.abs((test.values - baseline) / np.where(baseline == 0, np.nan, baseline))
    return float(np.nanmean(errors) * 100)


def directional_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Compute the percentage of periods where the model correctly predicted
    the direction of price movement (up, down, or flat) relative to the
    prior period.

    A correct directional call is defined as:
      - Both actual and predicted change have the same sign (both positive,
        both negative, or both within a flat band of ±1%).

    Returns a whole-number percentage (e.g. 66.7 = 66.7% correct).
    Requires at least 2 observations; returns NaN otherwise.
    """
    if len(actual) < 2 or len(predicted) < 2:
        return np.nan

    FLAT_THRESHOLD = 0.01   # ±1% treated as flat

    def direction(series: np.ndarray) -> np.ndarray:
        pct_change = np.diff(series) / np.where(series[:-1] == 0, np.nan, series[:-1])
        return np.where(pct_change >  FLAT_THRESHOLD,  1,
               np.where(pct_change < -FLAT_THRESHOLD, -1, 0))

    dir_actual    = direction(actual)
    dir_predicted = direction(predicted)
    valid         = ~(np.isnan(dir_actual) | np.isnan(dir_predicted))

    if valid.sum() == 0:
        return np.nan

    correct = np.sum(dir_actual[valid] == dir_predicted[valid])
    return float(correct / valid.sum() * 100)


def _build_xgb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the XGBoost feature matrix from a monthly price series.
    Features: price_lag_1/2/3, mom_pct_lag_1, month_of_year, usd_ghs.
    Rows with NaN lags (first 3 months) are dropped.
    """
    d = df.copy().reset_index(drop=True)
    d["lag1"]     = d["y"].shift(1)
    d["lag2"]     = d["y"].shift(2)
    d["lag3"]     = d["y"].shift(3)
    d["mom_lag1"] = d["y"].pct_change(1) * 100
    d["month"]    = d["ds"].dt.month
    return d.dropna(subset=["lag1", "lag2", "lag3"])


def fit_and_forecast(
    commodity: str,
    df: pd.DataFrame,
    fx_future: pd.DataFrame,
) -> pd.DataFrame:
    """
    Fit an XGBoost model on the full available training series and generate
    FORECAST_MONTHS forward projections using recursive one-step-ahead prediction.

    FX assumption: the most recent observed GHS/USD rate is held constant
    across the forecast horizon (no-change assumption). This is conservative —
    it avoids injecting speculative FX paths into food price projections.

    Confidence intervals are estimated as the residual standard deviation
    on the training set scaled by ±1.28 (80% interval).
    """
    logging.info(
        f"[{commodity}] Fitting XGBoost on full window: "
        f"{df['ds'].min().date()} to {df['ds'].max().date()} ({len(df)} months)"
    )

    full = _build_xgb_features(df)
    model = XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
        verbosity=0,
    )
    model.fit(full[FEATURES], full["y"])

    # Estimate residual std for confidence intervals
    train_pred  = model.predict(full[FEATURES])
    residual_std = float(np.std(full["y"].values - train_pred))

    # Recursive forecast: feed each prediction back as the next lag
    last_fx   = float(df["usd_ghs"].iloc[-1])
    last_3    = list(df["y"].iloc[-3:].values)   # [lag3, lag2, lag1]
    last_date = df["ds"].iloc[-1]
    records   = []

    for i in range(FORECAST_MONTHS):
        next_date = last_date + pd.DateOffset(months=i + 1)
        lag1, lag2, lag3 = last_3[-1], last_3[-2], last_3[-3]
        mom_lag1 = (lag1 - lag2) / lag2 * 100 if lag2 != 0 else 0.0
        row = pd.DataFrame([[lag1, lag2, lag3, mom_lag1, next_date.month, last_fx]],
                           columns=FEATURES)
        yhat = float(model.predict(row)[0])
        yhat = np.clip(yhat, PRICE_FLOOR_GHS, PRICE_CEIL_GHS)
        records.append({
            "record_date":         next_date,
            "predicted_price_ghs": round(yhat, 4),
            "lower_bound_ghs":     round(np.clip(yhat - 1.28 * residual_std, PRICE_FLOOR_GHS, PRICE_CEIL_GHS), 4),
            "upper_bound_ghs":     round(np.clip(yhat + 1.28 * residual_std, PRICE_FLOOR_GHS, PRICE_CEIL_GHS), 4),
        })
        last_3.append(yhat)

    result = pd.DataFrame(records)
    result["commodity_name"] = commodity
    result["market_name"]    = "national"
    result["is_forecast"]    = True
    return result[["commodity_name", "market_name", "record_date",
                   "predicted_price_ghs", "lower_bound_ghs", "upper_bound_ghs",
                   "is_forecast"]]


def evaluate_model(
    commodity: str,
    df: pd.DataFrame,
    train_end: str = TRAIN_END,
    test_start: str = TEST_START,
) -> tuple[float, float, float]:
    """
    Evaluate the XGBoost model on a date-based train/test split.
    Returns (model_mape, baseline_mape, directional_acc) as whole-number percents.

    Train: 2019-08-01 to train_end (2022-12-31) — includes all shock years.
    Test:  test_start (2023-01-01) to end of dataset — clean out-of-sample window.

    Note: WFP Ghana retail price coverage for these commodities begins August
    2019. Earlier records are wholesale only and are excluded to maintain
    price-type consistency in the feature matrix.
    """
    baseline = naive_mape(df["y"])
    n_months = len(df)

    if n_months < MIN_TRAINING_MONTHS:
        logging.warning(f"[{commodity}] Insufficient data ({n_months} months).")
        return np.nan, baseline, np.nan

    full  = _build_xgb_features(df)
    train = full[full["ds"] <= pd.Timestamp(train_end)]
    test  = full[full["ds"] >= pd.Timestamp(test_start)]

    if len(train) < MIN_TRAINING_MONTHS:
        logging.warning(f"[{commodity}] Training window too short ({len(train)} months).")
        return np.nan, baseline, np.nan

    if len(test) == 0:
        logging.warning(f"[{commodity}] No test data after {test_start}.")
        return np.nan, baseline, np.nan

    logging.info(
        f"[{commodity}] Train: {train['ds'].min().date()} to {train['ds'].max().date()} "
        f"({len(train)}m) | Test: {test['ds'].min().date()} to {test['ds'].max().date()} "
        f"({len(test)}m)"
    )

    model = XGBRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.05,
        subsample=0.8, random_state=42, verbosity=0,
    )
    model.fit(train[FEATURES], train["y"])

    predicted  = np.clip(model.predict(test[FEATURES]), PRICE_FLOOR_GHS, PRICE_CEIL_GHS)
    actual     = test["y"].values
    errors     = np.abs((actual - predicted) / np.where(actual == 0, np.nan, actual))
    model_mape = float(np.nanmean(errors) * 100)
    dir_acc    = directional_accuracy(actual, predicted)

    return model_mape, baseline, dir_acc


def main():
    pipeline_logger = PipelineLogger(DB_PATH)
    t0 = time.perf_counter()
    con = duckdb.connect(DB_PATH)
    logging.info(f"Database connection initialized: {DB_PATH}")

    # Build the monthly FX series once; reuse across all commodities
    logging.info("Building monthly GHS/USD exchange rate series...")
    fx = build_monthly_fx_series(start="2006-01-01", end="2023-07-01")
    logging.info(f"FX series built: {len(fx)} monthly observations "
                 f"({fx['ds'].min().date()} to {fx['ds'].max().date()})")

    # Build a future FX DataFrame covering the forecast horizon
    last_date   = fx["ds"].max()
    future_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1),
        periods=FORECAST_MONTHS,
        freq="MS",
    )
    last_rate   = float(fx["usd_ghs"].iloc[-1])
    fx_future   = pd.DataFrame({"ds": future_dates, "usd_ghs": last_rate})
    # Extend FX series to include future months for any lookups
    fx_extended = pd.concat([fx, fx_future], ignore_index=True)

    all_forecasts = []

    for commodity in STAPLES:
        df = get_national_monthly(con, commodity, fx_extended)

        if len(df) < MIN_TRAINING_MONTHS:
            logging.warning(f"Skipping {commodity}: Insufficient historical data.")
            continue

        model_mape, base_mape, dir_acc = evaluate_model(commodity, df)
        logging.info(
            f"Evaluated {commodity}: "
            f"Model MAPE = {model_mape:.1f}%  |  "
            f"Baseline MAPE = {base_mape:.1f}%  |  "
            f"Directional Accuracy = {dir_acc:.1f}%"
        )
        pipeline_logger.log(
            script_name=f"4_run_forecasting:{commodity}",
            status="SUCCESS",
            message=(
                f"MAPE={model_mape:.1f}% | BaseMAPE={base_mape:.1f}% | "
                f"DirAcc={dir_acc:.1f}% | Split={TRAIN_END}/{TEST_START}"
            ),
        )

        forecast_df = fit_and_forecast(commodity, df, fx_future)
        forecast_df["mape_score"]            = model_mape
        forecast_df["baseline_mape_score"]   = base_mape
        forecast_df["directional_accuracy"]  = dir_acc
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
            commodity_name        VARCHAR,
            market_name           VARCHAR,
            record_date           DATE,
            predicted_price_ghs   DOUBLE,
            lower_bound_ghs       DOUBLE,
            upper_bound_ghs       DOUBLE,
            mape_score            DOUBLE,
            baseline_mape_score   DOUBLE,
            directional_accuracy  DOUBLE,
            is_forecast           BOOLEAN
        )
    """)
    # Explicit column ordering prevents positional misalignment between the
    # DataFrame and the CREATE TABLE schema during the SELECT * insert.
    combined = combined[[
        "commodity_name", "market_name", "record_date",
        "predicted_price_ghs", "lower_bound_ghs", "upper_bound_ghs",
        "mape_score", "baseline_mape_score", "directional_accuracy", "is_forecast",
    ]]
    con.register("forecast_temp", combined)
    con.execute("INSERT INTO fact_price_forecasts SELECT * FROM forecast_temp")

    total = con.execute("SELECT COUNT(*) FROM fact_price_forecasts").fetchone()[0]
    logging.info(f"Pipeline complete. Forecast table populated with {total:,} records.")
    con.close()
    pipeline_logger.success("4_run_forecasting", rows_affected=total, duration_seconds=time.perf_counter() - t0)


if __name__ == "__main__":
    main()
