-- ============================================================
-- Operational Monitoring Views
-- For data quality checks and system health monitoring.
-- ============================================================

-- View for data quality overview
CREATE OR REPLACE VIEW v_data_quality AS
SELECT
    'cards' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE deleted_at IS NULL) AS active_rows,
    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted_rows,
    COUNT(*) FILTER (WHERE sport IS NULL) AS null_sport_count,
    COUNT(*) FILTER (WHERE player_name IS NULL) AS null_player_count
FROM cards

UNION ALL

SELECT
    'inventory',
    COUNT(*),
    COUNT(*) FILTER (WHERE deleted_at IS NULL),
    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL),
    COUNT(*) FILTER (WHERE status IS NULL),
    COUNT(*) FILTER (WHERE card_id IS NULL)
FROM inventory

UNION ALL

SELECT
    'transactions',
    COUNT(*),
    COUNT(*) FILTER (WHERE deleted_at IS NULL),
    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL),
    COUNT(*) FILTER (WHERE transaction_type IS NULL),
    COUNT(*) FILTER (WHERE transaction_date IS NULL)
FROM transactions;


-- View for recent changes (audit trail)
CREATE OR REPLACE VIEW v_recent_changes AS
SELECT
    audit_id,
    table_name,
    operation,
    record_id,
    changed_by,
    changed_at,
    -- Show summary of what changed
    CASE 
        WHEN operation = 'INSERT' THEN 'Created'
        WHEN operation = 'UPDATE' THEN 'Updated'
        WHEN operation = 'DELETE' THEN 'Deleted'
    END AS action
FROM audit_log
ORDER BY changed_at DESC
LIMIT 100;


-- View for inventory gaps (incomplete records)
CREATE OR REPLACE VIEW v_inventory_gaps AS
SELECT
    i.inventory_id,
    c.card_id,
    c.sport,
    c.year,
    c.manufacturer,
    c.set_name,
    c.card_number,
    c.player_name,
    CASE WHEN i.is_graded = true AND i.grading_company IS NULL THEN 'Missing grading_company'
         WHEN i.is_graded = true AND i.grade IS NULL THEN 'Missing grade'
         WHEN i.comp_low IS NULL OR i.comp_avg IS NULL OR i.comp_high IS NULL THEN 'Missing comp prices'
         WHEN i.cost_basis IS NULL THEN 'Missing cost_basis'
    END AS gap_description,
    i.status
FROM inventory i
JOIN cards c ON c.card_id = i.card_id
WHERE i.deleted_at IS NULL
  AND (
    (i.is_graded = true AND (i.grading_company IS NULL OR i.grade IS NULL))
    OR (i.comp_low IS NULL OR i.comp_avg IS NULL OR i.comp_high IS NULL)
    OR i.cost_basis IS NULL
  );


-- ============================================================
-- Performance Indexes for Read Workloads
-- ============================================================

-- For PowerBI filtering by status and card_id
CREATE INDEX IF NOT EXISTS inventory_status_card_id_idx ON inventory (status, card_id)
WHERE deleted_at IS NULL;

-- For transaction reporting
CREATE INDEX IF NOT EXISTS transaction_items_direction_idx ON transaction_items (direction);

-- For audit log queries (most common: recent changes)
CREATE INDEX IF NOT EXISTS audit_log_table_operation_changed_at_idx 
ON audit_log (table_name, operation, changed_at DESC);

-- For inventory card queries by sport/year (PowerBI)
CREATE INDEX IF NOT EXISTS cards_sport_year_idx ON cards (sport, year)
WHERE deleted_at IS NULL;

-- For inventory comp price queries
CREATE INDEX IF NOT EXISTS inventory_comp_avg_idx ON inventory (comp_avg)
WHERE deleted_at IS NULL AND status = 'OWNED';
