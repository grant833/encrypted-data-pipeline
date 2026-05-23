"""
Identity resolution layer.

For each incoming record, either matches it to an existing identity in
wh_identity or creates a new identity record. This is the hardest piece
of the pipeline conceptually — start with hash-based matching, add
probabilistic matching as a v2 enhancement.
"""

import hashlib
import logging
from typing import Optional, Tuple

import pandas as pd
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def normalize_field(value: str) -> str:
    """Lowercase, strip whitespace, remove punctuation for matching."""
    # TODO: Lowercase, strip, remove non-alphanumeric chars
    raise NotImplementedError


def compute_identity_hash(record: pd.Series) -> str:
    """
    Compute a deterministic hash of normalized identity fields.

    Combines first_name + last_name + str_addr + zip_cd + birth_date
    (or year_of_birth) into a single SHA-256 hash. Two records with the
    same hash are treated as the same person.
    """
    # TODO: Normalize each field, concatenate, hash with hashlib.sha256
    raise NotImplementedError


class IdentityResolver:
    """
    Resolves incoming records to existing identities or creates new ones.

    v1: Hash-based exact matching on normalized fields
    v2: Probabilistic matching with recordlinkage for fuzzy matches
    """

    def __init__(self, db_engine: Engine):
        self.engine = db_engine

    def resolve_identities(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        For each record in df, attach an indiv_id column.

        Args:
            df: Clean records ready for warehouse load

        Returns:
            df with indiv_id column populated (either existing or newly created)
        """
        # TODO: Compute source_hash for each row
        # TODO: Query wh_identity for existing matches by source_hash
        # TODO: For matches, attach existing indiv_id
        # TODO: For non-matches, insert new identity record and attach new indiv_id
        # TODO: Log match rate to audit log
        raise NotImplementedError

    def _find_existing_identity(self, source_hash: str) -> Optional[int]:
        """Look up indiv_id by source_hash. Returns None if no match."""
        # TODO: SELECT indiv_id FROM wh_identity WHERE source_hash = %s
        raise NotImplementedError

    def _create_new_identity(self, record: pd.Series) -> int:
        """Insert a new wh_identity row and return the generated indiv_id."""
        # TODO: INSERT INTO wh_identity, RETURNING indiv_id
        raise NotImplementedError
