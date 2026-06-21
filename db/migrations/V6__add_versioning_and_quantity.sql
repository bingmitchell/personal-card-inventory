-- ============================================================
-- Soft-Delete & Versioning Columns
-- Enables data recovery without migration rollback and tracks
-- logical schema versions independently from Flyway.
-- ============================================================

-- Add soft-delete to CARDS table
ALTER TABLE cards
ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL,
ADD COLUMN version INTEGER DEFAULT 1;

-- Add soft-delete to INVENTORY table
ALTER TABLE inventory
ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL,
ADD COLUMN version INTEGER DEFAULT 1,
ADD COLUMN quantity INTEGER DEFAULT 1 CHECK (quantity > 0);

-- Add soft-delete to TRANSACTIONS table
ALTER TABLE transactions
ADD COLUMN deleted_at TIMESTAMPTZ DEFAULT NULL,
ADD COLUMN version INTEGER DEFAULT 1;

-- Create index for soft-delete queries (WHERE deleted_at IS NULL)
CREATE INDEX cards_deleted_at_idx ON cards (deleted_at);
CREATE INDEX inventory_deleted_at_idx ON inventory (deleted_at);
CREATE INDEX transactions_deleted_at_idx ON transactions (deleted_at);

-- Create a system settings table for schema versioning
CREATE TABLE IF NOT EXISTS schema_version (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Record current schema version
INSERT INTO schema_version (key, value) 
VALUES ('schema_version', '6')
ON CONFLICT (key) DO UPDATE SET value = '6', updated_at = NOW();
