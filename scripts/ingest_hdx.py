"""Ingestion pipeline for WFP Ghana Food Prices and Markets datasets from HDX into DuckDB.

This module automates the retrieval of the latest food prices and market reference
datasets from the Humanitarian Data Exchange (HDX), ingests them into a local
DuckDB database, and writes operational metadata to the meta_pipeline_runs audit table.
"""

from __future__ import annotations

import datetime
import logging
import os
import shutil
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingest_hdx")

HDX_DATASET_BASE = "https://data.humdata.org/dataset/626e809c-c4fc-467b-a60c-129acb5e9320/resource"
RESOURCE_URLS = {
    "food_prices": (
        f"{HDX_DATASET_BASE}/e877350b-146f-4fa7-8690-db9605eea78c/download/wfp_food_prices_gha.csv"
    ),
    "markets": (
        f"{HDX_DATASET_BASE}/e674838c-87ba-4c7c-afc5-614226842768/download/wfp_markets_gha.csv"
    ),
}

DEFAULT_RAW_DATA_DIR = Path("data/raw")
DEFAULT_DUCKDB_PATH = Path("agri_ghana.duckdb")


def record_pipeline_run(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
    started_at: datetime.datetime,
    completed_at: datetime.datetime,
    pipeline_step: str,
    status: str,
    records_affected: int,
    execution_time_s: float,
    error_details: Optional[str] = None,
) -> None:
    """Persist pipeline operational metadata to meta_pipeline_runs table.

    Args:
        con: Active DuckDB connection.
        run_id: Unique identifier for the pipeline run.
        started_at: Start timestamp in UTC.
        completed_at: Completion timestamp in UTC.
        pipeline_step: Name of the executed pipeline step.
        status: Run status ('SUCCESS', 'WARNING', 'FAILED').
        records_affected: Number of records affected by the operation.
        execution_time_s: Total duration in seconds.
        error_details: Error details or stack trace, if applicable.
    """
    con.execute("""
        CREATE TABLE IF NOT EXISTS meta_pipeline_runs (
            run_id VARCHAR,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            pipeline_step VARCHAR,
            status VARCHAR,
            records_affected BIGINT,
            execution_time_s DOUBLE,
            error_details VARCHAR
        )
    """)

    con.execute(
        """
        INSERT INTO meta_pipeline_runs (
            run_id,
            started_at,
            completed_at,
            pipeline_step,
            status,
            records_affected,
            execution_time_s,
            error_details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            started_at,
            completed_at,
            pipeline_step,
            status,
            records_affected,
            execution_time_s,
            error_details,
        ],
    )


def download_file(url: str, destination: Path, timeout: int = 60, max_retries: int = 3) -> Path:
    """Download a remote file over HTTP/HTTPS with retry logic and row-count validation.

    Args:
        url: Direct download URL for the target resource.
        destination: Local path where the downloaded file should be written.
        timeout: Network timeout in seconds per attempt.
        max_retries: Maximum number of download attempts before raising.

    Returns:
        The resolved Path to the downloaded file.

    Raises:
        urllib.error.URLError: If all connection attempts fail.
        RuntimeError: If download response indicates an error status or row count is suspiciously low.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_destination = destination.with_suffix(".tmp")
    headers = {"User-Agent": "MarketPulse-Ghana-DataIngestion/1.0"}
    # Known baseline: wfp_food_prices_gha.csv has 39,038+ rows; markets file has 93 rows.
    # A floor of 50 catches catastrophically truncated downloads for both files.
    MIN_ROW_FLOOR = 50

    logger.info("Initiating download: %s -> %s", url, destination)

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                with open(temp_destination, "wb") as output_file:
                    shutil.copyfileobj(response, output_file)

            # Integrity check: verify downloaded CSV is not truncated or empty
            _integrity_con = duckdb.connect()
            try:
                row_count = _integrity_con.execute(
                    f"SELECT COUNT(*) FROM read_csv_auto('{temp_destination.as_posix()}', header=True)"
                ).fetchone()[0]
            finally:
                _integrity_con.close()

            if row_count < MIN_ROW_FLOOR:
                raise RuntimeError(
                    f"Integrity check failed: downloaded file has only {row_count} rows "
                    f"(floor: {MIN_ROW_FLOOR}). File may be truncated or empty."
                )

            temp_destination.replace(destination)
            file_size_mb = destination.stat().st_size / (1024 * 1024)
            logger.info(
                "Download completed successfully: %s (%.2f MB, %d rows validated)",
                destination.name,
                file_size_mb,
                row_count,
            )
            return destination

        except Exception as exc:
            last_exc = exc
            if temp_destination.exists():
                temp_destination.unlink()
            if attempt < max_retries:
                wait_s = 5 * attempt
                logger.warning(
                    "Download attempt %d/%d failed: %s. Retrying in %ds...",
                    attempt, max_retries, exc, wait_s,
                )
                time.sleep(wait_s)
            else:
                logger.error(
                    "All %d download attempts failed for %s: %s",
                    max_retries, url, exc,
                )

    raise last_exc  # type: ignore[misc]


def ingest_to_duckdb(
    db_path: Path,
    prices_csv: Path,
    markets_csv: Path,
    preserve_existing_table: bool = True,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Ingest downloaded CSV resources into DuckDB tables and log execution metrics.

    Preserves pre-existing raw tables if requested, recreates target raw
    tables to ensure clean, idempotent data ingestion, and writes audit metadata.

    Args:
        db_path: Path to the target DuckDB database file.
        prices_csv: Path to downloaded food prices CSV.
        markets_csv: Path to downloaded markets reference CSV.
        preserve_existing_table: If True, preserves previous raw_wfp_prices table.
        run_id: Optional identifier for current run. Generated if not supplied.

    Returns:
        Dictionary containing ingestion summary statistics.
    """
    current_run_id = run_id or str(uuid.uuid4())
    start_time = time.perf_counter()
    started_at = datetime.datetime.now(datetime.timezone.utc)

    logger.info("Opening DuckDB database at: %s", db_path)
    con = duckdb.connect(str(db_path))

    try:
        existing_tables = [
            row[0] for row in con.execute("SHOW TABLES").fetchall()
        ]
        logger.info("Existing database tables: %s", existing_tables)

        if preserve_existing_table and "raw_wfp_prices" in existing_tables:
            if "raw_wfp_prices_previous" not in existing_tables:
                logger.info(
                    "Preserving existing raw_wfp_prices as raw_wfp_prices_previous"
                )
                con.execute(
                    "CREATE TABLE raw_wfp_prices_previous AS SELECT * FROM raw_wfp_prices"
                )
            else:
                logger.info(
                    "Table raw_wfp_prices_previous already exists; retaining existing historical copy"
                )

        # Ingest incoming food prices dataset
        logger.info("Loading food prices from %s into raw_wfp_prices", prices_csv)
        con.execute("DROP TABLE IF EXISTS raw_wfp_prices")
        con.execute(f"""
            CREATE TABLE raw_wfp_prices AS 
            SELECT * FROM read_csv_auto(
                '{prices_csv.as_posix()}',
                header=True,
                all_varchar=False
            )
        """)

        # Ingest incoming markets dataset
        logger.info("Loading markets reference from %s into raw_wfp_markets", markets_csv)
        con.execute("DROP TABLE IF EXISTS raw_wfp_markets")
        con.execute(f"""
            CREATE TABLE raw_wfp_markets AS 
            SELECT * FROM read_csv_auto(
                '{markets_csv.as_posix()}',
                header=True,
                all_varchar=False
            )
        """)

        prices_count = con.execute("SELECT COUNT(*) FROM raw_wfp_prices").fetchone()[0]
        markets_count = con.execute("SELECT COUNT(*) FROM raw_wfp_markets").fetchone()[0]
        date_range = con.execute(
            "SELECT MIN(date), MAX(date) FROM raw_wfp_prices"
        ).fetchone()
        distinct_commodities = con.execute(
            "SELECT COUNT(DISTINCT commodity) FROM raw_wfp_prices"
        ).fetchone()[0]
        distinct_markets = con.execute(
            "SELECT COUNT(DISTINCT market) FROM raw_wfp_prices"
        ).fetchone()[0]

        completed_at = datetime.datetime.now(datetime.timezone.utc)
        duration_s = time.perf_counter() - start_time
        total_records = prices_count + markets_count

        record_pipeline_run(
            con=con,
            run_id=current_run_id,
            started_at=started_at,
            completed_at=completed_at,
            pipeline_step="hdx_raw_ingestion",
            status="SUCCESS",
            records_affected=total_records,
            execution_time_s=round(duration_s, 3),
            error_details=None,
        )

        summary = {
            "status": "success",
            "run_id": current_run_id,
            "prices_total_rows": prices_count,
            "markets_total_rows": markets_count,
            "min_date": str(date_range[0]),
            "max_date": str(date_range[1]),
            "unique_commodities": distinct_commodities,
            "unique_markets": distinct_markets,
            "tables_in_db": [r[0] for r in con.execute("SHOW TABLES").fetchall()],
            "duration_s": round(duration_s, 3),
        }
        return summary
    except Exception as exc:
        completed_at = datetime.datetime.now(datetime.timezone.utc)
        duration_s = time.perf_counter() - start_time
        try:
            record_pipeline_run(
                con=con,
                run_id=current_run_id,
                started_at=started_at,
                completed_at=completed_at,
                pipeline_step="hdx_raw_ingestion",
                status="FAILED",
                records_affected=0,
                execution_time_s=round(duration_s, 3),
                error_details=str(exc),
            )
        except Exception as inner_exc:
            logger.error("Failed to write error audit record: %s", str(inner_exc))
        raise
    finally:
        con.close()
        logger.info("DuckDB connection closed.")


def main() -> None:
    """Execute the full download and ingestion workflow."""
    raw_dir = DEFAULT_RAW_DATA_DIR
    db_file = DEFAULT_DUCKDB_PATH
    run_id = f"run_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    logger.info("Starting HDX data ingestion workflow (Run ID: %s)", run_id)

    prices_path = raw_dir / "wfp_food_prices_gha.csv"
    markets_path = raw_dir / "wfp_markets_gha.csv"

    download_file(RESOURCE_URLS["food_prices"], prices_path)
    download_file(RESOURCE_URLS["markets"], markets_path)

    summary = ingest_to_duckdb(
        db_path=db_file,
        prices_csv=prices_path,
        markets_csv=markets_path,
        preserve_existing_table=True,
        run_id=run_id,
    )

    logger.info("================ INGESTION SUMMARY ================")
    logger.info("Run ID: %s", summary["run_id"])
    logger.info("Database: %s", db_file.resolve())
    logger.info("Tables Present: %s", summary["tables_in_db"])
    logger.info("Prices Table (raw_wfp_prices) Row Count: %d", summary["prices_total_rows"])
    logger.info("Markets Table (raw_wfp_markets) Row Count: %d", summary["markets_total_rows"])
    logger.info("Date Range: %s to %s", summary["min_date"], summary["max_date"])
    logger.info("Unique Commodities: %d", summary["unique_commodities"])
    logger.info("Unique Markets in Prices: %d", summary["unique_markets"])
    logger.info("Execution Time: %.2f seconds", summary["duration_s"])
    logger.info("===================================================")


if __name__ == "__main__":
    main()
