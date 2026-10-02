---
title: Methods & Data
---

# Methods & Data
### How the findings were produced — and how to interpret them

> This page documents the scope, methods, and validation behind MarketPulse Ghana. Transparency about limitations is as important as the findings themselves.

---

## Data Source and Scope

| Dimension | Detail |
|---|---|
| **Source** | WFP VAM Food Security — Ghana dataset, Humanitarian Data Exchange (HDX) |
| **Price type** | **Retail only.** Wholesale data (available from 2006) is excluded — wholesale prices are structurally incompatible with retail (e.g. tomatoes wholesale ~GHS 1.42/kg vs retail ~GHS 6.14/kg) |
| **Retail coverage** | August 2019 – July 2023 (47 months). WFP began systematic retail price recording in August 2019 |
| **Markets** | 44 georeferenced markets (latitude/longitude) across 10 administrative regions |
| **Commodities retained** | Maize, Rice (local + imported), Cassava, Plantains, Tomatoes (core 8 staples) |
| **Unit** | GHS per kilogram (all units normalised to kg in the pipeline) |
| **Urban definition** | Greater Accra + Ashanti regions |
| **Producing/rural definition** | Northern, Upper East, Upper West, Brong Ahafo, Volta regions |

---

## Pipeline Overview

The analytical pipeline runs in five sequential steps:

| Step | Script | Output |
|---|---|---|
| 1. Ingest | `1_ingest_data.py` | `raw_wfp_prices` — raw WFP CSV loaded into DuckDB |
| 2. Transform | `2_transform_data.py` | `stg_wfp_prices` — all units normalised to GHS/kg |
| 3. Analytics | `3_build_analytics_views.py` | `fact_monthly_prices`, `fact_market_spreads`, `fact_gbvi_index` |
| 4. Forecast | `4_run_forecasting.py` | `fact_price_forecasts` — XGBoost 6-month projections |
| 5. Seasonal | `5_build_seasonal_outlook.py` | `fact_seasonal_outlook` — historical seasonal patterns |

All outputs are stored in a DuckDB analytical warehouse and queried directly by this dashboard.

---

## Ghana Basket Volatility Index (GBVI)

The GBVI is a composite 0–100 score measuring month-over-month price instability across the core staple basket:

```
GBVI = CLAMP(
    (avg_abs_mom_pct / 15.0) * 60
  + (stddev_mom_pct / 12.0)  * 40,
  0, 100
)
```

- **60% weight:** average absolute MoM price change across staples
- **40% weight:** cross-commodity standard deviation of MoM changes
- **Normalisation denominators** (15.0 and 12.0) were calibrated to the 75th percentile of the respective distributions in the 2006–2023 WFP Ghana dataset

| Band | Score Range | Definition |
|---|---|---|
| Stable | 0 – 30 | Normal seasonal fluctuations; no systemic stress |
| Moderate | 31 – 70 | Elevated volatility; heightened monitoring warranted |
| High Alert | 71 – 100 | Broad basket instability; policy response may be needed |

Risk band thresholds were set at the 33rd and 66th percentiles of the GBVI score distribution across 2006–2023, dividing the observed range into three roughly equal-frequency bands.

**Rice (paddy)** is included in the GBVI basket as an early-warning signal: paddy price movements at Northern farm-gate level lead milled rice retail prices by approximately 1–2 months. It is excluded from `CORE_STAPLES` (retail-only list used for consumer-facing KPIs).

---

## Urban–Rural Spread Analysis

Spreads compare average retail prices in urban markets (Greater Accra + Ashanti) against producing-region rural markets for each commodity and month.

- `absolute_spread_ghs` = urban_avg_price − producing_avg_price
- `spread_margin_pct` = (absolute_spread_ghs / producing_avg_price) × 100

A positive margin means urban consumers pay more. Widening margins over time indicate transport, logistics, or intermediary cost pressures.

---

## XGBoost Forecasting Model

| Parameter | Value |
|---|---|
| Model | XGBoost gradient-boosted regression |
| Train period | August 2019 – December 2022 |
| Test period | January 2023 – July 2023 (holdout, date-based split) |
| Forecast horizon | 6 months forward from July 2023 |
| Features | price_lag_1, price_lag_2, price_lag_3, mom_pct_lag_1, month_of_year, GHS/USD FX rate |
| FX source | World Bank indicator PA.NUS.FCRF, monthly, interpolated via linear spline |

**Model selection rationale:** Three models were formally evaluated on the same holdout period:

| Model | Directional Accuracy | Avg MAPE |
|---|---|---|
| XGBoost | **61.1%** | **21.5%** |
| ARIMAX | 38.9% | 23.8% |
| Prophet | 47.2% | 42.4% |

XGBoost was selected for its highest directional accuracy — the operationally relevant metric for food security procurement and intervention decisions. It makes no stationarity assumptions and handles structural breaks (such as the 2022 cedi crisis) via lag feature engineering.

**Confidence bands** are derived from per-commodity residual standard deviation on the test set. They widen for more volatile commodities.

---

## Seasonal Outlook

Seasonal patterns are computed from the available 4-year retail history (Aug 2019–Jul 2023). For each commodity and calendar month:

- `avg_mom_pct`: average price change in that month across observed years
- `pct_years_up`: percentage of years where price rose in that month
- `direction_signal`: "Typically rises" / "Typically falls" / "Mixed"

**Important caveat:** Signals are based on 4 annual cycles only. They indicate historically observed patterns, not climatological laws. Treat as probabilistic guidance, not prediction.

MoM values outside −60% to +200% are excluded as data-entry artefacts (the WFP Ghana observed maximum is ~180% before filtering).

---

## Shock Decomposition

The FX contribution to post-2021 price increases is estimated via Pearson correlation between monthly GHS/USD changes and commodity-level MoM price changes. The decomposition attributes:

- **FX contribution** = monthly FX change × correlation coefficient (signed)
- **Supply/other contribution** = residual (total MoM − FX contribution)

This is a correlation-based attribution method. It describes co-movement patterns within the WFP sample. **Causal identification is not claimed.**

The ~60% FX attribution finding applies specifically to import-dependent staples (rice imported, plantains) over the Aug 2019–Jul 2023 retail window.

---

## Statistical Diagnostics

The following analyses were completed to validate modeling assumptions. They are available in the project's `outputs/` directory:

| Analysis | Purpose | Finding |
|---|---|---|
| Correlation matrix (Pearson) | Cross-commodity co-movement | Rice (local) and rice (imported) strongly co-move; maize and cassava are more independent |
| ADF stationarity tests | Validates whether differencing is needed | Most retail series are non-stationary in levels; MoM returns are stationary — consistent with using MoM features in XGBoost |
| ACF/PACF plots | Autocorrelation structure | Significant lag-1 and lag-3 autocorrelation in most series — supports the lag feature design |
| Model comparison report | Model selection evidence | XGBoost selected (see Forecasting section above) |

---

> **Full pipeline source code** is available in the project repository. All analyses were conducted in Python using DuckDB, pandas, scikit-learn, xgboost, and statsmodels.
