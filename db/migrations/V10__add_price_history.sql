-- V10: Add price history tracking for PowerBI trending
-- Purpose: Track comp price changes over time to enable value trending, ROI analysis, and volatility charts

CREATE TABLE price_history (
    history_id BIGSERIAL PRIMARY KEY,
    inventory_id INTEGER NOT NULL REFERENCES inventory(inventory_id) ON DELETE CASCADE,
    comp_low DECIMAL(10, 2),
    comp_avg DECIMAL(10, 2),
    comp_high DECIMAL(10, 2),
    recorded_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX price_history_inventory_date_idx ON price_history(inventory_id, recorded_date DESC);
CREATE INDEX price_history_recorded_date_idx ON price_history(recorded_date DESC);

COMMENT ON TABLE price_history IS 'Time-series snapshots of comp prices for each inventory item; enables PowerBI trending, ROI analysis, and portfolio value charts';
COMMENT ON COLUMN price_history.recorded_date IS 'When the price snapshot was taken (typically daily)';
