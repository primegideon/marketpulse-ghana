select
    market_name,
    commodity_name,
    record_date::DATE as record_date,
    predicted_price_ghs,
    lower_bound_ghs,
    upper_bound_ghs,
    mape_score,
    baseline_mape_score,
    directional_accuracy,
    is_forecast
from fact_price_forecasts
order by commodity_name, record_date
