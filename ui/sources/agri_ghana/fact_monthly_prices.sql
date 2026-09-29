select
    month_start::DATE as month_start,
    commodity_name,
    region,
    avg_price_per_kg_ghs,
    observation_count,
    rolling_3m_avg,
    rolling_6m_avg,
    mom_inflation_pct,
    price_type
from fact_monthly_prices
order by month_start, commodity_name, region
