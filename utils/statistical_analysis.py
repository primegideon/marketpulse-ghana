"""
Statistical Analysis Module
============================
Produces four statistical analyses of the WFP Ghana commodity price data
for use in the MarketPulse Ghana presentation and model validation.

Outputs (all saved to outputs/ directory as PNG):
    1. outputs/correlation_matrix.png
       Pearson correlation heatmap — monthly retail prices per commodity
       vs GHS/USD exchange rate.

    2. outputs/adf_stationarity.png + console ADF table
       Augmented Dickey-Fuller stationarity test per commodity.
       Expected result: non-stationary (p > 0.05) due to upward trend
       and structural breaks — this validates the need for differencing
       or shock-aware models like ARIMAX/XGBoost.

    3. outputs/acf_pacf_{commodity}.png  (one per commodity)
       Autocorrelation and Partial Autocorrelation plots.
       Reveals how many months of price history carry predictive signal.

    4. outputs/shock_decomposition.png
       Stacked bar chart decomposing 2022-01-01 to 2023-07-01 MoM price
       changes into FX-explained and residual (supply/demand) components
       for each commodity.

Run:
    python utils/statistical_analysis.py
"""

import sys
import os
import logging
import warnings

import duckdb
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — no display required
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.pipeline_logger import PipelineLogger
from pipeline import run_forecasting_4 as forecasting

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("statistical_analysis")

DB_PATH     = "ui/sources/agri_ghana/agri_ghana.duckdb"
OUTPUTS_DIR = "outputs"

STAPLES = [
    "maize",
    "cassava",
    "rice (local)",
    "rice (imported)",
    "plantains (apentu)",
    "tomatoes (local)",
]

SHOCK_START = "2022-01-01"
SHOCK_END   = "2023-07-01"

# Chart style
PALETTE     = ["#1e3a5f", "#2563a8", "#4a90c4", "#7fb3d3", "#b91c1c", "#d97706"]
sns.set_theme(style="whitegrid", font_scale=1.05)
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "font.family": "sans-serif"})


# -----------------------------------------------------------------------
# Data loading helpers
# -----------------------------------------------------------------------

def _load_prices(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load national monthly retail prices per commodity from fact_monthly_prices."""
    df = con.execute("""
        SELECT
            month_start,
            commodity_name,
            ROUND(AVG(avg_price_per_kg_ghs), 4) AS avg_price
        FROM fact_monthly_prices
        WHERE price_type = 'retail'
          AND avg_price_per_kg_ghs IS NOT NULL
          AND commodity_name IN (
              'maize', 'cassava', 'rice (local)', 'rice (imported)',
              'plantains (apentu)', 'tomatoes (local)'
          )
        GROUP BY month_start, commodity_name
        ORDER BY month_start, commodity_name
    """).fetchdf()
    df["month_start"] = pd.to_datetime(df["month_start"])
    return df


def _wide_prices(df_long: pd.DataFrame) -> pd.DataFrame:
    """Pivot to wide format: index = month_start, columns = commodity names."""
    return df_long.pivot(index="month_start", columns="commodity_name", values="avg_price")


def _load_fx() -> pd.DataFrame:
    """Reuse the FX series builder from the forecasting module."""
    return forecasting.build_monthly_fx_series(start="2006-01-01", end="2023-07-01")


# -----------------------------------------------------------------------
# 1. Correlation Matrix
# -----------------------------------------------------------------------

def run_correlation_matrix(wide: pd.DataFrame, fx: pd.DataFrame, out_dir: str):
    log.info("Running correlation matrix analysis...")

    fx_m = fx.set_index("ds")["usd_ghs"]
    wide_aligned = wide.copy()
    wide_aligned["GHS/USD Rate"] = fx_m.reindex(wide_aligned.index)
    wide_aligned = wide_aligned.dropna(how="all")

    corr = wide_aligned.corr(method="pearson")

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        vmin=-1, vmax=1,
        linewidths=0.5,
        ax=ax,
        mask=mask,
        annot_kws={"size": 9},
    )
    ax.set_title(
        "Pearson Correlation — Monthly Retail Prices & GHS/USD Exchange Rate",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right", fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)
    plt.tight_layout()

    path = os.path.join(out_dir, "correlation_matrix.png")
    fig.savefig(path)
    plt.close(fig)
    log.info(f"Saved: {path}")

    # Print GHS/USD correlations to console
    fx_corr = corr["GHS/USD Rate"].drop("GHS/USD Rate").sort_values(ascending=False)
    log.info("GHS/USD correlation per commodity:")
    for c, r in fx_corr.items():
        log.info(f"  {c:<30} r = {r:.3f}")

    return fx_corr


# -----------------------------------------------------------------------
# 2. ADF Stationarity Tests
# -----------------------------------------------------------------------

def run_adf_tests(wide: pd.DataFrame, out_dir: str) -> pd.DataFrame:
    log.info("Running ADF stationarity tests...")

    results = []
    for commodity in STAPLES:
        if commodity not in wide.columns:
            continue
        series = wide[commodity].dropna()
        if len(series) < 20:
            log.warning(f"  [{commodity}] Insufficient data for ADF test.")
            continue

        adf_stat, p_value, used_lags, nobs, critical_values, _ = adfuller(series, autolag="AIC")
        verdict = "Non-stationary" if p_value > 0.05 else "Stationary"
        results.append({
            "commodity":   commodity,
            "adf_stat":    round(adf_stat, 4),
            "p_value":     round(p_value, 4),
            "lags_used":   used_lags,
            "nobs":        nobs,
            "crit_1pct":   round(critical_values["1%"], 3),
            "crit_5pct":   round(critical_values["5%"], 3),
            "verdict":     verdict,
        })
        log.info(f"  {commodity:<30} ADF={adf_stat:7.3f}  p={p_value:.4f}  → {verdict}")

    df_results = pd.DataFrame(results)

    # Save as a clean table chart
    fig, ax = plt.subplots(figsize=(11, max(3, len(results) * 0.7 + 1.5)))
    ax.axis("off")
    col_labels = ["Commodity", "ADF Stat", "p-value", "Critical 5%", "Verdict"]
    table_data = [
        [r["commodity"], f"{r['adf_stat']:.3f}", f"{r['p_value']:.4f}",
         f"{r['crit_5pct']:.3f}", r["verdict"]]
        for r in results
    ]
    tbl = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.6)

    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_facecolor("#1e3a5f")
            cell.set_text_props(color="white", fontweight="bold")
        elif col == 4:
            verdict_val = table_data[row - 1][4] if row > 0 else ""
            cell.set_facecolor("#fef3c7" if verdict_val == "Non-stationary" else "#dcfce7")
        cell.set_edgecolor("#e5e7eb")

    ax.set_title(
        "Augmented Dickey-Fuller Stationarity Test Results\n"
        "H₀: Series has a unit root (non-stationary). Reject if p < 0.05.",
        fontsize=12, fontweight="bold", pad=12,
    )
    plt.tight_layout()
    path = os.path.join(out_dir, "adf_stationarity.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    log.info(f"Saved: {path}")

    return df_results


# -----------------------------------------------------------------------
# 3. ACF / PACF Plots
# -----------------------------------------------------------------------

def run_acf_pacf(wide: pd.DataFrame, out_dir: str):
    log.info("Running ACF/PACF analysis...")

    for commodity in STAPLES:
        if commodity not in wide.columns:
            continue
        series = wide[commodity].dropna()
        if len(series) < 12:
            log.warning(f"  [{commodity}] Insufficient data for ACF/PACF.")
            continue

        max_lags = min(24, len(series) // 2 - 1)
        fig, axes = plt.subplots(1, 2, figsize=(13, 4))
        plot_acf(series, lags=max_lags, ax=axes[0], color="#1e3a5f", alpha=0.05)
        plot_pacf(series, lags=max_lags, ax=axes[1], color="#2563a8", alpha=0.05, method="ywm")

        axes[0].set_title(f"ACF — {commodity.title()}", fontsize=11, fontweight="bold")
        axes[1].set_title(f"PACF — {commodity.title()}", fontsize=11, fontweight="bold")
        axes[0].set_xlabel("Lag (months)")
        axes[1].set_xlabel("Lag (months)")

        fig.suptitle(
            f"Autocorrelation Analysis — {commodity.title()}\n"
            "Significant lags outside shaded band indicate predictive signal",
            fontsize=12, fontweight="bold", y=1.02,
        )
        plt.tight_layout()

        safe_name = commodity.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
        path = os.path.join(out_dir, f"acf_pacf_{safe_name}.png")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        log.info(f"  Saved: {path}")


# -----------------------------------------------------------------------
# 4. Shock Impact Decomposition
# -----------------------------------------------------------------------

def run_shock_decomposition(df_long: pd.DataFrame, fx: pd.DataFrame,
                             fx_corr: pd.Series, out_dir: str):
    log.info("Running shock impact decomposition (2022–2023)...")

    fx_m = fx.set_index("ds")["usd_ghs"].sort_index()
    fx_mom = fx_m.pct_change() * 100   # FX month-over-month % change

    shock_df = df_long[
        (df_long["month_start"] >= SHOCK_START) &
        (df_long["month_start"] <= SHOCK_END)
    ].copy()

    records = []
    for commodity in STAPLES:
        sub = shock_df[shock_df["commodity_name"] == commodity].set_index("month_start").sort_index()
        if len(sub) < 2:
            continue
        sub["mom_pct"] = sub["avg_price"].pct_change() * 100
        sub = sub.dropna(subset=["mom_pct"])

        corr_coeff = fx_corr.get(commodity, 0.0)

        for month, row in sub.iterrows():
            fx_change = fx_mom.get(month, 0.0)
            fx_contrib   = fx_change * abs(corr_coeff)
            residual     = row["mom_pct"] - fx_contrib
            records.append({
                "month":       month,
                "commodity":   commodity,
                "total_mom":   round(row["mom_pct"], 2),
                "fx_contrib":  round(fx_contrib, 2),
                "residual":    round(residual, 2),
            })

    decomp = pd.DataFrame(records)
    if decomp.empty:
        log.warning("No shock decomposition data available.")
        return

    # Aggregate across commodities per month for the chart
    monthly = (
        decomp.groupby("month")[["fx_contrib", "residual"]]
        .mean()
        .reset_index()
        .sort_values("month")
    )

    fig, ax = plt.subplots(figsize=(13, 5))
    months = [m.strftime("%b %Y") for m in monthly["month"]]
    x = np.arange(len(months))
    w = 0.55

    ax.bar(x, monthly["fx_contrib"], width=w, label="FX-explained component",
           color="#1e3a5f", alpha=0.85)
    ax.bar(x, monthly["residual"],   width=w, bottom=monthly["fx_contrib"],
           label="Residual (supply/demand)", color="#b91c1c", alpha=0.75)

    ax.axhline(0, color="#374151", linewidth=0.8, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Avg MoM Price Change (%)", fontsize=10)
    ax.set_title(
        "Shock Decomposition — Average MoM Price Change by Driver (Jan 2022 – Jul 2023)\n"
        "FX-explained = GHS/USD MoM change × commodity-FX correlation · "
        "Residual = supply/demand factors",
        fontsize=11, fontweight="bold",
    )
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    plt.tight_layout()

    path = os.path.join(out_dir, "shock_decomposition.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    log.info(f"Saved: {path}")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    import time
    t0 = time.perf_counter()
    pl = PipelineLogger("agri_ghana.duckdb")

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    log.info(f"Output directory: {os.path.abspath(OUTPUTS_DIR)}")

    con = duckdb.connect(DB_PATH, read_only=True)
    df_long = _load_prices(con)
    con.close()

    wide = _wide_prices(df_long)
    fx   = _load_fx()

    log.info(f"Loaded {len(df_long):,} price observations across {df_long['commodity_name'].nunique()} commodities.")
    log.info(f"Date range: {df_long['month_start'].min().date()} → {df_long['month_start'].max().date()}")

    # 1. Correlation matrix
    fx_corr = run_correlation_matrix(wide, fx, OUTPUTS_DIR)

    # 2. ADF stationarity
    run_adf_tests(wide, OUTPUTS_DIR)

    # 3. ACF / PACF
    run_acf_pacf(wide, OUTPUTS_DIR)

    # 4. Shock decomposition
    run_shock_decomposition(df_long, fx, fx_corr, OUTPUTS_DIR)

    duration = time.perf_counter() - t0
    pl.success("statistical_analysis", rows_affected=len(df_long), duration_seconds=duration)
    log.info(f"Statistical analysis complete. All outputs saved to '{OUTPUTS_DIR}/'. Total time: {duration:.1f}s")


if __name__ == "__main__":
    main()
