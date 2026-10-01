"""
Pipeline Run Logger
====================
Provides a PipelineLogger class that writes every pipeline step outcome —
success or failure — to a persistent `pipeline_run_log` table inside the
DuckDB analytical warehouse.

This satisfies the mentor requirement for database-level error logging so
that every pipeline run is permanently auditable, not just visible on the
console during execution.

Usage:
    from utils.pipeline_logger import PipelineLogger

    logger = PipelineLogger()
    logger.success("2_transform_data", rows_affected=36204, duration_seconds=4.2)
    logger.error("3_build_analytics_views", exception=e, duration_seconds=1.1)
    print(logger.get_run_history())
"""

import duckdb
import logging
import traceback
from datetime import datetime, timezone

DB_PATH = "agri_ghana.duckdb"

_console = logging.getLogger("pipeline_logger")
if not _console.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_run_log (
    run_id           INTEGER,
    script_name      VARCHAR,
    status           VARCHAR,
    message          VARCHAR,
    rows_affected    INTEGER,
    duration_seconds DOUBLE,
    run_at           TIMESTAMP
)
"""

_NEXT_RUN_ID_SQL = """
SELECT COALESCE(MAX(run_id), 0) + 1 FROM pipeline_run_log
"""


class PipelineLogger:
    """
    Writes pipeline step outcomes to `pipeline_run_log` in DuckDB.

    Opens and closes a dedicated short-lived DuckDB connection for each
    write so it does not conflict with connections held by the pipeline
    scripts themselves.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_table()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def success(self, script_name: str, rows_affected: int = 0, duration_seconds: float = 0.0):
        """Log a successful pipeline step."""
        message = f"{script_name} completed successfully. Rows affected: {rows_affected:,}."
        self._write(script_name, "SUCCESS", message, rows_affected, duration_seconds)
        _console.info(f"[LOG → DB] {script_name} SUCCESS — {rows_affected:,} rows in {duration_seconds:.1f}s")

    def error(self, script_name: str, exception: Exception, duration_seconds: float = 0.0):
        """Log a failed pipeline step, capturing the exception message."""
        message = f"{type(exception).__name__}: {str(exception)[:500]}"
        self._write(script_name, "ERROR", message, 0, duration_seconds)
        _console.error(f"[LOG → DB] {script_name} ERROR — {message}")

    def log(self, script_name: str, status: str, message: str,
            rows_affected: int = 0, duration_seconds: float = 0.0):
        """Generic log entry. status should be 'SUCCESS', 'ERROR', or 'WARNING'."""
        self._write(script_name, status.upper(), message, rows_affected, duration_seconds)

    def get_run_history(self, n: int = 20):
        """Return the last n log entries as a pandas DataFrame."""
        try:
            con = duckdb.connect(self.db_path)
            df = con.execute(f"""
                SELECT run_id, script_name, status, message, rows_affected,
                       ROUND(duration_seconds, 2) AS duration_seconds, run_at
                FROM pipeline_run_log
                ORDER BY run_at DESC
                LIMIT {n}
            """).fetchdf()
            con.close()
            return df
        except Exception as e:
            _console.warning(f"[PipelineLogger] Could not fetch run history: {e}")
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_table(self):
        """Create pipeline_run_log if it does not already exist."""
        try:
            con = duckdb.connect(self.db_path)
            con.execute(CREATE_TABLE_SQL)
            con.close()
        except Exception as e:
            _console.warning(f"[PipelineLogger] Could not initialise log table: {e}")

    def _write(self, script_name: str, status: str, message: str,
               rows_affected: int, duration_seconds: float):
        """Insert one log row. Opens and closes its own connection."""
        try:
            con = duckdb.connect(self.db_path)
            run_id = con.execute(_NEXT_RUN_ID_SQL).fetchone()[0]
            con.execute("""
                INSERT INTO pipeline_run_log
                    (run_id, script_name, status, message, rows_affected, duration_seconds, run_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [run_id, script_name, status, message, rows_affected,
                  duration_seconds, datetime.now(timezone.utc)])
            con.close()
        except Exception as e:
            # Never let logging failures crash the pipeline
            _console.warning(f"[PipelineLogger] DB write failed (continuing): {e}")
