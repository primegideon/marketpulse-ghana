# Pipeline package — maps clean aliases to the numerically-prefixed module files.
import importlib
import sys
import os

_pkg_dir = os.path.dirname(__file__)

def _load(alias: str, filename: str):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(_pkg_dir, filename))
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod

ingest_data_1    = _load("ingest_data_1",    "1_ingest_data.py")
transform_data_2 = _load("transform_data_2", "2_transform_data.py")
build_analytics_3 = _load("build_analytics_3", "3_build_analytics_views.py")
run_forecasting_4 = _load("run_forecasting_4", "4_run_forecasting.py")
build_seasonal_5  = _load("build_seasonal_5",  "5_build_seasonal_outlook.py")
