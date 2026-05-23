"""Tests for the reject rules engine."""

import pandas as pd
import pytest

# from pipeline.reject_rules import PreProcessRejectEngine, RejectRule


@pytest.fixture
def sample_df():
    """A small dataframe with known good and bad records."""
    return pd.DataFrame([
        {"Application_ID": "APP-001", "State": "GA", "App_Status_Flag": "A", "email_addr": "ok@test.com"},
        {"Application_ID": "",        "State": "GA", "App_Status_Flag": "A", "email_addr": "missing@test.com"},  # bad: missing ID
        {"Application_ID": "APP-002", "State": "GEORGIA", "App_Status_Flag": "A", "email_addr": "ok@test.com"},  # bad: state too long
        {"Application_ID": "APP-003", "State": "GA", "App_Status_Flag": "X", "email_addr": "ok@test.com"},  # bad: invalid flag
    ])


def test_required_field_rejects_nulls(sample_df):
    """A required field rule should reject empty values."""
    # TODO: Build engine with [RejectRule('Application_ID', 'required')]
    # TODO: Apply rules, assert 1 record rejected
    pass


def test_max_length_rejects_oversize(sample_df):
    """A max_length rule should reject values longer than limit."""
    # TODO: Build engine with [RejectRule('State', 'max_length', 2)]
    # TODO: Apply rules, assert 1 record rejected
    pass


def test_valid_values_rejects_invalid(sample_df):
    """A valid_values rule should reject out-of-set values."""
    # TODO: Build engine with [RejectRule('App_Status_Flag', 'valid_values', ['A','D','U'])]
    # TODO: Apply rules, assert 1 record rejected
    pass


def test_threshold_exceeded_raises():
    """If reject rate exceeds threshold, the engine should raise."""
    # TODO: Build engine with reject_threshold=0.01
    # TODO: Pass df with 50% bad records, expect Exception
    pass
