-- ============================================================================
-- Audit Queries
-- ============================================================================
-- These queries run after every pipeline execution to verify counts and
-- surface anomalies. They are loaded from pipeline/audit.py at runtime.
-- ============================================================================


-- Total records loaded for a given run
SELECT COUNT(*) AS count
FROM wh_cl_application
WHERE data_collection_id = :run_id;


-- Status breakdown — Approved / Declined / Under-review
SELECT app_status_flag, COUNT(*) AS count
FROM wh_cl_application
WHERE data_collection_id = :run_id
GROUP BY app_status_flag
ORDER BY count DESC;


-- Identity match rate — what % of incoming records matched existing identities
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN indiv_id IS NOT NULL THEN 1 ELSE 0 END) AS matched,
    ROUND(SUM(CASE WHEN indiv_id IS NOT NULL THEN 1 ELSE 0 END)
          * 100.0 / NULLIF(COUNT(*), 0), 2) AS match_rate_pct
FROM wh_cl_application
WHERE data_collection_id = :run_id;


-- Suppression summary by source
SELECT suppression_source, COUNT(*) AS suppressed_count
FROM suppression_exclusions
WHERE pipeline_run_id = :run_id
GROUP BY suppression_source
ORDER BY suppressed_count DESC;


-- Reject breakdown by reason
SELECT reject_reason, COUNT(*) AS reject_count
FROM rejected_records
WHERE pipeline_run_id = :run_id
GROUP BY reject_reason
ORDER BY reject_count DESC;


-- Volume vs 30-day baseline — flag if today is >40% off average
WITH today AS (
    SELECT COUNT(*) AS today_count
    FROM wh_cl_application
    WHERE data_collection_id = :run_id
),
baseline AS (
    SELECT AVG(record_count) AS baseline_avg
    FROM pipeline_audit_log
    WHERE feed_name = 'APPLICATION'
      AND stage = 'LOAD'
      AND run_timestamp >= NOW() - INTERVAL '30 days'
)
SELECT
    t.today_count,
    b.baseline_avg,
    ROUND(((t.today_count - b.baseline_avg) / NULLIF(b.baseline_avg, 0)) * 100, 2)
        AS pct_variance
FROM today t, baseline b;


-- Pipeline run history (last 20 runs)
SELECT pipeline_run_id, feed_name, stage, record_count,
       rejected_count, suppressed_count, status, run_timestamp
FROM pipeline_audit_log
ORDER BY run_timestamp DESC
LIMIT 20;
