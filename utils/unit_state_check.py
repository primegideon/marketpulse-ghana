import duckdb
con = duckdb.connect("agri_ghana.duckdb")

SEP = "\n" + "=" * 60 + "\n"

print(SEP + "1. ALL UNITS in stg_wfp_prices with current conversion factors")
print(con.execute("""
    SELECT raw_unit, kg_conversion_factor,
           COUNT(*) AS rows,
           COUNT(DISTINCT commodity_name) AS commodities
    FROM stg_wfp_prices
    GROUP BY raw_unit, kg_conversion_factor
    ORDER BY rows DESC
""").fetchdf().to_string(index=False))

print(SEP + "2. PLANTAIN BUNCH — current factor in stg_wfp_prices")
print(con.execute("""
    SELECT commodity_name, raw_unit, kg_conversion_factor,
           ROUND(AVG(raw_price_ghs),2) AS avg_raw_ghs,
           ROUND(AVG(price_per_kg_ghs),2) AS avg_per_kg,
           COUNT(*) AS rows
    FROM stg_wfp_prices
    WHERE raw_unit LIKE '%bunch%'
    GROUP BY commodity_name, raw_unit, kg_conversion_factor
""").fetchdf().to_string(index=False))

print(SEP + "3. YAM 250 KG BAG — cross-check per-kg vs standalone KG rows")
print(con.execute("""
    SELECT commodity_name, raw_unit, kg_conversion_factor,
           ROUND(AVG(raw_price_ghs),2) AS avg_raw_ghs,
           ROUND(AVG(price_per_kg_ghs),2) AS avg_per_kg,
           COUNT(*) AS rows
    FROM stg_wfp_prices
    WHERE raw_unit = '250 kg'
    GROUP BY commodity_name, raw_unit, kg_conversion_factor
""").fetchdf().to_string(index=False))

print(SEP + "4. CROSS-CHECKS: per-kg prices should match across unit types")

yam_bag   = con.execute("SELECT ROUND(AVG(price_per_kg_ghs),3) FROM stg_wfp_prices WHERE commodity_name='yam' AND raw_unit='250 kg'").fetchone()[0]
yam_kg    = con.execute("SELECT ROUND(AVG(price_per_kg_ghs),3) FROM stg_wfp_prices WHERE commodity_name='yam' AND raw_unit='kg'").fetchone()[0]
cass_bag  = con.execute("SELECT ROUND(AVG(price_per_kg_ghs),3) FROM stg_wfp_prices WHERE commodity_name='cassava' AND raw_unit='91 kg'").fetchone()[0]
cass_kg   = con.execute("SELECT ROUND(AVG(price_per_kg_ghs),3) FROM stg_wfp_prices WHERE commodity_name='cassava' AND raw_unit='kg'").fetchone()[0]
plan_bun  = con.execute("SELECT ROUND(AVG(price_per_kg_ghs),3) FROM stg_wfp_prices WHERE raw_unit='bunch'").fetchone()[0]
plan_kg   = con.execute("SELECT ROUND(AVG(price_per_kg_ghs),3) FROM stg_wfp_prices WHERE commodity_name LIKE '%plantain%' AND raw_unit='kg'").fetchone()[0]
yam_tub   = con.execute("SELECT ROUND(AVG(price_per_kg_ghs),3) FROM stg_wfp_prices WHERE commodity_name='yam' AND raw_unit LIKE '%tuber%'").fetchone()[0]

print(f"  Yam via 250 kg bag:       GHS {yam_bag}/kg")
print(f"  Yam via KG rows:          GHS {yam_kg}/kg")
print(f"  -- should be close; big gap = wrong factor")
print()
print(f"  Cassava via 91 kg bag:    GHS {cass_bag}/kg")
print(f"  Cassava via KG rows:      GHS {cass_kg}/kg")
print(f"  -- should be close; 91 kg bag is a common wholesale unit in Ghana")
print()
print(f"  Plantain via bunch (f=12):GHS {plan_bun}/kg")
print(f"  Plantain via KG rows:     GHS {plan_kg}/kg")
print(f"  -- if bunch factor=12 overestimates, bunch per-kg will be LOWER than kg rows")
print(f"  -- means bunch price_per_kg = raw/12 is TOO LOW (real bunch is lighter = higher per-kg)")
print()
print(f"  Yam via 100 tubers (f=50):GHS {yam_tub}/kg")
print(f"  Yam via KG rows:          GHS {yam_kg}/kg")
print(f"  -- if tuber factor=50 is too low, tuber per-kg will be HIGHER than actual")

print(SEP + "5. WHAT THE PLAN DOCUMENT SAYS ABOUT UNITS")
print("""
  Plan document (Day 2) states:
    'normalize measurement units into standardized 1 KG equivalents'

  ML Guardrail (b) states:
    'caps extreme historical outliers between GHS 0.05 and GHS 150.0/kg'

  This means:
  - The plan ceiling is GHS 150/kg (plan doc), but the code uses GHS 500/kg.
  - The code is more permissive than the plan specified.
  - All unit conversions must produce per-kg values consistent across unit types
    for the same commodity — if they don't, the normalisation is wrong.
""")

con.close()
print(SEP + "UNIT STATE AUDIT COMPLETE")
