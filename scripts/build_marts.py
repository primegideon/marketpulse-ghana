"""Analytical modeling pipeline for MarketPulse Ghana.

This module creates the staging, dimensional, and analytical mart layers
inside DuckDB from raw WFP datasets, establishing clean views for the
Evidence.dev web interface and recording pipeline execution metadata.
"""

from __future__ import annotations

import datetime
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("build_marts")

DEFAULT_DUCKDB_PATH = Path("agri_ghana.duckdb")


def record_pipeline_run(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
    started_at: datetime.datetime,
    completed_at: datetime.datetime,
    pipeline_step: str,
    status: str,
    records_affected: int,
    execution_time_s: float,
    error_details: Optional[str] = None,
) -> None:
    """Write execution metadata to the meta_pipeline_runs audit table."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS meta_pipeline_runs (
            run_id VARCHAR,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            pipeline_step VARCHAR,
            status VARCHAR,
            records_affected BIGINT,
            execution_time_s DOUBLE,
            error_details VARCHAR
        )
    """)

    con.execute(
        """
        INSERT INTO meta_pipeline_runs (
            run_id,
            started_at,
            completed_at,
            pipeline_step,
            status,
            records_affected,
            execution_time_s,
            error_details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            started_at,
            completed_at,
            pipeline_step,
            status,
            records_affected,
            execution_time_s,
            error_details,
        ],
    )


def build_staging_layer(con: duckdb.DuckDBPyConnection) -> None:
    """Build standardized staging views from raw tables."""
    logger.info("Building staging views: stg_food_prices and stg_markets")

    # Staging food prices: unit parsing, price per kg normalization, calendar attributes
    con.execute("""
        CREATE OR REPLACE VIEW stg_food_prices AS
        SELECT
            DATE_TRUNC('month', date::DATE)                               AS date,
            year(date::DATE)                                              AS calendar_year,
            month(date::DATE)                                             AS calendar_month,
            strftime(date::DATE, '%B')                                    AS month_name,
            strftime(date::DATE, '%Y-%m')                                 AS year_month,
            CASE admin1
                WHEN 'WESTERN' THEN 'Western'
                WHEN 'CENTRAL' THEN 'Central'
                WHEN 'ASHANTI' THEN 'Ashanti'
                WHEN 'GREATER ACCRA' THEN 'Greater Accra'
                WHEN 'EASTERN' THEN 'Eastern'
                WHEN 'UPPER WEST' THEN 'Upper West'
                WHEN 'NORTHERN' THEN 'Northern'
                WHEN 'VOLTA' THEN 'Volta'
                WHEN 'UPPER EAST' THEN 'Upper East'
                WHEN 'BRONG AHAFO' THEN 'Brong-Ahafo'
                ELSE admin1
            END                                                           AS region,
            admin2                                                        AS district,
            market                                                        AS market,
            market_id::BIGINT                                             AS market_id,
            latitude::DOUBLE                                              AS latitude,
            longitude::DOUBLE                                             AS longitude,
            category                                                      AS category,
            commodity                                                     AS commodity,
            commodity_id::BIGINT                                          AS commodity_id,
            unit                                                          AS raw_unit,
            CASE
                WHEN unit LIKE '%KG%' THEN
                    COALESCE(NULLIF(regexp_extract(unit, '([0-9]+)', 1), '')::DOUBLE, 1.0)
                ELSE NULL
            END                                                           AS unit_weight_kg,
            CASE
                WHEN unit LIKE '%KG%' THEN 'Mass / Weight'
                WHEN unit LIKE '%Tuber%' THEN 'Piece / Count'
                WHEN unit LIKE '%Bunch%' THEN 'Piece / Count'
                ELSE 'Piece / Count'
            END                                                           AS unit_family,
            priceflag                                                     AS price_flag,
            pricetype                                                     AS price_type,
            currency                                                      AS currency,
            price::DOUBLE                                                 AS price_ghs,
            usdprice::DOUBLE                                              AS price_usd,
            CASE
                WHEN unit LIKE '%KG%' THEN
                    price::DOUBLE / COALESCE(NULLIF(regexp_extract(unit, '([0-9]+)', 1), '')::DOUBLE, 1.0)
                ELSE NULL
            END                                                           AS price_ghs_per_kg,
            CASE
                WHEN unit LIKE '%KG%' THEN
                    usdprice::DOUBLE / COALESCE(NULLIF(regexp_extract(unit, '([0-9]+)', 1), '')::DOUBLE, 1.0)
                ELSE NULL
            END                                                           AS price_usd_per_kg
        FROM raw_wfp_prices
        WHERE price IS NOT NULL AND price > 0
    """)

    # Staging markets: normalized administrative naming and coordinate bounds
    con.execute("""
        CREATE OR REPLACE VIEW stg_markets AS
        SELECT
            market_id::BIGINT                                             AS market_id,
            market                                                        AS market,
            countryiso3                                                   AS country_iso3,
            CASE admin1
                WHEN 'WESTERN' THEN 'Western'
                WHEN 'CENTRAL' THEN 'Central'
                WHEN 'ASHANTI' THEN 'Ashanti'
                WHEN 'GREATER ACCRA' THEN 'Greater Accra'
                WHEN 'EASTERN' THEN 'Eastern'
                WHEN 'UPPER WEST' THEN 'Upper West'
                WHEN 'NORTHERN' THEN 'Northern'
                WHEN 'VOLTA' THEN 'Volta'
                WHEN 'UPPER EAST' THEN 'Upper East'
                WHEN 'BRONG AHAFO' THEN 'Brong-Ahafo'
                ELSE admin1
            END                                                           AS region,
            admin2                                                        AS district,
            latitude::DOUBLE                                              AS latitude,
            longitude::DOUBLE                                             AS longitude
        FROM raw_wfp_markets
    """)


def build_dimension_layer(con: duckdb.DuckDBPyConnection) -> None:
    """Build dimensional tables and views for markets, commodities, and calendar."""
    logger.info("Building dimensional views: dim_markets, dim_commodities, dim_calendar")

    # Markets dimension enriched with observation counts and trading activity
    con.execute("""
        CREATE OR REPLACE VIEW dim_markets AS
        WITH market_stats AS (
            SELECT
                market_id,
                COUNT(*)                                                  AS total_observations,
                COUNT(DISTINCT commodity)                                 AS commodities_monitored,
                MIN(date)                                                 AS first_observation_date,
                MAX(date)                                                 AS last_observation_date
            FROM stg_food_prices
            GROUP BY market_id
        )
        SELECT
            m.market_id,
            m.market,
            m.country_iso3,
            m.region,
            m.district,
            m.latitude,
            m.longitude,
            COALESCE(s.total_observations, 0)                             AS total_observations,
            COALESCE(s.commodities_monitored, 0)                          AS commodities_monitored,
            s.first_observation_date,
            s.last_observation_date,
            CASE
                WHEN m.market IN ('Accra', 'Tema', 'Kumasi') THEN 'Major National Hub'
                WHEN m.market IN (
                    'Sekondi/Takoradi', 'Tamale', 'Cape Coast', 'Sunyani',
                    'Bolgatanga', 'Wa', 'Bawku', 'Koforidua', 'Ho'
                ) THEN 'Regional Center'
                ELSE 'Local Market'
            END                                                           AS market_tier
        FROM stg_markets m
        LEFT JOIN market_stats s ON m.market_id = s.market_id
    """)

    # Commodities dimension with categories, wholesale packaging, and retail units
    con.execute("""
        CREATE OR REPLACE VIEW dim_commodities AS
        SELECT
            commodity_id,
            commodity,
            category,
            COUNT(DISTINCT raw_unit)                                      AS units_available,
            COALESCE(string_agg(DISTINCT CASE WHEN price_type = 'Wholesale' THEN raw_unit END, ', '), 'N/A') AS wholesale_units,
            COALESCE(string_agg(DISTINCT CASE WHEN price_type = 'Retail' THEN raw_unit END, ', '), 'N/A')    AS retail_units,
            string_agg(DISTINCT raw_unit, ', ')                           AS reported_units,
            COUNT(*)                                                      AS total_observations,
            MIN(date)                                                     AS first_recorded_date,
            MAX(date)                                                     AS last_recorded_date
        FROM stg_food_prices
        GROUP BY commodity_id, commodity, category
    """)

    # Calendar dimension covering Ghana agricultural seasons
    con.execute("""
        CREATE OR REPLACE VIEW dim_calendar AS
        WITH distinct_dates AS (
            SELECT DISTINCT date FROM stg_food_prices
        )
        SELECT
            date,
            year(date)                                                    AS year,
            quarter(date)                                                 AS quarter,
            month(date)                                                   AS month,
            strftime(date, '%B')                                          AS month_name,
            strftime(date, '%Y-%m')                                       AS year_month,
            CASE
                WHEN month(date) IN (8, 9, 10, 11) THEN 'Major Harvest'
                WHEN month(date) IN (12, 1) THEN 'Post-Harvest'
                WHEN month(date) IN (5, 6, 7) THEN 'Lean Season'
                ELSE 'Minor Season'
            END                                                           AS agricultural_season
        FROM distinct_dates
    """)


def build_marts_layer(con: duckdb.DuckDBPyConnection) -> None:
    """Build analytical marts for reporting and visualization."""
    logger.info("Building analytical marts: mart_commodity_monthly, mart_regional_spreads, mart_wholesale_retail_margins")

    # Mart: Monthly national commodity price trends with true calendar MoM and YoY growth
    con.execute("""
        CREATE OR REPLACE VIEW mart_commodity_monthly AS
        WITH monthly_base AS (
            SELECT
                year_month,
                date,
                category,
                commodity,
                commodity_id,
                raw_unit,
                unit_family,
                price_type,
                MEDIAN(price_ghs)                                         AS median_price_ghs,
                MEDIAN(price_usd)                                         AS median_price_usd,
                MEDIAN(price_ghs_per_kg)                                  AS median_price_ghs_per_kg,
                MIN(price_ghs)                                            AS min_price_ghs,
                MAX(price_ghs)                                            AS max_price_ghs,
                COUNT(DISTINCT market_id)                                 AS markets_reporting,
                COUNT(*)                                                  AS observations_count
            FROM stg_food_prices
            GROUP BY
                year_month, date, category, commodity, commodity_id,
                raw_unit, unit_family, price_type
        ),
        lagged_metrics AS (
            SELECT
                *,
                LAG(date, 1) OVER (
                    PARTITION BY commodity_id, raw_unit, price_type
                    ORDER BY date
                )                                                         AS prev_date,
                LAG(median_price_ghs, 1) OVER (
                    PARTITION BY commodity_id, raw_unit, price_type
                    ORDER BY date
                )                                                         AS raw_prev_month_price_ghs,
                LAG(date, 12) OVER (
                    PARTITION BY commodity_id, raw_unit, price_type
                    ORDER BY date
                )                                                         AS prev_12_date,
                LAG(median_price_ghs, 12) OVER (
                    PARTITION BY commodity_id, raw_unit, price_type
                    ORDER BY date
                )                                                         AS raw_prev_year_price_ghs,
                AVG(median_price_ghs) OVER (
                    PARTITION BY commodity_id, raw_unit, price_type
                    ORDER BY date
                    RANGE BETWEEN INTERVAL '2' MONTH PRECEDING AND CURRENT ROW
                )                                                         AS moving_avg_3m_ghs,
                AVG(median_price_ghs) OVER (
                    PARTITION BY commodity_id, raw_unit, price_type
                    ORDER BY date
                    RANGE BETWEEN INTERVAL '11' MONTH PRECEDING AND CURRENT ROW
                )                                                         AS moving_avg_12m_ghs
            FROM monthly_base
        )
        SELECT
            year_month,
            date,
            category,
            commodity,
            commodity_id,
            raw_unit,
            unit_family,
            price_type,
            median_price_ghs,
            median_price_usd,
            median_price_ghs_per_kg,
            min_price_ghs,
            max_price_ghs,
            markets_reporting,
            observations_count,
            CASE
                WHEN prev_date IS NOT NULL AND DATEDIFF('day', prev_date, date) BETWEEN 27 AND 35 THEN raw_prev_month_price_ghs
                ELSE NULL
            END                                                           AS prev_month_price_ghs,
            CASE
                WHEN prev_12_date IS NOT NULL AND DATEDIFF('day', prev_12_date, date) BETWEEN 350 AND 380 THEN raw_prev_year_price_ghs
                ELSE NULL
            END                                                           AS prev_year_price_ghs,
            moving_avg_3m_ghs,
            moving_avg_12m_ghs,
            CASE
                WHEN prev_date IS NOT NULL AND DATEDIFF('day', prev_date, date) BETWEEN 27 AND 35 AND raw_prev_month_price_ghs > 0 THEN
                    ROUND(((median_price_ghs - raw_prev_month_price_ghs) / raw_prev_month_price_ghs) * 100.0, 2)
                ELSE NULL
            END                                                           AS mom_pct_change,
            CASE
                WHEN prev_12_date IS NOT NULL AND DATEDIFF('day', prev_12_date, date) BETWEEN 350 AND 380 AND raw_prev_year_price_ghs > 0 THEN
                    ROUND(((median_price_ghs - raw_prev_year_price_ghs) / raw_prev_year_price_ghs) * 100.0, 2)
                ELSE NULL
            END                                                           AS yoy_pct_change
        FROM lagged_metrics
    """)

    # Mart: Regional price spreads against national median
    con.execute("""
        CREATE OR REPLACE VIEW mart_regional_spreads AS
        WITH market_monthly AS (
            SELECT
                p.year_month,
                p.date,
                p.region,
                p.market,
                p.market_id,
                p.latitude,
                p.longitude,
                p.commodity,
                p.commodity_id,
                p.raw_unit,
                p.price_type,
                MEDIAN(p.price_ghs)                                       AS market_median_ghs,
                MEDIAN(p.price_ghs_per_kg)                                AS market_median_ghs_per_kg
            FROM stg_food_prices p
            GROUP BY
                p.year_month, p.date, p.region, p.market, p.market_id,
                p.latitude, p.longitude, p.commodity, p.commodity_id,
                p.raw_unit, p.price_type
        ),
        national_monthly AS (
            SELECT
                year_month,
                commodity_id,
                raw_unit,
                price_type,
                median_price_ghs                                          AS national_median_ghs,
                median_price_ghs_per_kg                                   AS national_median_ghs_per_kg
            FROM mart_commodity_monthly
        )
        SELECT
            m.year_month,
            m.date,
            m.region,
            m.market,
            m.market_id,
            m.latitude,
            m.longitude,
            m.commodity,
            m.commodity_id,
            m.raw_unit,
            m.price_type,
            m.market_median_ghs,
            m.market_median_ghs_per_kg,
            n.national_median_ghs,
            n.national_median_ghs_per_kg,
            ROUND(m.market_median_ghs - n.national_median_ghs, 2)         AS spread_to_national_ghs,
            CASE
                WHEN n.national_median_ghs > 0 THEN
                    ROUND(((m.market_median_ghs - n.national_median_ghs) / n.national_median_ghs) * 100.0, 2)
                ELSE NULL
            END                                                           AS spread_to_national_pct,
            ROUND(m.market_median_ghs_per_kg - n.national_median_ghs_per_kg, 2) AS spread_to_national_per_kg,
            CASE
                WHEN n.national_median_ghs_per_kg > 0 THEN
                    ROUND(((m.market_median_ghs_per_kg - n.national_median_ghs_per_kg) / n.national_median_ghs_per_kg) * 100.0, 2)
                ELSE NULL
            END                                                           AS spread_to_national_per_kg_pct
        FROM market_monthly m
        JOIN national_monthly n
            ON m.year_month = n.year_month
            AND m.commodity_id = n.commodity_id
            AND m.raw_unit = n.raw_unit
            AND m.price_type = n.price_type
    """)

    # Mart: Wholesale vs Retail margins and trade markups
    con.execute("""
        CREATE OR REPLACE VIEW mart_wholesale_retail_margins AS
        WITH paired_observations AS (
            SELECT
                year_month,
                date,
                market_id,
                market,
                region,
                commodity_id,
                commodity,
                MEDIAN(CASE WHEN price_type = 'Wholesale' THEN price_ghs_per_kg END)  AS wholesale_price_per_kg,
                MEDIAN(CASE WHEN price_type = 'Retail' THEN price_ghs_per_kg END)     AS retail_price_per_kg
            FROM stg_food_prices
            WHERE price_ghs_per_kg IS NOT NULL
            GROUP BY year_month, date, market_id, market, region, commodity_id, commodity
        )
        SELECT
            year_month,
            date,
            market_id,
            market,
            region,
            commodity_id,
            commodity,
            wholesale_price_per_kg,
            retail_price_per_kg,
            ROUND(retail_price_per_kg - wholesale_price_per_kg, 2)                 AS margin_per_kg_ghs,
            CASE
                WHEN wholesale_price_per_kg > 0 THEN
                    ROUND(((retail_price_per_kg - wholesale_price_per_kg) / wholesale_price_per_kg) * 100.0, 2)
                ELSE NULL
            END                                                                    AS retail_markup_pct,
            CASE
                WHEN retail_price_per_kg >= wholesale_price_per_kg
                 AND ((retail_price_per_kg - wholesale_price_per_kg) / NULLIF(wholesale_price_per_kg, 0)) * 100.0 <= 200.0
                THEN TRUE
                ELSE FALSE
            END                                                                    AS is_verified_margin
        FROM paired_observations
        WHERE wholesale_price_per_kg IS NOT NULL
          AND retail_price_per_kg IS NOT NULL
          AND wholesale_price_per_kg >= 0.20
          AND retail_price_per_kg >= 0.20
    """)

    # Mart: Pipeline observability and data freshness summary
    con.execute("""
        CREATE OR REPLACE VIEW mart_pipeline_health AS
        SELECT
            run_id,
            started_at,
            completed_at,
            pipeline_step,
            status,
            records_affected,
            execution_time_s,
            error_details
        FROM meta_pipeline_runs
        ORDER BY started_at DESC
    """)

    # Mart: Data quality and anomaly quarantine log (Project Plan Phase 2 Requirement)
    con.execute("""
        CREATE OR REPLACE VIEW audit_data_anomalies AS
        SELECT
            date,
            market,
            region,
            commodity,
            'Margin Inversion / Outlier Markup'                           AS anomaly_type,
            'Wholesale GHS ' || ROUND(wholesale_price_per_kg, 2) || '/kg vs Retail GHS ' || ROUND(retail_price_per_kg, 2) || '/kg (' || retail_markup_pct || '% markup)' AS anomaly_details,
            'Quarantined from commercial margin benchmarks'              AS resolution_status
        FROM mart_wholesale_retail_margins
        WHERE is_verified_margin = FALSE

        UNION ALL

        SELECT
            date,
            market,
            region,
            commodity,
            'Extreme Unit Price Outlier'                                  AS anomaly_type,
            'Reported GHS ' || ROUND(price_ghs, 2) || ' (' || ROUND(price_ghs_per_kg, 2) || ' GHS/kg, ' || raw_unit || ')' AS anomaly_details,
            'Preserved in raw audit layer; flagged for monitoring'        AS resolution_status
        FROM stg_food_prices
        WHERE price_ghs_per_kg > 100.0 OR price_ghs_per_kg < 0.05
    """)


def execute_build(db_path: Path) -> Dict[str, Any]:
    """Execute the full data transformation and marts build workflow."""
    run_id = f"build_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    start_time = time.perf_counter()
    started_at = datetime.datetime.now(datetime.timezone.utc)

    logger.info("Starting analytical marts build (Run ID: %s)", run_id)
    con = duckdb.connect(str(db_path))

    try:
        build_staging_layer(con)
        build_dimension_layer(con)
        build_marts_layer(con)

        # Verification metrics
        views_created = [
            "stg_food_prices",
            "stg_markets",
            "dim_markets",
            "dim_commodities",
            "dim_calendar",
            "mart_commodity_monthly",
            "mart_regional_spreads",
            "mart_wholesale_retail_margins",
            "mart_pipeline_health",
            "audit_data_anomalies",
        ]

        metrics = {}
        for view_name in views_created:
            row_count = con.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
            metrics[view_name] = row_count
            logger.info("Verified view: %-30s | Rows: %d", view_name, row_count)

        duration_s = time.perf_counter() - start_time
        completed_at = datetime.datetime.now(datetime.timezone.utc)

        record_pipeline_run(
            con=con,
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            pipeline_step="build_analytical_marts",
            status="SUCCESS",
            records_affected=metrics.get("mart_commodity_monthly", 0),
            execution_time_s=round(duration_s, 3),
            error_details=None,
        )

        return {
            "status": "success",
            "run_id": run_id,
            "duration_s": round(duration_s, 3),
            "view_metrics": metrics,
        }
    except Exception as exc:
        duration_s = time.perf_counter() - start_time
        completed_at = datetime.datetime.now(datetime.timezone.utc)
        try:
            record_pipeline_run(
                con=con,
                run_id=run_id,
                started_at=started_at,
                completed_at=completed_at,
                pipeline_step="build_analytical_marts",
                status="FAILED",
                records_affected=0,
                execution_time_s=round(duration_s, 3),
                error_details=str(exc),
            )
        except Exception as inner_exc:
            logger.error("Failed to write build error audit: %s", str(inner_exc))
        raise
    finally:
        con.close()
        logger.info("DuckDB connection closed.")


def main() -> None:
    """Entry point for building analytical marts."""
    db_file = DEFAULT_DUCKDB_PATH
    summary = execute_build(db_file)

    logger.info("================ BUILD SUMMARY ================")
    logger.info("Run ID: %s", summary["run_id"])
    logger.info("Duration: %.2f seconds", summary["duration_s"])
    for view, count in summary["view_metrics"].items():
        logger.info("  - %-30s: %d rows", view, count)
    logger.info("===============================================")


if __name__ == "__main__":
    main()
