"""Tests for the suppression engine."""

import pandas as pd
import pytest

# from pipeline.suppression_engine import SuppressionEngine


def test_email_suppression_matches():
    """A record with an email in the CCPA list should be suppressed."""
    # TODO: Pre-load mock suppression list with 'test@test.com'
    # TODO: Pass df with that email, assert included.empty and excluded has 1 row
    pass


def test_case_insensitive_matching():
    """Email matching should be case insensitive."""
    # TODO: Suppression list has 'TEST@TEST.COM', input has 'test@test.com'
    # TODO: Assert match still works
    pass


def test_no_match_passes_through():
    """Records with no suppression match should pass through unmodified."""
    # TODO: Empty suppression lists, input df has 100 records
    # TODO: Assert included has 100 rows, excluded is empty
    pass


def test_application_id_suppression():
    """A record with an app_id in credit_abusers should be suppressed."""
    # TODO: Pre-load credit_abusers with 'APP-FRAUD-001'
    # TODO: Pass df with that app_id, assert excluded has 1 row
    pass
