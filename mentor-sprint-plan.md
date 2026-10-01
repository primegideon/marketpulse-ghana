# Mentor Sprint Plan — MarketPulse Ghana

## Overview

Following the mentor sprint review, five improvements are required before the
final presentation. They are ordered strictly for solo execution: the logging
infrastructure must exist before anything else uses it; main.py comes next;
the corrected train/test split feeds the statistical analysis; and model
evaluation + potential switching is the final gate before the pipeline is
considered production-ready.

**Scope:** pipeline/ directory, a new main.py at the repo root,
utils/pipeline_logger.py, utils/statistical_analysis.py, an outputs/ directory
for presentation charts, and no changes to the Evidence UI or database schema
beyond adding one new table (pipeline_run_log) and updating fact_price_forecasts
with corrected model outputs.

**Non-goals:** No UI changes. No changes to the DuckDB analytical views
(fact_monthly_prices, fact_market_spreads, fact_gbvi_index,
fact_seasonal_outlook). No new dashboard pages.

**Solo execution note:** Sub-Tasks must be completed in strict sequence —
1 → 2 → 3 → 4 → 5. No parallel work.

---

## Sub-Task 1 — Pipeline Run Log Table and Shared Logger

**Status:** [ ] pending

### Intent
Right now every pipeline script logs to the console only. Logs disappear after
the run. The mentor wants a permanent audit trail written to the database so
any pipeline run — success or failure — is queryable. This sub-task creates the
shared logging infrastructure that all other sub-tasks depend on.

### Expected Outcomes
- A `pipeline_run_log` table exists in `agri_ghana.duckdb` with columns:
  run_id, script_name, status, message, rows_affected, duration_seconds, run_at
- A reusable `PipelineLogger` class in `utils/pipeline_logger.py` that any
  pipeline script can import to write a log entry (SUCCESS or ERROR) to the
  table in one call
- The logger also keeps the existing console output (Python logging) so
  nothing is lost

### Todo List
- [ ] Create `utils/pipeline_logger.py` with a `PipelineLogger` class
- [ ] On instantiation, open a DuckDB connection and CREATE TABLE IF NOT EXISTS
  `pipeline_run_log` with the columns listed above
- [ ] Implement a `log(script_name, status, message, rows_affected,
  duration_seconds)` method that inserts one row
- [ ] Implement a `success(script_name, rows_affected, duration_seconds)`
  convenience method
- [ ] Implement an `error(script_name, exception, duration_seconds)` convenience
  method that captures the exception message as the log entry
- [ ] Close the DuckDB connection after each log write (the pipeline scripts
  hold their own connections; the logger should not conflict)
- [ ] Add a `get_run_history()` method that returns the last 20 log entries as
  a DataFrame for inspection

### Relevant Context
- All five pipeline scripts currently use:
  `logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")`
- DB path constant used across all scripts: `DB_PATH = "agri_ghana.duckdb"` (or
  `db_path = "agri_ghana.duckdb"` in older scripts)
- The logger must handle the case where the database is locked by another
  process and fail gracefully with a console warning rather than crashing

---

## Sub-Task 2 — main.py Pipeline Orchestrator

**Status:** [ ] pending

### Intent
Replace the manual five-command run sequence with a single entry point. `main.py`
imports and calls each pipeline module in order, measures execution time per
step, uses the PipelineLogger from Sub-Task 1 to record each step's outcome,
and stops the pipeline if any step raises an exception (fail-fast behaviour).

### Expected Outcomes
- Running `python main.py` from the repo root executes all five pipeline steps
  in sequence: ingest → transform → analytics views → forecasting → seasonal outlook
- Each step's success or failure is written to `pipeline_run_log`
- If any step fails, subsequent steps are skipped and the error is logged; the
  process exits with a non-zero exit code
- Console output clearly shows which step is running and its result
- A `--skip-forecast` flag is supported to skip Step 4 (Prophet training is slow;
  useful for quick data refreshes)

### Todo List
- [ ] Create `main.py` at the repo root
- [ ] Import the `main()` function from each of the five pipeline modules
- [ ] Wrap each call in a try/except block; catch all exceptions, log via
  PipelineLogger, and call `sys.exit(1)` on failure
- [ ] Use `time.perf_counter()` to measure and log duration per step
- [ ] Print a summary table to the console at the end showing each step,
  status, rows affected, and duration
- [ ] Add `argparse` with a single `--skip-forecast` flag that bypasses Step 4
- [ ] Update README.md Local Setup section to replace the five-command sequence
  with `python main.py`

### Relevant Context
- Each pipeline script already has a `main()` function and a
  `if __name__ == "__main__": main()` guard — they are importable without
  side effects
- Step 4 (`4_run_forecasting.py`) is the slowest step by far due to Prophet
  training; the skip flag makes day-to-day development faster
- The pipeline scripts use relative paths (`"agri_ghana.duckdb"`) so `main.py`
  must be run from the repo root — document this constraint

---

## Sub-Task 3 — Corrected ML Train/Test Split

**Status:** [x] done

### Intent
The current 80/20 chronological split puts all three macroeconomic shocks
(COVID 2020, Russia-Ukraine 2022, cedi crisis 2022) in the test set, where the
model has never seen them. The mentor's fix: train on 2006 through mid-2022
(so the model absorbs the shocks), and test on the final 6 months of the
dataset (a clean out-of-sample window). This produces a more honest and
meaningful MAPE and directional accuracy score.

### Expected Outcomes
- `4_run_forecasting.py` uses a fixed training cutoff of `2022-12-31` and a
  test window of `2023-01-01` to the end of the dataset
- Model MAPE and directional accuracy are re-evaluated on this new test window
- The `evaluate_model()` function accepts explicit `train_end` and `test_start`
  parameters instead of a percentage split
- `fact_price_forecasts` is rebuilt with updated accuracy metrics
- Log entries written via PipelineLogger for each commodity's evaluation result

### Todo List
- [ ] Replace the `int(n_months * 0.8)` percentage split in `evaluate_model()`
  with a date-based split using `train_end = "2022-12-31"` and
  `test_start = "2023-01-01"` as module-level constants
- [ ] Update `evaluate_model()` signature to accept optional `train_end` and
  `test_start` string parameters (defaulting to the new constants)
- [ ] Update the `fit_and_forecast()` function to also log the training data
  date range in its console output so it is clear what window was used
- [ ] Re-run the pipeline locally to rebuild `fact_price_forecasts` with the
  corrected metrics
- [ ] Add a comment block above the new constants explaining the rationale
  (shocks absorbed in training, clean OOS test)
- [ ] Integrate PipelineLogger from Sub-Task 1 to write per-commodity
  evaluation results to `pipeline_run_log`

### Relevant Context
- `evaluate_model()` is in `pipeline/4_run_forecasting.py` around line 316
- The training data covers `2006-01-01` to `2023-07-01` (latest WFP observation)
- `KNOWN_CHANGEPOINTS` are already defined: 2020-03-01, 2022-02-01, 2022-07-01
  — all will now fall within the training window under the new split, which is
  exactly the intent
- The existing `naive_mape()` function and `directional_accuracy()` function
  do not need changes — only the split logic in `evaluate_model()` changes
- `FORECAST_MONTHS = 3` stays unchanged — the forward projection horizon is
  separate from the evaluation split

---

## Sub-Task 4 — Statistical Analysis Module

**Status:** [ ] pending

### Intent
Before trusting a time-series model, you must understand the statistical
properties of the data. This sub-task adds a dedicated analysis script that
produces four outputs: a correlation matrix between commodity prices and
GHS/USD FX rates, ADF stationarity tests per commodity, ACF/PACF
autocorrelation plots, and a shock impact quantification that isolates
currency-driven inflation from supply-driven inflation. These outputs tell
the full analytical story for the presentation.

### Expected Outcomes
- A new script `utils/statistical_analysis.py` that runs end-to-end and saves
  all charts to a `outputs/` directory as PNG files
- **Correlation matrix:** Pearson correlation between monthly retail prices of
  each core staple and the GHS/USD rate; output as a heatmap PNG
- **ADF stationarity test:** Augmented Dickey-Fuller test per commodity price
  series; console output shows ADF statistic, p-value, and a plain-English
  verdict (stationary / non-stationary)
- **ACF/PACF plots:** Autocorrelation and partial autocorrelation plots per
  commodity saved as PNG; reveals how many months of price history carry
  predictive signal
- **Shock impact quantification:** For each commodity, split the MoM price
  change into the FX-explained component (FX rate change × correlation
  coefficient) and the residual supply-demand component; output as a stacked
  bar chart showing the proportion of price change attributable to FX vs
  other factors, specifically for the 2022–2023 shock period
- All four analyses are runnable with a single `python utils/statistical_analysis.py`

### Todo List
- [ ] Create `utils/statistical_analysis.py`
- [ ] Connect to `agri_ghana.duckdb` (read-only) and load:
    - Monthly retail prices per commodity from `fact_monthly_prices`
    - Monthly GHS/USD FX series from the `build_monthly_fx_series()` function
      in `pipeline/4_run_forecasting.py` (import and reuse it)
- [ ] Create `outputs/` directory if it does not exist
- [ ] **Correlation matrix:** compute Pearson correlation between each
  commodity's monthly price and the GHS/USD rate; plot as a seaborn heatmap;
  save to `outputs/correlation_matrix.png`
- [ ] **ADF test:** run `statsmodels.tsa.stattools.adfuller` on each commodity
  price series; print ADF statistic, p-value, and verdict; if p-value > 0.05
  the series is non-stationary (which is expected for Ghana food prices given
  the upward trend)
- [ ] **ACF/PACF plots:** use `statsmodels.graphics.tsaplots.plot_acf` and
  `plot_pacf` for each commodity; save to `outputs/acf_pacf_{commodity}.png`
- [ ] **Shock quantification:** for the period 2022-01-01 to 2023-07-01,
  compute for each commodity: FX contribution = FX MoM change × correlation
  coefficient; residual = total MoM change − FX contribution; plot as a
  grouped bar chart per month saved to `outputs/shock_decomposition.png`
- [ ] Add `statsmodels` and `seaborn` to `pipeline/requirements.txt`
- [ ] Log run completion to `pipeline_run_log` via PipelineLogger

### Relevant Context
- Monthly FX series is already built in `pipeline/4_run_forecasting.py` via
  `build_monthly_fx_series()` — import and reuse it, do not duplicate the logic
- Core staples list: maize, cassava, rice (local), rice (imported),
  plantains (apentu), tomatoes (local) — same as `STAPLES` in `4_run_forecasting.py`
- `fact_monthly_prices` has `month_start`, `commodity_name`, `avg_price_per_kg_ghs`,
  `price_type` — filter on `price_type = 'retail'` and aggregate nationally
  (average across all regions) before running the analysis
- `statsmodels` is not currently in requirements.txt — must be added
- `seaborn` is not currently in requirements.txt — must be added
- Output charts will be used directly in the presentation slides — PNG format
  at 150 DPI minimum

---

## Sub-Task 5 — Model Evaluation, Fine-Tuning, and Potential Model Switch

**Status:** [ ] pending

### Intent
After the corrected train/test split (Sub-Task 3) and statistical analysis
(Sub-Task 4) are complete, the model's true performance on an honest test window
is known. This sub-task evaluates whether Prophet is still the right model, and
if not, identifies and implements a better-suited alternative. The decision is
data-driven: if Prophet's directional accuracy on the corrected split is below
60% for the majority of commodities, a switch is warranted. If it is above 60%
but MAPE is high, fine-tuning is the path. If both metrics are acceptable,
no change is needed.

### Expected Outcomes
- A `utils/model_evaluation_report.py` script that runs all candidate models
  on the same corrected train/test split and prints a comparison table showing
  MAPE and directional accuracy side-by-side per commodity
- A clear decision is made and documented in a comment block at the top of
  `pipeline/4_run_forecasting.py`: Prophet retained, Prophet fine-tuned, or
  switched to alternative model
- If switched: the new model is implemented inside `4_run_forecasting.py`
  replacing Prophet, keeping the same function signatures (`fit_and_forecast`,
  `evaluate_model`) so `main.py` requires no changes
- `fact_price_forecasts` is rebuilt with the final model's outputs
- `outputs/model_comparison.png` saved — a bar chart of MAPE and directional
  accuracy per commodity per candidate model, for use in the presentation

### Decision Framework

| Scenario | Action |
|---|---|
| Prophet directional accuracy >= 60% majority of commodities | Retain Prophet, tune hyperparameters only |
| Prophet directional accuracy < 60% but high FX correlation confirmed | Switch to ARIMAX — handles external regressors cleanly, well-suited to non-stationary series with known drivers |
| Price series confirmed stationary by ADF (p < 0.05) | SARIMA is sufficient — no external regressor needed |
| Series is non-stationary AND FX correlation is weak | Switch to XGBoost with lag features — no stationarity assumption, handles structural breaks via feature engineering |

### Candidate Models to Evaluate

**Prophet (current)**
- Strengths: handles seasonality, accepts external regressors, interpretable
- Weaknesses: assumes recoverable trend; struggles with permanent structural
  level shifts like the cedi depreciation

**ARIMAX**
- Best fit when: ADF confirms non-stationarity after differencing, and FX
  correlation is strong (r > 0.6)
- Implementation: `statsmodels.tsa.statespace.SARIMAX` with GHS/USD as
  exogenous variable, order selection via AIC minimisation
- Already available: statsmodels added in Sub-Task 4

**XGBoost with lag features**
- Best fit when: structural breaks make parametric models unreliable
- Implementation: features = [price_lag_1, price_lag_2, price_lag_3,
  month_of_year, usd_ghs, mom_pct_lag_1]; target = next month price
- Requires adding `xgboost` to requirements.txt

### Fine-Tuning Options for Prophet (if retained)
- Increase `changepoint_prior_scale` from 0.15 to 0.3–0.5 to allow sharper
  trend breaks during the cedi crisis period
- Add a custom monthly seasonality component in addition to yearly
- Add 2023-specific changepoints if the cedi stabilisation in Q1 2023 is
  reflected in the data

### Todo List
- [ ] Create `utils/model_evaluation_report.py`
- [ ] Load the corrected train/test split data for each commodity (reuse
  the date-based split constants from Sub-Task 3)
- [ ] Implement evaluation for Prophet (current config) as baseline
- [ ] Implement evaluation for ARIMAX using statsmodels SARIMAX; use AIC to
  select p, d, q order (test p and q in range 0–3, d=1 for non-stationary)
- [ ] Implement evaluation for XGBoost with the lag feature set defined above
- [ ] Print a comparison table: commodity | model | MAPE | directional_accuracy
- [ ] Save `outputs/model_comparison.png` as a grouped bar chart
- [ ] Based on the comparison table, make the documented decision
- [ ] If switching: replace Prophet implementation inside `4_run_forecasting.py`
  while keeping `fit_and_forecast()` and `evaluate_model()` function signatures
  intact
- [ ] If fine-tuning: update Prophet hyperparameters in `4_run_forecasting.py`
  and re-run evaluation to confirm improvement
- [ ] Rebuild `fact_price_forecasts` by running `python main.py`
- [ ] Add `xgboost` to `pipeline/requirements.txt` if XGBoost is selected
- [ ] Log final model decision and per-commodity metrics to `pipeline_run_log`

### Relevant Context
- `fit_and_forecast()` is in `pipeline/4_run_forecasting.py` around line 253
- `evaluate_model()` is in `pipeline/4_run_forecasting.py` around line 316
- `statsmodels` will already be installed from Sub-Task 4
- ADF test results from Sub-Task 4 will determine which candidate model is
  the strongest theoretical fit before empirical comparison
- The FX correlation values from Sub-Task 4 will indicate whether an
  exogenous regressor is worth keeping
- Ghana food price series are expected to be non-stationary (upward trend +
  structural breaks) — ADF will likely confirm this, which favours ARIMAX
  or XGBoost over a plain ARIMA

---

## Execution Order — Solo

```
Sub-Task 1 — PipelineLogger (utils/pipeline_logger.py)
    ↓
Sub-Task 2 — main.py Orchestrator
    ↓
Sub-Task 3 — Corrected Train/Test Split (4_run_forecasting.py)
    ↓
Sub-Task 4 — Statistical Analysis (utils/statistical_analysis.py)
    ↓
Sub-Task 5 — Model Evaluation and Decision (utils/model_evaluation_report.py)
```

Each sub-task must be fully complete and tested before starting the next.
