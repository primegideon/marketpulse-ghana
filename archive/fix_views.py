"""
fix_views.py — DEPRECATED
==========================
This file was a one-off patch script used during early development.
The views it defined had several bugs (wrong region casing, unbounded
GBVI score, missing staple filter).

All three views are now correctly defined and rebuilt by:
    build_analytics_views.py

To rebuild all views from clean data, run in order:
    1. python transform_data.py         (rebuilds stg_wfp_prices)
    2. python build_analytics_views.py  (rebuilds all 3 views)
    3. python run_forecasting.py        (rebuilds fact_price_forecasts)

This file is kept only for git history reference.
"""
print("This script is deprecated. Please run build_analytics_views.py instead.")
