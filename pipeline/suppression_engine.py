"""
Suppression engine.

Checks incoming records against multiple suppression tables and flags
matches for exclusion. Records that match a privacy opt-out, delete
request, or fraud flag are removed from the pipeline.
"""

import logging
from datetime import datetime
from typing import Dict, Tuple

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


# Maps suppression table name -> (db_key_field, dataframe_key_field)
# db_key_field is the column name in Postgres
# dataframe_key_field is the column name in the incoming dataframe
SUPPRESSION_TABLES: Dict[str, Tuple[str, str]] = {
    "privacy_opt_outs": ("email_address", "email_address"),
    "privacy_deletes": ("email_address", "email_address"),
    "fraud_watchlist": ("application_id", "application_id"),
}


class SuppressionEngine:
    """
    Applies multiple suppression checks to an incoming dataframe.

    Loads keys from each suppression table into in-memory sets for fast
    lookup, then flags any incoming records that match. Returns separate
    dataframes for included and excluded records.
    """

    def __init__(
        self,
        db_engine: Engine,
        suppression_tables: Dict[str, Tuple[str, str]] = None,
    ):
        self.engine = db_engine
        self.suppression_tables = suppression_tables or SUPPRESSION_TABLES

    def load_suppression_lists(self) -> Dict[str, set]:
        """
        Load all suppression keys from Postgres into memory.

        Returns:
            Dict mapping table_name -> set of suppression keys (uppercased)
        """
        suppressions = {}
        for table, (db_field, _) in self.suppression_tables.items():
            query = text(f"SELECT {db_field} FROM {table}")
            with self.engine.connect() as conn:
                result = conn.execute(query)
                keys = {str(row[0]).upper() for row in result if row[0] is not None}
            suppressions[table] = keys
            logger.info(f"Loaded {len(keys):,} keys from {table}")
        return suppressions

    def apply_suppressions(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply all suppression checks and split the dataframe.

        Args:
            df: Incoming records (already passed reject rules)

        Returns:
            (included_df, excluded_df) - excluded_df has a 'suppression_source' column
        """
        if df.empty:
            logger.warning("Empty dataframe passed to suppression engine")
            return df.copy(), df.copy()

        df = df.copy()
        df["suppression_source"] = None

        suppressions = self.load_suppression_lists()

        for table, (_, df_field) in self.suppression_tables.items():
            if df_field not in df.columns:
                logger.warning(
                    f"Field '{df_field}' not in dataframe, skipping suppression for {table}"
                )
                continue

            supp_set = suppressions[table]
            if not supp_set:
                continue

            # Case-insensitive match
            field_upper = df[df_field].astype(str).str.upper()
            mask = field_upper.isin(supp_set) & df["suppression_source"].isna()
            df.loc[mask, "suppression_source"] = table

        included = df[df["suppression_source"].isna()].drop(
            columns=["suppression_source"]
        ).copy()
        excluded = df[df["suppression_source"].notna()].copy()

        suppression_rate = len(excluded) / len(df) if len(df) > 0 else 0
        logger.info(
            f"Suppression engine processed {len(df):,} records: "
            f"{len(included):,} included, {len(excluded):,} excluded "
            f"({suppression_rate:.2%})"
        )

        return included, excluded

    def log_excluded_to_db(
        self,
        excluded_df: pd.DataFrame,
        pipeline_run_id: str,
    ) -> int:
        """
        Write excluded records to the suppression_exclusions audit table.

        Returns:
            Number of rows written
        """
        if excluded_df.empty:
            return 0

        rows_to_insert = []
        for _, row in excluded_df.iterrows():
            rows_to_insert.append({
                "pipeline_run_id": pipeline_run_id,
                "application_id": row.get("application_id"),
                "email_address": row.get("email_address"),
                "suppression_source": row["suppression_source"],
            })

        insert_sql = text("""
            INSERT INTO suppression_exclusions
                (pipeline_run_id, application_id, email_address, suppression_source)
            VALUES
                (:pipeline_run_id, :application_id, :email_address, :suppression_source)
        """)

        with self.engine.begin() as conn:
            conn.execute(insert_sql, rows_to_insert)

        logger.info(f"Logged {len(rows_to_insert):,} suppressed records to audit table")
        return len(rows_to_insert)
