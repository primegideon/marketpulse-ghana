# Project Roadmap Checklist

This checklist tracks the MarketPulse Ghana analysis against the five-phase workflow in [general_ml_roadmap.html](../general_ml_roadmap.html). Each phase is completed and reviewed before the next phase begins.

## Working Principles
- **Single source of truth:** All analysis starts from the `raw_wfp_prices` table in `agri_ghana.duckdb`. During exploratory analysis the database is opened in read-only mode.
- **Existing pipeline:** The current `pipeline/` scripts and the derived `stg_` and `fact_` tables are not used as inputs. Phase 2 will decide what is rebuilt.
- **Comparability:** Prices are compared only within the same series (commodity, unit and price type), because units differ between series.
- **One notebook per phase:** Each phase is documented in a notebook in the `notebooks/` folder. Findings are recorded in the notebook before the phase is closed.

---

## Phase 1: Exploratory Data Analysis
Notebook: [01_exploratory_data_analysis.ipynb](../notebooks/01_exploratory_data_analysis.ipynb)

| Roadmap item | Notebook section | Implemented | Reviewed |
|---|---|---|---|
| Data overview (size, column types, period, file structure checks) | 1 | Yes | No |
| Cardinality and series inventory | 2 | Yes | No |
| Data quality (missing, blank and invalid values) | 3 | Yes | No |
| Duplicates and consistency (keys, price flag, identifiers, currency) | 4 | Yes | No |
| Coverage and completeness (gaps, data availability, usable series) | 5 | Yes | No |
| Descriptive statistics (per series and per year) | 6 | Yes | No |
| Distributions (skewness, log transformation, change over time) | 7 | Yes | No |
| Visualisation (trends, regional differences, seasonality) | 8 | Yes | No |
| Outlier detection (cross-market and month-over-month, identification only) | 9 | Yes | No |
| Correlation analysis (redundancy, co-movement, wholesale vs retail, geography) | 10 | Yes | No |
| Summary of findings and decisions for Phase 2 | 11 | Yes | No |

### Completion Criteria
- [ ] The notebook runs from start to finish without errors.
- [ ] The findings table (Section 11.2) is completed.
- [ ] The decisions listed in Section 11.3 are agreed.

### Preliminary Observations (to be confirmed during review)
- The data has two distinct periods: wholesale prices are available from 2006 in bulk units, while retail prices (per KG) are only available from August 2019.
- Approximately two thirds of records are flagged as `aggregate` rather than `actual`.
- The table contains 37,765 rows, compared with the 38,917 stated in the README.

---

## Phase 2: Preprocessing and Feature Engineering
*Begins after Phase 1 is complete.*
- [ ] Data cleaning rules, based on the findings in Phase 1 Sections 3, 4 and 9
- [ ] Unit strategy: conversion to a per-KG basis or modelling in original units
- [ ] Feature engineering: lagged prices, rolling statistics, calendar month and region
- [ ] Feature selection
- [ ] Transformations (log, encoding, scaling), fitted on the training data only
- [ ] Chronological split into training, validation and test sets, completed before any transformation is fitted

## Phase 3: Model Selection and Training
- [ ] Baseline models (naive and seasonal naive) to set a minimum benchmark
- [ ] Candidate models evaluated with time-series cross-validation

## Phase 4: Evaluation
- [ ] Performance metrics (MAE, RMSE, MAPE) on the held-out test set, compared with the baseline
- [ ] Error analysis by commodity, region and forecast horizon

## Phase 5: Post-Evaluation and Application
- [ ] Hyperparameter tuning using the validation set only
- [ ] Model interpretation and feature importance
- [ ] Monitoring and maintenance plan
