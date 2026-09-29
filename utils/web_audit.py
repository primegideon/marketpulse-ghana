"""
WFP Dataset Web Audit
======================
Downloads the live WFP Ghana Food Prices CSV from the Humanitarian Data
Exchange (HDX) and validates the following against the pipeline assumptions:

  - Dataset date range and total row count
  - All distinct unit values present in the source data
  - All distinct commodity names
  - Price type distribution (Retail vs Wholesale)
  - Sample rows for each unit type to confirm commodity mappings

This script does not modify any local data. It is intended as a reference
check to confirm that the pipeline ingestion layer and unit conversion
logic remain aligned with the upstream source after dataset updates.
"""

import urllib.request
import csv
import io

SOURCE_URL = (
    "https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320"
    "/resource/e877350b-146f-4fa7-8690-db9605eea78c/download/wfp_food_prices_gha.csv"
)
HEADERS = {"User-Agent": "Mozilla/5.0"}
READ_BYTES = 10_000_000

print("Downloading WFP Ghana Food Prices CSV (up to 10 MB)...")
req = urllib.request.Request(SOURCE_URL, headers=HEADERS)
with urllib.request.urlopen(req, timeout=90) as response:
    raw = response.read(READ_BYTES).decode("utf-8", errors="replace")

reader = csv.reader(io.StringIO(raw))
column_headers = next(reader)
rows = list(reader)

print(f"Column headers: {column_headers}")
print(f"Rows downloaded: {len(rows):,}")

# -------------------------------------------------------------------
# Distinct units with one representative row each
# -------------------------------------------------------------------
unit_examples: dict[str, tuple] = {}
for row in rows:
    if len(row) < 15:
        continue
    unit = row[10].strip()
    if unit not in unit_examples:
        unit_examples[unit] = (row[8].strip(), row[12].strip(), row[14].strip())

SEP = "\n" + "=" * 60 + "\n"

print(SEP + "DISTINCT UNITS — one representative row each")
print(f"{'Unit':<22} {'Commodity':<32} {'PriceType':<12} {'Price':>10}")
for unit, (commodity, pricetype, price) in sorted(unit_examples.items()):
    print(f"  {unit:<20} {commodity:<32} {pricetype:<12} {price:>10}")

# -------------------------------------------------------------------
# Distinct commodities with row count
# -------------------------------------------------------------------
from collections import defaultdict
commodity_counts: dict[str, int] = defaultdict(int)
pricetype_counts: dict[str, int] = defaultdict(int)

for row in rows:
    if len(row) < 13:
        continue
    commodity_counts[row[8].strip()] += 1
    pricetype_counts[row[12].strip()] += 1

print(SEP + "DISTINCT COMMODITIES — sorted by row count")
for commodity, count in sorted(commodity_counts.items(), key=lambda x: -x[1]):
    print(f"  {commodity:<40} {count:>6} rows")

print(SEP + "PRICE TYPE DISTRIBUTION")
for pricetype, count in sorted(pricetype_counts.items(), key=lambda x: -x[1]):
    print(f"  {pricetype:<20} {count:>6} rows")

# -------------------------------------------------------------------
# Date range from actual CSV content
# -------------------------------------------------------------------
dates = sorted(row[0].strip() for row in rows if row and row[0].strip())
print(SEP + "DATE RANGE — from actual CSV rows")
print(f"  Earliest: {dates[0]}")
print(f"  Latest:   {dates[-1]}")
print(f"  Total rows in download: {len(rows):,}")

print(SEP + "WEB AUDIT COMPLETE")
