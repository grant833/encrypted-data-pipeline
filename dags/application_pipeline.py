"""
Customer Application Pipeline DAG.

Orchestrates the full customer application file processing chain:
    ingest_file -> reject_rules -> suppression -> identity_resolution
    -> load_warehouse -> run_audit -> send_alert

Each task writes its output dataframe to a temp file in /tmp/pipeline_runs/{run_id}/
and passes the file path to the next task via XCom.
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from airflow.decorators import dag, task

from pipeline.reject_rules import (
    PreProcessRejectEngine,
    CUSTOMER_APPLICATION_RULES,
)
from pipeline.suppression_engine import SuppressionEngine
from pipeline.identity_resolution import IdentityResolver
from pipeline.loader import load_to_postgres
from pipeline.audit import run_audit_queries, write_audit_log
from pipeline.alerting import send_success_alert, airflow_failure_callback

logger = logging.getLogger(__name__)

POSTGRES_CONN_STRING = (
    "postgresql+psycopg2://pipeline_user:Tesla2345!@localhost/pipeline_db"
)
DATA_DIR = "/home/grant/pipeline-project/data"
TEMP_DIR = "/tmp/pipeline_runs"
FEED_NAME = "customer_applications"


default_args = {
    "owner": "grant",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
    "on_failure_callback": airflow_failure_callback,
}


def _get_engine():
    return create_engine(POSTGRES_CONN_STRING)


def _temp_path(pipeline_run_id: str, stage: str) -> str:
    run_dir = Path(TEMP_DIR) / pipeline_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return str(run_dir / f"{stage}.parquet")


@dag(
    dag_id="customer_application_pipeline",
    description="End-to-end customer application data pipeline",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["customer_applications", "inbound", "northstar_financial"],
)
def customer_application_pipeline():
    """The full pipeline DAG."""

    @task
    def initialize_run() -> str:
        run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"Pipeline run ID: {run_id}")
        return run_id

    @task
    def ingest_file(pipeline_run_id: str) -> str:
        engine = _get_engine()
        data_files = sorted(Path(DATA_DIR).glob("customer_applications_*.txt"))
        if not data_files:
            raise FileNotFoundError(f"No input files found in {DATA_DIR}")
        input_file = str(data_files[-1])
        logger.info(f"Ingesting {input_file}")

        df = pd.read_csv(input_file, sep="|", dtype=str)
        logger.info(f"Loaded {len(df):,} records")

        write_audit_log(pipeline_run_id, FEED_NAME, "ingest", len(df), engine)

        output_path = _temp_path(pipeline_run_id, "ingest")
        df.to_parquet(output_path, index=False)
        return output_path

    @task
    def apply_reject_rules(input_path: str, pipeline_run_id: str) -> str:
        engine = _get_engine()
        t0 = time.time()

        df = pd.read_parquet(input_path)
        reject_engine = PreProcessRejectEngine(
            CUSTOMER_APPLICATION_RULES, reject_threshold=0.10
        )
        passed, rejected = reject_engine.apply_rules(df)

        write_audit_log(
            pipeline_run_id, FEED_NAME, "reject_rules",
            len(passed), engine,
            rejected_count=len(rejected),
            runtime_seconds=time.time() - t0,
        )

        output_path = _temp_path(pipeline_run_id, "reject_rules")
        passed.to_parquet(output_path, index=False)
        return output_path

    @task
    def apply_suppression(input_path: str, pipeline_run_id: str) -> str:
        engine = _get_engine()
        t0 = time.time()

        df = pd.read_parquet(input_path)
        suppression_engine = SuppressionEngine(engine)
        included, excluded = suppression_engine.apply_suppressions(df)

        write_audit_log(
            pipeline_run_id, FEED_NAME, "suppression",
            len(included), engine,
            suppressed_count=len(excluded),
            runtime_seconds=time.time() - t0,
        )

        output_path = _temp_path(pipeline_run_id, "suppression")
        included.to_parquet(output_path, index=False)
        return output_path

    @task
    def resolve_identities(input_path: str, pipeline_run_id: str) -> str:
        engine = _get_engine()
        t0 = time.time()

        df = pd.read_parquet(input_path)
        resolver = IdentityResolver(engine)
        resolved = resolver.resolve_identities(df)

        write_audit_log(
            pipeline_run_id, FEED_NAME, "identity_resolution",
            len(resolved), engine,
            runtime_seconds=time.time() - t0,
        )

        output_path = _temp_path(pipeline_run_id, "identity_resolution")
        resolved.to_parquet(output_path, index=False)
        return output_path

    @task
    def load_to_warehouse(input_path: str, pipeline_run_id: str) -> int:
        engine = _get_engine()
        t0 = time.time()

        df = pd.read_parquet(input_path)
        loaded_count = load_to_postgres(df, pipeline_run_id, engine)

        write_audit_log(
            pipeline_run_id, FEED_NAME, "load",
            loaded_count, engine,
            runtime_seconds=time.time() - t0,
        )
        return loaded_count

    @task
    def run_post_load_audit(pipeline_run_id: str, loaded_count: int) -> dict:
        engine = _get_engine()
        results = run_audit_queries(pipeline_run_id, engine)

        summary = {
            "pipeline_run_id": pipeline_run_id,
            "total_loaded": int(results["total_loaded"]["count"].iloc[0])
                            if not results["total_loaded"].empty else 0,
        }

        if not results["identity_match_rate"].empty:
            match_row = results["identity_match_rate"].iloc[0]
            summary["match_rate_pct"] = float(match_row["match_rate_pct"] or 0)
            summary["new_identities"] = int(match_row["new_identities"] or 0)

        logger.info(f"Audit summary: {summary}")
        return summary

    @task
    def send_completion_alert(pipeline_run_id: str, audit_summary: dict) -> None:
        """Send a Slack success message at the end of the pipeline."""
        engine = _get_engine()

        # Pull the timing and counts from the audit log
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    SUM(runtime_seconds) AS total_runtime,
                    SUM(rejected_count) AS total_rejected,
                    SUM(suppressed_count) AS total_suppressed
                FROM pipeline_audit_log
                WHERE pipeline_run_id = :run_id
            """), {"run_id": pipeline_run_id}).fetchone()

        total_runtime = float(result[0] or 0)
        total_rejected = int(result[1] or 0)
        total_suppressed = int(result[2] or 0)

        send_success_alert(
            feed_name=FEED_NAME,
            pipeline_run_id=pipeline_run_id,
            record_count=audit_summary.get("total_loaded", 0),
            rejected_count=total_rejected,
            suppressed_count=total_suppressed,
            runtime_seconds=total_runtime,
        )

    # === Pipeline dependency chain ===
    run_id = initialize_run()
    ingested = ingest_file(run_id)
    validated = apply_reject_rules(ingested, run_id)
    suppressed = apply_suppression(validated, run_id)
    resolved = resolve_identities(suppressed, run_id)
    loaded = load_to_warehouse(resolved, run_id)
    audit_result = run_post_load_audit(run_id, loaded)
    send_completion_alert(run_id, audit_result)


dag = customer_application_pipeline()
