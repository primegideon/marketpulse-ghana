"""
Model Evaluation Report
========================
Evaluates three candidate time-series models against the same corrected
date-based train/test split (train: 2006-01-01 → 2022-12-31,
test: 2023-01-01 → 2023-07-01) for each core staple commodity.

Candidate models:
    1. Prophet (current) — additive decomposition with GHS/USD regressor
    2. ARIMAX             — SARIMAX(p,1,q) with GHS/USD as exogenous variable;
                           order selected by AIC minimisation over p,q in {0,1,2}
    3. XGBoost           — gradient boosted trees with lag features + month + FX rate

Decision framework (from mentor-sprint-plan.md):
    - Prophet directional accuracy >= 60% majority → retain / fine-tune Prophet
    - Strong FX correlation + non-stationary (confirmed by ADF) → ARIMAX preferred
    - Non-stationary + weak FX → XGBoost with lag features

Outputs:
    outputs/model_comparison.png   — grouped bar chart: MAPE + directional
                                     accuracy per model per commodity
    Console table                  — commodity | model | MAPE | dir_acc

Run:
    python utils/model_evaluation_report.py
"""

import sys
import os
import logging
import warnings
import itertools

import duckdb
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("model_evaluation_report")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.pipeline_logger import PipelineLogger
from pipeline import run_forecasting_4 as forecasting

# The root agri_ghana.duckdb contains the full 2006-2023 stg_wfp_prices history.
# The deployed ui/sources copy only surfaces post-2019 data via fact_monthly_prices.
# To avoid file-lock conflicts, work from a temp copy of the root database.
import shutil
import tempfile

def _get_db_path() -> str:
    root = "agri_ghana.duckdb"
    try:
        tmp = os.path.join(tempfile.gettempdir(), "agri_ghana_eval.duckdb")
        shutil.copy2(root, tmp)
        log.info(f"Working from temp DB copy: {tmp}")
        return tmp
    except Exception as e:
        log.warning(f"Could not copy root DB ({e}). Falling back to deployed copy.")
        return "ui/sources/agri_ghana/agri_ghana.duckdb"

OUTPUTS_DIR = "outputs"

STAPLES = [
    "maize",
    "cassava",
    "rice (local)",
    "rice (imported)",
    "plantains (apentu)",
    "tomatoes (local)",
]

TRAIN_END  = forecasting.TRAIN_END   # "2022-12-31"
TEST_START = forecasting.TEST_START  # "2023-01-01"

PRICE_FLOOR = forecasting.PRICE_FLOOR_GHS
PRICE_CEIL  = forecasting.PRICE_CEIL_GHS

# Directional accuracy threshold for the decision framework
DIR_ACC_THRESHOLD = 60.0


# -----------------------------------------------------------------------
# Data helpers
# -----------------------------------------------------------------------

def _load_series(con: duckdb.DuckDBPyConnection, commodity: str,
                 fx: pd.DataFrame) -> pd.DataFrame:
    """
    Load monthly retail price series for a commodity joined with the GHS/USD
    FX rate. Queries stg_wfp_prices (full 2006-2023 history) when available,
    falling back to fact_monthly_prices (post-2019 deployed subset) otherwise.
    """
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    if "stg_wfp_prices" in tables:
        df = con.execute(f"""
            SELECT
                DATE_TRUNC('month', record_date)::DATE AS ds,
                ROUND(AVG(price_per_kg_ghs), 4) AS y
            FROM stg_wfp_prices
            WHERE commodity_name = '{commodity}'
              AND price_type = 'retail'
              AND price_per_kg_ghs BETWEEN 0.05 AND 500.0
            GROUP BY DATE_TRUNC('month', record_date)::DATE
            HAVING COUNT(*) >= 3
            ORDER BY ds
        """).fetchdf()
    else:
        log.warning("stg_wfp_prices not found — using fact_monthly_prices (limited history).")
        df = con.execute(f"""
            SELECT
                month_start::DATE AS ds,
                ROUND(AVG(avg_price_per_kg_ghs), 4) AS y
            FROM fact_monthly_prices
            WHERE commodity_name = '{commodity}'
              AND price_type = 'retail'
              AND avg_price_per_kg_ghs IS NOT NULL
            GROUP BY month_start
            ORDER BY month_start
        """).fetchdf()
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.merge(fx[["ds", "usd_ghs"]], on="ds", how="left")
    df["usd_ghs"] = df["usd_ghs"].ffill().bfill()
    return df


def _split(df: pd.DataFrame):
    train = df[df["ds"] <= pd.Timestamp(TRAIN_END)]
    test  = df[df["ds"] >= pd.Timestamp(TEST_START)]
    return train, test


def _directional_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float:
    return forecasting.directional_accuracy(actual, predicted)


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    errors = np.abs((actual - predicted) / np.where(actual == 0, np.nan, actual))
    return float(np.nanmean(errors) * 100)


# -----------------------------------------------------------------------
# Model 1 — Prophet
# -----------------------------------------------------------------------

def eval_prophet(commodity: str, train: pd.DataFrame,
                 test: pd.DataFrame) -> tuple[float, float]:
    from prophet import Prophet
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.15,
        seasonality_mode="multiplicative",
        changepoints=[cp for cp in forecasting.KNOWN_CHANGEPOINTS
                      if cp <= str(train["ds"].max().date())],
    )
    model.add_regressor("usd_ghs")
    model.fit(train[["ds", "y", "usd_ghs"]])
    pred = model.predict(test[["ds", "usd_ghs"]])
    predicted = pred["yhat"].clip(lower=PRICE_FLOOR, upper=PRICE_CEIL).values
    actual    = test["y"].values
    return _mape(actual, predicted), _directional_accuracy(actual, predicted)


# -----------------------------------------------------------------------
# Model 2 — ARIMAX (SARIMAX p,1,q with GHS/USD exog)
# -----------------------------------------------------------------------

def eval_arimax(commodity: str, train: pd.DataFrame,
                test: pd.DataFrame) -> tuple[float, float]:
    """
    Select best SARIMAX(p,1,q) order by AIC on the training set,
    then evaluate on the test set with GHS/USD as exogenous variable.
    d=1 applied because ADF confirmed non-stationarity for most commodities.
    """
    best_aic   = np.inf
    best_order = (1, 1, 1)

    for p, q in itertools.product(range(3), range(3)):
        try:
            res = SARIMAX(
                train["y"],
                exog=train[["usd_ghs"]],
                order=(p, 1, q),
                trend="c",
                enforce_stationarity=False,
                enforce_invertibility=False,
            ).fit(disp=False)
            if res.aic < best_aic:
                best_aic   = res.aic
                best_order = (p, 1, q)
        except Exception:
            continue

    log.info(f"  [ARIMAX:{commodity}] Best order: {best_order}  AIC: {best_aic:.1f}")

    model = SARIMAX(
        train["y"],
        exog=train[["usd_ghs"]],
        order=best_order,
        trend="c",
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False)

    forecast = model.forecast(steps=len(test), exog=test[["usd_ghs"]])
    predicted = np.clip(forecast.values, PRICE_FLOOR, PRICE_CEIL)
    actual    = test["y"].values
    return _mape(actual, predicted), _directional_accuracy(actual, predicted)


# -----------------------------------------------------------------------
# Model 3 — XGBoost with lag features
# -----------------------------------------------------------------------

def eval_xgboost(commodity: str, train: pd.DataFrame,
                 test: pd.DataFrame) -> tuple[float, float]:
    """
    XGBoost regressor with lag features:
        price_lag_1, price_lag_2, price_lag_3,
        mom_pct_lag_1, month_of_year, usd_ghs
    No stationarity assumption — handles structural breaks via feature engineering.
    """
    try:
        from xgboost import XGBRegressor
    except ImportError:
        log.warning("  xgboost not installed. Skipping XGBoost evaluation.")
        return np.nan, np.nan

    def _build_features(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy().reset_index(drop=True)
        d["lag1"]       = d["y"].shift(1)
        d["lag2"]       = d["y"].shift(2)
        d["lag3"]       = d["y"].shift(3)
        d["mom_lag1"]   = d["y"].pct_change(1) * 100
        d["month"]      = d["ds"].dt.month
        return d.dropna(subset=["lag1", "lag2", "lag3"])

    FEATURES = ["lag1", "lag2", "lag3", "mom_lag1", "month", "usd_ghs"]

    # Build features on the full series so lags at the train/test boundary
    # are computed correctly, then split back
    full = pd.concat([train, test], ignore_index=True)
    full = _build_features(full)

    tr = full[full["ds"] <= pd.Timestamp(TRAIN_END)]
    te = full[full["ds"] >= pd.Timestamp(TEST_START)]

    if len(tr) < 6 or len(te) == 0:
        return np.nan, np.nan

    model = XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
        verbosity=0,
    )
    model.fit(tr[FEATURES], tr["y"])
    predicted = np.clip(model.predict(te[FEATURES]), PRICE_FLOOR, PRICE_CEIL)
    actual    = te["y"].values
    return _mape(actual, predicted), _directional_accuracy(actual, predicted)


# -----------------------------------------------------------------------
# Comparison chart
# -----------------------------------------------------------------------

def _save_comparison_chart(records: list[dict], out_dir: str):
    df = pd.DataFrame(records)
    commodities = df["commodity"].unique()
    models      = ["Prophet", "ARIMAX", "XGBoost"]
    x           = np.arange(len(commodities))
    width       = 0.22
    colors      = {"Prophet": "#1e3a5f", "ARIMAX": "#2563a8", "XGBoost": "#b91c1c"}

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 10), sharex=True)

    for i, model in enumerate(models):
        sub   = df[df["model"] == model].set_index("commodity")
        mapes = [sub.loc[c, "mape"] if c in sub.index else np.nan for c in commodities]
        dirs  = [sub.loc[c, "dir_acc"] if c in sub.index else np.nan for c in commodities]
        offset = (i - 1) * width
        ax1.bar(x + offset, mapes, width, label=model, color=colors[model], alpha=0.85)
        ax2.bar(x + offset, dirs,  width, label=model, color=colors[model], alpha=0.85)

    ax1.set_ylabel("MAPE (%)", fontsize=11)
    ax1.set_title("Model Comparison — MAPE (lower is better)", fontsize=12, fontweight="bold")
    ax1.legend(fontsize=10)
    ax1.axhline(20, color="#d97706", linewidth=1, linestyle="--", label="20% reference")

    ax2.set_ylabel("Directional Accuracy (%)", fontsize=11)
    ax2.set_title("Model Comparison — Directional Accuracy (higher is better)", fontsize=12, fontweight="bold")
    ax2.axhline(DIR_ACC_THRESHOLD, color="#16a34a", linewidth=1,
                linestyle="--", label=f"{DIR_ACC_THRESHOLD}% threshold")
    ax2.set_ylim(0, 105)
    ax2.legend(fontsize=10)

    ax2.set_xticks(x)
    ax2.set_xticklabels(commodities, rotation=25, ha="right", fontsize=10)

    fig.suptitle(
        f"Candidate Model Evaluation — Train: 2006–{TRAIN_END} | Test: {TEST_START}–2023-07-01",
        fontsize=13, fontweight="bold", y=1.01,
    )
    plt.tight_layout()
    path = os.path.join(out_dir, "model_comparison.png")
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    log.info(f"Saved: {path}")


# -----------------------------------------------------------------------
# Decision logic
# -----------------------------------------------------------------------

def _make_decision(records: list[dict]) -> str:
    df = pd.DataFrame(records)

    # Per-model average directional accuracy across commodities
    summary = (
        df.groupby("model")[["mape", "dir_acc"]]
        .mean()
        .round(1)
    )

    log.info("\n" + "=" * 65)
    log.info("MODEL COMPARISON SUMMARY (averages across all commodities)")
    log.info("=" * 65)
    log.info(f"{'Model':<12} {'Avg MAPE':>10} {'Avg Dir Acc':>13}")
    log.info("-" * 40)
    for model, row in summary.iterrows():
        log.info(f"{model:<12} {row['mape']:>9.1f}%  {row['dir_acc']:>11.1f}%")
    log.info("=" * 65)

    best_model = summary["dir_acc"].idxmax()
    best_dir   = summary.loc[best_model, "dir_acc"]
    best_mape  = summary.loc[best_model, "mape"]

    if best_dir >= DIR_ACC_THRESHOLD:
        decision = (
            f"DECISION: {best_model} achieves the highest directional accuracy "
            f"({best_dir:.1f}%) with MAPE {best_mape:.1f}%. "
            f"{'Retain with current config.' if best_model == 'Prophet' else f'Switch pipeline to {best_model}.'}"
        )
    else:
        decision = (
            f"DECISION: No model exceeds the {DIR_ACC_THRESHOLD}% directional accuracy threshold. "
            f"Best is {best_model} at {best_dir:.1f}%. "
            f"Recommend fine-tuning {best_model} or collecting more recent data."
        )

    log.info(f"\n{decision}\n")
    return decision


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    import time
    t0 = time.perf_counter()
    pl = PipelineLogger("agri_ghana.duckdb")
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    db_path = _get_db_path()
    fx  = forecasting.build_monthly_fx_series(start="2006-01-01", end="2023-07-01")
    con = duckdb.connect(db_path, read_only=True)

    records = []

    for commodity in STAPLES:
        log.info(f"\n{'─' * 55}")
        log.info(f"Evaluating: {commodity}")
        df = _load_series(con, commodity, fx)
        train, test = _split(df)

        if len(train) < 18 or len(test) == 0:
            log.warning(f"  Skipping {commodity}: insufficient train/test data.")
            continue

        log.info(f"  Train: {train['ds'].min().date()} → {train['ds'].max().date()} ({len(train)}m)")
        log.info(f"  Test:  {test['ds'].min().date()} → {test['ds'].max().date()} ({len(test)}m)")

        for model_name, eval_fn in [
            ("Prophet", eval_prophet),
            ("ARIMAX",  eval_arimax),
            ("XGBoost", eval_xgboost),
        ]:
            try:
                mape, dir_acc = eval_fn(commodity, train.copy(), test.copy())
                log.info(f"  {model_name:<10} MAPE={mape:6.1f}%  DirAcc={dir_acc:5.1f}%")
                records.append({
                    "commodity": commodity,
                    "model":     model_name,
                    "mape":      round(mape, 1),
                    "dir_acc":   round(dir_acc, 1),
                })
            except Exception as e:
                log.warning(f"  {model_name} failed for {commodity}: {e}")

    con.close()

    if not records:
        log.error("No evaluation results produced.")
        return

    _save_comparison_chart(records, OUTPUTS_DIR)
    decision = _make_decision(records)

    duration = time.perf_counter() - t0
    pl.log(
        script_name="model_evaluation_report",
        status="SUCCESS",
        message=decision[:500],
        duration_seconds=duration,
    )
    log.info(f"Model evaluation complete. Total time: {duration:.1f}s")


if __name__ == "__main__":
    main()
