# MarketPulse Ghana

MarketPulse Ghana is an AmaliTech internship capstone examining historical food prices in Ghana. It explores how price patterns across commodities and markets may provide useful context for small and medium-sized food businesses.

## Project focus

The project looks at historical price trends, seasonal patterns, and differences between markets. Its intended audience includes food traders, retailers, food-service businesses, and processors.

The WFP dataset contains market prices, not individual business costs or sales. It cannot show a particular SME's transport expenses, stock levels, margins, or expected profit. Findings should be treated as market context rather than business-specific recommendations.

## Data

- Source: [WFP Ghana Food Prices on HDX](https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320)
- CSV resource: [wfp_food_prices_gha.csv](https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320/resource/e877350b-146f-4fa7-8690-db9605eea78c/download/wfp_food_prices_gha.csv)
- Local storage: DuckDB, table `raw_wfp_prices`

The local snapshot contains 37,765 observations from January 2006 through July 2023, including wholesale and retail prices for multiple commodities, markets, and units. The snapshot is historical and is not a live price feed. Comparisons should use compatible commodities, units, price types, markets, and time periods. Check HDX for a newer release before presenting these observations as current.

## Modelling target

The forecasting objective is the national monthly median **wholesale maize price** (GHS per kg), predicted one month ahead. Wholesale maize was selected over the retail series because it provides 209 months of history (January 2006 – July 2023) against 48 months for the retail equivalent, producing a substantially larger training window for a lag-based model.

## Notebooks

| Notebook | Phase | Description |
|----------|-------|-------------|
| [exploratory_data_analysis.ipynb](notebooks/exploratory_data_analysis.ipynb) | 1 — EDA | Data structure, quality, coverage, distributions, seasonality, outlier detection, and correlation analysis |
| [preprocessing_and_feature_engineering.ipynb](notebooks/preprocessing_and_feature_engineering.ipynb) | 2 — Preprocessing | Data cleaning, lag and rolling features, calendar encoding, log transformation, and chronological train/test split |
| [model_selection_and_training.ipynb](notebooks/model_selection_and_training.ipynb) | 3 — Training | Naive baseline, walk-forward cross-validation, XGBoost hyperparameter grid search, final model training, and feature importance |

### Phase 1 — Exploratory Data Analysis

The EDA notebook examines data coverage, quality, price distributions, seasonality, unusual observations, and relationships between price series. In the local snapshot, the analysis found no missing values, exact duplicate rows, or duplicate record keys. It also flagged some currency-conversion inconsistencies and unusual prices for further review; flagged observations are not automatically errors and are not removed by the EDA.

### Phase 2 — Preprocessing & Feature Engineering

The preprocessing notebook produces a clean, model-ready feature matrix from the raw WFP snapshot. Features include price lags (1, 2, 3, 6, and 12 months), rolling means and standard deviation, cyclically encoded calendar variables, and month-on-month and year-on-year percentage changes. Price-level features and the target are log-transformed to reduce skew. The final 18 months (January 2022 – June 2023) are reserved as a held-out test set; all remaining rows form the training set.

Outputs written to `data/`:

| File | Description |
|------|-------------|
| `train.csv` | Training feature matrix and target (179 rows) |
| `test.csv` | Test feature matrix and target (18 rows) |
| `feature_config.json` | Feature names, target column, split date, and transformation notes |
| `maize_wholesale_features.csv` | Full feature-engineered dataset before splitting |
| `hyperparameter_search.csv` | Grid search results from Phase 3 |

### Phase 3 — Model Selection & Training

The training notebook establishes a naive persistence baseline, evaluates XGBoost with default parameters using walk-forward cross-validation (9 expanding folds, 2012–2021), runs a grid search over 18 hyperparameter combinations, trains the final model on the full training set, and records feature importance.

The test window covers a period of extreme food inflation driven by the Russia–Ukraine war and Ghana's currency crisis. Model performance on this window represents a lower bound on real-world capability under normal conditions.

Outputs written to `models/`:

| File | Description |
|------|-------------|
| `xgboost_maize_wholesale.json` | Trained XGBoost model (native JSON format) |
| `model_metadata.json` | Hyperparameters, CV configuration, and key metrics |

## Run the notebooks

Use Python 3.12 or a compatible version. From the project root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install duckdb numpy pandas matplotlib seaborn scikit-learn xgboost jupyter nbconvert ipykernel
```

Execute notebooks in order:

```powershell
jupyter nbconvert --to notebook --execute notebooks/exploratory_data_analysis.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/preprocessing_and_feature_engineering.ipynb --inplace
jupyter nbconvert --to notebook --execute notebooks/model_selection_and_training.ipynb --inplace
```

Each notebook opens `agri_ghana.duckdb` in read-only mode and expects it in the project root. Close other processes using the database if DuckDB reports a file-lock error. The preprocessing notebook must be executed before the training notebook, as it produces the `data/` files on which the training notebook depends.

## Results summary

All results are exploratory. Interpretations should account for data coverage, measurement units, price type, and the snapshot's July 2023 end date.
