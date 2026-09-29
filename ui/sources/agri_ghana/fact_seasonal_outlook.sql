select
    commodity_name,
    month_num,
    month_name,
    years_observed,
    avg_mom_pct,
    min_mom_pct,
    max_mom_pct,
    stddev_mom_pct,
    count_up,
    count_down,
    count_flat,
    pct_years_up,
    pct_years_down,
    direction_signal
from fact_seasonal_outlook
order by commodity_name, month_num
