# MarketPulse Ghana

MarketPulse Ghana is an AmaliTech internship capstone exploring how historical food-price data can help Ghanaian food SMEs compare markets and understand price trends and seasonality. The project will follow the roadmap in [general_ml_roadmap.html](general_ml_roadmap.html), with analysis and useful reporting as the core deliverables. Forecasting is a possible extension, not a requirement.

## Project question

How can historical WFP food-price observations help Ghanaian food businesses make better-informed decisions about where and when to buy or sell selected commodities?

The intended audience includes traders, retailers, food-service businesses, and processors. The available data can support like-for-like price comparisons, historical trend analysis, and seasonal analysis. It does not include individual businesses' purchase costs, transport costs, inventory, sales, or margins, so the project cannot estimate a specific SME's profitability.

## Data

- Source: [WFP Ghana Food Prices on HDX](https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320)
- CSV resource: [wfp_food_prices_gha.csv](https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320/resource/e877350b-146f-4fa7-8690-db9605eea78c/download/wfp_food_prices_gha.csv)
- Local database: `agri_ghana.duckdb`
- Raw table: `raw_wfp_prices`

The local snapshot contains 37,765 rows from January 2006 through July 2023. It includes wholesale and retail observations across different commodities, markets, and units. Prices should only be compared when their commodity, unit, price type, and time period are compatible.

This snapshot is historical, not a live market feed. Check the HDX resource for a newer release before presenting prices as current or attempting a forward-looking forecast. The EDA also found inconsistent USD conversions in some rows; treat the local-currency price as the primary measure unless currency handling is reviewed and justified.

## Roadmap and status

The roadmap is a guide. Each phase should be reviewed before its decisions are treated as settled.

1. **EDA:** The notebook has been executed. Its findings are marked provisional and its Phase 2 decisions remain open. The next step is to review those findings together, confirm the data-quality interpretations, and agree on the analysis scope.
2. **Preprocessing and feature engineering:** After EDA review, define comparable price series, document treatment of price flags and outliers, handle gaps, and create features appropriate to the chosen SME questions. Keep the raw source table unchanged.
3. **Modeling, if useful:** First select series with adequate coverage and establish simple time-series baselines. Do not add a forecast unless it provides useful performance beyond those baselines.
4. **Evaluation:** Use chronological or rolling-origin evaluation rather than a random split. Report forecast errors and uncertainty, and state the period and data release used.
5. **Application and reporting:** Build an Evidence.dev dashboard for validated descriptive insights. Evidence.dev and Vercel are the initial deployment ideas, not commitments; decide the final application scope after the analysis is clear.

Any forecast should be presented as an evaluated prototype, not as a guarantee or current-price recommendation. If the data is not refreshed, make its July 2023 end date prominent.

## EDA notebook

The analysis is in [notebooks/exploratory_data_analysis.ipynb](notebooks/exploratory_data_analysis.ipynb). It covers data overview, series inventory, data quality, duplicates and consistency, coverage, descriptive statistics, distributions, visualization, outlier detection, and correlation analysis.

The executed EDA reports no missing values, exact duplicate rows, or duplicate record keys. It flags 335 rows with inconsistent USD conversion, 873 cross-market outliers, and 714 month-to-month spikes for investigation; these flags are not automatic grounds for deleting observations. The notebook's findings and decisions still require review before preprocessing begins.

## Run the notebook

Use Python 3.12 or a compatible version. From the project root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install duckdb numpy pandas matplotlib seaborn jupyter nbconvert ipykernel
jupyter nbconvert --to notebook --execute notebooks/exploratory_data_analysis.ipynb --inplace
```

The notebook opens the database in read-only mode and expects `agri_ghana.duckdb` in the project root. Close other processes that have the database open if DuckDB reports a file-lock error.

## Current project files

- `agri_ghana.duckdb` - local DuckDB database containing the raw WFP table
- `general_ml_roadmap.html` - high-level project roadmap
- `notebooks/exploratory_data_analysis.ipynb` - executed EDA, pending review and sign-off
- `README.md` - project purpose, scope, status, and setup instructions