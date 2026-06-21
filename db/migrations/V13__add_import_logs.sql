-- V13: Add import logs for data lineage and audit trail
-- Purpose: Track all data imports (CLI, CSV, web form) to debug duplicates, find error sources, and maintain data quality audit

CREATE TABLE import_logs (
    import_id BIGSERIAL PRIMARY KEY,
    import_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    import_method VARCHAR(50) NOT NULL, -- 'CLI', 'CSV', 'WEB_FORM'
    file_name VARCHAR(500),
    record_count INTEGER,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    status VARCHAR(50) NOT NULL, -- 'SUCCESS', 'PARTIAL', 'FAILED'
    error_message TEXT,
    execution_time_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX import_logs_date_status_idx ON import_logs(import_date DESC, status);
CREATE INDEX import_logs_method_idx ON import_logs(import_method);

-- View for recent import summary
CREATE VIEW v_import_summary AS
SELECT 
    import_id,
    import_date,
    import_method,
    file_name,
    record_count,
    success_count,
    error_count,
    status,
    CASE 
        WHEN record_count > 0 THEN ROUND(100.0 * success_count / record_count, 1)
        ELSE 0
    END as success_rate_pct,
    execution_time_seconds
FROM import_logs
ORDER BY import_date DESC;

COMMENT ON TABLE import_logs IS 'Audit trail for all data imports; tracks success/failure for debugging and data quality audits';
COMMENT ON COLUMN import_logs.import_method IS 'Source of import: CLI (manual), CSV (bulk), WEB_FORM (web interface)';
COMMENT ON VIEW v_import_summary IS 'Recent imports with success rates for operational monitoring';
