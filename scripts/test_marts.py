"""
Automated Data Quality & Contract Assertion Suite for MarketPulse Ghana.

Validates schema integrity, composite primary key uniqueness, non-null constraints,
price positivity, trade margin validity, and anomaly quarantine consistency
directly against the embedded DuckDB database.

Exit code 0 on all passes, 1 on failure.
"""

import sys
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "agri_ghana.duckdb"

def run_assertions():
    print("=" * 70)
    print("MarketPulse Ghana - Automated Data Quality Assertion Suite")
    print(f"Target Database: {DB_PATH}")
    print("=" * 70)

    if not DB_PATH.exists():
        print(f"[FAIL] Database file does not exist at {DB_PATH}")
        sys.exit(1)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    failures = 0
    total_tests = 0

    def assert_check(name: str, query: str, expected_val, op="=="):
        nonlocal failures, total_tests
        total_tests += 1
        try:
            res = con.execute(query).fetchone()[0]
            if op == "==" and res == expected_val:
                print(f"  [PASS] {name} (Got: {res})")
            elif op == ">=" and res >= expected_val:
                print(f"  [PASS] {name} (Got: {res} >= {expected_val})")
            elif op == ">" and res > expected_val:
                print(f"  [PASS] {name} (Got: {res} > {expected_val})")
            else:
                print(f"  [FAIL] {name} (Expected {op} {expected_val}, got: {res})")
                failures += 1
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            failures += 1

    print("\n--- 1. Table & Mart Existence Checks ---")
    required_tables = [
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
    existing = set(r[0] for r in con.execute("SHOW TABLES").fetchall())
    for t in required_tables:
        total_tests += 1
        if t in existing:
            print(f"  [PASS] Required table/view '{t}' exists")
        else:
            print(f"  [FAIL] Missing table/view '{t}'")
            failures += 1

    print("\n--- 2. Primary Key & Uniqueness Contract Checks ---")
    assert_check(
        "dim_commodities primary key uniqueness (commodity)",
        "SELECT COUNT(*) - COUNT(DISTINCT commodity) FROM dim_commodities",
        0
    )
    assert_check(
        "dim_markets primary key uniqueness (market)",
        "SELECT COUNT(*) - COUNT(DISTINCT market) FROM dim_markets",
        0
    )
    assert_check(
        "dim_calendar date uniqueness (date)",
        "SELECT COUNT(*) - COUNT(DISTINCT date) FROM dim_calendar",
        0
    )
    assert_check(
        "mart_commodity_monthly composite PK uniqueness (date, commodity, raw_unit, price_type)",
        """SELECT COUNT(*) FROM (
            SELECT date, commodity, raw_unit, price_type, COUNT(*) as c
            FROM mart_commodity_monthly
            GROUP BY date, commodity, raw_unit, price_type
            HAVING c > 1
        )""",
        0
    )
    assert_check(
        "mart_regional_spreads composite PK uniqueness (date, market, commodity, raw_unit, price_type)",
        """SELECT COUNT(*) FROM (
            SELECT date, market, commodity, raw_unit, price_type, COUNT(*) as c
            FROM mart_regional_spreads
            GROUP BY date, market, commodity, raw_unit, price_type
            HAVING c > 1
        )""",
        0
    )
    assert_check(
        "mart_wholesale_retail_margins composite PK uniqueness (date, commodity, market)",
        """SELECT COUNT(*) FROM (
            SELECT date, commodity, market, COUNT(*) as c
            FROM mart_wholesale_retail_margins
            GROUP BY date, commodity, market
            HAVING c > 1
        )""",
        0
    )

    print("\n--- 3. Non-Null Mandatory Field Constraints ---")
    assert_check(
        "mart_commodity_monthly mandatory columns have 0 NULLs",
        """SELECT COUNT(*) FROM mart_commodity_monthly
           WHERE date IS NULL OR commodity IS NULL OR raw_unit IS NULL OR price_type IS NULL
              OR median_price_ghs IS NULL""",
        0
    )
    assert_check(
        "mart_commodity_monthly mass-standardized commodities have 0 NULLs for per-kg price",
        """SELECT COUNT(*) FROM mart_commodity_monthly
           WHERE unit_family = 'Mass / Weight' AND median_price_ghs_per_kg IS NULL""",
        0
    )
    assert_check(
        "mart_regional_spreads mandatory columns have 0 NULLs",
        """SELECT COUNT(*) FROM mart_regional_spreads
           WHERE date IS NULL OR commodity IS NULL OR market IS NULL OR region IS NULL
              OR market_median_ghs IS NULL OR spread_to_national_ghs IS NULL""",
        0
    )
    assert_check(
        "mart_wholesale_retail_margins essential columns have 0 NULLs",
        """SELECT COUNT(*) FROM mart_wholesale_retail_margins
           WHERE date IS NULL OR commodity IS NULL OR market IS NULL
              OR wholesale_price_per_kg IS NULL OR retail_price_per_kg IS NULL
              OR margin_per_kg_ghs IS NULL OR is_verified_margin IS NULL""",
        0
    )

    print("\n--- 4. Domain Logic & Value Sanity Assertions ---")
    assert_check(
        "Commodity prices must be strictly positive (> 0)",
        "SELECT COUNT(*) FROM mart_commodity_monthly WHERE median_price_ghs <= 0 OR (median_price_ghs_per_kg IS NOT NULL AND median_price_ghs_per_kg <= 0)",
        0
    )
    assert_check(
        "Verified trade margins must satisfy Retail >= Wholesale per kg",
        "SELECT COUNT(*) FROM mart_wholesale_retail_margins WHERE is_verified_margin = TRUE AND retail_price_per_kg < wholesale_price_per_kg",
        0
    )
    assert_check(
        "Anomaly log contains quarantined records",
        "SELECT COUNT(*) FROM audit_data_anomalies",
        0,
        op=">"
    )
    assert_check(
        "Temporal coverage span: calendar dates >= 210 consecutive months",
        "SELECT COUNT(*) FROM dim_calendar",
        210,
        op=">="
    )
    assert_check(
        "Regional coverage span: exactly 10 administrative regions monitored",
        "SELECT COUNT(DISTINCT region) FROM dim_markets WHERE region != 'National'",
        10
    )
    assert_check(
        "Commodity coverage span: at least 25 primary crops monitored",
        "SELECT COUNT(*) FROM dim_commodities",
        25,
        op=">="
    )
    assert_check(
        "Operational audit trail logged at least 1 pipeline run in meta_pipeline_runs",
        "SELECT COUNT(*) FROM meta_pipeline_runs WHERE status = 'SUCCESS'",
        1,
        op=">="
    )

    con.close()

    print("\n" + "=" * 70)
    print(f"Summary: {total_tests - failures}/{total_tests} tests passed. ({failures} failures)")
    print("=" * 70)

    if failures > 0:
        print(f"[ERROR] Data quality suite failed with {failures} assertion errors.")
        sys.exit(1)
    else:
        print("[SUCCESS] All data contracts and quality assertions passed cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    run_assertions()
