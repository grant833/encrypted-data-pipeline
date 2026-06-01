"""
SQL audit layer.

Runs a battery of audit queries after every pipeline run to verify
counts, surface anomalies, and log metrics to pipeline_audit_log.
"""

import logging
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


AUDIT_QUERIES: Dict[str, str] = {
    "total_loaded": """
        SELECT COUNT(*) AS count
        FROM customer_applications
        WHERE pipeline_run_id = :run_id
    """,
    "status_breakdown": """
        SELECT application_status, COUNT(*) AS count
        FROM customer_applications
        WHERE pipeline_run_id = :run_id
        GROUP BY application_status
        ORDER BY count DESC
    """,
    "identity_match_rate": """
        WITH run_records AS (
            SELECT identity_id
            FROM customer_applications
            WHERE pipeline_run_id = :run_id
        ),
        identity_first_seen AS (
            SELECT
                r.identity_id,
                i.first_seen_timestamp,
                CASE
                    WHEN i.first_seen_timestamp < CURRENT_DATE THEN 'matched_existing'
                    ELSE 'newly_created'
                END AS identity_status
            FROM run_records r
            JOIN identities i ON r.identity_id = i.identity_id
        )
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN identity_status = 'matched_existing' THEN 1 ELSE 0 END) AS matched,
            SUM(CASE WHEN identity_status = 'newly_created' THEN 1 ELSE 0 END) AS new_identities,
            ROUND(
                SUM(CASE WHEN identity_status = 'matched_existing' THEN 1 ELSE 0 END)
                * 100.0 / NULLIF(COUNT(*), 0), 2
            ) AS match_rate_pct
        FROM identity_first_seen
    """,
    "suppression_summary": """
        SELECT suppression_source, COUNT(*) AS suppressed_count
        FROM suppression_exclusions
        WHERE pipeline_run_id = :run_id
        GROUP BY suppression_source
        ORDER BY suppressed_count DESC
    """,
    "reject_breakdown": """
        SELECT reject_reason, COUNT(*) AS reject_count
        FROM rejected_records
        WHERE pipeline_run_id = :run_id
        GROUP BY reject_reason
        ORDER BY reject_count DESC
    """,
    "state_distribution": """
        SELECT state, COUNT(*) AS count
        FROM customer_applications
        WHERE pipeline_run_id = :run_id
        GROUP BY state
        ORDER BY count DESC
        LIMIT 10
    """,
}


def _query_to_dataframe(sql: str, params: dict, engine: Engine) -> pd.DataFrame:
    """Execute a SQL query and return results as a DataFrame.

    Uses SQLAlchemy Core directly to avoid pandas.read_sql compatibility
    issues with newer pandas + older SQLAlchemy versions.
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.fetchall()
        columns = list(result.keys())
    return pd.DataFrame(rows, columns=columns)


def run_audit_queries(
    pipeline_run_id: str,
    engine: Engine,
) -> Dict[str, pd.DataFrame]:
    """
    Run all audit queries for a pipeline run.

    Args:
        pipeline_run_id: Unique identifier for this pipeline run
        engine: SQLAlchemy engine

    Returns:
        Dict mapping query_name -> result DataFrame
    """
    results = {}
    for query_name, sql in AUDIT_QUERIES.items():
        df = _query_to_dataframe(sql, {"run_id": pipeline_run_id}, engine)
        results[query_name] = df
        logger.info(f"Audit '{query_name}': {len(df)} row(s) returned")
    return results


def write_audit_log(
    pipeline_run_id: str,
    feed_name: str,
    stage: str,
    record_count: int,
    engine: Engine,
    rejected_count: int = 0,
    suppressed_count: int = 0,
    runtime_seconds: Optional[float] = None,
    status: str = "SUCCESS",
    error_message: Optional[str] = None,
) -> None:
    """Insert a row into pipeline_audit_log capturing the result of a stage."""
    insert_sql = text("""
        INSERT INTO pipeline_audit_log (
            pipeline_run_id, feed_name, stage, record_count,
            rejected_count, suppressed_count, runtime_seconds,
            status, error_message
        ) VALUES (
            :pipeline_run_id, :feed_name, :stage, :record_count,
            :rejected_count, :suppressed_count, :runtime_seconds,
            :status, :error_message
        )
    """)

    with engine.begin() as conn:
        conn.execute(
            insert_sql,
            {
                "pipeline_run_id": pipeline_run_id,
                "feed_name": feed_name,
                "stage": stage,
                "record_count": record_count,
                "rejected_count": rejected_count,
                "suppressed_count": suppressed_count,
                "runtime_seconds": runtime_seconds,
                "status": status,
                "error_message": error_message,
            },
        )


def check_volume_anomaly(
    feed_name: str,
    today_count: int,
    engine: Engine,
    threshold_pct: float = 0.40,
) -> Dict[str, float]:
    """Compare today's volume against the 30-day average."""
    baseline_sql = text("""
        SELECT AVG(record_count) AS baseline_avg
        FROM pipeline_audit_log
        WHERE feed_name = :feed_name
          AND stage = 'load'
          AND status = 'SUCCESS'
          AND run_timestamp >= NOW() - INTERVAL '30 days'
          AND run_timestamp < CURRENT_DATE
    """)

    with engine.connect() as conn:
        result = conn.execute(baseline_sql, {"feed_name": feed_name}).fetchone()

    baseline_avg = float(result[0]) if result and result[0] else 0.0

    if baseline_avg == 0:
        return {
            "today_count": today_count,
            "baseline_avg": 0.0,
            "pct_variance": 0.0,
            "is_anomalous": False,
            "note": "No baseline available yet",
        }

    pct_variance = (today_count - baseline_avg) / baseline_avg
    is_anomalous = abs(pct_variance) > threshold_pct

    return {
        "today_count": today_count,
        "baseline_avg": round(baseline_avg, 0),
        "pct_variance": round(pct_variance * 100, 2),
        "is_anomalous": is_anomalous,
    }
