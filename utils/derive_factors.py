import duckdb, statistics
con = duckdb.connect("agri_ghana.duckdb")

SEP = "\n" + "=" * 60 + "\n"

# For each non-kg unit, find same-market + same-month + same-pricetype
# rows that also have a KG observation for the same commodity.
# implied_factor = raw_price / per_kg_price_from_kg_rows
# This is the ground-truth factor the data itself tells us to use.

print(SEP + "DERIVING CORRECT FACTORS FROM SAME-MARKET/MONTH CROSS-CHECK")

units_to_check = [
    ("bunch",       ["plantains (apem)", "plantains (apentu)"]),
    ("100 tubers",  ["yam", "yam (puna)"]),
    ("250 kg",      ["yam", "yam (puna)"]),
    ("91 kg",       ["cassava"]),
]

for unit, commodities in units_to_check:
    print(f"\nUnit: '{unit}' | Commodities: {commodities}")
    for commodity in commodities:
        # Get all (market, month, pricetype) for this unit
        bag_rows = con.execute(f"""
            SELECT market_name, DATE_TRUNC('month', record_date)::DATE AS m,
                   price_type, raw_price_ghs, kg_conversion_factor
            FROM stg_wfp_prices
            WHERE raw_unit = '{unit}' AND commodity_name = '{commodity}'
        """).fetchdf()

        # Get all KG rows for same commodity
        kg_rows = con.execute(f"""
            SELECT market_name, DATE_TRUNC('month', record_date)::DATE AS m,
                   price_type, AVG(price_per_kg_ghs) AS kg_price
            FROM stg_wfp_prices
            WHERE raw_unit = 'kg' AND commodity_name = '{commodity}'
            GROUP BY market_name, m, price_type
        """).fetchdf()

        if bag_rows.empty or kg_rows.empty:
            # No KG rows — use national monthly average ratio
            bag_avg = con.execute(f"""
                SELECT AVG(raw_price_ghs) FROM stg_wfp_prices
                WHERE raw_unit = '{unit}' AND commodity_name = '{commodity}'
            """).fetchone()[0]
            kg_avg = con.execute(f"""
                SELECT AVG(price_per_kg_ghs) FROM stg_wfp_prices
                WHERE raw_unit = 'kg' AND commodity_name = '{commodity}'
            """).fetchone()[0]
            if bag_avg and kg_avg and kg_avg > 0:
                implied = bag_avg / kg_avg
                print(f"  {commodity}: no direct overlap — global ratio: "
                      f"avg_raw={bag_avg:.2f} / avg_kg_price={kg_avg:.3f} = implied factor {implied:.1f}")
            else:
                print(f"  {commodity}: insufficient data")
            continue

        # Merge on market+month+pricetype
        merged = bag_rows.merge(kg_rows, on=["market_name", "m", "price_type"])
        if merged.empty:
            bag_avg = bag_rows["raw_price_ghs"].mean()
            kg_avg_val = kg_rows["kg_price"].mean()
            if kg_avg_val > 0:
                implied = bag_avg / kg_avg_val
                print(f"  {commodity}: no same-market overlap — global ratio: "
                      f"{implied:.1f} (current factor: {bag_rows['kg_conversion_factor'].iloc[0]:.1f})")
            continue

        implied_factors = (merged["raw_price_ghs"] / merged["kg_price"]).dropna()
        implied_factors = implied_factors[implied_factors > 0]
        current = bag_rows["kg_conversion_factor"].iloc[0]
        mean_f  = implied_factors.mean()
        med_f   = implied_factors.median()
        print(f"  {commodity}: {len(implied_factors)} matched pairs | "
              f"implied mean={mean_f:.1f}  median={med_f:.1f}  "
              f"current factor={current:.1f}  "
              f"{'OK' if abs(mean_f - current) / current < 0.2 else 'MISMATCH'}")

print(SEP + "SUMMARY OF ACTIONS NEEDED")
print("""
  bunch      -> need correct kg per bunch for apem vs apentu
  100 tubers -> yam: need correct kg per 100 tubers
  250 kg     -> yam: 250 kg bag — verify 250 is correct
  91 kg      -> cassava: verify 91 is correct
""")
con.close()
