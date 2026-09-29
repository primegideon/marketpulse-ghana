"""
Validates every SQL block in every Evidence markdown page against the live DuckDB database.
Prints PASS / FAIL for each query with error details on failure.
"""
import duckdb
import re
import sys

DB_PATH = "agri_ghana.duckdb"
PAGES = [
    "ui/pages/index.md",
    "ui/pages/commodities.md",
    "ui/pages/forecasts.md",
    "ui/pages/market_spreads.md",
]

# Placeholder substitutions for Evidence template variables
TEMPLATE_SUBS = {
    r"'\$\{inputs\.selected_commodity\.value\}'": "'maize'",
    r"'\$\{inputs\.[a-zA-Z_.]+\}'": "'maize'",
    r"\$\{inputs\.selected_commodity\.value\}": "maize",
    r"\$\{inputs\.[a-zA-Z_.]+\}": "maize",
}

SQL_BLOCK_RE = re.compile(r"```sql\s+(\w+)\s*\n(.*?)```", re.DOTALL)

# Strip Evidence-specific table props that are not valid SQL
def clean_sql(sql: str) -> str:
    for pattern, replacement in TEMPLATE_SUBS.items():
        sql = re.sub(pattern, replacement, sql)
    return sql.strip()

def run_checks():
    con = duckdb.connect(DB_PATH)
    # Register all agri_ghana views/tables under both bare name and agri_ghana. prefix
    for tbl in ["fact_monthly_prices", "fact_market_spreads", "fact_gbvi_index",
                "fact_price_forecasts", "fact_seasonal_outlook"]:
        try:
            con.execute(f"CREATE OR REPLACE VIEW \"agri_ghana.{tbl}\" AS SELECT * FROM {tbl}")
        except Exception as e:
            print(f"  [WARN] Could not alias {tbl}: {e}")

    total = 0
    failures = 0

    for page_path in PAGES:
        print(f"\n{'='*60}")
        print(f"PAGE: {page_path}")
        print('='*60)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = SQL_BLOCK_RE.findall(content)
        if not blocks:
            print("  No SQL blocks found.")
            continue

        for name, raw_sql in blocks:
            sql = clean_sql(raw_sql)
            total += 1
            try:
                con.execute(sql)
                print(f"  PASS  {name}")
            except Exception as e:
                print(f"  FAIL  {name}")
                print(f"        {e}")
                failures += 1

    con.close()
    print(f"\n{'='*60}")
    print(f"RESULT: {total - failures}/{total} queries passed.")
    if failures:
        print(f"FAILURES: {failures}")
        sys.exit(1)
    else:
        print("All queries validated successfully.")

if __name__ == "__main__":
    run_checks()
