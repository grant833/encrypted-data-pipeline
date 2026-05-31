"""
Warehouse loader for the pipeline.

Bulk-loads resolved records into the PostgreSQL warehouse using SQLAlchemy
Core, which is significantly faster than row-by-row INSERTs.
"""

import logging
from typing import Dict

import pandas as pd
from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# Columns we expect on customer_applications, in insert order
CUSTOMER_APPLICATIONS_COLUMNS = [
    "pipeline_run_id",
    "source_system",
    "application_id",
    "customer_id",
    "identity_id",
    "first_name",
    "middle_initial",
    "last_name",
    "street_address",
    "city",
    "state",
    "zip_code",
    "division_id",
    "submitted_date",
    "application_status",
    "email_address",
    "date_of_birth",
]


def load_to_postgres(
    df: pd.DataFrame,
    pipeline_run_id: str,
    engine: Engine,
    chunk_size: int = 5000,
) -> int:
    """
    Bulk-load a dataframe into customer_applications via SQLAlchemy Core.

    Uses chunked inserts to avoid blowing out memory on large batches. The
    pandas.to_sql() helper has compatibility issues with newer pandas
    versions, so we use Core inserts directly.

    Args:
        df: DataFrame of resolved records (must have identity_id column)
        pipeline_run_id: Unique run identifier
        engine: SQLAlchemy engine
        chunk_size: Records per INSERT statement

    Returns:
        Number of records inserted
    """
    if df.empty:
        logger.warning("Empty dataframe; nothing to load")
        return 0

    # Make sure pipeline_run_id and source_system are present
    df = df.copy()
    df["pipeline_run_id"] = pipeline_run_id
    if "source_system" not in df.columns:
        df["source_system"] = "NORTHSTAR_FINANCIAL"

    # Only keep columns we expect on the target table
    cols = [c for c in CUSTOMER_APPLICATIONS_COLUMNS if c in df.columns]
    df = df[cols]

    # Convert to list of dicts for SQLAlchemy
    records = df.to_dict(orient="records")
    total = len(records)
    logger.info(f"Loading {total:,} records into customer_applications...")

    metadata = MetaData()
    table = Table("customer_applications", metadata, autoload_with=engine)

    inserted = 0
    with engine.begin() as conn:
        for i in range(0, total, chunk_size):
            chunk = records[i : i + chunk_size]
            conn.execute(table.insert(), chunk)
            inserted += len(chunk)

    logger.info(f"Loaded {inserted:,} records into customer_applications")
    return inserted
