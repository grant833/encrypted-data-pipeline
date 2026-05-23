"""
SQL audit layer.

Runs a battery of audit queries after every pipeline run to verify counts,
surface anomalies, and log metrics to pipeline_audit_log. Mirrors the
count auditing done on every production pipeline run.
"""

import logging
from typing import Dict

import pandas as pd
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


AUDIT_QUERIES = {
    "total_loaded": """
        SELECT COUNT(*) AS count
        FROM wh_cl_application
        WHERE data_collection_id = %(run_id)s
    """,
    "status_breakdown": """
        SELECT app_status_flag, COUNT(*) AS count
        FROM wh_cl_application
        WHERE data_collection_id = %(run_id)s
        GROUP BY app_status_flag
        ORDER BY count DESC
    """,
    "identity_match_rate": """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN i.source_hash IS NOT NULL THEN 1 ELSE 0 END) AS matched,
            ROUND(SUM(CASE WHEN i.source_hash IS NOT NULL THEN 1 ELSE 0 END)
                  * 100.0 / NULLIF(COUNT(*), 0), 2) AS match_rate
        FROM wh_cl_application a
        LEFT JOIN wh_identity i ON a.application_id = i.data_src_cd
        WHERE a.data_collection_id = %(run_id)s
    """,
    "suppression_summary": """
        SELECT suppression_source, COUNT(*) AS suppressed_count
        FROM suppression_exclusions
        WHERE pipeline_run_id = %(run_id)s
        GROUP BY suppression_source
    """,
    "volume_vs_baseline": """
        SELECT
            (SELECT COUNT(*) FROM wh_cl_application
             WHERE data_collection_id = %(run_id)s) AS today_count,
            (SELECT AVG(record_count) FROM pipeline_audit_log
             WHERE feed_name = 'APPLICATION'
               AND stage = 'LOAD'
               AND run_timestamp >= NOW() - INTERVAL '30 days') AS baseline_avg
    """,
}


def run_audit_queries(pipeline_run_id: str, engine: Engine) -> Dict[str, pd.DataFrame]:
    """
    Run all audit queries for a pipeline run and return results.

    Args:
        pipeline_run_id: Unique identifier for this pipeline run
        engine: SQLAlchemy engine

    Returns:
        Dict mapping query_name -> result DataFrame
    """
    # TODO: Iterate AUDIT_QUERIES, run each with pipeline_run_id param
    # TODO: Log each result
    # TODO: Return dict of results
    raise NotImplementedError


def write_audit_log(
    pipeline_run_id: str,
    feed_name: str,
    stage: str,
    record_count: int,
    rejected_count: int = 0,
    suppressed_count: int = 0,
    status: str = "SUCCESS",
    error_message: str = None,
    engine: Engine = None,
) -> None:
    """Insert a row into pipeline_audit_log."""
    # TODO: INSERT INTO pipeline_audit_log
    raise NotImplementedError


def check_volume_anomaly(
    pipeline_run_id: str,
    feed_name: str,
    threshold_pct: float = 0.40,
    engine: Engine = None,
) -> bool:
    """
    Compare today's volume against the 30-day average.

    Returns:
        True if volume is anomalous (>threshold_pct deviation), False otherwise
    """
    # TODO: Run volume_vs_baseline query, compare today_count vs baseline_avg
    raise NotImplementedError
