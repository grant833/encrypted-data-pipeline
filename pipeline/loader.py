"""
Warehouse loader.

Loads cleaned, identity-resolved records into the customer_applications
warehouse table using SQLAlchemy Core for fast bulk inserts. Postgres is
the primary load target; Snowflake support is stubbed for a later phase.
"""

import logging
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


COLUMN_MAPPING = {
    "first_name": "first_name",
    "middle_initial": "middle_initial",
    "last_name": "last_name",
    "street_address": "street_address",
    "city": "city",
    "state": "state",
    "zip_code": "zip_code",
    "application_id": "application_id",
    "customer_id": "customer_id",
    "identity_id": "identity_id",
    "division_id": "division_id",
    "submitted_date": "submitted_date",
    "application_status": "application_status",
    "email_address": "email_address",
    "date_of_birth": "date_of_birth",
}


def load_to_postgres(
    df: pd.DataFrame,
    pipeline_run_id: str,
    engine: Engine,
    table_name: str = "customer_applications",
    chunksize: int = 5000,
) -> int:
    """
    Bulk-load a dataframe into the customer_applications table using
    SQLAlchemy Core. Faster and more reliable than pandas.to_sql() for
    large inserts.

    Args:
        df: Records to load (must already be resolved with identity_id)
        pipeline_run_id: Unique identifier for this pipeline run
        engine: SQLAlchemy engine
        table_name: Target table name (default: customer_applications)
        chunksize: Rows per insert batch

    Returns:
        Number of rows loaded
    """
    if df.empty:
        logger.warning("Empty dataframe passed to loader; nothing to load")
        return 0

    df = df.copy()

    # Select and rename source columns
    source_cols = [c for c in COLUMN_MAPPING.keys() if c in df.columns]
    if not source_cols:
        raise ValueError(
            "No matching columns found between dataframe and target table"
        )
    df_to_load = df[source_cols].rename(columns=COLUMN_MAPPING)

    # Add pipeline metadata
    df_to_load["pipeline_run_id"] = pipeline_run_id
    df_to_load["source_system"] = "NORTHSTAR_FINANCIAL"

    # Convert NaN to None so they become SQL NULLs
    df_to_load = df_to_load.astype(object).where(pd.notna(df_to_load), None)

    pre_count = len(df_to_load)
    logger.info(f"Loading {pre_count:,} records into {table_name}...")

    # Reflect the target table's schema from the database
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)

    # Convert dataframe to list of dicts (one per record)
    records = df_to_load.to_dict(orient="records")

    # Bulk insert in chunks
    with engine.begin() as conn:
        for i in range(0, len(records), chunksize):
            chunk = records[i:i + chunksize]
            conn.execute(table.insert(), chunk)

    logger.info(f"Loaded {pre_count:,} records into {table_name}")
    return pre_count


def load_to_snowflake(
    df: pd.DataFrame,
    pipeline_run_id: str,
    snowflake_conn_params: Dict[str, str],
    table_name: str = "CUSTOMER_APPLICATIONS",
) -> int:
    """
    Bulk-load a dataframe into Snowflake.

    Stubbed for now — will be wired up when Snowflake account is configured
    in a later phase.
    """
    logger.info("Snowflake load is stubbed; skipping until cloud setup complete")
    return 0


def load_to_warehouses(
    df: pd.DataFrame,
    pipeline_run_id: str,
    pg_engine: Engine,
    snowflake_params: Optional[Dict[str, str]] = None,
) -> Dict[str, int]:
    """Load to all configured warehouses in sequence."""
    results = {"postgres": 0, "snowflake": 0}
    results["postgres"] = load_to_postgres(df, pipeline_run_id, pg_engine)
    if snowflake_params:
        results["snowflake"] = load_to_snowflake(df, pipeline_run_id, snowflake_params)
    return results
