import duckdb
import pandas as pd

def main():
    db_path = "agri_ghana.duckdb"
    print(f"Connecting to {db_path}...")
    con = duckdb.connect(db_path)

    # ------------------------------------------------------------------
    # PART 1: Turn daily prices into monthly prices, and track changes
    #
    # What this does, in plain terms:
    # - Groups all daily prices into one average price per month
    # - For each month, checks: "was this month's price higher or lower
    #   than last month's, and by what percentage?"
    # - Also calculates a smoothed-out average using the last 3 months,
    #   and another using the last 6 months, so we can see the general
    #   trend without being distracted by single-month spikes or crashes
    #
    # We only look at our 5 chosen staple foods here.
    # ------------------------------------------------------------------
    
    print("Building fact_monthly_prices view...")

    sql_query = """
    CREATE OR REPLACE VIEW fact_monthly_prices AS
    WITH monthly AS (
        SELECT 
            DATE_TRUNC('month', record_date) AS month,
            market_name,
            commodity_name,
            AVG(price_per_kg_ghs) AS avg_price_per_kg
        FROM stg_wfp_prices
        WHERE commodity_name IN ('maize', 'rice (local)', 'cassava', 'yam', 'tomatoes (local)')
        GROUP BY DATE_TRUNC('month', record_date), market_name, commodity_name
    )
    SELECT 
        month,
        market_name,
        commodity_name,
        avg_price_per_kg,

        -- Simply grabs last month's price so we can compare against it
        LAG(avg_price_per_kg) OVER w AS prev_month_price,

        -- Turns the price change into a percentage, e.g. "prices rose 12%"
        (avg_price_per_kg - LAG(avg_price_per_kg) OVER w) / LAG(avg_price_per_kg) OVER w * 100 AS mom_inflation_pct,

        -- Smoothed price using this month + the 2 before it (3 months total)
        AVG(avg_price_per_kg) OVER (
            PARTITION BY market_name, commodity_name ORDER BY month 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_avg,

        -- Smoothed price using this month + the 5 before it (6 months total)
        AVG(avg_price_per_kg) OVER (
            PARTITION BY market_name, commodity_name ORDER BY month 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) AS rolling_6m_avg
    FROM monthly
    WINDOW w AS (PARTITION BY market_name, commodity_name ORDER BY month)
    """

    con.execute(sql_query)
    print("fact_monthly_prices view created successfully.")

    print("\nPreview (Kumasi, Maize):")
    sample_df = con.execute("""
        SELECT * FROM fact_monthly_prices 
        WHERE market_name = 'kumasi' AND commodity_name = 'maize'
        ORDER BY month
        LIMIT 12
    """).fetchdf()
    print(sample_df.to_string(index=False))

    # ------------------------------------------------------------------
    # PART 2: Compare prices between two markets
    #
    # What this does, in plain terms:
    # Techiman is where a lot of food is actually grown, so prices there
    # tend to be cheaper. Accra is a big city that buys food from
    # elsewhere, so prices there tend to be higher.
    #
    # This checks, for each month and each food: how much more expensive
    # is Accra compared to Techiman? Both in cash terms and as a percentage.
    # ------------------------------------------------------------------

    print("\nBuilding regional_price_spread view...")
    con.execute("""
        CREATE OR REPLACE VIEW regional_price_spread AS
        SELECT 
            t.month,
            t.commodity_name,
            t.avg_price_per_kg AS techiman_price,
            a.avg_price_per_kg AS accra_price,

            -- How many more cedis Accra costs compared to Techiman
            a.avg_price_per_kg - t.avg_price_per_kg AS price_spread,

            -- Same gap, but shown as a percentage instead of raw cedis
            (a.avg_price_per_kg - t.avg_price_per_kg) / t.avg_price_per_kg * 100 AS spread_pct
        FROM fact_monthly_prices t
        JOIN fact_monthly_prices a 
            ON t.month = a.month AND t.commodity_name = a.commodity_name
        WHERE t.market_name = 'techiman' AND a.market_name = 'accra'
        ORDER BY t.month, t.commodity_name
    """)
    print("regional_price_spread view created successfully.")

    print("\nPreview (Techiman vs Accra spread):")
    spread_df = con.execute("SELECT * FROM regional_price_spread LIMIT 10").fetchdf()
    print(spread_df.to_string(index=False))

    # ------------------------------------------------------------------
    # PART 3: One overall "how shaky were prices this month" score
    #
    # What this does, in plain terms:
    # For each month, we look at all 5 staple foods and check how much
    # each one's price jumped up or down compared to last month. Then we
    # average those jumps together into a single number for that month.
    #
    # We ignore whether the price went up or down (using ABS, which just
    # means "treat every number as positive") because we only care about
    # HOW BIG the swing was, not which direction it went.
    #
    # A high score means: "this month, food prices were jumping around a
    # lot." A low score means: "this month, prices were fairly stable."
    # ------------------------------------------------------------------

    print("\nBuilding gbvi_monthly view (Ghana Basket Volatility Index)...")
    con.execute("""
        CREATE OR REPLACE VIEW gbvi_monthly AS
        SELECT 
            month,
            AVG(ABS(mom_inflation_pct)) AS gbvi_score
        FROM fact_monthly_prices
        WHERE mom_inflation_pct IS NOT NULL
        GROUP BY month
        ORDER BY month
    """)
    print("gbvi_monthly view created successfully.")

    print("\nPreview (GBVI over time):")
    gbvi_df = con.execute("SELECT * FROM gbvi_monthly LIMIT 12").fetchdf()
    print(gbvi_df.to_string(index=False))

    con.close()

if __name__ == "__main__":
    main()