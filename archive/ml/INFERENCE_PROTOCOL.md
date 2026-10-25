# Machine Learning Downstream Inference Protocol

This specification defines the contract, schema, retraining triggers, and frontend visualization interface for reintegrating predictive commodity forecasting into the MarketPulse Ghana analytics stack.

---

## 1. Architectural Contract

```
┌─────────────────────────────────┐
│     mart_commodity_monthly      │  Input: Clean historical actuals (DuckDB)
└────────────────┬────────────────┘
                 │
                 ▼ scripts/forecast_maize.py
┌─────────────────────────────────┐
│     Feature Engineering         │  Lags (t-1, t-2, t-3, t-6, t-12), rolling stats (3m, 6m, 12m)
│     & XGBoost Inference         │  Load models/xgboost_maize_wholesale.json
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│      mart_maize_forecasts       │  Output: Forward-looking predictions with confidence intervals
└────────────────┬────────────────┘
                 │
                 ▼ ui/pages/forecasts.md
┌─────────────────────────────────┐
│     Evidence.dev Visualization  │  Seamless actual-to-projection line chart with shaded intervals
└─────────────────────────────────┘
```

---

## 2. Input Contract

The inference job consumes historical monthly aggregates directly from `mart_commodity_monthly`:

```sql
SELECT
    date,
    commodity,
    raw_unit,
    price_type,
    median_price_ghs_per_kg
FROM agri_ghana.mart_commodity_monthly
WHERE commodity = 'Maize'
  AND price_type = 'Wholesale'
  AND raw_unit = '100 KG'
ORDER BY date ASC;
```

* **Minimum Historical Depth**: 24 consecutive months required to populate 12-month rolling means and seasonal lag features.
* **Pre-condition**: Must pass `scripts/test_marts.py` assertions (0 nulls in price, positive values).

---

## 3. Output Data Mart Schema (`mart_maize_forecasts`)

The forecast script outputs a structured projection table in DuckDB:

| Column | Data Type | Nullable | Description | Example |
| :--- | :--- | :---: | :--- | :--- |
| `forecast_date` | `DATE` | No | Date when inference was generated (`YYYY-MM-01`). | `2026-10-01` |
| `target_date` | `DATE` | No | Projected target month (`YYYY-MM-01`). | `2026-11-01` |
| `horizon_months` | `INTEGER` | No | Forecast lead time (`1` to `3` months ahead). | `1` |
| `commodity` | `VARCHAR` | No | Forecasted commodity. | `Maize` |
| `predicted_price_ghs_per_kg` | `DOUBLE` | No | Point forecast from tuned XGBoost booster. | `5.45` |
| `lower_ci_95` | `DOUBLE` | No | 95% prediction interval lower bound. | `4.82` |
| `upper_ci_95` | `DOUBLE` | No | 95% prediction interval upper bound. | `6.08` |
| `model_version` | `VARCHAR` | No | Model binary hash / version. | `xgboost_v1.2_walkforward` |

---

## 4. Retraining Cadence & Model Drift Triggers

* **Scheduled Retraining**: Bi-annually following the August (Major Season) and November (Minor Season) harvest data syncs.
* **Model Drift Triggers**:
  1. **Residual Error**: If rolling 3-month Mean Absolute Percentage Error (MAPE) exceeds **15.0%**.
  2. **Macroeconomic Regime Shift**: If Year-over-Year national food inflation exceeds **40.0%**, indicating currency-driven price shocks outside training distributions.

---

## 5. Evidence.dev Frontend Query Template

To display historical prices stitched seamlessly to model forecasts:

```sql
-- Historical actuals
SELECT
    date,
    median_price_ghs_per_kg AS actual_price,
    CAST(NULL AS DOUBLE)    AS forecast_price,
    CAST(NULL AS DOUBLE)    AS lower_ci,
    CAST(NULL AS DOUBLE)    AS upper_ci,
    'Historical Actual'     AS series_type
FROM agri_ghana.mart_commodity_monthly
WHERE commodity = 'Maize' AND raw_unit = '100 KG' AND price_type = 'Wholesale'

UNION ALL

-- Forward projection
SELECT
    target_date             AS date,
    CAST(NULL AS DOUBLE)    AS actual_price,
    predicted_price_ghs_per_kg AS forecast_price,
    lower_ci_95             AS lower_ci,
    upper_ci_95             AS upper_ci,
    'Projected Forecast'    AS series_type
FROM agri_ghana.mart_maize_forecasts
WHERE commodity = 'Maize'
ORDER BY date ASC;
```
