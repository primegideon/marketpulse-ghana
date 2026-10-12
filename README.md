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

## Exploratory analysis

The [EDA notebook](notebooks/exploratory_data_analysis.ipynb) examines data coverage, quality, price distributions, seasonality, unusual observations, and relationships between price series. In the local snapshot, the analysis found no missing values, exact duplicate rows, or duplicate record keys. It also flagged some currency-conversion inconsistencies and unusual prices for further review; flagged observations are not automatically errors and are not removed by the EDA.

All results are exploratory. The database preserves the raw WFP table, and interpretations should account for data coverage, measurement units, price type, and the snapshot's July 2023 end date.

## Run the notebook

Use Python 3.12 or a compatible version. From the project root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install duckdb numpy pandas matplotlib seaborn jupyter nbconvert ipykernel
jupyter nbconvert --to notebook --execute notebooks/exploratory_data_analysis.ipynb --inplace
```

The notebook opens `agri_ghana.duckdb` in read-only mode and expects it in the project root. Close other processes using the database if DuckDB reports a file-lock error.