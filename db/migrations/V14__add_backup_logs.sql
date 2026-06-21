-- V14: Add backup logs for operational health and email alerts
-- Purpose: Track every S3 backup attempt to detect failures, monitor freshness, and enable email alerts

CREATE TABLE backup_logs (
    backup_id BIGSERIAL PRIMARY KEY,
    backup_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    s3_key VARCHAR(500),
    file_size_bytes BIGINT,
    status VARCHAR(50) NOT NULL, -- 'SUCCESS', 'FAILED', 'PARTIAL'
    error_message TEXT,
    execution_time_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX backup_logs_date_status_idx ON backup_logs(backup_date DESC, status);
CREATE INDEX backup_logs_status_idx ON backup_logs(status) WHERE status != 'SUCCESS';

-- View for health check and alerting
CREATE VIEW v_backup_status AS
SELECT 
    backup_id,
    backup_date,
    status,
    file_size_bytes,
    execution_time_seconds,
    NOW() - backup_date as time_since_backup,
    EXTRACT(HOURS FROM (NOW() - backup_date)) as hours_since_backup,
    CASE 
        WHEN status = 'SUCCESS' AND (NOW() - backup_date) < INTERVAL '25 hours' THEN 'HEALTHY'
        WHEN status = 'SUCCESS' AND (NOW() - backup_date) >= INTERVAL '25 hours' THEN 'STALE'
        ELSE 'FAILED'
    END as health_status
FROM backup_logs
WHERE backup_date = (SELECT MAX(backup_date) FROM backup_logs);

-- View for alerting logic
CREATE VIEW v_backup_alerts AS
SELECT 
    'BACKUP_FAILED' as alert_type,
    backup_id,
    backup_date,
    error_message,
    'Email alert: Backup failed' as action
FROM backup_logs
WHERE status IN ('FAILED', 'PARTIAL')
  AND backup_date > NOW() - INTERVAL '24 hours'
UNION ALL
SELECT 
    'BACKUP_STALE' as alert_type,
    backup_id,
    backup_date,
    'No successful backup in past 25 hours' as error_message,
    'Email alert: Backup is stale' as action
FROM backup_logs
WHERE status = 'SUCCESS'
  AND backup_date = (SELECT MAX(backup_date) FROM backup_logs)
  AND backup_date < NOW() - INTERVAL '25 hours';

COMMENT ON TABLE backup_logs IS 'S3 backup execution log; critical for monitoring, alerting, and recovery operations';
COMMENT ON VIEW v_backup_status IS 'Current backup health status for monitoring dashboards; triggers email alerts if FAILED or STALE';
COMMENT ON VIEW v_backup_alerts IS 'Rows present = alert conditions detected (backup failure or staleness > 25 hours)';
