# MarketPulse Ghana - Data Dictionary & Governance Catalog

This document defines the physical schema, grain, primary keys, calculation logic, units of measure, and business definitions for all analytical layers modeled in DuckDB (`agri_ghana.duckdb`) and presented through Evidence.dev.

---

## 1. Architectural Modeling Flow

```
┌─────────────────────────────────┐
│   Raw HDX Ingestion Tables      │  raw_wfp_prices (39,038 rows)
│   (Ingested from WFP CSVs)      │  raw_wfp_markets (93 rows)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│         Staging Views           │  • stg_food_prices (Standardized prices & per-kg mappings)
│    (Data Hygiene & Typing)      │  • stg_markets (Title Case regions & coordinates)
└────────────────┬────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌──────────────┐   ┌──────────────┐
│  Dimensions  │   │  Analytics   │  • mart_commodity_monthly (Temporal MoM/YoY & Moving Avgs)
│  • calendar  │   │    Marts     │  • mart_regional_spreads (Market vs. National Price Spreads)
│  • markets   │   └──────────────┘  • mart_wholesale_retail_margins (Trade Markups)
│  • crops     │
└──────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  Governance & Anomaly Logging   │  • audit_data_anomalies (Quarantined irregular records)
│  (Data Quality & Auditability)  │  • meta_pipeline_runs (Pipeline execution telemetry)
└─────────────────────────────────┘
```

---

## 2. Staging Layer

### `stg_food_prices`
* **Type**: SQL View
* **Grain / Composite Key**: `(date, market_id, commodity_id, raw_unit, price_type)`
* **Description**: Cleansed and standardized price observations from WFP HDX. Handles Title Case regional normalization, currency standardization, and mass/volume conversion factors to kilograms.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `date` | `DATE` | No | Observation date, standardized to the first day of the reporting month (`YYYY-MM-01`). | `2023-07-01` |
| `year_month` | `VARCHAR` | No | Calendar month identifier (`YYYY-MM`). | `2023-07` |
| `market_id` | `BIGINT` | No | Unique WFP market identifier. | `153` |
| `market` | `VARCHAR` | No | Standardized market name. | `Accra` |
| `region` | `VARCHAR` | No | Administrative region, normalized to Title Case (10 legacy regions). | `Greater Accra` |
| `commodity_id` | `BIGINT` | No | Unique WFP commodity identifier. | `51` |
| `commodity` | `VARCHAR` | No | Standardized commodity name. | `Maize` |
| `category` | `VARCHAR` | No | Broad food commodity group. | `cereals and tubers` |
| `raw_unit` | `VARCHAR` | No | Unit of sale reported in market surveys (`100 KG`, `50 KG`, `KG`, `Olonka`, etc.). | `100 KG` |
| `unit_family` | `VARCHAR` | No | Broad unit categorization: `'Mass / Weight'` (KG-based), `'Piece / Count'` (tubers, bunches, items). | `Mass / Weight` |
| `unit_weight_kg` | `DOUBLE` | Yes | Numeric kilogram weight extracted from the unit string (e.g. `100 KG` → `100.0`, bare `KG` → `1.0`). `NULL` for non-mass units. | `100.0` |
| `price_type` | `VARCHAR` | No | Point in value chain (`Wholesale` or `Retail`). | `Wholesale` |
| `price_ghs` | `DOUBLE` | No | Observed price in Ghanaian Cedis (GHS). | `350.0` |
| `price_usd` | `DOUBLE` | No | Observed price in US Dollars (USD) at prevailing exchange rate. | `31.25` |
| `price_ghs_per_kg` | `DOUBLE` | Yes | Standardized unit price: `price_ghs / unit_weight_kg`. `NULL` for non-mass units. | `3.50` |

---

## 3. Dimension Layer

### `dim_commodities`
* **Type**: SQL View
* **Primary Key**: `commodity`
* **Description**: Master catalog of all monitored food crops, categories, and standardized measurement packaging.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `commodity` | `VARCHAR` | No | Primary Key. Standardized commodity name. | `Cassava` |
| `commodity_id` | `BIGINT` | No | WFP global commodity reference ID. | `52` |
| `category` | `VARCHAR` | No | Agro-food classification (`cereals and tubers`, `pulses and nuts`, `vegetables and fruits`, etc.). | `cereals and tubers` |
| `units_available` | `BIGINT` | No | Count of distinct packaging unit types observed for this commodity across all records. | `3` |
| `wholesale_units` | `VARCHAR` | No | Comma-separated list of distinct packaging units observed in Wholesale transactions. `N/A` if none. | `100 KG, 50 KG` |
| `retail_units` | `VARCHAR` | No | Comma-separated list of distinct packaging units observed in Retail transactions. `N/A` if none. | `KG, Bunch` |
| `reported_units` | `VARCHAR` | No | Comma-separated list of all distinct units reported across both price types combined. | `100 KG, 50 KG, KG` |
| `total_observations` | `BIGINT` | No | Total raw survey records for this commodity across all markets and dates. | `1520` |
| `first_recorded_date` | `DATE` | No | Earliest observation date in the dataset for this commodity. | `2006-01-01` |
| `last_recorded_date` | `DATE` | No | Most recent observation date for this commodity. | `2023-07-01` |

### `dim_markets`
* **Type**: SQL View
* **Primary Key**: `market`
* **Description**: Spatial reference catalog of commercial hubs and rural markets across Ghana.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `market` | `VARCHAR` | No | Primary Key. Market trade hub name. | `Tamale` |
| `market_id` | `BIGINT` | No | WFP market identification integer. | `168` |
| `region` | `VARCHAR` | No | Normalized Title Case administrative region. | `Northern` |
| `latitude` | `DOUBLE` | Yes | Geographic latitude (WGS84). | `9.4008` |
| `longitude` | `DOUBLE` | Yes | Geographic longitude (WGS84). | `-0.8393` |

### `dim_calendar`
* **Type**: SQL View
* **Primary Key**: `date`
* **Description**: Temporal dimension table covering January 2006 through July 2023 without gaps.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `date` | `DATE` | No | Primary Key. First day of month (`YYYY-MM-01`). | `2020-01-01` |
| `year_month` | `VARCHAR` | No | Month identifier (`YYYY-MM`). | `2020-01` |
| `year` | `BIGINT` | No | Calendar year (`YYYY`). | `2020` |
| `month` | `BIGINT` | No | Month number (`1` to `12`). | `1` |
| `month_name` | `VARCHAR` | No | Full English month name. | `January` |
| `quarter` | `BIGINT` | No | Calendar quarter (`1` to `4`). | `1` |

---

## 4. Analytical Mart Layer

### `mart_commodity_monthly`
* **Type**: SQL View
* **Grain / Composite Key**: `(date, commodity, raw_unit, price_type)`
* **Description**: Monthly national aggregated commodity benchmarks, moving averages, and strictly validated MoM/YoY growth rates.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `year_month` | `VARCHAR` | No | Calendar month (`YYYY-MM`). | `2023-06` |
| `date` | `DATE` | No | Reporting date (`YYYY-MM-01`). | `2023-06-01` |
| `category` | `VARCHAR` | No | Food commodity category. | `cereals and tubers` |
| `commodity` | `VARCHAR` | No | Commodity name. | `Maize (white)` |
| `commodity_id` | `BIGINT` | No | Commodity reference ID. | `51` |
| `raw_unit` | `VARCHAR` | No | Reported market packaging unit. | `100 KG` |
| `unit_family` | `VARCHAR` | No | Unit category (`Mass / Weight`, `Piece / Count`). | `Mass / Weight` |
| `price_type` | `VARCHAR` | No | Value chain tier (`Wholesale` or `Retail`). | `Wholesale` |
| `median_price_ghs` | `DOUBLE` | No | National median reported price in GHS. | `420.0` |
| `median_price_usd` | `DOUBLE` | No | National median reported price in USD. | `38.18` |
| `median_price_ghs_per_kg` | `DOUBLE` | Yes | National median price normalized per kilogram. NULL for non-mass units. | `4.20` |
| `min_price_ghs` | `DOUBLE` | No | Lowest price recorded across all reporting markets in month. | `380.0` |
| `max_price_ghs` | `DOUBLE` | No | Highest price recorded across all reporting markets in month. | `480.0` |
| `markets_reporting` | `BIGINT` | No | Number of distinct markets reporting prices for this commodity in month. | `14` |
| `observations_count` | `BIGINT` | No | Total raw survey records aggregated. | `22` |
| `prev_month_price_ghs` | `DOUBLE` | Yes | Price from preceding month. Strict calendar interval check (`27-35 days`); NULL if non-contiguous. | `390.0` |
| `prev_year_price_ghs` | `DOUBLE` | Yes | Price from same month 1 year prior. Strict calendar check (`350-380 days`); NULL if non-contiguous. | `260.0` |
| `moving_avg_3m_ghs` | `DOUBLE` | Yes | 3-month trailing moving average price. | `400.0` |
| `moving_avg_12m_ghs` | `DOUBLE` | Yes | 12-month trailing moving average price. | `320.5` |
| `mom_pct_change` | `DOUBLE` | Yes | Month-over-Month price change percentage: `((curr - prev_month) / prev_month) * 100`. | `7.69` |
| `yoy_pct_change` | `DOUBLE` | Yes | Year-over-Year price change percentage: `((curr - prev_year) / prev_year) * 100`. | `61.54` |

---

### `mart_regional_spreads`
* **Type**: SQL View
* **Grain / Composite Key**: `(date, market, commodity, raw_unit, price_type)`
* **Description**: Spatial price disparities comparing individual market prices to national median benchmarks.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `year_month` | `VARCHAR` | No | Calendar month (`YYYY-MM`). | `2023-05` |
| `date` | `DATE` | No | Reporting date (`YYYY-MM-01`). | `2023-05-01` |
| `region` | `VARCHAR` | No | Administrative region (Title Case). | `Northern` |
| `market` | `VARCHAR` | No | Market trade node name. | `Tamale` |
| `market_id` | `BIGINT` | No | Market reference ID. | `168` |
| `latitude` | `DOUBLE` | Yes | Market latitude coordinate. | `9.4008` |
| `longitude` | `DOUBLE` | Yes | Market longitude coordinate. | `-0.8393` |
| `commodity` | `VARCHAR` | No | Commodity name. | `Millet` |
| `commodity_id` | `BIGINT` | No | Commodity reference ID. | `73` |
| `raw_unit` | `VARCHAR` | No | Reported market packaging unit. | `93 KG` |
| `price_type` | `VARCHAR` | No | `Wholesale` or `Retail`. | `Wholesale` |
| `market_median_ghs` | `DOUBLE` | No | Median price in this specific market. | `450.0` |
| `market_median_ghs_per_kg` | `DOUBLE` | Yes | Median price per kilogram in this market. | `4.84` |
| `national_median_ghs` | `DOUBLE` | No | Benchmark national median price across all markets. | `490.0` |
| `national_median_ghs_per_kg` | `DOUBLE` | Yes | Benchmark national median price per kilogram. | `5.27` |
| `spread_to_national_ghs` | `DOUBLE` | No | Absolute price difference: `market_median_ghs - national_median_ghs`. | `-40.0` |
| `spread_to_national_pct` | `DOUBLE` | Yes | Percentage spread: `(spread / national_median) * 100`. | `-8.16` |
| `spread_to_national_per_kg` | `DOUBLE` | Yes | Per-kg price difference: `market_per_kg - national_per_kg`. | `-0.43` |
| `spread_to_national_per_kg_pct` | `DOUBLE` | Yes | Per-kg percentage spread relative to national per-kg benchmark. | `-8.16` |

---

### `mart_wholesale_retail_margins`
* **Type**: SQL View
* **Grain / Composite Key**: `(date, commodity, market)`
* **Description**: Paired wholesale-to-retail trade margins, gross markups, and verification quarantine flags.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `year_month` | `VARCHAR` | No | Calendar month (`YYYY-MM`). | `2022-11` |
| `date` | `DATE` | No | Reporting date (`YYYY-MM-01`). | `2022-11-01` |
| `market_id` | `BIGINT` | No | Market identifier. | `153` |
| `market` | `VARCHAR` | No | Market name. | `Accra` |
| `region` | `VARCHAR` | No | Administrative region. | `Greater Accra` |
| `commodity_id` | `BIGINT` | No | Commodity reference ID. | `51` |
| `commodity` | `VARCHAR` | No | Commodity name. | `Maize (white)` |
| `wholesale_price_per_kg` | `DOUBLE` | No | Observed wholesale unit price per kilogram. | `3.20` |
| `retail_price_per_kg` | `DOUBLE` | No | Observed retail unit price per kilogram. | `4.10` |
| `margin_per_kg_ghs` | `DOUBLE` | No | Gross margin per kilogram: `retail_price_per_kg - wholesale_price_per_kg`. | `0.90` |
| `retail_markup_pct` | `DOUBLE` | Yes | Commercial trade markup percentage: `((retail - wholesale) / wholesale) * 100`. | `28.13` |
| `is_verified_margin` | `BOOLEAN` | No | Quality assertion flag. `TRUE` strictly when `retail >= wholesale` and `markup <= 200%`. `FALSE` for inverted or extreme markup anomalies. | `TRUE` |

---

## 5. Audit & Operations Layer

### `audit_data_anomalies`
* **Type**: SQL View
* **Description**: Quarantined observations failing commercial or statistical sanity rules (e.g., negative trade margins or extreme outliers).

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `date` | `DATE` | No | Date of irregular observation. | `2018-09-01` |
| `market` | `VARCHAR` | No | Market location reporting irregular record. | `Techiman` |
| `region` | `VARCHAR` | No | Administrative region. | `Brong Ahafo` |
| `commodity` | `VARCHAR` | No | Food commodity. | `Yam` |
| `anomaly_type` | `VARCHAR` | No | Anomaly classification (`Margin Inversion / Outlier Markup`, `Extreme Unit Price Outlier`). | `Margin Inversion / Outlier Markup` |
| `anomaly_details` | `VARCHAR` | No | Diagnostic explanation with observed metric values. | `Wholesale GHS 4.20/kg vs Retail GHS 2.50/kg (-40.48% markup)` |
| `resolution_status` | `VARCHAR` | No | Pipeline action taken (`Quarantined from commercial margin benchmarks`). | `Quarantined from commercial margin benchmarks` |

### `meta_pipeline_runs`
* **Type**: DuckDB Table
* **Primary Key**: `run_id`
* **Description**: Operational telemetry and audit execution trail logging data pipeline runs.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `run_id` | `VARCHAR` | No | Primary Key. Pipeline execution run identifier (`build_YYYYMMDD_HHMMSS`). | `build_20261019_072901` |
| `started_at` | `TIMESTAMP_WITH_TIME_ZONE` | No | UTC timestamp when run began. | `2026-10-19 07:29:01+00` |
| `completed_at` | `TIMESTAMP_WITH_TIME_ZONE` | No | UTC timestamp when run completed. | `2026-10-19 07:29:05+00` |
| `pipeline_step` | `VARCHAR` | No | Name of executed pipeline step (`build_analytical_marts`, `ingest_hdx`). | `build_analytical_marts` |
| `status` | `VARCHAR` | No | Execution status (`SUCCESS` or `FAILED`). | `SUCCESS` |
| `records_affected` | `BIGINT` | No | Number of records transformed or ingested. | `3534` |
| `execution_time_s` | `DOUBLE` | No | Pipeline execution duration in seconds. | `1.06` |
| `error_details` | `VARCHAR` | Yes | Error traceback message if run failed; NULL on success. | `NULL` |
