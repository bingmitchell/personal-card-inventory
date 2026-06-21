-- ============================================================
-- v_inventory_detail
-- Flat view joining inventory to cards — the main view for BI
-- dashboards and the mobile app. Filters to currently owned cards
-- but can be queried without the status filter for full history.
-- ============================================================
CREATE VIEW v_inventory_detail AS
SELECT
    i.inventory_id,
    i.status,
    i.acquisition_date,
    i.location,

    -- Card identity
    c.card_id,
    c.sport,
    c.year,
    c.manufacturer,
    c.set_name,
    c.insert_name,
    c.card_number,
    c.player_name,
    c.team,

    -- Variant flags
    c.is_base,
    c.parallel_name,
    c.is_auto,
    c.is_relic,
    c.is_patch,
    c.is_rookie,
    c.is_numbered,
    c.print_run,

    -- Grading
    i.is_graded,
    i.grading_company,
    i.grade,
    i.grade_qualifier,
    i.cert_number,

    -- Financials
    i.cost_basis,
    i.comp_low,
    i.comp_avg,
    i.comp_high,
    i.comp_updated_at,

    -- Derived: estimated gain/loss vs average comp
    CASE
        WHEN i.comp_avg IS NOT NULL AND i.cost_basis IS NOT NULL
        THEN i.comp_avg - i.cost_basis
    END AS unrealized_gain_avg,

    i.notes AS inventory_notes,
    c.notes AS card_notes
FROM inventory i
JOIN cards c ON c.card_id = i.card_id;


-- ============================================================
-- v_portfolio_summary
-- One row per owned card with current value snapshot.
-- Good for the "what is my collection worth" dashboard tile.
-- ============================================================
CREATE VIEW v_portfolio_summary AS
SELECT
    sport,
    player_name,
    COUNT(*)                        AS card_count,
    SUM(cost_basis)                 AS total_cost,
    SUM(comp_avg)                   AS total_comp_avg,
    SUM(comp_avg) - SUM(cost_basis) AS total_unrealized_gain
FROM v_inventory_detail
WHERE status = 'owned'
GROUP BY sport, player_name;


-- ============================================================
-- v_transaction_detail
-- Full ledger view: one row per card per transaction.
-- Positive amount = money in, negative = money out.
-- ============================================================
CREATE VIEW v_transaction_detail AS
SELECT
    t.transaction_id,
    t.transaction_date,
    t.transaction_type,
    t.counterparty,
    t.venue,
    t.cash_component,
    t.total_price,
    t.notes AS transaction_notes,

    ti.item_id,
    ti.direction,
    ti.item_price,

    -- Card detail
    c.card_id,
    c.year,
    c.manufacturer,
    c.set_name,
    c.card_number,
    c.player_name,
    c.parallel_name,
    c.is_auto,
    c.is_relic,
    c.print_run,

    i.inventory_id,
    i.is_graded,
    i.grading_company,
    i.grade,
    i.cost_basis
FROM transaction_items ti
JOIN transactions t  ON t.transaction_id  = ti.transaction_id
JOIN inventory   i  ON i.inventory_id    = ti.inventory_id
JOIN cards       c  ON c.card_id         = i.card_id;


-- ============================================================
-- v_pnl_summary
-- Realized P&L per sold/traded card.
-- cost_basis from inventory, proceeds from the disposal transaction item.
-- ============================================================
CREATE VIEW v_pnl_summary AS
SELECT
    c.player_name,
    c.year,
    c.manufacturer,
    c.set_name,
    c.card_number,
    c.parallel_name,
    t.transaction_date     AS disposal_date,
    t.transaction_type     AS disposal_type,
    t.venue,
    i.cost_basis,
    ti.item_price          AS proceeds,
    ti.item_price - i.cost_basis AS realized_gain
FROM transaction_items ti
JOIN transactions t ON t.transaction_id = ti.transaction_id
JOIN inventory    i ON i.inventory_id   = ti.inventory_id
JOIN cards        c ON c.card_id        = i.card_id
WHERE ti.direction = 'disposed';
