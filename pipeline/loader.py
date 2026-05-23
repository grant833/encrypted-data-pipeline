"""
Warehouse loader.

Loads cleaned, resolved records into both local Postgres and cloud Snowflake.
Uses bulk inserts for performance; logs row counts before and after to verify
nothing got dropped in transit.
"""

import logging
from typing import Dict

import pandas as pd
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def load_to_postgres(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    if_exists: str = "append",
    chunksize: int = 5000,
) -> int:
    """
    Bulk-load a dataframe into a Postgres table.

    Args:
        df: Records to load
        table_name: Target table name in Postgres
        engine: SQLAlchemy engine
        if_exists: 'append' (default), 'replace', or 'fail'
        chunksize: Rows per insert batch

    Returns:
        Number of rows loaded
    """
    # TODO: df.to_sql with method='multi' for bulk insert
    # TODO: Log row count before and after
    raise NotImplementedError


def load_to_snowflake(
    df: pd.DataFrame,
    table_name: str,
    snowflake_conn_params: Dict[str, str],
    if_exists: str = "append",
) -> int:
    """
    Bulk-load a dataframe into a Snowflake table.

    Args:
        df: Records to load
        table_name: Target table name in Snowflake (uppercase by convention)
        snowflake_conn_params: Dict with account, user, password, warehouse,
                               database, schema, role
        if_exists: 'append' (default), 'replace', or 'fail'

    Returns:
        Number of rows loaded
    """
    # TODO: Use snowflake.connector.pandas_tools.write_pandas() for fast load
    # TODO: Log row count before and after
    raise NotImplementedError


def load_to_both_warehouses(
    df: pd.DataFrame,
    table_name: str,
    pg_engine: Engine,
    sf_params: Dict[str, str],
) -> Dict[str, int]:
    """
    Load to both Postgres and Snowflake in sequence.

    Returns:
        Dict with keys 'postgres' and 'snowflake', values are row counts loaded
    """
    # TODO: Call load_to_postgres, then load_to_snowflake
    # TODO: Verify counts match
    raise NotImplementedError
