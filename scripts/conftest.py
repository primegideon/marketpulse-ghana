"""pytest fixtures for MarketPulse Ghana data quality test suite."""

import pytest
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "agri_ghana.duckdb"


@pytest.fixture(scope="session")
def con():
    """Open a read-only DuckDB session for the duration of the test run."""
    if not DB_PATH.exists():
        pytest.skip(f"Database not found at {DB_PATH}")
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()
