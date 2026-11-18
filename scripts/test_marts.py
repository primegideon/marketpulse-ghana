"""
Automated Data Quality & Contract Assertion Suite for MarketPulse Ghana.

Validates schema integrity, composite primary key uniqueness, non-null constraints,
price positivity, trade margin validity, and anomaly quarantine consistency
directly against the embedded DuckDB database.

Runs as a pytest suite (pytest scripts/test_marts.py -v) or directly:
    python scripts/test_marts.py

Exit code 0 on all passes, 1 on failure.
"""

import sys
import pytest
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "agri_ghana.duckdb"

# ---------------------------------------------------------------------------
# 1. Table & Mart Existence Checks
# ---------------------------------------------------------------------------

REQUIRED_TABLES = [
    "stg_food_prices",
    "stg_markets",
    "dim_commodities",
    "dim_markets",
    "dim_calendar",
    "mart_commodity_monthly",
    "mart_regional_spreads",
    "mart_wholesale_retail_margins",
    "audit_data_anomalies",
    "meta_pipeline_runs",
]


def test_required_tables_exist(con):
    """All required tables and views must be present in the database."""
    existing = set(r[0] for r in con.execute("SHOW TABLES").fetchall())
    for t in REQUIRED_TABLES:
        assert t in existing, f"Missing table/view: {t}"


# ---------------------------------------------------------------------------
# 2. Primary Key & Uniqueness Contract Checks
# ---------------------------------------------------------------------------

def test_pk_uniqueness_dim_commodities(con):
    res = con.execute(
        "SELECT COUNT(*) - COUNT(DISTINCT commodity) FROM dim_commodities"
    ).fetchone()[0]
    assert res == 0, f"dim_commodities commodity PK has {res} duplicates"


def test_pk_uniqueness_dim_markets(con):
    res = con.execute(
        "SELECT COUNT(*) - COUNT(DISTINCT market) FROM dim_markets"
    ).fetchone()[0]
    assert res == 0, f"dim_markets market PK has {res} duplicates"


def test_pk_uniqueness_dim_calendar(con):
    res = con.execute(
        "SELECT COUNT(*) - COUNT(DISTINCT date) FROM dim_calendar"
    ).fetchone()[0]
    assert res == 0, f"dim_calendar date PK has {res} duplicates"


def test_pk_uniqueness_mart_commodity_monthly(con):
    res = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT date, commodity, raw_unit, price_type, COUNT(*) AS c
            FROM mart_commodity_monthly
            GROUP BY date, commodity, raw_unit, price_type
            HAVING c > 1
        )
    """).fetchone()[0]
    assert res == 0, f"mart_commodity_monthly composite PK has {res} duplicate groups"


def test_pk_uniqueness_mart_regional_spreads(con):
    res = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT date, market, commodity, raw_unit, price_type, COUNT(*) AS c
            FROM mart_regional_spreads
            GROUP BY date, market, commodity, raw_unit, price_type
            HAVING c > 1
        )
    """).fetchone()[0]
    assert res == 0, f"mart_regional_spreads composite PK has {res} duplicate groups"


def test_pk_uniqueness_mart_wholesale_retail_margins(con):
    res = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT date, commodity, market, COUNT(*) AS c
            FROM mart_wholesale_retail_margins
            GROUP BY date, commodity, market
            HAVING c > 1
        )
    """).fetchone()[0]
    assert res == 0, f"mart_wholesale_retail_margins composite PK has {res} duplicate groups"


# ---------------------------------------------------------------------------
# 3. Non-Null Mandatory Field Constraints
# ---------------------------------------------------------------------------

def test_non_null_mart_commodity_monthly(con):
    res = con.execute("""
        SELECT COUNT(*) FROM mart_commodity_monthly
        WHERE date IS NULL OR commodity IS NULL OR raw_unit IS NULL OR price_type IS NULL
           OR median_price_ghs IS NULL
    """).fetchone()[0]
    assert res == 0, f"mart_commodity_monthly has {res} rows with NULL mandatory columns"


def test_non_null_per_kg_mass_commodities(con):
    res = con.execute("""
        SELECT COUNT(*) FROM mart_commodity_monthly
        WHERE unit_family = 'Mass / Weight' AND median_price_ghs_per_kg IS NULL
    """).fetchone()[0]
    assert res == 0, f"mart_commodity_monthly has {res} Mass/Weight rows with NULL per-kg price"


def test_unit_family_canonical_labels(con):
    res = con.execute("""
        SELECT COUNT(*) FROM stg_food_prices
        WHERE unit_family NOT IN ('Mass / Weight', 'Piece / Count')
    """).fetchone()[0]
    assert res == 0, f"stg_food_prices has {res} rows with non-canonical unit_family labels"


def test_non_null_mart_regional_spreads(con):
    res = con.execute("""
        SELECT COUNT(*) FROM mart_regional_spreads
        WHERE date IS NULL OR commodity IS NULL OR market IS NULL OR region IS NULL
           OR market_median_ghs IS NULL OR spread_to_national_ghs IS NULL
    """).fetchone()[0]
    assert res == 0, f"mart_regional_spreads has {res} rows with NULL mandatory columns"


def test_non_null_mart_wholesale_retail_margins(con):
    res = con.execute("""
        SELECT COUNT(*) FROM mart_wholesale_retail_margins
        WHERE date IS NULL OR commodity IS NULL OR market IS NULL
           OR wholesale_price_per_kg IS NULL OR retail_price_per_kg IS NULL
           OR margin_per_kg_ghs IS NULL OR is_verified_margin IS NULL
    """).fetchone()[0]
    assert res == 0, f"mart_wholesale_retail_margins has {res} rows with NULL mandatory columns"


# ---------------------------------------------------------------------------
# 4. Domain Logic & Value Sanity Assertions
# ---------------------------------------------------------------------------

def test_commodity_prices_positive(con):
    res = con.execute("""
        SELECT COUNT(*) FROM mart_commodity_monthly
        WHERE median_price_ghs <= 0
           OR (median_price_ghs_per_kg IS NOT NULL AND median_price_ghs_per_kg <= 0)
    """).fetchone()[0]
    assert res == 0, f"mart_commodity_monthly has {res} rows with non-positive prices"


def test_verified_margins_retail_gte_wholesale(con):
    res = con.execute("""
        SELECT COUNT(*) FROM mart_wholesale_retail_margins
        WHERE is_verified_margin = TRUE AND retail_price_per_kg < wholesale_price_per_kg
    """).fetchone()[0]
    assert res == 0, f"mart_wholesale_retail_margins has {res} verified margins where retail < wholesale"


def test_anomaly_log_has_records(con):
    res = con.execute("SELECT COUNT(*) FROM audit_data_anomalies").fetchone()[0]
    assert res > 0, "audit_data_anomalies is empty; expected at least 1 quarantined record"


def test_temporal_coverage_min_210_months(con):
    res = con.execute("SELECT COUNT(*) FROM dim_calendar").fetchone()[0]
    assert res >= 210, f"dim_calendar has only {res} months; expected >= 210"


def test_regional_coverage_10_regions(con):
    res = con.execute(
        "SELECT COUNT(DISTINCT region) FROM dim_markets WHERE region != 'National'"
    ).fetchone()[0]
    assert res == 10, f"dim_markets covers {res} regions; expected exactly 10"


def test_commodity_coverage_min_25(con):
    res = con.execute("SELECT COUNT(*) FROM dim_commodities").fetchone()[0]
    assert res >= 25, f"dim_commodities has only {res} commodities; expected >= 25"


def test_pipeline_audit_trail_exists(con):
    res = con.execute(
        "SELECT COUNT(*) FROM meta_pipeline_runs WHERE status = 'SUCCESS'"
    ).fetchone()[0]
    assert res >= 1, f"meta_pipeline_runs has {res} SUCCESS runs; expected >= 1"


# ---------------------------------------------------------------------------
# 5. Extended Coverage Checks (new)
# ---------------------------------------------------------------------------

def test_raw_date_range_min_200_months(con):
    """Raw data must span at least 200 months."""
    res = con.execute(
        "SELECT DATEDIFF('month', MIN(date::DATE), MAX(date::DATE)) FROM raw_wfp_prices"
    ).fetchone()[0]
    assert res >= 200, f"raw_wfp_prices spans only {res} months; expected >= 200"


def test_no_negative_per_kg_prices(con):
    """stg_food_prices must have no negative price_ghs_per_kg values."""
    res = con.execute("""
        SELECT COUNT(*) FROM stg_food_prices
        WHERE price_ghs_per_kg IS NOT NULL AND price_ghs_per_kg < 0
    """).fetchone()[0]
    assert res == 0, f"stg_food_prices has {res} negative price_ghs_per_kg values"


def test_regional_spreads_10_regions(con):
    """mart_regional_spreads must cover all 10 administrative regions."""
    res = con.execute(
        "SELECT COUNT(DISTINCT region) FROM mart_regional_spreads WHERE region IS NOT NULL"
    ).fetchone()[0]
    assert res >= 10, f"mart_regional_spreads covers only {res} regions; expected >= 10"


def test_pipeline_freshness_within_40_days(con):
    """The latest SUCCESS pipeline run must be within the last 40 days."""
    res = con.execute("""
        SELECT DATEDIFF('day', MAX(started_at::DATE), CURRENT_DATE)
        FROM meta_pipeline_runs
        WHERE status = 'SUCCESS'
    """).fetchone()[0]
    assert res <= 40, f"Latest SUCCESS run was {res} days ago; expected <= 40 days"


def test_wholesale_commodities_have_wholesale_units(con):
    """dim_commodities commodities traded at wholesale must have non-N/A wholesale_units."""
    res = con.execute("""
        SELECT COUNT(*) FROM dim_commodities
        WHERE wholesale_units = 'N/A'
          AND commodity IN (SELECT DISTINCT commodity FROM stg_food_prices WHERE price_type = 'Wholesale')
    """).fetchone()[0]
    assert res == 0, f"dim_commodities has {res} wholesale commodities with N/A wholesale_units"


# ---------------------------------------------------------------------------
# Legacy runner (backward-compatible direct execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
