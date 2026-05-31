"""
Customer Application Pipeline DAG.

End-to-end encrypted, cloud-integrated:
    Vendor encrypts file with inbound key, uploads to S3 inbound bucket
    -> ingest_file downloads from S3, decrypts with private key
    -> reject_rules -> suppression -> identity_resolution -> load -> audit
    -> encrypt_outbound (encrypts summary, uploads to S3 outbound bucket)
    -> send_alert

The load_to_warehouse task truncates customer_applications, rejected_records,
and suppression_exclusions before each fresh load. The 'history' lives in
pipeline_audit_log (never truncated), which is what the Streamlit dashboard
queries for run-over-run trends.
"""

import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

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
from pipeline.encryption import decrypt_file, encrypt_file
from pipeline.s3_utils import (
    download_file as s3_download,
    upload_file as s3_upload,
    get_latest_object,
)

logger = logging.getLogger(__name__)

POSTGRES_CONN_STRING = (
    "postgresql+psycopg2://pipeline_user:Tesla2345!@localhost/pipeline_db"
)
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


def _temp_path(pipeline_run_id: str, stage: str, ext: str = "parquet") -> str:
    run_dir = Path(TEMP_DIR) / pipeline_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return str(run_dir / f"{stage}.{ext}")


@dag(
    dag_id="customer_application_pipeline",
    description="End-to-end encrypted customer application data pipeline (S3-integrated)",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["customer_applications", "encrypted", "s3", "northstar_financial"],
)
def customer_application_pipeline():

    @task
    def initialize_run() -> str:
        run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"Pipeline run ID: {run_id}")
        return run_id

    @task
    def ingest_file(pipeline_run_id: str) -> str:
        """
        Find latest .pgp file in S3 inbound bucket, download it, decrypt it,
        and parse the plaintext into a dataframe.
        """
        engine = _get_engine()

        inbound_bucket = os.getenv("S3_INBOUND_BUCKET")
        if not inbound_bucket:
            raise RuntimeError("S3_INBOUND_BUCKET env var not set")

        # Find the most recent .pgp file in the inbound bucket
        latest = get_latest_object(inbound_bucket)
        if not latest:
            raise FileNotFoundError(
                f"No objects found in s3://{inbound_bucket}/"
            )

        logger.info(
            f"Latest inbound: {latest['Key']} "
            f"({latest['Size']:,} bytes, {latest['LastModified']})"
        )

        # Download the encrypted file to a temp location
        encrypted_path = _temp_path(pipeline_run_id, "encrypted_input", ext="pgp")
        ok = s3_download(inbound_bucket, latest["Key"], encrypted_path)
        if not ok:
            raise RuntimeError(f"Failed to download s3://{inbound_bucket}/{latest['Key']}")

        # Decrypt
        decrypted_path = _temp_path(pipeline_run_id, "decrypted_input", ext="txt")
        ok = decrypt_file(encrypted_path, decrypted_path)
        if not ok:
            raise RuntimeError(f"Failed to decrypt {encrypted_path}")
        logger.info(f"Decrypted to {decrypted_path}")

        # Read into dataframe
        df = pd.read_csv(decrypted_path, sep="|", dtype=str)
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

        # Truncate previous day's records before loading fresh data.
        # The 'history' lives in pipeline_audit_log; this table holds the
        # most recent batch only. This makes the scheduled 3am UTC run
        # idempotent against the same incoming file.
        with engine.begin() as conn:
            conn.execute(text(
                "TRUNCATE TABLE customer_applications, "
                "suppression_exclusions, rejected_records RESTART IDENTITY CASCADE"
            ))

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
    def encrypt_outbound(pipeline_run_id: str, audit_summary: dict) -> str:
        """
        Build a summary report, encrypt with vendor public key, upload to
        S3 outbound bucket as the delivery confirmation.
        """
        vendor_key = os.getenv("GPG_VENDOR_KEY_ID")
        outbound_bucket = os.getenv("S3_OUTBOUND_BUCKET")

        if not vendor_key:
            logger.warning("GPG_VENDOR_KEY_ID not set; skipping outbound")
            return ""
        if not outbound_bucket:
            logger.warning("S3_OUTBOUND_BUCKET not set; skipping outbound")
            return ""

        # Build plaintext summary
        plaintext_path = _temp_path(pipeline_run_id, "outbound_summary", ext="txt")
        with open(plaintext_path, "w") as f:
            f.write("Northstar Pipeline — Daily Delivery Confirmation\n")
            f.write("=" * 50 + "\n")
            f.write(f"Run ID:           {pipeline_run_id}\n")
            f.write(f"Records Loaded:   {audit_summary.get('total_loaded', 0):,}\n")
            f.write(f"Match Rate:       {audit_summary.get('match_rate_pct', 0):.2f}%\n")
            f.write(f"New Identities:   {audit_summary.get('new_identities', 0):,}\n")
            f.write(f"Generated:        {datetime.utcnow().isoformat()}Z\n")

        # Encrypt with vendor public key
        encrypted_local = _temp_path(pipeline_run_id, "outbound_summary", ext="pgp")
        ok = encrypt_file(plaintext_path, encrypted_local, vendor_key)
        if not ok:
            raise RuntimeError("Failed to encrypt outbound delivery file")

        # Upload to outbound S3 bucket
        s3_key = f"delivery_{pipeline_run_id}.txt.pgp"
        ok = s3_upload(encrypted_local, outbound_bucket, s3_key)
        if not ok:
            raise RuntimeError(f"Failed to upload to s3://{outbound_bucket}/{s3_key}")

        logger.info(f"Outbound delivery uploaded: s3://{outbound_bucket}/{s3_key}")
        return f"s3://{outbound_bucket}/{s3_key}"

    @task
    def send_completion_alert(pipeline_run_id: str, audit_summary: dict) -> None:
        engine = _get_engine()

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
    outbound = encrypt_outbound(run_id, audit_result)
    audit_result >> outbound >> send_completion_alert(run_id, audit_result)


dag = customer_application_pipeline()
