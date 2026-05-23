"""Tests for the suppression engine."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pipeline.suppression_engine import SuppressionEngine


class FakeEngine:
    """Minimal SQLAlchemy engine stand-in for unit tests.

    Returns predefined suppression keys when queried, so tests don't need
    a real Postgres connection.
    """

    def __init__(self, table_results):
        self.table_results = table_results

    def connect(self):
        return _FakeConnection(self.table_results)

    def begin(self):
        return _FakeTransaction()


class _FakeConnection:
    def __init__(self, table_results):
        self.table_results = table_results

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query):
        # Pull out the table name from "SELECT field FROM table"
        sql = str(query).strip()
        table = sql.split("FROM")[-1].strip().rstrip(";")
        rows = self.table_results.get(table, [])
        return [(r,) for r in rows]


class _FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, rows):
        return None


@pytest.fixture
def sample_df():
    """A small dataframe with known suppression-matching and non-matching records."""
    return pd.DataFrame([
        {"application_id": "APP-001", "email_address": "clean@example.com"},
        {"application_id": "APP-002", "email_address": "opted-out@example.com"},
        {"application_id": "APP-003", "email_address": "another-clean@example.com"},
        {"application_id": "APP-FRAUD-001", "email_address": "fraud@example.com"},
    ])


def test_email_suppression_matches(sample_df):
    """Records with emails in the privacy_opt_outs list should be excluded."""
    fake = FakeEngine({
        "privacy_opt_outs": ["opted-out@example.com"],
        "privacy_deletes": [],
        "fraud_watchlist": [],
    })
    engine = SuppressionEngine(fake)
    included, excluded = engine.apply_suppressions(sample_df)

    assert len(included) == 3
    assert len(excluded) == 1
    assert excluded.iloc[0]["email_address"] == "opted-out@example.com"
    assert excluded.iloc[0]["suppression_source"] == "privacy_opt_outs"


def test_case_insensitive_matching(sample_df):
    """Email matching should be case-insensitive."""
    fake = FakeEngine({
        "privacy_opt_outs": ["OPTED-OUT@EXAMPLE.COM"],
        "privacy_deletes": [],
        "fraud_watchlist": [],
    })
    engine = SuppressionEngine(fake)
    included, excluded = engine.apply_suppressions(sample_df)

    assert len(excluded) == 1


def test_no_match_passes_through(sample_df):
    """All records should pass through if no suppression matches."""
    fake = FakeEngine({
        "privacy_opt_outs": [],
        "privacy_deletes": [],
        "fraud_watchlist": [],
    })
    engine = SuppressionEngine(fake)
    included, excluded = engine.apply_suppressions(sample_df)

    assert len(included) == 4
    assert len(excluded) == 0


def test_application_id_fraud_suppression(sample_df):
    """Records with application_id in fraud_watchlist should be excluded."""
    fake = FakeEngine({
        "privacy_opt_outs": [],
        "privacy_deletes": [],
        "fraud_watchlist": ["APP-FRAUD-001"],
    })
    engine = SuppressionEngine(fake)
    included, excluded = engine.apply_suppressions(sample_df)

    assert len(included) == 3
    assert len(excluded) == 1
    assert excluded.iloc[0]["application_id"] == "APP-FRAUD-001"
    assert excluded.iloc[0]["suppression_source"] == "fraud_watchlist"


def test_multiple_sources_catch_different_records(sample_df):
    """Records matching different suppression sources should all be excluded."""
    fake = FakeEngine({
        "privacy_opt_outs": ["opted-out@example.com"],
        "privacy_deletes": [],
        "fraud_watchlist": ["APP-FRAUD-001"],
    })
    engine = SuppressionEngine(fake)
    included, excluded = engine.apply_suppressions(sample_df)

    assert len(included) == 2
    assert len(excluded) == 2
    sources = set(excluded["suppression_source"].tolist())
    assert sources == {"privacy_opt_outs", "fraud_watchlist"}


def test_empty_dataframe_returns_empty():
    """An empty dataframe should return two empty dataframes."""
    df = pd.DataFrame(columns=["application_id", "email_address"])
    fake = FakeEngine({
        "privacy_opt_outs": ["whatever@example.com"],
        "privacy_deletes": [],
        "fraud_watchlist": [],
    })
    engine = SuppressionEngine(fake)
    included, excluded = engine.apply_suppressions(df)

    assert len(included) == 0
    assert len(excluded) == 0


def test_missing_field_skips_suppression(sample_df):
    """If a dataframe lacks a key field, that suppression source should be skipped."""
    # Drop the email_address column so the email-based suppressions can't run
    df = sample_df.drop(columns=["email_address"])
    fake = FakeEngine({
        "privacy_opt_outs": ["opted-out@example.com"],
        "privacy_deletes": [],
        "fraud_watchlist": ["APP-FRAUD-001"],
    })
    engine = SuppressionEngine(fake)
    included, excluded = engine.apply_suppressions(df)

    # Only the fraud_watchlist suppression should fire
    assert len(excluded) == 1
    assert excluded.iloc[0]["suppression_source"] == "fraud_watchlist"


def test_record_only_flagged_by_first_matching_source():
    """A record matching multiple suppression sources should be flagged by first only."""
    df = pd.DataFrame([
        {"application_id": "APP-001", "email_address": "both@example.com"},
    ])
    fake = FakeEngine({
        "privacy_opt_outs": ["both@example.com"],
        "privacy_deletes": ["both@example.com"],
        "fraud_watchlist": [],
    })
    engine = SuppressionEngine(fake)
    included, excluded = engine.apply_suppressions(df)

    assert len(excluded) == 1
    # First source listed wins
    assert excluded.iloc[0]["suppression_source"] == "privacy_opt_outs"
