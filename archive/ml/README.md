# Machine Learning Pipeline Archive

This directory consolidates the Phase 2 (Data Preprocessing & Feature Engineering) and Phase 3 (Model Selection, Training, & Evaluation) assets developed for the MarketPulse Ghana predictive modeling stream.

---

## Strategic Context & Purpose

The machine learning assets in this archive were developed to evaluate the feasibility of forecasting agricultural commodity prices in Ghana. As part of an intentional architectural pivot, these artifacts have been preserved in this dedicated archive to allow the primary project scope to focus on a high-impact, modern analytics engineering stack:

$$\text{WFP Ghana Food Prices (HDX)} \longrightarrow \text{DuckDB Analytical Engine} \longrightarrow \text{Evidence.dev UI (Vercel)}$$

Establishing robust analytical marts, price indices, and interactive web-based data products delivers immediate operational clarity to food traders, processors, and retailers. This archive ensures that all feature engineering pipelines, cross-validation protocols, and trained model weights remain fully reproducible and ready for reintegration as an automated inference layer.

---

## Directory Inventory

```
archive/ml/
├── data/
│   ├── feature_config.json             # Feature definitions, target column, and transformation metadata
│   ├── hyperparameter_search.csv       # Walk-forward cross-validation results across 18 grid configurations
│   ├── maize_wholesale_features.csv    # Full engineered feature matrix prior to train/test split
│   ├── test.csv                        # Chronological holdout test set (Jan 2022 – Jun 2023, 18 rows)
│   ├── train.csv                       # Training feature matrix (Jan 2006 – Dec 2021, 179 rows)
│   └── train_predictions.csv           # In-sample fitted predictions versus actual historical prices
├── models/
│   ├── model_metadata.json             # Hyperparameters, evaluation metrics (RMSE, MAE, MAPE), and CV folds
│   └── xgboost_maize_wholesale.json    # Serialized final XGBoost model (native portable JSON format)
└── notebooks/
    ├── preprocessing_and_feature_engineering.ipynb  # Feature pipeline, lag generators, calendar encoding
    └── model_selection_and_training.ipynb           # Baseline modeling, expanding-window CV, final training
```

---

## Modeling Summary

| Attribute | Specification |
| :--- | :--- |
| **Prediction Objective** | National monthly median wholesale maize price ($GHS/\text{kg}$), predicted 1 month ahead ($t+1$). |
| **Commodity Rationale** | Wholesale maize offers 209 months of continuous monthly coverage (Jan 2006 – Jul 2023), providing a reliable temporal series compared to the 48-month retail equivalent. |
| **Feature Engineering** | • Autoregressive lags ($t-1, t-2, t-3, t-6, t-12$)<br>• Rolling aggregates (3, 6, and 12-month means and standard deviations)<br>• Logarithmic transformations on price levels and target to reduce right-skew<br>• Cyclical sine/cosine calendar encodings for annual seasonality |
| **Validation Strategy** | Walk-forward cross-validation utilizing 9 expanding folds spanning 2012 through 2021 to strictly avoid data leakage. |
| **Final Algorithm** | Tuned Gradient Boosted Trees ([XGBoost](https://xgboost.readthedocs.io/)) benchmarked against a naive persistence baseline. |
| **Holdout Test Period** | January 2022 – June 2023, representing a stress test under peak macroeconomic volatility and currency depreciation. |

---

## Reintegration Runbook

When re-incorporating predictive capabilities into the live analytics stack:

1. **Source Connection**: Ingest directly from `agri_ghana.duckdb` view `mart_commodity_monthly` (clean, calendar-validated, per-kg standardized monthly aggregates) rather than raw CSV exports or the raw ingestion table.
2. **Feature Extraction**: Execute the transformation pipeline in [`notebooks/preprocessing_and_feature_engineering.ipynb`](file:///c:/Users/qwarm/Desktop/marketpulse-ghana/archive/ml/notebooks/preprocessing_and_feature_engineering.ipynb) or refactor into a dbt/DuckDB SQL feature transformation layer.
3. **Model Scoring**: Load [`models/xgboost_maize_wholesale.json`](file:///c:/Users/qwarm/Desktop/marketpulse-ghana/archive/ml/models/xgboost_maize_wholesale.json) with `xgboost.Booster()` and generate forward-looking projections.
4. **Publishing Inferences**: Write forecasts back into DuckDB as an analytical view (`marts.fct_maize_price_forecasts`), enabling direct visualization in the Evidence.dev frontend.
