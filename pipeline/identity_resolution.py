"""
Identity resolution layer.

For every incoming record, either match it to an existing identity in the
identities table or create a new identity. Uses hash-based exact matching
on normalized fields (name + address + date of birth).
"""

import hashlib
import logging
import re

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def normalize_field(value) -> str:
    """
    Normalize a field value for matching.

    Lowercase, strip whitespace, remove all non-alphanumeric characters.
    Returns empty string for null/None values.

    Examples:
        "Grant Shimer"    -> "grantshimer"
        "  123 Main St."  -> "123mainst"
        "30309"           -> "30309"
        None              -> ""
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"[^a-z0-9]", "", str(value).lower().strip())


def compute_identity_hash(record) -> str:
    """
    Compute a deterministic SHA-256 hash of normalized identity fields.

    Uses: first_name + last_name + street_address + zip_code + year_of_birth

    Two records with the same hash are treated as the same person.
    """
    year_of_birth = ""
    dob = record.get("date_of_birth", "")
    if dob and isinstance(dob, str) and len(dob) >= 4:
        year_of_birth = dob[:4]

    components = [
        normalize_field(record.get("first_name", "")),
        normalize_field(record.get("last_name", "")),
        normalize_field(record.get("street_address", "")),
        normalize_field(record.get("zip_code", "")),
        normalize_field(year_of_birth),
    ]
    fingerprint = "|".join(components)
    return hashlib.sha256(fingerprint.encode()).hexdigest()


class IdentityResolver:
    """
    Resolves incoming records to existing identities or creates new ones.

    For each incoming record:
        1. Compute identity_hash
        2. Look up in identities table by hash
        3. If match: attach existing identity_id
        4. If no match: insert new identity, attach new identity_id
    """

    def __init__(self, db_engine: Engine):
        self.engine = db_engine

    def resolve_identities(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Attach identity_id to every record in the dataframe.

        Args:
            df: Clean records ready for identity resolution

        Returns:
            df with identity_id column populated
        """
        if df.empty:
            df = df.copy()
            df["identity_id"] = []
            return df

        df = df.copy()

        # Compute identity hash for every record
        df["identity_hash"] = df.apply(compute_identity_hash, axis=1)

        # Look up all hashes in the identities table in a single query
        unique_hashes = df["identity_hash"].unique().tolist()
        existing_map = self._lookup_existing_identities(unique_hashes)

        # Identify hashes that need new identity records
        new_hashes = [h for h in unique_hashes if h not in existing_map]
        new_identity_records = []
        for h in new_hashes:
            # Take the first row matching this hash and use it to seed the identity
            first_row = df[df["identity_hash"] == h].iloc[0]
            new_identity_records.append(self._build_identity_record(first_row, h))

        # Insert new identities and get their IDs
        if new_identity_records:
            new_id_map = self._insert_new_identities(new_identity_records)
            existing_map.update(new_id_map)

        # Map identity_id back onto every row
        df["identity_id"] = df["identity_hash"].map(existing_map)

        # Drop the hash column - it was just for joining
        df = df.drop(columns=["identity_hash"])

        match_count = len(unique_hashes) - len(new_hashes)
        match_rate = match_count / len(unique_hashes) if unique_hashes else 0
        logger.info(
            f"Identity resolution: {len(df):,} records resolved across "
            f"{len(unique_hashes):,} unique identities "
            f"({match_count:,} existing matched, {len(new_hashes):,} new created, "
            f"{match_rate:.2%} match rate)"
        )

        return df

    def _lookup_existing_identities(self, hashes: list) -> dict:
        """Query identities table for existing matches. Returns hash -> identity_id."""
        if not hashes:
            return {}
        query = text("""
            SELECT identity_hash, identity_id
            FROM identities
            WHERE identity_hash = ANY(:hashes)
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"hashes": hashes})
            return {row[0]: row[1] for row in result}

    def _build_identity_record(self, record, identity_hash: str) -> dict:
        """Build a row dict for inserting into the identities table."""
        dob = record.get("date_of_birth", "")
        year_of_birth = dob[:4] if dob and isinstance(dob, str) and len(dob) >= 4 else None

        return {
            "identity_hash": identity_hash,
            "source_system": "NORTHSTAR_FINANCIAL",
            "first_name": record.get("first_name"),
            "last_name": record.get("last_name"),
            "street_address": record.get("street_address"),
            "city": record.get("city"),
            "state": record.get("state"),
            "zip_code": record.get("zip_code"),
            "email_address": record.get("email_address"),
            "year_of_birth": year_of_birth,
        }

    def _insert_new_identities(self, records: list) -> dict:
        """
        Insert new identity rows. Returns hash -> identity_id for the new rows.

        Uses INSERT ... RETURNING to get the auto-generated identity_id back.
        """
        insert_sql = text("""
            INSERT INTO identities
                (identity_hash, source_system, first_name, last_name,
                 street_address, city, state, zip_code, email_address, year_of_birth)
            VALUES
                (:identity_hash, :source_system, :first_name, :last_name,
                 :street_address, :city, :state, :zip_code, :email_address, :year_of_birth)
            ON CONFLICT (identity_hash) DO UPDATE SET
                last_seen_timestamp = CURRENT_TIMESTAMP
            RETURNING identity_hash, identity_id
        """)

        result_map = {}
        with self.engine.begin() as conn:
            for record in records:
                result = conn.execute(insert_sql, record)
                row = result.fetchone()
                if row:
                    result_map[row[0]] = row[1]
        return result_map
