"""XGBoost inference script for MarketPulse Ghana price forecasting.

Reads the latest mart_commodity_monthly actuals from DuckDB, engineers
lag/rolling features, runs the pre-trained XGBoost model, and writes
3-month-ahead point forecasts with 95% confidence intervals into the
mart_maize_forecasts table in both DuckDB files.

Usage:
    python scripts/forecast_maize.py                    # defaults to Maize
    python scripts/forecast_maize.py --commodity Maize  # explicit

Extend: add new <commodity>_wholesale.json model binaries to
archive/ml/models/ and the script will pick them up automatically
when --commodity is set.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import duckdb
import xgboost as xgb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("forecast_maize")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "agri_ghana.duckdb"
UI_DB_PATH = REPO_ROOT / "ui" / "sources" / "agri_ghana" / "agri_ghana.duckdb"
ML_DIR = REPO_ROOT / "archive" / "ml"
MODELS_DIR = ML_DIR / "models"
FEATURE_CONFIG_PATH = ML_DIR / "data" / "feature_config.json"

# Residual std estimated from walk-forward CV: best_cv_rmse_log = 0.09948 (log space)
# In price space, 95% CI half-width ≈ 1.96 * residual_std_ghs
# Using conservative 12% of predicted price as CI half-width in GHS/kg
CI_HALF_WIDTH_FRACTION = 0.12


# ---------------------------------------------------------------------------
# Feature engineering — mirrors the training notebook exactly
# ---------------------------------------------------------------------------

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build lag / rolling / calendar features from a sorted price series."""
    df = df.copy()
    # Ensure date column is uniform datetime64 so sort and dt accessors work
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["log_price"] = np.log1p(df["median_price_ghs_per_kg"])

    # Lag features (log-space)
    for lag in [1, 2, 3, 6, 12]:
        df[f"log_lag_{lag}"] = df["log_price"].shift(lag)

    # Rolling means (log-space)
    for window in [3, 6, 12]:
        df[f"log_roll_mean_{window}"] = (
            df["log_price"].shift(1).rolling(window).mean()
        )

    # Rolling std (raw price)
    df["roll_std_3"] = (
        df["median_price_ghs_per_kg"].shift(1).rolling(3).std()
    )

    # Rename markets_reporting → n_markets to match training feature names
    if "markets_reporting" in df.columns and "n_markets" not in df.columns:
        df["n_markets"] = df["markets_reporting"]

    # Calendar / seasonal encodings
    df["month"] = pd.to_datetime(df["date"]).dt.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["quarter"] = pd.to_datetime(df["date"]).dt.quarter
    df["year"] = pd.to_datetime(df["date"]).dt.year

    # Percentage changes
    df["pct_change_1m"] = df["median_price_ghs_per_kg"].pct_change(1)
    df["pct_change_12m"] = df["median_price_ghs_per_kg"].pct_change(12)

    return df


# ---------------------------------------------------------------------------
# Multi-step recursive forecast
# ---------------------------------------------------------------------------

def forecast_multistep(
    model: xgb.Booster,
    feature_names: list[str],
    history: pd.DataFrame,
    horizon: int,
    commodity: str,
) -> list[dict]:
    """Generate horizon-step-ahead forecasts by recursive single-step prediction."""
    df = history.copy()
    forecasts = []

    forecast_date = pd.Timestamp(df["date"].max())

    for h in range(1, horizon + 1):
        # Build features from the current tail of history
        df_feat = engineer_features(df)
        last_row = df_feat.iloc[-1]

        # Check required features exist
        missing = [f for f in feature_names if f not in df_feat.columns]
        if missing:
            raise ValueError(f"Missing features for horizon {h}: {missing}")

        X = last_row[feature_names].values.reshape(1, -1)
        dmatrix = xgb.DMatrix(X, feature_names=feature_names)

        log_pred = model.predict(dmatrix)[0]
        pred_price = float(np.expm1(log_pred))

        # 95% CI: ±12% of predicted price (conservative, based on CV RMSE)
        ci_half = pred_price * CI_HALF_WIDTH_FRACTION
        lower = max(0.0, pred_price - ci_half * 1.96)
        upper = pred_price + ci_half * 1.96

        # Target date = last actual date + h months
        target_date = forecast_date + pd.DateOffset(months=h)
        target_date = target_date.replace(day=1)

        forecasts.append({
            "forecast_date": forecast_date.date(),
            "target_date": target_date.date(),
            "horizon_months": h,
            "commodity": commodity,
            "predicted_price_ghs_per_kg": round(pred_price, 4),
            "lower_ci_95": round(lower, 4),
            "upper_ci_95": round(upper, 4),
            "model_version": f"xgboost_v1_walkforward",
        })

        # Append synthetic next-month row for recursive forecasting
        next_row = pd.DataFrame([{
            "date": pd.Timestamp(target_date),
            "median_price_ghs_per_kg": pred_price,
            "markets_reporting": df["markets_reporting"].iloc[-1],
        }])
        df = pd.concat([df, next_row], ignore_index=True)

    return forecasts


# ---------------------------------------------------------------------------
# DuckDB write helpers
# ---------------------------------------------------------------------------

def write_forecasts_to_db(db_path: Path, forecasts: list[dict], run_id: str) -> None:
    """Write mart_maize_forecasts table and log to meta_pipeline_runs."""
    con = duckdb.connect(str(db_path))
    started_at = datetime.datetime.now(datetime.timezone.utc)
    t0 = time.perf_counter()

    try:
        # Create / replace table
        con.execute("""
            CREATE OR REPLACE TABLE mart_maize_forecasts (
                forecast_date      DATE    NOT NULL,
                target_date        DATE    NOT NULL,
                horizon_months     INTEGER NOT NULL,
                commodity          VARCHAR NOT NULL,
                predicted_price_ghs_per_kg DOUBLE NOT NULL,
                lower_ci_95        DOUBLE  NOT NULL,
                upper_ci_95        DOUBLE  NOT NULL,
                model_version      VARCHAR NOT NULL
            )
        """)

        for f in forecasts:
            con.execute(
                """
                INSERT INTO mart_maize_forecasts VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    f["forecast_date"],
                    f["target_date"],
                    f["horizon_months"],
                    f["commodity"],
                    f["predicted_price_ghs_per_kg"],
                    f["lower_ci_95"],
                    f["upper_ci_95"],
                    f["model_version"],
                ],
            )

        duration_s = time.perf_counter() - t0
        completed_at = datetime.datetime.now(datetime.timezone.utc)

        # Audit log
        con.execute("""
            CREATE TABLE IF NOT EXISTS meta_pipeline_runs (
                run_id VARCHAR,
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                pipeline_step VARCHAR,
                status VARCHAR,
                records_affected BIGINT,
                execution_time_s DOUBLE,
                error_details VARCHAR
            )
        """)
        con.execute(
            """
            INSERT INTO meta_pipeline_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                started_at,
                completed_at,
                "xgboost_forecast",
                "SUCCESS",
                len(forecasts),
                round(duration_s, 3),
                None,
            ],
        )

        logger.info(
            "Wrote %d forecast rows to %s (%.2fs)", len(forecasts), db_path, duration_s
        )
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_forecast(commodity: str = "Maize") -> None:
    """Full forecast pipeline: load model → fetch actuals → predict → write."""
    run_id = f"forecast_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    logger.info("Starting forecast pipeline (Run ID: %s, commodity: %s)", run_id, commodity)

    # Resolve model path — commodity-agnostic naming convention
    model_slug = commodity.lower().replace(" ", "_").replace("(", "").replace(")", "")
    model_path = MODELS_DIR / f"xgboost_{model_slug}_wholesale.json"

    if not model_path.exists():
        logger.warning(
            "No trained model found for commodity '%s' at %s — skipping.",
            commodity,
            model_path,
        )
        logger.info(
            "To add a new commodity, train a model and save it as: %s", model_path
        )
        return

    # Load feature config
    with open(FEATURE_CONFIG_PATH) as f:
        feature_config = json.load(f)
    feature_names: list[str] = feature_config["features"]
    logger.info("Using %d features: %s", len(feature_names), feature_names)

    # Load XGBoost model
    model = xgb.Booster()
    model.load_model(str(model_path))
    logger.info("Loaded model from %s", model_path)

    # Read historical actuals from root DuckDB
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    try:
        df = con.execute("""
            SELECT
                date,
                median_price_ghs_per_kg,
                markets_reporting
            FROM mart_commodity_monthly
            WHERE commodity = ?
              AND price_type = 'Wholesale'
              AND raw_unit = '100 KG'
              AND median_price_ghs_per_kg IS NOT NULL
            ORDER BY date ASC
        """, [commodity]).df()
    finally:
        con.close()

    if len(df) < 24:
        raise RuntimeError(
            f"Insufficient history: need ≥ 24 months, got {len(df)} for {commodity}."
        )

    logger.info(
        "Loaded %d months of history (%s → %s)",
        len(df),
        df["date"].min(),
        df["date"].max(),
    )

    # Generate 3-month-ahead forecasts
    forecasts = forecast_multistep(
        model=model,
        feature_names=feature_names,
        history=df,
        horizon=3,
        commodity=commodity,
    )

    for f in forecasts:
        logger.info(
            "  Horizon +%dm → %s: %.4f GHS/kg [%.4f – %.4f]",
            f["horizon_months"],
            f["target_date"],
            f["predicted_price_ghs_per_kg"],
            f["lower_ci_95"],
            f["upper_ci_95"],
        )

    # Write to both DuckDB files
    write_forecasts_to_db(DEFAULT_DB_PATH, forecasts, run_id)
    if UI_DB_PATH.exists():
        write_forecasts_to_db(UI_DB_PATH, forecasts, run_id)
        logger.info("Synced forecasts to UI DuckDB at %s", UI_DB_PATH)
    else:
        logger.warning(
            "UI DuckDB not found at %s — only root DB was updated.", UI_DB_PATH
        )

    logger.info("Forecast pipeline complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run XGBoost price forecasting for a MarketPulse Ghana commodity."
    )
    parser.add_argument(
        "--commodity",
        default="Maize",
        help="Commodity to forecast (default: Maize). Must have a trained model in archive/ml/models/.",
    )
    args = parser.parse_args()
    run_forecast(commodity=args.commodity)


if __name__ == "__main__":
    main()
