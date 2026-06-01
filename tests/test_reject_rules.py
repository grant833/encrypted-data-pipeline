"""Tests for the reject rules engine."""

import pandas as pd
import pytest

from pipeline.reject_rules import (
    PreProcessRejectEngine,
    RejectRule,
    RejectThresholdExceededError,
)


@pytest.fixture
def sample_df():
    """A small dataframe with known good and bad records."""
    return pd.DataFrame(
        [
            {
                "application_id": "APP-001",
                "state": "GA",
                "application_status": "approved",
                "email_address": "ok@test.com",
                "zip_code": "30309",
            },
            {
                "application_id": "",
                "state": "GA",
                "application_status": "approved",
                "email_address": "missing@test.com",
                "zip_code": "30309",
            },
            {
                "application_id": "APP-002",
                "state": "GEORGIA",
                "application_status": "approved",
                "email_address": "ok@test.com",
                "zip_code": "30309",
            },
            {
                "application_id": "APP-003",
                "state": "GA",
                "application_status": "INVALID",
                "email_address": "ok@test.com",
                "zip_code": "30309",
            },
            {
                "application_id": "APP-004",
                "state": "GA",
                "application_status": "approved",
                "email_address": "ok@test.com",
                "zip_code": "ABCDE",
            },
        ]
    )


def test_required_field_rejects_nulls(sample_df):
    """A required field rule should reject empty strings."""
    engine = PreProcessRejectEngine(
        [RejectRule("application_id", "required", None, "ID required")],
        reject_threshold=1.0,
    )
    passed, rejected = engine.apply_rules(sample_df)
    assert len(rejected) == 1
    assert rejected.iloc[0]["reject_reason"] == "ID required"


def test_max_length_rejects_oversize(sample_df):
    """A max_length rule should reject values longer than limit."""
    engine = PreProcessRejectEngine(
        [RejectRule("state", "max_length", 2, "state too long")],
        reject_threshold=1.0,
    )
    passed, rejected = engine.apply_rules(sample_df)
    assert len(rejected) == 1
    assert rejected.iloc[0]["state"] == "GEORGIA"


def test_valid_values_rejects_invalid(sample_df):
    """A valid_values rule should reject out-of-set values."""
    engine = PreProcessRejectEngine(
        [
            RejectRule(
                "application_status",
                "valid_values",
                ["approved", "declined", "under_review"],
                "bad status",
            )
        ],
        reject_threshold=1.0,
    )
    passed, rejected = engine.apply_rules(sample_df)
    assert len(rejected) == 1
    assert rejected.iloc[0]["application_status"] == "INVALID"


def test_format_rejects_bad_pattern(sample_df):
    """A format rule should reject values that fail the regex."""
    engine = PreProcessRejectEngine(
        [RejectRule("zip_code", "format", r"^\d{5}$", "zip must be 5 digits")],
        reject_threshold=1.0,
    )
    passed, rejected = engine.apply_rules(sample_df)
    assert len(rejected) == 1
    assert rejected.iloc[0]["zip_code"] == "ABCDE"


def test_multiple_rules_catch_all_bad_records(sample_df):
    """Running multiple rules should catch every bad record."""
    rules = [
        RejectRule("application_id", "required", None, "ID required"),
        RejectRule("state", "max_length", 2, "state too long"),
        RejectRule(
            "application_status",
            "valid_values",
            ["approved", "declined", "under_review"],
            "bad status",
        ),
        RejectRule("zip_code", "format", r"^\d{5}$", "bad zip"),
    ]
    engine = PreProcessRejectEngine(rules, reject_threshold=1.0)
    passed, rejected = engine.apply_rules(sample_df)
    assert len(passed) == 1
    assert len(rejected) == 4


def test_threshold_exceeded_raises():
    """If reject rate exceeds threshold, the engine should raise."""
    df = pd.DataFrame(
        [
            {"application_id": ""},
            {"application_id": ""},
            {"application_id": "APP-001"},
        ]
    )
    engine = PreProcessRejectEngine(
        [RejectRule("application_id", "required", None, "ID required")],
        reject_threshold=0.10,
    )
    with pytest.raises(RejectThresholdExceededError):
        engine.apply_rules(df)


def test_empty_dataframe_returns_empty():
    """An empty dataframe should return two empty dataframes."""
    df = pd.DataFrame(columns=["application_id"])
    engine = PreProcessRejectEngine(
        [RejectRule("application_id", "required", None, "ID required")],
    )
    passed, rejected = engine.apply_rules(df)
    assert len(passed) == 0
    assert len(rejected) == 0


def test_missing_field_skips_rule(sample_df):
    """A rule on a field not in the dataframe should be skipped, not crash."""
    engine = PreProcessRejectEngine(
        [RejectRule("nonexistent_field", "required", None, "missing field")],
        reject_threshold=1.0,
    )
    passed, rejected = engine.apply_rules(sample_df)
    assert len(passed) == 5
    assert len(rejected) == 0


def test_record_only_flagged_by_first_failing_rule(sample_df):
    """A record failing multiple rules should be flagged by the first failure only."""
    rules = [
        RejectRule("application_id", "required", None, "ID required"),
        RejectRule(
            "application_status",
            "valid_values",
            ["approved", "declined", "under_review"],
            "bad status",
        ),
    ]
    # Modify one record to fail BOTH rules
    df = sample_df.copy()
    df.at[1, "application_status"] = "INVALID"  # row 1 already has empty application_id

    engine = PreProcessRejectEngine(rules, reject_threshold=1.0)
    passed, rejected = engine.apply_rules(df)

    # The row with both empty ID and invalid status should be flagged by the first rule
    flagged_for_id = rejected[rejected["reject_reason"] == "ID required"]
    assert len(flagged_for_id) == 1
