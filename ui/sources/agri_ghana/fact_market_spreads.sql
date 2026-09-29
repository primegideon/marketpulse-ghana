select
    month_start::DATE as month_start,
    commodity_name,
    urban_avg_price,
    producing_avg_price,
    absolute_spread_ghs,
    spread_margin_pct,
    price_type
from fact_market_spreads
order by month_start, commodity_name
