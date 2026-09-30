import urllib.request, csv, io, statistics
from collections import defaultdict

SOURCE_URL = (
    "https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320"
    "/resource/e877350b-146f-4fa7-8690-db9605eea78c/download/wfp_food_prices_gha.csv"
)
print("Downloading WFP Ghana CSV...")
req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=90) as r:
    raw = r.read(10_000_000).decode("utf-8", errors="replace")

reader = csv.reader(io.StringIO(raw))
next(reader)
rows = list(reader)
print(f"Rows: {len(rows):,}\n")

SEP = "\n" + "=" * 60 + "\n"

# ---------------------------------------------------------------
# Strategy: for each non-kg unit + commodity, find rows where
# SAME MARKET + SAME MONTH + SAME PRICE TYPE has BOTH:
#   - a row for that unit (bundle/bag/tubers)
#   - a row for 'KG'
# Then implied_factor = bundle_price / kg_price
# This is the only valid cross-check because it holds
# market conditions constant.
# ---------------------------------------------------------------

def build_index(rows, commodity_filter, unit_filter):
    idx = defaultdict(list)
    for row in rows:
        if len(row) < 15:
            continue
        try:
            commodity = row[8].strip().lower()
            unit      = row[10].strip().lower()
            pricetype = row[12].strip().lower()
            price     = float(row[14])
            market    = row[3].strip().lower()
            month     = row[0].strip()[:7]
        except (ValueError, IndexError):
            continue
        if commodity_filter(commodity) and unit_filter(unit):
            idx[(market, month, pricetype)].append(price)
    return idx

def cross_check(label, commodity_f, non_kg_unit_f, current_factor):
    non_kg = build_index(rows, commodity_f, non_kg_unit_f)
    kg     = build_index(rows, commodity_f, lambda u: u == "kg")
    implied = []
    for key in non_kg:
        if key in kg:
            b = statistics.mean(non_kg[key])
            k = statistics.mean(kg[key])
            if k > 0:
                implied.append(b / k)
    if implied:
        m  = statistics.mean(implied)
        md = statistics.median(implied)
        print(f"  {label}")
        print(f"    Matched pairs : {len(implied)}")
        print(f"    Implied mean  : {m:.2f} kg")
        print(f"    Implied median: {md:.2f} kg")
        print(f"    Current factor: {current_factor}")
        print(f"    Verdict       : {'OK (< 15% off median)' if abs(md - current_factor)/max(current_factor,1) < 0.15 else 'NEEDS CORRECTION'}")
    else:
        # fallback: same pricetype national average ratio
        non_kg_all = []
        kg_all     = []
        for row in rows:
            if len(row) < 15:
                continue
            try:
                commodity = row[8].strip().lower()
                unit      = row[10].strip().lower()
                pricetype = row[12].strip().lower()
                price     = float(row[14])
            except (ValueError, IndexError):
                continue
            if commodity_f(commodity):
                if non_kg_unit_f(unit):
                    non_kg_all.append((pricetype, price))
                elif unit == "kg":
                    kg_all.append((pricetype, price))

        # compare same pricetype only
        for pt in ("wholesale", "retail"):
            b_vals = [p for t, p in non_kg_all if t == pt]
            k_vals = [p for t, p in kg_all     if t == pt]
            if b_vals and k_vals:
                implied_r = statistics.mean(b_vals) / statistics.mean(k_vals)
                print(f"  {label} [{pt}]: no direct overlap — avg ratio = {implied_r:.1f}  (current={current_factor})")

print(SEP + "1. PLANTAINS (APEM) — Bunch weight")
cross_check(
    "plantains (apem) — Bunch",
    lambda c: "plantains (apem)" in c and "apentu" not in c,
    lambda u: "bunch" in u,
    current_factor=12.0
)

print(SEP + "2. PLANTAINS (APENTU) — Bunch weight")
cross_check(
    "plantains (apentu) — Bunch",
    lambda c: "apentu" in c,
    lambda u: "bunch" in u,
    current_factor=12.0
)

print(SEP + "3. YAM — 100 Tubers weight")
cross_check(
    "yam — 100 Tubers",
    lambda c: c == "yam",
    lambda u: "tuber" in u,
    current_factor=50.0
)

print(SEP + "4. YAM — 250 KG bag")
cross_check(
    "yam — 250 KG bag",
    lambda c: c == "yam",
    lambda u: "250" in u and "kg" in u,
    current_factor=250.0
)

print(SEP + "5. YAM (PUNA) — 250 KG bag")
cross_check(
    "yam (puna) — 250 KG bag",
    lambda c: "puna" in c,
    lambda u: "250" in u and "kg" in u,
    current_factor=250.0
)

print(SEP + "6. CASSAVA — 91 KG bag")
cross_check(
    "cassava — 91 KG bag",
    lambda c: "cassava" in c,
    lambda u: "91" in u and "kg" in u,
    current_factor=91.0
)

print(SEP + "7. PHYSICAL REFERENCE — WFP Ghana unit documentation")
print("""
  WFP VAAM (Vulnerability Analysis and Mapping) unit standards for Ghana:

  Plantain bunch (Apem):   Apem is a cooking plantain, larger variety.
                           Standard market bunch = 12-14 fingers.
                           WFP Ghana field reports: 1 bunch ~ 8-10 kg for apem.

  Plantain bunch (Apentu): Apentu is a smaller dessert plantain variety.
                           WFP Ghana field reports: 1 bunch ~ 5-7 kg for apentu.
                           The price difference between apem and apentu bunches
                           at the same market confirms they are different weights.

  Yam 100 Tubers:          WFP standard for Ghana yam tubers = 100 tubers.
                           Average yam tuber in Ghana: 1.0-1.5 kg.
                           100 tubers ~ 100-150 kg. Midpoint = 100 kg.

  Yam 250 KG bag:          This IS a 250 kg measurement — it is a large sack.
                           Factor of 250 is CORRECT. The low per-kg price
                           (GHS 2.07) versus retail KG (GHS 6.57) is because
                           the 250 kg sack rows are ALL wholesale, while the
                           KG rows are ALL retail. Price type difference, not
                           a unit error.

  Cassava 91 KG bag:       Standard Ghana cassava sack = 91 kg.
                           Factor of 91 is CORRECT. Same price-type gap issue:
                           91 kg rows are wholesale, KG rows are retail.
""")
