"""Tests for the audit layer."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pipeline.audit import (
    AUDIT_QUERIES,
    check_volume_anomaly,
    run_audit_queries,
    write_audit_log,
)


def test_audit_queries_dict_has_expected_keys():
    """The audit query catalog should include all critical metrics."""
    expected_keys = {
        "total_loaded",
        "status_breakdown",
        "identity_match_rate",
        "suppression_summary",
        "reject_breakdown",
        "state_distribution",
    }
    assert expected_keys.issubset(set(AUDIT_QUERIES.keys()))


def test_audit_queries_are_parameterized():
    """Every audit query that filters by run should use the :run_id parameter."""
    queries_using_run_id = [
        "total_loaded", "status_breakdown", "identity_match_rate",
        "suppression_summary", "reject_breakdown", "state_distribution",
    ]
    for key in queries_using_run_id:
        assert ":run_id" in AUDIT_QUERIES[key], \
            f"Query '{key}' should use :run_id parameter to prevent SQL injection"


def test_write_audit_log_calls_execute():
    """write_audit_log should issue an INSERT to the database."""
    fake_engine = MagicMock()
    mock_conn = MagicMock()
    fake_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    fake_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    write_audit_log(
        pipeline_run_id="RUN-TEST",
        feed_name="customer_applications",
        stage="load",
        record_count=1000,
        engine=fake_engine,
        rejected_count=50,
        suppressed_count=10,
        runtime_seconds=5.5,
    )

    assert mock_conn.execute.called
    params = mock_conn.execute.call_args[0][1]
    assert params["pipeline_run_id"] == "RUN-TEST"
    assert params["stage"] == "load"
    assert params["record_count"] == 1000
    assert params["rejected_count"] == 50
    assert params["status"] == "SUCCESS"


def test_write_audit_log_supports_failure_status():
    """write_audit_log should allow logging failures with error message."""
    fake_engine = MagicMock()
    mock_conn = MagicMock()
    fake_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    fake_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    write_audit_log(
        pipeline_run_id="RUN-TEST",
        feed_name="customer_applications",
        stage="load",
        record_count=0,
        engine=fake_engine,
        status="FAILED",
        error_message="Database connection lost",
    )

    params = mock_conn.execute.call_args[0][1]
    assert params["status"] == "FAILED"
    assert params["error_message"] == "Database connection lost"


def test_volume_anomaly_no_baseline_returns_safe_default():
    """With no historical data, volume check should return non-anomalous."""
    fake_engine = MagicMock()
    mock_conn = MagicMock()
    fake_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    fake_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchone.return_value = (None,)

    result = check_volume_anomaly("customer_applications", 50000, fake_engine)

    assert result["is_anomalous"] is False
    assert result["baseline_avg"] == 0.0
    assert "No baseline" in result.get("note", "")


def test_volume_anomaly_detects_drop():
    """A 50% drop from baseline should flag as anomalous."""
    fake_engine = MagicMock()
    mock_conn = MagicMock()
    fake_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    fake_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchone.return_value = (100000,)

    result = check_volume_anomaly(
        "customer_applications", 50000, fake_engine, threshold_pct=0.40,
    )

    assert result["is_anomalous"] is True
    assert result["pct_variance"] == -50.0
    assert result["baseline_avg"] == 100000


def test_volume_anomaly_normal_volume_is_not_flagged():
    """Volume within threshold should not be flagged."""
    fake_engine = MagicMock()
    mock_conn = MagicMock()
    fake_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    fake_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchone.return_value = (50000,)

    # 10% above baseline — within 40% threshold
    result = check_volume_anomaly(
        "customer_applications", 55000, fake_engine, threshold_pct=0.40,
    )

    assert result["is_anomalous"] is False


def test_run_audit_queries_returns_dict_of_dataframes():
    """run_audit_queries should return a DataFrame for each query."""
    fake_engine = MagicMock()
    mock_conn = MagicMock()
    fake_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    fake_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    # Return an empty result for every query
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_result.keys.return_value = ["col1", "col2"]
    mock_conn.execute.return_value = mock_result

    results = run_audit_queries("RUN-TEST", fake_engine)

    assert isinstance(results, dict)
    for query_name in AUDIT_QUERIES.keys():
        assert query_name in results
        assert isinstance(results[query_name], pd.DataFrame)
