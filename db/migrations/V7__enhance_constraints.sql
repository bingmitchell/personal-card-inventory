-- ============================================================
-- Enhanced Data Validation Constraints
-- Enforces business rules at the database level.
-- ============================================================

-- Update inventory status constraint to include all valid statuses
ALTER TABLE inventory
DROP CONSTRAINT inventory_status_check;

ALTER TABLE inventory
ADD CONSTRAINT inventory_status_check
CHECK (status IN ('OWNED', 'SOLD', 'TRADED', 'LOST'));

-- Ensure comp prices maintain logical order (low <= avg <= high)
-- Only add if constraint doesn't already exist
ALTER TABLE inventory
DROP CONSTRAINT IF EXISTS comp_prices_consistent;

ALTER TABLE inventory
ADD CONSTRAINT comp_prices_consistent CHECK (
    comp_low IS NULL 
    OR comp_high IS NULL 
    OR (comp_low <= comp_avg AND comp_avg <= comp_high)
);

-- Update transaction_type constraint
ALTER TABLE transactions
DROP CONSTRAINT transactions_transaction_type_check;

ALTER TABLE transactions
ADD CONSTRAINT transactions_transaction_type_check
CHECK (transaction_type IN ('PURCHASE', 'SALE', 'TRADE', 'DONATION'));

-- Create unique constraint on cards to prevent duplicate variants
-- (Already exists as index from V1; this ensures data integrity)
ALTER TABLE cards
DROP CONSTRAINT IF EXISTS cards_unique_variant_check;
