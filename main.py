"""
MarketPulse Ghana — Pipeline Orchestrator
==========================================
Single entry point that runs the full data pipeline in sequence:

    1. Ingest raw WFP Ghana CSV → raw_wfp_prices
    2. Transform and normalise units → stg_wfp_prices
    3. Build analytical views → fact_monthly_prices, fact_market_spreads, fact_gbvi_index
    4. Run ML forecasting → fact_price_forecasts           (skip with --skip-forecast)
    5. Build seasonal outlook → fact_seasonal_outlook

Usage:
    python main.py                  # full pipeline
    python main.py --skip-forecast  # skip Prophet training (faster refresh)

Must be run from the repo root directory so that relative database paths resolve correctly.
"""

import argparse
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("main")

DB_PATH = "agri_ghana.duckdb"

# -------------------------------------------------------------------
# Step registry — order matters
# -------------------------------------------------------------------
def _get_steps(skip_forecast: bool) -> list[dict]:
    import pipeline  # triggers __init__.py which loads all modules
    s1 = pipeline.ingest_data_1
    s2 = pipeline.transform_data_2
    s3 = pipeline.build_analytics_3
    s4 = pipeline.run_forecasting_4
    s5 = pipeline.build_seasonal_5

    steps = [
        {"name": "1_ingest_data",           "fn": s1.main, "label": "Ingest raw WFP CSV"},
        {"name": "2_transform_data",         "fn": s2.main, "label": "Transform & normalise units"},
        {"name": "3_build_analytics_views",  "fn": s3.main, "label": "Build analytical views"},
    ]
    if not skip_forecast:
        steps.append(
            {"name": "4_run_forecasting", "fn": s4.main, "label": "Run ML forecasting (Prophet)"}
        )
    else:
        log.info("--skip-forecast flag set: skipping Step 4 (Prophet training).")

    steps.append(
        {"name": "5_build_seasonal_outlook", "fn": s5.main, "label": "Build seasonal outlook"}
    )
    return steps


# -------------------------------------------------------------------
# Runner
# -------------------------------------------------------------------
def run_pipeline(skip_forecast: bool = False):
    from utils.pipeline_logger import PipelineLogger
    pl = PipelineLogger(DB_PATH)

    steps = _get_steps(skip_forecast)
    results = []
    pipeline_start = time.perf_counter()

    log.info("=" * 60)
    log.info("MarketPulse Ghana — Pipeline Starting")
    log.info(f"Steps to execute: {len(steps)}")
    log.info("=" * 60)

    for step in steps:
        log.info(f"\n▶  {step['label']} ...")
        t0 = time.perf_counter()
        try:
            step["fn"]()
            duration = time.perf_counter() - t0
            results.append({"step": step["name"], "status": "SUCCESS", "duration": duration, "error": ""})
            log.info(f"✓  {step['label']} — done in {duration:.1f}s")
        except Exception as e:
            duration = time.perf_counter() - t0
            results.append({"step": step["name"], "status": "FAILED", "duration": duration, "error": str(e)})
            pl.error(f"main.py → {step['name']}", exception=e, duration_seconds=duration)
            log.error(f"✗  {step['label']} FAILED after {duration:.1f}s: {e}")
            log.error("Pipeline halted. Fix the error above and re-run.")
            _print_summary(results, time.perf_counter() - pipeline_start)
            sys.exit(1)

    _print_summary(results, time.perf_counter() - pipeline_start)


def _print_summary(results: list[dict], total_seconds: float):
    log.info("\n" + "=" * 60)
    log.info("PIPELINE SUMMARY")
    log.info("=" * 60)
    col_w = 36
    log.info(f"{'Step':<{col_w}} {'Status':<10} {'Duration':>10}")
    log.info("-" * 60)
    for r in results:
        status_icon = "✓" if r["status"] == "SUCCESS" else "✗"
        log.info(f"{status_icon} {r['step']:<{col_w - 2}} {r['status']:<10} {r['duration']:>8.1f}s")
        if r["error"]:
            log.info(f"  {'└─ ' + r['error'][:80]}")
    log.info("-" * 60)
    log.info(f"{'Total time':<{col_w}} {'':<10} {total_seconds:>8.1f}s")
    passed = sum(1 for r in results if r["status"] == "SUCCESS")
    log.info(f"Result: {passed}/{len(results)} steps completed successfully.")
    log.info("=" * 60)


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MarketPulse Ghana — full data pipeline orchestrator."
    )
    parser.add_argument(
        "--skip-forecast",
        action="store_true",
        help="Skip Step 4 (Prophet ML training). Use for fast data refreshes.",
    )
    args = parser.parse_args()
    run_pipeline(skip_forecast=args.skip_forecast)
