# MarketPulse Ghana - Data Dictionary & Governance Catalog

This document defines the physical schema, grain, primary keys, calculation logic, units of measure, and business definitions for all analytical layers modeled in DuckDB (`agri_ghana.duckdb`) and presented through Evidence.dev.

---

## 1. Architectural Modeling Flow

```
┌─────────────────────────────────┐
│   Raw HDX Ingestion Tables      │  raw_wfp_prices (39,038 rows)
│   (Ingested from WFP CSVs)      │  raw_wfp_markets (93 rows)
│                                 │  raw_wfp_prices_previous (snapshot)
│                                 │  meta_pipeline_runs (operational audit trail)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│         Staging Views           │  • stg_food_prices (unit normalization, per-kg mappings, typed columns)
│    (Data Hygiene & Typing)      │  • stg_markets (Title Case regions, verified coordinates)
└────────────────┬────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌──────────────┐   ┌──────────────┐
│  Dimensions  │   │  Analytics   │  • mart_commodity_monthly (Temporal MoM/YoY & Moving Avgs)
│  • calendar  │   │    Marts     │  • mart_regional_spreads (Market vs. National Price Spreads)
│  • markets   │   └──────────────┘  • mart_wholesale_retail_margins (Trade Markups)
│  • crops     │                     • mart_pipeline_health (Pipeline Observability View)
└──────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  Governance & Anomaly Logging   │  • audit_data_anomalies (Quarantined irregular records)
│  (Data Quality & Auditability)  │  • meta_pipeline_runs (Pipeline execution telemetry)
└─────────────────────────────────┘
```

---

## 2. Raw Ingestion Layer

### `raw_wfp_prices`
* **Type**: DuckDB Table
* **Description**: Unmodified food price survey records ingested directly from WFP HDX via `scripts/ingest_hdx.py`. Preserved verbatim from the source CSV.

| Column | Data Type | Description |
| :--- | :--- | :--- |
| `date` | `VARCHAR` / `DATE` | Survey observation date as reported. |
| `admin1` | `VARCHAR` | Administrative region (UPPERCASE as published by WFP). |
| `admin2` | `VARCHAR` | District or sub-district name. |
| `market` | `VARCHAR` | Market trade node name. |
| `market_id` | `VARCHAR` | WFP market integer identifier. |
| `latitude` | `VARCHAR` | Market latitude coordinate string. |
| `longitude` | `VARCHAR` | Market longitude coordinate string. |
| `category` | `VARCHAR` | Food commodity category. |
| `commodity` | `VARCHAR` | Commodity name as published. |
| `commodity_id` | `VARCHAR` | WFP global commodity reference ID. |
| `unit` | `VARCHAR` | Observed market packaging unit (e.g. `100 KG`, `Olonka`, `Bunch`). |
| `priceflag` | `VARCHAR` | WFP data quality flag for the observation (`actual`, `aggregate`, `estimated`). |
| `pricetype` | `VARCHAR` | Value chain tier (`Wholesale` or `Retail`). |
| `currency` | `VARCHAR` | Currency denomination (`GHS` or `USD`). |
| `price` | `VARCHAR` | Observed price in Ghanaian Cedis (GHS). |
| `usdprice` | `VARCHAR` | Observed price in USD at prevailing exchange rate. |

### `raw_wfp_markets`
* **Type**: DuckDB Table
* **Description**: Market reference directory from WFP HDX (93 rows). One row per monitored market node.

| Column | Data Type | Description |
| :--- | :--- | :--- |
| `market_id` | `VARCHAR` | WFP market identification integer. |
| `market` | `VARCHAR` | Market trade hub name. |
| `countryiso3` | `VARCHAR` | ISO 3166-1 alpha-3 country code (`GHA`). |
| `admin1` | `VARCHAR` | Administrative region name (UPPERCASE). |
| `admin2` | `VARCHAR` | District name. |
| `latitude` | `VARCHAR` | Geographic latitude string. |
| `longitude` | `VARCHAR` | Geographic longitude string. |

### `raw_wfp_prices_previous`
* **Type**: DuckDB Table (conditional — created on second and subsequent pipeline runs)
* **Description**: Preserved snapshot of the previous `raw_wfp_prices` table, created automatically by `ingest_hdx.py` before each ingestion cycle to enable longitudinal change detection.

### `meta_pipeline_runs`
* **Type**: DuckDB Table
* **Primary Key**: `run_id`
* **Description**: Operational telemetry and audit execution trail logging data pipeline runs. Written by both `ingest_hdx.py` (`pipeline_step = 'hdx_raw_ingestion'`) and `build_marts.py` (`pipeline_step = 'build_analytical_marts'`).

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `run_id` | `VARCHAR` | No | Primary Key. Pipeline execution run identifier (`build_YYYYMMDD_HHMMSS` or `run_YYYYMMDD_HHMMSS`). | `build_20261019_072901` |
| `started_at` | `TIMESTAMPTZ` | No | UTC timestamp (with timezone) when run began. | `2026-10-19 07:29:01+00` |
| `completed_at` | `TIMESTAMPTZ` | No | UTC timestamp (with timezone) when run completed. | `2026-10-19 07:29:05+00` |
| `pipeline_step` | `VARCHAR` | No | Name of executed pipeline step (`build_analytical_marts`, `hdx_raw_ingestion`). | `build_analytical_marts` |
| `status` | `VARCHAR` | No | Execution status (`SUCCESS` or `FAILED`). | `SUCCESS` |
| `records_affected` | `BIGINT` | No | Number of records transformed or ingested. | `3534` |
| `execution_time_s` | `DOUBLE` | No | Pipeline execution duration in seconds. | `1.06` |
| `error_details` | `VARCHAR` | Yes | Error traceback message if run failed; NULL on success. | `NULL` |

---

## 3. Staging Layer

### `stg_food_prices`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Grain / Composite Key**: `(date, market_id, commodity_id, raw_unit, price_type)`
* **Source**: `raw_wfp_prices`
* **Description**: Cleansed and standardized price observations. Handles Title Case regional normalization, TIMESTAMPTZ-safe date truncation to first-of-month, currency standardization, and mass/volume conversion factors to kilograms. Zero and NULL prices are filtered out at this layer (`WHERE price IS NOT NULL AND price > 0`).

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `date` | `DATE` | No | Observation date truncated to first day of the reporting month (`YYYY-MM-01`) via `DATE_TRUNC('month', date::DATE)`. | `2023-07-01` |
| `calendar_year` | `BIGINT` | No | Extracted calendar year. | `2023` |
| `calendar_month` | `BIGINT` | No | Extracted calendar month number (1–12). | `7` |
| `month_name` | `VARCHAR` | No | Full English month name derived from date. | `July` |
| `year_month` | `VARCHAR` | No | Calendar month identifier (`YYYY-MM`). | `2023-07` |
| `region` | `VARCHAR` | No | Administrative region normalized to Title Case (10 legacy regions). `BRONG AHAFO` → `Brong-Ahafo`, `NORTHERN` → `Northern`, etc. | `Greater Accra` |
| `district` | `VARCHAR` | Yes | District or sub-district name (passed through from `admin2`). | `Accra Metropolis` |
| `market` | `VARCHAR` | No | Standardized market name. | `Accra` |
| `market_id` | `BIGINT` | No | Unique WFP market identifier cast to integer. | `153` |
| `latitude` | `DOUBLE` | Yes | Market geographic latitude (WGS84). | `5.5502` |
| `longitude` | `DOUBLE` | Yes | Market geographic longitude (WGS84). | `-0.2174` |
| `category` | `VARCHAR` | No | Broad food commodity group (e.g. `cereals and tubers`, `pulses and nuts`, `vegetables and fruits`). | `cereals and tubers` |
| `commodity` | `VARCHAR` | No | Standardized commodity name. | `Maize` |
| `commodity_id` | `BIGINT` | No | Unique WFP commodity identifier cast to integer. | `51` |
| `raw_unit` | `VARCHAR` | No | Unit of sale reported in market surveys (`100 KG`, `50 KG`, `KG`, `Olonka`, `Tubers`, `Bunch`, etc.). | `100 KG` |
| `unit_weight_kg` | `DOUBLE` | Yes | Numeric kilogram weight extracted via regex from the unit string (`100 KG` → `100.0`, bare `KG` → `1.0`). `NULL` for non-mass units such as `Tubers` or `Bunch`. | `100.0` |
| `unit_family` | `VARCHAR` | No | Canonical unit categorization: `'Mass / Weight'` (any unit containing `KG`) or `'Piece / Count'` (tubers, bunches, and all other units). | `Mass / Weight` |
| `price_flag` | `VARCHAR` | No | WFP data quality flag for the observation (`actual`, `aggregate`, `estimated`). Passed through from `priceflag`. | `actual` |
| `price_type` | `VARCHAR` | No | Point in the value chain (`Wholesale` or `Retail`). | `Wholesale` |
| `currency` | `VARCHAR` | No | Currency denomination (`GHS`). | `GHS` |
| `price_ghs` | `DOUBLE` | No | Observed price in Ghanaian Cedis (GHS). | `350.0` |
| `price_usd` | `DOUBLE` | No | Observed price in US Dollars (USD) at prevailing exchange rate. | `31.25` |
| `price_ghs_per_kg` | `DOUBLE` | Yes | Standardized unit price in GHS: `price_ghs / unit_weight_kg`. `NULL` for non-mass units (`unit_family = 'Piece / Count'`). | `3.50` |
| `price_usd_per_kg` | `DOUBLE` | Yes | Standardized unit price in USD: `price_usd / unit_weight_kg`. `NULL` for non-mass units. | `0.31` |

---

### `stg_markets`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Grain / Primary Key**: `market_id`
* **Source**: `raw_wfp_markets`
* **Description**: Market reference table with administrative names normalized to Title Case and coordinates cast to `DOUBLE`. Used as the authoritative spatial join source for `dim_markets`.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `market_id` | `BIGINT` | No | Primary Key. WFP market integer identifier. | `153` |
| `market` | `VARCHAR` | No | Market trade hub name. | `Accra` |
| `country_iso3` | `VARCHAR` | No | ISO 3166-1 alpha-3 country code (`GHA` for all records). | `GHA` |
| `region` | `VARCHAR` | No | Administrative region normalized to Title Case (same 10-region mapping as `stg_food_prices`). | `Greater Accra` |
| `district` | `VARCHAR` | Yes | District or sub-district name passed through from `admin2`. | `Accra Metropolis` |
| `latitude` | `DOUBLE` | Yes | Geographic latitude (WGS84). | `5.5502` |
| `longitude` | `DOUBLE` | Yes | Geographic longitude (WGS84). | `-0.2174` |

---

## 4. Dimension Layer

### `dim_commodities`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Primary Key**: `commodity`
* **Source**: Aggregated from `stg_food_prices`
* **Description**: Master catalog of all monitored food crops, categories, packaging units, and observation metadata.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `commodity_id` | `BIGINT` | No | WFP global commodity reference ID. | `52` |
| `commodity` | `VARCHAR` | No | Primary Key. Standardized commodity name. | `Cassava` |
| `category` | `VARCHAR` | No | Agro-food classification (`cereals and tubers`, `pulses and nuts`, `vegetables and fruits`, etc.). | `cereals and tubers` |
| `units_available` | `BIGINT` | No | Count of distinct packaging unit types observed for this commodity across all records. | `3` |
| `wholesale_units` | `VARCHAR` | No | Comma-separated list of distinct packaging units observed in Wholesale transactions. `N/A` if none. | `100 KG, 50 KG` |
| `retail_units` | `VARCHAR` | No | Comma-separated list of distinct packaging units observed in Retail transactions. `N/A` if none. | `KG, Bunch` |
| `reported_units` | `VARCHAR` | No | Comma-separated list of all distinct units reported across both price types combined. | `100 KG, 50 KG, KG` |
| `total_observations` | `BIGINT` | No | Total raw survey records for this commodity across all markets and dates. | `1520` |
| `first_recorded_date` | `DATE` | No | Earliest observation date in the dataset for this commodity. | `2006-01-01` |
| `last_recorded_date` | `DATE` | No | Most recent observation date for this commodity. | `2023-07-01` |

---

### `dim_markets`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Primary Key**: `market`
* **Source**: `stg_markets` LEFT JOIN observation statistics from `stg_food_prices`
* **Description**: Spatial reference catalog of commercial hubs and rural markets across Ghana, enriched with trading activity statistics and market tier classification.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `market_id` | `BIGINT` | No | WFP market identification integer. | `153` |
| `market` | `VARCHAR` | No | Primary Key. Market trade hub name. | `Tamale` |
| `country_iso3` | `VARCHAR` | No | ISO 3166-1 alpha-3 country code (`GHA`). | `GHA` |
| `region` | `VARCHAR` | No | Normalized Title Case administrative region (10 legacy boundaries). | `Northern` |
| `district` | `VARCHAR` | Yes | Sub-district level geographic name. | `Tamale Metropolis` |
| `latitude` | `DOUBLE` | Yes | Geographic latitude (WGS84). | `9.4008` |
| `longitude` | `DOUBLE` | Yes | Geographic longitude (WGS84). | `-0.8393` |
| `total_observations` | `BIGINT` | No | Total price survey records recorded for this market across all commodities and dates. `0` for inactive markets. | `1842` |
| `commodities_monitored` | `BIGINT` | No | Count of distinct commodities with price observations in this market. | `18` |
| `first_observation_date` | `DATE` | Yes | Earliest date of any price observation for this market. `NULL` for inactive markets. | `2006-01-01` |
| `last_observation_date` | `DATE` | Yes | Most recent price observation date for this market. `NULL` for inactive markets. | `2023-07-01` |
| `market_tier` | `VARCHAR` | No | Commercial importance classification: `'Major National Hub'` (Accra, Tema, Kumasi), `'Regional Center'` (Tamale, Cape Coast, Sekondi/Takoradi, Sunyani, Bolgatanga, Wa, Bawku, Koforidua, Ho), or `'Local Market'` for all others. | `Regional Center` |

---

### `dim_calendar`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Primary Key**: `date`
* **Source**: Derived from `DISTINCT date` values in `stg_food_prices`
* **Description**: Temporal dimension table covering all months observed in the dataset (January 2006 – July 2023). Includes Ghana-specific agricultural season classification.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `date` | `DATE` | No | Primary Key. First day of month (`YYYY-MM-01`). | `2020-01-01` |
| `year` | `BIGINT` | No | Calendar year (`YYYY`). | `2020` |
| `quarter` | `BIGINT` | No | Calendar quarter (`1` to `4`). | `1` |
| `month` | `BIGINT` | No | Month number (`1` to `12`). | `1` |
| `month_name` | `VARCHAR` | No | Full English month name. | `January` |
| `year_month` | `VARCHAR` | No | Month identifier (`YYYY-MM`). | `2020-01` |
| `agricultural_season` | `VARCHAR` | No | Ghana agro-ecological season classification derived from calendar month: `'Major Harvest'` (Aug–Nov), `'Post-Harvest'` (Dec–Jan), `'Lean Season'` (May–Jul), `'Minor Season'` (Feb–Apr). Encodes predictable cyclical price dynamics directly into the data model. | `Lean Season` |

**Agricultural Season Mapping Logic:**
```sql
CASE
    WHEN month(date) IN (8, 9, 10, 11) THEN 'Major Harvest'   -- Peak supply, falling prices
    WHEN month(date) IN (12, 1)         THEN 'Post-Harvest'    -- Post-harvest stock buildup
    WHEN month(date) IN (5, 6, 7)       THEN 'Lean Season'     -- Granary depletion, rising prices
    ELSE                                     'Minor Season'     -- Feb–Apr (South minor crop cycle)
END AS agricultural_season
```

---

## 5. Analytical Mart Layer

### `mart_commodity_monthly`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Grain / Composite Key**: `(date, commodity, raw_unit, price_type)`
* **Source**: Aggregated from `stg_food_prices` with window functions for temporal lags
* **Description**: Monthly national aggregated commodity benchmarks, moving averages, and strictly calendar-validated MoM/YoY growth rates. The critical design decision is strict DATEDIFF validation on all LAG() comparisons to prevent false inflation spikes from survey gaps.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `year_month` | `VARCHAR` | No | Calendar month (`YYYY-MM`). | `2023-06` |
| `date` | `DATE` | No | Reporting date (`YYYY-MM-01`). | `2023-06-01` |
| `category` | `VARCHAR` | No | Food commodity category. | `cereals and tubers` |
| `commodity` | `VARCHAR` | No | Commodity name. | `Maize` |
| `commodity_id` | `BIGINT` | No | Commodity reference ID. | `51` |
| `raw_unit` | `VARCHAR` | No | Reported market packaging unit. | `100 KG` |
| `unit_family` | `VARCHAR` | No | Canonical unit category: `'Mass / Weight'` or `'Piece / Count'`. | `Mass / Weight` |
| `price_type` | `VARCHAR` | No | Value chain tier (`Wholesale` or `Retail`). | `Wholesale` |
| `median_price_ghs` | `DOUBLE` | No | National median reported price in GHS across all reporting markets. | `420.0` |
| `median_price_usd` | `DOUBLE` | No | National median reported price in USD. | `38.18` |
| `median_price_ghs_per_kg` | `DOUBLE` | Yes | National median price normalized per kilogram. `NULL` for non-mass (`Piece / Count`) units. | `4.20` |
| `min_price_ghs` | `DOUBLE` | No | Lowest price recorded across all reporting markets in month. | `380.0` |
| `max_price_ghs` | `DOUBLE` | No | Highest price recorded across all reporting markets in month. | `480.0` |
| `markets_reporting` | `BIGINT` | No | Number of distinct markets reporting prices for this commodity in month. | `14` |
| `observations_count` | `BIGINT` | No | Total raw survey records aggregated into this monthly row. | `22` |
| `prev_month_price_ghs` | `DOUBLE` | Yes | National median price from preceding month. **Strict calendar validation**: only populated when `DATEDIFF('day', prev_date, date) BETWEEN 27 AND 35`. Returns `NULL` for non-contiguous survey gaps, preventing false inflation spikes. | `390.0` |
| `prev_year_price_ghs` | `DOUBLE` | Yes | National median price from same month one year prior. **Strict calendar validation**: only populated when `DATEDIFF('day', prev_12_date, date) BETWEEN 350 AND 380`. | `260.0` |
| `moving_avg_3m_ghs` | `DOUBLE` | Yes | 3-month trailing moving average price (RANGE INTERVAL '2' MONTH PRECEDING to CURRENT ROW). | `400.0` |
| `moving_avg_12m_ghs` | `DOUBLE` | Yes | 12-month trailing moving average price (RANGE INTERVAL '11' MONTH PRECEDING to CURRENT ROW). | `320.5` |
| `mom_pct_change` | `DOUBLE` | Yes | Month-over-Month price change (%): `((curr - prev_month) / prev_month) * 100`. `NULL` when `prev_month_price_ghs` is `NULL` (non-contiguous period). | `7.69` |
| `yoy_pct_change` | `DOUBLE` | Yes | Year-over-Year price change (%): `((curr - prev_year) / prev_year) * 100`. `NULL` when `prev_year_price_ghs` is `NULL`. | `61.54` |

---

### `mart_regional_spreads`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Grain / Composite Key**: `(date, market, commodity, raw_unit, price_type)`
* **Source**: Market-level medians from `stg_food_prices` joined to national medians from `mart_commodity_monthly`
* **Description**: Spatial price disparities comparing individual market prices to the national median benchmark. Enables identification of consumer import premiums in coastal hubs and surplus producer discounts in northern farming regions.

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
| `market_median_ghs` | `DOUBLE` | No | Median price in this specific market for this month. | `450.0` |
| `market_median_ghs_per_kg` | `DOUBLE` | Yes | Median price per kilogram in this specific market. `NULL` for non-mass units. | `4.84` |
| `national_median_ghs` | `DOUBLE` | No | National benchmark median price across all reporting markets. | `490.0` |
| `national_median_ghs_per_kg` | `DOUBLE` | Yes | National benchmark median price per kilogram. `NULL` for non-mass units. | `5.27` |
| `spread_to_national_ghs` | `DOUBLE` | No | Absolute price difference: `market_median_ghs - national_median_ghs`. Negative = producing surplus hub; positive = consumer import premium. | `-40.0` |
| `spread_to_national_pct` | `DOUBLE` | Yes | Percentage spread: `(spread_to_national_ghs / national_median_ghs) * 100`. | `-8.16` |
| `spread_to_national_per_kg` | `DOUBLE` | Yes | Per-kg absolute difference: `market_per_kg - national_per_kg`. | `-0.43` |
| `spread_to_national_per_kg_pct` | `DOUBLE` | Yes | Per-kg percentage spread relative to national per-kg benchmark. | `-8.16` |

---

### `mart_wholesale_retail_margins`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Grain / Composite Key**: `(date, commodity, market)`
* **Source**: `stg_food_prices` pivot (MEDIAN of Wholesale and Retail `price_ghs_per_kg` per commodity-market-month)
* **Description**: Paired wholesale-to-retail trade margins, gross markups, and verification quarantine flags. Aggregates via `MEDIAN()` to guard against outlier skew. Observations are filtered to `price_ghs_per_kg >= 0.20` to exclude implausible outlier transactions.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `year_month` | `VARCHAR` | No | Calendar month (`YYYY-MM`). | `2022-11` |
| `date` | `DATE` | No | Reporting date (`YYYY-MM-01`). | `2022-11-01` |
| `market_id` | `BIGINT` | No | Market identifier. | `153` |
| `market` | `VARCHAR` | No | Market name. | `Accra` |
| `region` | `VARCHAR` | No | Administrative region. | `Greater Accra` |
| `commodity_id` | `BIGINT` | No | Commodity reference ID. | `51` |
| `commodity` | `VARCHAR` | No | Commodity name. | `Maize` |
| `wholesale_price_per_kg` | `DOUBLE` | No | Median observed wholesale price per kilogram in GHS. Minimum floor: `0.20 GHS/kg`. | `3.20` |
| `retail_price_per_kg` | `DOUBLE` | No | Median observed retail price per kilogram in GHS. Minimum floor: `0.20 GHS/kg`. | `4.10` |
| `margin_per_kg_ghs` | `DOUBLE` | No | Gross margin per kilogram: `retail_price_per_kg - wholesale_price_per_kg`. | `0.90` |
| `retail_markup_pct` | `DOUBLE` | Yes | Commercial trade markup percentage: `((retail - wholesale) / wholesale) * 100`. `NULL` when `wholesale_price_per_kg = 0`. | `28.13` |
| `is_verified_margin` | `BOOLEAN` | No | Quality assertion flag. `TRUE` strictly when `retail_price_per_kg >= wholesale_price_per_kg` AND `retail_markup_pct <= 200%`. `FALSE` for inverted (retail < wholesale) or extreme markup anomalies. The 21.6% of WFP paired records that fail this rule (e.g. farmgate unpeeled bulk vs. retail checkout) are quarantined into `audit_data_anomalies`. | `TRUE` |

---

### `mart_pipeline_health`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Source**: `meta_pipeline_runs` ordered descending by `started_at`
* **Description**: Evidence.dev-facing view of the operational pipeline audit log. Presents all pipeline execution records sorted newest-first for the governance dashboard. Surfaces both `hdx_raw_ingestion` and `build_analytical_marts` steps.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `run_id` | `VARCHAR` | No | Pipeline execution identifier. | `build_20261019_072901` |
| `started_at` | `TIMESTAMPTZ` | No | UTC run start timestamp. | `2026-10-19 07:29:01+00` |
| `completed_at` | `TIMESTAMPTZ` | No | UTC run completion timestamp. | `2026-10-19 07:29:05+00` |
| `pipeline_step` | `VARCHAR` | No | Step name (`build_analytical_marts` or `hdx_raw_ingestion`). | `build_analytical_marts` |
| `status` | `VARCHAR` | No | Execution result (`SUCCESS` or `FAILED`). | `SUCCESS` |
| `records_affected` | `BIGINT` | No | Record count processed in this step. | `3534` |
| `execution_time_s` | `DOUBLE` | No | Step duration in seconds. | `1.06` |
| `error_details` | `VARCHAR` | Yes | Error traceback (NULL on success). | `NULL` |

---

## 6. Audit & Governance Layer

### `audit_data_anomalies`
* **Type**: SQL View (`CREATE OR REPLACE VIEW`)
* **Description**: UNION of two anomaly classes quarantined from commercial reporting marts. Used by the governance dashboard to provide complete data transparency.

**Anomaly Class 1 — Margin Inversion / Outlier Markup**: Records from `mart_wholesale_retail_margins` where `is_verified_margin = FALSE`. These are observations where retail price is lower than wholesale price, or the retail markup exceeds 200%, typically caused by field enumerators recording farmgate unpeeled bulk root weights alongside retail checkout pieces.

**Anomaly Class 2 — Extreme Unit Price Outlier**: Records from `stg_food_prices` where `price_ghs_per_kg > 100.0` (implausibly expensive) or `price_ghs_per_kg < 0.05` (implausibly cheap). These are preserved in the raw audit layer and flagged for monitoring.

| Column | Data Type | Nullable | Description / Business Logic | Example |
| :--- | :--- | :---: | :--- | :--- |
| `date` | `DATE` | No | Date of irregular observation. | `2018-09-01` |
| `market` | `VARCHAR` | No | Market location reporting irregular record. | `Techiman` |
| `region` | `VARCHAR` | No | Administrative region. | `Brong-Ahafo` |
| `commodity` | `VARCHAR` | No | Food commodity. | `Yam` |
| `anomaly_type` | `VARCHAR` | No | Anomaly classification: `'Margin Inversion / Outlier Markup'` or `'Extreme Unit Price Outlier'`. | `Margin Inversion / Outlier Markup` |
| `anomaly_details` | `VARCHAR` | No | Diagnostic explanation with observed metric values. | `Wholesale GHS 4.20/kg vs Retail GHS 2.50/kg (-40.48% markup)` |
| `resolution_status` | `VARCHAR` | No | Pipeline governance action: `'Quarantined from commercial margin benchmarks'` or `'Preserved in raw audit layer; flagged for monitoring'`. | `Quarantined from commercial margin benchmarks` |

---

## 7. Automated Data Quality Test Suite (`scripts/test_marts.py`)

The project ships with **28 automated data quality assertions** executed via `python scripts/test_marts.py`. Tests are grouped into four categories:

| Category | Test Count | Scope |
| :--- | :---: | :--- |
| **Table & Mart Existence** | 10 | Verifies all required views and tables are present in `agri_ghana.duckdb`. |
| **Primary Key & Uniqueness** | 6 | Enforces PK uniqueness on all dimensions and composite keys on all marts. |
| **Non-Null Mandatory Fields** | 5 | Asserts zero NULLs in mandatory columns across staging, dimensions, and marts. |
| **Domain Logic & Value Sanity** | 7 | Price positivity, verified margin integrity, temporal and geographic coverage span. |
| **Total** | **28** | All 28 assertions currently pass with 0 failures. |

**Exit behavior**: Exits with code `0` on full pass, code `1` on any assertion failure — compatible with CI/CD pipeline failure gates.
