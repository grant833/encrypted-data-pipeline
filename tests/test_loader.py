"""Tests for the warehouse loader."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pipeline.loader import COLUMN_MAPPING, load_to_postgres


@pytest.fixture
def sample_df():
    """A small dataframe representing identity-resolved records."""
    return pd.DataFrame([
        {
            "first_name": "Grant", "middle_initial": "B", "last_name": "Shimer",
            "street_address": "123 Main St", "city": "Atlanta", "state": "GA",
            "zip_code": "30309", "application_id": "APP-001",
            "customer_id": "CUST-001", "identity_id": 1, "division_id": "500",
            "submitted_date": "2026-01-01", "application_status": "approved",
            "email_address": "grant@test.com", "date_of_birth": "2005-04-30",
        },
        {
            "first_name": "Jane", "middle_initial": "A", "last_name": "Doe",
            "street_address": "456 Oak Ave", "city": "Atlanta", "state": "GA",
            "zip_code": "30309", "application_id": "APP-002",
            "customer_id": "CUST-002", "identity_id": 2, "division_id": "500",
            "submitted_date": "2026-01-02", "application_status": "declined",
            "email_address": "jane@test.com", "date_of_birth": "1990-06-15",
        },
    ])


def test_empty_dataframe_returns_zero():
    """Loading an empty dataframe should return 0 without crashing."""
    df = pd.DataFrame()
    fake_engine = MagicMock()
    result = load_to_postgres(df, "RUN-TEST", fake_engine)
    assert result == 0


def test_returns_correct_row_count(sample_df):
    """load_to_postgres should return the number of rows it loaded."""
    fake_engine = MagicMock()
    fake_engine.begin.return_value.__enter__ = MagicMock(return_value=MagicMock())
    fake_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    with patch("pipeline.loader.Table") as mock_table_class:
        mock_table_class.return_value = MagicMock()
        result = load_to_postgres(sample_df, "RUN-TEST", fake_engine)

    assert result == 2


def test_missing_columns_raises(sample_df):
    """A dataframe with no matching columns should raise ValueError."""
    df = pd.DataFrame([{"unrelated_field": "value"}])
    fake_engine = MagicMock()
    with pytest.raises(ValueError, match="No matching columns"):
        load_to_postgres(df, "RUN-TEST", fake_engine)


def test_pipeline_run_id_added_to_records(sample_df):
    """Every loaded record should be tagged with pipeline_run_id and source_system."""
    fake_engine = MagicMock()
    mock_conn = MagicMock()
    fake_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    fake_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    with patch("pipeline.loader.Table") as mock_table_class:
        mock_table_class.return_value = MagicMock()
        load_to_postgres(sample_df, "RUN-ABC123", fake_engine)

    # The execute call should have received records with pipeline_run_id
    assert mock_conn.execute.called
    call_args = mock_conn.execute.call_args
    records = call_args[0][1]  # second positional arg is the list of dicts
    for record in records:
        assert record["pipeline_run_id"] == "RUN-ABC123"
        assert record["source_system"] == "NORTHSTAR_FINANCIAL"


def test_column_mapping_preserves_all_application_fields():
    """The column mapping should cover every field from the source data."""
    expected_fields = {
        "first_name", "middle_initial", "last_name", "street_address",
        "city", "state", "zip_code", "application_id", "customer_id",
        "identity_id", "division_id", "submitted_date", "application_status",
        "email_address", "date_of_birth",
    }
    assert set(COLUMN_MAPPING.keys()) == expected_fields


def test_chunksize_creates_multiple_inserts():
    """Large dataframes should be inserted in multiple chunks."""
    # Build a 12-row dataframe with all required columns
    rows = []
    for i in range(12):
        rows.append({col: f"val{i}" for col in COLUMN_MAPPING.keys()})
    df = pd.DataFrame(rows)

    fake_engine = MagicMock()
    mock_conn = MagicMock()
    fake_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    fake_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    with patch("pipeline.loader.Table") as mock_table_class:
        mock_table_class.return_value = MagicMock()
        # chunksize=5 means 12 rows should produce 3 inserts (5+5+2)
        load_to_postgres(df, "RUN-TEST", fake_engine, chunksize=5)

    assert mock_conn.execute.call_count == 3
