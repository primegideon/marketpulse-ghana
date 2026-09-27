select
    month_start::DATE as month_start,
    staple_count,
    avg_abs_mom_pct,
    stddev_mom_pct,
    avg_mom_pct,
    gbvi_score,
    risk_band
from fact_gbvi_index
order by month_start
