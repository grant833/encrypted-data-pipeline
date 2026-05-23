"""
Suppression engine.

Checks incoming records against multiple suppression tables (CCPA opt-outs,
credit abusers, custom client lists) and flags matches for exclusion.
Mirrors the JITSUP suppression workflow used in production.
"""

import logging
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# Maps suppression table name -> key field used for matching
SUPPRESSION_TABLES: Dict[str, str] = {
    "ccpa_donotsell": "email_addr",
    "ccpa_delete": "email_addr",
    "credit_abusers": "Application_ID",
}


class SuppressionEngine:
    """
    Applies multiple suppression checks to an incoming dataframe.

    For each suppression source, matches records on the appropriate key field
    and flags matches for exclusion. Returns separate dataframes for included
    and excluded records, with suppression source attached to excluded records.
    """

    def __init__(self, db_engine: Engine, suppression_tables: Dict[str, str] = None):
        """
        Args:
            db_engine: SQLAlchemy engine connected to Postgres
            suppression_tables: Dict mapping table_name -> key_field
                                (defaults to SUPPRESSION_TABLES)
        """
        self.engine = db_engine
        self.suppression_tables = suppression_tables or SUPPRESSION_TABLES

    def load_suppression_lists(self) -> Dict[str, set]:
        """
        Load all suppression keys from Postgres into memory as sets for fast lookup.

        Returns:
            Dict mapping table_name -> set of suppression keys (uppercased)
        """
        # TODO: For each table, SELECT the key field and load into a set
        # TODO: Uppercase keys for case-insensitive matching
        raise NotImplementedError

    def apply_suppressions(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply all suppression checks and split the dataframe.

        Args:
            df: Incoming records dataframe

        Returns:
            (included_df, excluded_df) — excluded_df has suppression_source column
        """
        # TODO: Load suppression lists
        # TODO: For each table, check df[key_field].str.upper().isin(suppression_set)
        # TODO: Flag matches with suppression_source = table_name
        # TODO: Split into included and excluded dataframes
        # TODO: Log counts by suppression source
        raise NotImplementedError

    def log_excluded_to_db(self, excluded_df: pd.DataFrame, pipeline_run_id: str) -> None:
        """Write excluded records to the suppression_exclusions audit table."""
        # TODO: Append excluded records to suppression_exclusions table
        raise NotImplementedError
